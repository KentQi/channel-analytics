"""initial schema — 17 张表(stg_/rpt_/dim_)

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- STG(5 张) ----
    op.create_table(
        "stg_purchase_req",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(64), index=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("order_qty", sa.Float),
        sa.Column("delivery_cycle", sa.Integer),
        sa.Column("request_date", sa.Date),
        sa.Column("requester", sa.String(64)),
    )
    op.create_table(
        "stg_purchase_order",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(64), index=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("factory_delivery_qty", sa.Float),
        sa.Column("pickup_qty", sa.Float),
        sa.Column("delivery_date", sa.Date),
        sa.Column("brand_sales_no", sa.String(64), index=True),
    )
    op.create_table(
        "stg_stock_in",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("brand_sales_no", sa.String(64), index=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("batch_number", sa.String(64), index=True),
        sa.Column("stock_in_qty", sa.Float),
        sa.Column("stock_in_date", sa.Date),
        sa.Column("expiry_date", sa.Date),
    )
    op.create_table(
        "stg_sales_out",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("batch_number", sa.String(64), index=True),
        sa.Column("doc_date", sa.Date, index=True),
        sa.Column("sales_out_qty", sa.Float),
        sa.Column("customer", sa.String(128), index=True),
    )
    op.create_table(
        "stg_stock_current",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("warehouse", sa.String(64), index=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("batch_number", sa.String(64), index=True),
        sa.Column("brand", sa.String(128)),
        sa.Column("available_qty", sa.Float),
        sa.Column("expiry_date", sa.Date),
    )

    # ---- RPT(7 张,字段从 ORM 模型对应) ----
    op.create_table(
        "rpt_expiry_warning",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("brand", sa.String(128)),
        sa.Column("brand_class", sa.String(32), index=True),
        sa.Column("batch_no", sa.String(64)),
        sa.Column("expiry_date", sa.Date),
        sa.Column("material_batch_available_qty", sa.Integer),
        sa.Column("sales_90d", sa.Integer),
        sa.Column("inventory_days", sa.Integer),
        sa.Column("remaining_expiry_months", sa.Integer),
        sa.Column("expiry_status", sa.String(64)),
        sa.Column("expiry_warning", sa.String(32), index=True),
    )
    op.create_table(
        "rpt_expiry_turnover",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("brand_class", sa.String(32), index=True),
        sa.Column("expiry_status", sa.String(64)),
        sa.Column("available_qty", sa.Integer),
        sa.Column("sales_90d", sa.Integer),
        sa.Column("turnover_days", sa.Float),
    )
    op.create_table(
        "rpt_self_operated_concentration",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("brand", sa.String(128)),
        sa.Column("expiry_status", sa.String(64)),
        sa.Column("material_batch_available_qty", sa.Integer),
        sa.Column("stock_ratio", sa.String(32)),
        sa.Column("cumulative_stock_ratio", sa.String(32)),
        sa.Column("sales_90d", sa.Integer),
    )
    op.create_table(
        "rpt_turnover_warning",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("brand", sa.String(128)),
        sa.Column("brand_class", sa.String(32), index=True),
        sa.Column("material_available_qty", sa.Integer),
        sa.Column("sales_90d", sa.Integer),
        sa.Column("inventory_days", sa.Integer),
        sa.Column("turnover_status", sa.String(64)),
        sa.Column("turnover_warning", sa.String(32), index=True),
    )
    op.create_table(
        "rpt_trend_warning",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("brand", sa.String(128)),
        sa.Column("brand_class", sa.String(32), index=True),
        sa.Column("material_available_qty", sa.Integer),
        sa.Column("cycle_4_sales", sa.Integer),
        sa.Column("cycle_3_sales", sa.Integer),
        sa.Column("cycle_2_sales", sa.Integer),
        sa.Column("cycle_1_sales", sa.Integer),
        sa.Column("total_dispatch_90d", sa.Integer),
        sa.Column("total_return_qty", sa.Integer),
        sa.Column("sales_90d", sa.Integer),
        sa.Column("return_ratio", sa.String(32)),
        sa.Column("trend_status", sa.String(64)),
        sa.Column("trend_warning", sa.String(32), index=True),
    )
    op.create_table(
        "rpt_warehouse_risk",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("warehouse", sa.String(64), index=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("brand", sa.String(128)),
        sa.Column("brand_class", sa.String(32), index=True),
        sa.Column("material_available_qty", sa.Integer),
        sa.Column("expiry_warning_status", sa.String(32)),
        sa.Column("inventory_days", sa.Integer),
        sa.Column("turnover_warning", sa.String(32)),
        sa.Column("return_ratio", sa.String(32)),
        sa.Column("trend_status", sa.String(64)),
        sa.Column("trend_warning", sa.String(32)),
        sa.Column("risk_level", sa.String(32), index=True),
    )
    op.create_table(
        "rpt_procurement_linked",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(64), index=True),
        sa.Column("material_code", sa.String(64), index=True),
        sa.Column("order_qty", sa.Integer),
        sa.Column("delivery_cycle", sa.Integer),
        sa.Column("cumulative_factory_delivery_qty", sa.Integer),
        sa.Column("cumulative_pickup_qty", sa.Integer),
        sa.Column("cumulative_stock_in_qty", sa.Integer),
        sa.Column("brand_sales_no", sa.String(64), index=True),
        sa.Column("first_delivery_date", sa.Date),
        sa.Column("last_delivery_date", sa.Date),
        sa.Column("first_stock_in_date", sa.Date),
        sa.Column("procurement_delivery_rate", sa.String(32)),
        sa.Column("procurement_pickup_rate", sa.String(32)),
        sa.Column("stock_in_complete_rate", sa.String(32)),
        sa.Column("pending_delivery_qty", sa.Integer),
        sa.Column("pending_pickup_qty", sa.Integer),
        sa.Column("pending_stock_in_qty", sa.Integer),
        sa.Column("offline_pending_stock_in_qty", sa.Integer),
    )

    # ---- dim(5 张) ----
    op.create_table(
        "dim_brand",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("brand_name", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "dim_product_attr",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("material_name", sa.String(255)),
        sa.Column("category", sa.String(128)),
        sa.Column("abc_class", sa.String(16)),
        sa.Column("lifecycle_status", sa.String(32)),
        sa.Column("custom_flag", sa.Boolean, default=False),
        sa.Column("promoted_flag", sa.Boolean, default=False),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_table(
        "dim_warehouse",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("warehouse_code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("warehouse_name", sa.String(255)),
        sa.Column("region", sa.String(64)),
        sa.Column("is_active", sa.Boolean, default=True),
    )
    op.create_table(
        "dim_customer",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("customer_code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("customer_name", sa.String(255)),
        sa.Column("channel", sa.String(64)),
        sa.Column("is_active", sa.Boolean, default=True),
    )
    op.create_table(
        "dim_filter_config",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filter_type", sa.String(64), nullable=False, index=True),
        sa.Column("filter_value", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text),
    )


def downgrade() -> None:
    for t in (
        "stg_purchase_req", "stg_purchase_order", "stg_stock_in",
        "stg_sales_out", "stg_stock_current",
        "rpt_expiry_warning", "rpt_expiry_turnover",
        "rpt_self_operated_concentration", "rpt_turnover_warning",
        "rpt_trend_warning", "rpt_warehouse_risk", "rpt_procurement_linked",
        "dim_brand", "dim_product_attr", "dim_warehouse",
        "dim_customer", "dim_filter_config",
    ):
        op.drop_table(t)