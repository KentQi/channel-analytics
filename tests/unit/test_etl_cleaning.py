"""W4 字段清洗单测 — 3 个纯函数 × 4 类用例。"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from channel_analytics.etl.cleaning import (
    clean_batch_number,
    clean_expiry_date,
    clean_material_code,
)
from channel_analytics.etl.rules import BusinessRules


# ---------------------------------------------------------------------------
# clean_batch_number
# ---------------------------------------------------------------------------

class TestCleanBatchNumber:
    def test_normal_value_preserved(self):
        assert clean_batch_number("B20250101") == "B20250101"

    def test_strip_whitespace(self):
        assert clean_batch_number("  B2025  ") == "B2025"

    def test_none_returns_none(self):
        assert clean_batch_number(None) is None

    def test_nan_returns_none(self):
        assert clean_batch_number(np.nan) is None
        assert clean_batch_number(pd.NA) is None

    @pytest.mark.parametrize("bad", ["", " ", "NA", "/", "\\", "无", "虚拟退货"])
    def test_clean_rules_match(self, bad):
        """BusinessRules.batch_clean_rules 内的字符串都返回 None。"""
        assert clean_batch_number(bad) is None

    @pytest.mark.parametrize("bad", ["无效", "无标", "批次001", "批次X"])
    def test_prefix_drops(self, bad):
        """原仓硬编码:以 '无' / '批次' 开头 → None。"""
        assert clean_batch_number(bad) is None

    def test_custom_rules_override(self):
        """从 dict 加载可加新规则。"""
        rules = BusinessRules.from_dict({"batch_clean_rules": ["QQQ"]})
        assert clean_batch_number("QQQ", rules=rules) is None
        assert clean_batch_number("B2025", rules=rules) == "B2025"


# ---------------------------------------------------------------------------
# clean_expiry_date
# ---------------------------------------------------------------------------

class TestCleanExpiryDate:
    def test_iso_date(self):
        assert clean_expiry_date("2025-12-31") == date(2025, 12, 31)

    def test_chinese_format(self):
        """dateutil 应能解析 "2025/12/31" 等常见格式。"""
        assert clean_expiry_date("2025/12/31") == date(2025, 12, 31)

    def test_none_returns_none(self):
        assert clean_expiry_date(None) is None

    def test_nan_returns_none(self):
        assert clean_expiry_date(np.nan) is None

    @pytest.mark.parametrize("bad", ["", " ", "NA", "n/a"])
    def test_clean_rules_match(self, bad):
        assert clean_expiry_date(bad) is None

    @pytest.mark.parametrize("bad", ["not-a-date", "2099-13-99", "abc"])
    def test_unparseable_returns_none(self, bad):
        assert clean_expiry_date(bad) is None

    def test_datetime_object_returns_date(self):
        """dateutil 也能从 datetime 字符串中提日期。"""
        result = clean_expiry_date("2025-01-01 10:30:00")
        assert result == date(2025, 1, 1)


# ---------------------------------------------------------------------------
# clean_material_code
# ---------------------------------------------------------------------------

class TestCleanMaterialCode:
    def test_normal_preserved(self):
        assert clean_material_code("MAT-001") == "MAT-001"

    def test_none_returns_empty(self):
        assert clean_material_code(None) == ""

    def test_nan_returns_empty(self):
        assert clean_material_code(np.nan) == ""

    def test_strip_whitespace(self):
        assert clean_material_code("  MAT-001  ") == "MAT-001"

    @pytest.mark.parametrize("raw,expected", [
        ("MAT'001", "MAT001"),
        ("MAT‘001", "MAT001"),       # 全角左单引号
        ("MAT001（仓）", "MAT001"),   # 全角仓
        ("MAT001(仓)", "MAT001"),     # 半角仓
    ])
    def test_token_stripping(self, raw, expected):
        assert clean_material_code(raw) == expected

    def test_returns_str_always(self):
        """非空清洗结果必须是 str(可空串)。"""
        result = clean_material_code(12345)  # 数字输入
        assert result == "12345"
        assert isinstance(result, str)
