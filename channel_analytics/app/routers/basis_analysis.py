"""
基础分析 API 路由 — 库存 + 销售概览仪表盘
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.services.stock_service import get_kpi_metrics, get_stock_summary_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/basis", tags=["基础分析"])


@router.get("/overview")
def fetch_overview(
    brand_class: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取基础分析概览：库存 KPI + 预警汇总 + 风险分布
    """
    filters = {"brand_class": brand_class, "warehouse": warehouse}

    # Stock KPIs
    try:
        kpis = get_kpi_metrics(db, **filters)
    except Exception as e:
        logger.warning(f"basis overview kpis failed: {e}")
        kpis = {
            "total_stock": 0, "total_90d_sales": 0, "inventory_days": None,
            "total_pending_in": 0, "no_sales_stock": 0,
            "in_stock_skus": 0, "no_sales_skus": 0,
        }

    # Stock summary (warning counts)
    try:
        summary = get_stock_summary_data(db, **filters)
    except Exception as e:
        logger.warning(f"basis overview summary failed: {e}")
        summary = {
            "total_records": 0,
            "expiry_warning_count": 0,
            "turnover_warning_count": 0,
            "trend_warning_count": 0,
        }

    # Risk distribution from rpt_warehouse_risk
    risk_dist = {"高风险": 0, "中风险": 0, "低风险": 0}
    try:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT risk_level, COUNT(DISTINCT material_code) as cnt "
            "FROM rpt_warehouse_risk GROUP BY risk_level"
        )).fetchall()
        for level, cnt in rows:
            if level in risk_dist:
                risk_dist[level] = int(cnt)
    except Exception as e:
        logger.warning(f"basis overview risk failed: {e}")

    # Latest ETL task time
    latest_etl = None
    try:
        from pathlib import Path
        import json
        tasks_dir = Path(__file__).resolve().parent.parent.parent.parent / "tasks" / "status"
        if tasks_dir.exists():
            latest_time = None
            for f in tasks_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data.get("status") == "completed":
                        t = data.get("updated_at")
                        if t and (latest_time is None or t > latest_time):
                            latest_time = t
                except Exception:
                    pass
            latest_etl = latest_time
    except Exception:
        pass

    return {
        "kpis": kpis,
        "summary": {
            "total_records": summary.get("total_records", 0),
            "expiry_warning_count": summary.get("expiry_warning_count", 0),
            "turnover_warning_count": summary.get("turnover_warning_count", 0),
            "trend_warning_count": summary.get("trend_warning_count", 0),
        },
        "risk_distribution": risk_dist,
        "latest_etl_time": latest_etl,
    }
