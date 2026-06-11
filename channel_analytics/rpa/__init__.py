"""RPA 包 — 通用 ERP 浏览器自动化框架。

设计原则(PLAN.md §2.4):
  - 框架(本仓)和实现(具体厂商)完全解耦
  - 用户继承 ErpAdapter 实现 5 个钩子即可接入任意 Web ERP
  - 通过 Python entry_points 自动发现插件(`channel_analytics.rpa_adapters`)
  - 主仓 adapters/ 只保留 example_minimal.py(全 NotImplementedError)作为模板
"""
from __future__ import annotations

from channel_analytics.rpa.base import ErpAdapter
from channel_analytics.rpa.exceptions import (
    ExportError,
    LoginError,
    NavigateError,
    RpaError,
    SearchError,
)
from channel_analytics.rpa.runner import RpaRunner, RpaRunnerConfig

__all__ = [
    "ErpAdapter",
    "RpaRunner",
    "RpaRunnerConfig",
    "RpaError",
    "LoginError",
    "NavigateError",
    "ExportError",
    "SearchError",
]