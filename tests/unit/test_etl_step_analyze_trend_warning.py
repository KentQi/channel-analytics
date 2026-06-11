"""W5-5c 单测 — RPT 5 物料维度趋势告警。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.analyze_trend_warning import AnalyzeTrendWarningStep
from channel_analytics.etl.types import EtlContext


def _ctx(stg=None, raw=None, rules=None) -> EtlContext:
    return EtlContext(
        stg=stg or {},
        raw_data=raw or {},
        meta={
            "rules": rules or BusinessRules.defaults(),
            "brand_provider": ExampleMinimalProvider(),
            "current_date": date(2026, 6, 10),
        },
    )


def test_step_skips_when_stock_empty():
    out = AnalyzeTrendWarningStep().run(_ctx(stg={"stg_stock_current": pd.DataFrame()}))
    assert "rpt_trend_warning" not in out.rpt


def test_step_skips_when_sales_empty():
    out = AnalyzeTrendWarningStep().run(_ctx(stg={
        "stg_stock_current": pd.DataFrame({"material_code": ["M1"], "material_name": ["n1"], "available_qty": [10]}),
    }))
    assert "rpt_trend_warning" not in out.rpt


def test_step_produces_15_columns():
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [10], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"], "doc_date": [date(2026, 5, 20)], "sales_out_qty": [10],
        }),
    }
    out = AnalyzeTrendWarningStep().run(_ctx(stg=stg))
    cols = list(out.rpt["rpt_trend_warning"].columns)
    assert len(cols) == 15
    assert cols == [
        "material_code", "material_name", "brand", "brand_class",
        "material_available_qty",
        "cycle_4_sales", "cycle_3_sales", "cycle_2_sales", "cycle_1_sales",
        "total_dispatch_90d", "total_return_qty", "sales_90d",
        "return_ratio", "trend_status", "trend_warning",
    ]


def test_step_brand_classification():
    """ExampleMinimal → 全部 非自营。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "material_name": ["n1", "n2"],
            "available_qty": [10, 20],
            "brand": ["A", "B"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"],
            "doc_date": [date(2026, 5, 20)],
            "sales_out_qty": [10],
        }),
    }
    out = AnalyzeTrendWarningStep().run(_ctx(stg=stg))
    r = out.rpt["rpt_trend_warning"]
    assert (r["brand_class"] == "非自营").all()


def test_step_sustained_rise_marked_as_warning():
    # c3=1, c2=10, c1=50 → 持续上升 + 任一比率>=3 → 迉速攀升 → 正常(不在预警关键字)
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [100], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"] * 4,
            "doc_date": [
                date(2026, 2, 20),  # c4
                date(2026, 3, 20),  # c3
                date(2026, 4, 20),  # c2
                date(2026, 5, 20),  # c1
            ],
            "sales_out_qty": [0, 1, 10, 50],
        }),
    }
    out = AnalyzeTrendWarningStep().run(_ctx(stg=stg))
    r = out.rpt["rpt_trend_warning"].iloc[0]
    assert r["trend_status"] == "迉速攀升"
    assert r["trend_warning"] == "正常"


def test_step_sustained_decline_marked_as_warning():
    # c3=50, c2=10, c1=1 → 持续下降 + r23=0.2<=1/3 → 迉速下滑 → 预警
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [100], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"] * 4,
            "doc_date": [
                date(2026, 2, 20), date(2026, 3, 20), date(2026, 4, 20), date(2026, 5, 20),
            ],
            "sales_out_qty": [0, 50, 10, 1],
        }),
    }
    out = AnalyzeTrendWarningStep().run(_ctx(stg=stg))
    r = out.rpt["rpt_trend_warning"].iloc[0]
    assert r["trend_status"] == "迉速下滑"
    assert r["trend_warning"] == "预警"


def test_step_return_ratio_format():
    """return_ratio 字段为 'xx.x%' 字符串。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [100], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"],
            "doc_date": [date(2026, 5, 20)],
            "sales_out_qty": [10],
        }),
    }
    out = AnalyzeTrendWarningStep().run(_ctx(stg=stg))
    rr = out.rpt["rpt_trend_warning"]["return_ratio"].iloc[0]
    assert rr.endswith("%")
    assert isinstance(rr, str)


def test_step_uses_custom_trend_config():
    """YAML 改 TrendConfig 后生效。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [100], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"] * 4,
            "doc_date": [date(2026, 2, 20), date(2026, 3, 20), date(2026, 4, 20), date(2026, 5, 20)],
            "sales_out_qty": [0, 1, 10, 50],
        }),
    }
    rules = BusinessRules.from_dict({"trend": {"ratio_threshold": 10.0, "min_change": 1.0}})
    # r23 = 10/1 = 10, ratio=10 → r23 >= R → 迉速攀升
    out = AnalyzeTrendWarningStep().run(_ctx(stg=stg, rules=rules))
    r = out.rpt["rpt_trend_warning"].iloc[0]
    assert r["trend_status"] == "迉速攀升"


def test_step_does_not_mutate_input():
    """不应 in-place 修改入参 DataFrame。"""
    stock = pd.DataFrame({
        "material_code": ["M1"], "material_name": ["n1"],
        "available_qty": [10], "brand": ["A"],
    })
    sales = pd.DataFrame({
        "material_code": ["M1"], "doc_date": [date(2026, 5, 20)], "sales_out_qty": [10],
    })
    stg = {"stg_stock_current": stock, "stg_sales_out": sales}
    AnalyzeTrendWarningStep().run(_ctx(stg=stg))
    assert "trend_warning" not in stock.columns
    assert "trend_warning" not in sales.columns