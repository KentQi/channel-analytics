"""channel_analytics.config — pydantic-settings 配置层

设计目标(PLAN.md §2.4.5 + W2-1):
  - 加载 .env(.env.example 是模板)
  - 提供 SecretStr 类型,SESSION_SECRET / JWT_SECRET 等不出现在日志
  - 启动时由 channel_analytics.cli init-secrets 自动生成 placeholder 替换
  - 任何值还是占位符 "GENERATE-ON-FIRST-RUN" 时,get_settings() raise

使用:
    from channel_analytics.config import get_settings
    settings = get_settings()  # 失败时 RefuseToStart 异常
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDER = "GENERATE-ON-FIRST-RUN"


class RefuseToStart(RuntimeError):
    """配置含占位符或默认值,拒绝启动。运行 `channel-analytics init-secrets` 修复。"""


class Settings(BaseSettings):
    """主配置。所有密钥字段为 SecretStr(日志/traceback 中显示为 '****')。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 安全 ----------
    session_secret: SecretStr
    jwt_secret: SecretStr
    app_secret: SecretStr | None = None

    # ---------- 数据库 ----------
    database_url: str = "sqlite:///./data/dev.db"

    # ---------- 应用 ----------
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    default_timezone: str = "Asia/Shanghai"

    # ---------- ETL(品牌白名单 / 业务规则) ----------
    # brand_provider 走 entry_points `channel_analytics.brand_providers`
    # 默认 ExampleMinimalProvider(返回空集,真实词条由部署环境注入)
    brand_provider: str = (
        "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
    )
    # business_rules YAML 路径(空 = 用代码内默认 BusinessRules.defaults())
    business_rules_path: str = ""

    # ---------- RPA(通用,无厂商) ----------
    rpa_adapter: str = (
        "channel_analytics.rpa.adapters.example_minimal:ExampleMinimalAdapter"
    )
    rpa_target_url: str = ""
    rpa_username: str = ""
    rpa_password: SecretStr | None = None
    rpa_download_dir: Path = Path("./data/rpa_downloads")
    rpa_headless: bool = True
    rpa_timeout_ms: int = 30_000
    rpa_slow_mo_ms: int = 300

    # ---------- SMTP(可选) ----------
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr | None = None
    smtp_from: str = ""
    smtp_to: str = ""

    @field_validator("database_url")
    @classmethod
    def _validate_db_url(cls, v: str) -> str:
        if not v or v == PLACEHOLDER:
            raise RefuseToStart(
                "DATABASE_URL is unset or still placeholder. "
                "Edit .env to set a real connection string."
            )
        return v

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"invalid log level: {v}")
        return v


def _ensure_real_secrets(settings: Settings) -> None:
    """检查 SecretStr 字段不是占位符。

    规则:
      - 字段值 == PLACEHOLDER  -> 阻断(必须 init-secrets)
      - 字段为空字符串         -> 允许(可选字段,如 rpa_password)
      - 字段未设置(None)       -> 允许
    """
    bad: list[str] = []
    for name in ("session_secret", "jwt_secret", "app_secret", "rpa_password"):
        val = getattr(settings, name, None)
        if val is None:
            continue
        try:
            raw = val.get_secret_value()
        except Exception:  # pragma: no cover
            continue
        if raw == PLACEHOLDER:
            bad.append(name)
    if bad:
        raise RefuseToStart(
            f"Security secrets are unset or still placeholder: {', '.join(bad)}. "
            "Run:  channel-analytics init-secrets   (or manually edit .env)"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """加载并校验配置。失败时 raise RefuseToStart(带清晰提示)。"""
    settings = Settings()  # type: ignore[call-arg]
    _ensure_real_secrets(settings)
    return settings


def reset_settings_cache() -> None:
    """测试时用:清缓存让 get_settings() 重新读 .env。"""
    get_settings.cache_clear()
