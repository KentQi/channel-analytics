"""Reports router — 列出已注册报表 + 查询单条 RPT 表。

新仓接口契约:
  - GET /reports            — 列出所有 RPT 表
  - GET /reports/{name}     — 查询 RPT 表内容(分页 + 过滤)
  - GET /reports/catalog    — 报表目录(描述 + 列名 + 索引)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from channel_analytics.api.deps import get_current_user


router = APIRouter()

# 默认 RPT 表清单(对齐 channel_analytics.etl.steps.write_rpt_tables.RPT_TABLES)
DEFAULT_REPORTS: tuple[str, ...] = (
    "rpt_expiry_warning",
    "rpt_expiry_turnover",
    "rpt_self_operated_concentration",
    "rpt_turnover_warning",
    "rpt_trend_warning",
    "rpt_warehouse_risk",
    "rpt_procurement_linked",
)


class ReportInfo(BaseModel):
    name: str
    description: str
    columns: list[str]


# 报表描述(部署方可扩展)
_REPORT_META: dict[str, dict[str, Any]] = {
    "rpt_expiry_warning": {
        "description": "物料+批次效期告警(物料×批次×库存)",
        "columns": [
            "material_code", "material_name", "brand", "brand_class",
            "batch_no", "expiry_date", "material_batch_available_qty",
            "sales_90d", "inventory_days", "remaining_expiry_months",
            "expiry_status", "expiry_warning",
        ],
    },
    "rpt_turnover_warning": {
        "description": "物料维度周转告警",
        "columns": [
            "material_code", "material_name", "brand", "brand_class",
            "material_available_qty", "sales_90d", "inventory_days",
            "turnover_status", "turnover_warning",
        ],
    },
}


@router.get("", response_model=list[ReportInfo])
async def list_reports(current_user=Depends(get_current_user)) -> list[ReportInfo]:
    return [
        ReportInfo(
            name=name,
            description=_REPORT_META.get(name, {}).get("description", ""),
            columns=_REPORT_META.get(name, {}).get("columns", []),
        )
        for name in DEFAULT_REPORTS
    ]


@router.get("/catalog")
async def get_catalog(current_user=Depends(get_current_user)) -> dict[str, Any]:
    """报表目录(name -> description + columns)。"""
    return {
        name: {
            "description": _REPORT_META.get(name, {}).get("description", ""),
            "columns": _REPORT_META.get(name, {}).get("columns", []),
        }
        for name in DEFAULT_REPORTS
    }


@router.get("/{name}")
async def get_report(
    name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """查询 RPT 表(占位实现)。

    部署期应替换为 DB 查询(SQLAlchemy session + RPT ORM 模型)。
    """
    if name not in DEFAULT_REPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown report: {name}")
    return {
        "name": name,
        "limit": limit,
        "offset": offset,
        "rows": [],  # 占位
        "total": 0,
    }


__all__ = ["router"]