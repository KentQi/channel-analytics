"""W6-1 单测 — 17 张表 schema 验证(sqlite 内存)。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect

from channel_analytics.db.engine import create_all, drop_all
from channel_analytics.db.models import (
    DimBrand, DimCustomer, DimFilterConfig, DimProductAttr, DimWarehouse,
    RptExpiryTurnover, RptExpiryWarning, RptProcurementLinked,
    RptSelfOperatedConcentration, RptTrendWarning, RptTurnoverWarning,
    RptWarehouseRisk,
    StgPurchaseOrder, StgPurchaseReq, StgSalesOut, StgStockCurrent, StgStockIn,
)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    create_all(eng)
    yield eng
    eng.dispose()


class TestSchemaCreate:
    def test_create_all_creates_17_tables(self, engine):
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        expected = {
            # STG
            "stg_purchase_req", "stg_purchase_order", "stg_stock_in",
            "stg_sales_out", "stg_stock_current",
            # RPT
            "rpt_expiry_warning", "rpt_expiry_turnover",
            "rpt_self_operated_concentration", "rpt_turnover_warning",
            "rpt_trend_warning", "rpt_warehouse_risk", "rpt_procurement_linked",
            # dim
            "dim_brand", "dim_product_attr", "dim_warehouse",
            "dim_customer", "dim_filter_config",
        }
        assert expected.issubset(tables), f"缺表: {expected - tables}"

    def test_drop_all_removes_tables(self, engine):
        drop_all(engine)
        insp = inspect(engine)
        # 删完后应剩 0 张业务表
        business = {t for t in insp.get_table_names()
                    if t.startswith(("stg_", "rpt_", "dim_"))}
        assert business == set()


class TestStgTables:
    @pytest.mark.parametrize("table,expected_cols", [
        (StgPurchaseReq, {"order_no", "material_code", "order_qty", "delivery_cycle"}),
        (StgPurchaseOrder, {"order_no", "material_code", "factory_delivery_qty",
                            "pickup_qty", "delivery_date", "brand_sales_no"}),
        (StgStockIn, {"brand_sales_no", "material_code", "batch_number",
                      "stock_in_qty", "stock_in_date", "expiry_date"}),
        (StgSalesOut, {"material_code", "batch_number", "doc_date", "sales_out_qty", "customer"}),
        (StgStockCurrent, {"warehouse", "material_code", "batch_number",
                           "available_qty", "expiry_date", "brand"}),
    ])
    def test_required_columns_present(self, engine, table, expected_cols):
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns(table.__tablename__)}
        assert expected_cols.issubset(cols), \
            f"{table.__tablename__} 缺列: {expected_cols - cols}"


class TestRptTables:
    @pytest.mark.parametrize("table,expected_cols", [
        (RptExpiryWarning, {"material_code", "expiry_status", "expiry_warning", "sales_90d"}),
        (RptExpiryTurnover, {"brand_class", "expiry_status", "turnover_days"}),
        (RptSelfOperatedConcentration, {"material_code", "stock_ratio",
                                        "cumulative_stock_ratio"}),
        (RptTurnoverWarning, {"material_code", "inventory_days", "turnover_warning"}),
        (RptTrendWarning, {"material_code", "cycle_1_sales", "trend_status", "trend_warning"}),
        (RptWarehouseRisk, {"warehouse", "material_code", "risk_level"}),
        (RptProcurementLinked, {"order_no", "material_code", "procurement_delivery_rate"}),
    ])
    def test_required_columns_present(self, engine, table, expected_cols):
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns(table.__tablename__)}
        assert expected_cols.issubset(cols), \
            f"{table.__tablename__} 缺列: {expected_cols - cols}"


class TestDimTables:
    @pytest.mark.parametrize("table,expected_cols", [
        (DimBrand, {"brand_name"}),
        (DimProductAttr, {"material_code", "lifecycle_status"}),
        (DimWarehouse, {"warehouse_code"}),
        (DimCustomer, {"customer_code"}),
        (DimFilterConfig, {"filter_type", "filter_value"}),
    ])
    def test_required_columns_present(self, engine, table, expected_cols):
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns(table.__tablename__)}
        assert expected_cols.issubset(cols)

    def test_dim_brand_unique_on_brand_name(self, engine):
        insp = inspect(engine)
        # sqlite 把 UNIQUE 表现为 unique index(inspect.get_unique_constraints 返回空)
        # 同时检查两种来源
        unique_cols = {
            tuple(c["column_names"])
            for c in insp.get_unique_constraints("dim_brand")
        }
        unique_indexes = {
            tuple(idx["column_names"])
            for idx in insp.get_indexes("dim_brand")
            if idx.get("unique")
        }
        all_unique = unique_cols | unique_indexes
        assert ("brand_name",) in all_unique, \
            f"brand_name 不在 UNIQUE 约束中: {all_unique}"