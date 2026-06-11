"""pytest configuration — channel-analytics(W2 净化版)

设计原则(对应 PLAN.md §4 + §6 P0):
  - 0 真实凭据:不出现真实用户名/密码等具体值
  - 0 真实数据库连接:默认 SQLite in-memory,fixture 隔离
  - 0 真实依赖:TestClient + httpx,无外部服务
  - 工厂函数:在 conftest 里只放基础设施;具体 factory 留 W4

fixture 清单(W2 提供):
  - app()         : FastAPI 实例(覆盖 .env 用临时配置)
  - client()      : TestClient
  - temp_settings(): 临时 .env,使用 SQLite in-memory

W4 升级:补 factory-boy + parametrize,接入 conftest.py
"""
from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 环境隔离:在 import app 之前,把 DATABASE_URL 指向 in-memory SQLite
# 把 SESSION/JWT 设为生成的 64 字符随机串,避免任何占位符
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_test_env() -> Iterator[None]:
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("SESSION_SECRET", secrets.token_urlsafe(48))
    os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
    # 让 config 缓存读到这些值
    try:
        from channel_analytics.config import reset_settings_cache
        reset_settings_cache()
    except ImportError:  # pragma: no cover  W2 早期允许
        pass
    yield


@pytest.fixture
def app():
    """FastAPI app 实例。"""
    from channel_analytics.api import create_app
    return create_app()


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    """TestClient,W4 之后会改用 httpx.AsyncClient。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tmp_env_file(tmp_path: Path) -> Path:
    """生成一个临时 .env(只用于 config 单元测试)。"""
    env = tmp_path / ".env"
    env.write_text(
        "SESSION_SECRET=test-session-secret-32-chars-xxxxxx\n"
        "JWT_SECRET=test-jwt-secret-32-chars-xxxxxxxxx\n"
        "DATABASE_URL=sqlite:///:memory:\n",
        encoding="utf-8",
    )
    return env
