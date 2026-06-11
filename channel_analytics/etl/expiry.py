"""效期计算与状态分类(对应原仓 calculate_expiry_months / classify_expiry_status)。

设计要点:
  - 全部纯函数,无 DB 依赖
  - current_date 由调用方注入(原仓走 ETLConfig.CURRENT_DATE_DT 模块全局)
  - 返回值在边界上保持 Pythonic:
      * 月份差 None / NaN → 未知
      * 数字(可为负)
      * 状态字符串
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta


# ---------------------------------------------------------------------------
# 1. 月份差
# ---------------------------------------------------------------------------

def calculate_expiry_months(
    expiry_date: object,
    current_date: date,
) -> Optional[int]:
    """计算 expiry_date 距 current_date 的月数(整月,负数表示已过期)。

    规则:
      1. None / NaN → None
      2. 接受 date / datetime / pd.Timestamp
      3. 其它类型 → 尝试 pd.Timestamp(expiry_date)
      4. 解析失败 → None
      5. relativedelta 的 years*12 + months(忽略 days — 跟原仓行为一致)
    """
    try:
        if expiry_date is None or pd.isna(expiry_date):
            return None
    except (TypeError, ValueError):
        pass

    try:
        if isinstance(expiry_date, datetime):
            expiry_dt = expiry_date
        elif hasattr(expiry_date, "date") and not isinstance(expiry_date, datetime):
            # date 对象
            expiry_dt = datetime.combine(expiry_date, datetime.min.time())  # type: ignore[arg-type]
        else:
            expiry_dt = pd.Timestamp(expiry_date).to_pydatetime()
        current_dt = datetime.combine(current_date, datetime.min.time())
        delta = relativedelta(expiry_dt, current_dt)
        return int(delta.years * 12 + delta.months)
    except (ValueError, TypeError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# 2. 状态分类
# ---------------------------------------------------------------------------

# (下限月数(含), 标签) — 按降序
_EXPIRY_BANDS: tuple[tuple[int, str], ...] = (
    (32, "效期极佳(32+)"),
    (28, "效期优秀(28-32)"),
    (24, "效期良好(24-28)"),
    (18, "效期一般(18-24)"),
    (12, "效期较差(12-18)"),
    (6, "效期很差(6-12)"),
    (0, "效期临期(0-6)"),
)
_UNKNOWN = "未知"
_EXPIRED = "过期(0-)"


def classify_expiry_status(months: object) -> str:
    """根据月数返回效期档位(对应原仓 classify_expiry_status)。

    边界对照(原仓 L145-152):
      months >= 32  → 效期极佳
      28 <= m < 32  → 效期优秀
      ...
      0  <= m <  6  → 效期临期
      m < 0         → 过期
      None / NaN    → 未知
      其它类型      → 未知
    """
    try:
        if months is None or pd.isna(months):
            return _UNKNOWN
    except (TypeError, ValueError):
        return _UNKNOWN
    if not isinstance(months, (int, float)):
        return _UNKNOWN
    if months < 0:
        return _EXPIRED
    for lower, label in _EXPIRY_BANDS:
        if months >= lower:
            return label
    return _EXPIRED  # 兜底(理论上不会到这里)


__all__ = [
    "calculate_expiry_months",
    "classify_expiry_status",
]
