"""W5-4a 单测 — RPT 3 自营集中度。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.analyze_self_operated_concentration import (
    AnalyzeSelfOperatedConcentrationStep,
)
from channel_analytics.etl.types import EtlContext


def _ctx(rpt=None) -> EtlContext:
    return EtlContext(
        rpt=rpt or {},
        meta={
            "rules": BusinessRules.defaults(),
            "brand_provider": ExampleMinimalProvider(),
            "current_date": date(2026, 6, 10),
        },
    )


def _base_rpt() -> dict:
    return {
        "rpt_expiry_warning": pd.DataFrame({
            "material_code": ["M1", "M2", "M3"],
            "material_name": ["n1", "n2", "n3"],
            "brand": ["A", "B", "C"],
            "brand_class": ["自营", "非自营", "自营"],  # M2 是非自营,应被排除
            "batch_no": ["B1", "B2", "B3"],
            "expiry_date": [date(2028, 1, 1)] * 3,
            "material_batch_available_qty": [50, 200, 50],
            "sales_90d": [10, 100, 10],
            "inventory_days": [10, 10, 10],
            "remaining_expiry_months": [18, 18, 18],
            "expiry_status": ["效期一般(18-24)"] * 3,
            "expiry_warning": ["预警"] * 3,
        })
    }


def test_step_skips_when_input_empty():
    out = AnalyzeSelfOperatedConcentrationStep().run(_ctx())
    assert out.rpt["rpt_self_operated_concentration"].empty
    assert list(out.rpt["rpt_self_operated_concentration"].columns) == [
        "material_code", "material_name", "brand", "expiry_status",
        "material_batch_available_qty", "stock_ratio", "cumulative_stock_ratio", "sales_90d",
    ]


def test_step_filters_non_self_operated():
    """非自营物料不进入 RPT 3。"""
    out = AnalyzeSelfOperatedConcentrationStep().run(_ctx(rpt=_base_rpt()))
    r = out.rpt["rpt_self_operated_concentration"]
    assert len(r) == 2  # M1 + M3,M2 被排除
    assert "M2" not in r["material_code"].tolist()


def test_step_aggregates_by_material_status():
    """同物料不同 expiry_status 仍出 2 行(原仓 L531 groupby 包含 expiry_status)。"""
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "material_code": ["M1", "M1"],
            "material_name": ["n1", "n1"],
            "brand": ["A", "A"],
            "brand_class": ["自营", "自营"],
            "batch_no": ["B1", "B1"],
            "expiry_date": [date(2028, 1, 1)] * 2,
            "material_batch_available_qty": [50, 70],
            "sales_90d": [10, 20],
            "expiry_status": ["效期极佳(32+)", "效期一般(18-24)"],
        })
    }
    out = AnalyzeSelfOperatedConcentrationStep().run(_ctx(rpt=rpt))
    r = out.rpt["rpt_self_operated_concentration"]
    assert len(r) == 2  # 不同 expiry_status 出 2 行
    # M1 两条记录,各档位 quantity 保留原值(不跨档位累加)
    assert sorted(r["material_batch_available_qty"].tolist()) == [50, 70]


def test_step_stock_ratio_cumulative():
    """stock_ratio + cumulative_stock_ratio 字符串带 %。"""
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "material_code": ["M1", "M2", "M3"],
            "material_name": ["n1", "n2", "n3"],
            "brand": ["A", "A", "A"],
            "brand_class": ["自营"] * 3,
            "batch_no": ["B1", "B2", "B3"],
            "expiry_date": [date(2028, 1, 1)] * 3,
            "material_batch_available_qty": [50, 30, 20],  # 总 100
            "sales_90d": [10, 5, 2],
            "expiry_status": ["效期一般(18-24)"] * 3,
        })
    }
    out = AnalyzeSelfOperatedConcentrationStep().run(_ctx(rpt=rpt))
    r = out.rpt["rpt_self_operated_concentration"]
    # 按库存降序
    rows = r.set_index("material_code")
    assert rows.loc["M1", "stock_ratio"] == "50.0%"
    assert rows.loc["M2", "stock_ratio"] == "30.0%"
    assert rows.loc["M3", "stock_ratio"] == "20.0%"
    # 累计
    assert rows.loc["M1", "cumulative_stock_ratio"] == "50.0%"
    assert rows.loc["M2", "cumulative_stock_ratio"] == "80.0%"
    assert rows.loc["M3", "cumulative_stock_ratio"] == "100.0%"


def test_step_handles_empty_self_operated():
    """全部物料都是非自营时,返回空 DataFrame(列结构保留)。"""
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "material_code": ["M1"],
            "material_name": ["n1"],
            "brand": ["X"],
            "brand_class": ["非自营"],
            "batch_no": ["B1"],
            "expiry_date": [date(2028, 1, 1)],
            "material_batch_available_qty": [100],
            "sales_90d": [10],
            "expiry_status": ["效期一般(18-24)"],
        })
    }
    out = AnalyzeSelfOperatedConcentrationStep().run(_ctx(rpt=rpt))
    r = out.rpt["rpt_self_operated_concentration"]
    assert r.empty
    assert "material_code" in r.columns
