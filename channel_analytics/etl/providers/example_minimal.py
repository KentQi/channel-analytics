"""开源仓默认 BrandWhitelistProvider — 始终返回空集。"""
from __future__ import annotations

from channel_analytics.etl.brand import BrandWhitelistProvider


class ExampleMinimalProvider(BrandWhitelistProvider):
    """开源仓默认实现 — 永远返回空集。

    设计意图:
      - 真实品牌白名单应在部署环境通过私有配置 / 数据库表注入
      - 真实词条 **绝不** 出现在本仓代码内(对应 PLAN.md §6 P0)
    """

    def get_brands(self) -> frozenset[str]:
        return frozenset()
