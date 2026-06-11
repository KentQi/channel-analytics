"""
ETL core service — 对齐原版 etl_processor.py + etl.py 的完整管道：
  - 5 张 STG 表清洗
  - 7 张 RPT 表生成
  - rpt_sales_out_wide 宽表构建
  - dim_product_attr 自动刷新
  - 全部写入 MySQL
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)


# ===================== Configuration =====================
class ETLConfig:
    """ETL configuration constants."""
    CURRENT_DATE = datetime.now().date()
    CURRENT_DATE_DT = datetime.combine(CURRENT_DATE, datetime.min.time())

    SELF_OPERATED_BRANDS_FALLBACK = [
        "Brand A", "Brand B", "Brand C", "Brand D",
        "Brand E", "Brand F", "Brand G", "Brand H",
        "Brand I", "Brand J", "Brand K", "Brand L"
    ]

    BATCH_CLEAN_RULES = ['', ' ', 'NA', '/', '\\', '无', '虚拟退货']
    EXPIRY_CLEAN_RULES = ['', ' ']
    TURNOVER_CYCLE_DAYS = 90
    TREND_CYCLE_DAYS = 30
    TREND_CONFIG = {"ratio_threshold": 3.0, "min_change": 1.0}


# 输出表名映射
TABLE_NAMES = {
    "请购单_清洗后": "stg_purchase_req",
    "采购单_清洗后": "stg_purchase_order",
    "入库单_清洗后": "stg_stock_in",
    "销售出库单_清洗后": "stg_sales_out",
    "current_stock_清洗后": "stg_stock_current",
    "expiry_warning聚合表（物料+批次）": "rpt_expiry_warning",
    "效期-周转表": "rpt_expiry_turnover",
    "自营品库存集中度分析": "rpt_self_operated_concentration",
    "turnover_warning聚合表（物料维度）": "rpt_turnover_warning",
    "trend_warning聚合表（物料维度）": "rpt_trend_warning",
    "物料-warehouse综合风险表": "rpt_warehouse_risk",
    "请购-采购-入库_关联": "rpt_procurement_linked",
}


# ===================== Cleaning Functions =====================
def clean_batch_number(batch_str) -> Optional[str]:
    try:
        if batch_str is None or pd.isna(batch_str):
            return np.nan
    except Exception:
        pass
    batch_str = str(batch_str).strip()
    if (batch_str in ETLConfig.BATCH_CLEAN_RULES or
            batch_str.startswith('无') or batch_str.startswith('批次')):
        return np.nan
    return batch_str


def clean_expiry_date(expiry_str):
    try:
        if expiry_str is None or pd.isna(expiry_str):
            return np.nan
    except Exception:
        pass
    if str(expiry_str).strip() in ETLConfig.EXPIRY_CLEAN_RULES:
        return np.nan
    try:
        return pd.to_datetime(expiry_str).date()
    except Exception:
        return np.nan


def clean_material_code(code) -> str:
    if code is None:
        return ""
    try:
        if pd.isna(code):
            return ""
    except Exception:
        pass
    code_str = str(code).strip()
    code_str = code_str.replace("'", "").replace("‘", "")
    code_str = code_str.replace("（仓）", "").replace("(仓)", "")
    return code_str


def format_date_to_ymd(date_obj):
    if pd.isna(date_obj):
        return np.nan
    try:
        if isinstance(date_obj, (str, int, float)):
            date_dt = pd.to_datetime(date_obj)
        else:
            date_dt = date_obj
        return date_dt.date() if hasattr(date_dt, 'date') else date_dt
    except Exception:
        return np.nan


def safe_divide(a, b):
    if b == 0 or pd.isna(b):
        return 0.0
    return float(a) / float(b)


def calculate_expiry_months(expiry_date):
    try:
        if expiry_date is None or pd.isna(expiry_date):
            return np.nan
    except Exception:
        pass
    try:
        if isinstance(expiry_date, datetime):
            expiry_dt = expiry_date
        elif hasattr(expiry_date, 'date'):
            expiry_dt = datetime.combine(expiry_date, datetime.min.time())
        else:
            expiry_dt = pd.Timestamp(expiry_date)
        delta = relativedelta(expiry_dt, ETLConfig.CURRENT_DATE_DT)
        return float(delta.years * 12 + delta.months)
    except Exception:
        return np.nan


def classify_expiry_status(months) -> str:
    try:
        if months is None or pd.isna(months):
            return "未知"
    except Exception:
        return "未知"
    if not isinstance(months, (int, float, np.integer, np.floating)):
        return "未知"
    if months >= 32: return "效期极佳(32+)"
    elif 28 <= months < 32: return "效期优秀(28-32)"
    elif 24 <= months < 28: return "效期良好(24-28)"
    elif 18 <= months < 24: return "效期一般(18-24)"
    elif 12 <= months < 18: return "效期较差(12-18)"
    elif 6 <= months < 12: return "效期很差(6-12)"
    elif 0 <= months < 6: return "效期临期(0-6)"
    else: return "过期（0-）"


def calculate_inventory_days(available_qty_total: float, sales_90d_total: float):
    if available_qty_total <= 0:
        return np.nan
    try:
        if sales_90d_total <= 0 or pd.isna(sales_90d_total):
            return 999.0
    except Exception:
        if sales_90d_total <= 0:
            return 999.0
    daily_sales = sales_90d_total / ETLConfig.TURNOVER_CYCLE_DAYS
    if daily_sales <= 0:
        return 999.0
    return available_qty_total / daily_sales


def classify_turnover_status(days) -> str:
    try:
        if days is None or pd.isna(days):
            return "无库存数据"
    except Exception:
        return "无库存数据"
    if days >= 999: return "周转高(>90天)"
    if days < 30: return "周转健康(<30天)"
    elif 30 <= days < 60: return "周转正常(30-60天)"
    elif 60 <= days < 90: return "周转偏低(60-90天)"
    else: return "周转高(>90天)"


# ===================== DB Helpers =====================
def _get_self_operated_brands_from_db(db) -> List[str]:
    """从 dim_self_operated_brand 读取自营品牌白名单"""
    try:
        rows = db.execute(text("SELECT brand_name FROM dim_self_operated_brand ORDER BY brand_name")).fetchall()
        brands = [r[0] for r in rows if r[0]]
        if brands:
            return brands
    except Exception as e:
        logger.warning(f"读取自营品牌失败: {e}")
    logger.warning("dim_self_operated_brand 表为空，降级使用硬编码列表")
    return ETLConfig.SELF_OPERATED_BRANDS_FALLBACK


def _save_dataframe_to_db(db, df: pd.DataFrame, table_name: str):
    """将 DataFrame 写入 MySQL（REPLACE INTO）"""
    if df.empty:
        logger.warning(f"{table_name}: 数据为空，跳过写入")
        return
    db.execute(text(f"TRUNCATE TABLE `{table_name}`"))
    db.commit()
    # 只选择数据库表中存在的列
    result = db.execute(text(f"SHOW COLUMNS FROM `{table_name}`"))
    db_columns = [row[0] for row in result.fetchall()]
    df_to_save = df[[col for col in df.columns if col in db_columns]]
    # 用 pandas to_sql 通过 SQLAlchemy engine
    from app.database import main_engine
    df_to_save.to_sql(name=table_name, con=main_engine, if_exists="append", index=False, method="multi", chunksize=5000)
    logger.info(f"写入 {table_name}: {len(df_to_save)} 行 (原始 {len(df)} 行)")


# ===================== Preprocessing =====================
def _clean_excel_rows(df, source_type: str):
    """清理 Excel 垃圾行和合计行"""
    if df.empty:
        return df
    first_cell = str(df.iloc[0, 0]).strip() if len(df) > 0 else ""
    last_cell = str(df.iloc[-1, 0]).strip() if len(df) > 0 else ""
    if source_type == "入库单":
        if first_cell in ("采购入库单列表",):
            df = df.iloc[1:].reset_index(drop=True)
        if last_cell == "合计":
            df = df.iloc[:-1].reset_index(drop=True)
    elif source_type == "销售出库单":
        if first_cell in ("销售出库单列表",):
            df = df.iloc[1:].reset_index(drop=True)
        if last_cell == "合计":
            df = df.iloc[:-1].reset_index(drop=True)
    elif source_type == "current_stock":
        if first_cell == "存量分析头":
            df = df.iloc[1:].reset_index(drop=True)
        if last_cell == "合计":
            df = df.iloc[:-1].reset_index(drop=True)
    return df


def preprocess_data(raw_data: Dict[str, pd.DataFrame]) -> Tuple:
    df_purchase_req = raw_data.get("请购单", pd.DataFrame()).copy()
    df_purchase_order = raw_data.get("采购单", pd.DataFrame()).copy()
    df_stock_in = raw_data.get("入库单", pd.DataFrame()).copy()
    df_sales_out = raw_data.get("销售出库单", pd.DataFrame()).copy()
    df_stock_current = raw_data.get("current_stock", pd.DataFrame()).copy()

    # ERP exported的 Excel 第一行可能是标题行（如"采购入库单列表"），pd.read_excel 把它当列名
    # 真正的列名在数据的第一行，需要提取
    def _fix_header(df, title_keywords):
        if df.empty or len(df) < 2:
            return df
        # 检查第一列的列名是否包含标题关键词
        first_col = str(df.columns[0]).strip()
        if any(kw in first_col for kw in title_keywords):
            new_cols = [str(v).strip() for v in df.iloc[0].values]
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = new_cols
        return df

    df_stock_in = _fix_header(df_stock_in, ["采购入库", "入库单"])
    df_sales_out = _fix_header(df_sales_out, ["销售出库", "出库单"])
    df_stock_current = _fix_header(df_stock_current, ["存量", "现存量"])

    df_stock_in = _clean_excel_rows(df_stock_in, "入库单")
    df_sales_out = _clean_excel_rows(df_sales_out, "销售出库单")
    df_stock_current = _clean_excel_rows(df_stock_current, "current_stock")

    df_stock_in.columns = [col.lower() for col in df_stock_in.columns]
    df_stock_current.columns = [col.lower().replace('*', '').strip() for col in df_stock_current.columns]

    rename_maps = {
        "请购单": {
            "下单日期": "order_date", "渠道对接人": "channel_contact",
            "交货周期": "delivery_cycle", "下单单号": "order_no",
            "是否到货": "is_delivered", "品牌": "brand",
            "推广词": "promotion_tags",
            "商品条码": "material_code", "商品名称": "material_name",
            "渠道": "channel",
            "下单数量": "order_qty", "下单备注": "order_remark",
            "预计交货日期": "expected_delivery_date",
            "实际到货手工登账数量": "actual_manual_stock_qty",
            "特殊情况备注": "special_remark",
        },
        "采购单": {
            "到货日期": "delivery_date", "下单单号": "order_no",
            "商品条码": "material_code", "商品名称": "material_name",
            "工厂交付数量": "factory_delivery_qty",
            "批次号": "batch_no", "限用日期": "expiry_date",
            "提货数量": "pickup_qty", "品牌销售单号": "brand_sales_no",
            "品牌": "brand", "生产日期": "production_date",
            "是否开单": "is_billed", "备注": "remark",
        },
        "入库单": {
            "品牌销售单号": "brand_sales_no", "单据日期": "stock_in_date",
            "单据编号": "doc_no", "审核日期": "audit_date",
            "仓库": "warehouse",
            "物料sku编码": "material_code", "物料sku名称": "material_name",
            "批次号": "batch_no", "有效期至": "expiry_date",
            "数量": "stock_in_qty", "应收数量": "receivable_qty",
            "型号": "model", "备注": "remark",
            "物流单号": "logistics_no", "物流公司": "logistics_company",
        },
        "销售出库单": {
            "单据日期": "doc_date", "单据编号": "doc_no",
            "源头交易类型": "source_tx_type", "交易类型名称": "tx_type_name",
            "客户": "customer", "客户分类": "customer_class",
            "大区经理": "region_manager", "仓库": "warehouse",
            "审核日期": "audit_date",
            "物料编码": "material_code", "物料名称": "material_name",
            "品牌": "brand", "含税金额": "tax_included_amount",
            "批次号": "batch_no",
            "应发数量": "dispatch_qty", "数量": "sales_out_qty",
            "出货渠道": "shipping_channel", "创建人": "creator",
            "已开票数量": "invoiced_qty", "交易类型": "tx_type",
            "审核时间": "audit_time", "备注": "remark",
            "来源单据交易类型": "source_doc_tx_type",
            "入账方式": "entry_method", "含税单价": "tax_included_unit_price",
            "源头单据号": "source_doc_no",
        },
        "current_stock": {
            "仓库": "warehouse", "品牌": "brand",
            "物料sku编码": "material_code", "物料sku名称": "material_name",
            "批号": "batch_no", "生产日期": "production_date",
            "有效期至": "expiry_date", "规格说明": "spec",
            "现存量": "current_stock", "可用量": "available_qty",
            "发货预计出库量": "estimated_shipping_qty",
            "订单预计出库量": "estimated_order_qty",
        },
    }

    for sheet_name, df in zip(
        ["请购单", "采购单", "入库单", "销售出库单", "current_stock"],
        [df_purchase_req, df_purchase_order, df_stock_in, df_sales_out, df_stock_current]
    ):
        rm = rename_maps.get(sheet_name, {})
        df.rename(columns={k: v for k, v in rm.items() if k in df.columns}, inplace=True)

    # Add missing columns for stock_in to match DB schema
    # 注：仅用于中间处理，写入 DB 前会清理掉中文别名列
    if "material_code" in df_stock_in.columns and "物料编码" not in df_stock_in.columns:
        df_stock_in["物料编码"] = df_stock_in["material_code"]
    if "material_name" in df_stock_in.columns and "物料名称" not in df_stock_in.columns:
        df_stock_in["物料名称"] = df_stock_in["material_name"]

    for df in [df_purchase_req, df_purchase_order, df_stock_in, df_sales_out, df_stock_current]:
        seen, keep = {}, []
        for col in df.columns:
            if col not in seen:
                seen[col] = 0
                keep.append(col)
            else:
                seen[col] += 1
                keep.append(f"{col}_{seen[col]}")
        df.columns = keep

    for df in [df_purchase_req, df_purchase_order, df_stock_in, df_sales_out, df_stock_current]:
        if "material_code" in df.columns:
            df["material_code"] = df["material_code"].apply(clean_material_code).astype(str)

    for df in [df_purchase_order, df_stock_in, df_sales_out, df_stock_current]:
        if "batch_no" in df.columns:
            df["batch_no"] = df["batch_no"].apply(clean_batch_number)

    date_fields = {
        "请购单": ["order_date"],
        "采购单": ["delivery_date", "expiry_date"],
        "入库单": ["stock_in_date", "audit_date", "expiry_date"],
        "销售出库单": ["doc_date", "audit_date"],
        "current_stock": ["production_date", "expiry_date"],
    }
    for sheet_name, df in zip(
        ["请购单", "采购单", "入库单", "销售出库单", "current_stock"],
        [df_purchase_req, df_purchase_order, df_stock_in, df_sales_out, df_stock_current]
    ):
        for field in date_fields.get(sheet_name, []):
            if field in df.columns:
                if "expiry_date" in field:
                    df[field] = df[field].apply(clean_expiry_date)
                else:
                    df[field] = df[field].apply(format_date_to_ymd)

    for col, df in [("stock_in_qty", df_stock_in), ("sales_out_qty", df_sales_out)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0.0)

    # expected_delivery_date
    if all(c in df_purchase_req.columns for c in ["order_date", "delivery_cycle"]):
        df_purchase_req["expected_delivery_date"] = df_purchase_req.apply(
            lambda x: x["order_date"] + timedelta(days=x["delivery_cycle"])
            if pd.notna(x["order_date"]) and pd.notna(x["delivery_cycle"]) else None, axis=1)

    return df_purchase_req, df_purchase_order, df_stock_in, df_sales_out, df_stock_current


# ===================== 报告表生成 =====================

def fill_stock_expiry_date(df_stock_current, df_stock_in):
    expiry_mapping = df_stock_in[["material_code", "batch_no", "expiry_date"]].copy()
    expiry_mapping = expiry_mapping.dropna(subset=["batch_no", "expiry_date"])
    expiry_mapping["_dt"] = pd.to_datetime(expiry_mapping["expiry_date"], errors="coerce")
    expiry_mapping = expiry_mapping.sort_values("_dt")
    expiry_mapping = expiry_mapping.groupby(["material_code", "batch_no"], as_index=False)[["expiry_date"]].last()

    df_merged = pd.merge(df_stock_current, expiry_mapping[["material_code", "batch_no", "expiry_date"]],
                         on=["material_code", "batch_no"], how="left", suffixes=("", "_from_in"))
    filled = df_merged["expiry_date"].apply(format_date_to_ymd)
    df_stock_current["expiry_date"].update(filled)
    return df_stock_current


def get_material_sales_trend(df_sales_out, material_code):
    df_m = df_sales_out[df_sales_out["material_code"] == material_code].copy()
    if len(df_m) == 0:
        return [0.0] * 7
    df_m = df_m.dropna(subset=["doc_date"]).copy()
    df_m["doc_date"] = pd.to_datetime(df_m["doc_date"], errors="coerce")

    cd = ETLConfig.CURRENT_DATE
    td = ETLConfig.TREND_CYCLE_DAYS
    c1_end = cd
    c1_start = cd - timedelta(days=td)
    c2_start = c1_start - timedelta(days=td)
    c3_start = c2_start - timedelta(days=td)
    c4_start = c3_start - timedelta(days=td)

    c4 = df_m[(df_m["doc_date"] >= pd.Timestamp(c4_start)) & (df_m["doc_date"] < pd.Timestamp(c3_start))]["sales_out_qty"].sum()
    c3 = df_m[(df_m["doc_date"] >= pd.Timestamp(c3_start)) & (df_m["doc_date"] < pd.Timestamp(c2_start))]["sales_out_qty"].sum()
    c2 = df_m[(df_m["doc_date"] >= pd.Timestamp(c2_start)) & (df_m["doc_date"] < pd.Timestamp(c1_start))]["sales_out_qty"].sum()
    c1 = df_m[(df_m["doc_date"] >= pd.Timestamp(c1_start)) & (df_m["doc_date"] <= pd.Timestamp(c1_end))]["sales_out_qty"].sum()

    sales_90d = [c3, c2, c1]
    total_send_90d = sum(s for s in sales_90d if s > 0)
    total_return_90d = abs(sum(s for s in sales_90d if s < 0))
    total_sales_90d = sum(sales_90d)
    return [c4, c3, c2, c1, total_send_90d, total_return_90d, total_sales_90d]


def classify_trend_status(trend_sales, material_stock_total):
    c3, c2, c1 = trend_sales[1], trend_sales[2], trend_sales[3]
    total_send = trend_sales[4]
    total_return = trend_sales[5]
    return_ratio = safe_divide(total_return, total_send)

    mc = ETLConfig.TREND_CONFIG["min_change"]
    c3 = max(float(c3), mc)
    c2 = max(float(c2), mc)
    c1 = max(float(c1), mc)

    r23 = c2 / c3
    r12 = c1 / c2
    R = ETLConfig.TREND_CONFIG["ratio_threshold"]
    Ri = 1.0 / R
    d23 = c2 - c3
    d12 = c1 - c2

    if d23 > mc and d12 > mc: basic = "持续上升"
    elif d23 > mc and d12 < -mc: basic = "先升后降"
    elif d23 < -mc and d12 > mc: basic = "先降后升"
    elif d23 < -mc and d12 < -mc: basic = "持续下降"
    else: basic = "无明显趋势"

    if basic == "持续上升":
        ts = "迉速攀升" if (r23 >= R or r12 >= R) else "持续攀升"
    elif basic == "先升后降":
        ub = r23 >= R
        db_ = r12 <= Ri
        if ub and db_: ts = "迉速冲高后显著回落"
        elif ub and not db_: ts = "迉速冲高后企稳"
        elif not ub and db_: ts = "冲高后后显著回落"
        else: ts = "正常波动"
    elif basic == "先降后升":
        db_ = r23 <= Ri
        ub = r12 >= R
        if db_ and ub: ts = "大幅下滑后显著攀升"
        elif db_ and not ub: ts = "大幅下滑后企稳"
        elif not db_ and ub: ts = "下滑后显著攀升"
        else: ts = "正常波动"
    elif basic == "持续下降":
        ts = "迉速下滑" if (r23 <= Ri or r12 <= Ri) else "持续下滑"
    else:
        ts = "无明显趋势"
    return ts, return_ratio, c3, c2, c1


def analyze_expiry_warning(df_stock_current, material_brand_mapping, df_sales_out):
    agg = df_stock_current.groupby(["material_code", "material_name", "batch_no", "expiry_date"]).agg(
        material_batch_available_qty=("available_qty", "sum")).reset_index()
    agg = pd.merge(agg, material_brand_mapping[["material_code", "brand", "brand_class"]], on="material_code", how="left")
    agg["brand"] = agg["brand"].fillna("未知brand")
    agg["brand_class"] = agg["brand_class"].fillna("非自营")

    df_sc = df_sales_out.dropna(subset=["doc_date", "batch_no", "material_code"]).copy()
    df_sc["batch_no"] = df_sc["batch_no"].apply(clean_batch_number)
    df_sc = df_sc.dropna(subset=["batch_no"])
    df_sc["doc_date"] = pd.to_datetime(df_sc["doc_date"], errors="coerce")
    r90 = df_sc[df_sc["doc_date"] >= pd.Timestamp(ETLConfig.CURRENT_DATE - timedelta(days=ETLConfig.TURNOVER_CYCLE_DAYS))]
    bs = r90.groupby(["material_code", "batch_no"]).agg(sales_90d=("sales_out_qty", "sum")).reset_index()
    bs["sales_90d"] = pd.to_numeric(bs["sales_90d"], errors="coerce").fillna(0.0)

    agg = pd.merge(agg, bs, on=["material_code", "batch_no"], how="left")
    agg["sales_90d"] = agg["sales_90d"].fillna(0.0)
    agg["inventory_days"] = agg.apply(lambda x: calculate_inventory_days(x["material_batch_available_qty"], x["sales_90d"]), axis=1)
    agg["remaining_expiry_months"] = agg["expiry_date"].apply(calculate_expiry_months)
    agg["expiry_status"] = agg["remaining_expiry_months"].apply(classify_expiry_status)
    agg["expiry_warning"] = agg["remaining_expiry_months"].apply(lambda x: "预警" if (pd.notna(x) and x < 24) else "正常")

    for c in ["material_batch_available_qty", "sales_90d"]:
        agg[c] = agg[c].fillna(0).astype(int)
    agg["inventory_days"] = agg["inventory_days"].fillna(0).round(0).astype(int)

    cols = ["material_code", "material_name", "brand", "brand_class", "batch_no", "expiry_date",
            "material_batch_available_qty", "sales_90d", "inventory_days",
            "remaining_expiry_months", "expiry_status", "expiry_warning"]
    return agg[cols].sort_values(["material_code", "batch_no"]).reset_index(drop=True)


def analyze_expiry_turnover(df_expiry_warning):
    df = df_expiry_warning.groupby(["brand_class", "expiry_status"]).agg(
        available_qty=("material_batch_available_qty", "sum"), sales_90d=("sales_90d", "sum")).reset_index()
    df["turnover_days"] = df.apply(lambda x: safe_divide(x["available_qty"], x["sales_90d"]) * 90, axis=1)
    df["available_qty"] = df["available_qty"].astype(int)
    df["sales_90d"] = df["sales_90d"].astype(int)
    df["turnover_days"] = df["turnover_days"].round(1)
    return df[["brand_class", "expiry_status", "available_qty", "sales_90d", "turnover_days"]].sort_values(["brand_class", "expiry_status"]).reset_index(drop=True)


def analyze_self_operated_stock_concentration(df_expiry_warning):
    df_self = df_expiry_warning[df_expiry_warning["brand_class"] == "自营"].copy()
    if len(df_self) == 0:
        return pd.DataFrame(columns=["material_code", "material_name", "brand", "expiry_status",
                                      "material_batch_available_qty", "stock_ratio", "cumulative_stock_ratio", "sales_90d"])
    agg = df_self.groupby(["material_code", "material_name", "brand", "expiry_status"]).agg(
        material_batch_available_qty=("material_batch_available_qty", "sum"), sales_90d=("sales_90d", "sum")).reset_index()
    total = agg["material_batch_available_qty"].sum()
    agg["stock_ratio"] = (agg["material_batch_available_qty"] / total * 100).round(1).astype(str) + "%"
    agg = agg.sort_values("material_batch_available_qty", ascending=False).reset_index(drop=True)
    agg["cumulative_available_qty"] = agg["material_batch_available_qty"].cumsum()
    agg["cumulative_stock_ratio"] = (agg["cumulative_available_qty"] / total * 100).round(1).astype(str) + "%"
    return agg[["material_code", "material_name", "brand", "expiry_status",
                "material_batch_available_qty", "stock_ratio", "cumulative_stock_ratio", "sales_90d"]].reset_index(drop=True)


def analyze_turnover_warning(df_stock_current, df_sales_out, material_brand_mapping):
    ms = df_stock_current.groupby(["material_code", "material_name"])["available_qty"].sum().reset_index()
    ms.columns = ["material_code", "material_name", "material_available_qty"]
    df_sc = df_sales_out.dropna(subset=["doc_date"]).copy()
    df_sc["doc_date"] = pd.to_datetime(df_sc["doc_date"], errors="coerce")
    r90 = df_sc[df_sc["doc_date"] >= pd.Timestamp(ETLConfig.CURRENT_DATE - timedelta(days=ETLConfig.TURNOVER_CYCLE_DAYS))]
    msl = r90.groupby("material_code")["sales_out_qty"].sum().reset_index()
    msl.columns = ["material_code", "sales_90d"]
    df = pd.merge(ms, msl, on="material_code", how="left").fillna({"sales_90d": 0})
    df = pd.merge(df, material_brand_mapping[["material_code", "brand", "brand_class"]], on="material_code", how="left")
    df["brand"] = df["brand"].fillna("未知brand")
    df["brand_class"] = df["brand_class"].fillna("非自营")
    df["inventory_days"] = df.apply(lambda x: calculate_inventory_days(x["material_available_qty"], x["sales_90d"]), axis=1)
    df["turnover_status"] = df["inventory_days"].apply(classify_turnover_status)
    df["turnover_warning"] = df["inventory_days"].apply(lambda x: "预警" if (pd.notna(x) and (x < 15 or x > 60)) else "正常")
    for c in ["material_available_qty", "sales_90d"]:
        df[c] = df[c].fillna(0).astype(int)
    df["inventory_days"] = df["inventory_days"].fillna(0).round(0).astype(int)
    cols = ["material_code", "material_name", "brand", "brand_class", "material_available_qty",
            "sales_90d", "inventory_days", "turnover_status", "turnover_warning"]
    return df[cols].sort_values("material_code").reset_index(drop=True)


def analyze_trend_warning(df_sales_out, df_stock_current, material_brand_mapping):
    ms = df_stock_current.groupby(["material_code", "material_name"])["available_qty"].sum().reset_index()
    ms.columns = ["material_code", "material_name", "material_available_qty"]
    ms = pd.merge(ms, material_brand_mapping[["material_code", "brand", "brand_class"]], on="material_code", how="left")
    ms["brand"] = ms["brand"].fillna("未知brand")
    ms["brand_class"] = ms["brand_class"].fillna("非自营")

    results = []
    for _, row in ms.iterrows():
        trend = get_material_sales_trend(df_sales_out, row["material_code"])
        ts, rr, c3, c2, c1 = classify_trend_status(trend, row["material_available_qty"])
        w_kw = ["迉速下滑", "持续下滑", "迉速冲高后显著回落",
                "冲高后后显著回落", "大幅下滑后显著攀升", "大幅下滑后企稳"]
        tw = "预警" if any(k in ts for k in w_kw) else "正常"
        results.append({
            "material_code": row["material_code"], "material_name": row["material_name"],
            "brand": row["brand"], "brand_class": row["brand_class"],
            "material_available_qty": row["material_available_qty"],
            "cycle_4_sales": trend[0], "cycle_3_sales": trend[1], "cycle_2_sales": trend[2], "cycle_1_sales": trend[3],
            "total_dispatch_90d": trend[4], "total_return_qty": trend[5], "sales_90d": trend[6],
            "return_ratio": rr, "trend_status": ts, "trend_warning": tw,
        })
    df = pd.DataFrame(results)
    for c in ["material_available_qty", "cycle_4_sales", "cycle_3_sales", "cycle_2_sales",
              "cycle_1_sales", "total_dispatch_90d", "total_return_qty", "sales_90d"]:
        df[c] = df[c].fillna(0).astype(int)
    df["return_ratio"] = df["return_ratio"].astype(float).apply(lambda x: f"{x*100:.1f}%")
    cols = ["material_code", "material_name", "brand", "brand_class", "material_available_qty",
            "cycle_4_sales", "cycle_3_sales", "cycle_2_sales", "cycle_1_sales",
            "total_dispatch_90d", "total_return_qty", "sales_90d", "return_ratio", "trend_status", "trend_warning"]
    return df[cols].sort_values("material_code").reset_index(drop=True)


def analyze_material_warehouse_risk(df_expiry, df_turnover, df_trend, df_stock_current, material_brand_mapping):
    df_wh = df_stock_current[["warehouse", "material_code", "material_name"]].drop_duplicates()
    df_wh = pd.merge(df_wh, material_brand_mapping[["material_code", "brand", "brand_class"]], on="material_code", how="left")
    df_wh["brand"] = df_wh["brand"].fillna("未知brand")
    df_wh["brand_class"] = df_wh["brand_class"].fillna("非自营")
    me = df_expiry.groupby("material_code")["expiry_warning"].agg(
        expiry_warning_status=lambda x: "预警" if (x == "预警").any() else "正常").reset_index()
    df_wh = pd.merge(df_wh, me, on="material_code", how="left")
    df_wh = pd.merge(df_wh, df_turnover[["material_code", "turnover_warning", "inventory_days", "material_available_qty"]], on="material_code", how="left")
    df_wh = pd.merge(df_wh, df_trend[["material_code", "trend_warning", "trend_status", "return_ratio"]], on="material_code", how="left")

    def get_risk(row):
        cnt = sum(1 for k in ["expiry_warning_status", "turnover_warning", "trend_warning"] if row.get(k) == "预警")
        return "高风险" if cnt >= 2 else ("中风险" if cnt == 1 else "低风险")
    df_wh["risk_level"] = df_wh.apply(get_risk, axis=1)
    cols = ["warehouse", "material_code", "material_name", "brand", "brand_class", "material_available_qty",
            "expiry_warning_status", "inventory_days", "turnover_warning", "return_ratio",
            "trend_status", "trend_warning", "risk_level"]
    return df_wh[cols].sort_values(["warehouse", "material_code"]).reset_index(drop=True)


def link_procurement_process(df_req, df_order, df_in):
    oa = df_order.groupby(["order_no", "material_code"]).agg(
        cumulative_factory_delivery_qty=("factory_delivery_qty", "sum"),
        cumulative_pickup_qty=("pickup_qty", "sum"),
        first_delivery_date=("delivery_date", "min"),
        last_delivery_date=("delivery_date", "max")).reset_index()
    for c in ["cumulative_factory_delivery_qty", "cumulative_pickup_qty"]:
        oa[c] = pd.to_numeric(oa[c], errors="coerce").fillna(0.0)

    dfi = df_in.copy()
    dfi["stock_in_qty"] = pd.to_numeric(dfi["stock_in_qty"], errors="coerce").fillna(0.0)
    ia = dfi.groupby(["brand_sales_no", "material_code"]).agg(
        cumulative_stock_in_qty=("stock_in_qty", "sum"),
        first_stock_in_date=("stock_in_date", "min")).reset_index()

    ri = pd.merge(df_req, oa, on=["order_no", "material_code"], how="left")
    ob = df_order[["order_no", "material_code", "brand_sales_no"]].drop_duplicates()
    ri = pd.merge(ri, ob, on=["order_no", "material_code"], how="left")
    ri = pd.merge(ri, ia, on=["brand_sales_no", "material_code"], how="left")

    ri["order_qty"] = pd.to_numeric(ri["order_qty"], errors="coerce").fillna(0.0)
    for c in ["cumulative_factory_delivery_qty", "cumulative_pickup_qty", "cumulative_stock_in_qty"]:
        ri[c] = ri[c].fillna(0.0)

    ri["procurement_delivery_rate"] = ri.apply(lambda x: f"{safe_divide(x['cumulative_factory_delivery_qty'], x['order_qty'])*100:.1f}%", axis=1)
    ri["procurement_pickup_rate"] = ri.apply(lambda x: f"{safe_divide(x['cumulative_pickup_qty'], x['order_qty'])*100:.1f}%", axis=1)
    ri["stock_in_complete_rate"] = ri.apply(lambda x: f"{safe_divide(x['cumulative_stock_in_qty'], x['order_qty'])*100:.1f}%", axis=1)
    ri["pending_delivery_qty"] = ri.apply(lambda x: max(x["order_qty"] - x["cumulative_factory_delivery_qty"], 0), axis=1)
    ri["pending_pickup_qty"] = ri.apply(lambda x: max(x["cumulative_factory_delivery_qty"] - x["cumulative_pickup_qty"], 0), axis=1)
    ri["pending_stock_in_qty"] = ri.apply(lambda x: max(x["cumulative_pickup_qty"] - x["cumulative_stock_in_qty"], 0), axis=1)
    ri["offline_pending_stock_in_qty"] = ri.apply(lambda x: max(x["cumulative_factory_delivery_qty"] - x["cumulative_stock_in_qty"], 0), axis=1)

    for f in ["delivery_cycle", "order_qty", "cumulative_factory_delivery_qty", "cumulative_pickup_qty",
              "cumulative_stock_in_qty", "pending_delivery_qty", "pending_pickup_qty",
              "pending_stock_in_qty", "offline_pending_stock_in_qty"]:
        if f in ri.columns:
            ri[f] = ri[f].fillna(0).astype(int)
    return ri


def build_sales_out_wide(db):
    """从 stg_sales_out 补全维度后写入 rpt_sales_out_wide"""
    from app.database import main_engine
    logger.info("===== 销售出库宽表补全开始 =====")

    df_sales = pd.read_sql("SELECT * FROM stg_sales_out", main_engine)
    if df_sales.empty:
        logger.warning("stg_sales_out 为空，跳过宽表构建")
        return

    # customer 筛选
    try:
        saved = db.execute(text("SELECT filter_value FROM dim_filter_config WHERE filter_type='customer'")).fetchall()
        saved_customers = [r[0] for r in saved]
        if saved_customers:
            df_sales = df_sales[df_sales["customer"].isin(saved_customers)]
    except Exception:
        pass

    df_product = pd.read_sql("SELECT material_code, category, abc_class, lifecycle_status, custom_flag, promoted_flag FROM dim_product_attr", main_engine)
    df_customer = pd.read_sql("SELECT customer_name, region, account_manager, channel FROM dim_customer", main_engine)

    df_sales["material_code"] = df_sales["material_code"].astype(str)
    df_sales["customer"] = df_sales["customer"].astype(str)
    df_product["material_code"] = df_product["material_code"].astype(str)
    df_customer["customer_name"] = df_customer["customer_name"].astype(str)

    df_customer["_has_mgr"] = df_customer["account_manager"].notna().astype(int)
    df_customer = df_customer.sort_values("_has_mgr", ascending=False).drop_duplicates(subset="customer_name", keep="first")
    df_customer.drop(columns=["_has_mgr"], inplace=True)

    df_sales = df_sales.merge(df_product[["material_code", "category", "abc_class", "lifecycle_status", "custom_flag", "promoted_flag"]],
                              on="material_code", how="left")
    df_sales = df_sales.merge(df_customer[["customer_name", "region", "account_manager", "channel"]],
                              left_on="customer", right_on="customer_name", how="left")
    if "customer_name" in df_sales.columns:
        df_sales.drop(columns=["customer_name"], inplace=True)
    df_sales["creation_time"] = datetime.now()

    _save_dataframe_to_db(db, df_sales, "rpt_sales_out_wide")
    logger.info(f"✅ rpt_sales_out_wide 写入成功: {len(df_sales)} 行")

    # 创建复合索引（如果不存在），加速 material_code + doc_date 查询
    # material_code 是 TEXT 类型，需用前缀索引
    try:
        existing = db.execute(text(
            "SHOW INDEX FROM rpt_sales_out_wide WHERE Key_name = 'idx_wide_mc_docdate'"
        )).fetchone()
        if not existing:
            db.execute(text("""
                CREATE INDEX idx_wide_mc_docdate
                ON rpt_sales_out_wide (material_code(50), doc_date)
            """))
            db.commit()
            logger.info("✅ idx_wide_mc_docdate 索引创建成功")
        else:
            logger.info("✅ idx_wide_mc_docdate 索引已存在")
    except Exception as e:
        logger.warning(f"索引操作失败（不影响数据写入）: {e}")


def _auto_update_dim_after_etl(db):
    """ETL 后自动更新 dim_product_attr"""
    from app.services.data_service import sync_product_dimension_from_stock_in, update_lifecycle_status
    try:
        r1 = sync_product_dimension_from_stock_in(db)
        logger.info(f"同步物料维度: inserted={r1.get('inserted')}, updated={r1.get('updated')}")
    except Exception as e:
        logger.warning(f"sync_product_dimension_from_stock_in 失败: {e}")
    try:
        r2 = update_lifecycle_status(db)
        logger.info(f"更新生命周期状态: {r2}")
    except Exception as e:
        logger.warning(f"update_lifecycle_status 失败: {e}")


# ===================== 主 ETL 执行 =====================
def run_etl(raw_data: Dict[str, pd.DataFrame], db, current_date=None) -> Dict:
    """
    执行全量 ETL，结果写入 MySQL，包括：
    - 5 张 STG 表
    - 7 张 RPT 表
    - rpt_sales_out_wide
    - dim_product_attr 自动刷新
    """
    if current_date:
        cd = current_date.date() if isinstance(current_date, datetime) else current_date
        ETLConfig.CURRENT_DATE = cd
        ETLConfig.CURRENT_DATE_DT = datetime.combine(cd, datetime.min.time())

    logger.info("===== 开始 ETL =====")

    # 预处理
    df_req, df_order, df_in, df_sales, df_stock = preprocess_data(raw_data)

    # 品牌分类（从 DB 读取）
    if "brand" in df_stock.columns:
        df_stock["brand"] = df_stock["brand"].astype(str).str.strip()
        self_brands = _get_self_operated_brands_from_db(db)
        df_stock["brand_class"] = df_stock["brand"].apply(lambda x: "自营" if x in self_brands else "非自营")

    # 补全 expiry_date
    df_stock_filled = fill_stock_expiry_date(df_stock, df_in)

    # 生成 7 张报表
    material_brand_mapping = df_stock_filled[["material_code", "brand", "brand_class"]].drop_duplicates(subset=["material_code"], keep="first")
    df_expiry = analyze_expiry_warning(df_stock_filled, material_brand_mapping, df_sales)
    df_et = analyze_expiry_turnover(df_expiry)
    df_conc = analyze_self_operated_stock_concentration(df_expiry)
    df_turn = analyze_turnover_warning(df_stock_filled, df_sales, material_brand_mapping)
    df_trend = analyze_trend_warning(df_sales, df_stock_filled, material_brand_mapping)
    df_risk = analyze_material_warehouse_risk(df_expiry, df_turn, df_trend, df_stock_filled, material_brand_mapping)
    df_proc = link_procurement_process(df_req, df_order, df_in)

    # model 字段追加
    if "model" in df_in.columns:
        mm = df_in[["material_code", "model"]].dropna(subset=["material_code"]).drop_duplicates(subset=["material_code"], keep="first")
        mm["material_code"] = mm["material_code"].astype(str)
        for key, df in [("rpt_expiry_warning", df_expiry), ("rpt_turnover_warning", df_turn),
                        ("rpt_trend_warning", df_trend), ("rpt_warehouse_risk", df_risk),
                        ("rpt_procurement_linked", df_proc)]:
            if "material_code" in df.columns:
                df["material_code"] = df["material_code"].astype(str)
                merged = df.merge(mm, on="material_code", how="left")
                for col in df.columns:
                    df[col] = merged[col]

    # 写入 MySQL
    tables = {
        "请购单_清洗后": df_req,
        "采购单_清洗后": df_order,
        "入库单_清洗后": df_in,
        "销售出库单_清洗后": df_sales,
        "current_stock_清洗后": df_stock_filled,
        "expiry_warning聚合表（物料+批次）": df_expiry,
        "效期-周转表": df_et,
        "自营品库存集中度分析": df_conc,
        "turnover_warning聚合表（物料维度）": df_turn,
        "trend_warning聚合表（物料维度）": df_trend,
        "物料-warehouse综合风险表": df_risk,
        "请购-采购-入库_关联": df_proc,
    }

    for sheet_name, df in tables.items():
        table_name = TABLE_NAMES[sheet_name]
        try:
            _save_dataframe_to_db(db, df, table_name)
        except Exception as e:
            logger.error(f"写入 {table_name} 失败: {e}")
            raise

    # 宽表
    try:
        build_sales_out_wide(db)
    except Exception as e:
        logger.error(f"build_sales_out_wide 失败: {e}")

    # dim 自动刷新
    _auto_update_dim_after_etl(db)

    summary = {
        "expiry_warning": df_expiry["expiry_warning"].value_counts().to_dict() if len(df_expiry) else {},
        "turnover_warning": df_turn["turnover_warning"].value_counts().to_dict() if len(df_turn) else {},
        "trend_warning": df_trend["trend_warning"].value_counts().to_dict() if len(df_trend) else {},
        "综合风险": df_risk["risk_level"].value_counts().to_dict() if len(df_risk) else {},
    }

    logger.info("===== ETL 完成 =====")
    return {"summary": summary}
