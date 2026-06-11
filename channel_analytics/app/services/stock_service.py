"""
库存分析服务
提供库存集中度、效期、周转等分析功能
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db_context

logger = logging.getLogger(__name__)


def _apply_stock_filters(tables: Dict[str, pd.DataFrame],
                         brand_class: Optional[str] = None,
                         warehouse: Optional[str] = None,
                         model: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """对库存相关表应用全局筛选器"""
    if not any([brand_class, warehouse, model]):
        return tables
    result = {}
    for name, df in tables.items():
        if df.empty:
            result[name] = df
            continue
        filtered = df
        if brand_class and "brand_class" in filtered.columns:
            filtered = filtered[filtered["brand_class"] == brand_class]
        if warehouse and "warehouse" in filtered.columns:
            filtered = filtered[filtered["warehouse"] == warehouse]
        if model and "model" in filtered.columns:
            filtered = filtered[filtered["model"] == model]
        result[name] = filtered.reset_index(drop=True)
    return result


# ===================== 数据加载 =====================
def load_stock_tables(db: Session) -> Dict[str, pd.DataFrame]:
    """
    加载库存分析相关的所有数据表

    Args:
        db: Database session

    Returns:
        Dictionary of DataFrames keyed by table name
    """
    tables = {}
    table_names = [
        "stg_stock_current",
        "rpt_turnover_warning",
        "rpt_expiry_warning",
        "rpt_trend_warning",
        "rpt_procurement_linked",
        "stg_stock_in",
    ]

    for name in table_names:
        try:
            result = db.execute(text(f"SELECT * FROM `{name}`"))
            columns = result.keys()
            data = result.fetchall()
            if data:
                tables[name] = pd.DataFrame(data, columns=columns)
            else:
                tables[name] = pd.DataFrame()
        except Exception as e:
            logger.warning(f"Failed to load table {name}: {e}")
            tables[name] = pd.DataFrame()

    return tables


# ===================== KPI 指标计算 =====================
def get_kpi_metrics(db: Session, brand_class: Optional[str] = None,
                    warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    计算库存分析的7个KPI指标

    Args:
        db: Database session

    Returns:
        Dictionary with 7 KPI metrics
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)

    df_stock = tables.get("stg_stock_current", pd.DataFrame())
    df_turn = tables.get("rpt_turnover_warning", pd.DataFrame())
    df_proc = tables.get("rpt_procurement_linked", pd.DataFrame())

    # 库存数量
    total_stock = 0
    if "available_qty" in df_stock.columns and not df_stock.empty:
        total_stock = int(df_stock["available_qty"].sum())

    # 90天净出货数量
    total_90d_sales = 0
    if "sales_90d" in df_turn.columns and not df_turn.empty:
        total_90d_sales = int(df_turn["sales_90d"].sum())

    # 库存天数
    inventory_days = None
    if total_stock > 0 and total_90d_sales > 0:
        inventory_days = round(total_stock / total_90d_sales * 90, 1)

    # 待入库数量
    total_pending_in = 0
    if "pending_stock_in_qty" in df_proc.columns and not df_proc.empty:
        total_pending_in = int(df_proc["pending_stock_in_qty"].sum())

    # 90天不动销库存数量
    no_sales_stock = 0
    if "sales_90d" in df_turn.columns and "material_available_qty" in df_turn.columns and not df_turn.empty:
        no_sales_stock = int(df_turn[df_turn["sales_90d"] == 0]["material_available_qty"].sum())

    # 在库SKU数量
    in_stock_skus = 0
    if "available_qty" in df_stock.columns and "material_code" in df_stock.columns and not df_stock.empty:
        in_stock_skus = int(df_stock[df_stock["available_qty"] > 0]["material_code"].nunique())

    # 90天不动销SKU数量
    no_sales_skus = 0
    if "sales_90d" in df_turn.columns and "material_code" in df_turn.columns and not df_turn.empty:
        no_sales_skus = int(df_turn[df_turn["sales_90d"] == 0]["material_code"].nunique())

    return {
        "total_stock": total_stock,
        "total_90d_sales": total_90d_sales,
        "inventory_days": inventory_days,
        "total_pending_in": total_pending_in,
        "no_sales_stock": no_sales_stock,
        "in_stock_skus": in_stock_skus,
        "no_sales_skus": no_sales_skus,
    }


# ===================== 帕累托数据 =====================
def get_pareto_data(
    db: Session,
    threshold: float = 80.0,
    by_batch: bool = False,
    brand_class: Optional[str] = None,
    warehouse: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict:
    """
    计算帕累托图数据

    Args:
        db: Database session
        threshold: 累计占比阈值，默认80%
        by_batch: 是否按批次维度计算

    Returns:
        Dictionary with Pareto chart data
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)
    df_stock = tables.get("stg_stock_current", pd.DataFrame())

    if df_stock.empty:
        return {
            "items": [],
            "total_count": 0,
            "filtered_count": 0,
            "total_quantity": 0,
        }

    # 过滤有效数据
    df = df_stock[
        df_stock["material_code"].notna() &
        (df_stock["available_qty"] > 0)
    ].copy()

    if df.empty:
        return {
            "items": [],
            "total_count": 0,
            "filtered_count": 0,
            "total_quantity": 0,
        }

    df["available_qty"] = pd.to_numeric(df["available_qty"], errors="coerce").fillna(0)

    if by_batch:
        # 按物料+批次维度聚合
        df["batch_no"] = df["batch_no"].fillna("未知")
        df["expiry_status"] = df.get("expiry_status", pd.Series(["未知"] * len(df)))
        df["expiry_status"] = df["expiry_status"].fillna("未知")

        agg = df.groupby(
            ["material_code", "material_name", "batch_no", "expiry_status"],
            as_index=False
        )["available_qty"].sum()
        agg = agg[agg["available_qty"] > 0].sort_values(
            "available_qty", ascending=False
        ).reset_index(drop=True)

        # 计算累计
        total = agg["available_qty"].sum()
        agg["累计available_qty"] = agg["available_qty"].cumsum()
        agg["累计占比"] = agg["累计available_qty"] / total * 100

        # 组合标签
        agg["label"] = (
            agg["material_name"].fillna("未知").astype(str) +
            " (" + agg["expiry_status"].astype(str) + ")"
        )
    else:
        # 按物料维度聚合（不考虑批次）
        agg = df.groupby(
            ["material_code", "material_name"],
            as_index=False
        )["available_qty"].sum()
        agg["material_name"] = agg["material_name"].fillna("未知").astype(str)
        agg = agg.sort_values("available_qty", ascending=False).reset_index(drop=True)

        # 计算累计
        total = agg["available_qty"].sum()
        agg["累计available_qty"] = agg["available_qty"].cumsum()
        agg["累计占比"] = agg["累计available_qty"] / total * 100
        agg["label"] = agg["material_name"]

    # 过滤阈值内的数据
    filtered = agg[agg["累计占比"] <= threshold].reset_index(drop=True)

    return {
        "items": filtered.to_dict(orient="records"),
        "total_count": len(agg),
        "filtered_count": len(filtered),
        "total_quantity": int(total),
        "threshold": threshold,
    }


# ===================== 效期×周转矩阵 =====================
def get_expiry_turnover_matrix(db: Session, brand_class: Optional[str] = None, warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    计算效期×周转矩阵数据

    Args:
        db: Database session

    Returns:
        Dictionary with expiry-turnover matrix data
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)
    df_exp = tables.get("rpt_expiry_warning", pd.DataFrame())

    if df_exp.empty:
        return {
            "ranges": [],
            "total_available": 0,
            "total_sales_90d": 0,
        }

    # 效期区间定义
    def expiry_bin(months):
        if pd.isna(months):
            return "无数据"
        if months < 6:
            return "[0-6)"
        elif months < 12:
            return "[6-12)"
        elif months < 18:
            return "[12-18)"
        elif months < 24:
            return "[18-24)"
        elif months < 28:
            return "[24-28)"
        elif months < 32:
            return "[28-32)"
        else:
            return "[32+)"

    df = df_exp.copy()

    # 确保必要的列存在
    if "remaining_expiry_months" not in df.columns:
        return {"ranges": [], "total_available": 0, "total_sales_90d": 0}

    if "material_batch_available_qty" not in df.columns:
        if "available_qty" in df.columns:
            df["material_batch_available_qty"] = df["available_qty"]
        else:
            return {"ranges": [], "total_available": 0, "total_sales_90d": 0}

    if "sales_90d" not in df.columns:
        df["sales_90d"] = 0

    df["expiry_range"] = df["remaining_expiry_months"].apply(expiry_bin)

    # 按效期区间聚合
    df_grp = df.groupby("expiry_range").agg(
        available_qty=("material_batch_available_qty", "sum"),
        sales_90d=("sales_90d", "sum")
    ).reset_index()

    # 计算加权周转天数
    df_grp["turnover_days"] = df_grp.apply(
        lambda r: round(r["available_qty"] / r["sales_90d"] * 90, 1)
        if r["sales_90d"] > 0 else 999,
        axis=1
    )

    # 按固定顺序排列
    order = ["[0-6)", "[6-12)", "[12-18)", "[18-24)", "[24-28)", "[28-32)", "[32+)", "无数据"]
    df_grp["expiry_range"] = pd.Categorical(
        df_grp["expiry_range"], categories=order, ordered=True
    )
    df_grp = df_grp.sort_values("expiry_range").reset_index(drop=True)

    return {
        "ranges": df_grp.to_dict(orient="records"),
        "total_available": int(df_grp["available_qty"].sum()),
        "total_sales_90d": int(df_grp["sales_90d"].sum()),
    }


# ===================== 不动销数据 =====================
def get_no_sales_data(db: Session, days: int = 30, brand_class: Optional[str] = None, warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    计算不动销数据分类

    Args:
        db: Database session
        days: 不动销天数阈值，默认30天

    Returns:
        Dictionary with no-sales classification data
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)
    df_trend = tables.get("rpt_trend_warning", pd.DataFrame())

    if df_trend.empty:
        return {
            "categories": [],
            "total_stock": 0,
            "total_skus": 0,
        }

    # 确保必要的列存在
    required_cols = ["cycle_1_sales", "cycle_2_sales", "cycle_3_sales", "cycle_4_sales"]
    if not all(col in df_trend.columns for col in required_cols):
        return {
            "categories": [],
            "total_stock": 0,
            "total_skus": 0,
        }

    if "material_available_qty" not in df_trend.columns:
        if "available_qty" in df_trend.columns:
            df_trend["material_available_qty"] = df_trend["available_qty"]
        else:
            return {
                "categories": [],
                "total_stock": 0,
                "total_skus": 0,
            }

    df = df_trend.copy()

    # 转换为数值
    for col in ["cycle_1_sales", "cycle_2_sales", "cycle_3_sales", "cycle_4_sales"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["material_available_qty"] = pd.to_numeric(
        df["material_available_qty"], errors="coerce"
    ).fillna(0)

    c1 = df["cycle_1_sales"]
    c2 = df["cycle_2_sales"]
    c3 = df["cycle_3_sales"]
    c4 = df["cycle_4_sales"]

    # 定义分类条件
    cond_30_no = (c1 == 0) & (c2 != 0)
    cond_60_no = (c1 == 0) & (c2 == 0) & (c3 != 0)
    cond_90_no = (c1 == 0) & (c2 == 0) & (c3 == 0) & (c4 != 0)
    cond_180_no = (c1 == 0) & (c2 == 0) & (c3 == 0) & (c4 == 0)
    cond_30_active = c1 > 0

    rows = []
    for label, cond in [
        ("30天内动销产品", cond_30_active),
        ("30-60天动销产品", cond_30_no),
        ("60-90天动销产品", cond_60_no),
        ("90-180天动销产品", cond_90_no),
        ("180天以上不动销产品", cond_180_no),
    ]:
        sub = df[cond]
        stock_qty = int(sub["material_available_qty"].sum())
        sku_count = int(sub["material_code"].nunique())
        c1_sum = int(sub["cycle_1_sales"].sum())
        c2_sum = int(sub["cycle_2_sales"].sum())
        c3_sum = int(sub["cycle_3_sales"].sum())
        c4_sum = int(sub["cycle_4_sales"].sum())

        # 计算周转天数
        if label in ("30-60天动销产品", "60-90天动销产品"):
            ref = c1_sum + c2_sum + c3_sum
            turnover = round(stock_qty / ref * 90, 1) if ref > 0 else None
        elif label == "90-180天动销产品":
            ref = c1_sum + c2_sum + c3_sum + c4_sum
            turnover = round(stock_qty / ref * 180, 1) if ref > 0 else None
        elif label == "180天以上不动销产品":
            turnover = None
        else:
            ref = c1_sum + c2_sum + c3_sum
            turnover = round(stock_qty / ref * 90, 1) if ref > 0 else None

        rows.append({
            "分类": label,
            "库存数量": stock_qty,
            "SKU数量": sku_count,
            "周转天数": turnover,
        })

    return {
        "categories": rows,
        "total_stock": int(sum(r["库存数量"] for r in rows)),
        "total_skus": int(sum(r["SKU数量"] for r in rows)),
        "days_threshold": days,
    }


# ===================== 库存汇总数据 =====================
def get_stock_summary_data(db: Session, brand_class: Optional[str] = None, warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    获取库存汇总数据

    Args:
        db: Database session

    Returns:
        Dictionary with stock summary data
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)

    df_stock = tables.get("stg_stock_current", pd.DataFrame())
    df_exp = tables.get("rpt_expiry_warning", pd.DataFrame())
    df_turn = tables.get("rpt_turnover_warning", pd.DataFrame())
    df_trend = tables.get("rpt_trend_warning", pd.DataFrame())

    summary = {
        "total_records": len(df_stock),
        "expiry_warning_count": 0,
        "turnover_warning_count": 0,
        "trend_warning_count": 0,
        "by_brand_class": {},
        "by_warehouse": {},
        "by_expiry_status": {},
        "by_turnover_status": {},
    }

    # 品牌分类统计
    if "brand_class" in df_stock.columns and not df_stock.empty:
        brand_stats = df_stock.groupby("brand_class").agg(
            sku_count=("material_code", "nunique"),
            total_qty=("available_qty", "sum")
        ).to_dict()
        summary["by_brand_class"] = brand_stats

    # 仓库统计
    if "warehouse" in df_stock.columns and not df_stock.empty:
        warehouse_stats = df_stock.groupby("warehouse").agg(
            sku_count=("material_code", "nunique"),
            total_qty=("available_qty", "sum")
        ).to_dict()
        summary["by_warehouse"] = warehouse_stats

    # 效期预警统计
    if "expiry_warning" in df_exp.columns and not df_exp.empty:
        summary["expiry_warning_count"] = int(
            (df_exp["expiry_warning"] == "预警").sum()
        )
        expiry_stats = df_exp.groupby("expiry_status").agg(
            sku_count=("material_code", "nunique"),
            total_qty=("material_batch_available_qty", "sum")
        ).to_dict()
        summary["by_expiry_status"] = expiry_stats

    # 周转预警统计
    if "turnover_warning" in df_turn.columns and not df_turn.empty:
        summary["turnover_warning_count"] = int(
            (df_turn["turnover_warning"] == "预警").sum()
        )
        turnover_stats = df_turn.groupby("turnover_status").agg(
            sku_count=("material_code", "nunique"),
            total_qty=("material_available_qty", "sum")
        ).to_dict()
        summary["by_turnover_status"] = turnover_stats

    # 趋势预警统计
    if "trend_warning" in df_trend.columns and not df_trend.empty:
        summary["trend_warning_count"] = int(
            (df_trend["trend_warning"] == "预警").sum()
        )

    return summary


# ===================== 批次维度数据 =====================
def get_batch_analysis_data(db: Session, n_show: int = 50, brand_class: Optional[str] = None, warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    获取批次维度分析数据

    Args:
        db: Database session
        n_show: 显示数量

    Returns:
        Dictionary with batch analysis data
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)
    df_stock = tables.get("stg_stock_current", pd.DataFrame())

    if df_stock.empty:
        return {"items": [], "total_count": 0}

    # 过滤有效数据
    df = df_stock[
        df_stock["material_code"].notna() &
        df_stock["batch_no"].notna() &
        (df_stock["available_qty"] > 0)
    ].copy()

    if df.empty:
        return {"items": [], "total_count": 0}

    df["available_qty"] = pd.to_numeric(df["available_qty"], errors="coerce").fillna(0)

    # 按物料维度聚合
    agg = df.groupby(["material_code", "material_name"], as_index=False).agg(
        total_available_qty=("available_qty", "sum"),
        batch_count=("batch_no", "nunique")
    ).sort_values("total_available_qty", ascending=False).reset_index(drop=True)

    # 限制数量
    agg = agg.head(n_show)

    return {
        "items": agg.to_dict(orient="records"),
        "total_count": len(agg),
    }


# ===================== 效期状态分布 =====================
def get_expiry_status_distribution(db: Session, brand_class: Optional[str] = None, warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    获取效期状态分布数据

    Args:
        db: Database session

    Returns:
        Dictionary with expiry status distribution
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)
    df_exp = tables.get("rpt_expiry_warning", pd.DataFrame())

    if df_exp.empty:
        return {"distribution": [], "total_stock": 0, "total_skus": 0}

    if "expiry_status" not in df_exp.columns:
        return {"distribution": [], "total_stock": 0, "total_skus": 0}

    grp = df_exp.groupby("expiry_status").agg(
        库存数量=("material_batch_available_qty", "sum"),
        SKU数量=("material_code", "nunique")
    ).reset_index()

    # 按固定顺序排列
    order = [
        "效期极佳(32+)", "效期优秀(28-32)", "效期良好(24-28)", "效期一般(18-24)",
        "效期较差(12-18)", "效期很差(6-12)", "效期临期(0-6)", "过期（0-）", "未知"
    ]
    grp["expiry_status"] = pd.Categorical(
        grp["expiry_status"], categories=order, ordered=True
    )
    grp = grp.sort_values("expiry_status").reset_index(drop=True)

    return {
        "distribution": grp.to_dict(orient="records"),
        "total_stock": int(grp["库存数量"].sum()),
        "total_skus": int(grp["SKU数量"].sum()),
    }


# ===================== 周转状态分布 =====================
def get_turnover_status_distribution(db: Session, brand_class: Optional[str] = None, warehouse: Optional[str] = None, model: Optional[str] = None) -> Dict:
    """
    获取周转状态分布数据

    Args:
        db: Database session

    Returns:
        Dictionary with turnover status distribution
    """
    tables = load_stock_tables(db)
    tables = _apply_stock_filters(tables, brand_class, warehouse, model)
    df_turn = tables.get("rpt_turnover_warning", pd.DataFrame())

    if df_turn.empty:
        return {"distribution": [], "total_stock": 0, "total_skus": 0}

    if "turnover_status" not in df_turn.columns:
        return {"distribution": [], "total_stock": 0, "total_skus": 0}

    grp = df_turn.groupby("turnover_status").agg(
        库存数量=("material_available_qty", "sum"),
        SKU数量=("material_code", "nunique")
    ).reset_index(drop=True)

    return {
        "distribution": grp.to_dict(orient="records"),
        "total_stock": int(grp["库存数量"].sum()),
        "total_skus": int(grp["SKU数量"].sum()),
    }
