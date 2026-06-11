"""Provider 加载器(entry_points + 字符串路径双模式)。"""
from __future__ import annotations

import importlib
from typing import Type

from channel_analytics.etl.brand import BrandWhitelistProvider


_ENTRY_POINT_GROUP = "channel_analytics.brand_providers"


def load_brand_provider(dotted: str) -> BrandWhitelistProvider:
    """按 `module:Class` 形式加载 provider。

    优先尝试 entry_points(便于三方包挂载),失败则回退到字符串路径。
    """
    if ":" in dotted:
        mod_path, class_name = dotted.split(":", 1)
    elif "." in dotted:
        # 退路: 没有冒号时按 `pkg.mod.Class` 处理
        parts = dotted.split(".")
        mod_path, class_name = ".".join(parts[:-1]), parts[-1]
    else:
        raise ValueError(
            f"brand_provider must be `module:Class` form, got: {dotted!r}"
        )

    # 1) 尝试 entry_points(如果 group 存在)
    try:
        eps = importlib.metadata.entry_points()  # type: ignore[attr-defined]
        if hasattr(eps, "select"):
            for ep in eps.select(group=_ENTRY_POINT_GROUP):
                if ep.module == mod_path and ep.attr == class_name:
                    cls = ep.load()
                    return _instantiate(cls)
        else:  # Python 3.9 fallback(distribution)
            for ep in eps.get(_ENTRY_POINT_GROUP, []):  # type: ignore[union-attr]
                if ep.module == mod_path and ep.attr == class_name:
                    cls = ep.load()
                    return _instantiate(cls)
    except Exception:  # pragma: no cover - 失败回落到 importlib
        pass

    # 2) 直接 importlib 加载
    module = importlib.import_module(mod_path)
    cls: Type[BrandWhitelistProvider] = getattr(module, class_name)
    return _instantiate(cls)


def _instantiate(cls: Type[BrandWhitelistProvider]) -> BrandWhitelistProvider:
    if not issubclass(cls, BrandWhitelistProvider):
        raise TypeError(f"{cls!r} must subclass BrandWhitelistProvider")
    # 默认无参构造;如有需要 Provider 自行读取环境变量
    return cls()
