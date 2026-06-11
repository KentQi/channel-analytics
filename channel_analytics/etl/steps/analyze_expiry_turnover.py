"""Pipeline 步骤 4 — RPT 2:效期-周转关联表(brand_class × expiry_status 聚合)。

对应原仓 etl_service.analyze_expiry_turnover (L516-523)。

输入:
  - ctx.rpt['rpt_expiry_warning']  (上一步产物)

输出:
  - ctx.rpt['rpt_expiry_turnover']  6 列

新仓行为差异:
  - turnover_days 计算走 rules.turnover_cycle_days(原仓硬编码 90)
  - 缺输入时安全降级(返回空 DataFrame)
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.types import EtlContext, Transformer
from channel_analytics.etl.utils import safe_divide


_RPT_INPUT = "rpt_expiry_warning"
_RPT_OUTPUT = "rpt_expiry_turnover"

_OUTPUT_COLS: tuple[str, ...] = (
    "brand_class", "expiry_status",
    "available_qty", "sales_90d", "turnover_days",
)


class AnalyzeExpiryTurnoverStep(Transformer):
    """RPT 2 — 效期 × 周转关联表。"""
    name: ClassVar[str] = "analyze_expiry_turnover"

    def run(self, ctx: EtlContext) -> EtlContext:
        df_in = ctx.rpt.get(_RPT_INPUT)
        if df_in is None or df_in.empty:
            return ctx

        rules: BusinessRules = ctx.meta.get("rules") or BusinessRules.defaults()
        cycle = rules.turnover_cycle_days

        agg = df_in.groupby(["brand_class", "expiry_status"], as_index=False).agg(
            available_qty=("material_batch_available_qty", "sum"),
            sales_90d=("sales_90d", "sum"),
        )
        # 原仓 L519: safe_divide(available_qty, sales_90d) * 90
        agg["turnover_days"] = agg.apply(
            lambda r: round(safe_divide(r["available_qty"], r["sales_90d"], 0) * cycle, 1),
            axis=1,
        )
        agg["available_qty"] = agg["available_qty"].astype(int)
        agg["sales_90d"] = agg["sales_90d"].astype(int)

        out = agg[list(_OUTPUT_COLS)].sort_values(
            ["brand_class", "expiry_status"]
        ).reset_index(drop=True)
        ctx.rpt[_RPT_OUTPUT] = out
        return ctx
