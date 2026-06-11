# ERP adapter 模板

复制本目录即可开始写你自己的 adapter。

## 5 步接入

```bash
cp -r examples/minimal_plugin my_erp_adapter
cd my_erp_adapter
```

### 1. 编辑 `adapter.py`

```python
from channel_analytics.rpa.base import ErpAdapter
from channel_analytics.rpa.exceptions import LoginError, NavigateError, ExportError

class MyErpAdapter(ErpAdapter):
    async def login(self, page, url, username, password):
        # 你的登录逻辑
        ...

    async def navigate_to_module(self, page, module):
        # 导航
        ...

    async def search(self, page):
        # 点查询
        ...

    async def export(self, page, download_dir):
        # 导出 Excel,返回文件路径
        ...
```

### 2. 编辑 `pyproject.toml`

```toml
[project.entry-points."channel_analytics.rpa_adapters"]
my_erp = "my_erp_package.adapter:MyErpAdapter"
```

### 3. 安装

```bash
pip install -e .
```

### 4. 配置 channel-analytics

设置环境变量 `RPA_ADAPTER=my_erp_package.adapter:MyErpAdapter`,或在 `.env` 加:

```
RPA_ADAPTER=my_erp_package.adapter:MyErpAdapter
RPA_TARGET_URL=https://your-erp.example.com
RPA_USERNAME=your_username
RPA_PASSWORD=your_password
```

### 5. 跑

```bash
python -m channel_analytics.rpa.worker --task-id 1 --module "your_module_name"
```

## 不应该做的事

- 不要把品牌名 / 客户名 / 厂商特定字符串写进 `adapter.py`(会被 `scripts/check_branding.py` 拦截)
- 不要 fork 主仓加 vendor 特定代码 — 用 contrib 仓或自己的包
- 不要把登录 token / cookie 写进 git — 用环境变量