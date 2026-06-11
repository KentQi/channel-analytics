"""Pipeline 步骤 11 — ETL 后自动同步 dim 表。

对应原仓 etl_service._auto_update_dim_after_etl (L720-732)。

新仓策略:
  - 接口设计为可注入的钩子函数,部署期挂真实同步逻辑
  - 默认实现是 no-op(因为 sync_product_dimension_from_stock_in / update_lifecycle_status 在 data_service 里,完整复刻超出 W5-7 范围)
  - ctx.meta['dim_sync_hooks'] 是可选 dict,key 是 hook 名,value 是 callable(ctx) -> dict
"""
from __future__ import annotations

import logging
from typing import Any, Callable, ClassVar

from channel_analytics.etl.types import EtlContext, Writer


logger = logging.getLogger(__name__)


class AutoUpdateDimStep(Writer):
    """Writer — ETL 末尾自动同步 dim 表。"""
    name: ClassVar[str] = "auto_update_dim"

    def run(self, ctx: EtlContext) -> EtlContext:
        hooks: dict[str, Callable[[EtlContext], dict[str, Any]]] = (
            ctx.meta.get("dim_sync_hooks") or {}
        )
        # 默认 hooks(可被 ctx.meta['dim_sync_hooks'] 覆盖)
        if not hooks:
            return ctx  # 默认无 hook,no-op

        for hook_name, hook_fn in hooks.items():
            try:
                result = hook_fn(ctx)
                logger.info("dim_sync[%s]: %s", hook_name, result)
            except Exception as e:  # 防御:不让 ETL 因 dim 同步失败而崩
                logger.warning("dim_sync[%s] 失败: %s", hook_name, e)
        return ctx


__all__ = ["AutoUpdateDimStep"]