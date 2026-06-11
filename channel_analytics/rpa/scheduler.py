"""RPA 调度器 — APScheduler 封装 + 任务 CRUD + ETL 触发钩子。

设计要点:
  - 单例 Scheduler(全局唯一),便于 FastAPI lifespan 管理
  - 任务存储:RPA_TASKS 表(由 ORM 提供,可选;无表时只做内存)
  - ETL 触发:on_module_done 可触发 ETL Pipeline(注入 ctx)
  - 僵尸清理:启动时清 status=running 的过期记录(对齐原仓 rpa_worker L57-77)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from channel_analytics.rpa.runner import ModuleResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 任务模型(纯数据,不绑 ORM,部署期可换 ORM 模型)
# ---------------------------------------------------------------------------

@dataclass
class RpaTask:
    """RPA 任务定义。"""
    id: int
    name: str
    module_names: list[str]
    schedule_cron: str | None = None  # 例如 "0 9 * * *"
    is_active: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RpaLog:
    """单次执行日志。"""
    task_id: int
    task_name: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"  # running / success / failed
    error_msg: str | None = None
    error_type: str | None = None  # config / stale / login / navigate / export / etl


# ---------------------------------------------------------------------------
# 调度器
# ---------------------------------------------------------------------------

class RpaScheduler:
    """APScheduler 封装(对齐原仓 rpa_service._scheduler)。"""

    def __init__(self) -> None:
        self._scheduler: BackgroundScheduler | None = None
        # task_id -> RpaTask(内存注册)
        self._tasks: dict[int, RpaTask] = {}
        # task_id -> 当前正在执行的 log
        self._running: dict[int, RpaLog] = {}

    # ----- 生命周期 -----

    def start(self) -> None:
        """启动后台调度器。"""
        if self._scheduler is not None:
            return
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self._scheduler.start()
        logger.info("RPA Scheduler started")

    def shutdown(self) -> None:
        """关闭调度器,等待所有任务结束。"""
        if self._scheduler is None:
            return
        try:
            self._scheduler.shutdown(wait=True)
        finally:
            self._scheduler = None
        logger.info("RPA Scheduler stopped")

    # ----- 任务 CRUD -----

    def register(self, task: RpaTask, runner_fn: Callable[[RpaTask], None]) -> None:
        """注册任务 + 调度(对齐原仓 rpa_service.add_task)。"""
        if self._scheduler is None:
            raise RuntimeError("Scheduler 未启动")
        self._tasks[task.id] = task
        if task.is_active and task.schedule_cron:
            trigger = CronTrigger.from_crontab(task.schedule_cron, timezone="Asia/Shanghai")
            self._scheduler.add_job(
                func=runner_fn,
                args=[task],
                trigger=trigger,
                id=f"rpa_task_{task.id}",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info("RPA task %d 注册到调度器: %s", task.id, task.schedule_cron)

    def unregister(self, task_id: int) -> None:
        """注销任务。"""
        self._tasks.pop(task_id, None)
        if self._scheduler:
            try:
                self._scheduler.remove_job(f"rpa_task_{task_id}")
            except Exception:
                pass

    def list_tasks(self) -> list[RpaTask]:
        return list(self._tasks.values())

    # ----- 执行 + 日志 -----

    def mark_start(self, task: RpaTask) -> RpaLog:
        log = RpaLog(task_id=task.id, task_name=task.name, started_at=datetime.utcnow())
        self._running[task.id] = log
        return log

    def mark_done(
        self,
        log: RpaLog,
        results: list[ModuleResult],
    ) -> None:
        """所有模块跑完后回写 log(对齐原仓 _update_log)。"""
        log.finished_at = datetime.utcnow()
        if all(r.success for r in results):
            log.status = "success"
        else:
            log.status = "failed"
            first_fail = next((r for r in results if not r.success), None)
            if first_fail and first_fail.error:
                log.error_msg = first_fail.error
                log.error_type = first_fail.error.split(":", 1)[0] if ":" in first_fail.error else "unknown"
        self._running.pop(log.task_id, None)

    def cleanup_stale_running(
        self,
        storage: Any | None = None,
        etl_task_name: str = "ETL 数据导入",
    ) -> int:
        """清理僵尸 running 记录(对齐原仓 rpa_worker L57-77)。

        storage: 可选 ORM session;None 时只清内存。
        返回清理条数。
        """
        cleaned = 0
        # 内存部分
        for tid, log in list(self._running.items()):
            log.status = "failed"
            log.finished_at = datetime.utcnow()
            log.error_msg = (log.error_msg or "") + " [stale cleanup]"
            log.error_type = "stale"
            cleaned += 1
        self._running.clear()

        # DB 部分(若有 storage)
        if storage is not None:
            try:
                from sqlalchemy import text
                result = storage.execute(text("""
                    UPDATE rpa_logs
                    SET status = 'failed',
                        finished_at = NOW(),
                        error_msg = CONCAT('worker 重入清理: ', COALESCE(error_msg, '')),
                        error_type = 'stale'
                    WHERE status = 'running'
                      AND (task_id = 0 AND task_name = :etl_name)
                """), {"etl_name": etl_task_name})
                storage.commit()
                cleaned += result.rowcount or 0
            except Exception as e:
                logger.warning("storage 僵尸清理失败: %s", e)
        return cleaned


__all__ = ["RpaScheduler", "RpaTask", "RpaLog"]