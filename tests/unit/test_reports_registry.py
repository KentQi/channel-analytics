"""W2补 reports 框架单测。"""
from __future__ import annotations

import pandas as pd

from channel_analytics.reports import BaseReport, ReportMeta, ReportRegistry, registry


class TestRegistry:
    def test_default_reports_registered(self):
        """7 张默认 RPT 都被注册。"""
        names = registry.list_names()
        for n in (
            "rpt_expiry_warning", "rpt_expiry_turnover",
            "rpt_self_operated_concentration", "rpt_turnover_warning",
            "rpt_trend_warning", "rpt_warehouse_risk",
            "rpt_procurement_linked",
        ):
            assert n in names

    def test_get_registered_report(self):
        cls = registry.get("rpt_expiry_warning")
        assert cls.meta.name == "rpt_expiry_warning"

    def test_get_unknown_raises(self):
        with __import__("pytest").raises(KeyError):
            registry.get("rpt_ghost")

    def test_custom_report_register(self):
        reg = ReportRegistry()

        @reg.register()
        class CustomReport(BaseReport):
            meta = ReportMeta(name="custom_rpt", description="test", columns=["a", "b"])

            def generate(self, ctx):
                return pd.DataFrame({"a": [1], "b": [2]})

        assert "custom_rpt" in reg.list_names()
        cls = reg.get("custom_rpt")
        assert cls.meta.columns == ["a", "b"]

    def test_register_with_explicit_name(self):
        reg = ReportRegistry()

        @reg.register("renamed_rpt")
        class CustomReport(BaseReport):
            meta = ReportMeta(name="different_name", description="")
            def generate(self, ctx): return None

        # 用局部 reg 查,而不是全局 registry
        assert "renamed_rpt" in reg.list_names()
        cls = reg.get("renamed_rpt")
        assert cls.meta.name == "different_name"

    def test_list_meta(self):
        meta_list = registry.list_meta()
        assert len(meta_list) == 7
        for m in meta_list:
            assert isinstance(m, ReportMeta)
            assert m.description != ""


class TestPassthroughReport:
    def test_generate_returns_ctx_rpt(self):
        from dataclasses import dataclass, field

        @dataclass
        class FakeCtx:
            rpt: dict = field(default_factory=dict)

        ctx = FakeCtx()
        ctx.rpt["rpt_expiry_warning"] = pd.DataFrame({"a": [1]})
        cls = registry.get("rpt_expiry_warning")
        result = cls().generate(ctx)
        assert result["a"].iloc[0] == 1

    def test_generate_returns_none_when_missing(self):
        from dataclasses import dataclass, field

        @dataclass
        class FakeCtx:
            rpt: dict = field(default_factory=dict)

        cls = registry.get("rpt_expiry_warning")
        result = cls().generate(FakeCtx())
        assert result is None


class TestBaseReportAbstract:
    def test_cannot_instantiate_base_directly(self):
        with __import__("pytest").raises(TypeError):
            BaseReport()