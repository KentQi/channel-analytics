"""SQLAlchemy declarative Base — 所有 ORM 模型的根。"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的根。新仓用 SQLAlchemy 2.x 风格 declarative_base。"""

    pass