"""W3 烟雾测试 — 验证 BrandWhitelistProvider / BusinessRules / Pipeline 跑通。"""
from __future__ import annotations

import pandas as pd

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.pipeline import (
    EtlContext,
    Pipeline,
    build_default_pipeline,
    make_context,
    run_default_etl,
)
from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules, TrendConfig


# ---------------------------------------------------------------------------
# BrandWhitelistProvider
# ---------------------------------------------------------------------------

def test_example_minimal_provider_returns_empty():
    """默认 provider 必须返回空集(确保新仓代码不含任何品牌名)。"""
    p = ExampleMinimalProvider()
    assert p.get_brands() == frozenset()
    assert p.is_self_operated("any-brand") is False


def test_provider_loader_resolves_dotted_path():
    """`module:Class` 形式可被加载。"""
    from channel_analytics.etl.provider_loader import load_brand_provider
    p = load_brand_provider(
        "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
    )
    assert isinstance(p, BrandWhitelistProvider)
    assert p.get_brands() == frozenset()


# ---------------------------------------------------------------------------
# BusinessRules
# ---------------------------------------------------------------------------

def test_business_rules_defaults():
    """默认值等于原仓 ETLConfig 的硬编码(7 项 batch_clean_rules / 90 / 30 / 3.0 / 1.0)。"""
    r = BusinessRules.defaults()
    assert r.turnover_cycle_days == 90
    assert r.trend_cycle_days == 30
    assert r.trend.ratio_threshold == 3.0
    assert r.trend.min_change == 1.0
    assert "无" in r.batch_clean_rules
    assert "虚拟退货" in r.batch_clean_rules


def test_business_rules_from_dict_overrides():
    """dict 加载支持部分覆盖。"""
    r = BusinessRules.from_dict({
        "turnover_cycle_days": 60,
        "trend": {"ratio_threshold": 5.0},
    })
    assert r.turnover_cycle_days == 60
    assert r.trend.ratio_threshold == 5.0
    # 未覆盖字段保持默认
    assert r.trend.min_change == 1.0
    assert r.trend_cycle_days == 30


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def test_default_pipeline_runs_with_empty_data():
    """空数据 + 默认 provider + 默认规则 → 跑通,ctx 仍是 EtlContext。"""
    ctx = run_default_etl(
        raw_data={},
        brand_provider_dotted=(
            "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
        ),
    )
    assert isinstance(ctx, EtlContext)
    assert ctx.stg == {}
    # RPT 1/2/4 步骤在缺数据时不写入(避免污染);RPT 3 主动写空表(保留列结构,原仓行为)
    assert "rpt_expiry_warning" not in ctx.rpt
    assert "rpt_expiry_turnover" not in ctx.rpt
    assert "rpt_turnover_warning" not in ctx.rpt
    # RPT 3 写空表,断言列结构保留
    rpt3 = ctx.rpt.get("rpt_self_operated_concentration")
    assert rpt3 is not None and rpt3.empty
    assert "material_code" in rpt3.columns
    assert isinstance(ctx.meta["brand_provider"], BrandWhitelistProvider)
    assert isinstance(ctx.meta["rules"], BusinessRules)


def test_pipeline_step_order_preserved():
    """Pipeline.steps 顺序 = 注册顺序(DefaultPipeline 至少 12 步对齐原仓 run_etl)。"""
    p = build_default_pipeline(
        brand_provider=ExampleMinimalProvider(),
        rules=BusinessRules.defaults(),
    )
    assert len(p.steps) >= 12


def test_custom_pipeline_supports_extra_steps():
    """Pipeline.add 可链式追加自定义步骤。"""
    p = Pipeline()
    seen: list[str] = []

    class S1:
        name = "s1"
        def run(self, ctx):
            seen.append("s1")
            return ctx

    class S2:
        name = "s2"
        def run(self, ctx):
            seen.append("s2")
            return ctx

    p.add(S1()).add(S2()).run(EtlContext())
    assert seen == ["s1", "s2"]
