"""核心 ETL 纯函数单元测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from app.services.etl_service import (
    clean_batch_number,
    clean_material_code,
    clean_expiry_date,
    safe_divide,
    calculate_expiry_months,
    classify_expiry_status,
    calculate_inventory_days,
    classify_turnover_status,
)
from app.services.data_service import (
    clean_value,
    validate_enum,
)
from app.services.field_mapping import ABC_VALID, LIFECYCLE_VALID, CUST_CHANNEL_VALID


# ========== clean_batch_number ==========
class TestCleanBatchNumber:
    def test_normal_batch(self):
        assert clean_batch_number("B20250101") == "B20250101"

    def test_empty_returns_nan(self):
        assert clean_batch_number("") is np.nan

    def test_none_returns_nan(self):
        assert clean_batch_number(None) is np.nan

    def test_na_returns_nan(self):
        assert clean_batch_number(np.nan) is np.nan

    def test_virtual_return_returns_nan(self):
        assert clean_batch_number("虚拟退货") is np.nan

    def test_whitespace_returns_nan(self):
        assert clean_batch_number(" ") is np.nan


# ========== clean_material_code ==========
class TestCleanMaterialCode:
    def test_normal_code(self):
        assert clean_material_code("6901234567890") == "6901234567890"

    def test_with_quotes(self):
        assert clean_material_code("'6901234'") == "6901234"

    def test_with_warehouse_suffix(self):
        assert clean_material_code("6901234（仓）") == "6901234"

    def test_none(self):
        assert clean_material_code(None) == ""

    def test_nan(self):
        assert clean_material_code(np.nan) == ""


# ========== safe_divide ==========
class TestSafeDivide:
    def test_normal(self):
        assert safe_divide(10, 2) == 5.0

    def test_divide_by_zero(self):
        assert safe_divide(10, 0) == 0.0

    def test_divide_by_nan(self):
        assert safe_divide(10, np.nan) == 0.0


# ========== classify_expiry_status ==========
class TestClassifyExpiryStatus:
    def test_36_months(self):
        assert classify_expiry_status(36) == "效期极佳(32+)"

    def test_6_months(self):
        assert classify_expiry_status(6) == "效期很差(6-12)"

    def test_negative(self):
        assert classify_expiry_status(-1) == "过期（0-）"

    def test_none(self):
        assert classify_expiry_status(None) == "未知"

    def test_nan(self):
        assert classify_expiry_status(np.nan) == "未知"


# ========== classify_turnover_status ==========
class TestClassifyTurnoverStatus:
    def test_15_days(self):
        assert classify_turnover_status(15) == "周转健康(<30天)"

    def test_45_days(self):
        assert classify_turnover_status(45) == "周转正常(30-60天)"

    def test_999_days(self):
        assert classify_turnover_status(999) == "周转高(>90天)"

    def test_none(self):
        assert classify_turnover_status(None) == "无库存数据"


# ========== calculate_inventory_days ==========
class TestCalculateInventoryDays:
    def test_normal(self):
        result = calculate_inventory_days(900, 90)
        assert result == 900.0  # 900 / (90/90) = 900

    def test_no_stock(self):
        assert np.isnan(calculate_inventory_days(0, 90))

    def test_no_sales(self):
        assert calculate_inventory_days(900, 0) == 999.0


# ========== clean_value (data_service) ==========
class TestCleanValue:
    def test_normal_string(self):
        assert clean_value("hello") == "hello"

    def test_empty_string(self):
        assert clean_value("") is None

    def test_none(self):
        assert clean_value(None) is None

    def test_whitespace(self):
        assert clean_value("  hello  ") == "hello"


# ========== validate_enum (data_service) ==========
class TestValidateEnum:
    def test_valid_value(self):
        assert validate_enum("引流品", list(ABC_VALID), "ABC分类") is None

    def test_invalid_value(self):
        result = validate_enum("xxx", list(ABC_VALID), "ABC分类")
        assert "ABC分类" in result

    def test_empty_value(self):
        assert validate_enum("", list(ABC_VALID), "ABC分类") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
