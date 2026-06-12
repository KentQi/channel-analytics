# channel-analytics

> 多渠道零售数据分析平台 - 销售/库存/复购/告警/报表一体化的开源 ERP

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4-brightgreen.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com/)

---

## ✨ 这是什么

`channel-analytics` 是一个**面向多渠道零售(母婴/化妆品/快消)的数据分析平台**,对接企业 ERP 抽取销售/库存/采购数据,自动生成 7 张分析报表(销售看板、库存预警、复购分析、自营品集中度、效期管理等)。

**适用于**:

- 🔌 需要对接多种 ERP 的中大型零售企业
- 📊 希望从销售/库存数据中自动发现业务风险
- 🤖 有自动化定时数据采集需求(RPA + Playwright)
- 🏢 希望基于开源底座二次开发,数据掌握在自己手中

**核心能力**:

| 模块 | 能力 |
|------|------|
| **ETL 管道** | 12 步自动清洗 + 7 张 RPT 报表 + 17 张表 |
| **销售分析** | 大区/客户/渠道维度,宽表查询 + ABC 分类 |
| **库存分析** | 效期预警 / 周转天数 / 趋势预警 / 仓储风险 |
| **返单分析** | 客户生命周期 / 流失预警 / 新品追踪 |
| **三维权限** | 模块 / 销售标签 / 大区(基于角色) |
| **RPA 自动化** | Playwright + APScheduler 定时抓取 ERP |
| **自定义报表** | 用户可配置查询,SQL 可视化 |
| **告警通知** | 规则引擎 + 历史追溯 + 邮件通知 |

---

## 🚀 30 秒快速开始

> **前置要求**: Python 3.11+ 和 pip(可选: Node.js 18+ 用于前端)

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/channel-analytics.git
cd channel-analytics

# 2. 一键启动(自动安装依赖 + 灌入 mock 数据 + 启动 API)
python demo.py

# 3. 浏览器打开
#    API 文档: http://127.0.0.1:8602/api/docs
#    登录: admin / admin123
```

看到 API 文档 + 销售宽表返回 10 行 mock 数据 = 成功 ✓

> 💡 **零依赖启动**:`demo.py` 自动检测数据库,如果本机无 MySQL 则降级到 SQLite(数据存 `data/demo.db`),无需任何外部依赖。

---

## 🏗️ 项目结构

```
channel-analytics/
├── channel_analytics/            # 核心应用包
│   ├── app/                      # 完整业务代码(从源仓脱敏平移,20,000+ 行)
│   │   ├── routers/ (17)         # FastAPI 路由层
│   │   ├── services/ (16)        # 业务服务层
│   │   ├── utils/ (8)            # 工具
│   │   ├── models/ (4)           # Pydantic schemas
│   │   ├── config/               # pydantic-settings 配置
│   │   ├── database.py           # 多后端 DB 引擎(MySQL/SQLite/Postgres)
│   │   └── main.py               # FastAPI 应用入口
│   ├── etl/                      # ETL 框架(12 步 pipeline)
│   ├── db/                       # SQLAlchemy ORM(17 张表)
│   ├── auth/                     # 三维权限框架
│   ├── rpa/                      # RPA 框架(ErpAdapter 抽象)
│   ├── reports/                  # 报表注册中心
│   ├── scheduler/                # APScheduler 任务调度
│   ├── api/                      # 兼容层 API(预留扩展点)
│   ├── data/
│   │   ├── fixtures.py           # Mock 数据生成器
│   │   └── seed.py               # raw SQL 灌入脚本
│   └── cli.py
├── web/                          # 前端 (Vue 3 + Vite + TS)
│   ├── src/
│   │   ├── views/ (49)           # 业务页面
│   │   ├── components/ (12)      # 公共组件
│   │   ├── api/ (16)             # API 封装
│   │   ├── stores/ (5)           # Pinia 状态
│   │   ├── router/               # 路由
│   │   └── main.js
│   └── package.json
├── tests/                        # 测试
│   ├── unit/ (314 tests)         # 单元测试
│   ├── integration/              # 集成测试
│   ├── original/                 # 源仓测试(需 MySQL)
│   └── plugins/                  # 插件测试
├── data/
│   └── fixtures/                 # 11 个 mock CSV(7,105 行)
├── docs/                         # mkdocs 文档
├── deploy/                       # Docker + 部署脚本
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── scripts/                  # start/backup/restore
├── alembic/                      # 数据库迁移
├── reports/                      # CI 扫描报告 + 专家评估
├── .github/
│   └── workflows/ci.yml          # CI: test + gitleaks + branding + pii
└── demo.py                       # 一键启动入口
```

---

## 📦 安装(生产部署)

### 方式一:Docker

```bash
# 1. 启动 MySQL + 应用
cd deploy/docker
docker compose up -d

# 2. 初始化数据库
docker exec channel-analytics python -m channel_analytics.data.seed
```

### 方式二:本地 Python

```bash
# 1. 安装依赖
pip install -e ".[mysql,postgres]"

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 MySQL 连接串 / ERP 凭据

# 3. 跑数据库迁移
alembic upgrade head

# 4. 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## ⚙️ 配置

所有配置通过环境变量管理(`.env` 文件):

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `DATABASE_URL` | 推荐 | SQLite (demo) | `mysql+pymysql://user:pwd@host:3306/db` |
| `SESSION_SECRET` | 生产必填 | 64字符随机 | JWT / Session 签名 |
| `JWT_SECRET` | 生产必填 | 64字符随机 | JWT 签名 |
| `RPA_ERP_URL` | 可选 | `https://erp.example.com` | RPA 目标 ERP 入口 |
| `RPA_DOWNLOAD_DIR` | 可选 | `./rpa_downloads` | ERP 文件下载目录 |
| `SMTP_*` | 可选 | 空 | 告警邮件通知 |

> ⚠️ 生产环境务必设置 `SESSION_SECRET` 和 `JWT_SECRET`,否则首次启动会被 `RefuseToStart` 异常拦截。

---

## 🧪 测试

```bash
# 单元测试 (314 个,无需 MySQL)
pytest tests/unit -v

# 全部测试(需 MySQL)
pytest tests/

# 覆盖率
pytest tests/ --cov=channel_analytics --cov-report=html
```

---

## 🛠️ 扩展开发

### 接入你的 ERP

实现 `ErpAdapter` 接口,放入你的项目:

```python
from channel_analytics.rpa.base import ErpAdapter

class YourErpAdapter(ErpAdapter):
    async def login(self, username, password, captcha=None): ...
    async def navigate_to_module(self, module_name): ...
    async def set_date_filter(self, start, end): ...
    async def search(self): ...
    async def export(self, save_path): ...
```

通过 entry_points 注册到你的项目,自动被发现。

### 添加自定义报表

```python
from channel_analytics.reports import BaseReport, register_report

class MyReport(BaseReport):
    name = "my_report"
    description = "我的自定义报表"
    sql = "SELECT * FROM stg_sales_out WHERE ..."
    columns = ["doc_no", "customer", "tax_included_amount"]

register_report(MyReport)
```

### 添加自营品牌白名单

```yaml
# config/brands.yaml
brands:
  - "你的品牌1"
  - "你的品牌2"
```

实现 `BrandWhitelistProvider` 接口或使用默认的 YAML provider。

---

## 🤝 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

简短版:

1. Fork → 创建 feature 分支 (`git checkout -b feat/xxx`)
2. 提交 (`git commit -m 'feat: add xxx'`)
3. 推送 (`git push origin feat/xxx`)
4. 创建 PR,所有 CI 必须通过

---

## 🔒 安全

- **漏洞披露**: 参见 [SECURITY.md](SECURITY.md)
- **报告安全漏洞**: `security@your-org.example.com`
- **凭据管理**: 永远不要提交真实凭据到 git,使用 `.env` 文件

---

## 📜 许可证

[Apache License 2.0](LICENSE)

---

## 🙏 致谢

本项目脱敏于真实业务场景，多年业务沉淀恰逢vibe coing正当时:

- 17 个 FastAPI 路由模块
- 16 个业务服务层
- 8 个工具模块
- 5 张 STG / 7 张 RPT / 5 张 DIM 数据库表
- 12 步 ETL pipeline
- 49 个 Vue 3 业务页面
- 12 个公共组件
- 314 个单元测试
- 17 篇 mkdocs 文档

---

## 📞 联系方式
kirroyu@126.com

- **问题反馈**: [GitHub Issues](https://github.com/your-org/channel-analytics/issues)
- **功能请求**: [GitHub Discussions](https://github.com/your-org/channel-analytics/discussions)
- **安全问题**: `security@your-org.example.com`(参见 [SECURITY.md](SECURITY.md))

---

**⭐ 如果这个项目对你有帮助,请给个 Star!**
