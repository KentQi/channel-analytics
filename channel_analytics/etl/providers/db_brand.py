"""DbBrandWhitelistProvider — 从 dim_brand 表读品牌白名单(对应原仓 _get_self_operated_brands_from_db L184-194)。

设计要点:
  - 接 SQLAlchemy engine / Connection,跨 sqlite / mysql / postgres
  - 表名 `dim_brand`(新仓标准命名;原仓 `dim_self_operated_brand` 作为 alias)
  - 任何异常(表不存在 / 列不存在 / 权限)→ fallback 空集(防御部署环境差异)
  - 默认每次 get_brands() 都查 DB — 缓存用 lru_cache(若调用方需要热替换可禁用)
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import text

from channel_analytics.etl.brand import BrandWhitelistProvider


class DbBrandWhitelistProvider(BrandWhitelistProvider):
    """从 dim_brand 表读品牌白名单的 Provider。

    构造参数:
      engine: SQLAlchemy Engine 或 Connection 实例
      table_name: 表名,默认 'dim_brand'
      cache: 是否缓存查询结果(默认 True;False 用于部署期热重载)
    """

    DEFAULT_TABLE = "dim_brand"
    FALLBACK_TABLES = ("dim_brand", "dim_self_operated_brand")  # 兼容原仓命名

    def __init__(self, engine, table_name: str = DEFAULT_TABLE, cache: bool = True) -> None:
        self._engine = engine
        self._table_name = table_name
        self._cache = cache
        self._cached: frozenset[str] | None = None

    def get_brands(self) -> frozenset[str]:
        if self._cache and self._cached is not None:
            return self._cached
        brands = self._query_db()
        if self._cache:
            self._cached = brands
        return brands

    def invalidate(self) -> None:
        """手动清缓存(用于部署期热替换 / ETL 末尾 dim 同步后)。"""
        self._cached = None

    def _query_db(self) -> frozenset[str]:
        # 尝试候选表名(dim_brand → dim_self_operated_brand)
        for table in (self._table_name, *self.FALLBACK_TABLES):
            if table == self._table_name:
                continue  # 跳过第一个(避免重复)
            try:
                return self._read_table(table)
            except Exception:
                continue
        try:
            return self._read_table(self._table_name)
        except Exception:
            return frozenset()

    def _read_table(self, table: str) -> frozenset[str]:
        # 兼容 sqlite / mysql / postgres
        sql = text(f"SELECT brand_name FROM {table} ORDER BY brand_name")
        with self._engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return frozenset(r[0] for r in rows if r and r[0])


__all__ = ["DbBrandWhitelistProvider"]