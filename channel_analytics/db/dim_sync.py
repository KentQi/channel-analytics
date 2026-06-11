"""dim_sync 默认 hooks — 对应原仓 _auto_update_dim_after_etl 调用的 2 个函数。

原仓:
  sync_product_dimension_from_stock_in(db) → 用 stock_in 同步 dim_product_attr
  update_lifecycle_status(db)              → 重新计算 lifecycle_status

新仓策略: 提供 SQLAlchemy ORM 风格的最小实现,作为 DefaultDimSyncHooks 的成员函数,
部署期可注入自定义版本。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from channel_analytics.db.models.dim import DimProductAttr
from channel_analytics.etl.types import EtlContext


class DefaultDimSyncHooks:
    """默认 dim_sync hooks — 注入 AutoUpdateDimStep。

    用法:
        engine = create_engine(DATABASE_URL)
        hooks = DefaultDimSyncHooks(engine)
        ctx.meta["dim_sync_hooks"] = hooks.as_dict()
    """

    def __init__(self, engine) -> None:
        self._engine = engine

    def as_dict(self) -> dict[str, Any]:
        return {
            "sync_product_dim": self.sync_product_dimension_from_stock_in,
            "update_lifecycle": self.update_lifecycle_status,
        }

    def sync_product_dimension_from_stock_in(self, ctx: EtlContext) -> dict[str, int]:
        """从 stg_stock_in 抽取 (material_code, material_name) → UPSERT dim_product_attr。

        返回 {inserted, updated}。
        """
        stock_in = ctx.stg.get("stg_stock_in")
        if stock_in is None:
            stock_in = ctx.raw_data.get("stg_stock_in")
        if stock_in is None or stock_in.empty:
            return {"inserted": 0, "updated": 0}
        if "material_code" not in stock_in.columns:
            return {"inserted": 0, "updated": 0}

        # 取最新一条 material_name
        mat = (
            stock_in[["material_code", "material_name"]]
            .dropna(subset=["material_code"])
            .drop_duplicates("material_code", keep="last")
        )

        inserted = 0
        updated = 0
        now = datetime.now(timezone.utc)
        with Session(self._engine) as session:
            for _, row in mat.iterrows():
                code = str(row["material_code"])
                name = str(row.get("material_name", "")) or None
                existing = session.execute(
                    select(DimProductAttr).where(DimProductAttr.material_code == code)
                ).scalar_one_or_none()
                if existing is None:
                    session.add(DimProductAttr(
                        material_code=code, material_name=name, updated_at=now,
                    ))
                    inserted += 1
                else:
                    if name and existing.material_name != name:
                        existing.material_name = name
                        existing.updated_at = now
                        updated += 1
            session.commit()
        return {"inserted": inserted, "updated": updated}

    def update_lifecycle_status(self, ctx: EtlContext) -> dict[str, int]:
        """根据 90 天销售汇总重新计算 lifecycle_status。

        简单规则:
          - 无销售且有库存 → '休眠'
          - 高销售(>= 30/天) → '畅销'
          - 有销售 → '正常'
          - 无销售无库存 → '停售'(不写)
        """
        trend = ctx.rpt.get("rpt_trend_warning")
        if trend is None or trend.empty:
            return {"updated": 0}

        updated = 0
        now = datetime.now(timezone.utc)
        with Session(self._engine) as session:
            for _, row in trend.iterrows():
                code = str(row["material_code"])
                sales_90d = int(row.get("sales_90d", 0) or 0)
                stock = int(row.get("material_available_qty", 0) or 0)
                if stock <= 0 and sales_90d <= 0:
                    continue
                if sales_90d <= 0:
                    status = "休眠"
                elif sales_90d >= 30 * 90:
                    status = "畅销"
                else:
                    status = "正常"
                existing = session.execute(
                    select(DimProductAttr).where(DimProductAttr.material_code == code)
                ).scalar_one_or_none()
                if existing is not None and existing.lifecycle_status != status:
                    existing.lifecycle_status = status
                    existing.updated_at = now
                    updated += 1
            session.commit()
        return {"updated": updated}


__all__ = ["DefaultDimSyncHooks"]