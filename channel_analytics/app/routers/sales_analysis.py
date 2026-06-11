"""
销售分析API路由
提供销售出库、仪表盘、指标达成等分析功能的API端点
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.services.sales_service import (
    get_filter_options,
    search_material_name_options,
    get_wide_table_data,
    get_dashboard_data,
    get_indicator_progress,
    get_sales_detail,
    get_product_flow_detail,
    get_star_products,
    get_customer_tier_data,
    get_region_customer_ranking,
)

router = APIRouter(prefix="/sales", tags=["销售分析"])
security = HTTPBearer()


def get_user_regions(user: UserResponse) -> Optional[List[str]]:
    """
    从用户权限中获取允许访问的大区列表

    Args:
        user: 当前用户

    Returns:
        允许访问的大区列表，None表示无限制
    """
    # 从用户角色权限中提取区域权限
    if hasattr(user, 'role_permissions') and user.role_permissions:
        import json
        try:
            perms = json.loads(user.role_permissions) if isinstance(user.role_permissions, str) else user.role_permissions
            return perms.get('regions')
        except (json.JSONDecodeError, TypeError):
            pass
    return None


@router.get("/filter-options")
async def get_sales_filter_options(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取销售分析的级联筛选器选项

    返回大区、业务经理、客户、渠道等筛选维度的可选值列表
    """
    allowed_regions = get_user_regions(user)
    return get_filter_options(db, allowed_regions)


@router.get("/material-name-options")
async def get_material_name_options(
    keyword: str = Query("", description="物料名称关键词"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    根据关键词模糊搜索物料名称选项

    返回匹配的去重物料名称列表，用于前端远程搜索下拉框
    """
    allowed_regions = get_user_regions(user)
    return search_material_name_options(db, keyword=keyword, allowed_regions=allowed_regions)


@router.get("/wide-table")
async def get_sales_wide_table(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    customer: Optional[str] = Query(None, description="客户"),
    channel: Optional[str] = Query(None, description="渠道"),
    date_from: Optional[str] = Query(None, description="审核日期开始 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="审核日期结束 YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="商品品类"),
    abc_class: Optional[str] = Query(None, description="ABC分类"),
    lifecycle_status: Optional[str] = Query(None, description="生命周期"),
    custom_flag: Optional[str] = Query(None, description="定制标记"),
    promoted_flag: Optional[str] = Query(None, description="主推标记"),
    material_code: Optional[str] = Query(None, description="物料编码"),
    material_name: Optional[str] = Query(None, description="物料名称（模糊搜索）"),
    doc_date_from: Optional[str] = Query(None, description="单据日期开始 YYYY-MM-DD"),
    doc_date_to: Optional[str] = Query(None, description="单据日期结束 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(1000, ge=1, le=5000, description="每页数量"),
    db_session: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取销售出库宽表数据

    支持多维度筛选，返回分页的销售出库明细数据及汇总统计
    """
    return get_wide_table_data(
        db=db_session,
        region=region,
        manager=manager,
        customer=customer,
        channel=channel,
        date_from=date_from,
        date_to=date_to,
        category=category,
        abc_class=abc_class,
        lifecycle_status=lifecycle_status,
        custom_flag=custom_flag,
        promoted_flag=promoted_flag,
        material_code=material_code,
        material_name=material_name,
        doc_date_from=doc_date_from,
        doc_date_to=doc_date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/dashboard")
async def get_sales_dashboard(
    region: Optional[str] = Query(None, description="大区"),
    start_year_month: Optional[str] = Query(None, description="起始期间 YYYY/MM"),
    end_year_month: Optional[str] = Query(None, description="结束期间 YYYY/MM"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取出货仪表盘数据

    返回用户选择时间范围内的出货数据，包含完成率、同比、环比等指标
    """
    allowed_regions = get_user_regions(user)
    return get_dashboard_data(
        db=db,
        region=region,
        start_year_month=start_year_month,
        end_year_month=end_year_month,
        allowed_regions=allowed_regions,
    )


@router.get("/indicator-progress")
async def get_sales_indicator_progress(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    month: Optional[str] = Query(None, description="月份 YYYY/MM"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取指标达成进度

    返回指定月份的周度任务、实际完成额、完成率等指标
    """
    allowed_regions = get_user_regions(user)
    return get_indicator_progress(
        db=db,
        region=region,
        manager=manager,
        year_month=month,
        allowed_regions=allowed_regions,
    )


@router.get("/sales-detail")
async def get_sales_detail_data(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    customer: Optional[str] = Query(None, description="客户"),
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="商品品类"),
    abc_class: Optional[str] = Query(None, description="ABC分类"),
    material_code: Optional[str] = Query(None, description="物料编码"),
    group_by: str = Query("material", description="分组维度: material/region_customer/region_material/customer_material"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=2000, description="每页数量"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取销售出库明细

    支持按物料、客户、区域等维度聚合，返回带同比环比数据的明细报表
    """
    allowed_regions = get_user_regions(user)
    return get_sales_detail(
        db=db,
        region=region,
        manager=manager,
        customer=customer,
        date_from=date_from,
        date_to=date_to,
        category=category,
        abc_class=abc_class,
        material_code=material_code,
        group_by=group_by,
        page=page,
        page_size=page_size,
        allowed_regions=allowed_regions,
    )


@router.get("/product-flow")
async def get_product_flow(
    material_code: Optional[str] = Query(None, description="物料编码"),
    batch_no: Optional[str] = Query(None, description="批次号"),
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    customer_id: Optional[str] = Query(None, description="客户ID"),
    customer: Optional[str] = Query(None, description="客户(兼容)"),
    tx_type: Optional[str] = Query(None, description="交易类型: 销售出库/退货入库"),
    order_type: Optional[str] = Query(None, description="交易类型(兼容): 销售出库/退货入库"),
    region: Optional[str] = Query(None, description="大区"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取单品货流明细

    返回指定物料/批次的出入库明细及汇总统计
    """
    # 兼容前端参数名
    effective_tx_type = tx_type or order_type
    effective_customer = customer_id or customer
    allowed_regions = get_user_regions(user)

    return get_product_flow_detail(
        db=db,
        material_code=material_code,
        batch_no=batch_no,
        date_from=date_from,
        date_to=date_to,
        customer=effective_customer,
        order_type=effective_tx_type,
        region=region,
        allowed_regions=allowed_regions,
        page=page,
        page_size=page_size,
    )


@router.get("/star-products")
async def get_star_products_ranking(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    top_n: Optional[int] = Query(None, description="返回前N个商品"),
    limit: Optional[int] = Query(None, description="返回前N个商品（别名）"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取明星商品评分

    返回TOP N商品的销售额、销量、市场占比、同比等指标
    """
    # 支持 limit 和 top_n 参数
    effective_limit = top_n if top_n is not None else (limit if limit is not None else 30)

    allowed_regions = get_user_regions(user)
    return get_star_products(
        db=db,
        region=region,
        manager=manager,
        date_from=date_from,
        date_to=date_to,
        top_n=effective_limit,
        allowed_regions=allowed_regions,
    )


@router.get("/customer-tier")
async def get_customer_tier(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    start_year_month: Optional[str] = Query(None, description="起始期间 YYYY/MM"),
    end_year_month: Optional[str] = Query(None, description="结束期间 YYYY/MM"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取客户分层数据

    按出货金额将客户分为不同等级，返回各等级的客户数量和金额分布
    """
    return get_customer_tier_data(
        db=db,
        region=region,
        manager=manager,
        start_year_month=start_year_month,
        end_year_month=end_year_month,
    )


@router.get("/region-customer-ranking")
async def get_region_customer_ranking_data(
    region: Optional[str] = Query(None, description="大区"),
    manager: Optional[str] = Query(None, description="客户经理"),
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    top_n: int = Query(50, ge=1, le=200, description="返回前N个"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取区域×客户排名

    按出货金额排序，返回区域和客户的交叉排名数据
    """
    return get_region_customer_ranking(
        db=db,
        region=region,
        manager=manager,
        date_from=date_from,
        date_to=date_to,
        top_n=top_n,
    )


@router.get("/category-distribution")
async def get_category_dist(
    region: Optional[str] = Query(None, description="大区"),
    start_month: Optional[str] = Query(None),
    end_month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    from app.services.sales_service import get_category_distribution
    allowed_regions = get_user_regions(user)
    return get_category_distribution(db, start_month, end_month, allowed_regions, region=region)




@router.get("/promoted-penetration")
async def get_promoted_penetration_api(
    region: Optional[str] = Query(None, description="大区"),
    start_month: Optional[str] = Query(None),
    end_month: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    from app.services.sales_service import get_promoted_penetration
    allowed_regions = get_user_regions(user)
    return get_promoted_penetration(db, start_month, end_month, allowed_regions, region=region)
