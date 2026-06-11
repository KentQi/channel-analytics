"""create_all + drop_all 工具函数。"""
from __future__ import annotations

from sqlalchemy.engine import Engine

from channel_analytics.db.models.base import Base
from channel_analytics.db.models import (  # noqa: F401  触发模型注册
    StgPurchaseReq, StgPurchaseOrder, StgStockIn, StgSalesOut, StgStockCurrent,
    RptExpiryWarning, RptExpiryTurnover, RptSelfOperatedConcentration,
    RptTurnoverWarning, RptTrendWarning, RptWarehouseRisk, RptProcurementLinked,
    DimBrand, DimProductAttr, DimWarehouse, DimCustomer, DimFilterConfig,
)


def create_all(engine: Engine) -> None:
    """建全部 17 张表。"""
    Base.metadata.create_all(engine)


def drop_all(engine: Engine) -> None:
    """删全部 17 张表(谨慎使用,会丢数据)。"""
    Base.metadata.drop_all(engine)


__all__ = ["create_all", "drop_all"]