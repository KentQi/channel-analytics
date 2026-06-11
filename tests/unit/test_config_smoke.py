"""W2 端到端冒烟:占位符 + healthz + .env 写入"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_refuse_to_start_when_placeholder(monkeypatch, tmp_path: Path):
    """没有 init-secrets 时,get_settings() 必须 raise RefuseToStart。"""
    env = tmp_path / ".env"
    env.write_text(
        "SESSION_SECRET=GENERATE-ON-FIRST-RUN\n"
        "JWT_SECRET=GENERATE-ON-FIRST-RUN\n"
        "DATABASE_URL=sqlite:///:memory:\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SESSION_SECRET", "GENERATE-ON-FIRST-RUN")
    monkeypatch.setenv("JWT_SECRET", "GENERATE-ON-FIRST-RUN")
    # 重新加载(因为 cache)
    from channel_analytics.config import RefuseToStart, get_settings, reset_settings_cache
    reset_settings_cache()
    with pytest.raises(RefuseToStart) as exc:
        get_settings()
    assert "placeholder" in str(exc.value).lower()


def test_init_secrets_replaces_placeholders(tmp_path: Path, monkeypatch):
    """init_secrets() 应当把 .env.example 复制为 .env 并替换占位符。"""
    monkeypatch.chdir(tmp_path)
    # 写 .env.example
    (tmp_path / ".env.example").write_text(
        "SESSION_SECRET=GENERATE-ON-FIRST-RUN\n"
        "JWT_SECRET=GENERATE-ON-FIRST-RUN\n"
        "DATABASE_URL=sqlite:///:memory:\n",
        encoding="utf-8",
    )
    from channel_analytics.config.secrets import init_secrets
    n = init_secrets()
    assert n == 2
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GENERATE-ON-FIRST-RUN" not in env_text
    # 长度应 >= 64 字符(token_urlsafe(48) 约 64)
    for line in env_text.splitlines():
        if line.startswith("SESSION_SECRET="):
            assert len(line.split("=", 1)[1].split()[0]) >= 64
