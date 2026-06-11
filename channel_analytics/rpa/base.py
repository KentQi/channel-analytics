"""ErpAdapter 抽象基类(对应 PLAN.md §2.4.3 + 原仓 rpa_engine.py)。

5 个钩子:
  - login(page, url, username, password)
  - navigate_to_module(page, module)
  - set_date_filter(page, start_date, end_date)
  - search(page)
  - export(page, download_dir) -> str(下载文件路径)

用户实现任一 ERP 适配器只需继承本类 + 实现 5 个方法,然后通过 entry_points 注册:

    # pyproject.toml
    [project.entry-points."channel_analytics.rpa_adapters"]
    my_erp = "my_package.my_module:MyAdapter"
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from playwright.async_api import Page


class ErpAdapter(ABC):
    """ERP 浏览器自动化适配器抽象基类。

    用户实现这个接口即可接入任何 Web ERP。
    实现中通过 page.frame_locator / page.locator 写自己的选择器,
    不在本框架的关注范围。
    """

    @abstractmethod
    async def login(
        self, page: Page, url: str, username: str, password: str
    ) -> None:
        """登录 ERP。失败抛 LoginError。"""
        raise NotImplementedError

    @abstractmethod
    async def navigate_to_module(self, page: Page, module: str) -> None:
        """导航到指定模块(由用户在 adapter 内定义 module 名)。失败抛 NavigateError。"""
        raise NotImplementedError

    async def set_date_filter(
        self, page: Page, start_date: str, end_date: str
    ) -> None:
        """设置日期筛选。可选覆写;默认 no-op。"""
        return None

    @abstractmethod
    async def search(self, page: Page) -> None:
        """点击查询按钮。失败抛 SearchError(可选)。"""
        raise NotImplementedError

    @abstractmethod
    async def export(self, page: Page, download_dir: Path | str) -> str:
        """导出并下载 Excel。返回下载文件绝对路径。失败抛 ExportError。"""
        raise NotImplementedError


__all__ = ["ErpAdapter"]