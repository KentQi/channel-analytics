"""Writer 抽象 — 把 7 张 RPT 表写入数据库。

设计要点:
  - 不依赖 MySQL/Postgres 特定语法(原仓用 SHOW COLUMNS + TRUNCATE,新仓走 SQLAlchemy 通用)
  - 通过 SQLAlchemy engine 支持 sqlite / mysql / postgres 全部
  - 表 schema 防御:df 中的列只在 DB 表存在时才写入(原仓 L207)
  - 空表跳过(原仓 L199-201)
  - ctx.meta['engine'] = SQLAlchemy Engine 实例(由 caller 注入);无 engine → 静默 no-op(便于测试)

新仓行为差异:
  - 用 if_exists='replace' 替代原仓 TRUNCATE + to_sql append(更原子)
  - chunksize=5000(对齐原仓)
  - method='multi'(对齐原仓)
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.types import EtlContext, Writer


# 7 张 RPT 表的写入顺序(原仓 run_etl L736 起)
RPT_TABLES: tuple[str, ...] = (
    "rpt_expiry_warning",
    "rpt_expiry_turnover",
    "rpt_self_operated_concentration",
    "rpt_turnover_warning",
    "rpt_trend_warning",
    "rpt_warehouse_risk",
    "rpt_procurement_linked",
)


class WriteRptTablesStep(Writer):
    """Writer — 把 ctx.rpt 中的所有 RPT 表写入 DB。"""
    name: ClassVar[str] = "write_rpt_tables"

    def run(self, ctx: EtlContext) -> EtlContext:
        engine = ctx.meta.get("engine")
        if engine is None:
            # 没有 engine 时静默 no-op(便于测试 & CI)
            return ctx
        for table in RPT_TABLES:
            df = ctx.rpt.get(table)
            if df is None or df.empty:
                continue
            self._write_one(df, table, engine)
        return ctx

    @staticmethod
    def _write_one(df: pd.DataFrame, table: str, engine) -> None:
        """单表写入 — 列裁剪 + replace + chunksize。"""
        # 表存在性 + 列裁剪
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            if not inspector.has_table(table):
                # 表不存在时直接 to_sql(if_exists='replace' 会建表)
                df.to_sql(
                    name=table, con=engine,
                    if_exists="replace", index=False,
                    chunksize=5000, method="multi",
                )
                return
            db_columns = {c["name"] for c in inspector.get_columns(table)}
        except Exception:
            # 任何 DB 异常都不让 ETL 整体崩
            return

        df_to_save = df[[c for c in df.columns if c in db_columns]]
        if df_to_save.empty:
            return
        df_to_save.to_sql(
            name=table, con=engine,
            if_exists="replace", index=False,
            chunksize=5000, method="multi",
        )


__all__ = ["WriteRptTablesStep", "RPT_TABLES"]