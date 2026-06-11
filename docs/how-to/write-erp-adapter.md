# 写 ERP Adapter

5 步接入你的 Web ERP。

## 1. 创建包

```bash
mkdir my_erp_adapter
cd my_erp_adapter
```

## 2. 写 pyproject.toml

```toml
[project]
name = "my-erp-adapter"
version = "0.1.0"
dependencies = [
    "channel-analytics>=0.1.0",
    "playwright>=1.40",
]

[project.entry-points."channel_analytics.rpa_adapters"]
my_erp = "my_erp_package.adapter:MyErpAdapter"
```

## 3. 写 adapter.py

继承 `ErpAdapter`,实现 5 个方法:

```python
from pathlib import Path
from playwright.async_api import Page
from channel_analytics.rpa.base import ErpAdapter

class MyErpAdapter(ErpAdapter):
    async def login(self, page: Page, url: str, username: str, password: str) -> None:
        """登录 ERP。"""
        await page.goto(url)
        # 假设你的 ERP 有这样的结构:
        iframe = page.frame_locator('iframe[title="login"]')
        await iframe.locator('#username').fill(username)
        await iframe.locator('#password').fill(password)
        await iframe.locator('#submit').click()

    async def navigate_to_module(self, page: Page, module: str) -> None:
        """导航到模块。module 名由你自己定义(例如 'inventory_query')。"""
        await page.locator(f'a[href="/modules/{module}"]').click()

    async def search(self, page: Page) -> None:
        """点击查询。"""
        await page.locator('button#search').click()

    async def export(self, page: Page, download_dir: Path | str) -> str:
        """导出 Excel,返回下载文件路径。"""
        async with page.expect_download() as dl_info:
            await page.locator('button#export').click()
        download = await dl_info.value
        target = Path(download_dir) / download.suggested_filename
        await download.save_as(str(target))
        return str(target)
```

## 4. 安装

```bash
pip install -e .
```

## 5. 配置 + 跑

```bash
# .env
RPA_ADAPTER=my_erp_package.adapter:MyErpAdapter
RPA_TARGET_URL=https://your-erp.example.com
RPA_USERNAME=alice
RPA_PASSWORD=secret

# 跑 worker
python -m channel_analytics.rpa.worker --task-id 1 --module "inventory_query"
```

## 应该避免

- ❌ 把品牌名 / 客户名 / 厂商字符串写进 adapter(CI 会拦截)
- ❌ fork 主仓加 vendor 特定代码
- ❌ 在 adapter 里 hardcode 凭据(用环境变量)