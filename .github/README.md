# GitHub Actions

`.github/workflows/ci.yml` 包含 4 个 jobs:

| Job | 工具 | 阻断条件 |
|-----|------|----------|
| test | pytest (矩阵 Python 3.11/3.12) | 任一测试失败 |
| secret-scan | gitleaks (.gitleaks.toml) | 任何 secret 命中 |
| branding-scan | check_branding.py (空 example) | 0 命中或非零退出 |
| pii-scan | detect_pii.py | 0 命中或非零退出 |

`ci-gate` job 等所有 4 个通过才输出成功,触发 merge 保护。

## 真实品牌词条如何接入 CI

`branding_keywords.example.yaml` 在开源仓里**是空的**(对应 PLAN.md §6 P0)。
真实词条通过 GitHub Secret 注入:
- 在 repo settings 添加 secret `BRANDING_KEYWORDS_PATH` 指向仓库外路径(不便)
- 或 fork 私有 repo,替换 `branding_keywords.example.yaml` 后跑(开源仓不能这么做)

实务方案:**CI 阶段只跑空模板验证工具能跑通**;真实词条扫描由部署方在私有环境跑。

## 本地模拟 CI

```bash
# 一行复刻 CI 全套
pip install -e ".[dev]" && \
  ruff check . && \
  pytest -q && \
  gitleaks detect --config .gitleaks.toml --no-git --source . && \
  python scripts/check_branding.py --root . --keywords scripts/branding_keywords.example.yaml && \
  python scripts/detect_pii.py --root ./
```

5 项全 0 命中 = CI 绿。