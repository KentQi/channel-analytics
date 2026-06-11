"""
RPA Worker - 独立进程入口
通过 subprocess.Popen 调用，完全隔离 Playwright 与 FastAPI 的事件循环。
"""
import asyncio
import json
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("rpa_worker")


def main():
    """
    命令行入口:
        python -m app.services.rpa_worker <task_id> [--skip-etl]
    """
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.rpa_worker <task_id> [--skip-etl]", file=sys.stderr)
        sys.exit(1)

    task_id = int(sys.argv[1])
    skip_etl = "--skip-etl" in sys.argv
    logger.info(f"Worker 进程启动, task_id={task_id}")

    try:
        from app.database import get_db_context
        from app.services.rpa_engine import RpaEngine, cleanup_old_downloads
        from sqlalchemy import text

        with get_db_context() as db:
            task = db.execute(
                text("SELECT * FROM rpa_tasks WHERE id = :id"), {"id": task_id}
            ).fetchone()
            if not task:
                _fail(db, task_id, "任务不存在")
                sys.exit(1)

            # 进入时清理同 task_id 遗留的 running 僵尸记录。
            # 场景：上次 worker 进程被 OOM / kill / 父进程崩溃，
            # _update_log 没机会回写，导致 rpa_logs status 永远 running，
            # 调度器后续看到 running 会误判任务还在跑。
            # 同时清掉 ETL 任务卡死的（task_id=0, task_name='ETL 数据导入'），
            # 防止"采集成功 + ETL 假 running"导致下游永远等不到。
            db.execute(text("""
                UPDATE rpa_logs
                SET status = 'failed',
                    finished_at = NOW(),
                    error_msg = CONCAT('worker 重入清理: ', COALESCE(error_msg, '')),
                    error_type = 'stale'
                WHERE status = 'running'
                  AND (task_id = :task_id
                       OR (task_id = 0 AND task_name = 'ETL 数据导入'))
            """), {"task_id": task_id})
            db.commit()

            url = _cfg(db, "rpa_erp_url", "https://erp.example.com")
            username = _cfg(db, "rpa_erp_username", "")
            password = _cfg(db, "rpa_erp_password", "")
            if not username or not password:
                _fail(db, task_id, "ERP system账号未配置", error_type="config")
                sys.exit(1)

            modules = json.loads(task.module_name) if task.module_name.startswith("[") else [task.module_name]
            download_dir = _cfg(db, "rpa_download_dir", "./rpa_downloads")
            headless = _cfg(db, "rpa_headless", "true").lower() == "true"
            slow_mo = int(_cfg(db, "rpa_slow_mo", "300"))
            timeout_mult = float(_cfg(db, "rpa_timeout_multiplier", "1.5"))

            # 创建执行日志
            log_id = _create_log(db, task_id)
            log_started_at = datetime.now()

            # 为每个模块创建独立的 running 日志
            module_log_ids = {}
            for m in modules:
                module_log_ids[m] = _create_module_log(db, task_id, m)

        # ---- Playwright 在独立进程中运行，无事件循环冲突 ----
        engine = RpaEngine(download_dir=download_dir, headless=headless,
                           slow_mo=slow_mo, timeout_multiplier=timeout_mult)

        # 模块级日志回调：每个模块完成后立即更新库
        def on_module_done(module_name: str, result: dict):
            try:
                with get_db_context() as mod_db:
                    status = "success" if result["success"] else "failed"
                    mod_db.execute(text("""
                        UPDATE rpa_logs SET status=:status, finished_at=NOW(),
                        duration_sec=:duration, file_path=:file_path, error_msg=:error_msg
                        WHERE id=:log_id
                    """), {
                        "status": status,
                        "duration": result.get("duration", 0),
                        "file_path": result.get("file"),
                        "error_msg": result.get("error"),
                        "log_id": module_log_ids.get(module_name),
                    })
                    mod_db.commit()
                    logger.info(f"模块「{module_name}」完成: {status}, {result.get('duration', 0)}s")
            except Exception as e:
                logger.warning(f"写入模块日志失败({module_name}): {e}")

        try:
            results = asyncio.run(engine.run_all(modules, username, password, url,
                                                  on_module_done=on_module_done))
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.warning(f"Playwright 清理时事件循环已关闭（忽略）: {e}")
                results = engine._last_results if hasattr(engine, '_last_results') else {}
            else:
                raise

        # 记录结果
        with get_db_context() as db:
            success = all(r["success"] for r in results.values()) if results else False
            files = [r["file"] for r in results.values() if r.get("file")] if results else []
            errors = [f"{k}: {r['error']}" for k, r in results.items() if r.get("error")] if results else ["执行无结果"]

            _update_log(
                db, log_id,
                "success" if success else "failed",
                file_path=files[0] if files else None,
                error_msg="; ".join(errors) if errors else None,
            )

            db.execute(text("""
                UPDATE rpa_tasks SET last_run_at=NOW(), last_run_status=:status, updated_at=NOW()
                WHERE id=:id
            """), {"status": "success" if success else "failed", "id": task_id})
            db.commit()

            # 邮件通知
            try:
                task_row = db.execute(text("SELECT name, notify_targets FROM rpa_tasks WHERE id=:id"), {"id": task_id}).fetchone()
                task_name = task_row[0] if task_row else f"任务#{task_id}"
                notify_targets = task_row[1] if task_row else None
                from app.utils.email import notify_rpa_result
                notify_rpa_result(
                    db, task_name=task_name, module_name=task_name,
                    status="success" if success else "failed",
                    duration_sec=int((datetime.now() - log_started_at).total_seconds()),
                    error_msg="; ".join(errors) if not success else "",
                    file_path=files[0] if files else "",
                    task_recipients=notify_targets,
                )
            except Exception as ne:
                logger.warning(f"邮件通知异常（不影响主流程）: {ne}")

            # ETL — 检查 5 张表是否全部就绪（不管当前任务是否成功）
            if skip_etl:
                logger.info("跳过 ETL（由 run-all 统一触发）")
            else:
                from pathlib import Path
                from app.services.etl_service import run_etl

                # 扫描下载目录，收集所有可用文件
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
                                    logger.info(f"ETL 收集(RPA): {f.name} → {key}")
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

                # 检查 5 张表是否全部就绪
                missing = REQUIRED_KEYS - set(raw_data.keys())
                if missing:
                    logger.info(f"ETL 等待中，缺少: {missing} (已有: {set(raw_data.keys())})")
                else:
                    logger.info("5 张表全部就绪，开始 ETL")
                    etl_log_id = _create_log_task(db, "ETL 数据导入", task_id)
                    etl_start = datetime.now()
                    try:
                        run_etl(raw_data, db)
                        rows = sum(len(v) for v in raw_data.values())
                        etl_duration = int((datetime.now() - etl_start).total_seconds())
                        _update_etl_log(db, etl_log_id, "success", etl_duration,
                                        detail=f"导入 {rows} 条记录")
                        logger.info(f"ETL 完成: {rows} 条, 耗时 {etl_duration}s")
                    except Exception as e:
                        etl_duration = int((datetime.now() - etl_start).total_seconds())
                        _update_etl_log(db, etl_log_id, "failed", etl_duration,
                                        detail=str(e)[:500])
                        logger.error(f"ETL 执行失败: {e}", exc_info=True)

            # 清理旧文件
            keep_days = int(_cfg(db, "rpa_keep_days", "7"))
            cleanup_old_downloads(download_dir, keep_days)

        logger.info(f"Worker 完成, task_id={task_id}, success={success}")
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Worker 异常: {e}", exc_info=True)
        try:
            from app.database import get_db_context
            with get_db_context() as db:
                _fail(db, task_id, str(e), error_type="runtime")
        except Exception:
            pass
        sys.exit(1)


def _safe_read_excel(path: str) -> "pd.DataFrame":
    """读取 Excel，自动处理ERP exported文件的 openpyxl 样式兼容问题"""
    import pandas as pd
    try:
        return pd.read_excel(path)
    except (TypeError, Exception) as e:
        if "name should be" in str(e) or "_NamedCellStyle" in str(e):
            logger.warning(f"openpyxl 样式错误，使用兼容模式读取: {path}")
            # 临时修补 openpyxl 的 _NamedCellStyle 以接受 None name
            from openpyxl.styles import named_styles as ns
            orig_init = ns._NamedCellStyle.__init__
            def patched_init(self, name=None, **kw):
                if name is None:
                    name = "Normal"
                orig_init(self, name=name, **kw)
            ns._NamedCellStyle.__init__ = patched_init
            try:
                return pd.read_excel(path)
            finally:
                ns._NamedCellStyle.__init__ = orig_init
        raise


def _cfg(db, key, default=""):
    from sqlalchemy import text
    row = db.execute(text("SELECT config_value FROM sys_config WHERE config_key=:key"), {"key": key}).fetchone()
    return row[0] if row and row[0] else default


def _create_log(db, task_id):
    from sqlalchemy import text
    db.execute(text(
        "INSERT INTO rpa_logs (task_id, status, started_at) VALUES (:task_id, 'running', NOW())"
    ), {"task_id": task_id})
    db.commit()
    return db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]


def _create_module_log(db, task_id, module_name):
    """为单个模块创建 running 状态的日志记录"""
    from sqlalchemy import text
    db.execute(text(
        "INSERT INTO rpa_logs (task_id, task_name, status, started_at) "
        "VALUES (:task_id, :name, 'running', NOW())"
    ), {"task_id": task_id, "name": module_name})
    db.commit()
    return db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]


def _create_log_task(db, task_name: str, trigger_task_id: int = 0):
    """创建独立日志记录（如 ETL），task_id=0 表示无关联采集任务"""
    from sqlalchemy import text
    db.execute(text(
        "INSERT INTO rpa_logs (task_id, task_name, status, started_at) VALUES (0, :name, 'running', NOW())"
    ), {"name": task_name})
    db.commit()
    return db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]


def _update_etl_log(db, log_id: int, status: str, duration: int, detail: str = None):
    """更新 ETL 日志记录"""
    from sqlalchemy import text
    db.execute(text("""
        UPDATE rpa_logs SET status=:status, finished_at=NOW(),
        duration_sec=:duration, error_msg=:detail
        WHERE id=:id
    """), {"status": status, "duration": duration, "detail": detail, "id": log_id})
    db.commit()


def _update_log(db, log_id, status, file_path=None, error_msg=None):
    from sqlalchemy import text
    db.execute(text("""
        UPDATE rpa_logs SET status=:status, finished_at=NOW(),
        duration_sec=TIMESTAMPDIFF(SECOND, started_at, NOW()),
        file_path=:file_path, error_msg=:error_msg
        WHERE id=:id
    """), {"status": status, "file_path": file_path, "error_msg": error_msg, "id": log_id})
    db.commit()


def _fail(db, task_id, msg, error_type="runtime"):
    from sqlalchemy import text
    db.execute(text("""
        UPDATE rpa_logs SET status='failed', finished_at=NOW(),
        duration_sec=TIMESTAMPDIFF(SECOND, started_at, NOW()),
        error_msg=:msg, error_type=:et
        WHERE task_id=:tid AND status='running'
    """), {"msg": msg, "et": error_type, "tid": task_id})
    db.commit()


if __name__ == "__main__":
    main()
