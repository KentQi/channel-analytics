# 添加品牌白名单

3 种方式。

## 方式 1:DB 表(推荐生产)

```sql
INSERT INTO dim_brand (brand_name) VALUES ('Brand A'), ('Brand B');
```

`DbBrandWhitelistProvider` 自动读取:

```python
from channel_analytics.etl.providers.db_brand import DbBrandWhitelistProvider
from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://...")
provider = DbBrandWhitelistProvider(engine, table_name="dim_brand")
print(provider.get_brands())  # frozenset({"Brand A", "Brand B"})
```

## 方式 2:自定义 provider

```python
from channel_analytics.etl.brand import BrandWhitelistProvider

class CsvBrandProvider(BrandWhitelistProvider):
    def get_brands(self):
        with open("brands.csv") as f:
            return frozenset(line.strip() for line in f)

# 注册到 entry_points
# pyproject.toml:
# [project.entry-points."channel_analytics.brand_providers"]
# csv = "my_pkg.csv_brands:CsvBrandProvider"
```

## 方式 3:YAML(开发)

```yaml
# examples/cosmetics_demo/brands.yaml
brands:
  - name: "Brand A"
  - name: "Brand B"
```

```python
import yaml
from channel_analytics.etl.brand import BrandWhitelistProvider

class YamlBrandProvider(BrandWhitelistProvider):
    def __init__(self, path: str):
        with open(path) as f:
            data = yaml.safe_load(f)
        self._brands = frozenset(b["name"] for b in data["brands"])
    def get_brands(self):
        return self._brands
```

## 在 ETL Pipeline 中使用

```python
ctx = run_default_etl(
    raw_data,
    brand_provider_dotted="my_pkg.csv_brands:CsvBrandProvider",
)
```

或在 `.env`:

```
BRAND_PROVIDER=channel_analytics.etl.providers.db_brand:DbBrandWhitelistProvider
```

## 安全约束

- **严禁**在开源仓的代码 / 文档 / 测试数据中写真实品牌名(对应 PLAN.md §6 P0)
- `scripts/check_branding.py` 会扫描仓库,任何命中阻断 CI