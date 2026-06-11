"""自营品牌白名单抽象(对应原仓 _get_self_operated_brands_from_db)。

设计要点:
  - Provider 通过 entry_points(`channel_analytics.rpa_adapters` 同款机制,
    暂用 `channel_analytics.brand_providers`)发现,默认实现指向
    `channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider`
  - 所有实现必须返回 frozenset[str],**禁止把真实品牌名写进新仓代码**
  - 返回空集合法 — 表示"无白名单,全部按非自营分类"
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BrandWhitelistProvider(ABC):
    """自营品牌白名单的数据源。

    实现方:
      - ExampleMinimalProvider : 默认实现,返回空集(新仓默认)
      - DbBrandWhitelistProvider: 从 dim_brand 表读(W4+ 接入)
      - FileBrandWhitelistProvider: 从 .yaml 读(开发期用)
    """

    @abstractmethod
    def get_brands(self) -> frozenset[str]:
        """返回自营品牌名集合(去重、不可变)。"""
        raise NotImplementedError

    # 便捷方法
    def is_self_operated(self, brand: str) -> bool:
        return brand in self.get_brands()
