"""W5-3b 单测 — AnalyzeExpiryWarningStep。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.analyze_expiry_warning import AnalyzeExpiryWarningStep
from channel_analytics.etl.types import EtlContext


def _ctx(stg=None, raw=None, rules=None, provider=None, current_date=None) -> EtlContext:
    return EtlContext(
        stg=stg or {},
        raw_data=raw or {},
        meta={
            "rules": rules or BusinessRules.defaults(),
            "brand_provider": provider or ExampleMinimalProvider(),
            "current_date": current_date or date(2026, 6, 10),
        },
    )


def test_step_skips_when_stock_empty():
    stg = {
        "stg_stock_current": pd.DataFrame(columns=["material_code", "batch_no", "expiry_date", "available_qty"]),
        "stg_sales_out": pd.DataFrame({"material_code": ["M1"], "batch_no": ["B1"], "doc_date": ["2026-01-01"], "sales_out_qty": [10]}),
    }
    out = AnalyzeExpiryWarningStep().run(_ctx(stg=stg))
    assert "rpt_expiry_warning" not in out.rpt


def test_step_skips_when_sales_empty():
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "batch_no": ["B1"],
            "expiry_date": [date(2028, 1, 1)], "available_qty": [100],
        }),
    }
    out = AnalyzeExpiryWarningStep().run(_ctx(stg=stg))
    assert "rpt_expiry_warning" not in out.rpt


def test_step_produces_required_columns():
    """产出表 12 列对齐原仓 L510-512。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "material_name": ["name1", "name2"],
            "batch_no": ["B1", "B2"],
            "expiry_date": [date(2028, 1, 1), date(2026, 1, 1)],
            "available_qty": [100, 200],
            "brand": ["BrandA", "BrandB"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"],
            "batch_no": ["B1"],
            "doc_date": ["2026-01-01"],
            "sales_out_qty": [50],
        }),
    }
    out = AnalyzeExpiryWarningStep().run(_ctx(stg=stg))
    cols = list(out.rpt["rpt_expiry_warning"].columns)
    assert cols == [
        "material_code", "material_name", "brand", "brand_class",
        "batch_no", "expiry_date",
        "material_batch_available_qty", "sales_90d", "inventory_days",
        "remaining_expiry_months", "expiry_status", "expiry_warning",
    ]


def test_step_aggregates_by_material_batch():
    """同物料多批次应被聚类到不同行,available_qty 累加。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M1"],
            "material_name": ["name1", "name1"],
            "batch_no": ["B1", "B1"],
            "expiry_date": [date(2028, 1, 1), date(2028, 1, 1)],
            "available_qty": [50, 70],
            "brand": ["BrandA", "BrandA"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"], "batch_no": ["B1"],
            "doc_date": ["2026-01-01"], "sales_out_qty": [30],
        }),
    }
    out = AnalyzeExpiryWarningStep().run(_ctx(stg=stg))
    rpt = out.rpt["rpt_expiry_warning"]
    assert len(rpt) == 1
    assert rpt["material_batch_available_qty"].iloc[0] == 120


def test_step_uses_brand_provider_for_classification():
    """品牌分类走 provider,ExampleMinimal 返回空集 → 全部 "非自营"。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "batch_no": ["B1"], "expiry_date": [date(2028, 1, 1)],
            "available_qty": [100], "brand": ["AnyBrand"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"], "batch_no": ["B1"],
            "doc_date": ["2026-01-01"], "sales_out_qty": [10],
        }),
    }
    out = AnalyzeExpiryWarningStep().run(_ctx(stg=stg, provider=ExampleMinimalProvider()))
    assert out.rpt["rpt_expiry_warning"]["brand_class"].iloc[0] == "非自营"


def test_step_marks_expiry_warning_below_24_months():
    """remaining_expiry_months < 24 → 预警。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "batch_no": ["B1"], "expiry_date": [date(2027, 6, 1)],  # 12 月后
            "available_qty": [100], "brand": ["X"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"], "batch_no": ["B1"],
            "doc_date": ["2026-01-01"], "sales_out_qty": [10],
        }),
    }
    out = AnalyzeExpiryWarningStep().run(
        _ctx(stg=stg, current_date=date(2026, 6, 10))
    )
    rpt = out.rpt["rpt_expiry_warning"]
    assert rpt["expiry_warning"].iloc[0] == "预警"


def test_step_does_not_mutate_input():
    """不应 in-place 修改入参 DataFrame。"""
    stock = pd.DataFrame({
        "material_code": ["M1"], "material_name": ["n1"],
        "batch_no": ["B1"], "expiry_date": [date(2028, 1, 1)],
        "available_qty": [100], "brand": ["X"],
    })
    sales = pd.DataFrame({
        "material_code": ["M1"], "batch_no": ["B1"],
        "doc_date": ["2026-01-01"], "sales_out_qty": [10],
    })
    stg = {"stg_stock_current": stock, "stg_sales_out": sales}
    AnalyzeExpiryWarningStep().run(_ctx(stg=stg))
    # 入参不应多出列
    assert "expiry_warning" not in stock.columns
    assert "sales_90d" not in stock.columns


def test_step_sales_90d_window_uses_rules_cycle_days():
    """cycle_days=30 时,60 天前的销售不应被纳入。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "batch_no": ["B1"], "expiry_date": [date(2028, 1, 1)],
            "available_qty": [100], "brand": ["X"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1", "M1"],
            "batch_no": ["B1", "B1"],
            "doc_date": [date(2026, 1, 1), date(2026, 6, 1)],  # 1月窗口外;6/1 窗口内
            "sales_out_qty": [999, 30],
        }),
    }
    rules = BusinessRules.from_dict({"turnover_cycle_days": 30})
    out = AnalyzeExpiryWarningStep().run(
        _ctx(stg=stg, rules=rules, current_date=date(2026, 6, 10))
    )
    # 只有 30 进入 sales_90d
    assert out.rpt["rpt_expiry_warning"]["sales_90d"].iloc[0] == 30
