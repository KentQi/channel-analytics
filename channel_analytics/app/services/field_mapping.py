# -*- coding: utf-8 -*-
"""
中英文字段映射表（全局统一引用）
Excel/源文件(中文) → ETL rename → 数据库/代码(英文)
同时提供反向映射(英→中)，用于前端展示。
"""

# ============================================================
# DIM 表映射
# ============================================================

DIM_PRODUCT_ATTR = {
    "物料编码": "material_code",
    "物料名称": "material_name",
    "商品品类": "category",
    "首批入库时间": "first_stock_in_date",
    "ABC分类": "abc_class",
    "生命周期": "lifecycle_status",
    "定制标记": "custom_flag",
    "主推标记": "promoted_flag",
    "创建时间": "created_at",
    "更新时间": "updated_at",
}

DIM_CUSTOMER = {
    "客户名称": "customer_name",
    "大区": "region",
    "省区": "province",
    "销售区域": "sales_area",
    "客户渠道": "channel",
    "合作状态": "cooperation_status",
    "客户经理": "account_manager",
    "创建时间": "created_at",
    "更新时间": "updated_at",
}

DIM_BUSINESS_INDICATOR_REGION = {
    "时间": "period",
    "大区": "region",
    "省份": "province",
    "销售区域": "sales_area",
    "负责人": "manager",
    "月度指标": "monthly_target",
    "创建时间": "created_at",
    "更新时间": "updated_at",
}

DIM_BUSINESS_INDICATOR_CUSTOMER = {
    "时间": "period",
    "大区": "region",
    "省份": "province",
    "销售区域": "sales_area",
    "负责人": "manager",
    "客户名称": "customer_name",
    "月度指标": "monthly_target",
    "创建时间": "created_at",
    "更新时间": "updated_at",
}

DIM_SELF_OPERATED_BRAND = {
    "品牌名称": "brand_name",
    "备注": "remark",
    "创建时间": "created_at",
    "更新时间": "updated_at",
}

DIM_FILTER_CONFIG = {
    "筛选类型": "filter_type",
    "筛选值": "filter_value",
    "创建时间": "created_at",
    "更新时间": "updated_at",
}

# ============================================================
# STG 表映射
# ============================================================

STG_PURCHASE_REQ = {
    "下单日期": "order_date",
    "下单单号": "order_no",
    "渠道对接人": "channel_contact",
    "交货周期": "delivery_cycle",
    "品牌": "brand",
    "推广词": "promotion_tags",
    "商品条码": "material_code",
    "商品名称": "material_name",
    "渠道": "channel",
    "下单数量": "order_qty",
    "下单备注": "order_remark",
    "预计交货日期": "expected_delivery_date",
    "实际到货手工登账数量": "actual_manual_stock_qty",
    "特殊情况备注": "special_remark",
    "是否到货": "is_delivered",
}

STG_PURCHASE_ORDER = {
    "到货日期": "delivery_date",
    "下单单号": "order_no",
    "品牌": "brand",
    "商品条码": "material_code",
    "商品名称": "material_name",
    "工厂交付数量": "factory_delivery_qty",
    "批次号": "batch_no",
    "限用日期": "expiry_date",
    "品牌销售单号": "brand_sales_no",
    "备注": "remark",
    "提货数量": "pickup_qty",
    "生产日期": "production_date",
    "是否开单": "is_billed",
}

STG_STOCK_IN = {
    "品牌销售单号": "brand_sales_no",
    "单据日期": "stock_in_date",
    "单据编号": "doc_no",
    "订单交易类型": "order_tx_type",
    "审核日期": "audit_date",
    "物料sku编码": "material_code",
    "物料sku名称": "material_name",
    "应收数量": "receivable_qty",
    "批次号": "batch_no",
    "仓库": "warehouse",
    "单据状态": "doc_status",
    "有效期至": "expiry_date",
    "型号": "model",
    "入库数量": "stock_in_qty",
    "备注": "remark",
    "物流单号": "logistics_no",
    "物流公司": "logistics_company",
    "供应商物料编码": "supplier_material_code",
    "供应商物料名称": "supplier_material_name",
}

STG_SALES_OUT = {
    "单据日期": "doc_date",
    "单据编号": "doc_no",
    "源头交易类型": "source_tx_type",
    "交易类型名称": "tx_type_name",
    "客户": "customer",
    "客户分类": "customer_class",
    "大区经理": "region_manager",
    "仓库": "warehouse",
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "含税金额": "tax_included_amount",
    "批次号": "batch_no",
    "出货渠道": "shipping_channel",
    "审核日期": "audit_date",
    "创建人": "creator",
    "销售出库数量": "sales_out_qty",
    "应发数量": "dispatch_qty",
    "已开票数量": "invoiced_qty",
    "交易类型": "tx_type",
    "审核时间": "audit_time",
    "备注": "remark",
    "来源单据交易类型": "source_doc_tx_type",
    "入账方式": "entry_method",
    "含税单价": "tax_included_unit_price",
    "源头单据号": "source_doc_no",
}

STG_STOCK_CURRENT = {
    "仓库": "warehouse",
    "品牌": "brand",
    "物料sku编码": "material_code",
    "物料sku名称": "material_name",
    "批号": "batch_no",
    "生产日期": "production_date",
    "有效期至": "expiry_date",
    "规格说明": "spec",
    "现存量": "current_stock",
    "可用量": "available_qty",
    "品牌分类": "brand_class",
    "发货预计出库量": "estimated_shipping_qty",
    "订单预计出库量": "estimated_order_qty",
}

# ============================================================
# RPT 报表表映射
# ============================================================

RPT_SALES_OUT_WIDE = {
    "单据日期": "doc_date",
    "单据编号": "doc_no",
    "交易类型": "tx_type",
    "交易类型名称": "tx_type_name",
    "客户": "customer",
    "客户分类": "customer_class",
    "大区经理": "region_manager",
    "仓库": "warehouse",
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "含税金额": "tax_included_amount",
    "批次号": "batch_no",
    "出货渠道": "shipping_channel",
    "审核日期": "audit_date",
    "审核时间": "audit_time",
    "创建人": "creator",
    "销售出库数量": "sales_out_qty",
    "应发数量": "dispatch_qty",
    "已开票数量": "invoiced_qty",
    "来源单据交易类型": "source_doc_tx_type",
    "入账方式": "entry_method",
    "含税单价": "tax_included_unit_price",
    "源头单据号": "source_doc_no",
    "源头交易类型": "source_tx_type",
    "备注": "remark",
    "商品品类": "category",
    "ABC分类": "abc_class",
    "生命周期状态": "lifecycle_status",
    "定制标记": "custom_flag",
    "主推标记": "promoted_flag",
    "大区": "region",
    "客户经理": "account_manager",
    "渠道": "channel",
    "创建时间": "creation_time",
}

RPT_EXPIRY_WARNING = {
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "品牌分类": "brand_class",
    "批号": "batch_no",
    "有效期至": "expiry_date",
    "可用数量": "material_batch_available_qty",
    "90天销量": "sales_90d",
    "库存天数": "inventory_days",
    "剩余有效期月数": "remaining_expiry_months",
    "效期状态": "expiry_status",
    "效期预警": "expiry_warning",
    "型号": "model",
}

RPT_EXPIRY_TURNOVER = {
    "品牌分类": "brand_class",
    "效期状态": "expiry_status",
    "可用数量": "available_qty",
    "90天销量": "sales_90d",
    "周转天数": "turnover_days",
}

RPT_SELF_OPERATED_CONCENTRATION = {
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "效期状态": "expiry_status",
    "可用数量": "material_batch_available_qty",
    "库存占比": "stock_ratio",
    "累计库存占比": "cumulative_stock_ratio",
    "90天销量": "sales_90d",
    "型号": "model",
}

RPT_TURNOVER_WARNING = {
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "品牌分类": "brand_class",
    "可用数量": "material_available_qty",
    "90天销量": "sales_90d",
    "库存天数": "inventory_days",
    "周转状态": "turnover_status",
    "周转预警": "turnover_warning",
    "型号": "model",
}

RPT_TREND_WARNING = {
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "品牌分类": "brand_class",
    "可用数量": "material_available_qty",
    "周期4销量": "cycle_4_sales",
    "周期3销量": "cycle_3_sales",
    "周期2销量": "cycle_2_sales",
    "周期1销量": "cycle_1_sales",
    "90天总发货": "total_dispatch_90d",
    "总退货数量": "total_return_qty",
    "90天销量": "sales_90d",
    "退货率": "return_ratio",
    "趋势状态": "trend_status",
    "趋势预警": "trend_warning",
    "型号": "model",
}

RPT_WAREHOUSE_RISK = {
    "仓库": "warehouse",
    "物料编码": "material_code",
    "物料名称": "material_name",
    "品牌": "brand",
    "品牌分类": "brand_class",
    "可用数量": "material_available_qty",
    "效期预警状态": "expiry_warning_status",
    "库存天数": "inventory_days",
    "周转预警": "turnover_warning",
    "退货率": "return_ratio",
    "趋势状态": "trend_status",
    "趋势预警": "trend_warning",
    "风险等级": "risk_level",
    "型号": "model",
}

RPT_PROCUREMENT_LINKED = {
    "下单日期": "order_date",
    "渠道对接人": "channel_contact",
    "交货周期": "delivery_cycle",
    "下单单号": "order_no",
    "是否到货": "is_delivered",
    "品牌": "brand",
    "推广词": "promotion_tags",
    "物料编码": "material_code",
    "物料名称": "material_name",
    "渠道": "channel",
    "下单数量": "order_qty",
    "下单备注": "order_remark",
    "预计交货日期": "expected_delivery_date",
    "实际手工登账数量": "actual_manual_stock_qty",
    "特殊情况备注": "special_remark",
}

# ============================================================
# 枚举常量（对齐原版 config.py）
# ============================================================

ABC_VALID = {"引流品", "主推品", "利润品"}

LIFECYCLE_VALID = {"新品", "持续销售", "售完即止", "重新上架", "淘汰"}

LIFECYCLE_STATUS = {
    "END_OF_LIFE": "售完即止",
    "NEW": "新品",
    "ONGOING": "持续销售",
    "PHASING_OUT": "淘汰",
    "FULL": "足量",
    "RESTOCK": "重新上架",
}

CUST_CHANNEL_VALID = ["批发", "零售", "电商", "直营"]

CUST_STATUS_VALID = ["合作中", "已暂停", "已终止"]

MAX_IMPORT_ROWS = 5000

# ============================================================
# 反向映射（英→中）：用于前端展示
# ============================================================

def build_reverse_map(forward_map: dict) -> dict:
    return {v: k for k, v in forward_map.items()}

REVERSE_DIM_PRODUCT_ATTR = build_reverse_map(DIM_PRODUCT_ATTR)
REVERSE_DIM_CUSTOMER = build_reverse_map(DIM_CUSTOMER)
REVERSE_DIM_BUSINESS_INDICATOR_REGION = build_reverse_map(DIM_BUSINESS_INDICATOR_REGION)
REVERSE_DIM_BUSINESS_INDICATOR_CUSTOMER = build_reverse_map(DIM_BUSINESS_INDICATOR_CUSTOMER)
REVERSE_DIM_SELF_OPERATED_BRAND = build_reverse_map(DIM_SELF_OPERATED_BRAND)
REVERSE_DIM_FILTER_CONFIG = build_reverse_map(DIM_FILTER_CONFIG)

REVERSE_STG_PURCHASE_REQ = build_reverse_map(STG_PURCHASE_REQ)
REVERSE_STG_PURCHASE_ORDER = build_reverse_map(STG_PURCHASE_ORDER)
REVERSE_STG_STOCK_IN = build_reverse_map(STG_STOCK_IN)
REVERSE_STG_SALES_OUT = build_reverse_map(STG_SALES_OUT)
REVERSE_STG_STOCK_CURRENT = build_reverse_map(STG_STOCK_CURRENT)
REVERSE_RPT_SALES_OUT_WIDE = build_reverse_map(RPT_SALES_OUT_WIDE)
REVERSE_RPT_EXPIRY_WARNING = build_reverse_map(RPT_EXPIRY_WARNING)
REVERSE_RPT_EXPIRY_TURNOVER = build_reverse_map(RPT_EXPIRY_TURNOVER)
REVERSE_RPT_SELF_OPERATED_CONCENTRATION = build_reverse_map(RPT_SELF_OPERATED_CONCENTRATION)
REVERSE_RPT_TURNOVER_WARNING = build_reverse_map(RPT_TURNOVER_WARNING)
REVERSE_RPT_TREND_WARNING = build_reverse_map(RPT_TREND_WARNING)
REVERSE_RPT_WAREHOUSE_RISK = build_reverse_map(RPT_WAREHOUSE_RISK)
REVERSE_RPT_PROCUREMENT_LINKED = build_reverse_map(RPT_PROCUREMENT_LINKED)

# ============================================================
# 前端展示重命名表
# ============================================================

_DISPLAY_MAPS = {
    "dim_product_attr": REVERSE_DIM_PRODUCT_ATTR,
    "dim_customer": REVERSE_DIM_CUSTOMER,
    "dim_business_indicator_region": REVERSE_DIM_BUSINESS_INDICATOR_REGION,
    "dim_business_indicator_customer": REVERSE_DIM_BUSINESS_INDICATOR_CUSTOMER,
    "dim_self_operated_brand": REVERSE_DIM_SELF_OPERATED_BRAND,
    "dim_filter_config": REVERSE_DIM_FILTER_CONFIG,
    "rpt_sales_out_wide": REVERSE_RPT_SALES_OUT_WIDE,
    "rpt_expiry_warning": REVERSE_RPT_EXPIRY_WARNING,
    "rpt_expiry_turnover": REVERSE_RPT_EXPIRY_TURNOVER,
    "rpt_self_operated_concentration": REVERSE_RPT_SELF_OPERATED_CONCENTRATION,
    "rpt_turnover_warning": REVERSE_RPT_TURNOVER_WARNING,
    "rpt_trend_warning": REVERSE_RPT_TREND_WARNING,
    "rpt_warehouse_risk": REVERSE_RPT_WAREHOUSE_RISK,
    "rpt_procurement_linked": REVERSE_RPT_PROCUREMENT_LINKED,
}


def rename_for_display(df, table_name):
    """将 DataFrame 英文字段名按 table_name 对应的映射表重命名为中文。"""
    import pandas as pd
    reverse_map = _DISPLAY_MAPS.get(table_name)
    if reverse_map is None:
        return df
    cols_to_rename = {k: v for k, v in reverse_map.items() if k in df.columns}
    if not cols_to_rename:
        return df
    return df.rename(columns=cols_to_rename)
