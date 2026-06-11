# 计划：开新仓库做 channel-analytics 开源版

## Context

要把当前私有项目（Vue3 + FastAPI + MySQL + Playwright RPA，4.3 万行；以下称"原仓库"）**从 0 重新做一个开源版本**放到新仓库，**不会直接开源现有项目**——原因：原仓库含品牌关键字、`.env` 中明文 JWT 密钥、75MB 客户数据库 dump 已纳入 git tracking，开源等于事故。

**用户决策**：
- 范围：**通用核心 + RPA 通用框架**（ETL + 权限 + 报表 + 前端 + **RPA 调度器/Worker/Adapter 抽象**），**不包含**具体 ERP 厂商的选择器实现
- 许可证：Apache-2.0
- 命名：channel-analytics 风格（具体名 W1 末抢注 PyPI 时再定）
- 时间：2-3 个月产品级，8 周时间表

**核心思路**：新仓库不是脱敏版，而是**通用化重构版**——把业务硬编码（品牌白名单、效期、周转阈值）抽成插件 + YAML；把 RPA 拆成**框架（调度器/Worker/Adapter 接口）** 与 **实现（具体 ERP 选择器）** 两层。各 ERP 厂商接入走**插件仓 `channel-analytics-contrib/`**，主仓只保留一个**最简示例 adapter**（不绑定任何厂商）作为模板。

**RPA 通用化的关键边界（避免误带入任何厂商特定信息）**：
- ✅ 保留：浏览器生命周期、流程调度、子进程隔离、僵尸清理、邮件通知、APScheduler 封装、openpyxl 损坏样式补丁、异常体系
- ❌ 不保留：任何厂商特定的 `MODULE_CONFIG` 字典、硬编码 DOM ID、iframe 选择器、配置文件命名、错误消息
- 🎁 接口：`ErpAdapter` 抽象基类（5 个钩子：`login` / `navigate_to_module` / `set_date_filter` / `search` / `export`），通过 Python `entry_points` 自动发现插件

---

## 1. 新仓库目标结构

```
channel-analytics/
├── README.md / LICENSE (Apache-2.0) / NOTICE / CHANGELOG.md
├── CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md
├── pyproject.toml / Makefile / docker-compose.yml / .env.example
│
├── channel_analytics/                # 核心 Python 包（pip install -e .）
│   ├── config/                       # pydantic-settings + business_rules.yaml
│   ├── etl/
│   │   ├── pipeline.py / cleaners.py / classifiers.py
│   │   ├── field_mapping.py          # 从原 backend 平移（90% 通用）
│   │   ├── plugins/                  # ⭐ BrandWhitelistProvider 抽象 + 3 个实现
│   │   └── rpt/                      # 6 个 RPT 表生成器
│   ├── db/                           # engine / session / models / alembic
│   ├── auth/permissions.py           # 三维权限（module/sales_tab/region）
│   ├── reports/                      # 通用报表框架 + 注册中心
│   ├── scheduler/                    # APScheduler 封装 + 子进程 worker（80% 通用）
│   ├── rpa/                          # ⭐ RPA 通用框架（与 ERP 完全解耦）
│   │   ├── base.py                   # ErpAdapter 抽象基类（login/navigate/export 三个钩子）
│   │   ├── runner.py                 # Playwright 通用流程引擎（启动浏览器/重试/超时/下载）
│   │   ├── worker.py                 # 独立子进程入口（隔离 asyncio）
│   │   ├── scheduler.py              # APScheduler 任务调度 + 僵尸清理 + 邮件通知
│   │   ├── exceptions.py             # LoginError/NavigateError/ExportError
│   │   ├── excel_compat.py           # openpyxl 损坏样式补丁（通用工具，不绑定某 ERP 厂商）
│   │   └── adapters/                 # 具体 ERP 实现（不绑定某 ERP）
│   │       └── README.md             # 指向 contrib 仓，本仓只放 1 个 minimal 示例
│   ├── api/routers/
│   └── cli.py                        # `channel-analytics etl run` / `rpa run`
│
├── web/                              # Vue3 前端（品牌痕迹全清）
│
├── examples/                         # ⭐ 模板与示例
│   ├── cosmetics_demo/               # 化妆品行业示例数据（品牌名改为 Brand A/B）
│   ├── minimal_plugin/               # ERP adapter 模板（cookiecutter）
│   └── notebooks/01_quickstart.ipynb
│
├── deploy/docker/ + deploy/scripts/  # Dockerfile / start.sh / backup.sh
├── docs/                             # mkdocs（getting-started / architecture / how-to / reference / decisions）
├── tests/{unit,integration,plugins}/
├── scripts/
│   ├── scan_secrets.sh               # gitleaks / trufflehog
│   ├── detect_pii.py
│   └── check_branding.py             # ⭐ CI 必跑，扫描原仓库品牌痕迹（关键词列表维护在脚本内部）
│
└── .github/workflows/{ci,docs,release,codeql}.yml
       + ISSUE_TEMPLATE/{bug,feature,adapter_integration}.md
       + .gitleaks.toml               # 加严
```

---

## 2. 业务通用化重构（3 处核心改造）

### 2.1 品牌白名单（原 `etl_service.py:27-31` + `:184-194`）

**方案**：插件接口 + DB/File/Env 三种 Provider，通过 YAML 选择。

- `channel_analytics/etl/plugins/base.py` 定义 `BrandWhitelistProvider` 抽象
- 默认 `db_provider.py` 从 `dim_brand` 表读；备选 `file_provider.py` / `env_provider.py`
- `business_rules.yaml` 配 `provider: db|file|env`
- **删除** `ETLConfig.SELF_OPERATED_BRANDS_FALLBACK` 整段（27-31 行）

### 2.2 效期阈值（原 `etl_service.py:137-152`）

**方案**：`BusinessRules` dataclass 从 YAML 加载，`classify_expiry_status(months, rules)` 参数化。

```yaml
expiry_rules:
  - { label: "效期极佳(32+)", min_months: 32, max_months: null }   # null = +inf
  - { label: "效期优秀(28-32)", min_months: 28, max_months: 32 }
  # ... 顺序敏感，第一个匹配命中即返回
```

### 2.3 周转阈值（原 `etl_service.py:170-180`）

**方案**：同 2.2 结构。`TURNOVER_CYCLE_DAYS=90` 和 `TREND_CONFIG` 一起入 YAML 的 `cycle` 节点。

**用户使用方式**：在 `business_rules.yaml` 改一行，无需改代码。

---

## 2.4 RPA 通用化（核心新增）

**核心拆分原则**：把"流程骨架"与"具体选择器"彻底分开。开源仓只保留**框架**（任何 ERP 都能复用），不绑定任何具体厂商。

### 2.4.1 保留什么（通用框架）

| 原文件/类 | 通用程度 | 新仓中的位置 |
|---|---|---|
| `rpa_engine.py` 的 `start/close/_timeout` 浏览器生命周期 | **100% 通用** | `rpa/runner.py` |
| `rpa_engine.py` 的 `run_all(modules, ..., on_module_done)` 调度循环 | **100% 通用** | `rpa/runner.py` |
| `rpa_engine.py` 的 `set_date_filter` 时间区间选择 | **80% 通用**（接口 + 默认实现） | `rpa/runner.py` 默认实现 + `ErpAdapter.set_date_filter` 可覆写 |
| `rpa_service.py` 的 APScheduler 调度器、僵尸清理（`rpa_logs` 重入清理）、邮件通知、crontab 解析 | **90% 通用** | `rpa/scheduler.py` |
| `rpa_worker.py` 的子进程入口、stale log 清理、ETL 联动 | **80% 通用** | `rpa/worker.py`（去除某 ERP账号变量名） |
| `LoginError/NavigateError/ExportError` 异常体系 | **100% 通用** | `rpa/exceptions.py` |
| openpyxl monkey-patch（处理 None name 的 `_NamedCellStyle`） | **通用工具**（不绑定某 ERP 厂商） | `rpa/excel_compat.py`（写明：用于处理任何导出工具产生的损坏样式） |

### 2.4.2 不保留什么（具体实现）

下表列出原仓库中**会被彻底删除的具体厂商代码片段**（不作为保留代码，只是说明要被替换的位置）：

| 原仓库中的具体硬编码（要删除的） | 不带原因 |
|---|---|
| `rpa_engine.py` 内的 `MODULE_CONFIG` 字典（含业务模块中文名 + 硬编码选择器 DOM ID） | **完全绑定特定 ERP 的 DOM 结构**——任何 ERP 都不一样 |
| `rpa_engine.py` 内 `login_iframe = self.page.frame_locator('iframe[title="<vendor>_login"]')` | **特定厂商的 iframe 标题** |
| `rpa_engine.py` 内厂商收藏夹模块的 DOM 选择器 | **特定厂商的收藏夹 DOM 结构** |
| `rpa_service.py:64` 配置项命名 `rpa_<vendor>_url` / `rpa_<vendor>_username` | **厂商名直接进配置**——改为通用的 `rpa_target_url` / `rpa_username` |
| `rpa_engine.py` 类注释 `"""<某 ERP> RPA 引擎"""` | **厂商描述**——改为 `"""通用 ERP 浏览器自动化基类"""` |
| `rpa_worker.py:67` 错误消息 `"<某 ERP> 账号未配置"` | **厂商名**——改为 `"ERP 账号未配置"` |

### 2.4.3 抽象接口设计（`rpa/base.py`）

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from playwright.async_api import Page

class ErpAdapter(ABC):
    """ERP 浏览器自动化适配器抽象基类。
    用户实现这个接口即可接入任何 Web ERP（某 ERP、SAP、金蝶、Oracle EBS 等）。
    """

    @abstractmethod
    async def login(self, page: Page, url: str, username: str, password: str) -> None:
        """登录 ERP。失败抛 LoginError。"""

    @abstractmethod
    async def navigate_to_module(self, page: Page, module: str) -> None:
        """导航到指定模块（如"现存量查询"）。失败抛 NavigateError。"""

    @abstractmethod
    async def set_date_filter(self, page: Page, start_date: str, end_date: str) -> None:
        """设置日期筛选。可选覆写，默认实现不操作。"""

    @abstractmethod
    async def search(self, page: Page) -> None:
        """点击查询按钮。"""

    @abstractmethod
    async def export(self, page: Page, download_dir: str) -> str:
        """导出并下载 Excel。返回文件路径。失败抛 ExportError。"""
```

### 2.4.4 框架运行流程（`rpa/runner.py`）

```python
class RpaRunner:
    """通用 RPA 流程引擎。注入不同 ErpAdapter 即可工作。"""
    def __init__(self, adapter: ErpAdapter, download_dir: str, ...): ...

    async def start(self): ...       # 启动 Playwright 浏览器（与 adapter 无关）
    async def close(self): ...       # 关闭浏览器

    async def run_module(self, module: str, url: str, username: str, password: str,
                         start_date: str, end_date: str) -> Dict[str, Any]:
        """单模块执行：login → navigate → set_date → search → export"""
        await self.adapter.login(self.page, url, username, password)
        await self.adapter.navigate_to_module(self.page, module)
        await self.adapter.set_date_filter(self.page, start_date, end_date)
        await self.adapter.search(self.page)
        return await self.adapter.export(self.page, str(self.download_dir))

    async def run_all(self, modules, ...): ...  # 遍历 + 重试 + on_module_done 回调
```

### 2.4.5 用户使用方式

**主仓不内置任何具体 ERP**。`adapters/` 目录仅放：

```
channel_analytics/rpa/adapters/
├── README.md             # 解释如何接入自己的 ERP
└── example_minimal.py    # 一个"什么都不做"的 demo adapter（5 个钩子都抛 NotImplementedError）
```

**接入具体 ERP 厂商**的两种方式：
1. **官方 contrib 仓**：`channel-analytics-contrib/<vendor>-adapter/`（后续单独仓库，本计划不交付）
2. **自行实现**：在用户自己的项目里继承 `ErpAdapter`，写 5 个方法，pip install 后通过 `YAML` 配 `adapter: <your_package>.<your_module>:<YourAdapterClass>`

**插件发现机制**：通过 Python entry_points 自动注册（`<vendor_name>` 和 `<YourAdapterClass>` 都由用户自己命名）：
```toml
# 用户的 adapter 项目 setup.cfg
[options.entry_points]
channel_analytics.rpa_adapters =
    <vendor_name> = <your_package>.<your_module>:<YourAdapterClass>
```

### 2.4.6 文档占位（`docs/how-to/write-erp-adapter.md`）

最小可行示例（伪代码）：

```python
# 接入某 ERP：实现 5 个钩子即可
class YourAdapter(ErpAdapter):   # 用户自己命名
    async def login(self, page, url, username, password):
        await page.goto(url)
        iframe = page.frame_locator('iframe[title="erp_login_iframe"]')  # 用户自己写
        await iframe.locator('#username').fill(username)
        await iframe.locator('#password').fill(password)
        # ... 用户写自己的选择器
```

文档只讲**接口契约**（每个方法必须做什么、抛什么异常、返回什么），不提供任何厂商特定的选择器代码。

### 2.4.7 拆分后的工作占比

- `rpa_service.py`（含调度器、僵尸清理、邮件、ETL 联动）= **约 800 行 → 90% 复用**
- `rpa_worker.py`（子进程入口）= **约 340 行 → 80% 复用**（去品牌化）
- `rpa_engine.py`（引擎 + 选择器）= **约 600 行 → 拆成框架 200 行 + adapter 接口 80 行 + 0 行具体实现**
- 新增 `rpa/base.py` + `rpa/runner.py` + `rpa/adapters/example_minimal.py` ≈ **新增 300 行**

净变化：原 1700 行 → 新框架 800 + adapter 接口 80 + 示例 100 = **约 980 行**，但**完全无品牌依赖**。

---

## 3. 8 周时间表

| 周 | 主题 | 关键产出 | 风险/前置 |
|---|------|---------|----------|
| **W1** 净化 & 安全 | (1) `check_branding.py` 扫出所有品牌痕迹<br>(2) `gitleaks` 升级 + 凭据清除<br>(3) `scan_pii.py` 跑 etl_data/uploads/logs | git filter-repo 改写历史前**需用户授权**；先备份 |
| **W2** 核心包抽离 (后端 50%) | `channel_analytics/config/` + `etl/` + `db/` 拆包；`field_mapping.py` 90% 复用；`permission_service.py` 平移；**`rpa/` 框架抽离（去厂商特定信息）** | `app.main` 跨包引用多，import 链要重写；YAML None↔inf 转换；rpa_service 配置文件名 `rpa_<vendor>_*` → `rpa_target_*` |
| **W3** 业务通用化重构 | 完成 2.1/2.2/2.3；完成 2.4 RPA 抽象（`base.py` 接口 + `runner.py` 流程引擎 + `adapters/example_minimal.py`）；保留 fallback 但默认禁用；新增 `examples/cosmetics_demo/` + **`examples/minimal_plugin/`**（adapter 模板） | `classify_*_status` 边界用例多，parametrize 覆盖；adapter 接口契约要写清楚；entry_points 注册机制要测通 |
| **W4** 测试补强 I | conftest 改 SQLite-in-memory + factory-boy；纯函数测试 100% 覆盖；**目标 30%** | SQLAlchemy 在 SQLite vs MySQL 有方言差异（`REPLACE INTO`、JSON 字段），需 mock |
| **W5** 测试补强 II + 前端净化 | 集成测试 ETL 管道（5 STG → 7 RPT）；前端 91 文件品牌字符串清除 + i18n 拆分；**目标 50%** | Vue3 测试要补 Vitest；前端测试当前 0 |
| **W6** 文档 & 部署 | mkdocs 站（getting-started/architecture/how-to/reference）；Dockerfile 收敛到 `deploy/docker/`；`docker-compose.yml` 一键跑通 | 教程截图脱敏；API 文档从内嵌注释重生（**先 review 内部表名**） |
| **W7** CI/CD + Go-Live 准备 | 6 个 GH Action 跑通：lint/test/secret-scan/branding-scan/docs-build/release-dry-run；CHANGELOG/CONTRIBUTING/CoC 落地；抢注 PyPI 名 | branding-scan 必须 fail-closed；PyPI 名字可能冲突 |
| **W8** 公测 & 发布 | 内测 3-5 个外部人跑通 30 分钟教程；写发布博客；tag `v0.1.0`；PyPI + GH Release | 至少留 2 天处理公测反馈 |

**总人力估算**：1 主程 + 0.5 测试/文档 ≈ 12-14 周人·周 / 8 周墙钟（并行）。

---

## 4. 测试补强策略

| 阶段 | 覆盖率目标 | 关键文件 |
|------|-----------|---------|
| W4 末 | 30% | conftest 改 SQLite；`etl/cleaners.py` 100%；`classifiers.py` parametrize |
| W5 末 | 50% | 集成测试 5 STG → 7 RPT；前端 Vitest 起步 |
| W8 末 | ≥ 60% | 6 张 RPT 表 + 主要 API |

**测试改造方向**：
- 删除 `conftest.py:27` 真实凭据 `kent/[REDACTED]`，改 SQLite + factory-boy
- 拆 `test_auth_api.py` 为 `test_jwt_unit.py` + `test_auth_integration.py`（httpx.AsyncClient）
- API 测试改用 `TestClient` + SQLite seed data
- 优先级：`cleaners` → `classifiers` → `field_mapping` → `permissions` → `db/session` → `scheduler/worker` → `rpt/*`

**60% 而非 70% 的原因**：开源项目 60% 是健康线，70% 边际成本陡升。

---

## 5. 文档清单（三层递进）

### L1 — 30 分钟跑通
- `README.md`（30 秒电梯 + 截图 + 4 个 badge：CI / PyPI / License / Discord）
- `docs/getting-started/install.md`、`first-run.md`、`docker.md`
- `examples/notebooks/01_quickstart.ipynb`

### L2 — 1 小时理解架构
- `docs/architecture/overview.md`（分层图：前端/API/Service/ETL/DB/Plugin）
- `docs/architecture/etl-pipeline.md`（5 STG → 7 RPT 流向图）
- `docs/architecture/permissions.md`（三维权限）
- `docs/architecture/plugin-system.md`（BrandWhitelistProvider 抽象 + 3 Provider 对比）
- `docs/decisions/` ADRs：monorepo / plugin-system / license-apache

### L3 — 1 天能改业务
- `docs/how-to/add-erp-adapter.md`（继承 `BaseAdapter`，5 分钟生成新适配器）
- `docs/how-to/add-brand-whitelist.md`（改 YAML / 插 DB / 切 env）
- `docs/how-to/customize-thresholds.md`（改 `business_rules.yaml`，边界用例提醒）
- `docs/how-to/add-custom-report.md`（继承 `BaseReport` + 注册）
- `docs/reference/api.md`（OpenAPI 自动生成，**先 review 内部表名**）
- `docs/reference/config.md`、`cli.md`

---

## 6. 发布前 Go-Live Checklist

### P0 — 必须 100% 完成
- [ ] `LICENSE` = Apache-2.0，header 在所有 `.py` / `.ts` 文件
- [ ] `NOTICE` 列出 pandas / FastAPI / Vue3 / openpyxl 等依赖与版本
- [ ] `.gitleaks.toml` 加严，gitleaks 0 命中
- [ ] `check_branding.py` 0 命中（扫描关键词维护在 `scripts/check_branding.py` 内部列表中——含原仓库的内部品牌名/客户名/员工账号 + 常见 ERP 厂商字符串）。**注意：关键词列表本身不进入开源仓，放在构建脚本的私有配置里**。
- [ ] `detect_pii.py` 对 `etl_data/` `uploads/` `logs/` 0 命中
- [ ] 删除：`.env`、`.session_secret`、`docs/superpowers/*`、`.claude/`、`.superpowers/`、`backup/`、`tasks/`、`.claude/CLAUDE.md` 中的 kent 凭据
- [ ] `conftest.py` 无真实凭据
- [ ] `README.md` 无公司名 / 客户名 / 内部代号
- [ ] CI 全绿（lint / type-check / test / secret-scan / branding-scan / docs-build）
- [ ] PyPI 包名已抢注（即使空包也要先占）
- [ ] GitHub 仓库设 License Detection = Apache-2.0
- [ ] `SECURITY.md` 提供上报邮箱
- [ ] `v0.1.0` tag 切的是 `main`（**不是** `master`，避免历史污染）

### P1 — 应该完成
- [ ] 至少 3 个 `examples/` 跑通（cosmetics demo / minimal plugin / notebook）
- [ ] mkdocs 0 警告
- [ ] Dockerfile 构建 < 5 分钟，镜像 < 500MB
- [ ] 6 个 GH Action 都跑过 dry-run
- [ ] 邀请 3-5 个外部开发者跑通 30 分钟教程并反馈
- [ ] 至少 1 个 ADR
- [ ] `CODE_OF_CONDUCT.md` + `CONTRIBUTING.md` + PR/Issue 模板
- [ ] 域名（可选）：`channel-analytics.dev` 或 GitHub Pages

### P2 — 有空再做
- [ ] Discord / Slack 频道
- [ ] i18n 拆分后做中文 README 镜像
- [ ] 录 5 分钟 demo 视频
- [ ] 在 HN / Reddit / V2EX / 掘金 发预告
- [ ] logo 设计
- [ ] 第一个 `good first issue`

---

## 7. 开源后运营建议

### 7.1 降低 issue 噪音
1. **Issue 模板三件套**：`bug_report` / `feature_request` / `adapter_integration`（第三个引导"加你的 ERP"走插件仓而非代码）
2. **Stale Bot**：60 天无活动自动关闭
3. **Discussions 优先**："How do I…" 类问题引导到 Discussions，issue 区只放 bug / RFC
4. **Issue Form 强制字段**：版本号、日志、复现步骤

### 7.2 引导贡献者
1. W7 末人工标注 5-10 个 `good first issue`
2. `CONTRIBUTING.md` 写明：`make dev` / `make test` / `make lint && make test` / Conventional Commits
3. 首个贡献者特别答谢 + 发推
4. Discord 频道：`#dev` / `#plugins` / `#users-cn` / `#users-en`

### 7.3 处理"我要加我的 ERP"类 PR
**核心原则：不拒绝，三条路径都欢迎。**

**路径 1：自行实现 + pip install（推荐大多数用户）**
- 文档明确写："继承 `channel_analytics.rpa.base.ErpAdapter`，实现 5 个方法，打包发布到 PyPI，在你自己的项目里 `pip install` 后通过 `entry_points` 注册"
- 这种 PR **不要发到主仓**——直接走用户自己的项目

**路径 2：贡献到 contrib 仓**
- README + CONTRIBUTING 写："具体 ERP 适配请放 `channel-analytics-contrib/<erp>-adapter/`，主仓只接受通用核心"
- 提供 `cookiecutter adapter-template`，5 分钟生成新适配器
- 在主仓 README 列一个"生态适配器"清单（指向 contrib 仓）
- 每季度整理 contrib 仓，把活跃适配器反向推荐到主仓

**路径 3：极少数通用模式提入主仓**
- 比如 `BaseExcelAdapter`（处理 `iframe` + `file_input` + 等待下载的通用步骤）这种**与厂商无关的 helper**，可以进主仓 `rpa/adapters/_helpers/`
- 限制：单文件 < 100 行、零厂商特定字符串、必须配 3 个测试用例

**反向防御**：
- `CODEOWNERS` 限制 `rpa/adapters/` 只有核心 maintainer 可改
- 厂商特定 PR（如"我加个某 ERP"）必须走 contrib 仓，不直接合入 `main`
- 长期（v0.5+）：把"广泛使用的 contrib 适配器"提到主仓 `optional-dependencies`（`pip install channel-analytics[sap]`）

---

## 8. 关键决策点（一次性确认，避免 8 周内反复）

1. **包名**：`channel-analytics`（PyPI）/ `channel_analytics`（import 路径）— W1 末抢注
2. **最低 Python 版本**：3.11（match-case / tomllib / 性能）
3. **数据库后端**：MySQL 8 主仓；测试用 SQLite；PostgreSQL 列为 "experimental"
4. **类型注解**：全量 `mypy --strict`（开源前一次性补齐）
5. **格式化**：ruff format + ruff check
6. **commit 风格**：Conventional Commits（release-please 自动生成 CHANGELOG）
7. **品牌名处理**：12 个品牌名**不**在 `cosmetics_demo/seed_data/brands.yaml` 保留中文原名，改为 `Brand A / Brand B` 占位
8. **`docs/superpowers/` 处置**：**不**带进新仓，留在私有仓；新仓文档从零写

---

## 9. 关键文件清单（实施时必读）

| 原文件（私有仓） | 在新仓中的去向 |
|---|---|
| `backend/app/services/etl_service.py`（业务硬编码 3 处源头） | **W3 重构**为 `channel_analytics/etl/{pipeline,cleaners,classifiers}.py` + `plugins/` |
| `backend/app/services/field_mapping.py`（70% 通用） | **W2 平移**到 `channel_analytics/etl/field_mapping.py` |
| `backend/app/database.py`（三种 Session 上下文） | **W2 平移**为 `channel_analytics/db/session.py` |
| `backend/app/services/permission_service.py`（三维权限） | **W2 平移**为 `channel_analytics/auth/permissions.py` |
| `backend/tests/conftest.py`（含真实凭据 kent） | **W1 净化** + **W4 改造**为 SQLite in-memory |
| `backend/app/services/rpa_engine.py`（具体厂商实现） | **W2 拆**：流程骨架（`start/close/run_all`）→ `rpa/runner.py`；具体选择器（`MODULE_CONFIG`、厂商特定 iframe、硬编码 DOM ID）→ **不带**；新增 `rpa/base.py` 定义 `ErpAdapter` 抽象接口 |
| `backend/app/services/rpa_service.py`（调度器 + 僵尸清理 + 邮件） | **W2 平移**到 `rpa/scheduler.py`（去厂商特定命名 → 通用 `rpa_target_url`） |
| `backend/app/services/rpa_worker.py`（子进程隔离 80% 通用） | **W2 平移**到 `rpa/worker.py`（去厂商特定错误消息 → "ERP 账号未配置"） |
| `scripts/automation/<vendor>_config.yaml`（厂商特定配置） | **不带**——`rpa/adapters/` 下只留 `example_minimal.py` |
| `backend/app/services/llm_service.py`（商业 LLM 配置） | **不带**——商业 LLM 服务对接不进开源仓 |
| `frontend/index.html` / `public/manifest.json` / `public/sw.js` | **W5 净化**品牌字符串 |
| `deploy/*.sh` | **W6 脱敏**（替换 4 处路径/DB 名） |
| `docs/superpowers/*` | **不带**新仓 |
| `docs/API_ENDPOINTS.md` | **W6 改写**为新仓 docs（先 review 内部表名） |

---

## 10. 验证方案（end-to-end）

每个阶段都设可验证里程碑：

| 阶段 | 验证命令 | 期望结果 |
|------|---------|---------|
| W1 末 | `python scripts/check_branding.py && gitleaks detect --no-git` | 0 命中 |
| W2 末 | `pip install -e . && python -c "from channel_analytics.etl import pipeline"` | import 成功 |
| W3 末 | `pytest tests/unit/test_classifiers.py -v` | parametrize 全绿（边界值 0/6/12/18/24/28/32/999） |
| W4 末 | `pytest --cov=channel_analytics --cov-report=term-missing` | 覆盖率 ≥ 30% |
| W5 末 | `pytest --cov=channel_analytics` | ≥ 50%；前端 `npm run test` 绿 |
| W6 末 | `mkdocs serve` + `docker compose up` | 0 警告，5 分钟内看到 demo 数据 |
| W7 末 | `act -j ci`（或 push 到 feature branch 看 Action） | 6 个 Action 全绿 |
| W8 末 | 3-5 个外部开发者按 README 跑通 30 分钟教程 | 100% 跑通；PyPI `pip install channel-analytics` 成功 |

**End-to-end 验证**：
```bash
git clone https://github.com/<org>/channel-analytics
cd channel-analytics
make dev         # 装依赖 + 起 MySQL + 起后端
make seed        # 加载 examples/cosmetics_demo 数据
make run-etl     # 跑 ETL 管道
open http://localhost:5173  # 看到示例报表
```

任何一步失败 → 阻塞发布。

---

## 11. 反向风险登记（提前预警）

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| git filter-repo 改写时丢失 commit | 低 | 高 | **操作前全量备份** + 通知所有 contributor |
| PyPI 包名冲突 | 中 | 中 | W1 末先抢注（占空包也行） |
| **某 ERP 厂商特定选择器 / iframe / DOM ID 残留在 rpa/ 目录** | 中 | 高 | **`check_branding.py` 加严匹配常见 ERP 厂商字符串**（具体列表维护在 `scripts/check_branding.py` 头部，不进版本库），CI fail-closed；rpa/ 目录 grep 二次确认 |
| **rpa/example_minimal.py 误写成"接近某 ERP 厂商"导致被搜索到** | 中 | 中 | 故意保持 5 个方法都是 `raise NotImplementedError`；注释明确写"这是一个空模板，请自己实现" |
| **`docs/superpowers/` 误带入** | 中 | 中 | 新仓 `.gitignore` + 复制清单黑名单 |
| 第一个月 issue 爆炸（"支持 X 系统"） | 高 | 中 | 模板 + Stale Bot + Discussions + `adapter_integration` issue 模板引导到 contrib 仓 |
| 真实凭据通过 PR 误提交 | 中 | 高 | gitleaks PR 阶段强制扫描 |
| **adapter 插件的 entry_points 注册机制不工作** | 中 | 高 | W3 写一个 `tests/plugins/test_entry_points_discovery.py` 跑通；W4 集成测试覆盖 |
| 公开后被竞争对手直接 fork 卖 | 高 | 中 | 这是开源的代价，不算"风险"——接受 |
