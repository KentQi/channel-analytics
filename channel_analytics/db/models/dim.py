"""dim 表 — 5 张(原仓 dim_* + dim_product_attr)。"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text

from channel_analytics.db.models.base import Base


class DimBrand(Base):
    """自营品牌白名单表(对应原仓 dim_self_operated_brand)。"""
    __tablename__ = "dim_brand"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_name = Column(String(128), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)


class DimProductAttr(Base):
    """物料属性维度(对应原仓 dim_product_attr — ETL 末尾自动刷新)。"""
    __tablename__ = "dim_product_attr"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(64), unique=True, index=True, nullable=False)
    material_name = Column(String(255))
    category = Column(String(128))
    abc_class = Column(String(16))
    lifecycle_status = Column(String(32))
    custom_flag = Column(Boolean, default=False)
    promoted_flag = Column(Boolean, default=False)
    updated_at = Column(DateTime)


class DimWarehouse(Base):
    """仓库维度。"""
    __tablename__ = "dim_warehouse"
    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_code = Column(String(64), unique=True, index=True, nullable=False)
    warehouse_name = Column(String(255))
    region = Column(String(64))
    is_active = Column(Boolean, default=True)


class DimCustomer(Base):
    """客户维度。"""
    __tablename__ = "dim_customer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_code = Column(String(64), unique=True, index=True, nullable=False)
    customer_name = Column(String(255))
    channel = Column(String(64))
    is_active = Column(Boolean, default=True)


class DimFilterConfig(Base):
    """筛选配置(原仓 L671 用 — build_sales_out_wide 客户筛选)。"""
    __tablename__ = "dim_filter_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filter_type = Column(String(64), nullable=False, index=True)
    filter_value = Column(String(255), nullable=False)
    notes = Column(Text)