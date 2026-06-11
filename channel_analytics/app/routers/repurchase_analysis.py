"""
返单分析API路由
提供客户留存、商品生命周期、流失预警等复购分析功能的API端点
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.services.repurchase_service import (
    get_cohort_matrix,
    get_customer_value_scatter,
    get_churn_warning,
    get_new_customer_repurchase,
    get_product_lifecycle,
    get_customer_retention_rate,
    get_new_product_warning,
    get_customer_product_matrix,
    get_product_customer_cohort,
)

router = APIRouter(prefix="/repurchase", tags=["返单分析"])
security = HTTPBearer()


def get_user_regions(user: UserResponse) -> Optional[List[str]]:
    """
    从用户权限中获取允许访问的大区列表

    Args:
        user: 当前用户

    Returns:
        允许访问的大区列表，None表示无限制
    """
    if hasattr(user, 'role_permissions') and user.role_permissions:
        import json
        try:
            perms = json.loads(user.role_permissions) if isinstance(user.role_permissions, str) else user.role_permissions
            return perms.get('regions')
        except (json.JSONDecodeError, TypeError):
            pass
    return None


@router.get("/cohort-matrix")
async def get_repurchase_cohort_matrix(
    months: int = Query(12, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    customer: Optional[str] = Query(None, description="客户名称关键词"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取客户留存热力图数据

    返回客户留存矩阵和客户统计信息，包含复购次数、平均进货间隔等指标
    """
    allowed_regions = get_user_regions(user)
    return get_cohort_matrix(
        db=db,
        months=months,
        region=region,
        manager=manager,
        customer=customer,
        allowed_regions=allowed_regions,
    )


@router.get("/customer-value")
async def get_repurchase_customer_value(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    customer: Optional[str] = Query(None, description="客户名称关键词"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取客户价值散点图数据

    返回客户累计金额和订单次数的散点数据，用于分析客户价值分布
    """
    allowed_regions = get_user_regions(user)
    return get_customer_value_scatter(
        db=db,
        region=region,
        manager=manager,
        customer=customer,
        allowed_regions=allowed_regions,
    )


@router.get("/churn-warning")
async def get_repurchase_churn_warning(
    days: int = Query(90, ge=30, le=365, description="流失阈值天数"),
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    customer: Optional[str] = Query(None, description="客户名称关键词"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取流失预警客户列表

    返回超过指定天数未返单的客户列表，按最大进货间隔天数排序
    """
    allowed_regions = get_user_regions(user)
    return get_churn_warning(
        db=db,
        days=days,
        region=region,
        manager=manager,
        customer=customer,
        allowed_regions=allowed_regions,
    )


@router.get("/new-customer-repurchase")
async def get_repurchase_new_customer(
    days: int = Query(90, ge=30, le=365, description="新客户定义天数"),
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    customer: Optional[str] = Query(None, description="客户名称关键词"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取新客户返单监控

    返回新客户（首单后N天内）首单后8周的返单数量监控数据
    """
    allowed_regions = get_user_regions(user)
    return get_new_customer_repurchase(
        db=db,
        days=days,
        region=region,
        manager=manager,
        customer=customer,
        allowed_regions=allowed_regions,
    )


@router.get("/product-lifecycle")
async def get_repurchase_product_lifecycle(
    months: int = Query(18, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    abc_class: Optional[str] = Query(None, description="ABC分类"),
    lifecycle_status: Optional[str] = Query(None, description="生命周期状态"),
    product_name: Optional[str] = Query(None, description="物料名称关键词"),
    category: Optional[str] = Query(None, description="品类"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取商品生命周期表

    返回商品的月度销量矩阵，包含首次入库时间、首销时间、在库量等信息
    """
    allowed_regions = get_user_regions(user)
    return get_product_lifecycle(
        db=db,
        months=months,
        region=region,
        abc_class=abc_class,
        lifecycle_status=lifecycle_status,
        product_name=product_name,
        category=category,
        allowed_regions=allowed_regions,
    )


@router.get("/customer-retention")
async def get_repurchase_customer_retention(
    months: int = Query(18, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    abc_class: Optional[str] = Query(None, description="ABC分类"),
    lifecycle_status: Optional[str] = Query(None, description="生命周期状态"),
    product_name: Optional[str] = Query(None, description="物料名称关键词"),
    category: Optional[str] = Query(None, description="品类"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取客户留存率表

    返回商品维度的客户留存率矩阵，展示每月新增客户中在后续各月的复购率
    """
    allowed_regions = get_user_regions(user)
    return get_customer_retention_rate(
        db=db,
        months=months,
        region=region,
        abc_class=abc_class,
        lifecycle_status=lifecycle_status,
        product_name=product_name,
        category=category,
        allowed_regions=allowed_regions,
    )


@router.get("/new-product-warning")
async def get_repurchase_new_product_warning(
    days: int = Query(90, ge=30, le=365, description="建档天数范围"),
    db: Session = Depends(get_db),
):
    """
    获取新品预警表

    返回在建档天数内入库的产品的各时间段销量数据
    """
    return get_new_product_warning(
        db=db,
        days=days,
    )


@router.get("/customer-product-matrix")
async def get_repurchase_customer_product_matrix(
    customer: str = Query(..., description="客户名称"),
    months: int = Query(12, ge=1, le=36, description="追溯月数"),
    view_mode: str = Query('offset', description="视图模式: offset=偏移模式, absolute=动态日期"),
    db: Session = Depends(get_db),
):
    """
    获取指定客户的商品 Cohort 矩阵

    返回该客户各物料在各月（按其首批进货计算月份偏移）的销量分布
    """
    return get_customer_product_matrix(
        db=db,
        customer=customer,
        months=months,
        view_mode=view_mode,
    )


@router.get("/product-customer-cohort")
async def get_repurchase_product_customer_cohort(
    material_code: str = Query(..., description="物料编码"),
    months: int = Query(12, ge=1, le=36, description="追溯月数"),
    view_mode: str = Query('offset', description="视图模式: offset=偏移模式, absolute=动态日期"),
    category: Optional[str] = Query(None, description="品类（与物料编码联合限定）"),
    db: Session = Depends(get_db),
):
    """
    获取指定物料的客户 Cohort 矩阵

    返回购买过该物料的客户在各月（按其首次购买该物料计算月份偏移）的购买次数分布
    """
    return get_product_customer_cohort(
        db=db,
        material_code=material_code,
        months=months,
        view_mode=view_mode,
        category=category,
    )
