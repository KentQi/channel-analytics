# examples/

教学与模板目录。

| 目录 | 内容 |
|------|------|
| `cosmetics_demo/brands.yaml` | 占位品牌数据(Brand A/B/C,严禁写真实品牌) |
| `minimal_plugin/` | ERP adapter 模板(cookiecutter 起点) |
| `notebooks/01_quickstart.ipynb` | 30 分钟上手 Jupyter notebook |

## 重要安全约束

所有示例文件都用通用代号(Brand A / MAT-001),**严禁**写原仓的真实品牌名 / 客户代号 / 厂商特定字符串。CI 会通过 `scripts/check_branding.py` 扫描,任何命中都会阻断。

```bash
python scripts/check_branding.py \
  --root ./examples \
  --keywords ~/.config/channel-analytics/branding_keywords.yaml
```