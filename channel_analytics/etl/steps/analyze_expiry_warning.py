"""Pipeline 步骤 3 — RPT 1:物料+批次效期告警表(物料+批次聚类)。

对应原仓 etl_service.analyze_expiry_warning (L484-513)。

输入:
  - ctx.stg['stg_stock_current']   (material_code / material_name / batch_no / expiry_date / available_qty)
  - ctx.stg['stg_sales_out']       (material_code / batch_no / doc_date / sales_out_qty)
  - ctx.meta['brand_provider']     BrandWhitelistProvider
  - ctx.meta['rules']              BusinessRules
  - ctx.meta['current_date']       date(必填,无则用 date.today())

输出:
  - ctx.rpt['rpt_expiry_warning']  12 列

新仓行为差异:
  - brand 白名单从 brand_provider.get_brands() 判,不再依赖 material_brand_mapping 入参
  - current_date 走 ctx.meta['current_date'](原仓 ETLConfig.CURRENT_DATE 模块全局)
  - sales_90d 周期走 rules.turnover_cycle_days(原仓硬编码 90)
  - 缺失列时安全降级(返回空 DataFrame)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import ClassVar

import pandas as pd

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.cleaning import clean_batch_number
from channel_analytics.etl.expiry import calculate_expiry_months, classify_expiry_status
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.turnover import calculate_inventory_days
from channel_analytics.etl.types import EtlContext, Transformer


_STOCK_CURRENT = "stg_stock_current"
_SALES_OUT = "stg_sales_out"
_RPT_NAME = "rpt_expiry_warning"

_OUTPUT_COLS: tuple[str, ...] = (
    "material_code", "material_name", "brand", "brand_class",
    "batch_no", "expiry_date",
    "material_batch_available_qty", "sales_90d", "inventory_days",
    "remaining_expiry_months", "expiry_status", "expiry_warning",
)


def _classify_brand(brand: str, provider: BrandWhitelistProvider) -> str:
    if provider.is_self_operated(brand):
        return "自营"
    return "非自营"


class AnalyzeExpiryWarningStep(Transformer):
    """RPT 1 — 物料+批次效期告警。"""
    name: ClassVar[str] = "analyze_expiry_warning"

    def run(self, ctx: EtlContext) -> EtlContext:
        stock = ctx.stg.get(_STOCK_CURRENT)
        if stock is None or stock.empty:
            return ctx
        sales = ctx.stg.get(_SALES_OUT)
        if sales is None:
            sales = ctx.raw_data.get(_SALES_OUT)
        if sales is None or sales.empty:
            return ctx

        required_stock = {"material_code", "material_name", "batch_no", "expiry_date", "available_qty"}
        if not required_stock.issubset(stock.columns):
            return ctx

        rules: BusinessRules = ctx.meta.get("rules") or BusinessRules.defaults()
        provider: BrandWhitelistProvider = (
            ctx.meta.get("brand_provider") or BrandWhitelistProvider.__new__(BrandWhitelistProvider)
        )
        cd: date = ctx.meta.get("current_date") or date.today()

        # 1. 物料+批次聚类
        agg = stock.groupby(
            ["material_code", "material_name", "batch_no", "expiry_date"],
            as_index=False,
        ).agg(material_batch_available_qty=("available_qty", "sum"))

        # 2. brand 分类 — 走 provider,缺列时 brand 留空
        if "brand" in stock.columns:
            brand_map = stock[["material_code", "brand"]].drop_duplicates("material_code")
            agg = agg.merge(brand_map, on="material_code", how="left")
        else:
            agg["brand"] = ""
        agg["brand"] = agg["brand"].fillna("未知brand").replace("", "未知brand")
        agg["brand_class"] = agg["brand"].apply(lambda b: _classify_brand(b, provider))

        # 3. 90 天销售(用 rules.turnover_cycle_days)
        sc = sales.dropna(subset=["doc_date", "batch_no", "material_code"]).copy()
        sc["batch_no"] = sc["batch_no"].map(clean_batch_number)
        sc = sc.dropna(subset=["batch_no"])
        sc["doc_date"] = pd.to_datetime(sc["doc_date"], errors="coerce")
        threshold = pd.Timestamp(cd - timedelta(days=rules.turnover_cycle_days))
        r90 = sc[sc["doc_date"] >= threshold]
        bs = r90.groupby(["material_code", "batch_no"], as_index=False).agg(
            sales_90d=("sales_out_qty", "sum"),
        )
        bs["sales_90d"] = pd.to_numeric(bs["sales_90d"], errors="coerce").fillna(0.0)

        agg = agg.merge(bs, on=["material_code", "batch_no"], how="left")
        agg["sales_90d"] = agg["sales_90d"].fillna(0.0)

        # 4. 指标计算
        agg["inventory_days"] = agg.apply(
            lambda r: calculate_inventory_days(
                r["material_batch_available_qty"], r["sales_90d"], rules
            ),
            axis=1,
        )
        agg["remaining_expiry_months"] = agg["expiry_date"].map(
            lambda d: calculate_expiry_months(d, cd)
        )
        agg["expiry_status"] = agg["remaining_expiry_months"].map(
            lambda m: classify_expiry_status(m)
        )
        agg["expiry_warning"] = agg["remaining_expiry_months"].map(
            lambda m: "预警" if (pd.notna(m) and m < 24) else "正常"
        )

        # 5. 类型规整
        for c in ("material_batch_available_qty", "sales_90d"):
            agg[c] = agg[c].fillna(0).astype(int)
        agg["inventory_days"] = agg["inventory_days"].fillna(0).round(0).astype(int)

        out = agg[list(_OUTPUT_COLS)].sort_values(["material_code", "batch_no"]).reset_index(drop=True)
        ctx.rpt[_RPT_NAME] = out
        return ctx
