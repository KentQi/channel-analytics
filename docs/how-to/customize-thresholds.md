# 自定义业务规则

通过 `business_rules.yaml` 改阈值,**无需改代码**。

## 字段说明

```yaml
# 批次号清洗:原值匹配列表内任一 → 视为"无效"
batch_clean_rules: []

# 效期清洗
expiry_clean_rules: []

# 周转周期(天)
turnover_cycle_days: 90

# 趋势周期(天)
trend_cycle_days: 30

# 销售趋势判断
trend:
  ratio_threshold: 3.0   # 期末/期初 >= 3 视为"突增"
  min_change: 1.0        # 绝对变化 < 1 时不报警

# 周转档位
turnover_status_bands:
  - { upper: 30,  label: "周转健康(<30天)" }
  - { upper: 60,  label: "周转正常(30-60天)" }
  - { upper: 90,  label: "周转偏低(60-90天)" }
  - { upper: .inf, label: "周转高(>90天)" }

# 周转计算:无销售/销售<=0 时返回 sentinel
inventory_days_sentinel: 999.0

# 周转告警阈值
turnover_warning_low: 15.0   # < 此值 → 预警(快销)
turnover_warning_high: 60.0  # > 此值 → 预警(积压)
```

## 在 Python 中加载

```python
from channel_analytics.etl.rules import BusinessRules

rules = BusinessRules.from_yaml("business_rules.yaml")
print(rules.turnover_cycle_days)  # 90(默认)
```

或通过 env / settings:

```bash
# .env
BUSINESS_RULES_PATH=./business_rules.yaml
```

```python
from channel_analytics.config import get_settings
from channel_analytics.etl.rules import load_rules_for_settings

settings = get_settings()
rules = load_rules_for_settings(settings.business_rules_path)
```

## 在 ETL Pipeline 中使用

```python
ctx = run_default_etl(
    raw_data,
    brand_provider_dotted="...",
    business_rules_path="./business_rules.yaml",
)
```

## 部分覆盖

`BusinessRules.from_dict({...})` 支持只传部分字段,缺失字段用默认值:

```python
rules = BusinessRules.from_dict({"turnover_cycle_days": 60})
print(rules.trend.ratio_threshold)  # 3.0(默认)
print(rules.turnover_cycle_days)    # 60(覆盖)
```

## 边界用例提醒

- `turnover_cycle_days <= 0` 会触发防御性返回 sentinel(999.0)
- `inventory_days_sentinel` 应该大于所有档位 upper,否则 sentinel 被错分档位
- `TurnoverBand.contains()` 用 `[0, upper)`,upper 必须正数(末段用 `inf`)