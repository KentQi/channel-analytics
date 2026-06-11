"""W5-6 单测 — RPT 6 综合风险 + RPT 7 采购三表关联。"""
from __future__ import annotations

from datetime import date

import pandas as pd

from channel_analytics.etl.providers.example_minimal import ExampleMinimalProvider
from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.steps.analyze_material_warehouse_risk import (
    AnalyzeMaterialWarehouseRiskStep,
)
from channel_analytics.etl.steps.link_procurement_process import (
    LinkProcurementProcessStep,
)
from channel_analytics.etl.types import EtlContext


def _ctx(stg=None, raw=None, rpt=None) -> EtlContext:
    return EtlContext(
        stg=stg or {},
        raw_data=raw or {},
        rpt=rpt or {},
        meta={
            "rules": BusinessRules.defaults(),
            "brand_provider": ExampleMinimalProvider(),
            "current_date": date(2026, 6, 10),
        },
    )


# ---------------------------------------------------------------------------
# RPT 6
# ---------------------------------------------------------------------------

class TestAnalyzeMaterialWarehouseRisk:
    def test_skips_when_stock_empty(self):
        out = AnalyzeMaterialWarehouseRiskStep().run(_ctx())
        assert "rpt_warehouse_risk" not in out.rpt

    def test_skips_when_required_columns_missing(self):
        stg = {"stg_stock_current": pd.DataFrame({"material_code": ["M1"]})}
        out = AnalyzeMaterialWarehouseRiskStep().run(_ctx(stg=stg))
        assert "rpt_warehouse_risk" not in out.rpt

    def test_risk_levels(self):
        """0 预警 → 低风险,1 预警 → 中风险,2+ → 高风险。"""
        stg = {
            "stg_stock_current": pd.DataFrame({
                "warehouse": ["W1", "W1", "W1"],
                "material_code": ["M1", "M2", "M3"],
                "material_name": ["n1", "n2", "n3"],
                "brand": ["A", "B", "C"],
            }),
        }
        rpt = {
            "rpt_expiry_warning": pd.DataFrame({
                "material_code": ["M1", "M2", "M3"],
                "expiry_warning": ["预警", "正常", "预警"],
            }),
            "rpt_turnover_warning": pd.DataFrame({
                "material_code": ["M1", "M2", "M3"],
                "turnover_warning": ["预警", "正常", "正常"],
                "inventory_days": [200, 30, 40],
                "material_available_qty": [100, 50, 60],
            }),
            "rpt_trend_warning": pd.DataFrame({
                "material_code": ["M1", "M2", "M3"],
                "trend_warning": ["正常", "正常", "预警"],
                "trend_status": ["持续上升", "无明显趋势", "迉速下滑"],
                "return_ratio": ["0.0%", "0.0%", "5.0%"],
            }),
        }
        out = AnalyzeMaterialWarehouseRiskStep().run(_ctx(stg=stg, rpt=rpt))
        r = out.rpt["rpt_warehouse_risk"].set_index("material_code")
        # M1: expiry+turnover 预警 → 高风险
        assert r.loc["M1", "risk_level"] == "高风险"
        # M2: 无预警 → 低风险
        assert r.loc["M2", "risk_level"] == "低风险"
        # M3: expiry+trend 预警 → 高风险
        assert r.loc["M3", "risk_level"] == "高风险"

    def test_output_13_columns(self):
        stg = {"stg_stock_current": pd.DataFrame({
            "warehouse": ["W1"], "material_code": ["M1"],
            "material_name": ["n1"], "brand": ["A"],
        })}
        out = AnalyzeMaterialWarehouseRiskStep().run(_ctx(stg=stg))
        assert len(out.rpt["rpt_warehouse_risk"].columns) == 13

    def test_no_rpt_inputs_yields_low_risk(self):
        """无 RPT 1/4/5 时,所有预警列兜底"正常" → 低风险。"""
        stg = {"stg_stock_current": pd.DataFrame({
            "warehouse": ["W1"], "material_code": ["M1"],
            "material_name": ["n1"], "brand": ["A"],
        })}
        out = AnalyzeMaterialWarehouseRiskStep().run(_ctx(stg=stg))
        r = out.rpt["rpt_warehouse_risk"].iloc[0]
        assert r["risk_level"] == "低风险"
        assert r["expiry_warning_status"] == "正常"


# ---------------------------------------------------------------------------
# RPT 7
# ---------------------------------------------------------------------------

class TestLinkProcurementProcess:
    def test_skips_when_any_input_missing(self):
        out = LinkProcurementProcessStep().run(_ctx(stg={
            "stg_purchase_req": pd.DataFrame({"order_no": ["O1"]}),
        }))
        assert "rpt_procurement_linked" not in out.rpt

    def test_links_three_tables(self):
        """三表 join + % 计算 + pending 数。"""
        stg = {
            "stg_purchase_req": pd.DataFrame({
                "order_no": ["O1", "O1"],
                "material_code": ["M1", "M2"],
                "order_qty": [100, 200],
                "delivery_cycle": [7, 14],
            }),
            "stg_purchase_order": pd.DataFrame({
                "order_no": ["O1", "O1"],
                "material_code": ["M1", "M2"],
                "factory_delivery_qty": [80, 100],
                "pickup_qty": [80, 50],
                "delivery_date": [date(2026, 5, 1), date(2026, 5, 5)],
                "brand_sales_no": ["B1", "B2"],
            }),
            "stg_stock_in": pd.DataFrame({
                "brand_sales_no": ["B1", "B2"],
                "material_code": ["M1", "M2"],
                "stock_in_qty": [80, 30],
                "stock_in_date": [date(2026, 5, 2), date(2026, 5, 7)],
            }),
        }
        out = LinkProcurementProcessStep().run(_ctx(stg=stg))
        r = out.rpt["rpt_procurement_linked"].set_index("material_code")
        assert r.loc["M1", "procurement_delivery_rate"] == "80.0%"
        assert r.loc["M1", "procurement_pickup_rate"] == "80.0%"
        assert r.loc["M1", "stock_in_complete_rate"] == "80.0%"
        assert r.loc["M1", "pending_delivery_qty"] == 20
        assert r.loc["M1", "pending_pickup_qty"] == 0
        assert r.loc["M1", "pending_stock_in_qty"] == 0
        # M2: 200 - 100 = 100 pending_delivery
        assert r.loc["M2", "pending_delivery_qty"] == 100

    def test_handles_zero_order_qty(self):
        """order_qty=0 时 % 字符串为 "0.0%",不抛 ZeroDivision。"""
        stg = {
            "stg_purchase_req": pd.DataFrame({
                "order_no": ["O1"], "material_code": ["M1"],
                "order_qty": [0], "delivery_cycle": [7],
            }),
            "stg_purchase_order": pd.DataFrame({
                "order_no": ["O1"], "material_code": ["M1"],
                "factory_delivery_qty": [0], "pickup_qty": [0],
                "delivery_date": [date(2026, 5, 1)], "brand_sales_no": ["B1"],
            }),
            "stg_stock_in": pd.DataFrame({
                "brand_sales_no": ["B1"], "material_code": ["M1"],
                "stock_in_qty": [0], "stock_in_date": [date(2026, 5, 2)],
            }),
        }
        out = LinkProcurementProcessStep().run(_ctx(stg=stg))
        r = out.rpt["rpt_procurement_linked"].iloc[0]
        assert r["procurement_delivery_rate"] == "0.0%"
        assert r["stock_in_complete_rate"] == "0.0%"

    def test_skips_when_required_columns_missing(self):
        stg = {
            "stg_purchase_req": pd.DataFrame({"unrelated": [1]}),
            "stg_purchase_order": pd.DataFrame({"order_no": ["O1"]}),
            "stg_stock_in": pd.DataFrame({"brand_sales_no": ["B1"]}),
        }
        out = LinkProcurementProcessStep().run(_ctx(stg=stg))
        assert "rpt_procurement_linked" not in out.rpt