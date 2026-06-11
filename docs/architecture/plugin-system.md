# 插件系统

两套插件:`ErpAdapter`(RPA) 和 `BrandWhitelistProvider`(品牌白名单)。

## ErpAdapter

5 个钩子,接入任意 Web ERP:

```python
from channel_analytics.rpa.base import ErpAdapter

class MyErpAdapter(ErpAdapter):
    async def login(self, page, url, username, password): ...
    async def navigate_to_module(self, page, module): ...
    async def search(self, page): ...
    async def export(self, page, download_dir): ...

# pyproject.toml
[project.entry-points."channel_analytics.rpa_adapters"]
my_erp = "my_pkg.my_module:MyErpAdapter"

# .env
RPA_ADAPTER=my_pkg.my_module:MyErpAdapter
```

详见 [how-to/write-erp-adapter.md](../../how-to/write-erp-adapter.md)。

## BrandWhitelistProvider

```python
from channel_analytics.etl.brand import BrandWhitelistProvider

class MyBrandProvider(BrandWhitelistProvider):
    def get_brands(self):
        return frozenset({"Brand A", "Brand B"})

# pyproject.toml
[project.entry-points."channel_analytics.brand_providers"]
my_brands = "my_pkg.brands:MyBrandProvider"

# .env / settings
BRAND_PROVIDER=my_pkg.brands:MyBrandProvider
```

主仓已实现 2 个 provider:
- `ExampleMinimalProvider` — 默认,返回空集
- `DbBrandWhitelistProvider` — 从 `dim_brand` 表读

## 插件发现机制

通过 Python 标准 `importlib.metadata.entry_points()`,group 名:
- `channel_analytics.rpa_adapters`
- `channel_analytics.brand_providers`

主仓只放 1 个示例(`ExampleMinimalAdapter` / `ExampleMinimalProvider`)。
具体厂商实现放用户自己的包,通过 `pip install` + entry_points 注册。