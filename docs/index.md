# channel-analytics

通用渠道分析平台 — ETL + 报表 + RPA 框架,Apache-2.0 开源。

## 30 秒电梯

```bash
pip install channel-analytics
channel-analytics init-secrets
alembic upgrade head
uvicorn channel_analytics.api.app:app --reload
```

打开 http://localhost:8000/docs 看 API 文档,http://localhost:8000/healthz 看存活探针。

## 核心特性

- **ETL Pipeline**:12 步骤,可插拔(brand provider / business rules)
- **7 张 RPT 表**:效期 / 周转 / 趋势 / 自营集中度 / 综合风险 / 采购关联
- **RPA 框架**:`ErpAdapter` 抽象,支持任意 Web ERP 接入
- **三维权限**:role → modules / sales_tabs / regions
- **SQLAlchemy 2.x**:sqlite / MySQL / Postgres 全部支持
- **Alembic 迁移**:17 张表 schema 演进

## 4 个 badge

| | |
|--|--|
| CI | ![CI](https://img.shields.io/badge/CI-passing-brightgreen) |
| License | ![License](https://img.shields.io/badge/License-Apache_2.0-blue) |
| Python | ![Python](https://img.shields.io/badge/Python-3.11%2B-blue) |
| Status | ![Status](https://img.shields.io/badge/Status-Alpha-yellow) |

## 下一步

- [安装指南](getting-started/install.md) — 5 分钟装好
- [架构总览](architecture/overview.md) — 理解系统分层
- [写 ERP adapter](how-to/write-erp-adapter.md) — 接入你的 ERP

## 安全

本仓库**不**包含任何真实品牌名 / 客户代号 / 凭据。详见 [SECURITY.md](../SECURITY.md)。

## 许可证

Apache License 2.0 — 见 [LICENSE](../LICENSE)。