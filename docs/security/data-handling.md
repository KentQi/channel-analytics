# Data handling — backup & PII exclusion(W2-5 决策落实)

## 决策(2026-06-10 经用户授权)

| 场景 | 决策 |
|------|------|
| 75MB 客户数据 SQL dump(`backup/`) | **新仓不出现,原仓历史不动** |
| `etl_data/*.xlsx` 客户采购数据 | **新仓不出现** |
| `uploads/<user>/` 用户上传文件 | **新仓不出现** |
| `logs/*.log` 行为日志 | **新仓不出现** |
| 任何 `*.db` / `*.sqlite` / `*.sql` | **新仓不出现** |

## .gitignore 已拦截路径

参见仓库根 `.gitignore`,以下条目已生效:

```gitignore
data/
uploads/
etl_data/
logs/
*.log
*.db
*.sqlite
*.sqlite3
*.db.backup_*
*.sql
backup/
backups/
```

## CI 防护

- **W7 末** 在 `.github/workflows/ci.yml` 增加 "secret-scan" step:
  - `gitleaks detect --no-git --source .` (用本仓 `.gitleaks.toml`)
  - `python scripts/check_branding.py --root . --keywords ~/.config/channel-analytics/branding_keywords.yaml` (CI secret 注入)
  - `python scripts/detect_pii.py --root ./data --root ./uploads --root ./logs` (如果有本地测试数据)
- 三项全 0 命中才能 merge

## 测试夹具例外

`tests/fixtures/` 下可以有"占位/合成"的 PII 数据(用于单测),但:
- 路径必须在 `tests/fixtures/` 之内,且 git tracked
- 文件名带 `.fixture.` 后缀(被 `check_branding.py` 默认忽略)
- 仅含合成数据(明显是 Lorem Ipsum / 555-01-XXXX / +1-555-XXXX),不含真实 PII
- **W4 接入** 后,fixtures 工厂用 `factory-boy.fuzzy` 生成,无任何真实凭据

## 原仓历史

- 本仓**完全不引用**原仓的 `backup/`
- 原仓 `.gitignore` 已包含 `backup/`,本地历史保留不动
- 任何"删除原仓 backup"的工作 → 不在本仓范围
