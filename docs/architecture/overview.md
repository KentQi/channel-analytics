# 系统总览

channel-analytics 是 4 层架构:

```
┌──────────────────────────────────────┐
│  Web SPA (前端 Vue3 + Vite)         │  ← web/ (开源仓可选)
└──────────────────────────────────────┘
                 │ HTTP / JSON
                 ▼
┌──────────────────────────────────────┐
│  FastAPI API (4 routers)            │  ← api/
│    /auth /rpa /etl /reports         │
└──────────────────────────────────────┘
                 │ SQLAlchemy
                 ▼
┌──────────────────────────────────────┐
│  ETL Pipeline (12 steps)            │  ← etl/
│    cleaning → analyze → write        │
└──────────────────────────────────────┘
                 │ SQLAlchemy ORM
                 ▼
┌──────────────────────────────────────┐
│  Database (sqlite/MySQL/Postgres)   │  ← db/
│    5 STG + 7 RPT + 5 dim            │
└──────────────────────────────────────┘
```

## 分层职责

| 层 | 入口 | 职责 |
|----|------|------|
| Web SPA | web/ | UI(开源仓不强制,部署方可替换) |
| FastAPI | api/ | REST API + JWT 验证 + 路由分发 |
| ETL Pipeline | etl/ | 数据清洗 / 聚合 / 7 张 RPT 产出 |
| Scheduler | scheduler/ | APScheduler 调度(ETL + RPA) |
| RPA | rpa/ | 通用浏览器自动化框架 |
| Reports | reports/ | 报表注册中心 + 元数据 |
| Auth | auth/ | 三维权限(role → modules/sales_tabs/regions) |
| DB | db/ | ORM models + Alembic + dim_sync hooks |
| Config | config/ | pydantic-settings + SecretStr |

## 数据流

1. **STG(清洗后)**:Pipeline 第 1-2 步把原始 Excel/CSV 写到 5 张 STG 表
2. **RPT(聚合)**:Pipeline 第 3-9 步从 STG 聚合,产出 7 张 RPT
3. **DB 写入**:Pipeline 第 11-12 步同步 dim + 写 RPT 到 DB
4. **API 查询**:API `/reports/{name}` 查 RPT,前端渲染

## 关键约束

- **品牌白名单从 provider 注入**:默认 `ExampleMinimalProvider` 返回空集;真实白名单走 `DbBrandWhitelistProvider` 或 entry_points
- **业务阈值从 YAML 注入**:`business_rules.yaml` 改一行生效,无需改代码
- **RPA adapter 通过 entry_points**:主仓只放 `ExampleMinimalAdapter` 模板,具体厂商走 contrib 仓