"""SQLAlchemy ORM 模型 — 5 张 STG + 7 张 RPT + 5 张 dim 共 17 张表。

设计要点:
  - declarative_base 单一来源(channel_analytics.db.models.base.Base)
  - 所有表名 + 列名与原仓 ETL 路径(PIPELINE)对齐,RPT 表对应原仓 rpt_*
  - 不写明 schema 强约束(给部署期灵活度);列类型用通用 SQLAlchemy 类型
  - 通过 Base.metadata.create_all(engine) 在 sqlite / mysql / postgres 全部能建表
"""
from channel_analytics.db.models.base import Base
from channel_analytics.db.models.stg import (
    StgPurchaseReq,
    StgPurchaseOrder,
    StgStockIn,
    StgSalesOut,
    StgStockCurrent,
)
from channel_analytics.db.models.rpt import (
    RptExpiryWarning,
    RptExpiryTurnover,
    RptSelfOperatedConcentration,
    RptTurnoverWarning,
    RptTrendWarning,
    RptWarehouseRisk,
    RptProcurementLinked,
)
from channel_analytics.db.models.dim import (
    DimBrand,
    DimProductAttr,
    DimWarehouse,
    DimCustomer,
    DimFilterConfig,
)


__all__ = [
    "Base",
    # STG
    "StgPurchaseReq", "StgPurchaseOrder", "StgStockIn", "StgSalesOut", "StgStockCurrent",
    # RPT
    "RptExpiryWarning", "RptExpiryTurnover", "RptSelfOperatedConcentration",
    "RptTurnoverWarning", "RptTrendWarning", "RptWarehouseRisk", "RptProcurementLinked",
    # dim
    "DimBrand", "DimProductAttr", "DimWarehouse", "DimCustomer", "DimFilterConfig",
]