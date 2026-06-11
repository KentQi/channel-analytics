"""ETL 字段清洗纯函数(对应原仓 etl_service.clean_* 系列)。

设计要点:
  - 全部无 DB 依赖,易于单测
  - 清洗规则来自 BusinessRules(已外移到 YAML)
  - 原仓返回 np.nan 的地方 → 新仓统一返回 None
  - 不在函数内打印 / 写日志(让调用方控制可观测性)
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from dateutil import parser as dateutil_parser

from channel_analytics.etl.rules import BusinessRules


# ---------------------------------------------------------------------------
# 1. 批次号
# ---------------------------------------------------------------------------

_BATCH_PREFIX_DROP = ("无", "批次")  # 原仓: startswith 任意一个 → nan


def clean_batch_number(
    batch_str: object,
    rules: BusinessRules | None = None,
) -> Optional[str]:
    """清洗批次号。

    规则(按顺序):
      1. None / NaN → None
      2. strip 后命中 batch_clean_rules 任一项 → None
      3. 以 "无" / "批次" 开头 → None(原仓硬编码)
      4. 其它 → 返回 strip 后的字符串
    """
    rules = rules or BusinessRules.defaults()
    try:
        if batch_str is None or pd.isna(batch_str):
            return None
    except (TypeError, ValueError):
        pass
    text = str(batch_str).strip()
    if text in rules.batch_clean_rules:
        return None
    if text.startswith(_BATCH_PREFIX_DROP):
        return None
    return text


# ---------------------------------------------------------------------------
# 2. 效期
# ---------------------------------------------------------------------------

def clean_expiry_date(
    expiry_str: object,
    rules: BusinessRules | None = None,
) -> Optional[date]:
    """清洗效期。

    规则:
      1. None / NaN → None
      2. strip 后命中 expiry_clean_rules → None
      3. 用 dateutil 解析,失败 → None
      4. 成功 → 返回 date
    """
    rules = rules or BusinessRules.defaults()
    try:
        if expiry_str is None or pd.isna(expiry_str):
            return None
    except (TypeError, ValueError):
        pass
    if str(expiry_str).strip() in rules.expiry_clean_rules:
        return None
    try:
        return dateutil_parser.parse(str(expiry_str)).date()
    except (ValueError, TypeError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# 3. 物料编码
# ---------------------------------------------------------------------------

_MATERIAL_STRIP_CHARS = ("'", "‘", "（仓）", "(仓)")


def clean_material_code(code: object) -> str:
    """清洗物料编码。

    规则:
      1. None / NaN → ""
      2. strip
      3. 去掉引号 / 全角左单引号 / 仓标识
      4. 永远返回 str(空串合法 — 表示"无编码")
    """
    if code is None:
        return ""
    try:
        if pd.isna(code):
            return ""
    except (TypeError, ValueError):
        pass
    out = str(code).strip()
    for token in _MATERIAL_STRIP_CHARS:
        out = out.replace(token, "")
    return out


__all__ = [
    "clean_batch_number",
    "clean_expiry_date",
    "clean_material_code",
]
