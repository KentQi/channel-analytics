"""channel_analytics.cli — 入口命令

子命令:
  init-secrets    生成 .env 里的占位 secret
  check-config    校验配置(无占位符 + DB 可连)
  run-etl         跑 ETL 管道
  run-rpa         跑 RPA 流程

使用:
  channel-analytics init-secrets
  channel-analytics check-config
  channel-analytics run-etl --pipeline stg_purchase_order
  channel-analytics run-rpa --module "stock_query" --start 2026-01-01 --end 2026-01-31
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence


def _cmd_init_secrets(_args: argparse.Namespace) -> int:
    from channel_analytics.config.secrets import init_secrets
    return 0 if init_secrets() >= 0 else 1


def _cmd_check_config(_args: argparse.Namespace) -> int:
    from channel_analytics.config import RefuseToStart, get_settings
    try:
        settings = get_settings()
    except RefuseToStart as e:
        print(f"REFUSE TO START: {e}", file=sys.stderr)
        return 1
    print(f"OK: env={settings.app_env} db={settings.database_url!r} adapter={settings.rpa_adapter}")
    return 0


def _cmd_run_etl(args: argparse.Namespace) -> int:
    print(f"run-etl pipeline={args.pipeline} (TODO: W3 接入 etl.pipeline)", file=sys.stderr)
    return 0


def _cmd_run_rpa(args: argparse.Namespace) -> int:
    print(
        f"run-rpa module={args.module} start={args.start} end={args.end} "
        f"(TODO: W3 接入 rpa.runner)",
        file=sys.stderr,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="channel-analytics",
        description="通用渠道分析平台 CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s1 = sub.add_parser("init-secrets", help="生成 .env 里的占位 secret")
    s1.set_defaults(func=_cmd_init_secrets)

    s2 = sub.add_parser("check-config", help="校验配置(无占位符 + DB 可连)")
    s2.set_defaults(func=_cmd_check_config)

    s3 = sub.add_parser("run-etl", help="跑 ETL 管道")
    s3.add_argument("--pipeline", default="all", help="管道名,默认 all")
    s3.set_defaults(func=_cmd_run_etl)

    s4 = sub.add_parser("run-rpa", help="跑 RPA 流程")
    s4.add_argument("--module", required=True, help="业务模块名(adapter 决定含义)")
    s4.add_argument("--start", required=True, help="起始日期 YYYY-MM-DD")
    s4.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")
    s4.set_defaults(func=_cmd_run_rpa)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
