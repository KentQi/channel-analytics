"""channel_analytics.api.routers — 路由集合。"""
from fastapi import APIRouter

from channel_analytics.api.routers.auth import router as auth_router
from channel_analytics.api.routers.etl import router as etl_router
from channel_analytics.api.routers.reports import router as reports_router
from channel_analytics.api.routers.rpa_tasks import router as rpa_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(rpa_router, prefix="/rpa", tags=["rpa"])
api_router.include_router(etl_router, prefix="/etl", tags=["etl"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])


__all__ = ["api_router"]