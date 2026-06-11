"""W2补 API routers 单测。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from channel_analytics.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# healthz
# ---------------------------------------------------------------------------

def test_healthz():
    c = _client()
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

def test_auth_login_no_authenticator_returns_401():
    """默认 _authenticate 返回 None → 401。"""
    c = _client()
    r = c.post("/auth/login", json={"username": "x", "password": "y"})
    assert r.status_code == 401


def test_auth_me_requires_token():
    c = _client()
    r = c.get("/auth/me")
    assert r.status_code == 401


def test_auth_me_with_valid_token():
    """手动签 token → me 应返回 username + role。"""
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice", extra={"role": "admin"})
    c = _client()
    r = c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"
    assert r.json()["role"] == "admin"


def test_auth_me_with_invalid_token():
    c = _client()
    r = c.get("/auth/me", headers={"Authorization": "Bearer bogus.token.here"})
    assert r.status_code == 401


def test_auth_logout_returns_204():
    c = _client()
    r = c.post("/auth/logout")
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# rpa tasks
# ---------------------------------------------------------------------------

def test_rpa_list_tasks_empty():
    c = _client()
    # 无 token → 401
    r = c.get("/rpa/tasks")
    assert r.status_code == 401


def test_rpa_task_lifecycle_with_auth():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    headers = {"Authorization": f"Bearer {token}"}

    # 创建
    r = c.post(
        "/rpa/tasks",
        json={"name": "task1", "module_names": ["m1", "m2"], "is_active": False},
        headers=headers,
    )
    assert r.status_code == 201
    task_id = r.json()["id"]

    # 列出
    r = c.get("/rpa/tasks", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # 详情
    r = c.get(f"/rpa/tasks/{task_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "task1"

    # 触发
    r = c.post(f"/rpa/tasks/{task_id}/run", headers=headers)
    assert r.status_code == 202
    assert r.json()["status"] == "queued"


def test_rpa_task_404():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/rpa/tasks/999", headers=headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# etl
# ---------------------------------------------------------------------------

def test_etl_pipeline_endpoint():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    r = c.get("/etl/pipeline", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 12  # DefaultPipeline 12 steps


def test_etl_run_returns_202():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    r = c.post(
        "/etl/run",
        json={"raw_data": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 202
    assert "run_id" in r.json()


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------

def test_reports_list():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    r = c.get("/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 7  # 7 RPT


def test_reports_catalog():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    r = c.get("/reports/catalog", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "rpt_expiry_warning" in r.json()


def test_reports_query_unknown():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    r = c.get("/reports/ghost", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_reports_query_known():
    from channel_analytics.api.deps import create_access_token
    token = create_access_token("alice")
    c = _client()
    r = c.get(
        "/reports/rpt_expiry_warning?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "rpt_expiry_warning"
    assert body["limit"] == 10
    assert body["rows"] == []


# ---------------------------------------------------------------------------
# password helpers
# ---------------------------------------------------------------------------

def test_hash_and_verify_password():
    from channel_analytics.api.deps import hash_password, verify_password
    h = hash_password("secret")
    assert verify_password("secret", h) is True
    assert verify_password("wrong", h) is False


def test_verify_password_invalid_format():
    from channel_analytics.api.deps import verify_password
    assert verify_password("anything", "bogus_format") is False
    assert verify_password("anything", "") is False