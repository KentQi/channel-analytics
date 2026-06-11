#!/usr/bin/env bash
# channel-analytics 生产启动脚本
#
# 启动顺序:
#   1. 跑 Alembic 迁移(自动建表)
#   2. 启动 uvicorn
#
# ⚠️ 入口说明:
#   - `app.main:app`  (原仓平移,17 routers,完整业务)  ← 推荐生产用这个
#   - `channel_analytics.api.app:app` (W3-W7 抽象层,4 routers 占位)
# 部署方可按需切换,但需保证 routers 完整注册

set -euo pipefail

echo "[start.sh] running alembic upgrade head..."
alembic upgrade head

echo "[start.sh] starting uvicorn on 0.0.0.0:8000..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_WORKERS:-2}" \
    --log-level "${LOG_LEVEL:-info}"