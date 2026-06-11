"""Pipeline 步骤 2 — 用 stock_in 的效期填补 current_stock 的空值。

对应原仓 etl_service.fill_stock_expiry_date (L396-407)。

行为差异(新仓改进):
  - 列名别名 batch_number / batch_no / batch 全部支持
  - **不 in-place 修改 ctx.stg['stg_stock_current']**,输出新 DataFrame 写回
  - ctx.stg / ctx.raw_data 缺表时安全跳过

逻辑(对齐原仓):
  1. df_stock_in → 按 (material_code, batch_no) groupby 取最新 expiry_date
  2. merge 到 df_stock_current
  3. 合并后的 expiry_date 写入 ctx.stg['stg_stock_current']
"""
from __future__ import annotations

from typing import ClassVar

import pandas as pd

from channel_analytics.etl.types import EtlContext, Transformer

_STOCK_IN = "stg_stock_in"
_STOCK_CURRENT = "stg_stock_current"

_BATCH_KEYS: tuple[str, ...] = ("batch_number", "batch_no", "batch")
_MATERIAL_KEYS: tuple[str, ...] = ("material_code", "material")


def _first_present(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


class FillStockExpiryStep(Transformer):
    """用 stock_in 反向填补 stock_current 的空 expiry_date。"""
    name: ClassVar[str] = "fill_stock_expiry_date"

    def run(self, ctx: EtlContext) -> EtlContext:
        stock_current = ctx.stg.get(_STOCK_CURRENT)
        if stock_current is None:
            return ctx
        stock_in = ctx.stg.get(_STOCK_IN)
        if stock_in is None:
            stock_in = ctx.raw_data.get(_STOCK_IN)
        if stock_in is None or stock_current.empty or stock_in.empty:
            return ctx

        if "expiry_date" not in stock_current.columns or "expiry_date" not in stock_in.columns:
            return ctx

        mat_col = _first_present(stock_in, _MATERIAL_KEYS) or _first_present(stock_current, _MATERIAL_KEYS)
        bat_col = _first_present(stock_in, _BATCH_KEYS) or _first_present(stock_current, _BATCH_KEYS)
        if mat_col is None or bat_col is None:
            return ctx

        # 1. 构造 mapping: (material_code, batch_no) → 最新 expiry_date
        mapping = stock_in[[mat_col, bat_col, "expiry_date"]].copy()
        mapping = mapping.dropna(subset=[bat_col, "expiry_date"])
        # parse 一次,按日期排序,取 last(最新)
        mapping["_dt"] = pd.to_datetime(mapping["expiry_date"], errors="coerce")
        mapping = (
            mapping.dropna(subset=["_dt"])
            .sort_values("_dt")
            .groupby([mat_col, bat_col], as_index=False)["expiry_date"].last()
        )

        # 2. merge → 已有 expiry_date 不变,空值用 mapping 补
        merged = stock_current.merge(
            mapping[[mat_col, bat_col, "expiry_date"]],
            on=[mat_col, bat_col],
            how="left",
            suffixes=("", "_from_in"),
        )
        # 如果带 _from_in 后缀,组合两者
        if "expiry_date_from_in" in merged.columns:
            merged["expiry_date"] = merged["expiry_date"].combine_first(merged["expiry_date_from_in"])
            merged = merged.drop(columns=["expiry_date_from_in"])

        # 3. 写回(用副本,不改 stock_current 引用)
        out = stock_current.copy()
        out["expiry_date"] = merged["expiry_date"].values
        ctx.stg[_STOCK_CURRENT] = out
        return ctx
