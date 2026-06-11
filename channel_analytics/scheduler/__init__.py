"""scheduler 包 — APScheduler 顶层封装 + ETL 触发钩子。

注意:本包的实现复用 rpa.scheduler.RpaScheduler(90% 通用);
新仓这里只放任务调度的高层 facade + ETL 触发钩子。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ETL 触发钩子(对应原仓 ETL 联动)
# ---------------------------------------------------------------------------

@dataclass
class EtlJobConfig:
    """ETL 调度任务配置。"""
    job_id: str
    cron: str  # 标准 5 段 crontab
    raw_data_loader: Callable[[datetime], dict[str, Any]] | None = None
    brand_provider_dotted: str = (
        "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
    )
    business_rules_path: str = ""
    engine: Any = None  # SQLAlchemy engine(可选,无则不写库)


def run_etl_job(config: EtlJobConfig) -> None:
    """ETL 触发函数(被 scheduler 调用)。

    异常被吞 + 日志记录,避免 APScheduler 杀掉整个 scheduler。
    """
    from channel_analytics.etl.pipeline import run_default_etl
    try:
        now = datetime.utcnow()
        raw_data = config.raw_data_loader(now) if config.raw_data_loader else {}
        ctx = run_default_etl(
            raw_data,
            brand_provider_dotted=config.brand_provider_dotted,
            business_rules_path=config.business_rules_path,
        )
        # 若有 engine,触发 Writer 步骤
        if config.engine is not None:
            ctx.meta["engine"] = config.engine
            # 重跑 pipeline 走 writer(简化版:直接用 WriteRptTablesStep)
            from channel_analytics.etl.steps.write_rpt_tables import WriteRptTablesStep
            WriteRptTablesStep().run(ctx)
        logger.info("ETL job %s 完成: stg=%d rpt=%d", config.job_id, len(ctx.stg), len(ctx.rpt))
    except Exception as e:  # noqa: BLE001
        logger.exception("ETL job %s 失败: %s", config.job_id, e)


# ---------------------------------------------------------------------------
# 顶层 Scheduler Facade
# ---------------------------------------------------------------------------

class SchedulerService:
    """APScheduler 顶层 facade(RPA + ETL 共用)。"""

    def __init__(self, timezone: str = "Asia/Shanghai") -> None:
        self.timezone = timezone
        self._scheduler: BackgroundScheduler | None = None
        self._etl_jobs: dict[str, EtlJobConfig] = {}

    def start(self) -> None:
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler(timezone=self.timezone)
            self._scheduler.start()
            logger.info("SchedulerService started")

    def shutdown(self) -> None:
        if self._scheduler is not None:
            try:
                self._scheduler.shutdown(wait=True)
            finally:
                self._scheduler = None

    # ----- ETL jobs -----

    def schedule_etl(self, config: EtlJobConfig) -> None:
        if self._scheduler is None:
            raise RuntimeError("Scheduler 未启动")
        self._etl_jobs[config.job_id] = config
        trigger = CronTrigger.from_crontab(config.cron, timezone=self.timezone)
        self._scheduler.add_job(
            func=run_etl_job,
            args=[config],
            trigger=trigger,
            id=f"etl_{config.job_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("ETL job %s scheduled: %s", config.job_id, config.cron)

    def unschedule_etl(self, job_id: str) -> None:
        self._etl_jobs.pop(job_id, None)
        if self._scheduler:
            try:
                self._scheduler.remove_job(f"etl_{job_id}")
            except Exception:
                pass

    def list_etl_jobs(self) -> list[str]:
        return list(self._etl_jobs.keys())

    def trigger_etl_now(self, job_id: str) -> None:
        """立即触发(用于测试 / 手动跑)。"""
        if job_id not in self._etl_jobs:
            raise KeyError(f"ETL job {job_id} not scheduled")
        run_etl_job(self._etl_jobs[job_id])


__all__ = ["SchedulerService", "EtlJobConfig", "run_etl_job"]