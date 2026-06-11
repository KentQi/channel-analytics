# ETL Pipeline

12 步骤的 ETL 流水线。

## 步骤一览

| # | 步骤 | 输入 | 输出 |
|---|------|------|------|
| 1 | `CleanStgFieldsStep` | raw_data | ctx.stg(5 张 STG 清洗后) |
| 2 | `FillStockExpiryStep` | stg_stock_in + stg_stock_current | stg_stock_current.expiry_date 填补 |
| 3 | `AnalyzeExpiryWarningStep` | stg_stock_current + stg_sales_out | RPT 1 物料+批次效期告警 |
| 4 | `AnalyzeExpiryTurnoverStep` | RPT 1 | RPT 2 效期-周转关联 |
| 5 | `AnalyzeSelfOperatedConcentrationStep` | RPT 1 | RPT 3 自营集中度 |
| 6 | `AnalyzeTurnoverWarningStep` | stg_stock_current + stg_sales_out | RPT 4 物料周转告警 |
| 7 | `AnalyzeTrendWarningStep` | stg_stock_current + stg_sales_out | RPT 5 物料趋势告警 |
| 8 | `AnalyzeMaterialWarehouseRiskStep` | RPT 1+4+5 + stg_stock_current | RPT 6 综合风险 |
| 9 | `LinkProcurementProcessStep` | stg_purchase_req + stg_purchase_order + stg_stock_in | RPT 7 采购三表关联 |
| 10 | (build_sales_out_wide,部署期实现) | stg_sales_out | 销售宽表 |
| 11 | `AutoUpdateDimStep` | RPT 5 | dim_product_attr 同步 |
| 12 | `WriteRptTablesStep` | ctx.rpt | 7 张 RPT 表写入 DB |

## EtlContext

```python
@dataclass
class EtlContext:
    raw_data: dict[str, pd.DataFrame]  # 原始输入
    stg: dict[str, pd.DataFrame]       # 清洗后(5 张 STG)
    rpt: dict[str, pd.DataFrame]       # 聚合后(7 张 RPT)
    extras: dict[str, pd.DataFrame]    # 销售宽表
    meta: dict[str, Any]               # rules / brand_provider / current_date / engine
```

## 自定义步骤

```python
from channel_analytics.etl.types import Transformer

class MyStep(Transformer):
    name = "my_step"
    def run(self, ctx):
        # 修改 ctx in-place
        ctx.rpt["my_custom_rpt"] = ...
        return ctx

# 注入
from channel_analytics.etl.pipeline import build_default_pipeline, run_default_etl
default = build_default_pipeline(...)
default.steps.insert(7, MyStep())
```

## 防御性设计

- 每个步骤对缺失输入都做安全降级(返回 ctx,不抛)
- 列名做别名兼容(`batch_number` / `batch_no` / `batch` 都识别)
- 品牌判定用 `provider.is_self_operated(brand)`,不内嵌任何品牌字符串