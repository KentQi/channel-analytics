"""
FastAPI application entry point.
Configures CORS, registers routes, and provides health check endpoint.

⚠️ RECOMMENDED ENTRY POINT
==========================
This module (`app.main:app`) is the **primary** application entry, registering
all 17 business routers. For new code, deploy, and CI, use this.

The alternative `channel_analytics.api.app:app` is a 4-router placeholder kept
for backward compatibility. It does NOT include the business routers below;
using it will result in missing endpoints. See:
- docs/architecture/overview.md for the layering
- `start.sh` (which explicitly launches `app.main:app`)

P0 note: do NOT delete the `channel_analytics/api/app.py` file as part of
cleanup - third-party users may still invoke it via
`uvicorn channel_analytics.api.app:app`. The two are equivalent at the ASGI
surface level; the divergence is in which routers each mounts.
"""
import os
import traceback
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.limiter import limiter

from app.database import init_db
from app.routers.auth import auth_router
from app.routers.etl import router as etl_router
from app.routers.stock_analysis import router as stock_router
from app.routers.sales_analysis import router as sales_router
from app.routers.repurchase_analysis import router as repurchase_router
from app.routers.data_management import router as data_management_router
from app.routers.todo import router as todo_router
from app.routers.permissions import router as permissions_router
from app.routers.basis_analysis import router as basis_router
from app.routers.logs import router as logs_router
from app.routers.alerts import router as alerts_router
from app.routers.custom_report import router as custom_report_router
from app.routers.advanced_analysis import router as advanced_router
from app.routers.sys_config import router as sys_config_router
from app.routers.rpa import router as rpa_router
from app.routers.stub import (
    channels_router,
    analytics_router,
    reports_router,
    wholesale_router,
)

def create_app() -> FastAPI:
    """
    Application factory.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Channel Analytics Channel Analytics API",
        description="API for channel analytics and reporting",
        version="2.2.6",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Add rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Max upload size — block requests larger than this to prevent OOM
    # Default 50 MB; override via env var MAX_UPLOAD_BYTES for production
    max_upload_bytes = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))

    @app.middleware("http")
    async def _limit_upload_size(request, call_next):
        """Reject upload requests larger than max_upload_bytes with HTTP 413."""
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > max_upload_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large (max {max_upload_bytes} bytes)",
                    },
                )
        return await call_next(request)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            # dev 期局域网前端地址（vite dev 8502 / 生产期 80）。后端仅 127.0.0.1 监听，
            # 这些 origin 仅由同机前端发起，不会被外部直接利用。
            "http://localhost:8502",
            "http://127.0.0.1:8502",
            "http://127.0.0.1:8502",
            # Add your frontend origins here
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(etl_router, prefix="/api")
    app.include_router(stock_router, prefix="/api")
    app.include_router(sales_router, prefix="/api")
    app.include_router(repurchase_router, prefix="/api")
    app.include_router(data_management_router, prefix="/api")
    app.include_router(todo_router, prefix="/api")
    app.include_router(permissions_router, prefix="/api")
    app.include_router(basis_router, prefix="/api")
    app.include_router(logs_router, prefix="/api")
    app.include_router(alerts_router, prefix="/api")
    app.include_router(custom_report_router, prefix="/api")
    app.include_router(advanced_router, prefix="/api")
    app.include_router(sys_config_router, prefix="/api")
    app.include_router(rpa_router, prefix="/api")
    app.include_router(channels_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(wholesale_router, prefix="/api")

    # Prometheus metrics endpoint
    @app.get("/api/metrics", tags=["monitoring"])
    async def metrics():
        """
        Prometheus metrics endpoint.
        Exposes application metrics for Prometheus scraping.
        """
        from starlette.responses import Response as StarletteResponse
        return StarletteResponse(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    # Health check endpoints — /api/health (rich) + /healthz (liveness, for K8s)
    @app.get("/api/health", tags=["health"])
    async def health_check():
        """
        Enhanced health check endpoint with system metrics.

        Returns detailed health status including:
        - API service status
        - Database connection status
        - System metrics (disk, memory)
        """
        import psutil
        from app.database import main_engine

        health_status = {
            "status": "healthy",
            "service": "channel-analytics-channel-analytics",
            "timestamp": None,
        }

        # Database health check
        from sqlalchemy import text
        db_status = {"database": "unknown"}
        try:
            with main_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status["database"] = "connected"
        except Exception as e:
            db_status["database"] = "disconnected"
            db_status["error"] = str(e)
            health_status["status"] = "degraded"
        health_status["database"] = db_status

        # System metrics
        try:
            disk_usage = psutil.disk_usage('/')
            health_status["system"] = {
                "disk_used_percent": round(disk_usage.percent, 1),
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "memory_used_percent": round(psutil.virtual_memory().percent, 1),
            }
            # Alert if disk > 90% or memory > 90%
            if disk_usage.percent > 90 or psutil.virtual_memory().percent > 90:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["system"] = {"error": str(e)}

        # Add timestamp
        from datetime import datetime
        health_status["timestamp"] = datetime.now().isoformat()

        return health_status

    # Liveness probe — for K8s livenessProbe / load balancers
    # Returns 200 OK if the process is up; does NOT check DB.
    # Use /api/health for readiness (includes DB check).
    @app.get("/healthz", tags=["health"])
    async def liveness():
        """Lightweight liveness probe — does not touch DB. Use /api/health for full health."""
        return {"status": "ok"}

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "Channel Analytics Channel Analytics API",
            "version": "0.1.0",
            "docs": "/api/docs",
        }

    # RPA 调度器生命周期
    @app.on_event("startup")
    async def startup_rpa_scheduler():
        import logging
        logger = logging.getLogger(__name__)
        # 自动创建 RPA 表结构
        try:
            from app.database import main_engine
            from sqlalchemy import text
            with main_engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS rpa_tasks (
                        id              INT AUTO_INCREMENT PRIMARY KEY,
                        name            VARCHAR(100) NOT NULL,
                        module_name     VARCHAR(50) NOT NULL,
                        enabled         BOOLEAN DEFAULT TRUE,
                        schedule_times  JSON NOT NULL,
                        schedule_days   VARCHAR(50) DEFAULT 'daily',
                        max_retries     INT DEFAULT 3,
                        retry_interval  INT DEFAULT 5,
                        timeout_seconds INT DEFAULT 300,
                        captcha_strategy VARCHAR(20) DEFAULT 'skip',
                        notify_channels JSON,
                        extra_config    JSON,
                        last_run_at     DATETIME,
                        last_run_status VARCHAR(20),
                        next_run_at     DATETIME,
                        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """))
                # 兼容旧表：添加新列
                try:
                    conn.execute(text("ALTER TABLE rpa_tasks ADD COLUMN IF NOT EXISTS timeout_seconds INT DEFAULT 300"))
                except Exception:
                    pass
                try:
                    conn.execute(text("ALTER TABLE rpa_logs ADD COLUMN IF NOT EXISTS task_name VARCHAR(100) DEFAULT NULL"))
                except Exception:
                    pass
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS rpa_logs (
                        id              INT AUTO_INCREMENT PRIMARY KEY,
                        task_id         INT NOT NULL DEFAULT 0,
                        task_name       VARCHAR(100),
                        status          VARCHAR(20) NOT NULL,
                        started_at      DATETIME NOT NULL,
                        finished_at     DATETIME,
                        duration_sec    INT,
                        file_path       VARCHAR(500),
                        file_size       BIGINT,
                        etl_status      VARCHAR(20),
                        etl_rows        INT,
                        error_msg       TEXT,
                        error_type      VARCHAR(50),
                        retry_count     INT DEFAULT 0,
                        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES rpa_tasks(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()

                # 初始化 RPA 默认配置（如果不存在）
                rpa_defaults = {
                    "rpa_erp_url": ("https://erp.example.com", "ERP system地址"),
                    "rpa_download_dir": ("./rpa_downloads", "RPA 下载目录"),
                    "rpa_keep_days": ("7", "下载文件保留天数"),
                    "rpa_headless": ("true", "无头模式(服务模式必须true, 调试用false)"),
                    "smtp_host": ("", "SMTP 服务器地址"),
                    "smtp_port": ("465", "SMTP 端口"),
                    "smtp_user": ("", "发件人邮箱"),
                    "smtp_password": ("", "SMTP 授权码/密码"),
                    "smtp_default_to": ("", "默认收件人(逗号分隔)"),
                }
                for key, (value, desc) in rpa_defaults.items():
                    conn.execute(text("""
                        INSERT IGNORE INTO sys_config (config_key, config_value, description, updated_at)
                        VALUES (:key, :val, :desc, NOW())
                    """), {"key": key, "val": value, "desc": desc})
                conn.commit()

            logger.info("RPA 表结构已就绪")
        except Exception as e:
            logger.warning(f"RPA 表初始化: {e}")

        from app.services.rpa_service import start_scheduler
        start_scheduler()

    @app.on_event("shutdown")
    async def shutdown_rpa_scheduler():
        from app.services.rpa_service import stop_scheduler
        stop_scheduler()

    # Global exception handler for page crash logging
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch all unhandled exceptions and log them."""
        try:
            from app.utils.audit import log_page_crash
            # Try to get username from token if available
            username = "anonymous"
            try:
                from app.dependencies import get_current_user
                from app.database import MainSessionLocal
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    # Decode token to get username (with signature verification)
                    import jwt
                    try:
                        from app.config import get_jwt_secret
                        payload = jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
                        username = payload.get("sub", "unknown")
                    except Exception:
                        pass
            except Exception:
                pass

            log_page_crash(username, request.url.path, traceback.format_exc())
        except Exception:
            pass  # Don't let logging failure cause another exception

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    return app


# Create application instance
app = create_app()


# Initialize database on startup (optional - uncomment if needed)
# @app.on_event("startup")
# async def startup_event():
#     init_db()
