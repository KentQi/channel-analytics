"""Pipeline 步骤 5 — RPT 3:自营品库存集中度分析。

对应原仓 etl_service.analyze_self_operated_stock_concentration (L526-539)。

输入:
  - ctx.rpt['rpt_expiry_warning']  (RPT 1 产物)

输出:
  - ctx.rpt['rpt_self_operated_concentration']  8 列

新仓行为:
  - 自营判定走 brand_class == "自营"(由 RPT 1 已聚合完成,无需 provider)
  - 无自营时返回空 DataFrame(对齐原仓 L529-530)
  - 字符串 % 后缀(原仓 L534: .astype(str) + "%")
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.types import EtlContext, Transformer


_RPT_INPUT = "rpt_expiry_warning"
_RPT_OUTPUT = "rpt_self_operated_concentration"

_OUTPUT_COLS: tuple[str, ...] = (
    "material_code", "material_name", "brand", "expiry_status",
    "material_batch_available_qty", "stock_ratio", "cumulative_stock_ratio", "sales_90d",
)

_EMPTY_COLS: tuple[str, ...] = _OUTPUT_COLS


class AnalyzeSelfOperatedConcentrationStep(Transformer):
    """RPT 3 — 自营品库存集中度。"""
    name: ClassVar[str] = "analyze_self_operated_stock_concentration"

    def run(self, ctx: EtlContext) -> EtlContext:
        df_in = ctx.rpt.get(_RPT_INPUT)
        if df_in is None or df_in.empty:
            ctx.rpt[_RPT_OUTPUT] = pd.DataFrame(columns=list(_EMPTY_COLS))
            return ctx

        df_self = df_in[df_in["brand_class"] == "自营"].copy()
        if df_self.empty:
            ctx.rpt[_RPT_OUTPUT] = pd.DataFrame(columns=list(_EMPTY_COLS))
            return ctx

        agg = df_self.groupby(
            ["material_code", "material_name", "brand", "expiry_status"],
            as_index=False,
        ).agg(
            material_batch_available_qty=("material_batch_available_qty", "sum"),
            sales_90d=("sales_90d", "sum"),
        )

        total = agg["material_batch_available_qty"].sum()
        if total <= 0:
            ctx.rpt[_RPT_OUTPUT] = pd.DataFrame(columns=list(_EMPTY_COLS))
            return ctx

        agg["stock_ratio"] = (agg["material_batch_available_qty"] / total * 100).round(1).astype(str) + "%"
        agg = agg.sort_values("material_batch_available_qty", ascending=False).reset_index(drop=True)
        agg["cumulative_available_qty"] = agg["material_batch_available_qty"].cumsum()
        agg["cumulative_stock_ratio"] = (agg["cumulative_available_qty"] / total * 100).round(1).astype(str) + "%"

        out = agg[list(_OUTPUT_COLS)].reset_index(drop=True)
        ctx.rpt[_RPT_OUTPUT] = out
        return ctx
