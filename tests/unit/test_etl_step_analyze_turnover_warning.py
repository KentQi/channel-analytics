"""W5-4b 单测 — RPT 4 物料维度周转告警。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.analyze_turnover_warning import AnalyzeTurnoverWarningStep
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


def _base_stg() -> dict:
    return {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "material_name": ["n1", "n2"],
            "available_qty": [100, 200],
            "brand": ["A", "B"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "doc_date": [date(2026, 4, 1), date(2026, 4, 1)],  # 90 天窗口内
            "sales_out_qty": [50, 100],
        }),
    }


def test_step_skips_when_stock_empty():
    stg = {"stg_stock_current": pd.DataFrame(columns=["material_code", "material_name", "available_qty"])}
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=stg))
    assert "rpt_turnover_warning" not in out.rpt


def test_step_skips_when_sales_empty():
    stg = {"stg_stock_current": pd.DataFrame({
        "material_code": ["M1"], "material_name": ["n1"], "available_qty": [100],
    })}
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=stg))
    assert "rpt_turnover_warning" not in out.rpt


def test_step_output_columns():
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=_base_stg()))
    cols = list(out.rpt["rpt_turnover_warning"].columns)
    assert cols == [
        "material_code", "material_name", "brand", "brand_class",
        "material_available_qty", "sales_90d", "inventory_days",
        "turnover_status", "turnover_warning",
    ]


def test_step_normal_turnover_is_normal():
    """库存 100,90 天销 50 → 180 天,>60 告警 / 库存 20,销 100 → 18 天,健康。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "material_name": ["n1", "n2"],
            "available_qty": [100, 20],
            "brand": ["A", "B"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1", "M2"],
            "doc_date": [date(2026, 4, 1), date(2026, 4, 1)],  # 在 90 天窗口内(6/10 - 70 天)
            "sales_out_qty": [50, 100],
        }),
    }
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=stg))
    r = out.rpt["rpt_turnover_warning"]
    m1 = r[r["material_code"] == "M1"].iloc[0]
    m2 = r[r["material_code"] == "M2"].iloc[0]
    # 100/50*90 = 180,>60 → 预警
    assert m1["inventory_days"] == 180
    assert m1["turnover_warning"] == "预警"
    # 20/100*90 = 18,>=15 且 <=60 → 正常
    assert m2["inventory_days"] == 18
    assert m2["turnover_warning"] == "正常"


def test_step_low_inventory_below_low_threshold_warns():
    """< 15 天 → 预警(快销/库存不足)。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [10], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1"], "doc_date": [date(2026, 4, 1)], "sales_out_qty": [100],
        }),
    }
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=stg))
    r = out.rpt["rpt_turnover_warning"].iloc[0]
    # 10/100*90 = 9,<15 → 预警
    assert r["inventory_days"] == 9
    assert r["turnover_warning"] == "预警"


def test_step_custom_warning_thresholds():
    """YAML 改 turnover_warning_{low,high} 后,新阈值生效。"""
    stg = _base_stg()
    rules = BusinessRules.from_dict({
        "turnover_warning_low": 30,
        "turnover_warning_high": 100,
    })
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=stg, rules=rules))
    r = out.rpt["rpt_turnover_warning"]
    m1 = r[r["material_code"] == "M1"].iloc[0]
    # 100/50*90=180,>100 仍预警
    assert m1["turnover_warning"] == "预警"
    m2 = r[r["material_code"] == "M2"].iloc[0]
    # 20/100*90=18,<30 仍预警
    assert m2["turnover_warning"] == "预警"


def test_step_brand_classification_uses_provider():
    """ExampleMinimal → 全部非自营。"""
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=_base_stg()))
    r = out.rpt["rpt_turnover_warning"]
    assert (r["brand_class"] == "非自营").all()


def test_step_uses_custom_cycle_days_for_sales_window():
    """cycle_days=30 时,60 天前销售不进 sales_90d。"""
    stg = {
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["n1"],
            "available_qty": [100], "brand": ["A"],
        }),
        "stg_sales_out": pd.DataFrame({
            "material_code": ["M1", "M1"],
            "doc_date": [date(2026, 1, 1), date(2026, 6, 1)],
            "sales_out_qty": [999, 50],
        }),
    }
    rules = BusinessRules.from_dict({"turnover_cycle_days": 30})
    out = AnalyzeTurnoverWarningStep().run(_ctx(stg=stg, rules=rules))
    r = out.rpt["rpt_turnover_warning"].iloc[0]
    assert r["sales_90d"] == 50  # 999 被 30 天窗口排除
