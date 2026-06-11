"""channel_analytics.api — FastAPI 应用。

W2 阶段补全 4 个路由模块:
  - /auth (login / me / logout)
  - /rpa (tasks CRUD + run + logs)
  - /etl (run / status / pipeline)
  - /reports (list / catalog / query)
  - /healthz (存活探针)

部署方应:
  - 在 rpa_tasks / etl / reports 的占位实现处注入 DB session
  - 在 auth._authenticate 处接入 user 表查询
"""
from __future__ import annotations

from fastapi import FastAPI

from channel_analytics import __version__
from channel_analytics.api.routers import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="channel-analytics",
        version=__version__,
        description="通用渠道分析平台(开源版)",
    )

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(api_router)
    return app


# 兼容 uvicorn 启动:  uvicorn channel_analytics.api.app:app
app = create_app()
