# 源项目 vs 开源项目 完整对比

**生成日期**: 2026-06-11  
**源项目**: 私有仓库(已脱敏,路径不公开)  
**开源项目**: channel-analytics (Apache-2.0)

---

## 一、总览

| 指标 | 源项目 | 开源项目 | 差异 |
|------|--------|---------|------|
| 源文件总数 | 302 | 309 | +7 |
| Python 总行数 | 20,655 | 29,975 | +9,320 (+45%) |
| 前端(Vue/JS/TS/CSS) | 24,463 | 24,554 | +91 (~0%) |
| CSV 数据文件 | 2 个(真实 xlsx) | 10 个(mock CSV) | +8 |
| DB 文件 | 1 个(真实 .db) | 0 | -1(运行时生成) |
| 品牌泄露 | 源项目:含 12 个真实品牌 | 开源项目:0 泄露 | 完全脱敏 |

---

## 二、后端 Python 逐模块对比

### 2.1 核心应用(`app/`)

| 模块 | 源项目 | 开源项目 | 差异 | 说明 |
|------|--------|---------|------|------|
| `app/routers/`(17 个) | 4,175 行 | 4,241 行 | +66 | 新增 `routers/stub.py`(占位路由) |
| `app/services/`(16 个) | 11,930 行 | 11,932 行 | +2 | 完全一致(仅脱敏替换) |
| `app/utils/`(8 个) | 1,329 行 | 1,329 行 | 0 | 完全一致 |
| `app/models/`(4 个) | 395 行 | 395 行 | 0 | 完全一致 |
| `app/config.py` | 139 行 | 139 行 | 0 | 完全一致 |
| `app/database.py` | 123 行 | 186 行 | +63 | 新增 SQLite 降级逻辑 |
| `app/dependencies.py` | 160 行 | 160 行 | 0 | 完全一致 |
| `app/limiter.py` | 4 行 | 4 行 | 0 | 完全一致 |
| `app/main.py` | 311 行 | 311 行 | 0 | 完全一致(脱敏替换内网 IP) |
| **小计** | **18,666** | **18,797** | **+131** | |

### 2.2 开源项目独有模块(源项目没有)

| 模块 | 行数 | 说明 |
|------|------|------|
| `channel_analytics/etl/`(11 文件) | 2,207 | ETL pipeline + 12 步 + providers |
| `channel_analytics/db/models/`(5 文件) | 458 | SQLAlchemy ORM(17 张表) |
| `channel_analytics/auth/`(1 文件) | 225 | 三维权限框架 |
| `channel_analytics/rpa/`(6 文件) | 748 | RPA 框架(ErpAdapter 抽象) |
| `channel_analytics/reports/`(1 文件) | 123 | 报表注册中心 |
| `channel_analytics/scheduler/`(1 文件) | 122 | 调度器 facade |
| `channel_analytics/api/routers/`(5 文件) | 598 | W3-W7 API routers |
| `channel_analytics/data/`(2 文件) | 943 | Mock data fixtures + seed 脚本 |
| `tests/unit/`(20 文件) | 3,177 | 单元测试(314 个) |
| `tests/integration/` | 0 | 空目录(预留) |
| `tests/plugins/` | 0 | 空目录(预留) |
| `docs/`(18 文件) | 1,058 | mkdocs 文档 |
| `deploy/`(5 文件) | 263 | Docker + 启动/备份脚本 |
| `data/fixtures/`(10 CSV) | 7,105 行数据 | Mock 数据(11 CSV 文件) |
| **独有总计** | **8,601 行代码 + 7,105 行数据** | |

### 2.3 源项目独有的(开源项目没有)

| 文件 | 说明 | 为什么不移植 |
|------|------|-------------|
| `backend/migrations/*.sql` | 数据库迁移 SQL | 改用 Alembic 管理 |
| `backend/scripts/dba_optimization_v2.2.12.sql` | DBA 优化脚本 | 生产运维脚本,非业务逻辑 |
| `USER_MANUAL.html` | 92KB 用户手册 | 替换为 mkdocs 文档 |
| `data_analysis.db` | SQLite 数据库(含真实数据) | 不进入开源仓 |
| `scripts/automation/` 厂商配置 | 厂商配置(含真实账号) | 不进入开源仓 |
| 厂商专用下载器 | ERP 厂商专用 | 替换为通用 adapter |
| `deploy/backups/*.sql.gz` | 数据库备份(含真实数据) | 不进入开源仓 |
| `etl_data/*.xlsx` | RPA 下载的真实 Excel | 替换为 mock CSV |
| `.env` | 真实环境变量 | 在 `.gitignore` |

---

## 三、前端逐模块对比

| 模块 | 源项目 | 开源项目 | 差异 | 说明 |
|------|--------|---------|------|------|
| `views/`(49 个 .vue) | 18,046 行 | 18,046 行 | 0 | 完全一致(脱敏替换) |
| `components/`(12 个 .vue) | 3,663 行 | 3,663 行 | 0 | 完全一致 |
| `api/`(16 个 .js) | 867 行 | 867 行 | 0 | 完全一致 |
| `stores/`(6 个 .js) | 1,472 行 | 1,472 行 | 0 | 完全一致 |
| `router/index.js` | 241 行 | 241 行 | 0 | 完全一致 |
| `composables/useResponsive.js` | 80 行 | 80 行 | 0 | 完全一致 |
| `styles/responsive.css` | 151 行 | 151 行 | 0 | 完全一致 |
| `App.vue` | 1,345 行 | 1,345 行 | 0 | 完全一致 |
| `main.js` | — | 19 行 | +19 | 新增 |
| **小计** | **24,463** | **24,554** | **+91** | |

---

## 四、测试对比

| 模块 | 源项目 | 开源项目 | 差异 |
|------|--------|---------|------|
| `backend/tests/`(10 文件) | 1,054 行 | 1,055 行 | +1(脱敏修复) |
| `tests/unit/`(20 文件) | — | 3,177 行 | +3,177(开源项目独有) |
| **测试总计** | 1,054 行 | 4,232 行 | **+3,178** |

---

## 五、安全对比

| 检查项 | 源项目 | 开源项目 |
|--------|--------|---------|
| 12 个真实自营品牌名 | 硬编码 | 已脱敏为占位 |
| ERP 厂商 | 真实 URL + 产品代号 | 替换为通用占位 |
| 内网 IP | 硬编码真实 IP | 替换为本地回环 |
| 真实密码 / 用户名 | 硬编码 | 占位 + 公开测试值 |
| 真实数据 | 真实 xlsx + 备份 | 替换为 mock CSV |
| 真实路径 | 真实用户目录 | 动态检测或占位 |
| LLM API key | 配置从 env 读 | 配置从 env 读 |
| `.env` secrets | 含真实值 | 已在 `.gitignore` |

---

## 六、目录结构对比(简化)

```
源项目(私有)                          开源项目(Apache-2.0)
backend/                              channel_analytics/
├── app/ (完整业务)                   ├── app/          ← 完整平移(脱敏)
│   ├── routers/ services/ utils/     │   ├── routers/ services/ utils/
│   └── main.py                        │   ├── etl/ db/ auth/ rpa/   ← 新增
├── tests/                            │   └── api/ reports/ scheduler/ data/
├── etl_data/ (真实 xlsx)            ├── web/ (完整前端平移)
└── .env (真实)                      ├── tests/unit/integration/original/
                                      ├── data/fixtures/ (mock CSV)
frontend/                            ├── docs/ (mkdocs)
└── src/                              ├── deploy/ (Docker + 脚本)
    ├── views/ components/ api/       ├── .env (占位, .gitignore)
    └── stores/                       ├── demo.py (一键启动)
                                      └── reports/ (CI + 专家评估)
```

---

## 七、总结

### 移植了什么

| 类别 | 源代码 | 说明 |
|------|--------|------|
| 后端 17 个 router + 16 个 service + 8 个 util | **18,666 行** | 100% 完整保留(脱敏替换) |
| 前端 49 个 view + 12 个 component + 16 个 api + 6 个 store | **24,463 行** | 100% 完整保留(脱敏替换) |
| 测试 10 个文件 | **1,055 行** | 100% 完整保留(脱敏替换) |
| **移植小计** | **44,184 行** | |

### 新增了什么

| 类别 | 行数 | 说明 |
|------|------|------|
| ETL pipeline + steps + providers | 2,207 | 可扩展 ETL 框架 |
| ORM models (17 张表) | 458 | SQLAlchemy 2.x 风格 |
| Auth + RPA + Reports + Scheduler | 1,118 | 框架/抽象层 |
| Mock data fixtures + seed | 943 | 脱敏数据 + 一键灌入 |
| 单元测试 | 3,177 | 314 个测试用例 |
| 文档 | 1,058 | mkdocs 站 |
| 部署 | 263 | Docker + 脚本 |
| **新增小计** | **8,601 行代码 + 7,105 行数据** | |

### 移除了什么

| 类别 | 说明 |
|------|------|
| 12 个真实品牌名 | 替换为占位 |
| ERP 厂商 URL/字符串 | 替换为通用占位 |
| 真实内网 IP | 替换为本地回环 |
| 真实密码/用户名 | 调试脚本已删除,测试改为公开值 |
| 真实数据文件 | 替换为 mock CSV |
| 数据库备份 | 不进入开源仓 |
| 真实路径 | 改为动态检测或占位 |
| 全部 ERP 厂商字符串 | 替换为通用术语 |

### 安全检查结果

| 检查项 | 命中数 |
|--------|--------|
| 真实品牌名 | 0 |
| ERP 厂商字符串 | 0 |
| 内网 IP | 0 |
| 真实密码 | 0 |
| 真实用户名 | 0 |
| 真实数据文件 | 0 |
| 真实路径 | 0 |
| 真实 secret | 0 |

---

**结论**: 开源项目完整保留了源项目 100% 的业务代码(44,184 行),新增了 8,601 行框架/测试/文档/部署代码,总计 52,785 行。所有敏感信息已完全清除。
