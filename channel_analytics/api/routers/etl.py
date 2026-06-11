"""ETL router — 触发 ETL Pipeline + 状态查询。

新仓接口契约:
  - POST /etl/run           — 立即跑 ETL(异步返回 task_id)
  - GET  /etl/status/{id}   — 查询运行状态
  - GET  /etl/pipeline      — 列出 Pipeline 步骤
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from channel_analytics.api.deps import get_current_user
from channel_analytics.etl.pipeline import (
    Pipeline,
    build_default_pipeline,
    make_context,
    run_default_etl,
)


router = APIRouter()


class RunETLRequest(BaseModel):
    raw_data: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="key=STG 表名(无 stg_ 前缀),value=行 list",
    )
    brand_provider_dotted: str = (
        "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
    )
    business_rules_path: str = ""


class RunETLResponse(BaseModel):
    run_id: str
    status: str  # queued / running / success / failed


# 内存 run 跟踪(部署期应替换为 DB)
_runs: dict[str, dict[str, Any]] = {}


@router.post("/run", response_model=RunETLResponse, status_code=status.HTTP_202_ACCEPTED)
async def run(req: RunETLRequest, current_user=Depends(get_current_user)) -> RunETLResponse:
    import uuid
    import pandas as pd

    run_id = str(uuid.uuid4())
    raw_data = {
        (k if k.startswith("stg_") else f"stg_{k}"): pd.DataFrame(v)
        for k, v in req.raw_data.items()
    }
    _runs[run_id] = {"status": "queued", "started_at": datetime.utcnow()}

    def _worker():
        try:
            _runs[run_id]["status"] = "running"
            ctx = run_default_etl(
                raw_data,
                brand_provider_dotted=req.brand_provider_dotted,
                business_rules_path=req.business_rules_path,
            )
            _runs[run_id]["status"] = "success"
            _runs[run_id]["finished_at"] = datetime.utcnow()
            _runs[run_id]["ctx"] = ctx
        except Exception as e:  # noqa: BLE001
            _runs[run_id]["status"] = "failed"
            _runs[run_id]["error"] = str(e)

    threading.Thread(target=_worker, daemon=True).start()
    return RunETLResponse(run_id=run_id, status="queued")


@router.get("/status/{run_id}", response_model=RunETLResponse)
async def get_status(run_id: str, current_user=Depends(get_current_user)) -> RunETLResponse:
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunETLResponse(run_id=run_id, status=_runs[run_id]["status"])


@router.get("/pipeline")
async def get_pipeline(current_user=Depends(get_current_user)) -> list[dict[str, Any]]:
    """列出默认 Pipeline 步骤(无实际执行)。"""
    from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
    from channel_analytics.etl.rules import BusinessRules
    p = build_default_pipeline(
        brand_provider=ExampleMinimalProvider(),
        rules=BusinessRules.defaults(),
    )
    return [{"index": str(i), "name": str(getattr(s, "name", s.__class__.__name__))} for i, s in enumerate(p.steps)]


__all__ = ["router"]