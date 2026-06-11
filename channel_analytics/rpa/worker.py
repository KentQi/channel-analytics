"""RPA Worker — 独立子进程入口。

用途:
  - 完全隔离 Playwright 与 FastAPI 的事件循环
  - 通过 `python -m channel_analytics.rpa.worker <task_id>` 启动
  - 进入时清理同 task_id 遗留的 running 僵尸记录(对齐原仓 rpa_worker.py)

入口函数 main() 是 CLI 启动点。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime

from channel_analytics.rpa.runner import RpaRunner, RpaRunnerConfig
from channel_analytics.rpa.scheduler import RpaLog, RpaScheduler, RpaTask


logger = logging.getLogger("rpa_worker")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RPA Worker — 独立子进程入口")
    p.add_argument("--task-id", type=int, required=True, help="RPA task ID")
    p.add_argument("--module", type=str, default=None, help="指定单一模块(可选)")
    p.add_argument("--skip-etl", action="store_true", help="完成后不触发 ETL")
    p.add_argument(
        "--adapter",
        type=str,
        default=os.environ.get("RPA_ADAPTER", ""),
        help="ErpAdapter 路径(module:Class)",
    )
    p.add_argument("--log-file", type=str, default=None, help="日志文件路径")
    return p.parse_args(argv)


def _load_adapter(dotted: str):
    """按 `module:Class` 加载 ErpAdapter。"""
    import importlib
    mod_path, class_name = dotted.split(":", 1)
    module = importlib.import_module(mod_path)
    cls = getattr(module, class_name)
    if not isinstance(cls, type):
        raise TypeError(f"{dotted} 不是类")
    from channel_analytics.rpa.base import ErpAdapter
    if not issubclass(cls, ErpAdapter):
        raise TypeError(f"{class_name} 必须继承 ErpAdapter")
    return cls()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    # 日志配置
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=handlers,
    )

    logger.info("Worker 进程启动 task_id=%d", args.task_id)

    # adapter 加载
    if not args.adapter:
        logger.error("未指定 --adapter(或环境变量 RPA_ADAPTER)")
        return 1
    try:
        adapter = _load_adapter(args.adapter)
    except Exception as e:
        logger.exception("adapter 加载失败: %s", e)
        return 2

    # 任务构造(部署期应从 DB 读;此处保持最小骨架)
    task = RpaTask(
        id=args.task_id,
        name=f"task_{args.task_id}",
        module_names=[args.module] if args.module else [],
    )

    scheduler = RpaScheduler()
    scheduler.cleanup_stale_running(storage=None)
    log = scheduler.mark_start(task)

    # 凭据从环境变量读(部署期由 orchestrator 注入)
    url = os.environ.get("RPA_TARGET_URL", "")
    username = os.environ.get("RPA_USERNAME", "")
    password = os.environ.get("RPA_PASSWORD", "")
    if not username or not password:
        logger.error("RPA 凭据未配置(RPA_USERNAME / RPA_PASSWORD)")
        log.status = "failed"
        log.error_type = "config"
        log.error_msg = "RPA 凭据未配置"
        log.finished_at = datetime.utcnow()
        return 1

    config = RpaRunnerConfig(
        download_dir=os.environ.get("RPA_DOWNLOAD_DIR", "./data/rpa_downloads"),
        headless=os.environ.get("RPA_HEADLESS", "true").lower() == "true",
        slow_mo_ms=int(os.environ.get("RPA_SLOW_MO_MS", "300")),
        timeout_multiplier=float(os.environ.get("RPA_TIMEOUT_MULTIPLIER", "1.0")),
    )
    runner = RpaRunner(adapter=adapter, config=config)

    try:
        asyncio.run(_run(runner, task, url, username, password, log, scheduler, args))
    except Exception as e:
        logger.exception("Worker 顶层异常: %s", e)
        log.status = "failed"
        log.error_msg = str(e)
        log.error_type = "unknown"
        log.finished_at = datetime.utcnow()
        return 1
    return 0 if log.status == "success" else 1


async def _run(
    runner: RpaRunner,
    task: RpaTask,
    url: str,
    username: str,
    password: str,
    log: RpaLog,
    scheduler: RpaScheduler,
    args: argparse.Namespace,
) -> None:
    """异步执行 runner,完成后回写 log。"""
    await runner.start()
    try:
        results = await runner.run_all(
            task.module_names or [""],
            url=url, username=username, password=password,
        )
        scheduler.mark_done(log, results)
    finally:
        await runner.close()
    logger.info(
        "Worker 结束 status=%s task_id=%d",
        log.status, task.id,
    )


if __name__ == "__main__":
    sys.exit(main())