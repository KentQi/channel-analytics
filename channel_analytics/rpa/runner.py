"""RpaRunner — 通用 RPA 流程引擎(对应原仓 RpaEngine 的通用部分)。

职责:
  - 浏览器生命周期管理(start / close)
  - 单模块执行流程:login → navigate → set_date_filter → search → export
  - 多模块遍历 + 重试 + on_module_done 回调

不依赖具体厂商(厂商特定逻辑由 ErpAdapter 实现)。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterable

from playwright.async_api import Page, async_playwright

from channel_analytics.rpa.base import ErpAdapter
from channel_analytics.rpa.exceptions import (
    ExportError,
    LoginError,
    NavigateError,
    RpaError,
)

logger = logging.getLogger(__name__)


@dataclass
class RpaRunnerConfig:
    """RPA Runner 运行时配置(对齐原仓 RpaEngine.__init__ 参数)。"""
    download_dir: str = "./data/rpa_downloads"
    headless: bool = True
    slow_mo_ms: int = 300
    timeout_ms: int = 30_000
    timeout_multiplier: float = 1.0
    retries: int = 1  # 每个模块失败重试次数


@dataclass
class ModuleResult:
    """单模块执行结果。"""
    module: str
    success: bool
    file_path: str | None = None
    error: str | None = None


OnModuleDone = Callable[[ModuleResult], Awaitable[None]]


class RpaRunner:
    """通用 RPA 流程引擎。注入不同 ErpAdapter 即可工作。"""

    def __init__(
        self,
        adapter: ErpAdapter,
        config: RpaRunnerConfig | None = None,
    ) -> None:
        self.adapter = adapter
        self.config = config or RpaRunnerConfig()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None

    # ----- 浏览器生命周期(对应原仓 RpaEngine.start / close) -----

    async def start(self) -> None:
        """启动 Playwright Chromium。"""
        download_dir = Path(self.config.download_dir).resolve()
        download_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo_ms,
        )
        self._context = await self._browser.new_context(
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.timeout_ms)
        logger.info("RPA 浏览器已启动 (headless=%s)", self.config.headless)

    async def close(self) -> None:
        """关闭浏览器(防御性清理,异常被吞)。"""
        for close_fn in (self._close_context, self._close_browser, self._stop_playwright):
            try:
                await close_fn()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        logger.info("RPA 浏览器已关闭")

    async def _close_context(self) -> None:
        if self._context:
            await self._context.close()

    async def _close_browser(self) -> None:
        if self._browser:
            await self._browser.close()

    async def _stop_playwright(self) -> None:
        if self._playwright:
            await self._playwright.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("RPA 未启动;请先调用 start()")
        return self._page

    # ----- 单模块执行 -----

    async def run_module(
        self,
        *,
        module: str,
        url: str,
        username: str,
        password: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> ModuleResult:
        """单模块执行(对齐原仓 run_all 单次循环)。"""
        assert self._page is not None, "请先 start()"
        last_error: str | None = None
        for attempt in range(self.config.retries + 1):
            try:
                await self.adapter.login(self._page, url, username, password)
                await self.adapter.navigate_to_module(self._page, module)
                if start_date and end_date:
                    await self.adapter.set_date_filter(
                        self._page, start_date, end_date,
                    )
                await self.adapter.search(self._page)
                file_path = await self.adapter.export(
                    self._page, self.config.download_dir,
                )
                logger.info("模块 %s 成功(attempt=%d)", module, attempt)
                return ModuleResult(module=module, success=True, file_path=file_path)
            except LoginError as e:
                last_error = f"login: {e}"
                logger.warning("模块 %s 登录失败: %s", module, e)
                break  # 登录失败不重试
            except (NavigateError, ExportError, RpaError) as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(
                    "模块 %s attempt=%d 失败: %s", module, attempt, e,
                )
                continue
        return ModuleResult(module=module, success=False, error=last_error)

    async def run_all(
        self,
        modules: Iterable[str],
        *,
        url: str,
        username: str,
        password: str,
        start_date: str | None = None,
        end_date: str | None = None,
        on_module_done: OnModuleDone | None = None,
    ) -> list[ModuleResult]:
        """遍历多个模块逐个执行,每个完成后回调 on_module_done(对齐原仓 on_module_done)。"""
        results: list[ModuleResult] = []
        for mod in modules:
            r = await self.run_module(
                module=mod, url=url, username=username, password=password,
                start_date=start_date, end_date=end_date,
            )
            results.append(r)
            if on_module_done is not None:
                try:
                    await on_module_done(r)
                except Exception as e:  # 回调异常不阻断后续模块
                    logger.warning("on_module_done 回调异常: %s", e)
        return results


__all__ = ["RpaRunner", "RpaRunnerConfig", "ModuleResult"]