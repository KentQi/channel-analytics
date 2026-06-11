"""W5-1a/b 单测 — 效期计算与状态分类。"""
from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from channel_analytics.etl.expiry import (
    calculate_expiry_months,
    classify_expiry_status,
)


# ---------------------------------------------------------------------------
# calculate_expiry_months
# ---------------------------------------------------------------------------

class TestCalculateExpiryMonths:
    CD = date(2026, 6, 10)

    def test_expiry_24_months_later(self):
        """过 24 个月整 → 24"""
        assert calculate_expiry_months(date(2028, 6, 10), self.CD) == 24

    def test_expiry_in_past_returns_negative(self):
        """已过效期 → 负数"""
        assert calculate_expiry_months(date(2025, 1, 1), self.CD) == -17

    def test_same_month_returns_zero(self):
        """当月效期 → 0"""
        assert calculate_expiry_months(date(2026, 6, 1), self.CD) == 0

    def test_partial_month_truncates_to_zero(self):
        """不足 1 整月 → 0(原仓 relativedelta 行为)"""
        assert calculate_expiry_months(date(2026, 6, 25), self.CD) == 0

    def test_none_returns_none(self):
        assert calculate_expiry_months(None, self.CD) is None

    def test_nan_returns_none(self):
        assert calculate_expiry_months(np.nan, self.CD) is None
        assert calculate_expiry_months(pd.NA, self.CD) is None

    def test_unparseable_returns_none(self):
        assert calculate_expiry_months("not-a-date", self.CD) is None
        assert calculate_expiry_months([], self.CD) is None

    def test_datetime_input_accepted(self):
        """datetime 对象直接接受。"""
        assert calculate_expiry_months(datetime(2028, 6, 10), self.CD) == 24

    def test_iso_string_accepted(self):
        """字符串通过 pd.Timestamp 解析。"""
        assert calculate_expiry_months("2028-06-10", self.CD) == 24


# ---------------------------------------------------------------------------
# classify_expiry_status
# ---------------------------------------------------------------------------

class TestClassifyExpiryStatus:
    @pytest.mark.parametrize("months,expected", [
        (40, "效期极佳(32+)"),
        (32, "效期极佳(32+)"),
        (31, "效期优秀(28-32)"),
        (28, "效期优秀(28-32)"),
        (27, "效期良好(24-28)"),
        (24, "效期良好(24-28)"),
        (23, "效期一般(18-24)"),
        (18, "效期一般(18-24)"),
        (17, "效期较差(12-18)"),
        (12, "效期较差(12-18)"),
        (11, "效期很差(6-12)"),
        (6, "效期很差(6-12)"),
        (5, "效期临期(0-6)"),
        (0, "效期临期(0-6)"),
        (-1, "过期(0-)"),
        (-100, "过期(0-)"),
    ])
    def test_band_boundaries(self, months, expected):
        """每个分段的上下界都要测。"""
        assert classify_expiry_status(months) == expected

    def test_none_returns_unknown(self):
        assert classify_expiry_status(None) == "未知"

    def test_nan_returns_unknown(self):
        assert classify_expiry_status(np.nan) == "未知"
        assert classify_expiry_status(pd.NA) == "未知"

    def test_invalid_type_returns_unknown(self):
        assert classify_expiry_status("not-a-number") == "未知"
        assert classify_expiry_status([1, 2]) == "未知"
