"""
SQLAlchemy database connection management.
Supports MySQL (production) and SQLite (dev/demo fallback).

- 优先级: `DATABASE_URL` 环境变量 > MySQL 配置文件 > SQLite (./data/demo.db)
- MySQL 不可用时自动降级到 SQLite,让 git clone 后无需 MySQL 也能跑通。
- 通过 `DB_BACKEND` 环境变量强制指定: 'mysql' | 'sqlite'
"""
from __future__ import annotations

import os
import logging
import sqlite3
from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

logger = logging.getLogger(__name__)

# SQLAlchemy declarative base for models
Base = declarative_base()

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "demo.db"


def _probe_mysql(host: str, port: int, user: str, password: str, database: str, timeout: int = 2) -> bool:
    """快速探测 MySQL 是否可用 (2s 超时)"""
    try:
        import pymysql
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, connect_timeout=timeout, charset="utf8mb4",
        )
        conn.close()
        return True
    except Exception as e:
        logger.info(f"MySQL probe failed: {e}")
        return False


def _resolve_database_url() -> str:
    """
    按优先级解析数据库 URL:
    1. DATABASE_URL 环境变量
    2. DB_BACKEND=sqlite 强制 SQLite
    3. DB_BACKEND=mysql 强制 MySQL (无降级)
    4. 默认探测 MySQL → 不可用 → 降级 SQLite
    """
    # 1) 直接环境变量
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        logger.info(f"Using DATABASE_URL env: {env_url.split('@')[-1]}")  # 不打密码
        return env_url

    # 2-3) 强制后端
    forced = os.environ.get("DB_BACKEND", "").lower()
    if forced == "sqlite":
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{DEFAULT_SQLITE_PATH}"
        logger.info(f"DB_BACKEND=sqlite forced, using {url}")
        return url

    # 4) 探测 MySQL
    from app.config import get_db_config
    cfg = get_db_config()
    if cfg["host"] not in ("", "localhost", "127.0.0.1"):
        # 真实 host,探测
        if _probe_mysql(cfg["host"], cfg["port"], cfg["user"], cfg["password"], cfg["database"]):
            url = (
                f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
                f"@{cfg['host']}:{cfg['port']}/{cfg['database']}?charset={cfg['charset']}"
                f"&collation=utf8mb4_unicode_ci"
            )
            logger.info(f"MySQL available, using: {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}")
            return url
        else:
            logger.warning(f"MySQL unreachable at {cfg['host']}:{cfg['port']}, falling back to SQLite")
    else:
        logger.info(f"Default config (host={cfg['host']}), trying SQLite for dev/demo")

    # 5) 降级到 SQLite
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{DEFAULT_SQLITE_PATH}"
    logger.info(f"Using SQLite at {url}")
    return url


# 决定用哪个后端
MAIN_DATABASE_URL = _resolve_database_url()
IS_SQLITE = MAIN_DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    main_engine: Engine = create_engine(
        MAIN_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    main_engine: Engine = create_engine(
        MAIN_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        echo=False,
    )

MainSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=main_engine,
)


# Wholesale database engine (optional, MySQL only)
_ws_engine: Optional[Engine] = None


def get_ws_engine() -> Optional[Engine]:
    """Get or create wholesale database engine lazily. (MySQL only)"""
    global _ws_engine
    if _ws_engine is not None:
        return _ws_engine
    if IS_SQLITE:
        return None  # SQLite 单文件,不分 main/ws
    try:
        from app.config import get_ws_db_config
        ws_db_config = get_ws_db_config()
        WS_DATABASE_URL = (
            f"mysql+pymysql://{ws_db_config['user']}:{ws_db_config['password']}"
            f"@{ws_db_config['host']}:{ws_db_config['port']}"
            f"/{ws_db_config['database']}?charset={ws_db_config['charset']}"
        )
        _ws_engine = create_engine(
            WS_DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            echo=False,
        )
        return _ws_engine
    except Exception:
        _ws_engine = None
        return None


def get_ws_session_local() -> Optional[sessionmaker]:
    ws_engine = get_ws_engine()
    if ws_engine is None:
        return None
    return sessionmaker(autocommit=False, autoflush=False, bind=ws_engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for database sessions.

    Yields:
        Session: SQLAlchemy database session
    """
    db = MainSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions. Outside of FastAPI request context."""
    db = MainSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    # Import models to ensure they are registered with Base
    Base.metadata.create_all(bind=main_engine)
    logger.info(f"init_db done on {'SQLite' if IS_SQLITE else 'MySQL'}: {MAIN_DATABASE_URL}")


def health_check() -> dict:
    """返回 DB 状态 (用于 /api/health)"""
    try:
        with main_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "backend": "sqlite" if IS_SQLITE else "mysql",
            "url_safe": MAIN_DATABASE_URL.split("@")[-1] if "@" in MAIN_DATABASE_URL else MAIN_DATABASE_URL,
            "status": "connected",
        }
    except Exception as e:
        return {
            "backend": "sqlite" if IS_SQLITE else "mysql",
            "status": "disconnected",
            "error": str(e),
        }
