"""Pipeline 步骤 8 — RPT 6:物料×warehouse 综合风险表。

对应原仓 etl_service.analyze_material_warehouse_risk (L598-616)。

输入:
  - ctx.stg['stg_stock_current']   (warehouse / material_code / material_name)
  - ctx.rpt['rpt_expiry_warning']  (RPT 1)
  - ctx.rpt['rpt_turnover_warning'] (RPT 4)
  - ctx.rpt['rpt_trend_warning']    (RPT 5)

输出:
  - ctx.rpt['rpt_warehouse_risk']   13 列

新仓行为:
  - brand 分类走 brand_provider(原仓传 material_brand_mapping)
  - 风险等级 = "高风险"(≥2 预警) / "中风险"(=1) / "低风险"(0)
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.types import EtlContext, Transformer


_STOCK_CURRENT = "stg_stock_current"
_EXPIRY = "rpt_expiry_warning"
_TURNOVER = "rpt_turnover_warning"
_TREND = "rpt_trend_warning"
_OUTPUT = "rpt_warehouse_risk"

_OUTPUT_COLS: tuple[str, ...] = (
    "warehouse", "material_code", "material_name", "brand", "brand_class",
    "material_available_qty",
    "expiry_warning_status", "inventory_days", "turnover_warning", "return_ratio",
    "trend_status", "trend_warning", "risk_level",
)


def _classify_brand(brand: str, provider: BrandWhitelistProvider) -> str:
    if provider.is_self_operated(brand):
        return "自营"
    return "非自营"


def _risk_level(row: pd.Series) -> str:
    cnt = sum(
        1
        for k in ("expiry_warning_status", "turnover_warning", "trend_warning")
        if row.get(k) == "预警"
    )
    if cnt >= 2:
        return "高风险"
    if cnt == 1:
        return "中风险"
    return "低风险"


class AnalyzeMaterialWarehouseRiskStep(Transformer):
    """RPT 6 — 物料×warehouse 综合风险。"""
    name: ClassVar[str] = "analyze_material_warehouse_risk"

    def run(self, ctx: EtlContext) -> EtlContext:
        stock = ctx.stg.get(_STOCK_CURRENT)
        if stock is None or stock.empty:
            return ctx
        required = {"warehouse", "material_code", "material_name"}
        if not required.issubset(stock.columns):
            return ctx

        provider: BrandWhitelistProvider = ctx.meta.get("brand_provider")

        df_wh = stock[["warehouse", "material_code", "material_name"]].drop_duplicates()
        # brand 映射(走 provider,缺列时 brand 留空)
        if "brand" in stock.columns:
            brand_map = stock[["material_code", "brand"]].drop_duplicates("material_code")
            df_wh = df_wh.merge(brand_map, on="material_code", how="left")
        else:
            df_wh["brand"] = ""
        df_wh["brand"] = df_wh["brand"].fillna("未知brand").replace("", "未知brand")
        df_wh["brand_class"] = df_wh["brand"].apply(lambda b: _classify_brand(b, provider))

        # RPT 1 聚合:material_code → expiry_warning_status
        expiry = ctx.rpt.get(_EXPIRY)
        if expiry is not None and not expiry.empty:
            me = expiry.groupby("material_code", as_index=False)["expiry_warning"].agg(
                expiry_warning_status=lambda x: "预警" if (x == "预警").any() else "正常",
            )
            df_wh = df_wh.merge(me, on="material_code", how="left")
        else:
            df_wh["expiry_warning_status"] = "正常"

        # RPT 4:material_code → turnover_warning / inventory_days / material_available_qty
        turnover = ctx.rpt.get(_TURNOVER)
        if turnover is not None and not turnover.empty:
            cols = [c for c in ("material_code", "turnover_warning", "inventory_days", "material_available_qty")
                    if c in turnover.columns]
            df_wh = df_wh.merge(turnover[cols], on="material_code", how="left")

        # RPT 5:material_code → trend_warning / trend_status / return_ratio
        trend = ctx.rpt.get(_TREND)
        if trend is not None and not trend.empty:
            cols = [c for c in ("material_code", "trend_warning", "trend_status", "return_ratio")
                    if c in trend.columns]
            df_wh = df_wh.merge(trend[cols], on="material_code", how="left")

        # 兜底: 列不存在时填默认;存在时只 fillna 缺值
        for c, default in (
            ("material_available_qty", 0),
            ("inventory_days", 0),
            ("turnover_warning", "正常"),
            ("trend_warning", "正常"),
            ("trend_status", "无明显趋势"),
            ("return_ratio", "0.0%"),
        ):
            if c not in df_wh.columns:
                df_wh[c] = default
            elif c in ("material_available_qty", "inventory_days"):
                df_wh[c] = df_wh[c].fillna(default).astype(int)
            else:
                df_wh[c] = df_wh[c].fillna(default)

        df_wh["risk_level"] = df_wh.apply(_risk_level, axis=1)
        out = df_wh[list(_OUTPUT_COLS)].sort_values(["warehouse", "material_code"]).reset_index(drop=True)
        ctx.rpt[_OUTPUT] = out
        return ctx