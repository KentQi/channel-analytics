"""minimal_plugin — adapter 模板示例。

复制本文件到你的项目,改名为 my_erp_adapter.py,实现 5 个方法即可。
"""
from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page

from channel_analytics.rpa.base import ErpAdapter


class MyErpAdapter(ErpAdapter):
    """示例 adapter 骨架。"""

    async def login(
        self, page: Page, url: str, username: str, password: str
    ) -> None:
        # TODO: 你的登录逻辑
        raise NotImplementedError

    async def navigate_to_module(self, page: Page, module: str) -> None:
        # TODO: 导航到指定模块
        raise NotImplementedError

    async def search(self, page: Page) -> None:
        # TODO: 点击查询按钮
        raise NotImplementedError

    async def export(self, page: Page, download_dir: Path | str) -> str:
        # TODO: 导出 + 返回下载文件路径
        raise NotImplementedError


__all__ = ["MyErpAdapter"]