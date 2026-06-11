"""W4-4 测试 — CleanStgFieldsStep 接入 pipeline。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.pipeline import EtlContext, run_default_etl
from channel_analytics.etl.steps.clean_stg_fields import (
    STG_TABLES,
    CleanStgFieldsStep,
)


def _ctx(raw: dict[str, pd.DataFrame]) -> EtlContext:
    return EtlContext(raw_data=raw, meta={"rules": None})


def test_step_runs_with_empty_raw_data():
    """空 raw_data 必须跑通(无任何 STG 表 → ctx.stg 为空)。"""
    step = CleanStgFieldsStep()
    ctx = step.run(_ctx({}))
    assert ctx.stg == {}


def test_step_cleans_stg_purchase_req():
    """stg_purchase_req 中的 batch_number / material_code 走清洗。"""
    raw = {
        "stg_purchase_req": pd.DataFrame({
            "batch_number": ["B001", "无效", "  B003  ", None],
            "material_code": ["MAT-1", "MAT'2", "MAT003（仓）", None],
        })
    }
    ctx = CleanStgFieldsStep().run(_ctx(raw))
    out = ctx.stg["stg_purchase_req"]
    # batch_number 清洗:None / 无效 → NaN
    assert out["batch_number"].dropna().tolist() == ["B001", "B003"]
    assert out["batch_number"].isna().sum() == 2
    # material_code 清洗:None → "" (空串合法)
    assert out["material_code"].tolist() == ["MAT-1", "MAT2", "MAT003", ""]


def test_step_cleans_expiry_column_aliases():
    """expiry_date / expiry / 效期 三种列名都应被清洗。"""
    raw = {
        "stg_stock_in": pd.DataFrame({
            "expiry_date": ["2025-12-31", "n/a", "2026/06/30"],
        }),
        "stg_sales_out": pd.DataFrame({
            "expiry": ["2025-01-01", "", "bad-date"],
        }),
    }
    ctx = CleanStgFieldsStep().run(_ctx(raw))
    # DataFrame 列里 None 表现成 NaN,用 isna() 判断
    in_dates = ctx.stg["stg_stock_in"]["expiry_date"]
    assert in_dates.iloc[0] == pd.Timestamp(date(2025, 12, 31)).date() or in_dates.iloc[0] == date(2025, 12, 31)
    assert in_dates.isna().tolist() == [False, True, False]

    out_dates = ctx.stg["stg_sales_out"]["expiry"]
    assert out_dates.iloc[0] == date(2025, 1, 1)
    assert out_dates.isna().tolist() == [False, True, True]


def test_step_skips_missing_columns():
    """不存在 batch_number 列时,不能炸(防御列名差异)。"""
    raw = {
        "stg_stock_current": pd.DataFrame({"unrelated": [1, 2, 3]}),
    }
    ctx = CleanStgFieldsStep().run(_ctx(raw))
    assert ctx.stg["stg_stock_current"]["unrelated"].tolist() == [1, 2, 3]


def test_step_does_not_mutate_raw_data():
    """清洗后 raw_data 应保持原样(防御性 in-place bug)。"""
    raw = {"stg_purchase_req": pd.DataFrame({"batch_number": ["B001", "无效"]})}
    original_batch = raw["stg_purchase_req"]["batch_number"].tolist()
    CleanStgFieldsStep().run(_ctx(raw))
    assert raw["stg_purchase_req"]["batch_number"].tolist() == original_batch


def test_default_pipeline_runs_step1_with_all_5_tables():
    """run_default_etl 第 1 步跑完后,5 张 STG 表都应能在 ctx.stg 中。"""
    raw = {table: pd.DataFrame({"batch_number": ["B001"]}) for table in STG_TABLES}
    ctx = run_default_etl(
        raw_data=raw,
        brand_provider_dotted=(
            "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
        ),
    )
    for table in STG_TABLES:
        assert table in ctx.stg
        assert ctx.stg[table]["batch_number"].tolist() == ["B001"]


def test_default_pipeline_handles_partial_tables():
    """只传入 2 张表时,其他 3 张表 ctx.stg 中应不存在(不被错填)。"""
    raw = {
        "stg_purchase_req": pd.DataFrame({"batch_number": ["B001"]}),
        "stg_sales_out": pd.DataFrame({"batch_number": ["B002"]}),
    }
    ctx = run_default_etl(
        raw_data=raw,
        brand_provider_dotted=(
            "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
        ),
    )
    assert "stg_purchase_req" in ctx.stg
    assert "stg_sales_out" in ctx.stg
    assert "stg_purchase_order" not in ctx.stg
    assert "stg_stock_in" not in ctx.stg
    assert "stg_stock_current" not in ctx.stg
