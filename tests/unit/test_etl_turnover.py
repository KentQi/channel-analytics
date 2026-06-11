"""W5-2 单测 — 周转天数 + 状态分类。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from channel_analytics.etl.rules import BusinessRules, TurnoverBand
from channel_analytics.etl.turnover import (
    calculate_inventory_days,
    classify_turnover_status,
)


# ---------------------------------------------------------------------------
# calculate_inventory_days
# ---------------------------------------------------------------------------

class TestCalculateInventoryDays:
    RULES = BusinessRules.defaults()  # cycle=90, sentinel=999.0

    def test_normal_case(self):
        """库存 1000,90 天销 300 → 1000 / (300/90) = 300 天"""
        assert calculate_inventory_days(1000, 300, self.RULES) == pytest.approx(300.0)

    def test_zero_inventory_returns_none(self):
        """库存 0 → None(无可销库存)"""
        assert calculate_inventory_days(0, 300, self.RULES) is None

    def test_negative_inventory_returns_none(self):
        assert calculate_inventory_days(-10, 300, self.RULES) is None

    def test_zero_sales_returns_sentinel(self):
        """无销售 → sentinel(999.0)"""
        assert calculate_inventory_days(1000, 0, self.RULES) == 999.0
        assert calculate_inventory_days(1000, -5, self.RULES) == 999.0

    def test_nan_sales_returns_sentinel(self):
        assert calculate_inventory_days(1000, np.nan, self.RULES) == 999.0
        assert calculate_inventory_days(1000, pd.NA, self.RULES) == 999.0

    def test_nan_inventory_returns_none(self):
        assert calculate_inventory_days(np.nan, 300, self.RULES) is None
        assert calculate_inventory_days(pd.NA, 300, self.RULES) is None

    def test_none_inputs(self):
        assert calculate_inventory_days(None, 300, self.RULES) is None
        assert calculate_inventory_days(1000, None, self.RULES) == 999.0

    def test_custom_cycle_days(self):
        """cycle_days=30 时,库存 100, 30 天销 60 → 100/2 = 50 天"""
        rules = BusinessRules.from_dict({"turnover_cycle_days": 30})
        assert calculate_inventory_days(100, 60, rules) == 50.0

    def test_invalid_inputs_return_none_or_sentinel(self):
        """字符串数字等异常输入 → 走 None / sentinel 兜底,不抛异常。"""
        assert calculate_inventory_days([], 300, self.RULES) is None
        assert calculate_inventory_days(1000, "bad", self.RULES) == 999.0


# ---------------------------------------------------------------------------
# classify_turnover_status
# ---------------------------------------------------------------------------

class TestClassifyTurnoverStatus:
    RULES = BusinessRules.defaults()  # sentinel=999

    @pytest.mark.parametrize("days,expected", [
        (0, "周转健康(<30天)"),
        (15, "周转健康(<30天)"),
        (29, "周转健康(<30天)"),
        (30, "周转正常(30-60天)"),
        (45, "周转正常(30-60天)"),
        (59, "周转正常(30-60天)"),
        (60, "周转偏低(60-90天)"),
        (75, "周转偏低(60-90天)"),
        (89, "周转偏低(60-90天)"),
        (90, "周转高(>90天)"),
        (200, "周转高(>90天)"),
        (998, "周转高(>90天)"),
        (999, "周转高(>90天)"),   # sentinel 也归最高档
        (10000, "周转高(>90天)"),
    ])
    def test_band_boundaries(self, days, expected):
        assert classify_turnover_status(days, self.RULES) == expected

    def test_none_returns_no_data(self):
        assert classify_turnover_status(None, self.RULES) == "无库存数据"

    def test_nan_returns_no_data(self):
        assert classify_turnover_status(np.nan, self.RULES) == "无库存数据"
        assert classify_turnover_status(pd.NA, self.RULES) == "无库存数据"

    def test_invalid_type_returns_no_data(self):
        assert classify_turnover_status("30", self.RULES) == "无库存数据"
        assert classify_turnover_status([30], self.RULES) == "无库存数据"

    def test_custom_bands_override(self):
        """YAML 改 bands 后,新档位生效。"""
        rules = BusinessRules.from_dict({
            "turnover_status_bands": [
                {"upper": 14, "label": "高速(0-14)"},
                {"upper": 45, "label": "中速(14-45)"},
                {"upper": float("inf"), "label": "慢速(>45)"},
            ],
        })
        assert classify_turnover_status(10, rules) == "高速(0-14)"
        assert classify_turnover_status(30, rules) == "中速(14-45)"
        assert classify_turnover_status(100, rules) == "慢速(>45)"

    def test_invalid_bands_fall_back_to_defaults(self):
        """YAML 写非法 bands → 走 defaults,不抛异常。"""
        rules = BusinessRules.from_dict({
            "turnover_status_bands": [{"upper": "bad", "label": "x"}],  # 缺 label + 非法 upper
        })
        # 兜底到 defaults
        assert classify_turnover_status(15, rules) == "周转健康(<30天)"


# ---------------------------------------------------------------------------
# TurnoverBand 单元
# ---------------------------------------------------------------------------

class TestTurnoverBand:
    def test_contains_inclusive_zero_exclusive_upper(self):
        b = TurnoverBand(30, "x")
        assert b.contains(0) is True
        assert b.contains(29.9) is True
        assert b.contains(30) is False

    def test_contains_negative(self):
        b = TurnoverBand(30, "x")
        assert b.contains(-1) is False
