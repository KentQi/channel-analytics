"""7 张 RPT 表(对应原仓 ETLConfig.TABLE_NAMES 中 RPT 部分 + 销售宽表)。

字段对应 Pipeline 各步骤的 OUTPUT_COLS。
"""
from __future__ import annotations

from sqlalchemy import Column, Date, Float, Integer, String

from channel_analytics.db.models.base import Base


class RptExpiryWarning(Base):
    """RPT 1:物料+批次效期告警。"""
    __tablename__ = "rpt_expiry_warning"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    brand = Column(String(128))
    brand_class = Column(String(32), index=True)
    batch_no = Column(String(64))
    expiry_date = Column(Date)
    material_batch_available_qty = Column(Integer)
    sales_90d = Column(Integer)
    inventory_days = Column(Integer)
    remaining_expiry_months = Column(Integer)
    expiry_status = Column(String(64))
    expiry_warning = Column(String(32), index=True)


class RptExpiryTurnover(Base):
    """RPT 2:效期-周转关联(brand_class × expiry_status)。"""
    __tablename__ = "rpt_expiry_turnover"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_class = Column(String(32), index=True)
    expiry_status = Column(String(64))
    available_qty = Column(Integer)
    sales_90d = Column(Integer)
    turnover_days = Column(Float)


class RptSelfOperatedConcentration(Base):
    """RPT 3:自营品库存集中度。"""
    __tablename__ = "rpt_self_operated_concentration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    brand = Column(String(128))
    expiry_status = Column(String(64))
    material_batch_available_qty = Column(Integer)
    stock_ratio = Column(String(32))
    cumulative_stock_ratio = Column(String(32))
    sales_90d = Column(Integer)


class RptTurnoverWarning(Base):
    """RPT 4:物料维度周转告警。"""
    __tablename__ = "rpt_turnover_warning"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    brand = Column(String(128))
    brand_class = Column(String(32), index=True)
    material_available_qty = Column(Integer)
    sales_90d = Column(Integer)
    inventory_days = Column(Integer)
    turnover_status = Column(String(64))
    turnover_warning = Column(String(32), index=True)


class RptTrendWarning(Base):
    """RPT 5:物料维度趋势告警。"""
    __tablename__ = "rpt_trend_warning"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    brand = Column(String(128))
    brand_class = Column(String(32), index=True)
    material_available_qty = Column(Integer)
    cycle_4_sales = Column(Integer)
    cycle_3_sales = Column(Integer)
    cycle_2_sales = Column(Integer)
    cycle_1_sales = Column(Integer)
    total_dispatch_90d = Column(Integer)
    total_return_qty = Column(Integer)
    sales_90d = Column(Integer)
    return_ratio = Column(String(32))
    trend_status = Column(String(64))
    trend_warning = Column(String(32), index=True)


class RptWarehouseRisk(Base):
    """RPT 6:物料×warehouse 综合风险。"""
    __tablename__ = "rpt_warehouse_risk"
    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse = Column(String(64), index=True)
    material_code = Column(String(64), index=True)
    material_name = Column(String(255))
    brand = Column(String(128))
    brand_class = Column(String(32), index=True)
    material_available_qty = Column(Integer)
    expiry_warning_status = Column(String(32))
    inventory_days = Column(Integer)
    turnover_warning = Column(String(32))
    return_ratio = Column(String(32))
    trend_status = Column(String(64))
    trend_warning = Column(String(32))
    risk_level = Column(String(32), index=True)


class RptProcurementLinked(Base):
    """RPT 7:请购-采购-入库 三表关联。"""
    __tablename__ = "rpt_procurement_linked"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(64), index=True)
    material_code = Column(String(64), index=True)
    order_qty = Column(Integer)
    delivery_cycle = Column(Integer)
    cumulative_factory_delivery_qty = Column(Integer)
    cumulative_pickup_qty = Column(Integer)
    cumulative_stock_in_qty = Column(Integer)
    brand_sales_no = Column(String(64), index=True)
    first_delivery_date = Column(Date)
    last_delivery_date = Column(Date)
    first_stock_in_date = Column(Date)
    procurement_delivery_rate = Column(String(32))
    procurement_pickup_rate = Column(String(32))
    stock_in_complete_rate = Column(String(32))
    pending_delivery_qty = Column(Integer)
    pending_pickup_qty = Column(Integer)
    pending_stock_in_qty = Column(Integer)
    offline_pending_stock_in_qty = Column(Integer)