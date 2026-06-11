"""Pipeline 步骤 1 — 5 张 STG 表字段清洗。

对 raw_data 中的 5 张 STG 表的已知列跑 clean_* 函数:
  - batch_number / production_batch / batch → clean_batch_number
  - expiry_date / expiry / 效期             → clean_expiry_date
  - material_code / material / 物料编码     → clean_material_code

只对**存在**的列做清洗;不存在的列跳过(防御列名差异)。
结果写入 ctx.stg(不修改 raw_data)。
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.cleaning import (
    clean_batch_number,
    clean_expiry_date,
    clean_material_code,
)
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.types import EtlContext, Transformer


STG_TABLES: tuple[str, ...] = (
    "stg_purchase_req",
    "stg_purchase_order",
    "stg_stock_in",
    "stg_sales_out",
    "stg_stock_current",
)

_BATCH_COLS: tuple[str, ...] = ("batch_number", "production_batch", "batch")
_EXPIRY_COLS: tuple[str, ...] = ("expiry_date", "expiry", "效期")
_MATERIAL_COLS: tuple[str, ...] = ("material_code", "material", "物料编码")


class CleanStgFieldsStep(Transformer):
    """STG 字段清洗(纯函数,无 DB 依赖)。"""
    name: ClassVar[str] = "clean_stg_fields"

    def run(self, ctx: EtlContext) -> EtlContext:
        rules: BusinessRules = ctx.meta.get("rules") or BusinessRules.defaults()
        for table in STG_TABLES:
            df = ctx.raw_data.get(table)
            if df is None or df.empty:
                continue
            df = df.copy()
            for col in _BATCH_COLS:
                if col in df.columns:
                    df[col] = df[col].map(lambda v: clean_batch_number(v, rules))
            for col in _EXPIRY_COLS:
                if col in df.columns:
                    df[col] = df[col].map(lambda v: clean_expiry_date(v, rules))
            for col in _MATERIAL_COLS:
                if col in df.columns:
                    df[col] = df[col].map(clean_material_code)
            ctx.stg[table] = df
        return ctx
