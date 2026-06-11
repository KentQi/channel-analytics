"""5 张 STG 表(原仓 ETLConfig.TABLE_NAMES 中 STG 部分)。

字段对齐原仓清洗后 ETL 输出(供 RPT 步骤消费)。
列定义用通用 SQLAlchemy 类型(无方言特定类型),保证 sqlite / mysql / postgres 全部兼容。
"""
from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Float, Integer, String

from channel_analytics.db.models.base import Base


class StgPurchaseReq(Base):
    """请购单(清洗后)。"""
    __tablename__ = "stg_purchase_req"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(64), index=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    order_qty = Column(Float)
    delivery_cycle = Column(Integer)
    request_date = Column(Date)
    requester = Column(String(64))


class StgPurchaseOrder(Base):
    """采购单(清洗后)。"""
    __tablename__ = "stg_purchase_order"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(64), index=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    factory_delivery_qty = Column(Float)
    pickup_qty = Column(Float)
    delivery_date = Column(Date)
    brand_sales_no = Column(String(64), index=True)


class StgStockIn(Base):
    """入库单(清洗后)。"""
    __tablename__ = "stg_stock_in"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_sales_no = Column(String(64), index=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    batch_number = Column(String(64), index=True)
    stock_in_qty = Column(Float)
    stock_in_date = Column(Date)
    expiry_date = Column(Date)


class StgSalesOut(Base):
    """销售出库单(清洗后)。"""
    __tablename__ = "stg_sales_out"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    batch_number = Column(String(64), index=True)
    doc_date = Column(Date, index=True)
    sales_out_qty = Column(Float)
    customer = Column(String(128), index=True)


class StgStockCurrent(Base):
    """当前库存(清洗后)。"""
    __tablename__ = "stg_stock_current"
    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse = Column(String(64), index=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    batch_number = Column(String(64), index=True)
    brand = Column(String(128))
    available_qty = Column(Float)
    expiry_date = Column(Date)