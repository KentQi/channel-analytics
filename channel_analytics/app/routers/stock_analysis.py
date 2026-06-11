"""
库存分析 API 路由 — 支持全局筛选器 (brand_class/warehouse/model)
"""
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.services.stock_service import (
    get_kpi_metrics,
    get_pareto_data,
    get_expiry_turnover_matrix,
    get_no_sales_data,
    get_stock_summary_data,
    get_batch_analysis_data,
    get_expiry_status_distribution,
    get_turnover_status_distribution,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stock", tags=["stock"])


def _filter_params(
    brand_class: Optional[str] = Query(None, description="品牌分类筛选: 自营/非自营"),
    warehouse: Optional[str] = Query(None, description="仓库筛选"),
    model: Optional[str] = Query(None, description="型号筛选"),
):
    return {"brand_class": brand_class, "warehouse": warehouse, "model": model}


@router.get("/kpis")
def fetch_kpis(
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        kpis = get_kpi_metrics(db, **filters)
        return {"success": True, "data": kpis}
    except Exception as e:
        logger.error(f"Failed to fetch KPIs: {e}")
        return {"success": False, "error": str(e), "data": {
            "total_stock": 0, "total_90d_sales": 0, "inventory_days": None,
            "total_pending_in": 0, "no_sales_stock": 0, "in_stock_skus": 0, "no_sales_skus": 0,
        }}


@router.get("/pareto")
def fetch_pareto(
    threshold: float = Query(80, ge=0, le=100),
    by_batch: bool = Query(False),
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = get_pareto_data(db, threshold=threshold, by_batch=by_batch, **filters)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"items": [], "total_count": 0, "filtered_count": 0, "total_quantity": 0}}


@router.get("/expiry-turnover-matrix")
def fetch_expiry_turnover_matrix(
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return {"success": True, "data": get_expiry_turnover_matrix(db, **filters)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"ranges": [], "total_available": 0, "total_sales_90d": 0}}


@router.get("/no-sales")
def fetch_no_sales(
    days: int = Query(30, ge=30, le=180),
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return {"success": True, "data": get_no_sales_data(db, days=days, **filters)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"categories": [], "total_stock": 0, "total_skus": 0}}


@router.get("/summary")
def fetch_stock_summary(
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return {"success": True, "data": get_stock_summary_data(db, **filters)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {
            "total_records": 0, "expiry_warning_count": 0, "turnover_warning_count": 0,
            "trend_warning_count": 0, "by_brand_class": {}, "by_warehouse": {},
        }}


@router.get("/batch-analysis")
def fetch_batch_analysis(
    n_show: int = Query(50, ge=1, le=200),
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return {"success": True, "data": get_batch_analysis_data(db, n_show=n_show, **filters)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"items": [], "total_count": 0}}


@router.get("/expiry-status")
def fetch_expiry_status(
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return {"success": True, "data": get_expiry_status_distribution(db, **filters)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"distribution": [], "total_stock": 0, "total_skus": 0}}


@router.get("/turnover-status")
def fetch_turnover_status(
    filters: dict = Depends(_filter_params),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return {"success": True, "data": get_turnover_status_distribution(db, **filters)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"distribution": [], "total_stock": 0, "total_skus": 0}}


# ---- 基础分析：通用 RPT 报表查询 ----

ALLOWED_REPORT_TABLES = {
    "rpt_expiry_warning",
    "rpt_expiry_turnover",
    "rpt_self_operated_concentration",
    "rpt_turnover_warning",
    "rpt_trend_warning",
    "rpt_warehouse_risk",
    "rpt_procurement_linked",
    "stg_stock_current",
}


@router.get("/filter-options/spec")
def fetch_spec_options(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取品项（spec/规格）筛选选项"""
    try:
        result = db.execute(text("""
            SELECT DISTINCT spec FROM stg_stock_current
            WHERE spec IS NOT NULL AND spec != '' AND spec != 'None'
            ORDER BY spec
        """))
        specs = [row[0] for row in result.fetchall() if row[0]]
        return {"success": True, "data": specs}
    except Exception as e:
        logger.error(f"Failed to fetch spec options: {e}")
        return {"success": False, "error": str(e), "data": []}


@router.get("/filter-options/model")
def fetch_model_options(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取型号筛选选项"""
    try:
        result = db.execute(text("""
            SELECT DISTINCT model FROM stg_stock_in
            WHERE model IS NOT NULL AND model != ''
            ORDER BY model
        """))
        models = [row[0] for row in result.fetchall() if row[0]]
        return {"success": True, "data": models}
    except Exception as e:
        logger.error(f"Failed to fetch model options: {e}")
        return {"success": False, "error": str(e), "data": []}


@router.get("/filter-options/warehouse")
def fetch_warehouse_options(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取仓库筛选选项"""
    try:
        result = db.execute(text("""
            SELECT DISTINCT warehouse FROM stg_stock_current
            WHERE warehouse IS NOT NULL AND warehouse != ''
            ORDER BY warehouse
        """))
        warehouses = [row[0] for row in result.fetchall() if row[0]]
        return {"success": True, "data": warehouses}
    except Exception as e:
        logger.error(f"Failed to fetch warehouse options: {e}")
        return {"success": False, "error": str(e), "data": []}


@router.get("/report/{table_name}")
def fetch_report_table(
    table_name: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """通用报表查询端点 — 白名单校验表名，防止 SQL 注入"""
    from app.services.field_mapping import rename_for_display

    if table_name not in ALLOWED_REPORT_TABLES:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    try:
        # 使用 db.execute 而不是 pd.read_sql 避免异步上下文问题
        result = db.execute(text(f"SELECT * FROM `{table_name}` LIMIT 5000"))
        columns = list(result.keys())
        rows = result.fetchall()

        # 构建 DataFrame 并转换为中文列名
        df = pd.DataFrame(rows, columns=columns)
        df_display = rename_for_display(df, table_name)

        # 转换为字典并处理 NaN
        records = []
        for row in df_display.to_dict(orient="records"):
            record = {}
            for k, v in row.items():
                if pd.isna(v):
                    v = None
                record[k] = v
            records.append(record)

        return {
            "success": True,
            "data": {
                "columns": list(df_display.columns),
                "rows": records,
                "total": len(records),
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch report {table_name}: {e}")
        return {"success": False, "error": str(e), "data": {"columns": [], "rows": [], "total": 0}}
