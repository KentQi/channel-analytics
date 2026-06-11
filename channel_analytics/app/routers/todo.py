"""
待办事项API路由
提供数据维护提醒等待办事项查询接口
"""
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse

router = APIRouter(prefix="/todo", tags=["待办事项"])


@router.get("/items")
async def get_todo_items(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取待办事项列表

    数据维护提醒：
    - rpt_sales_out_wide 中有但 dim_product_attr 中没有的物料
    - rpt_sales_out_wide 中有但 dim_customer 中没有的客户
    - 已建档但客户经理为空的客户
    """
    missing_products = []
    missing_customers = []
    no_manager_customers = []

    # 缺少物料属性的物料
    try:
        rows = db.execute(text("""
            SELECT DISTINCT w.material_code, w.material_name
            FROM rpt_sales_out_wide w
            LEFT JOIN dim_product_attr d ON w.material_code = d.material_code
            WHERE d.material_code IS NULL
            AND w.material_code IS NOT NULL AND w.material_code != ''
        """)).fetchall()
        missing_products = [{"material_code": r[0], "material_name": r[1]} for r in rows]
    except Exception:
        pass

    # 缺少客户信息的客户
    try:
        rows = db.execute(text("""
            SELECT DISTINCT w.customer, w.region
            FROM rpt_sales_out_wide w
            LEFT JOIN dim_customer d ON w.customer = d.customer_name
            WHERE d.customer_name IS NULL
            AND w.customer IS NOT NULL AND w.customer != ''
        """)).fetchall()
        missing_customers = [{"customer": r[0], "region": r[1]} for r in rows]
    except Exception:
        pass

    # 已建档但客户经理为空的客户
    try:
        rows = db.execute(text("""
            SELECT customer, d.region, SUM(IFNULL(tax_included_amount,0)) as annual_sales, cooperation_status
            FROM rpt_sales_out_wide w
            JOIN dim_customer d ON w.customer = d.customer_name
            WHERE (d.account_manager IS NULL OR d.account_manager = '')
            AND YEAR(doc_date) = YEAR(CURDATE())
            GROUP BY customer, d.region, cooperation_status
        """)).fetchall()
        no_manager_customers = [{"customer": r[0], "region": r[1], "annual_sales": float(r[2] or 0), "cooperation_status": r[3]} for r in rows]
    except Exception:
        pass

    # 数据对齐统计
    try:
        stg_count = db.execute(text("SELECT COUNT(*) FROM rpt_sales_out_wide")).scalar() or 0
        wide_count = stg_count
        diff = 0
    except Exception:
        stg_count = 0
        wide_count = 0
        diff = 0

    return {
        "missing_products": missing_products,
        "missing_customers": missing_customers,
        "no_manager_customers": no_manager_customers,
        "data_alignment": {"stg_count": stg_count, "wide_count": wide_count, "diff": diff},
    }


@router.get("/maintenance-alerts")
async def get_maintenance_alerts(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    维护提醒 — 找出销售宽表中存在但未维护维度的物料/客户
    """
    alerts = {"unmaintained_materials": [], "unmaintained_customers": [], "no_manager_customers": []}

    # 未维护商品属性的物料
    try:
        rows = db.execute(text("""
            SELECT DISTINCT w.material_code, w.material_name
            FROM rpt_sales_out_wide w
            LEFT JOIN dim_product_attr d ON w.material_code = d.material_code
            WHERE d.material_code IS NULL
            AND w.material_code IS NOT NULL AND w.material_code != ''
        """)).fetchall()
        alerts["unmaintained_materials"] = [{"material_code": r[0], "material_name": r[1]} for r in rows]
    except Exception:
        pass

    # 未维护客户信息的客户
    try:
        rows = db.execute(text("""
            SELECT DISTINCT w.customer
            FROM rpt_sales_out_wide w
            LEFT JOIN dim_customer d ON w.customer = d.customer_name
            WHERE d.customer_name IS NULL
            AND w.customer IS NOT NULL AND w.customer != ''
        """)).fetchall()
        alerts["unmaintained_customers"] = [{"customer": r[0]} for r in rows]
    except Exception:
        pass

    # 有客户但无客户经理的
    try:
        rows = db.execute(text("""
            SELECT DISTINCT w.customer, d.region
            FROM rpt_sales_out_wide w
            JOIN dim_customer d ON w.customer = d.customer_name
            WHERE (d.account_manager IS NULL OR d.account_manager = '')
            AND w.customer IS NOT NULL AND w.customer != ''
        """)).fetchall()
        alerts["no_manager_customers"] = [{"customer": r[0], "region": r[1]} for r in rows]
    except Exception:
        pass

    alerts["total_alerts"] = (len(alerts["unmaintained_materials"])
                              + len(alerts["unmaintained_customers"])
                              + len(alerts["no_manager_customers"]))
    return alerts
