"""
RPA 服务 - 调度器管理、任务 CRUD、ETL 触发
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db_context

logger = logging.getLogger(__name__)

# Monkey-patch openpyxl 的 _NamedCellStyle（ERP exported的 Excel 样式 name 为 None）
# 必须在模块导入时执行，确保后续所有 pd.read_excel 调用都生效
try:
    from openpyxl.styles import named_styles as _ns
    _orig_named_init = _ns._NamedCellStyle.__init__
    def _patched_named_init(self, name=None, **kw):
        if name is None:
            name = "Normal"
        _orig_named_init(self, name=name, **kw)
    _ns._NamedCellStyle.__init__ = _patched_named_init
except Exception as _e:
    logger.warning(f"openpyxl monkey-patch 失败（不影响主流程）: {_e}")


def _safe_read_excel(path: str):
    """读取 Excel，自动处理ERP exported文件的 openpyxl 样式兼容问题（monkey-patch 兜底）"""
    import pandas as pd
    try:
        return pd.read_excel(path)
    except (TypeError, Exception) as e:
        if "name should be" in str(e) or "_NamedCellStyle" in str(e):
            # monkey-patch 未生效时再尝试一次（热修补）
            from openpyxl.styles import named_styles as ns
            orig_init = ns._NamedCellStyle.__init__
            def _patched(self, name=None, **kw):
                if name is None:
                    name = "Normal"
                orig_init(self, name=name, **kw)
            ns._NamedCellStyle.__init__ = _patched
            try:
                return pd.read_excel(path)
            finally:
                ns._NamedCellStyle.__init__ = orig_init
        raise

# 追踪正在运行的子进程，用于停止采集
_running_procs: dict[int, "subprocess.Popen"] = {}

# 全局调度器实例
_scheduler = None
_running_tasks = {}  # task_id -> asyncio.Task


def _parse_times_to_cron(schedule_times: list[str], schedule_days: str) -> list[dict]:
    """
    将时间点列表转换为 cron 触发器配置
    返回 [{"hour": 9, "minute": 0}, {"hour": 18, "minute": 30}, ...]
    """
    triggers = []
    for time_str in schedule_times:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        trigger_args = {"hour": hour, "minute": minute}

        if schedule_days == "daily":
            trigger_args["day_of_week"] = "mon,tue,wed,thu,fri,sat,sun"
        elif schedule_days == "weekdays":
            trigger_args["day_of_week"] = "mon,tue,wed,thu,fri"
        elif schedule_days == "weekend":
            trigger_args["day_of_week"] = "sat,sun"
        elif "," in schedule_days:
            # 自定义星期: "mon,wed,fri"
            trigger_args["day_of_week"] = schedule_days

        triggers.append(trigger_args)
    return triggers


def _calculate_next_run(schedule_times: list[str], schedule_days: str) -> Optional[datetime]:
    """计算下次执行时间"""
    now = datetime.now()
    today = now.strftime("%a").lower()[:3]  # mon, tue, ...

    # 判断今天是否在执行日范围内
    is_active_day = False
    if schedule_days == "daily":
        is_active_day = True
    elif schedule_days == "weekdays":
        is_active_day = now.weekday() < 5
    elif schedule_days == "weekend":
        is_active_day = now.weekday() >= 5
    elif "," in schedule_days:
        is_active_day = today in schedule_days

    # 找到最近的执行时间
    for time_str in sorted(schedule_times):
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if is_active_day and target > now:
            return target

    # 今天没有了，找明天的
    tomorrow = now + timedelta(days=1)
    if schedule_times:
        parts = sorted(schedule_times)[0].split(":")
        return tomorrow.replace(hour=int(parts[0]), minute=int(parts[1]) if len(parts) > 1 else 0, second=0, microsecond=0)

    return None


def _execute_rpa_task(task_id: int, skip_etl: bool = False):
    """执行 RPA 任务（通过独立子进程，避免 asyncio 事件循环冲突）"""
    import subprocess
    import sys
    import os
    from pathlib import Path

    worker_script = Path(__file__).parent / "rpa_worker.py"
    backend_dir = str(Path(__file__).parent.parent.parent)  # backend/
    logger.info(f"RPA 任务 #{task_id} 启动子进程 (skip_etl={skip_etl})")

    # 读取 per-task 超时设置
    try:
        with get_db_context() as db:
            row = db.execute(text("SELECT timeout_seconds FROM rpa_tasks WHERE id=:id"), {"id": task_id}).fetchone()
            task_timeout = row[0] if row and row[0] else 600
    except Exception:
        task_timeout = 600
    proc_timeout = max(task_timeout + 120, 600)  # 子进程超时 = 任务超时 + 2分钟缓冲，最少10分钟

    try:
        # 确保子进程能找到 app 模块和 Playwright 浏览器
        env = os.environ.copy()
        env["PYTHONPATH"] = backend_dir + os.pathsep + env.get("PYTHONPATH", "")
        # SYSTEM 用户的 Playwright 浏览器路径不同，指向实际安装位置
        # 优先使用环境变量 PLAYWRIGHT_BROWSERS_PATH,否则自动检测默认路径
        import platform
        if platform.system() == "Windows":
            default_pw = Path.home() / "AppData" / "Local" / "ms-playwright"
            pw_browsers = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", str(default_pw)))
            if pw_browsers.exists():
                env["PLAYWRIGHT_BROWSERS_PATH"] = str(pw_browsers)

        cmd = [sys.executable, str(worker_script), str(task_id)]
        if skip_etl:
            cmd.append("--skip-etl")
        proc = subprocess.Popen(
            cmd,
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # 注册进程，用于停止采集
        _running_procs[task_id] = proc

        # 等待子进程完成，收集输出用于日志
        stdout, stderr = proc.communicate(timeout=proc_timeout)

        # 注销进程
        _running_procs.pop(task_id, None)

        # 将子进程的 stderr（logger 输出）转发到主进程日志
        if stderr:
            for line in stderr.decode("utf-8", errors="replace").strip().splitlines():
                logger.info(f"[worker #{task_id}] {line}")

        if proc.returncode != 0:
            logger.warning(f"RPA 任务 #{task_id} 子进程退出码: {proc.returncode}")
            # 子进程异常退出时，确保日志不会卡在 running
            try:
                with get_db_context() as db:
                    error_output = stderr.decode("utf-8", errors="replace")[-500:] if stderr else "子进程异常退出"
                    _log_result(db, task_id, "failed",
                                error_msg=f"子进程退出码 {proc.returncode}: {error_output}",
                                error_type="runtime")
            except Exception:
                pass
        else:
            logger.info(f"RPA 任务 #{task_id} 子进程完成")

    except subprocess.TimeoutExpired:
        _running_procs.pop(task_id, None)
        proc.kill()
        logger.error(f"RPA 任务 #{task_id} 超时，已强制终止")
        with get_db_context() as db:
            _log_result(db, task_id, "failed", error_msg="执行超时", error_type="timeout")

            # 子进程被杀后邮件通知代码无法执行，由调度器补发
            try:
                task_row = db.execute(text("SELECT name, notify_targets FROM rpa_tasks WHERE id=:id"), {"id": task_id}).fetchone()
                task_name = task_row[0] if task_row else f"任务#{task_id}"
                notify_targets = task_row[1] if task_row else None
                from app.utils.email import notify_rpa_result
                notify_rpa_result(
                    db, task_name=task_name, module_name=task_name,
                    status="failed", duration_sec=proc_timeout,
                    error_msg="执行超时，子进程已被强制终止",
                    task_recipients=notify_targets,
                )
            except Exception as ne:
                logger.warning(f"超时后邮件通知异常: {ne}")
    except Exception as e:
        _running_procs.pop(task_id, None)
        logger.error(f"RPA 任务 #{task_id} 子进程异常: {e}", exc_info=True)
        try:
            with get_db_context() as db:
                _log_result(db, task_id, "failed", error_msg=str(e), error_type="runtime")

                # 子进程异常退出时也补发邮件
                try:
                    task_row = db.execute(text("SELECT name, notify_targets FROM rpa_tasks WHERE id=:id"), {"id": task_id}).fetchone()
                    task_name = task_row[0] if task_row else f"任务#{task_id}"
                    notify_targets = task_row[1] if task_row else None
                    from app.utils.email import notify_rpa_result
                    notify_rpa_result(
                        db, task_name=task_name, module_name=task_name,
                        status="failed", duration_sec=0,
                        error_msg=f"子进程异常: {str(e)[:200]}",
                        task_recipients=notify_targets,
                    )
                except Exception as ne:
                    logger.warning(f"异常后邮件通知失败: {ne}")
        except:
            pass


async def execute_task(task_id: int):
    """公开接口：手动触发任务执行（异步包装）"""
    import asyncio
    await asyncio.to_thread(_execute_rpa_task, task_id)


def execute_task_sync(task_id: int, skip_etl: bool = False):
    """公开接口：手动触发任务执行（同步包装，用于 BackgroundTasks）"""
    try:
        _execute_rpa_task(task_id, skip_etl=skip_etl)
    except Exception as e:
        logger.error(f"RPA 任务 #{task_id} 执行异常: {e}", exc_info=True)


def stop_all_running() -> list[int]:
    """停止所有正在运行的 RPA 子进程，返回被终止的任务 ID 列表"""
    import os, signal
    stopped = []
    for task_id, proc in list(_running_procs.items()):
        try:
            if proc.poll() is None:  # 进程仍在运行
                # 杀掉进程树（Windows: taskkill /T, Unix: os.killpg）
                if os.name == "nt":
                    os.system(f"taskkill /F /T /PID {proc.pid}")
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                stopped.append(task_id)
                logger.info(f"已终止 RPA 任务 #{task_id} (PID={proc.pid})")
            _running_procs.pop(task_id, None)
        except Exception as e:
            logger.warning(f"终止任务 #{task_id} 失败: {e}")
            _running_procs.pop(task_id, None)
    return stopped


def _get_config_value(db: Session, key: str, default: str = "") -> str:
    """从 sys_config 表获取配置值"""
    try:
        row = db.execute(text("SELECT config_value FROM sys_config WHERE config_key=:key"), {"key": key}).fetchone()
        return row[0] if row and row[0] else default
    except:
        return default


def _create_log(db: Session, task_id: int) -> int:
    """创建执行日志"""
    db.execute(text("""
        INSERT INTO rpa_logs (task_id, status, started_at) VALUES (:task_id, 'running', NOW())
    """), {"task_id": task_id})
    db.commit()
    row = db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()
    return row[0]


def _update_log(db: Session, log_id: int, status: str, file_path: str = None, error_msg: str = None):
    """更新执行日志"""
    db.execute(text("""
        UPDATE rpa_logs SET status=:status, finished_at=NOW(),
        duration_sec=TIMESTAMPDIFF(SECOND, started_at, NOW()),
        file_path=:file_path, error_msg=:error_msg
        WHERE id=:id
    """), {"status": status, "file_path": file_path, "error_msg": error_msg, "id": log_id})
    db.commit()


def _log_result(db: Session, task_id: int, status: str, error_msg: str = None, error_type: str = None):
    """记录执行结果"""
    db.execute(text("""
        UPDATE rpa_logs SET status=:status, finished_at=NOW(),
        duration_sec=TIMESTAMPDIFF(SECOND, started_at, NOW()),
        error_msg=:error_msg, error_type=:error_type
        WHERE task_id=:task_id AND status='running'
    """), {"status": status, "error_msg": error_msg, "error_type": error_type, "task_id": task_id})
    db.commit()


def _trigger_etl(file_paths: list[str], log_id: int, db: Session):
    """触发 ETL 处理"""
    try:
        from app.services.etl_service import run_etl
        import pandas as pd

        raw_data = {}
        for fp in file_paths:
            if not fp or not Path(fp).exists():
                continue
            try:
                df = pd.read_excel(fp)
                # 根据文件名判断数据类型
                fname = Path(fp).stem
                if "现存量" in fname:
                    raw_data["current_stock"] = df
                elif "采购入库" in fname or "入库" in fname:
                    raw_data["stock_in"] = df
                elif "销售出库" in fname or "出库" in fname:
                    raw_data["sales_out"] = df
            except Exception as e:
                logger.warning(f"读取文件失败 {fp}: {e}")

        if raw_data:
            result = run_etl(raw_data, db)
            rows = sum(len(v) for v in raw_data.values())
            db.execute(text("""
                UPDATE rpa_logs SET etl_status='success', etl_rows=:rows WHERE id=:id
            """), {"rows": rows, "id": log_id})
            db.commit()
            logger.info(f"ETL 完成: {rows} 条记录")
        else:
            db.execute(text("UPDATE rpa_logs SET etl_status='skipped' WHERE id=:id"), {"id": log_id})
            db.commit()

    except Exception as e:
        logger.error(f"ETL 触发失败: {e}", exc_info=True)
        try:
            db.execute(text("""
                UPDATE rpa_logs SET etl_status='failed', error_msg=:msg WHERE id=:id
            """), {"msg": str(e), "id": log_id})
            db.commit()
        except:
            pass


def cleanup_stale_running_logs(stale_minutes: int = 30) -> int:
    """
    清理 rpa_logs 中状态卡在 running 的僵尸记录。

    适用场景：worker 子进程被 OOM / kill / 父进程崩溃时，
    _update_log / _update_etl_log 没机会被调用，DB 里 status 永远 running。
    调度器/ETL 看到 running 状态会误判任务还在跑，不能触发新一次。

    规则：status='running' AND started_at < NOW() - INTERVAL stale_minutes MINUTE
    处理：标 failed，写 finished_at 和 error_msg。
    """
    try:
        with get_db_context() as db:
            row = db.execute(text("""
                UPDATE rpa_logs
                SET status = 'failed',
                    finished_at = NOW(),
                    error_msg = CONCAT('超时清理（卡在 running > ', :minutes, ' 分钟）: ', COALESCE(error_msg, '')),
                    error_type = 'timeout'
                WHERE status = 'running'
                  AND started_at < DATE_SUB(NOW(), INTERVAL :minutes MINUTE)
            """), {"minutes": stale_minutes})
            cleaned = row.rowcount
            db.commit()
            if cleaned > 0:
                logger.warning(f"清理了 {cleaned} 条僵尸 rpa_logs 记录（running > {stale_minutes} 分钟）")
            return cleaned
    except Exception as e:
        logger.error(f"清理僵尸 rpa_logs 失败: {e}", exc_info=True)
        return 0


def start_scheduler():
    """启动 APScheduler 调度器"""
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        # 先清理上次崩溃遗留的僵尸日志（必须先于 _restore_tasks，
        # 避免 _restore_tasks 误把僵尸状态当成"任务还在跑"）
        cleanup_stale_running_logs(stale_minutes=30)

        _scheduler = AsyncIOScheduler()
        _scheduler.start()
        logger.info("RPA 调度器已启动")

        # 从数据库加载已有任务
        _restore_tasks()
    except ImportError:
        logger.warning("APScheduler 未安装，定时功能不可用。pip install APScheduler")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}")


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("RPA 调度器已停止")


def _restore_tasks():
    """从数据库恢复所有启用的任务到调度器"""
    try:
        with get_db_context() as db:
            rows = db.execute(text("SELECT * FROM rpa_tasks WHERE enabled=1")).fetchall()
            for row in rows:
                _add_job_to_scheduler(row.id, row.schedule_times, row.schedule_days)
            logger.info(f"恢复了 {len(rows)} 个 RPA 任务")
    except Exception as e:
        logger.warning(f"恢复任务失败: {e}")


def _add_job_to_scheduler(task_id: int, schedule_times_json: str, schedule_days: str):
    """添加任务到调度器"""
    if not _scheduler:
        return

    import json
    from apscheduler.triggers.cron import CronTrigger

    # 移除旧的 job（如果存在）
    job_id = f"rpa_task_{task_id}"
    existing = _scheduler.get_job(job_id)
    if existing:
        existing.remove()

    # 解析时间点
    times = json.loads(schedule_times_json) if isinstance(schedule_times_json, str) else schedule_times_json

    # 为每个时间点创建一个 cron trigger
    for i, time_str in enumerate(times):
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        trigger_args = {"hour": hour, "minute": minute}
        if schedule_days == "weekdays":
            trigger_args["day_of_week"] = "mon,tue,wed,thu,fri"
        elif schedule_days == "weekend":
            trigger_args["day_of_week"] = "sat,sun"
        elif schedule_days != "daily" and "," in schedule_days:
            trigger_args["day_of_week"] = schedule_days

        trigger = CronTrigger(**trigger_args)
        _scheduler.add_job(
            _execute_rpa_task,
            trigger=trigger,
            args=[task_id],
            id=f"{job_id}_{i}",
            replace_existing=True,
            misfire_grace_time=3600,
        )

    logger.info(f"已添加任务 #{task_id} 到调度器: {times} ({schedule_days})")


def remove_job_from_scheduler(task_id: int):
    """从调度器移除任务"""
    if not _scheduler:
        return
    job_id = f"rpa_task_{task_id}"
    for job in _scheduler.get_jobs():
        if job.id.startswith(job_id):
            job.remove()


def get_scheduler_status() -> dict:
    """获取调度器状态"""
    if not _scheduler:
        return {"running": False, "jobs": 0, "next_runs": []}

    jobs = _scheduler.get_jobs()
    next_runs = []
    for job in jobs:
        next_run = job.next_run_time
        if next_run:
            next_runs.append({
                "job_id": job.id,
                "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S"),
            })

    return {
        "running": _scheduler.running,
        "jobs": len(jobs),
        "next_runs": sorted(next_runs, key=lambda x: x["next_run"])[:10],
    }


# ============ 任务 CRUD ============

def get_all_tasks(db: Session) -> list[dict]:
    """获取所有任务"""
    rows = db.execute(text("SELECT * FROM rpa_tasks ORDER BY created_at DESC")).fetchall()
    return [dict(row._mapping) for row in rows]


def get_task(db: Session, task_id: int) -> Optional[dict]:
    """获取单个任务"""
    row = db.execute(text("SELECT * FROM rpa_tasks WHERE id=:id"), {"id": task_id}).fetchone()
    return dict(row._mapping) if row else None


def create_task(db: Session, data: dict) -> dict:
    """创建任务"""
    import json
    db.execute(text("""
        INSERT INTO rpa_tasks (name, module_name, enabled, schedule_times, schedule_days,
            max_retries, retry_interval, captcha_strategy, notify_channels, notify_targets, next_run_at)
        VALUES (:name, :module_name, :enabled, :schedule_times, :schedule_days,
            :max_retries, :retry_interval, :captcha_strategy, :notify_channels, :notify_targets, :next_run_at)
    """), {
        "name": data["name"],
        "module_name": data["module_name"],
        "enabled": data.get("enabled", True),
        "schedule_times": json.dumps(data["schedule_times"]),
        "schedule_days": data.get("schedule_days", "daily"),
        "max_retries": data.get("max_retries", 3),
        "retry_interval": data.get("retry_interval", 5),
        "captcha_strategy": data.get("captcha_strategy", "skip"),
        "notify_channels": json.dumps(data.get("notify_channels", [])),
        "notify_targets": data.get("notify_targets") or None,
        "next_run_at": _calculate_next_run(data["schedule_times"], data.get("schedule_days", "daily")),
    })
    db.commit()

    task_id = db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
    task = get_task(db, task_id)

    # 添加到调度器
    if task.get("enabled"):
        _add_job_to_scheduler(task_id, task["schedule_times"], task["schedule_days"])

    return task


def update_task(db: Session, task_id: int, data: dict) -> dict:
    """更新任务"""
    import json
    fields = []
    params = {"id": task_id}

    for key in ["name", "module_name", "enabled", "max_retries", "retry_interval", "captcha_strategy"]:
        if key in data:
            fields.append(f"{key}=:{key}")
            params[key] = data[key]

    if "schedule_times" in data:
        fields.append("schedule_times=:schedule_times")
        params["schedule_times"] = json.dumps(data["schedule_times"])

    if "schedule_days" in data:
        fields.append("schedule_days=:schedule_days")
        params["schedule_days"] = data["schedule_days"]

    if "notify_channels" in data:
        fields.append("notify_channels=:notify_channels")
        params["notify_channels"] = json.dumps(data["notify_channels"])

    if "notify_targets" in data:
        fields.append("notify_targets=:notify_targets")
        params["notify_targets"] = data["notify_targets"] or None

    if "schedule_times" in data or "schedule_days" in data:
        task = get_task(db, task_id)
        times = data.get("schedule_times", json.loads(task["schedule_times"]))
        days = data.get("schedule_days", task["schedule_days"])
        fields.append("next_run_at=:next_run_at")
        params["next_run_at"] = _calculate_next_run(times, days)

    if fields:
        db.execute(text(f"UPDATE rpa_tasks SET {', '.join(fields)}, updated_at=NOW() WHERE id=:id"), params)
        db.commit()

    task = get_task(db, task_id)

    # 更新调度器
    remove_job_from_scheduler(task_id)
    if task.get("enabled"):
        _add_job_to_scheduler(task_id, task["schedule_times"], task["schedule_days"])

    return task


def delete_task(db: Session, task_id: int):
    """删除任务"""
    remove_job_from_scheduler(task_id)
    db.execute(text("DELETE FROM rpa_tasks WHERE id=:id"), {"id": task_id})
    db.commit()


def toggle_task(db: Session, task_id: int) -> dict:
    """启用/禁用任务"""
    task = get_task(db, task_id)
    if not task:
        return None

    new_enabled = not task["enabled"]
    db.execute(text("UPDATE rpa_tasks SET enabled=:enabled, updated_at=NOW() WHERE id=:id"),
               {"enabled": new_enabled, "id": task_id})
    db.commit()

    if new_enabled:
        _add_job_to_scheduler(task_id, task["schedule_times"], task["schedule_days"])
    else:
        remove_job_from_scheduler(task_id)

    return get_task(db, task_id)


def get_logs(db: Session, task_id: int = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """获取执行日志
    派生 log_kind：etl=ETL阶段日志(task_id=0)、main=主任务汇总(task_name NULL)、module=模块行
    """
    log_kind_sql = (
        "CASE WHEN l.task_id=0 THEN 'etl' "
        "     WHEN l.task_name IS NULL THEN 'main' "
        "     ELSE 'module' END"
    )
    if task_id:
        rows = db.execute(text(f"""
            SELECT l.*,
                   l.task_name AS task_name,
                   t.name AS task_real_name,
                   {log_kind_sql} AS log_kind
            FROM rpa_logs l
            LEFT JOIN rpa_tasks t ON l.task_id = t.id
            WHERE l.task_id=:task_id ORDER BY l.started_at DESC LIMIT :limit OFFSET :offset
        """), {"task_id": task_id, "limit": limit, "offset": offset}).fetchall()
    else:
        rows = db.execute(text(f"""
            SELECT l.*,
                   l.task_name AS task_name,
                   t.name AS task_real_name,
                   {log_kind_sql} AS log_kind
            FROM rpa_logs l
            LEFT JOIN rpa_tasks t ON l.task_id = t.id
            ORDER BY l.started_at DESC LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset}).fetchall()

    return [dict(row._mapping) for row in rows]


def get_stats(db: Session) -> dict:
    """获取统计信息"""
    total = db.execute(text("SELECT COUNT(*) FROM rpa_tasks")).fetchone()[0]
    enabled = db.execute(text("SELECT COUNT(*) FROM rpa_tasks WHERE enabled=1")).fetchone()[0]
    last_success = db.execute(text("""
        SELECT COUNT(*) FROM rpa_tasks WHERE last_run_status='success'
    """)).fetchone()[0]
    last_failed = db.execute(text("""
        SELECT COUNT(*) FROM rpa_tasks WHERE last_run_status='failed'
    """)).fetchone()[0]
    last_run = db.execute(text("""
        SELECT MAX(last_run_at) FROM rpa_tasks
    """)).fetchone()[0]

    return {
        "total_tasks": total,
        "enabled_tasks": enabled,
        "last_success": last_success,
        "last_failed": last_failed,
        "last_run_at": last_run.strftime("%Y-%m-%d %H:%M") if last_run else None,
    }


def test_connection(db: Session, url: str, username: str, password: str) -> dict:
    """测试ERP system连接（在子进程中运行，避免事件循环冲突）

    安全:用 base64 编码参数,避免 f-string 拼代码导致的 Python 代码注入。
    """
    import subprocess
    import sys
    import base64
    from pathlib import Path

    # base64 编码参数,确保不会作为代码执行
    params_b64 = base64.b64encode(
        f"{url}|{username}|{password}".encode("utf-8")
    ).decode("ascii")

    worker_code = f"""
import asyncio, sys, base64
params_b64 = "{params_b64}"
params_str = base64.b64decode(params_b64).decode("utf-8")
url, username, password = params_str.split("|", 2)

async def test():
    from app.services.rpa_engine import RpaEngine
    engine = RpaEngine(download_dir="./rpa_test")
    try:
        await engine.start()
        ok = await engine.login(url, username, password)
        await engine.close()
        return ok
    except Exception as e:
        try: await engine.close()
        except: pass
        raise e

result = asyncio.run(test())
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", worker_code],
            cwd=str(Path(__file__).parent.parent.parent),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return {"success": True, "message": "连接成功"}
        else:
            err = proc.stderr.strip().splitlines()[-1] if proc.stderr else "未知错误"
            return {"success": False, "message": f"连接失败: {err}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "连接超时"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


def trigger_etl_once():
    """统一触发一次 ETL（在所有采集任务完成后调用）"""
    from pathlib import Path
    from app.services.etl_service import run_etl
    from datetime import datetime

    logger.info("===== 统一触发 ETL =====")

    # 从数据库获取下载目录
    try:
        with get_db_context() as db:
            download_dir = _get_config_value(db, "rpa_download_dir", "./rpa_downloads")
    except Exception as e:
        logger.error(f"获取下载目录配置失败: {e}")
        return

    date_dir = Path(download_dir).resolve() / datetime.now().strftime("%Y-%m-%d")
    logger.info(f"ETL 扫描目录: {date_dir}, exists={date_dir.exists()}")

    KEY_MAP = {
        "现存量": "current_stock",
        "采购入库": "入库单",
        "入库单": "入库单",
        "入库": "入库单",
        "销售出库": "销售出库单",
        "出库": "销售出库单",
        "请购单": "请购单",
        "请购": "请购单",
        "采购单": "采购单",
        "提货": "采购单",
    }
    REQUIRED_KEYS = {"请购单", "采购单", "入库单", "销售出库单", "current_stock"}

    raw_data = {}
    if date_dir.exists():
        for f in date_dir.glob("*.xlsx"):
            for pattern, key in KEY_MAP.items():
                if pattern in f.stem:
                    try:
                        raw_data[key] = _safe_read_excel(str(f))
                        logger.info(f"ETL 收集: {f.name} → {key}")
                        break
                    except Exception as e:
                        logger.warning(f"读取文件失败 {f}: {e}")

    # 缺失的表从 etl_data 目录补充
    missing = REQUIRED_KEYS - set(raw_data.keys())
    if missing:
        etl_data_dir = Path(download_dir).resolve().parent.parent / "etl_data"
        if etl_data_dir.exists():
            for f in sorted(etl_data_dir.glob("*.xlsx"), reverse=True):
                for pattern, key in KEY_MAP.items():
                    if key in missing and pattern in f.stem:
                        try:
                            raw_data[key] = _safe_read_excel(str(f))
                            logger.info(f"ETL 补充(etl_data): {f.name} → {key}")
                            missing.discard(key)
                            break
                        except Exception as e:
                            logger.warning(f"读取文件失败 {f}: {e}")

    missing = REQUIRED_KEYS - set(raw_data.keys())
    if missing:
        logger.warning(f"ETL 无法执行，缺少: {missing} (已有: {set(raw_data.keys())})")
        # 即使缺失也要写一条 failed 日志，让前端能看到状态
        try:
            with get_db_context() as db:
                db.execute(text(
                    "INSERT INTO rpa_logs (task_id, task_name, status, started_at, finished_at, duration_sec, error_msg, error_type) "
                    "VALUES (0, 'ETL 数据导入', 'failed', NOW(), NOW(), 0, :msg, 'missing_files')"
                ), {"msg": f"ETL 无法执行，缺少文件: {sorted(missing)} (已有: {sorted(set(raw_data.keys()))})"})
                db.commit()
        except Exception as log_e:
            logger.error(f"写入ETL缺失文件日志失败: {log_e}")
        return

    logger.info("5 张表全部就绪，开始 ETL")
    with get_db_context() as db:
        # 创建 ETL 日志
        db.execute(text(
            "INSERT INTO rpa_logs (task_id, task_name, status, started_at) VALUES (0, 'ETL 数据导入', 'running', NOW())"
        ))
        db.commit()
        etl_log_id = db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

        etl_start = datetime.now()
        try:
            run_etl(raw_data, db)
            rows = sum(len(v) for v in raw_data.values())
            etl_duration = int((datetime.now() - etl_start).total_seconds())
            db.execute(text("""
                UPDATE rpa_logs SET status='success', finished_at=NOW(),
                duration_sec=:duration, error_msg=:detail WHERE id=:id
            """), {"duration": etl_duration, "detail": f"导入 {rows} 条记录", "id": etl_log_id})
            db.commit()
            logger.info(f"ETL 完成: {rows} 条, 耗时 {etl_duration}s")
        except Exception as e:
            etl_duration = int((datetime.now() - etl_start).total_seconds())
            db.execute(text("""
                UPDATE rpa_logs SET status='failed', finished_at=NOW(),
                duration_sec=:duration, error_msg=:detail WHERE id=:id
            """), {"duration": etl_duration, "detail": str(e)[:500], "id": etl_log_id})
            db.commit()
            logger.error(f"ETL 执行失败: {e}", exc_info=True)


# 需要在文件顶部导入
from pathlib import Path
