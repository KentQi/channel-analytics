"""W5-8 单测 — DbBrandWhitelistProvider。"""
from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import create_engine

from channel_analytics.etl.providers.db_brand import DbBrandWhitelistProvider


@pytest.fixture
def sqlite_engine():
    return create_engine("sqlite:///:memory:")


def _seed_brands(engine, table: str = "dim_brand", brands: list[str] | None = None) -> None:
    brands = brands or ["BrandA", "BrandB"]
    df = pd.DataFrame({"brand_name": brands})
    df.to_sql(table, engine, index=False, if_exists="replace")


class TestDbBrandWhitelistProvider:
    def test_empty_when_table_not_exists(self, sqlite_engine):
        """dim_brand 表不存在 → 空集,不抛异常。"""
        p = DbBrandWhitelistProvider(sqlite_engine)
        assert p.get_brands() == frozenset()

    def test_reads_from_dim_brand(self, sqlite_engine):
        _seed_brands(sqlite_engine, brands=["BrandA", "BrandB", "BrandC"])
        p = DbBrandWhitelistProvider(sqlite_engine)
        assert p.get_brands() == frozenset({"BrandA", "BrandB", "BrandC"})

    def test_fallback_to_original_table_name(self, sqlite_engine):
        """原仓 dim_self_operated_brand 表名也支持。"""
        _seed_brands(sqlite_engine, table="dim_self_operated_brand", brands=["LegacyBrand"])
        p = DbBrandWhitelistProvider(sqlite_engine)
        assert p.get_brands() == frozenset({"LegacyBrand"})

    def test_filter_null_brands(self, sqlite_engine):
        """None / 空 brand_name 应被过滤。"""
        _seed_brands(sqlite_engine, brands=["BrandA", None, "", "BrandB"])
        p = DbBrandWhitelistProvider(sqlite_engine)
        # None 和空串被排除
        assert p.get_brands() == frozenset({"BrandA", "BrandB"})

    def test_cache_enabled_returns_same_set(self, sqlite_engine):
        _seed_brands(sqlite_engine, brands=["BrandA"])
        p = DbBrandWhitelistProvider(sqlite_engine, cache=True)
        first = p.get_brands()
        # 再写入一条新品牌,缓存应该还是原值
        _seed_brands(sqlite_engine, brands=["BrandA", "BrandB"])
        # 此时 DB 已是 2 条,但 cache 还在
        assert p.get_brands() == first  # 缓存命中

    def test_cache_disabled_re_reads(self, sqlite_engine):
        _seed_brands(sqlite_engine, brands=["BrandA"])
        p = DbBrandWhitelistProvider(sqlite_engine, cache=False)
        first = p.get_brands()
        _seed_brands(sqlite_engine, brands=["BrandA", "BrandB"])
        second = p.get_brands()
        assert second != first

    def test_invalidate_clears_cache(self, sqlite_engine):
        _seed_brands(sqlite_engine, brands=["BrandA"])
        p = DbBrandWhitelistProvider(sqlite_engine, cache=True)
        p.get_brands()  # 触发缓存
        _seed_brands(sqlite_engine, brands=["BrandA", "BrandB"])
        p.invalidate()
        assert "BrandB" in p.get_brands()

    def test_custom_table_name(self, sqlite_engine):
        _seed_brands(sqlite_engine, table="my_brands", brands=["CustomBrand"])
        p = DbBrandWhitelistProvider(sqlite_engine, table_name="my_brands")
        assert p.get_brands() == frozenset({"CustomBrand"})

    def test_is_self_operated_helper(self, sqlite_engine):
        _seed_brands(sqlite_engine, brands=["KnownBrand"])
        p = DbBrandWhitelistProvider(sqlite_engine)
        assert p.is_self_operated("KnownBrand") is True
        assert p.is_self_operated("UnknownBrand") is False