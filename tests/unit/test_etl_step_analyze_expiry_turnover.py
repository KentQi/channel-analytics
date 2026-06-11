"""W5-3c 单测 — AnalyzeExpiryTurnoverStep。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.analyze_expiry_turnover import AnalyzeExpiryTurnoverStep
from channel_analytics.etl.types import EtlContext


def _ctx(rpt=None, rules=None) -> EtlContext:
    return EtlContext(
        rpt=rpt or {},
        meta={
            "rules": rules or BusinessRules.defaults(),
            "brand_provider": ExampleMinimalProvider(),
            "current_date": date(2026, 6, 10),
        },
    )


def test_step_skips_when_input_empty():
    out = AnalyzeExpiryTurnoverStep().run(_ctx())
    assert "rpt_expiry_turnover" not in out.rpt


def test_step_aggregates_by_brand_status():
    """brand_class × expiry_status 聚合,available_qty / sales_90d 累加。"""
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "material_code": ["M1", "M1", "M2"],
            "material_name": ["n1", "n1", "n2"],
            "brand": ["A", "A", "B"],
            "brand_class": ["自营", "自营", "非自营"],
            "batch_no": ["B1", "B1", "B2"],
            "expiry_date": [date(2028, 1, 1)] * 3,
            "material_batch_available_qty": [50, 70, 200],
            "sales_90d": [10, 20, 100],
            "inventory_days": [10, 10, 10],
            "remaining_expiry_months": [18, 18, 18],
            "expiry_status": ["效期一般(18-24)", "效期一般(18-24)", "效期一般(18-24)"],
            "expiry_warning": ["预警", "预警", "预警"],
        })
    }
    out = AnalyzeExpiryTurnoverStep().run(_ctx(rpt=rpt))
    r = out.rpt["rpt_expiry_turnover"]
    # 自营 + 效期一般 聚合: 120 库存, 90 天销 30
    # 原仓: safe_divide(available_qty, sales_90d) * 90 = 120/30 * 90 = 360
    self_row = r[r["brand_class"] == "自营"].iloc[0]
    assert self_row["available_qty"] == 120
    assert self_row["sales_90d"] == 30
    assert self_row["turnover_days"] == 360.0


def test_step_uses_custom_cycle_days():
    """cycle_days=30 时,turnover_days = safe_div / * 30。"""
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "brand_class": ["自营"],
            "expiry_status": ["效期一般(18-24)"],
            "material_batch_available_qty": [60],
            "sales_90d": [30],
        })
    }
    rules = BusinessRules.from_dict({"turnover_cycle_days": 30})
    out = AnalyzeExpiryTurnoverStep().run(_ctx(rpt=rpt, rules=rules))
    assert out.rpt["rpt_expiry_turnover"]["turnover_days"].iloc[0] == 60.0  # 60/30 * 30


def test_step_handles_zero_sales_safely():
    """sales_90d=0 时,turnover_days 应走 safe_divide → 0(不抛异常)。"""
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "brand_class": ["非自营"],
            "expiry_status": ["效期临期(0-6)"],
            "material_batch_available_qty": [100],
            "sales_90d": [0],
        })
    }
    out = AnalyzeExpiryTurnoverStep().run(_ctx(rpt=rpt))
    assert out.rpt["rpt_expiry_turnover"]["turnover_days"].iloc[0] == 0


def test_step_output_columns():
    rpt = {
        "rpt_expiry_warning": pd.DataFrame({
            "brand_class": ["自营"],
            "expiry_status": ["效期极佳(32+)"],
            "material_batch_available_qty": [10],
            "sales_90d": [5],
        })
    }
    out = AnalyzeExpiryTurnoverStep().run(_ctx(rpt=rpt))
    cols = list(out.rpt["rpt_expiry_turnover"].columns)
    assert cols == ["brand_class", "expiry_status", "available_qty", "sales_90d", "turnover_days"]


def test_step_pipeline_chain():
    """完整链:stock + sales → step 3 (RPT 1) → step 4 (RPT 2) 跑通。"""
    from channel_analytics.etl.steps.analyze_expiry_warning import AnalyzeExpiryWarningStep

    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "material_name": ["n1", "n2"],
            "batch_no": ["B1", "B2"],
            "expiry_date": [date(2028, 1, 1), date(2028, 1, 1)],
            "available_qty": [100, 200],
            "brand": ["A", "B"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "batch_no": ["B1", "B2"],
            "doc_date": [date(2026, 1, 1), date(2026, 1, 1)],
            "sales_out_qty": [50, 100],
        }),
    }
    ctx = EtlContext(stg=stg, meta={
        "rules": BusinessRules.defaults(),
        "brand_provider": ExampleMinimalProvider(),
        "current_date": date(2026, 6, 10),
    })
    ctx = AnalyzeExpiryWarningStep().run(ctx)
    ctx = AnalyzeExpiryTurnoverStep().run(ctx)
    assert "rpt_expiry_warning" in ctx.rpt
    assert "rpt_expiry_turnover" in ctx.rpt
    assert len(ctx.rpt["rpt_expiry_turnover"]) >= 1
