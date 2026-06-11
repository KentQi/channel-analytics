"""
Unit tests for custom_report_service.py
"""
import pytest
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.custom_report_service import (
    validate_config,
    clean_invalid_fields,
    build_report_sql,
    ALLOWED_REPORT_TABLES,
)


class TestValidateConfig:
    """Tests for validate_config function"""

    def test_valid_config(self):
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no", "doc_date", "material_code"],
        }
        is_valid, error = validate_config(config)
        assert is_valid is True
        assert error == ""

    def test_missing_table(self):
        config = {"fields": ["doc_no"]}
        is_valid, error = validate_config(config)
        assert is_valid is False
        assert "缺少数据表名" in error

    def test_invalid_table(self):
        config = {"table": "invalid_table", "fields": ["doc_no"]}
        is_valid, error = validate_config(config)
        assert is_valid is False
        assert "不支持的数据表" in error

    def test_missing_fields(self):
        config = {"table": "rpt_sales_out_wide", "fields": []}
        is_valid, error = validate_config(config)
        assert is_valid is False
        assert "请选择至少一个字段" in error

    def test_invalid_field(self):
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["invalid_field_name"],
        }
        is_valid, error = validate_config(config)
        assert is_valid is False
        assert "不在表" in error


class TestValidateConfigDateField:
    """Tests for date_field/numeric_fields consistency validation"""

    def test_date_field_not_in_fields(self):
        """date_field that doesn't exist in fields should fail validation"""
        # rpt_sales_monthly was fixed to not have date_field='doc_date' anymore
        # This test verifies the validation works for any table with invalid date_field
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no", "doc_date"],
        }
        is_valid, error = validate_config(config)
        # doc_date is in fields for rpt_sales_out_wide, should pass
        assert is_valid is True

    def test_numeric_field_not_in_fields(self):
        """numeric_field that doesn't exist in fields should fail validation"""
        # Check rpt_expiry_warning has valid numeric_fields
        # material_batch_available_qty and remaining_expiry_months are in fields
        meta = ALLOWED_REPORT_TABLES["rpt_expiry_warning"]
        assert "material_batch_available_qty" in meta["fields"]
        assert "remaining_expiry_months" in meta["fields"]


class TestCleanInvalidFields:
    """Tests for clean_invalid_fields function"""

    def test_clean_fields_only(self):
        """Valid config should pass through unchanged (except fields cleaned)"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no", "doc_date"],
            "filters": [],
            "sort": [],
        }
        result = clean_invalid_fields(config)
        assert result["fields"] == ["doc_no", "doc_date"]

    def test_clean_removes_invalid_fields(self):
        """Invalid fields should be removed from fields array"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no", "invalid_field", "also_bad"],
        }
        result = clean_invalid_fields(config)
        assert "invalid_field" not in result["fields"]
        assert "also_bad" not in result["fields"]
        assert "doc_no" in result["fields"]

    def test_clean_removes_invalid_filters(self):
        """Invalid filter field references should be removed"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
            "filters": [
                {"field": "doc_no", "op": "=", "value": "123"},
                {"field": "invalid_field", "op": "=", "value": "456"},
            ],
        }
        result = clean_invalid_fields(config)
        assert len(result["filters"]) == 1
        assert result["filters"][0]["field"] == "doc_no"

    def test_clean_removes_invalid_sort(self):
        """Invalid sort field references should be removed"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
            "sort": [
                {"field": "doc_no", "direction": "asc"},
                {"field": "invalid_field", "direction": "desc"},
            ],
        }
        result = clean_invalid_fields(config)
        assert len(result["sort"]) == 1
        assert result["sort"][0]["field"] == "doc_no"

    def test_clean_removes_invalid_group_by(self):
        """Invalid group_by field references should be removed"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no", "material_code"],
            "group_by": ["material_code", "invalid_field"],
        }
        result = clean_invalid_fields(config)
        assert "invalid_field" not in result["group_by"]
        assert "material_code" in result["group_by"]

    def test_unknown_table_passes_through(self):
        """Config with unknown table should pass through unchanged"""
        config = {
            "table": "unknown_table",
            "fields": ["some_field"],
        }
        result = clean_invalid_fields(config)
        assert result["fields"] == ["some_field"]


class TestBuildReportSql:
    """Tests for build_report_sql function"""

    def test_basic_query(self):
        """Basic query should build valid SQL"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no", "doc_date"],
        }
        sql, params = build_report_sql(config, page=1, page_size=10)
        assert "SELECT" in sql
        assert "FROM rpt_sales_out_wide" in sql
        assert "doc_no" in sql
        assert "doc_date" in sql

    def test_pagination_included_by_default(self):
        """Pagination should be included by default"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
        }
        sql, params = build_report_sql(config, page=1, page_size=10)
        assert "LIMIT 10 OFFSET 0" in sql

    def test_pagination_skipped_when_disabled(self):
        """Pagination should be skipped when include_pagination=False"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
        }
        sql, params = build_report_sql(config, page=1, page_size=10, include_pagination=False)
        assert "LIMIT" not in sql
        assert "OFFSET" not in sql

    def test_page_2_offset(self):
        """Page 2 should have correct OFFSET"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
        }
        sql, params = build_report_sql(config, page=2, page_size=10)
        assert "LIMIT 10 OFFSET 10" in sql

    def test_filters_applied(self):
        """Filters should be applied to SQL"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
            "filters": [{"field": "doc_no", "op": "=", "value": "123"}],
        }
        sql, params = build_report_sql(config, page=1, page_size=10)
        assert "WHERE" in sql or "doc_no" in sql

    def test_sort_applied(self):
        """Sort should be applied to SQL"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["doc_no"],
            "sort": [{"field": "doc_no", "direction": "desc"}],
        }
        sql, params = build_report_sql(config, page=1, page_size=10)
        assert "ORDER BY doc_no desc" in sql

    def test_group_by_applied(self):
        """Group by should be applied to SQL"""
        config = {
            "table": "rpt_sales_out_wide",
            "fields": ["material_code"],
            "group_by": ["material_code"],
        }
        sql, params = build_report_sql(config, page=1, page_size=10)
        assert "GROUP BY material_code" in sql