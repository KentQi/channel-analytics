"""辅助工具(对应原仓 safe_divide)。"""
from __future__ import annotations

from typing import Union

Number = Union[int, float]


def safe_divide(a: Number, b: Number, default: Number = 0) -> Number:
    """安全除法(对应原仓 safe_divide L112-115)。

    b == 0 / None / NaN → 返回 default
    """
    try:
        if b is None or b == 0:
            return default
    except (TypeError, ValueError):
        return default
    try:
        return a / b  # type: ignore[operator]
    except (TypeError, ValueError, ZeroDivisionError):
        return default


__all__ = ["safe_divide"]
