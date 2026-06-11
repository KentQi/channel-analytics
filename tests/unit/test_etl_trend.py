"""W5-5a/b 单测 — 趋势 4 段 + 状态分类。"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from channel_analytics.etl.rules import BusinessRules
from channel_analytics.etl.trend import (
    classify_trend_status,
    get_material_sales_trend,
    is_trend_warning,
)


CD = date(2026, 6, 10)
RULES = BusinessRules.defaults()  # cycle=30, ratio=3.0, min=1.0


# ---------------------------------------------------------------------------
# get_material_sales_trend
# ---------------------------------------------------------------------------

class TestGetMaterialSalesTrend:
    def test_empty_returns_zeros(self):
        assert get_material_sales_trend(pd.DataFrame(), "M1", CD, RULES) == [0.0] * 7

    def test_no_match_returns_zeros(self):
        df = pd.DataFrame({"material_code": ["M2"], "doc_date": [date(2026, 5, 1)], "sales_out_qty": [10]})
        assert get_material_sales_trend(df, "M1", CD, RULES) == [0.0] * 7

    def test_4_cycle_aggregation(self):
        """每段 30 天,4 段不同销售值 → 应分别汇总到 c4/c3/c2/c1。"""
        df = pd.DataFrame({
            "material_code": ["M1"] * 4,
            "doc_date": [
                date(2026, 2, 20),  # c4
                date(2026, 3, 20),  # c3
                date(2026, 4, 20),  # c2
                date(2026, 5, 20),  # c1
            ],
            "sales_out_qty": [10, 20, 30, 40],
        })
        result = get_material_sales_trend(df, "M1", CD, RULES)
        # 6/10 - 30 = 5/11 c1_start;6/10 c1_end
        # c1: [5/11, 6/10+1d) → 6/1 在内
        assert result[0] == 10  # c4
        assert result[1] == 20  # c3
        assert result[2] == 30  # c2
        assert result[3] == 40  # c1

    def test_returns_handling(self):
        # total_send / total_return / total_sales_90d 区分正负
        # CD=2026-06-10, td=30
        # c2=[5/11, 6/10), c1=[5/11, 6/11) → 5/1/5/15 都不在
        # 调整:5/15 在 c2,5/20 在 c2,6/1 在 c1
        df = pd.DataFrame({
            "material_code": ["M1"] * 4,
            "doc_date": [date(2026, 4, 20), date(2026, 5, 5), date(2026, 6, 1), date(2026, 6, 5)],
            "sales_out_qty": [50, -20, 30, -10],
        })
        result = get_material_sales_trend(df, "M1", CD, RULES)
        # c2: [5/11, 6/10) → 5/20, 5/25 → 50-20=30
        # c1: [5/11, 6/11) → 6/1 → 30
        # sales_90d=[c3=0, c2=30, c1=20]
        # total_send = sum(s for s in sales_90d if s > 0) = 30+20 = 50
        # total_return = abs(sum(s for s in sales_90d if s < 0)) = 0
        # total_sales_90d = sum(sales_90d) = 30+20 = 50
        assert result[4] == 50
        assert result[5] == 0
        assert result[6] == 50


# ---------------------------------------------------------------------------
# classify_trend_status
# ---------------------------------------------------------------------------

class TestClassifyTrendStatus:
    def test_short_input_returns_default(self):
        # 长度 < 4 返回无明显趋势
        ts, rr, *_ = classify_trend_status([0.0, 0.0], 100, RULES)
        assert ts == "无明显趋势"
        assert rr == 0.0

    def test_steady_trend_returns_稳定(self):
        """三段销售相近 → 无明显趋势"""
        ts, *_ = classify_trend_status([0, 50, 50, 50], 100, RULES)
        assert ts == "无明显趋势"

    def test_sustained_rise(self):
        # 持续上升 + 任一比率 >= 3 → 迉速攀升
        # c3=1, c2=10, c1=50 → d23=9, d12=40 都 > 1
        # r23=10/1=10>=3 → 迉速攀升
        ts, *_ = classify_trend_status([0, 1, 10, 50], 100, RULES)
        assert ts == "迉速攀升"

    def test_sustained_decline(self):
        # 持续下降 + 任一比率 <= 1/3 → 迉速下滑
        # c3=50, c2=10, c1=1 → d23=-40, d12=-9 都 < -1
        # r23=10/50=0.2<=1/3 → 迉速下滑
        ts, *_ = classify_trend_status([0, 50, 10, 1], 100, RULES)
        assert ts == "迉速下滑"

    def test_rise_then_fall(self):
        # 先升后降 → 4 种可能之一
        # c3=1, c2=50, c1=2 → d23=49>1, d12=-48<-1
        # r23=50, r12=2/50=0.04 → 0.04<=1/3 → 迉速冲高后显著回落
        ts, *_ = classify_trend_status([0, 1, 50, 2], 100, RULES)
        assert ts in (
            "迉速冲高后显著回落",
            "迉速冲高后企稳",
            "冲高后后显著回落",
            "正常波动",
        )

    def test_custom_trend_config(self):
        """YAML 改 ratio_threshold / min_change 后生效。"""
        rules = BusinessRules.from_dict({"trend": {"ratio_threshold": 5.0, "min_change": 2.0}})
        # ratio=5,min=2 时:c3=1, c2=10, c1=50
        # c3=max(1,2)=2, c2=max(10,2)=10, c1=50
        # d23=10-1=9>2, d12=50-10=40>2 → 持续上升
        # r23=10/2=5, r12=50/10=5, ratio=5 → r12>=R → 迉速攀升
        ts, *_ = classify_trend_status([0, 1, 10, 50], 100, rules)
        assert ts == "迉速攀升"

    def test_5_tuple_returned(self):
        """返回 5 元 tuple。"""
        out = classify_trend_status([0, 1, 1, 1], 100, RULES)
        assert len(out) == 5
        ts, rr, c3, c2, c1 = out
        assert c3 == 1 and c2 == 1 and c1 == 1
        assert isinstance(rr, float)


class TestIsTrendWarning:
    @pytest.mark.parametrize("status,warning", [
        ("迉速下滑", "预警"),
        ("持续下滑", "预警"),
        ("迉速冲高后显著回落", "预警"),
        ("冲高后后显著回落", "预警"),
        ("大幅下滑后显著攀升", "预警"),
        ("大幅下滑后企稳", "预警"),
        ("迉速攀升", "正常"),
        ("持续攀升", "正常"),
        ("正常波动", "正常"),
        ("无明显趋势", "正常"),
    ])
    def test_warning_keywords(self, status, warning):
        assert is_trend_warning(status) == warning