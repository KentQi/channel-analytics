"""W6-3 单测 — DefaultDimSyncHooks。"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from channel_analytics.db.dim_sync import DefaultDimSyncHooks
from channel_analytics.db.engine import create_all
from channel_analytics.db.models.dim import DimProductAttr
from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.types import EtlContext


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    create_all(eng)
    yield eng
    eng.dispose()


def _ctx(stg=None, rpt=None) -> EtlContext:
    return EtlContext(
        stg=stg or {}, rpt=rpt or {},
        meta={
            "rules": BusinessRules.defaults(),
            "brand_provider": ExampleMinimalProvider(),
            "current_date": date(2026, 6, 10),
        },
    )


class TestDefaultDimSyncHooks:
    def test_as_dict_returns_two_hooks(self):
        eng = create_engine("sqlite:///:memory:")
        h = DefaultDimSyncHooks(eng)
        assert set(h.as_dict().keys()) == {"sync_product_dim", "update_lifecycle"}

    def test_sync_product_dim_inserts_new(self, engine):
        stg = {"stg_stock_in": pd.DataFrame({
            "material_code": ["M1", "M2", "M1"],  # M1 出现两次
            "material_name": ["Name1", "Name2", "Name1Final"],
        })}
        h = DefaultDimSyncHooks(engine)
        result = h.sync_product_dimension_from_stock_in(_ctx(stg=stg))
        assert result["inserted"] == 2
        assert result["updated"] == 0

        with Session(engine) as s:
            rows = s.execute(__import__("sqlalchemy").select(DimProductAttr)).scalars().all()
            mat_to_name = {r.material_code: r.material_name for r in rows}
            # M1 keep='last' → "Name1Final"
            assert mat_to_name["M1"] == "Name1Final"
            assert mat_to_name["M2"] == "Name2"

    def test_sync_product_dim_updates_existing(self, engine):
        # 先 seed 一条
        with Session(engine) as s:
            s.add(DimProductAttr(material_code="M1", material_name="OldName"))
            s.commit()
        stg = {"stg_stock_in": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["NewName"],
        })}
        h = DefaultDimSyncHooks(engine)
        result = h.sync_product_dimension_from_stock_in(_ctx(stg=stg))
        assert result["inserted"] == 0
        assert result["updated"] == 1

    def test_sync_handles_missing_stock_in(self, engine):
        h = DefaultDimSyncHooks(engine)
        result = h.sync_product_dimension_from_stock_in(_ctx(stg={}))
        assert result == {"inserted": 0, "updated": 0}

    def test_lifecycle_high_sales(self, engine):
        # seed M1
        with Session(engine) as s:
            s.add(DimProductAttr(material_code="M1", material_name="x"))
            s.commit()
        rpt = {"rpt_trend_warning": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["x"],
            "sales_90d": [3000],  # 30+/天 → 畅销
            "material_available_qty": [100],
        })}
        h = DefaultDimSyncHooks(engine)
        result = h.update_lifecycle_status(_ctx(rpt=rpt))
        assert result["updated"] == 1
        with Session(engine) as s:
            row = s.get(DimProductAttr, 1)
            assert row.lifecycle_status == "畅销"

    def test_lifecycle_no_sales_dormant(self, engine):
        with Session(engine) as s:
            s.add(DimProductAttr(material_code="M1", material_name="x"))
            s.commit()
        rpt = {"rpt_trend_warning": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["x"],
            "sales_90d": [0], "material_available_qty": [50],
        })}
        DefaultDimSyncHooks(engine).update_lifecycle_status(_ctx(rpt=rpt))
        with Session(engine) as s:
            row = s.get(DimProductAttr, 1)
            assert row.lifecycle_status == "休眠"

    def test_lifecycle_normal(self, engine):
        with Session(engine) as s:
            s.add(DimProductAttr(material_code="M1", material_name="x"))
            s.commit()
        rpt = {"rpt_trend_warning": pd.DataFrame({
            "material_code": ["M1"], "material_name": ["x"],
            "sales_90d": [500],  # 5.5/天 → 正常
            "material_available_qty": [100],
        })}
        DefaultDimSyncHooks(engine).update_lifecycle_status(_ctx(rpt=rpt))
        with Session(engine) as s:
            row = s.get(DimProductAttr, 1)
            assert row.lifecycle_status == "正常"