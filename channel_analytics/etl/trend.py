"""销售趋势分析(对应原仓 get_material_sales_trend / classify_trend_status)。

设计要点:
  - 4 段窗口:c4 / c3 / c2 / c1(每段 trend_cycle_days 天,c1 为最近一段)
  - 阈值 ratio_threshold / min_change 走 BusinessRules.trend(可被 YAML 覆盖)
  - classify_trend_status 返回 (status_str, return_ratio, c3, c2, c1) 5 元 tuple 对齐原仓
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from channel_analytics.etl.rules import BusinessRules, TrendConfig


# ---------------------------------------------------------------------------
# 1. 4 段销售
# ---------------------------------------------------------------------------

def get_material_sales_trend(
    df_sales_out: pd.DataFrame,
    material_code: str,
    current_date: date,
    rules: BusinessRules | None = None,
) -> list[float]:
    """取 4 段窗口的销售汇总(对应原仓 get_material_sales_trend L410-434)。

    返回 7 元 list:
      [c4, c3, c2, c1, total_send_90d, total_return_90d, total_sales_90d]
      (c4 是 trend_cycle*4 ~ trend_cycle*3 天前;c1 是 0 ~ trend_cycle 天前)

    无销售记录 → [0.0]*7
    """
    rules = rules or BusinessRules.defaults()
    if df_sales_out is None or df_sales_out.empty:
        return [0.0] * 7

    df_m = df_sales_out[df_sales_out["material_code"] == material_code].copy()
    if df_m.empty:
        return [0.0] * 7

    df_m = df_m.dropna(subset=["doc_date"]).copy()
    if df_m.empty:
        return [0.0] * 7
    df_m["doc_date"] = pd.to_datetime(df_m["doc_date"], errors="coerce")

    td = rules.trend_cycle_days
    c1_end = current_date
    c1_start = c1_end - timedelta(days=td)
    c2_start = c1_start - timedelta(days=td)
    c3_start = c2_start - timedelta(days=td)
    c4_start = c3_start - timedelta(days=td)

    def _sum(start: date, end: date) -> float:
        mask = (df_m["doc_date"] >= pd.Timestamp(start)) & (df_m["doc_date"] < pd.Timestamp(end))
        return float(df_m.loc[mask, "sales_out_qty"].sum())

    c4 = _sum(c4_start, c3_start)
    c3 = _sum(c3_start, c2_start)
    c2 = _sum(c2_start, c1_start)
    c1 = _sum(c1_start, c1_end + timedelta(days=1))  # 含当前 end

    sales_90d = [c3, c2, c1]
    total_send_90d = sum(s for s in sales_90d if s > 0)
    total_return_90d = abs(sum(s for s in sales_90d if s < 0))
    total_sales_90d = sum(sales_90d)
    return [c4, c3, c2, c1, total_send_90d, total_return_90d, total_sales_90d]


# ---------------------------------------------------------------------------
# 2. 趋势状态分类
# ---------------------------------------------------------------------------

_TREND_KW_WARN = (
    "迉速下滑", "持续下滑", "迉速冲高后显著回落",
    "冲高后后显著回落", "大幅下滑后显著攀升", "大幅下滑后企稳",
)


def _safe_divide(a: float, b: float, default: float = 0.0) -> float:
    try:
        if b == 0:
            return default
        return a / b
    except (TypeError, ValueError, ZeroDivisionError):
        return default


def classify_trend_status(
    trend_sales: list[float],
    material_stock_total: float = 0,
    rules: BusinessRules | None = None,
) -> tuple[str, float, float, float, float]:
    """趋势分类(对应原仓 classify_trend_status L437-481)。

    返回 5 元 tuple:
      (trend_status, return_ratio, c3, c2, c1)

    注意:原仓 stock_total 入参 **未被使用**(函数体里没有引用),保留仅为了签名兼容。
    """
    rules = rules or BusinessRules.defaults()
    cfg: TrendConfig = rules.trend

    # 兼容长度 < 4 / 全 0 情况
    if len(trend_sales) < 4:
        return ("无明显趋势", 0.0, 0.0, 0.0, 0.0)

    c3, c2, c1 = float(trend_sales[1]), float(trend_sales[2]), float(trend_sales[3])
    total_send = float(trend_sales[4]) if len(trend_sales) > 4 else 0.0
    total_return = float(trend_sales[5]) if len(trend_sales) > 5 else 0.0
    return_ratio = _safe_divide(total_return, total_send)

    mc = cfg.min_change
    c3c = max(c3, mc)
    c2c = max(c2, mc)
    c1c = max(c1, mc)

    r23 = _safe_divide(c2c, c3c)
    r12 = _safe_divide(c1c, c2c)
    R = cfg.ratio_threshold
    Ri = 1.0 / R
    d23 = c2 - c3
    d12 = c1 - c2

    if d23 > mc and d12 > mc:
        basic = "持续上升"
    elif d23 > mc and d12 < -mc:
        basic = "先升后降"
    elif d23 < -mc and d12 > mc:
        basic = "先降后升"
    elif d23 < -mc and d12 < -mc:
        basic = "持续下降"
    else:
        basic = "无明显趋势"

    if basic == "持续上升":
        ts = "迉速攀升" if (r23 >= R or r12 >= R) else "持续攀升"
    elif basic == "先升后降":
        ub = r23 >= R
        db_ = r12 <= Ri
        if ub and db_:
            ts = "迉速冲高后显著回落"
        elif ub and not db_:
            ts = "迉速冲高后企稳"
        elif not ub and db_:
            ts = "冲高后后显著回落"
        else:
            ts = "正常波动"
    elif basic == "先降后升":
        db_ = r23 <= Ri
        ub = r12 >= R
        if db_ and ub:
            ts = "大幅下滑后显著攀升"
        elif db_ and not ub:
            ts = "大幅下滑后企稳"
        elif not ub and ub:  # 原仓 L475 也写了 `not ub and ub`(永真),保留以 1:1 对齐
            ts = "下滑后显著攀升"
        else:
            ts = "正常波动"
    elif basic == "持续下降":
        ts = "迉速下滑" if (r23 <= Ri or r12 <= Ri) else "持续下滑"
    else:
        ts = "无明显趋势"
    return (ts, return_ratio, c3, c2, c1)


def is_trend_warning(trend_status: str) -> str:
    """把 status 字符串映射成 预警/正常(对应原仓 L576-578)。

    新仓独立成函数,便于单元测。
    """
    return "预警" if any(k in trend_status for k in _TREND_KW_WARN) else "正常"


__all__ = [
    "get_material_sales_trend",
    "classify_trend_status",
    "is_trend_warning",
]