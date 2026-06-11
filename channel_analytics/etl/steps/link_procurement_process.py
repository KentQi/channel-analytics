"""Pipeline 步骤 9 — RPT 7:请购-采购-入库 三表关联。

对应原仓 etl_service.link_procurement_process (L619-656)。

输入:
  - ctx.stg['stg_purchase_req']  (请购单:order_no / material_code / order_qty / delivery_cycle / ...)
  - ctx.stg['stg_purchase_order'] (采购单:order_no / material_code / factory_delivery_qty / pickup_qty / delivery_date / brand_sales_no / ...)
  - ctx.stg['stg_stock_in']       (入库单:brand_sales_no / material_code / stock_in_qty / stock_in_date)

输出:
  - ctx.rpt['rpt_procurement_linked']  多列(原仓直接 return ri,不重命名 cols)

新仓行为:
  - 缺任何一张表时返回 ctx 不写 rpt(对齐原仓会抛 KeyError 的真实情况)
  - 数字列安全 NaN → 0
  - % 字符串 suffix("xx.x%")对齐原仓
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.types import EtlContext, Transformer
from channel_analytics.etl.utils import safe_divide


_REQ = "stg_purchase_req"
_ORDER = "stg_purchase_order"
_IN = "stg_stock_in"
_OUTPUT = "rpt_procurement_linked"


class LinkProcurementProcessStep(Transformer):
    """RPT 7 — 请购-采购-入库 三表关联。"""
    name: ClassVar[str] = "link_procurement_process"

    def run(self, ctx: EtlContext) -> EtlContext:
        req = ctx.stg.get(_REQ)
        if req is None:
            req = ctx.raw_data.get(_REQ)
        order = ctx.stg.get(_ORDER)
        if order is None:
            order = ctx.raw_data.get(_ORDER)
        stock_in = ctx.stg.get(_IN)
        if stock_in is None:
            stock_in = ctx.raw_data.get(_IN)
        if req is None or order is None or stock_in is None:
            return ctx
        if req.empty or order.empty or stock_in.empty:
            return ctx

        # 必要列缺失时跳过
        if "order_no" not in req.columns or "material_code" not in req.columns:
            return ctx

        # 1. 采购单聚合
        order_agg = order.groupby(["order_no", "material_code"], as_index=False).agg(
            cumulative_factory_delivery_qty=("factory_delivery_qty", "sum")
            if "factory_delivery_qty" in order.columns else ("order_no", "count"),
            cumulative_pickup_qty=("pickup_qty", "sum")
            if "pickup_qty" in order.columns else ("order_no", "count"),
            first_delivery_date=("delivery_date", "min")
            if "delivery_date" in order.columns else ("order_no", "min"),
            last_delivery_date=("delivery_date", "max")
            if "delivery_date" in order.columns else ("order_no", "max"),
        )
        for c in ("cumulative_factory_delivery_qty", "cumulative_pickup_qty"):
            order_agg[c] = pd.to_numeric(order_agg[c], errors="coerce").fillna(0.0)

        # 2. 入库单聚合
        if "stock_in_qty" in stock_in.columns:
            in_agg = stock_in.groupby(["brand_sales_no", "material_code"], as_index=False).agg(
                cumulative_stock_in_qty=("stock_in_qty", "sum"),
                first_stock_in_date=("stock_in_date", "min") if "stock_in_date" in stock_in.columns else ("brand_sales_no", "min"),
            )
        else:
            return ctx

        # 3. 三表 join
        ri = req.merge(order_agg, on=["order_no", "material_code"], how="left")
        # 补 brand_sales_no (从 order 表)
        if "brand_sales_no" in order.columns:
            ob = order[["order_no", "material_code", "brand_sales_no"]].drop_duplicates()
            ri = ri.merge(ob, on=["order_no", "material_code"], how="left")
        ri = ri.merge(in_agg, on=["brand_sales_no", "material_code"], how="left")

        ri["order_qty"] = pd.to_numeric(ri.get("order_qty"), errors="coerce").fillna(0.0)
        for c in ("cumulative_factory_delivery_qty", "cumulative_pickup_qty", "cumulative_stock_in_qty"):
            ri[c] = ri[c].fillna(0.0)

        # % 字符串
        ri["procurement_delivery_rate"] = ri.apply(
            lambda x: f"{safe_divide(x['cumulative_factory_delivery_qty'], x['order_qty'])*100:.1f}%",
            axis=1,
        )
        ri["procurement_pickup_rate"] = ri.apply(
            lambda x: f"{safe_divide(x['cumulative_pickup_qty'], x['order_qty'])*100:.1f}%",
            axis=1,
        )
        ri["stock_in_complete_rate"] = ri.apply(
            lambda x: f"{safe_divide(x['cumulative_stock_in_qty'], x['order_qty'])*100:.1f}%",
            axis=1,
        )
        ri["pending_delivery_qty"] = ri.apply(
            lambda x: max(x["order_qty"] - x["cumulative_factory_delivery_qty"], 0), axis=1,
        )
        ri["pending_pickup_qty"] = ri.apply(
            lambda x: max(x["cumulative_factory_delivery_qty"] - x["cumulative_pickup_qty"], 0), axis=1,
        )
        ri["pending_stock_in_qty"] = ri.apply(
            lambda x: max(x["cumulative_pickup_qty"] - x["cumulative_stock_in_qty"], 0), axis=1,
        )
        ri["offline_pending_stock_in_qty"] = ri.apply(
            lambda x: max(x["cumulative_factory_delivery_qty"] - x["cumulative_stock_in_qty"], 0), axis=1,
        )

        for f in ("delivery_cycle", "order_qty", "cumulative_factory_delivery_qty",
                  "cumulative_pickup_qty", "cumulative_stock_in_qty",
                  "pending_delivery_qty", "pending_pickup_qty",
                  "pending_stock_in_qty", "offline_pending_stock_in_qty"):
            if f in ri.columns:
                ri[f] = ri[f].fillna(0).astype(int)

        ctx.rpt[_OUTPUT] = ri.reset_index(drop=True)
        return ctx