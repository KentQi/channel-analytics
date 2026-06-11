"""W2补 field_mapping 单测。"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from channel_analytics.etl.field_mapping import (
    build_reverse_map,
    load_mapping,
    rename_columns,
    rename_for_display,
    suggest_mapping_from_columns,
)


class TestBuildReverseMap:
    def test_basic(self):
        fwd = {"物料编码": "material_code", "物料名称": "material_name"}
        rev = build_reverse_map(fwd)
        assert rev == {"material_code": "物料编码", "material_name": "物料名称"}

    def test_collision_later_wins(self):
        fwd = {"A": "x", "B": "x"}
        rev = build_reverse_map(fwd)
        # 后者覆盖前者
        assert rev == {"x": "B"}

    def test_empty(self):
        assert build_reverse_map({}) == {}


class TestLoadMapping:
    def test_from_dict(self):
        m = load_mapping({"k1": "v1", "k2": "v2"})
        assert m == {"k1": "v1", "k2": "v2"}

    def test_from_json_file(self, tmp_path):
        path = tmp_path / "mapping.json"
        path.write_text(json.dumps({"中文列": "english_col"}, ensure_ascii=False), encoding="utf-8")
        m = load_mapping(path)
        assert m["中文列"] == "english_col"

    def test_from_nonexistent_file_returns_empty(self, tmp_path):
        m = load_mapping(tmp_path / "ghost.json")
        assert m == {}


class TestRenameColumns:
    def test_only_mapped_columns_renamed(self):
        df = pd.DataFrame({
            "物料编码": ["A1", "A2"],
            "其他列": [1, 2],
        })
        mapping = {"物料编码": "material_code"}
        result = rename_columns(df, mapping)
        # 中文列被改名,未在 mapping 中的列保留
        assert "material_code" in result.columns
        assert result["material_code"].tolist() == ["A1", "A2"]
        assert "其他列" in result.columns

    def test_no_mapping_no_change(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = rename_columns(df, {})
        assert result.columns.tolist() == ["a"]


class TestRenameForDisplay:
    def test_reverse_renames_english_to_chinese(self):
        df = pd.DataFrame({
            "material_code": ["A1", "A2"],
            "qty": [10, 20],
        })
        mapping = {"物料编码": "material_code"}
        result = rename_for_display(df, mapping)
        assert "物料编码" in result.columns
        assert result["物料编码"].tolist() == ["A1", "A2"]


class TestSuggestMapping:
    def test_english_columns_lowercased(self):
        result = suggest_mapping_from_columns(["brand_name", "sales_qty_90d"])
        assert result["brand_name"] == "brand_name"
        assert result["sales_qty_90d"] == "sales_qty_90d"

    def test_chinese_columns_kept_as_is(self):
        result = suggest_mapping_from_columns(["物料编码", "数量"])
        assert result["物料编码"] == "物料编码"

    def test_empty_skipped(self):
        result = suggest_mapping_from_columns(["", "  ", "valid"])
        assert "" not in result
        assert "  " not in result
        assert "valid" in result