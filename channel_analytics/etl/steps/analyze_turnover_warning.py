"""Pipeline 步骤 6 — RPT 4:物料维度周转告警。

对应原仓 etl_service.analyze_turnover_warning (L542-562)。

输入:
  - ctx.stg['stg_stock_current']   (material_code / material_name / available_qty / brand)
  - ctx.stg['stg_sales_out']       (material_code / doc_date / sales_out_qty)

输出:
  - ctx.rpt['rpt_turnover_warning']  9 列

新仓行为差异:
  - 销售窗口走 rules.turnover_cycle_days(原仓硬编码 90)
  - 告警阈值走 rules.turnover_warning_{low,high}(原仓硬编码 15 / 60)
  - brand 分类走 brand_provider(原仓传 material_brand_mapping)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import ClassVar

import pandas as pd

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.turnover import (
    calculate_inventory_days,
    classify_turnover_status,
)
from channel_analytics.etl.types import EtlContext, Transformer


_STOCK_CURRENT = "stg_stock_current"
_SALES_OUT = "stg_sales_out"
_RPT_OUTPUT = "rpt_turnover_warning"

_OUTPUT_COLS: tuple[str, ...] = (
    "material_code", "material_name", "brand", "brand_class",
    "material_available_qty", "sales_90d", "inventory_days",
    "turnover_status", "turnover_warning",
)


def _classify_brand(brand: str, provider: BrandWhitelistProvider) -> str:
    if provider.is_self_operated(brand):
        return "自营"
    return "非自营"


class AnalyzeTurnoverWarningStep(Transformer):
    """RPT 4 — 物料维度周转告警。"""
    name: ClassVar[str] = "analyze_turnover_warning"

    def run(self, ctx: EtlContext) -> EtlContext:
        stock = ctx.stg.get(_STOCK_CURRENT)
        if stock is None or stock.empty:
            return ctx
        sales = ctx.stg.get(_SALES_OUT)
        if sales is None:
            sales = ctx.raw_data.get(_SALES_OUT)
        if sales is None or sales.empty:
            return ctx

        # 防御: 关键列缺失则跳过
        required = {"material_code", "material_name", "available_qty"}
        if not required.issubset(stock.columns):
            return ctx

        rules: BusinessRules = ctx.meta.get("rules") or BusinessRules.defaults()
        provider: BrandWhitelistProvider = ctx.meta.get("brand_provider")
        cd: date = ctx.meta.get("current_date") or date.today()

        # 1. 物料维度聚类
        ms = stock.groupby(["material_code", "material_name"], as_index=False)["available_qty"].sum()
        ms.columns = ["material_code", "material_name", "material_available_qty"]

        # 2. 90 天销售
        sc = sales.dropna(subset=["doc_date"]).copy()
        sc["doc_date"] = pd.to_datetime(sc["doc_date"], errors="coerce")
        threshold = pd.Timestamp(cd - timedelta(days=rules.turnover_cycle_days))
        r90 = sc[sc["doc_date"] >= threshold]
        msl = r90.groupby("material_code", as_index=False)["sales_out_qty"].sum()
        msl.columns = ["material_code", "sales_90d"]

        df = ms.merge(msl, on="material_code", how="left").fillna({"sales_90d": 0})

        # 3. brand 映射(走 provider,无列时 brand 留空)
        if "brand" in stock.columns:
            brand_map = stock[["material_code", "brand"]].drop_duplicates("material_code")
            df = df.merge(brand_map, on="material_code", how="left")
        else:
            df["brand"] = ""
        df["brand"] = df["brand"].fillna("未知brand").replace("", "未知brand")
        df["brand_class"] = df["brand"].apply(lambda b: _classify_brand(b, provider))

        # 4. 指标
        df["inventory_days"] = df.apply(
            lambda r: calculate_inventory_days(
                r["material_available_qty"], r["sales_90d"], rules
            ),
            axis=1,
        )
        df["turnover_status"] = df["inventory_days"].map(
            lambda d: classify_turnover_status(d, rules)
        )
        # 告警:不在 [low, high] 区间内
        low = rules.turnover_warning_low
        high = rules.turnover_warning_high
        df["turnover_warning"] = df["inventory_days"].map(
            lambda d: "预警" if (pd.notna(d) and (d < low or d > high)) else "正常"
        )

        # 5. 类型规整
        for c in ("material_available_qty", "sales_90d"):
            df[c] = df[c].fillna(0).astype(int)
        df["inventory_days"] = df["inventory_days"].fillna(0).round(0).astype(int)

        out = df[list(_OUTPUT_COLS)].sort_values("material_code").reset_index(drop=True)
        ctx.rpt[_RPT_OUTPUT] = out
        return ctx
