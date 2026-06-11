"""W5-1c 单测 — FillStockExpiryStep。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.steps.fill_stock_expiry import FillStockExpiryStep
from channel_analytics.etl.types import EtlContext


def _ctx(stg=None, raw=None) -> EtlContext:
    return EtlContext(stg=stg or {}, raw_data=raw or {})


def test_step_skips_when_no_stock_in():
    """stg_stock_in 缺失时安全跳过(不炸)。"""
    stg = {"stg_stock_current": pd.DataFrame({
        "material_code": ["M1"],
        "batch_no": ["B1"],
        "expiry_date": [None],
    })}
    out = FillStockExpiryStep().run(_ctx(stg=stg))
    assert out.stg["stg_stock_current"]["expiry_date"].isna().iloc[0]


def test_step_skips_when_no_stock_current():
    """stg_stock_current 缺失时安全跳过。"""
    stg = {"stg_stock_in": pd.DataFrame({
        "material_code": ["M1"],
        "batch_no": ["B1"],
        "expiry_date": [date(2027, 1, 1)],
    })}
    out = FillStockExpiryStep().run(_ctx(stg=stg))
    # 写回不应发生
    assert "stg_stock_current" not in out.stg


def test_step_fills_existing_rows():
    """当前 stock 已有 expiry → 不应被覆盖(取已有优先)。"""
    stg = {
        "stg_stock_in": pd.DataFrame({
            "material_code": ["M1", "M1"],
            "batch_no": ["B1", "B1"],
            "expiry_date": [date(2025, 1, 1), date(2027, 1, 1)],
        }),
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"],
            "batch_no": ["B1"],
            "expiry_date": [date(2026, 6, 1)],  # 已有值
        }),
    }
    out = FillStockExpiryStep().run(_ctx(stg=stg))
    assert out.stg["stg_stock_current"]["expiry_date"].iloc[0] == pd.Timestamp(date(2026, 6, 1)).date() \
        or out.stg["stg_stock_current"]["expiry_date"].iloc[0] == date(2026, 6, 1)


def test_step_fills_missing_with_latest_from_stock_in():
    """当前 stock.expiry_date 为空 → 用 stock_in 最新日期填补。"""
    stg = {
        "stg_stock_in": pd.DataFrame({
            "material_code": ["M1", "M1", "M2"],
            "batch_no": ["B1", "B1", "B2"],
            "expiry_date": [date(2025, 1, 1), date(2027, 6, 1), date(2026, 3, 1)],
        }),
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1", "M2", "M3"],
            "batch_no": ["B1", "B2", "B3"],
            "expiry_date": [None, None, None],
        }),
    }
    out = FillStockExpiryStep().run(_ctx(stg=stg))
    result = out.stg["stg_stock_current"]["expiry_date"]
    # M1+B1 取最新 2027-06-01
    assert result.iloc[0] == date(2027, 6, 1) or result.iloc[0] == pd.Timestamp(date(2027, 6, 1)).date()
    # M2+B2 → 2026-03-01
    assert result.iloc[1] == date(2026, 3, 1) or result.iloc[1] == pd.Timestamp(date(2026, 3, 1)).date()
    # M3+B3 在 stock_in 找不到 → 仍为空
    assert pd.isna(result.iloc[2])


def test_step_supports_batch_number_alias():
    """batch_number 是别名时也应能匹配(列名兼容)。"""
    stg = {
        "stg_stock_in": pd.DataFrame({
            "material_code": ["M1"],
            "batch_number": ["B1"],
            "expiry_date": [date(2027, 6, 1)],
        }),
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"],
            "batch_number": ["B1"],
            "expiry_date": [None],
        }),
    }
    out = FillStockExpiryStep().run(_ctx(stg=stg))
    assert out.stg["stg_stock_current"]["expiry_date"].iloc[0] == date(2027, 6, 1) \
        or out.stg["stg_stock_current"]["expiry_date"].iloc[0] == pd.Timestamp(date(2027, 6, 1)).date()


def test_step_does_not_mutate_input_dataframe():
    """不应 in-place 修改入参 DataFrame。"""
    original = pd.DataFrame({
        "material_code": ["M1"],
        "batch_no": ["B1"],
        "expiry_date": [None],
    })
    stg = {
        "stg_stock_in": pd.DataFrame({
            "material_code": ["M1"],
            "batch_no": ["B1"],
            "expiry_date": [date(2027, 6, 1)],
        }),
        "stg_stock_current": original,
    }
    FillStockExpiryStep().run(_ctx(stg=stg))
    # 原始 DataFrame 引用应保持空值
    assert original["expiry_date"].isna().iloc[0]


def test_step_handles_empty_stock_in():
    """stg_stock_in 是空 DataFrame 时安全跳过。"""
    stg = {
        "stg_stock_in": pd.DataFrame(columns=["material_code", "batch_no", "expiry_date"]),
        "stg_stock_current": pd.DataFrame({
            "material_code": ["M1"],
            "batch_no": ["B1"],
            "expiry_date": [None],
        }),
    }
    out = FillStockExpiryStep().run(_ctx(stg=stg))
    assert out.stg["stg_stock_current"]["expiry_date"].isna().iloc[0]
