"""
系统日志查询 API 路由
提供安全日志、业务日志、错误日志的查询接口
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.schemas import UserResponse
from app.utils.audit import read_logs

router = APIRouter(prefix="/logs", tags=["系统日志"])


@router.get("/audit")
async def get_audit_logs(
    type_filter: str = Query("", alias="type_filter"),
    level_filter: str = Query("", alias="level_filter"),
    user_filter: str = Query("", alias="user_filter"),
    keyword: str = Query("", alias="keyword"),
    limit: int = Query(200, ge=1, le=1000),
    user: UserResponse = Depends(get_current_user),
):
    """查询安全日志（登录、退出、权限变更、密码修改）"""
    items = read_logs("audit", type_filter, level_filter, user_filter, keyword, limit)
    return {"items": items, "total": len(items)}


@router.get("/business")
async def get_business_logs(
    type_filter: str = Query("", alias="type_filter"),
    level_filter: str = Query("", alias="level_filter"),
    user_filter: str = Query("", alias="user_filter"),
    keyword: str = Query("", alias="keyword"),
    limit: int = Query(200, ge=1, le=1000),
    user: UserResponse = Depends(get_current_user),
):
    """查询业务日志（ETL、数据导入）"""
    items = read_logs("business", type_filter, level_filter, user_filter, keyword, limit)
    return {"items": items, "total": len(items)}


@router.get("/error")
async def get_error_logs(
    type_filter: str = Query("", alias="type_filter"),
    level_filter: str = Query("", alias="level_filter"),
    user_filter: str = Query("", alias="user_filter"),
    keyword: str = Query("", alias="keyword"),
    limit: int = Query(200, ge=1, le=1000),
    user: UserResponse = Depends(get_current_user),
):
    """查询错误日志（页面崩溃等）"""
    items = read_logs("error", type_filter, level_filter, user_filter, keyword, limit)
    return {"items": items, "total": len(items)}
