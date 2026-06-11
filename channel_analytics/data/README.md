# Mock 数据 fixtures

脱敏后的虚构数据,用于开发/演示/测试。

## 字段对齐

| Fixture | 字段数 | 对应原仓 STG 表 | 行数(默认) |
|---------|-------|----------------|------------|
| `load_sales_out_mock` | 27 | `stg_sales_out` | 2000 |
| `load_purchase_order_mock` | 13 | `stg_purchase_order` | 500 |
| `load_stock_in_mock` | 19 | `stg_stock_in` | 800 |
| `load_purchase_req_mock` | 14 | `stg_purchase_req` | 300 |
| `load_stock_current_mock` | 13 | `stg_stock_current` | 1500 |

## 数据生成

```python
from channel_analytics.data.fixtures import load_sales_out_mock
df = load_sales_out_mock(months=3, n=2000)
```

## 生成 CSV 文件

```bash
python -m channel_analytics.data.fixtures
# 生成到 data/fixtures/*_mock.csv
```

## 占位说明

- 12 个品牌名 `Brand A` - `Brand L` (替代真实自营品牌)
- 50 个虚拟客户 `客户001` - `客户050`
- 30 个虚拟 SKU `SKU-0001` - `SKU-0030`
- 30 个虚拟物料名 `物料-01` - `物料-30`
- 4 个渠道 / 3 个仓库 / 4 个 ABC 分类 / 5 个生命周期状态
- 所有日期基于 `2026/01/01` ~ `2026/06/10` 范围

## 与原仓差异

- 移除真实品牌 / 客户 / 厂商字符串
- 数据规模缩小(原仓 30k+ 行,本 fixtures 默认 2k 行)
- 时间范围收窄到 3 个月(原仓 1+ 年)
- 内部 ID 用 `SO-` / `PO-` / `RK-` / `PR-` / `BS-` 占位,无业务含义
