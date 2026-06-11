"""ExampleMinimalAdapter — 空模板,5 个方法都 raise NotImplementedError。

本文件故意保持极简,绝不暗示任何具体厂商的选择器 / DOM 结构 / iframe 标题。
接入你自己的 ERP 时,复制本文件并实现 5 个方法即可。
"""
from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page

from channel_analytics.rpa.base import ErpAdapter
from channel_analytics.rpa.exceptions import (
    ExportError,
    LoginError,
    NavigateError,
)


class ExampleMinimalAdapter(ErpAdapter):
    """最小示例 adapter — 不绑定任何厂商。

    5 个方法都是 NotImplementedError;部署方继承本类实现自己的选择器。
    """

    async def login(
        self, page: Page, url: str, username: str, password: str
    ) -> None:
        raise NotImplementedError(
            "ExampleMinimalAdapter 不实现 login。请继承 ErpAdapter 实现自己的登录逻辑。"
        )

    async def navigate_to_module(self, page: Page, module: str) -> None:
        raise NotImplementedError(
            "ExampleMinimalAdapter 不实现 navigate_to_module。"
        )

    async def search(self, page: Page) -> None:
        raise NotImplementedError(
            "ExampleMinimalAdapter 不实现 search。"
        )

    async def export(self, page: Page, download_dir: Path | str) -> str:
        raise NotImplementedError(
            "ExampleMinimalAdapter 不实现 export。"
        )


__all__ = ["ExampleMinimalAdapter"]