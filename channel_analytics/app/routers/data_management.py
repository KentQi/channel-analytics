"""
数据维护 API 路由 — 对齐原版 info_maint.py 的 6 张维表 CRUD + 业务逻辑接口
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.utils.audit import log_data_import
from app.models.schemas import (
    UserResponse, ProductAttrUpdate, CustomerUpdate,
    RegionIndicatorUpdate, CustomerIndicatorUpdate,
    FilterConfigSave, FilterConfigUpdate, BrandUpdate,
)
from app.services.data_service import (
    # 商品属性
    get_product_attrs,
    update_product_attr,
    import_product_attrs,
    update_first_stock_in_date,
    update_lifecycle_status,
    # 客户信息
    get_customers,
    update_customer,
    import_customers,
    # 省区指标
    get_region_indicators,
    update_region_indicator,
    import_region_indicators,
    # 客户指标
    get_customer_indicators,
    update_customer_indicator,
    import_customer_indicators,
    # 筛选配置
    get_filter_configs,
    get_filter_config,
    save_filter_config,
    update_filter_config,
    import_filter_configs,
    # 自营品牌
    get_self_operated_brands,
    update_self_operated_brand,
    import_self_operated_brands,
    # stg 数据源
    get_customer_classes_from_stg,
    get_customers_by_class_from_stg,
    # 模板
    get_table_template,
)
import pandas as pd
import io

router = APIRouter(prefix="/data", tags=["数据维护"])


# ============================================================
# 商品属性
# ============================================================

@router.get("/product-attrs")
async def list_product_attrs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return get_product_attrs(db, page, page_size, search)


@router.put("/product-attrs/{material_code}")
async def edit_product_attr(
    material_code: str,
    data: ProductAttrUpdate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    success = update_product_attr(db, material_code, data.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="商品属性不存在或无需更新")
    return {"message": "更新成功"}


@router.post("/product-attrs/import")
async def import_product_attrs_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        records = df.to_dict('records')
        result = import_product_attrs(db, records)
        log_data_import(user.username, "product_attr", result.get("success",0), result.get("error",0))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/product-attrs/template")
async def download_product_attrs_template(
    user: UserResponse = Depends(get_current_user),
):
    columns = get_table_template("product_attr")
    return {"columns": columns}


@router.post("/product-attrs/update-first-stock-date")
async def api_update_first_stock_date(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """批量更新首次入库日期（从 stg_stock_in）"""
    result = update_first_stock_in_date(db)
    return result


@router.post("/product-attrs/update-lifecycle-status")
async def api_update_lifecycle_status(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """批量更新商品生命周期状态"""
    result = update_lifecycle_status(db)
    return result


# ============================================================
# 客户信息
# ============================================================

@router.get("/customers")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return get_customers(db, page, page_size, search, region)


@router.put("/customers/{customer_name}")
async def edit_customer(
    customer_name: str,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    success = update_customer(db, customer_name, data.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="客户不存在或无需更新")
    return {"message": "更新成功"}


@router.post("/customers/import")
async def import_customers_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        records = df.to_dict('records')
        result = import_customers(db, records)
        log_data_import(user.username, "customer", result.get("success",0), result.get("error",0))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/customers/template")
async def download_customers_template(
    user: UserResponse = Depends(get_current_user),
):
    columns = get_table_template("customer")
    return {"columns": columns}


# ============================================================
# 省区指标
# ============================================================

@router.get("/region-indicators")
async def list_region_indicators(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return get_region_indicators(db, page, page_size, search)


@router.put("/region-indicators/{region}/{period}")
async def edit_region_indicator(
    region: str,
    period: str,
    data: RegionIndicatorUpdate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    success = update_region_indicator(db, region, period, data.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="省区指标不存在或无需更新")
    return {"message": "更新成功"}


@router.post("/region-indicators/import")
async def import_region_indicators_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        records = df.to_dict('records')
        result = import_region_indicators(db, records)
        log_data_import(user.username, "region_indicator", result.get("success",0), result.get("error",0))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/region-indicators/template")
async def download_region_indicators_template(
    user: UserResponse = Depends(get_current_user),
):
    columns = get_table_template("region_indicator")
    return {"columns": columns}


# ============================================================
# 客户指标
# ============================================================

@router.get("/customer-indicators")
async def list_customer_indicators(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return get_customer_indicators(db, page, page_size, search)


@router.put("/customer-indicators/{customer}/{period}")
async def edit_customer_indicator(
    customer: str,
    period: str,
    data: CustomerIndicatorUpdate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    success = update_customer_indicator(db, customer, period, data.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="客户指标不存在或无需更新")
    return {"message": "更新成功"}


@router.post("/customer-indicators/import")
async def import_customer_indicators_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        records = df.to_dict('records')
        result = import_customer_indicators(db, records)
        log_data_import(user.username, "customer_indicator", result.get("success",0), result.get("error",0))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/customer-indicators/template")
async def download_customer_indicators_template(
    user: UserResponse = Depends(get_current_user),
):
    columns = get_table_template("customer_indicator")
    return {"columns": columns}


# ============================================================
# 筛选配置
# ============================================================

@router.get("/filter-configs")
async def list_filter_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    filter_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return get_filter_configs(db, page, page_size, filter_type)


@router.get("/filter-config/{filter_type}")
async def api_get_filter_config(
    filter_type: str,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """获取指定筛选配置（渠道客户设定用）"""
    values = get_filter_config(db, filter_type)
    return {"filter_type": filter_type, "values": values}


@router.put("/filter-config/{filter_type}")
async def api_save_filter_config(
    filter_type: str,
    data: FilterConfigSave,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """保存指定筛选配置"""
    save_filter_config(db, filter_type, data.values)
    return {"message": "保存成功"}


@router.put("/filter-configs/{config_id}")
async def edit_filter_config(
    config_id: int,
    data: FilterConfigUpdate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    success = update_filter_config(db, config_id, data.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在或无需更新")
    return {"message": "更新成功"}


@router.post("/filter-configs/import")
async def import_filter_configs_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        records = df.to_dict('records')
        result = import_filter_configs(db, records)
        log_data_import(user.username, "filter_config", result.get("success",0), result.get("error",0))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/filter-configs/template")
async def download_filter_configs_template(
    user: UserResponse = Depends(get_current_user),
):
    columns = get_table_template("filter_config")
    return {"columns": columns}


# ============================================================
# 自营品牌
# ============================================================

@router.get("/self-operated-brands")
async def list_self_operated_brands(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return get_self_operated_brands(db, page, page_size, search)


@router.put("/self-operated-brands/{brand_id}")
async def edit_self_operated_brand(
    brand_id: int,
    data: BrandUpdate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    success = update_self_operated_brand(db, brand_id, data.model_dump(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="品牌不存在或无需更新")
    return {"message": "更新成功"}


@router.post("/self-operated-brands/import")
async def import_self_operated_brands_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        records = df.to_dict('records')
        result = import_self_operated_brands(db, records)
        log_data_import(user.username, "brand", result.get("success",0), result.get("error",0))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/self-operated-brands/template")
async def download_self_operated_brands_template(
    user: UserResponse = Depends(get_current_user),
):
    columns = get_table_template("self_operated_brand")
    return {"columns": columns}


# ============================================================
# stg 数据源选项（渠道客户设定用）
# ============================================================

@router.get("/stg-options/customer-classes")
async def api_get_customer_classes(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """从 stg_sales_out 获取客户类别列表"""
    classes = get_customer_classes_from_stg(db)
    return {"items": classes}


@router.get("/stg-options/customers")
async def api_get_customers_by_class(
    customer_classes: Optional[str] = Query(None, description="逗号分隔的 customer_class"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """从 stg_sales_out 获取客户列表（可按 class 过滤）"""
    class_list = [c.strip() for c in customer_classes.split(",")] if customer_classes else None
    items = get_customers_by_class_from_stg(db, class_list)
    return {"items": items}


# ============================================================
# 通用
# ============================================================

@router.get("/table-types")
async def list_table_types(
    user: UserResponse = Depends(get_current_user),
):
    return {
        "types": [
            {"key": "product_attr", "name": "商品属性", "table": "dim_product_attr"},
            {"key": "customer", "name": "客户信息", "table": "dim_customer"},
            {"key": "region_indicator", "name": "省区指标", "table": "dim_business_indicator_region"},
            {"key": "customer_indicator", "name": "客户指标", "table": "dim_business_indicator_customer"},
            {"key": "filter_config", "name": "筛选配置", "table": "dim_filter_config"},
            {"key": "self_operated_brand", "name": "自营品牌", "table": "dim_self_operated_brand"},
        ]
    }
