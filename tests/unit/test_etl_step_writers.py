"""W5-7 单测 — Writer 步骤(sqlite 内存验证)。"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect

from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.auto_update_dim import AutoUpdateDimStep
from channel_analytics.etl.steps.write_rpt_tables import RPT_TABLES, WriteRptTablesStep
from channel_analytics.etl.types import EtlContext


@pytest.fixture
def sqlite_engine():
    """内存 SQLite engine,所有测试隔离。"""
    return create_engine("sqlite:///:memory:")


def _ctx(rpt=None, engine=None, hooks=None) -> EtlContext:
    meta = {
        "rules": BusinessRules.defaults(),
        "brand_provider": ExampleMinimalProvider(),
        "current_date": date(2026, 6, 10),
    }
    if engine is not None:
        meta["engine"] = engine
    if hooks is not None:
        meta["dim_sync_hooks"] = hooks
    return EtlContext(rpt=rpt or {}, meta=meta)


# ---------------------------------------------------------------------------
# WriteRptTablesStep
# ---------------------------------------------------------------------------

class TestWriteRptTablesStep:
    def test_noop_when_no_engine(self):
        """ctx.meta 无 engine → 静默 no-op。"""
        rpt = {"rpt_expiry_warning": pd.DataFrame({"material_code": ["M1"], "expiry_warning": ["正常"]})}
        out = WriteRptTablesStep().run(_ctx(rpt=rpt))
        assert out.rpt == rpt  # 不修改

    def test_writes_table_to_sqlite(self, sqlite_engine):
        """7 张 RPT 表都应被写入。"""
        for table in RPT_TABLES:
            _ctx(rpt={table: pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})}, engine=sqlite_engine)
        # 一次跑完所有 7 张
        rpt = {t: pd.DataFrame({"a": [1], "b": ["x"]}) for t in RPT_TABLES}
        WriteRptTablesStep().run(_ctx(rpt=rpt, engine=sqlite_engine))
        insp = inspect(sqlite_engine)
        for table in RPT_TABLES:
            assert insp.has_table(table), f"{table} 未创建"

    def test_skips_empty_dataframe(self, sqlite_engine):
        """空 DataFrame 应被跳过,不应建表。"""
        rpt = {"rpt_expiry_warning": pd.DataFrame(columns=["a", "b"])}
        WriteRptTablesStep().run(_ctx(rpt=rpt, engine=sqlite_engine))
        insp = inspect(sqlite_engine)
        assert not insp.has_table("rpt_expiry_warning")

    def test_column_clipping_against_existing_table(self, sqlite_engine):
        """df 中多余列不应写入(对齐原仓 L207 列裁剪)。"""
        # 1. 写入 1 列的表
        df1 = pd.DataFrame({"a": [1, 2]})
        rpt1 = {"rpt_expiry_warning": df1}
        WriteRptTablesStep().run(_ctx(rpt=rpt1, engine=sqlite_engine))
        # 2. 再写入有 a/b/c 的表,只应保留 a
        df2 = pd.DataFrame({"a": [3], "b": ["x"], "c": [True]})
        rpt2 = {"rpt_expiry_warning": df2}
        WriteRptTablesStep().run(_ctx(rpt=rpt2, engine=sqlite_engine))
        # 验证列只有 a
        insp = inspect(sqlite_engine)
        cols = {c["name"] for c in insp.get_columns("rpt_expiry_warning")}
        assert cols == {"a"}

    def test_writes_preserves_data(self, sqlite_engine):
        """写入数据可被 SQLAlchemy 读回。"""
        df = pd.DataFrame({
            "material_code": ["M1", "M2"],
            "expiry_status": ["效期极佳(32+)", "效期临期(0-6)"],
            "expiry_warning": ["正常", "预警"],
        })
        rpt = {"rpt_expiry_warning": df}
        WriteRptTablesStep().run(_ctx(rpt=rpt, engine=sqlite_engine))
        result = pd.read_sql("SELECT * FROM rpt_expiry_warning", sqlite_engine)
        assert len(result) == 2
        assert "M1" in result["material_code"].tolist()


# ---------------------------------------------------------------------------
# AutoUpdateDimStep
# ---------------------------------------------------------------------------

class TestAutoUpdateDimStep:
    def test_noop_when_no_hooks(self):
        out = AutoUpdateDimStep().run(_ctx())
        assert isinstance(out, EtlContext)

    def test_invokes_hooks(self):
        """ctx.meta['dim_sync_hooks'] 中的每个 hook 都被调用一次。"""
        called = []

        def hook_a(ctx):
            called.append("a")
            return {"inserted": 5}

        def hook_b(ctx):
            called.append("b")
            return {"updated": 3}

        hooks = {"sync_product_dim": hook_a, "update_lifecycle": hook_b}
        AutoUpdateDimStep().run(_ctx(hooks=hooks))
        assert called == ["a", "b"]

    def test_hook_failure_does_not_crash(self):
        """单个 hook 抛异常不影响其他 hook,ETL 继续。"""
        called = []

        def hook_ok(ctx):
            called.append("ok")
            return {}

        def hook_fail(ctx):
            raise RuntimeError("simulated DB error")

        hooks = {"ok": hook_ok, "fail": hook_fail}
        AutoUpdateDimStep().run(_ctx(hooks=hooks))
        # ok 仍被调用,fail 被吞掉
        assert called == ["ok"]

    def test_hook_receives_etl_context(self):
        """hook 应能访问 ctx(rpt / stg / meta 全部可见)。"""
        captured = {}

        def inspect_hook(ctx):
            captured["has_rpt"] = bool(ctx.rpt)
            captured["has_meta"] = bool(ctx.meta)
            return {}

        hooks = {"inspect": inspect_hook}
        AutoUpdateDimStep().run(_ctx(rpt={"rpt_x": pd.DataFrame()}, hooks=hooks))
        assert captured == {"has_rpt": True, "has_meta": True}