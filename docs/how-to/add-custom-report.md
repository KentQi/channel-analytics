# 添加自定义报表

通过 `reports.registry` 装饰器注入。

## 默认 7 张 RPT

主仓已注册(对齐 `RPT_TABLES`):
- `rpt_expiry_warning`
- `rpt_expiry_turnover`
- `rpt_self_operated_concentration`
- `rpt_turnover_warning`
- `rpt_trend_warning`
- `rpt_warehouse_risk`
- `rpt_procurement_linked`

## 添加自定义报表

```python
from channel_analytics.reports import BaseReport, ReportMeta, registry

@registry.register()
class TopMoversReport(BaseReport):
    meta = ReportMeta(
        name="rpt_top_movers",
        description="Top 10 销量增长物料",
        columns=["material_code", "material_name", "growth_rate"],
    )

    def generate(self, ctx):
        # 从 ctx.rpt['rpt_trend_warning'] 算
        trend = ctx.rpt.get("rpt_trend_warning")
        if trend is None or trend.empty:
            return None
        return trend.nlargest(10, "sales_90d")[["material_code", "material_name"]]
```

## API 暴露

注册后,`/reports` GET 自动列出:

```bash
curl http://localhost:8000/reports -H "Authorization: Bearer $TOKEN"
```

返回:

```json
[
    {"name": "rpt_top_movers", "description": "Top 10 销量增长物料", "columns": [...]},
    ...
]
```

## 写库

如果同时想写库,在 ReportMeta 加 `db_table`,然后扩展 `WriteRptTablesStep` 的 `RPT_TABLES` tuple。

## 单元测试

```python
from channel_analytics.reports import registry

def test_top_movers_registered():
    assert "rpt_top_movers" in registry.list_names()

def test_top_movers_generate():
    cls = registry.get("rpt_top_movers")
    ctx = ...  # mock EtlContext with rpt_trend_warning
    result = cls().generate(ctx)
    assert len(result) <= 10
```