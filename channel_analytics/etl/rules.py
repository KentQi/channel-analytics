"""业务规则阈值(对应原仓 ETLConfig 中硬编码的数字常量)。

设计要点:
  - 默认值在代码内(BusinessRules.defaults()),无需 YAML 也能跑
  - YAML 存在时覆盖默认值(部署期 / 测试可调阈值,不改代码)
  - 字段都是数值/列表,不接受字符串
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from channel_analytics.etl.brand import BrandWhitelistProvider


# ---------------------------------------------------------------------------
# 规则字段
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrendConfig:
    """销售趋势判断阈值(对应原仓 ETLConfig.TREND_CONFIG)。"""
    ratio_threshold: float = 3.0   # 期末/期初 >= 3 视为"突增"
    min_change: float = 1.0        # 绝对变化 < 1 时不报警


@dataclass(frozen=True)
class TurnoverBand:
    """周转档位 — 上限(开区间,exclusive)与标签。"""
    upper: float       # 该档位的天数上界(不含)
    label: str

    def contains(self, days: float) -> bool:
        return 0 <= days < self.upper


@dataclass(frozen=True)
class BusinessRules:
    """业务规则阈值集合(对应原仓 ETLConfig 中的全部常量)。"""

    # 清洗规则(批次号 / 效期)
    batch_clean_rules: tuple[str, ...] = ("", " ", "NA", "/", "\\", "无", "虚拟退货")
    expiry_clean_rules: tuple[str, ...] = ("", " ")

    # 周转 / 趋势周期
    turnover_cycle_days: int = 90
    trend_cycle_days: int = 30

    # 趋势阈值
    trend: TrendConfig = field(default_factory=TrendConfig)

    # 周转档位(对应原仓 classify_turnover_status L170-180)
    # 上界按降序,首个满足 contains() 的胜出;最后一段无限上界
    turnover_status_bands: tuple[TurnoverBand, ...] = (
        TurnoverBand(30, "周转健康(<30天)"),
        TurnoverBand(60, "周转正常(30-60天)"),
        TurnoverBand(90, "周转偏低(60-90天)"),
        TurnoverBand(float("inf"), "周转高(>90天)"),
    )
    # 周转计算:无销售/销售<=0 时返回 sentinel
    inventory_days_sentinel: float = 999.0

    # 周转告警阈值(对应原仓 analyze_turnover_warning L556)
    # inventory_days < low OR inventory_days > high → "预警"
    turnover_warning_low: float = 15.0
    turnover_warning_high: float = 60.0

    @classmethod
    def defaults(cls) -> "BusinessRules":
        """代码内默认值 — 不依赖任何 YAML / DB。"""
        return cls()

    @classmethod
    def from_yaml(cls, path: Path | str) -> "BusinessRules":
        """从 YAML 加载,缺失字段用 defaults() 填充。"""
        path = Path(path)
        if not path.exists():
            return cls.defaults()
        with path.open("r", encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "BusinessRules":
        """从 dict 构造(测试友好)。"""
        defaults = cls.defaults()
        trend_raw = raw.get("trend", {}) or {}
        trend = TrendConfig(
            ratio_threshold=float(trend_raw.get("ratio_threshold", defaults.trend.ratio_threshold)),
            min_change=float(trend_raw.get("min_change", defaults.trend.min_change)),
        )
        bands = _parse_turnover_bands(
            raw.get("turnover_status_bands"),
            defaults.turnover_status_bands,
        )
        return cls(
            batch_clean_rules=tuple(raw.get("batch_clean_rules", defaults.batch_clean_rules)),
            expiry_clean_rules=tuple(raw.get("expiry_clean_rules", defaults.expiry_clean_rules)),
            turnover_cycle_days=int(raw.get("turnover_cycle_days", defaults.turnover_cycle_days)),
            trend_cycle_days=int(raw.get("trend_cycle_days", defaults.trend_cycle_days)),
            trend=trend,
            turnover_status_bands=bands,
            inventory_days_sentinel=float(
                raw.get("inventory_days_sentinel", defaults.inventory_days_sentinel)
            ),
            turnover_warning_low=float(
                raw.get("turnover_warning_low", defaults.turnover_warning_low)
            ),
            turnover_warning_high=float(
                raw.get("turnover_warning_high", defaults.turnover_warning_high)
            ),
        )


def _parse_turnover_bands(
    raw: Any,
    defaults: tuple[TurnoverBand, ...],
) -> tuple[TurnoverBand, ...]:
    """从 YAML dict 解析档位。缺失或非法 → 兜底 defaults。"""
    if not isinstance(raw, list) or not raw:
        return defaults
    out: list[TurnoverBand] = []
    for item in raw:
        if not isinstance(item, dict):
            return defaults
        if "upper" not in item or "label" not in item:
            return defaults
        try:
            upper = float(item["upper"])
        except (TypeError, ValueError):
            return defaults
        out.append(TurnoverBand(upper, str(item["label"])))
    if not out:
        return defaults
    return tuple(out)


def load_rules_for_settings(settings_path: str) -> BusinessRules:
    """按 settings.business_rules_path 加载,空字符串 → defaults()。"""
    if not settings_path:
        return BusinessRules.defaults()
    return BusinessRules.from_yaml(settings_path)


__all__ = [
    "BrandWhitelistProvider",
    "BusinessRules",
    "TrendConfig",
    "TurnoverBand",
    "load_rules_for_settings",
]
