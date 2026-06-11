"""
高级分析API路由
提供商品生命周期分析、客户生命周期分析、商品聚类、客户聚类
"""
import asyncio
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.services.advanced_analysis_service import (
    get_product_lifecycle,
    get_customer_lifecycle,
    get_product_cluster,
    get_customer_cluster,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advanced", tags=["高级分析"])

# 超时时间（秒）
CLUSTER_TIMEOUT = 60  # K-Means 聚类操作超时
LLM_TIMEOUT = 30  # LLM 建议生成超时


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


@router.get("/product-lifecycle")
async def get_advanced_product_lifecycle(
    months: int = Query(18, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    category: Optional[str] = Query(None, description="商品品类"),
    abc_class: Optional[str] = Query(None, description="ABC分类"),
    lifecycle_status: Optional[str] = Query(None, description="生命周期状态（新品/持续销售/售完即止/重新上架/淘汰）"),
    material_code: Optional[str] = Query(None, description="物料编码"),
    brand_class: Optional[str] = Query(None, description="品牌类型（自营/非自营）"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    商品生命周期分析（供应链PLC模型）

    基于累计出库量 + 销售趋势的MECE级联判定：
    - 导入期: 累计出库 < 5000
    - 成长期: 累计出库 ≥ 5000 且正增长
    - 成熟期: 累计出库 ≥ 20000 且增长稳定
    - 衰退期: 连续负增长 ≥ 3月

    Returns:
        包含lifecycle_data(明细)、metrics(汇总)、demand_signals(需求信号)的字典
    """
    allowed_regions = get_user_regions(user)
    return get_product_lifecycle(
        db=db,
        months=months,
        region=region,
        manager=manager,
        category=category,
        abc_class=abc_class,
        lifecycle_status=lifecycle_status,
        material_code=material_code,
        brand_class=brand_class,
        allowed_regions=allowed_regions,
    )


class LLMLifecycleAdviceRequest(BaseModel):
    """LLM生命周期建议请求"""
    material_name: str
    material_code: str
    plc_stage: str
    sub_stage: str
    cumulative_out_qty: int
    total_amount: float
    growth_rate: float
    sales_acceleration: float
    customer_penetration: float
    cv: float
    days_since_launch: int
    abc_class: str
    consecutive_negative_months: int
    avg_monthly_qty: float


@router.post("/product-lifecycle/advice")
async def get_llm_lifecycle_advice(
    request: LLMLifecycleAdviceRequest,
    user: UserResponse = Depends(get_current_user),
):
    """
    调用LLM生成个性化商品生命周期运营建议

    根据商品的具体数据指标，实时生成采购/库存/销售策略建议
    """
    from app.services.llm_service import generate_lifecycle_advice

    try:
        async with asyncio.timeout(LLM_TIMEOUT):
            advice = await asyncio.to_thread(
                generate_lifecycle_advice,
                material_name=request.material_name,
                material_code=request.material_code,
                plc_stage=request.plc_stage,
                sub_stage=request.sub_stage,
                cumulative_out_qty=request.cumulative_out_qty,
                total_amount=request.total_amount,
                growth_rate=request.growth_rate,
                sales_acceleration=request.sales_acceleration,
                customer_penetration=request.customer_penetration,
                cv=request.cv,
                days_since_launch=request.days_since_launch,
                abc_class=request.abc_class,
                consecutive_negative_months=request.consecutive_negative_months,
                avg_monthly_qty=request.avg_monthly_qty,
            )
            return {"data": {"advice": advice}}
    except asyncio.TimeoutError:
        logger.error("LLM建议生成超时")
        raise HTTPException(status_code=504, detail="建议生成超时，请稍后重试")
    except Exception as e:
        logger.error(f"LLM建议生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"建议生成失败: {str(e)}")


@router.get("/customer-lifecycle")
async def get_advanced_customer_lifecycle(
    months: int = Query(18, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    channel: Optional[str] = Query(None, description="渠道"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    客户生命周期分析

    基于RFM模型 + CLV，划分客户阶段：
    - 新客户: F=1 且 R < 30
    - 成长客户: F 递增趋势 且 R < 60
    - 成熟客户: F >= 3 且 R < 90 且 M高
    - 衰退客户: R > 90 但 F >= 2
    - 流失客户: R > 180

    Returns:
        包含customer_data(明细)和metrics(汇总)的字典
    """
    allowed_regions = get_user_regions(user)
    return get_customer_lifecycle(
        db=db,
        months=months,
        region=region,
        manager=manager,
        channel=channel,
        allowed_regions=allowed_regions,
    )


@router.get("/product-cluster")
async def get_advanced_product_cluster(
    months: int = Query(18, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    n_clusters: int = Query(4, ge=3, le=6, description="聚类数量"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    商品聚类分析

    基于K-Means聚类，结果映射到BCG矩阵风格标签：
    - 明星商品（高金额+高增长）
    - 现金牛（高金额+稳定）
    - 问题商品（高波动+低渗透）
    - 瘦狗商品（低金额+低频次）

    Returns:
        包含cluster_data(明细)、cluster_summary(聚类汇总)、radar_data(雷达图)的字典
    """
    allowed_regions = get_user_regions(user)
    try:
        async with asyncio.timeout(CLUSTER_TIMEOUT):
            return get_product_cluster(
                db=db,
                months=months,
                region=region,
                n_clusters=n_clusters,
                allowed_regions=allowed_regions,
            )
    except asyncio.TimeoutError:
        logger.error(f"商品聚类分析超时（{CLUSTER_TIMEOUT}秒）")
        raise HTTPException(status_code=504, detail=f"分析超时，请减少数据范围或聚类数")


@router.get("/customer-cluster")
async def get_advanced_customer_cluster(
    months: int = Query(18, ge=6, le=36, description="追溯月数"),
    region: Optional[str] = Query(None, description="大区"),
    n_clusters: int = Query(5, ge=3, le=6, description="聚类数量"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    客户聚类分析

    基于RFM特征的K-Means聚类
    标签: VIP客户、高价值客户、潜力客户、一般客户、流失风险客户

    Returns:
        包含cluster_data(明细)、cluster_summary(聚类汇总)、radar_data(RFM雷达图)的字典
    """
    allowed_regions = get_user_regions(user)
    try:
        async with asyncio.timeout(CLUSTER_TIMEOUT):
            return get_customer_cluster(
                db=db,
                months=months,
                region=region,
                n_clusters=n_clusters,
                allowed_regions=allowed_regions,
            )
    except asyncio.TimeoutError:
        logger.error(f"客户聚类分析超时（{CLUSTER_TIMEOUT}秒）")
        raise HTTPException(status_code=504, detail=f"分析超时，请减少数据范围或聚类数")
