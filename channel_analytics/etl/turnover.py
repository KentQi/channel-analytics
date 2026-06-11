"""库存周转天数计算与状态分类(对应原仓 calculate_inventory_days / classify_turnover_status)。

设计要点:
  - 全部纯函数,无 DB 依赖
  - cycle_days / sentinel / bands 全部从 BusinessRules 注入(原仓硬编码 90 / 999)
  - 返回值在边界上保持 Pythonic:
      * None / NaN 输入 → None(可销库存) / "无库存数据"(状态)
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from channel_analytics.etl.rules import BusinessRules, TurnoverBand


# ---------------------------------------------------------------------------
# 1. 周转天数
# ---------------------------------------------------------------------------

def calculate_inventory_days(
    available_qty_total: object,
    sales_cycle_total: object,
    rules: BusinessRules | None = None,
) -> Optional[float]:
    """计算库存周转天数(对应原仓 calculate_inventory_days L155-167)。

    规则:
      1. available_qty_total <= 0 或 NaN → None(无可销库存)
      2. sales_cycle_total <= 0 或 NaN → rules.inventory_days_sentinel(无销售 = 永久积压)
      3. daily_sales <= 0 → sentinel
      4. 其它 → available_qty / daily_sales
    """
    rules = rules or BusinessRules.defaults()
    try:
        if available_qty_total is None or pd.isna(available_qty_total):
            return None
    except (TypeError, ValueError):
        return None
    try:
        if float(available_qty_total) <= 0:
            return None
    except (TypeError, ValueError):
        return None

    try:
        if sales_cycle_total is None or pd.isna(sales_cycle_total):
            return rules.inventory_days_sentinel
        if float(sales_cycle_total) <= 0:
            return rules.inventory_days_sentinel
    except (TypeError, ValueError):
        return rules.inventory_days_sentinel

    cycle_days = rules.turnover_cycle_days
    if cycle_days <= 0:
        return rules.inventory_days_sentinel  # 防御
    daily_sales = float(sales_cycle_total) / cycle_days
    if daily_sales <= 0:
        return rules.inventory_days_sentinel
    return float(available_qty_total) / daily_sales


# ---------------------------------------------------------------------------
# 2. 状态分类
# ---------------------------------------------------------------------------

def classify_turnover_status(
    days: object,
    rules: BusinessRules | None = None,
) -> str:
    """根据天数返回周转档位(对应原仓 classify_turnover_status L170-180)。

    边界:
      None / NaN / 非数值  → "无库存数据"
      days >= sentinel      → "周转高(>90天)" (匹配最高档)
      0  <= days <  30      → "周转健康(<30天)"
      30 <= days <  60      → "周转正常(30-60天)"
      60 <= days <  90      → "周转偏低(60-90天)"
      90 <= days            → "周转高(>90天)"
    """
    rules = rules or BusinessRules.defaults()
    try:
        if days is None or pd.isna(days):
            return "无库存数据"
    except (TypeError, ValueError):
        return "无库存数据"
    if not isinstance(days, (int, float, np.integer, np.floating)):
        return "无库存数据"
    days_f = float(days)
    # sentinel 视为"无销售"区间
    if days_f >= rules.inventory_days_sentinel:
        # 取最高档
        return rules.turnover_status_bands[-1].label
    for band in rules.turnover_status_bands:
        if band.contains(days_f):
            return band.label
    return rules.turnover_status_bands[-1].label  # 兜底


__all__ = [
    "calculate_inventory_days",
    "classify_turnover_status",
]
