# 变更日志

本项目所有重要变更都记录在此。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 8 个专家维度评估报告(PM/ARCH/FE/BE/QA/OP/SEC/DEVOPS)
- 2 轮共 18 个维度脱敏扫描,0 真实泄露
- 一键启动脚本 `demo.py`
- 7,105 行 mock 数据(11 个 CSV 文件)
- 314 个单元测试
- Docker 多阶段构建(非 root 用户)
- 完整的 mkdocs 文档站

### Fixed
- 路由守卫首次访问崩溃(`from` undefined)
- filter store `resetSales` 引用未定义变量
- `vite.config.ts` 和 `vite.config.js` 双配置冲突
- `api/index.ts` 和 `api/index.js` 双入口冲突
- Dockerfile 容器以 root 启动
- `backup.sh` / `restore.sh` URL 解析错误
- 6 处 SQL 注入(f-string 拼 SQL)
- 12 个真实品牌名泄露
- 真实 ERP 厂商 URL (`c2.yonyoucloud.com`) 泄露
- 真实内网 IP `192.168.110.222` 泄露
- 真实调试脚本(含 `Unny12345.` 密码)被删除
- 原仓路径 `C:\Projects\Data_Analysis` 泄露

## [0.1.0] - 2026-06-11

### Added
- 从私有仓库 `C:\Projects\Data_Analysis` 脱敏后开源
- 完整后端(FastAPI + SQLAlchemy 2.x + APScheduler)
  - 17 个 routers
  - 16 个 services
  - 8 个 utils
  - 4 个 Pydantic schemas
  - 17 张表(5 STG + 7 RPT + 5 DIM)
  - 12 步 ETL pipeline
  - 三维权限(模块/销售标签/区域)
  - RPA 框架(ErpAdapter 抽象)
- 完整前端(Vue 3 + Vite + TS + Pinia)
  - 49 个 views
  - 12 个公共组件
  - 16 个 API 封装
  - 5 个 Pinia stores
- 数据库迁移(Alembic)
- Docker 部署(多阶段构建)
- 部署脚本(start / backup / restore)
- CI 流水线(test + gitleaks + branding + pii)
- 完整文档(mkdocs 17 篇)
- Mock 数据 + 一键灌入

### Security
- Apache-2.0 开源协议
- 12 个真实品牌名 → 替换为 `Brand A` - `Brand L`
- ERP 厂商字符串 → 替换为 `erp.example.com`
- 真实凭据 → 已从仓库删除
- 真实业务数据 → 替换为 mock CSV
- 2 轮共 18 个维度深度脱敏扫描

---

**版本说明**:
- 主版本号: 不兼容的 API 变更
- 次版本号: 向下兼容的功能新增
- 修订号: 向下兼容的问题修正
