"""ETL Pipeline — 步骤注册表(对应原仓 etl_service.run_etl 的串接顺序)。

设计要点:
  - 步骤分三类:Loader / Transformer / Writer
  - Pipeline 跑时按 registered order 串行执行
  - DefaultPipeline 复刻原仓 run_etl 的步骤顺序,**不实现具体业务逻辑**
    (W4 起按本骨架逐个 PR 复刻 clean_batch / classify_expiry / ... 等函数)
  - 所有步骤可被三方包覆盖(entry_points 后续 W4+)

为什么先建骨架:
  - 让新仓 import 路径稳定,后续 PR 不会破坏外部调用方
  - 烟雾测试可以验证"空数据 + 空白名单 + 默认规则 → 跑通"

EtlContext / Step / Loader / Transformer / Writer 在 types.py 定义,
本文件 re-export 保持向后兼容(老 import `from .pipeline import EtlContext` 仍可用)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from channel_analytics.etl.brand import BrandWhitelistProvider
from channel_analytics.etl.provider_loader import load_brand_provider
from channel_analytics.etl.rules import BusinessRules, load_rules_for_settings
from channel_analytics.etl.steps.analyze_expiry_turnover import AnalyzeExpiryTurnoverStep
from channel_analytics.etl.steps.analyze_expiry_warning import AnalyzeExpiryWarningStep
from channel_analytics.etl.steps.analyze_material_warehouse_risk import (
    AnalyzeMaterialWarehouseRiskStep,
)
from channel_analytics.etl.steps.analyze_self_operated_concentration import (
    AnalyzeSelfOperatedConcentrationStep,
)
from channel_analytics.etl.steps.analyze_trend_warning import AnalyzeTrendWarningStep
from channel_analytics.etl.steps.analyze_turnover_warning import AnalyzeTurnoverWarningStep
from channel_analytics.etl.steps.auto_update_dim import AutoUpdateDimStep
from channel_analytics.etl.steps.clean_stg_fields import CleanStgFieldsStep
from channel_analytics.etl.steps.fill_stock_expiry import FillStockExpiryStep
from channel_analytics.etl.steps.link_procurement_process import LinkProcurementProcessStep
from channel_analytics.etl.steps.write_rpt_tables import WriteRptTablesStep
from channel_analytics.etl.types import (
    EtlContext,
    Loader,
    Step,
    Transformer,
    Writer,
)

# Re-export,保持旧 import 路径可用
__all__ = [
    "EtlContext",
    "Step",
    "Loader",
    "Transformer",
    "Writer",
    "Pipeline",
    "build_default_pipeline",
    "make_context",
    "run_default_etl",
]


# ---------------------------------------------------------------------------
# 默认步骤(no-op 占位,W4 起替换为真实实现)
# ---------------------------------------------------------------------------

class _NoOp(Transformer):
    name = "noop"

    def run(self, ctx: EtlContext) -> EtlContext:
        return ctx


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@dataclass
class Pipeline:
    """ETL 步骤注册表。"""
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> "Pipeline":
        self.steps.append(step)
        return self

    def run(self, ctx: EtlContext) -> EtlContext:
        for step in self.steps:
            ctx = step.run(ctx)
        return ctx


def build_default_pipeline(
    brand_provider: BrandWhitelistProvider,
    rules: BusinessRules,
) -> Pipeline:
    """构造 DefaultPipeline — 步骤顺序对齐原仓 run_etl。

    真实业务逻辑(W4+ 起按本仓 clean_batch / classify_expiry 等函数逐个 PR 复刻)
    暂时用 noop 占位,**不改 import 路径**。
    """
    p = Pipeline()
    # 原仓顺序(对应 L736 run_etl):
    #   preprocess_data  → fill_stock_expiry_date
    #   → 7 张 RPT(expiry / et / conc / turn / trend / risk / proc)
    #   → build_sales_out_wide  → _auto_update_dim_after_etl  → 写库
    p.add(CleanStgFieldsStep())  # 1. preprocess(已复刻 W4-4)
    p.add(FillStockExpiryStep())  # 2. fill_stock_expiry_date(已复刻 W5-1c)
    p.add(AnalyzeExpiryWarningStep())  # 3. analyze_expiry_warning(已复刻 W5-3b)
    p.add(AnalyzeExpiryTurnoverStep())  # 4. analyze_expiry_turnover(已复刻 W5-3c)
    p.add(AnalyzeSelfOperatedConcentrationStep())  # 5. self_operated_concentration(已复刻 W5-4a)
    p.add(AnalyzeTurnoverWarningStep())  # 6. analyze_turnover_warning(已复刻 W5-4b)
    p.add(AnalyzeTrendWarningStep())  # 7. analyze_trend_warning(已复刻 W5-5c)
    p.add(AnalyzeMaterialWarehouseRiskStep())  # 8. material_warehouse_risk(已复刻 W5-6a)
    p.add(LinkProcurementProcessStep())  # 9. link_procurement_process(已复刻 W5-6b)
    p.add(_NoOp())  # 10. build_sales_out_wide(强依赖 DB + dim,留待 W5-7+ DB 接入后再做)
    p.add(AutoUpdateDimStep())  # 11. auto_update_dim(已复刻 W5-7b,可注入 hooks)
    p.add(WriteRptTablesStep())  # 12. write_rpt_tables(已复刻 W5-7a)
    return p


# ---------------------------------------------------------------------------
# 工厂(CLI / API 入口)
# ---------------------------------------------------------------------------

def make_context(
    raw_data: dict[str, pd.DataFrame] | None = None,
    *,
    brand_provider_dotted: str,
    business_rules_path: str = "",
) -> EtlContext:
    """构造 EtlContext,内部完成 provider / rules 加载。"""
    provider = load_brand_provider(brand_provider_dotted)
    rules = load_rules_for_settings(business_rules_path)
    ctx = EtlContext(raw_data=raw_data or {})
    ctx.meta["brand_provider"] = provider
    ctx.meta["rules"] = rules
    return ctx


def run_default_etl(
    raw_data: dict[str, pd.DataFrame],
    *,
    brand_provider_dotted: str,
    business_rules_path: str = "",
) -> EtlContext:
    """高层入口:加载 → 跑 DefaultPipeline。"""
    ctx = make_context(
        raw_data,
        brand_provider_dotted=brand_provider_dotted,
        business_rules_path=business_rules_path,
    )
    pipeline = build_default_pipeline(
        brand_provider=ctx.meta["brand_provider"],
        rules=ctx.meta["rules"],
    )
    return pipeline.run(ctx)
