"""Pipeline 步骤 7 — RPT 5:物料维度趋势告警。

对应原仓 etl_service.analyze_trend_warning (L565-595)。

输入:
  - ctx.stg['stg_stock_current']   (material_code / material_name / available_qty / brand)
  - ctx.stg['stg_sales_out']       (material_code / doc_date / sales_out_qty)

输出:
  - ctx.rpt['rpt_trend_warning']   15 列

新仓行为:
  - 4 段窗口走 rules.trend_cycle_days
  - 分类阈值走 rules.trend.{ratio_threshold, min_change}
  - brand 分类走 brand_provider(原仓传 material_brand_mapping)
"""
from __future__ import annotations

from datetime import date
from typing import ClassVar

import pandas as pd

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.trend import (
    classify_trend_status,
    get_material_sales_trend,
    is_trend_warning,
)
from channel_analytics.etl.types import EtlContext, Transformer


_STOCK_CURRENT = "stg_stock_current"
_SALES_OUT = "stg_sales_out"
_RPT_OUTPUT = "rpt_trend_warning"

_OUTPUT_COLS: tuple[str, ...] = (
    "material_code", "material_name", "brand", "brand_class",
    "material_available_qty",
    "cycle_4_sales", "cycle_3_sales", "cycle_2_sales", "cycle_1_sales",
    "total_dispatch_90d", "total_return_qty", "sales_90d",
    "return_ratio", "trend_status", "trend_warning",
)


def _classify_brand(brand: str, provider: BrandWhitelistProvider) -> str:
    if provider.is_self_operated(brand):
        return "自营"
    return "非自营"


class AnalyzeTrendWarningStep(Transformer):
    """RPT 5 — 物料维度趋势告警。"""
    name: ClassVar[str] = "analyze_trend_warning"

    def run(self, ctx: EtlContext) -> EtlContext:
        stock = ctx.stg.get(_STOCK_CURRENT)
        if stock is None or stock.empty:
            return ctx
        sales = ctx.stg.get(_SALES_OUT)
        if sales is None:
            sales = ctx.raw_data.get(_SALES_OUT)
        if sales is None or sales.empty:
            return ctx

        required = {"material_code", "material_name", "available_qty"}
        if not required.issubset(stock.columns):
            return ctx

        rules: BusinessRules = ctx.meta.get("rules") or BusinessRules.defaults()
        provider: BrandWhitelistProvider = ctx.meta.get("brand_provider")
        cd: date = ctx.meta.get("current_date") or date.today()

        # 1. 物料维度聚类
        ms = stock.groupby(["material_code", "material_name"], as_index=False)["available_qty"].sum()
        ms.columns = ["material_code", "material_name", "material_available_qty"]

        # 2. brand 映射
        if "brand" in stock.columns:
            brand_map = stock[["material_code", "brand"]].drop_duplicates("material_code")
            ms = ms.merge(brand_map, on="material_code", how="left")
        else:
            ms["brand"] = ""
        ms["brand"] = ms["brand"].fillna("未知brand").replace("", "未知brand")
        ms["brand_class"] = ms["brand"].apply(lambda b: _classify_brand(b, provider))

        # 3. 每物料跑 trend + classify
        results: list[dict] = []
        for _, row in ms.iterrows():
            mat = row["material_code"]
            trend = get_material_sales_trend(sales, mat, cd, rules)
            ts, rr, c3, c2, c1 = classify_trend_status(
                list(trend), float(row["material_available_qty"]), rules
            )
            tw = is_trend_warning(ts)
            results.append({
                "material_code": mat,
                "material_name": row["material_name"],
                "brand": row["brand"],
                "brand_class": row["brand_class"],
                "material_available_qty": int(row["material_available_qty"]),
                "cycle_4_sales": trend[0],
                "cycle_3_sales": trend[1],
                "cycle_2_sales": trend[2],
                "cycle_1_sales": trend[3],
                "total_dispatch_90d": trend[4],
                "total_return_qty": trend[5],
                "sales_90d": trend[6],
                "return_ratio": rr,
                "trend_status": ts,
                "trend_warning": tw,
            })

        df = pd.DataFrame(results)
        for c in ("material_available_qty", "cycle_4_sales", "cycle_3_sales", "cycle_2_sales",
                  "cycle_1_sales", "total_dispatch_90d", "total_return_qty", "sales_90d"):
            df[c] = df[c].fillna(0).astype(int)
        df["return_ratio"] = df["return_ratio"].astype(float).apply(lambda x: f"{x*100:.1f}%")

        out = df[list(_OUTPUT_COLS)].sort_values("material_code").reset_index(drop=True)
        ctx.rpt[_RPT_OUTPUT] = out
        return ctx