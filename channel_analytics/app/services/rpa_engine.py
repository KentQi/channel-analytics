"""
RPA 引擎 - Playwright 浏览器自动化
负责ERP system登录、模块导航、数据导出下载
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class RpaError(Exception):
    """RPA 基础异常"""
    def __init__(self, stage: str, message: str, cause: str = ""):
        self.stage = stage
        self.message = message
        self.cause = cause
        super().__init__(f"[{stage}] {message}")


class LoginError(RpaError):
    """登录失败"""
    def __init__(self, message: str, cause: str = ""):
        super().__init__("登录", message, cause)


class NavigateError(RpaError):
    """导航失败"""
    def __init__(self, message: str, cause: str = ""):
        super().__init__("导航", message, cause)


class ExportError(RpaError):
    """导出失败"""
    def __init__(self, message: str, cause: str = ""):
        super().__init__("导出", message, cause)

# 模块配置：选择器、导航路径等
MODULE_CONFIG = {
    "现存量查询": {
        "favorites_text": "现存量查询",
        "search_button_id": "2798265search",
        "has_expand": False,
        "has_date_filter": False,
        "has_search": True,
    },
    "采购入库": {
        "favorites_text": "采购入库",
        "search_button_id": "3111171search",
        "has_expand": True,
        "has_date_filter": True,
        "has_search": True,
    },
    "销售出库": {
        "favorites_text": "销售出库",
        "search_button_id": "59413689search",
        "has_expand": True,
        "has_date_filter": True,
        "has_search": True,
    },
}


class RpaEngine:
    """ERP system RPA 引擎"""

    def __init__(self, download_dir: str, timeout_multiplier: float = 1.0, headless: bool = True, slow_mo: int = 300):
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_mult = timeout_multiplier
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    def _timeout(self, base_ms: int) -> int:
        return int(base_ms * self.timeout_mult)

    async def start(self):
        """启动浏览器"""
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
        self.context = await self.browser.new_context(
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        logger.info("RPA 浏览器已启动")

    async def close(self):
        """关闭浏览器（防御性清理，确保不影响进程退出）"""
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        # 清除引用，防止重复关闭
        self.context = None
        self.browser = None
        self.playwright = None
        logger.info("RPA 浏览器已关闭")

    async def login(self, url: str, username: str, password: str) -> bool:
        """登录ERP system"""
        logger.info(f"正在登录: {url}")
        try:
            await self.page.goto(url.rstrip("/") + "/", wait_until="domcontentloaded")
        except Exception as e:
            raise LoginError("无法打开登录页面，请检查网络或ERP system地址", cause=str(e))

        await asyncio.sleep(5)

        # 处理弹窗
        for btn_name in ["接受", "拒绝"]:
            try:
                btn = self.page.get_by_role("button", name=btn_name)
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    logger.info(f"已点击'{btn_name}'")
                    await asyncio.sleep(2)
                    break
            except:
                continue

        # 处理 workbench-overlay 遮罩层
        try:
            overlay = self.page.locator(".workbench-overlay")
            if await overlay.is_visible(timeout=2000):
                logger.info("检测到 workbench-overlay，尝试关闭")
                close_btn = overlay.locator(".close, .workbench-overlay-close, [aria-label='Close']")
                if await close_btn.first.is_visible(timeout=1000):
                    await close_btn.first.click()
                else:
                    await self.page.keyboard.press("Escape")
                await asyncio.sleep(1)
                if await overlay.is_visible(timeout=1000):
                    await self.page.evaluate("""
                        document.querySelectorAll('.workbench-overlay').forEach(el => {
                            el.style.display = 'none';
                        });
                    """)
                    logger.info("已通过 JS 隐藏 workbench-overlay")
        except Exception as e:
            logger.debug(f"处理 workbench-overlay 异常（可忽略）: {e}")

        # 等待 iframe
        try:
            login_iframe = self.page.frame_locator('iframe[title="erp_login"]')
            username_input = login_iframe.get_by_role("textbox", name="邮箱/账号/用户手机号")
            await username_input.wait_for(state="visible", timeout=self._timeout(45000))
        except Exception:
            raise LoginError("登录页面加载超时，未找到登录表单", cause="iframe[erp_login] 未出现")

        # 通用遮挡清理（登录前）：点击前先把所有已知遮罩层关掉
        try:
            # 关闭可能的公告/升级弹窗
            for btn_name in ["我知道了", "知道了", "稍后再说", "不再提示", "关闭", "Close", "取消", "接受", "拒绝"]:
                try:
                    btn = self.page.get_by_role("button", name=btn_name)
                    if await btn.first.is_visible(timeout=800):
                        await btn.first.click()
                        logger.info(f"登录前关闭遮挡弹窗（按钮: {btn_name}）")
                        await asyncio.sleep(0.5)
                except Exception:
                    continue
            # JS 强制隐藏所有遮罩层
            await self.page.evaluate("""
                document.querySelectorAll(
                    '.workbench-overlay, .ant-modal-mask, .erp-modal-mask, ' +
                    '[class*="mask"], [class*="overlay"], [class*="modal-mask"], ' +
                    '.ant-modal-wrap, .el-overlay, .el-dialog__wrapper'
                ).forEach(el => { el.style.display = 'none'; el.style.pointerEvents = 'none'; });
            """)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"登录前遮挡清理异常（可忽略）: {e}")

        # 输入账号密码
        try:
            await username_input.click()
            await username_input.fill(username)
        except Exception as e:
            raise LoginError("无法输入账号，登录表单可能被遮挡", cause=str(e)[:200])

        try:
            password_input = login_iframe.get_by_role("textbox", name="密码")
            await password_input.click()
            await password_input.fill(password)
        except Exception as e:
            raise LoginError("无法输入密码", cause=str(e)[:200])

        # 点击登录
        login_btn = login_iframe.get_by_role("button", name="登录")
        try:
            await login_btn.wait_for(state="visible", timeout=self._timeout(15000))
            await login_btn.click(timeout=self._timeout(5000))
        except Exception:
            try:
                login_btn = login_iframe.locator('#submit_btn_login')
                await login_btn.wait_for(state="visible", timeout=self._timeout(10000))
                await login_btn.click(force=True)
            except Exception as e:
                raise LoginError("无法点击登录按钮", cause=str(e)[:200])

        # 等待登录完成（检查是否登录成功）
        try:
            await username_input.wait_for(state="hidden", timeout=self._timeout(30000))
        except:
            # 登录表单还在 → 可能密码错误或验证码
            # 检查是否有错误提示
            try:
                error_el = login_iframe.locator('.error-msg, .login-error, .err-msg, [class*="error"]')
                error_text = await error_el.first.text_content(timeout=2000)
                if error_text and error_text.strip():
                    raise LoginError(f"登录失败: {error_text.strip()}", cause="账号密码错误或需要验证码")
            except LoginError:
                raise
            except:
                pass
            raise LoginError("登录超时，请检查账号密码是否正确", cause="登录表单30秒内未消失")

        try:
            await self.page.wait_for_load_state("networkidle", timeout=self._timeout(15000))
        except:
            pass

        # 处理登录后可能弹出的各种公告/升级/新手引导弹窗
        await self._dismiss_post_login_dialogs()

        logger.info("登录成功")
        return True

    async def _dismiss_post_login_dialogs(self):
        """关闭登录后弹出的各种公告弹窗（升级提示、新手引导等）"""
        # 通用关闭按钮关键词
        close_keywords = ["我知道了", "知道了", "稍后再说", "不再提示", "关闭", "Close", "取消", "×", "X"]
        for kw in close_keywords:
            try:
                btn = self.page.get_by_role("button", name=kw)
                if await btn.first.is_visible(timeout=1500):
                    await btn.first.click()
                    logger.info(f"已关闭登录后弹窗（按钮: {kw}）")
                    await asyncio.sleep(1)
            except:
                continue
        # 处理可能的遮罩层
        try:
            await self.page.evaluate("""
                document.querySelectorAll('.workbench-overlay, .ant-modal-mask, .erp-modal-mask, [class*="mask"]').forEach(el => {
                    el.style.display = 'none';
                });
            """)
        except:
            pass

    async def go_home(self):
        """返回首页"""
        try:
            home_btn = self.page.locator("span").filter(has_text=r"^首页$")
            await home_btn.wait_for(state="visible", timeout=self._timeout(10000))
            await home_btn.click()
            await self.page.wait_for_load_state("networkidle", timeout=self._timeout(15000))
        except:
            await self.page.goto("https://erp.example.com/", wait_until="domcontentloaded")
            await self.page.wait_for_load_state("networkidle", timeout=self._timeout(15000))

    async def open_module(self, module_name: str) -> bool:
        """通过收藏夹打开模块"""
        config = MODULE_CONFIG.get(module_name)
        if not config:
            logger.error(f"未知模块: {module_name}")
            return False

        try:
            link = self.page.locator(
                '#FavoriteApplicationGroup_1872859676802547731'
            ).get_by_text(config["favorites_text"])
            await link.wait_for(state="visible", timeout=self._timeout(10000))
            await link.click()
            await self.page.wait_for_load_state("networkidle", timeout=self._timeout(30000))
            logger.info(f"已打开模块: {module_name}")
            return True
        except Exception as e:
            logger.error(f"打开模块失败: {e}")
            return False

    async def set_date_filter(self):
        """设置日期筛选：更多 → 点击单据日期开始输入框 → 至过去"""
        try:
            more_radio = self.page.locator('.predicateDatepicker-dropDown-more')
            await more_radio.wait_for(state="visible", timeout=self._timeout(10000))
            await asyncio.sleep(2)
            await more_radio.click()
            await asyncio.sleep(2)

            # 精确点击"单据日期"的开始输入框（fieldid 含 vouchdate），避免误点自定义字段
            start_input = self.page.locator(
                'input[fieldid*="vouchdate"][placeholder="开始"]'
            )
            await start_input.wait_for(state="visible", timeout=self._timeout(10000))
            await asyncio.sleep(2)
            await start_input.click()
            await asyncio.sleep(2)

            # 在已打开的日历下拉面板中点击"至过去"
            past_option = self.page.locator('.wui-picker-dropdown').get_by_text("至过去", exact=True)
            await past_option.wait_for(state="visible", timeout=self._timeout(10000))
            await asyncio.sleep(2)
            await past_option.click()
            await asyncio.sleep(2)
            logger.info("日期筛选设置完成: 至过去")
        except Exception as e:
            logger.warning(f"日期设置异常: {e}")

    async def click_search(self, search_button_id: str):
        """点击搜索按钮"""
        try:
            btn = self.page.locator(f'[id="{search_button_id}"]')
            await btn.wait_for(state="visible", timeout=self._timeout(10000))
            await btn.click()
            await self.page.wait_for_load_state("networkidle", timeout=self._timeout(30000))
            logger.info("搜索完成")
        except Exception as e:
            logger.error(f"搜索失败: {e}")

    async def export_and_download(self, task_name: str) -> str | None:
        """执行导出并下载：点确定 → 等Chrome下载完成 → 点Close"""

        # Step 1: 点击顶部导出按钮
        try:
            export_btn = self.page.get_by_role("button", name="导出")
            await export_btn.wait_for(state="visible", timeout=self._timeout(10000))
            await export_btn.click()
            logger.info("已点击导出")
        except Exception:
            raise ExportError("导出按钮不可用（可能查询无结果或页面未加载）")

        await asyncio.sleep(2)

        # Step 2: 点击 footer 导出按钮（确认弹窗）
        try:
            footer_export = self.page.locator("#u_mdf_workbench_footer").get_by_role(
                "button", name="导出", exact=True
            )
            await footer_export.wait_for(state="visible", timeout=self._timeout(10000))
            await footer_export.click()
            logger.info("已确认导出")
        except Exception:
            raise ExportError("确认导出按钮不可用（弹窗可能未弹出）")

        await asyncio.sleep(2)

        # Step 3: 找到确定按钮（headless 模式下尝试多种选择器）
        confirm_btn = None
        for strategy in [
            lambda: self.page.get_by_role("button", name="确定"),
            lambda: self.page.locator("button:has-text('确定')"),
            lambda: self.page.locator(".ant-btn-primary:has-text('确定')"),
            lambda: self.page.locator("[class*='modal'] button:has-text('确定')"),
        ]:
            try:
                btn = strategy()
                if await btn.first.is_visible(timeout=8000):
                    confirm_btn = btn.first
                    logger.info("找到确定按钮")
                    break
            except Exception:
                continue

        if not confirm_btn:
            debug_path = self.download_dir / f"debug_export_{datetime.now().strftime('%H%M%S')}.png"
            await self.page.screenshot(path=str(debug_path), full_page=True)
            logger.error(f"未找到确定按钮，截图: {debug_path}")
            return None

        # Step 4: 点击确定并等待下载
        try:
            async with self.page.expect_download(timeout=self._timeout(600000)) as dl_info:
                await confirm_btn.click()
                logger.info("已确定，等待Chrome下载...")

            download = await dl_info.value
            logger.info(f"下载已开始: {download.suggested_filename}")

            # Step 5: 保存文件到日期子目录
            filename = download.suggested_filename
            if not filename:
                filename = f"{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            date_dir = self.download_dir / datetime.now().strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            save_path = date_dir / filename
            await download.save_as(str(save_path))
            logger.info(f"已下载: {save_path}")

            # Step 6: 关闭弹窗
            try:
                for close_name in ["Close", "关闭", "确定"]:
                    try:
                        close_btn = self.page.get_by_role("button", name=close_name)
                        if await close_btn.is_visible(timeout=2000):
                            await close_btn.click()
                            logger.info(f"已关闭弹窗('{close_name}')")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            return str(save_path)

        except Exception as e:
            logger.error(f"导出失败: {e}")
            return None

    async def download_module(self, module_name: str) -> tuple:
        """
        下载单个模块的完整流程
        Returns: (file_path, error_message) - 成功时 error_message 为 None
        """
        config = MODULE_CONFIG.get(module_name)
        if not config:
            return None, f"未知模块: {module_name}"

        logger.info(f"开始下载模块: {module_name}")

        # 返回首页
        try:
            await self.go_home()
            await asyncio.sleep(1)
        except Exception as e:
            return None, f"返回首页失败: {str(e)[:100]}"

        # 打开模块
        try:
            if not await self.open_module(module_name):
                return None, f"无法打开模块「{module_name}」，收藏夹中未找到"
        except Exception as e:
            return None, f"打开模块「{module_name}」失败: {str(e)[:100]}"

        # 展开筛选
        if config.get("has_expand"):
            try:
                expand_btn = self.page.get_by_role("button", name="展开")
                await expand_btn.wait_for(state="visible", timeout=self._timeout(10000))
                await expand_btn.click()
                await asyncio.sleep(2)
                logger.info("已展开筛选条件")
            except Exception as e:
                logger.warning(f"展开按钮: {e}")

        # 日期筛选
        if config.get("has_date_filter"):
            try:
                await self.set_date_filter()
            except Exception as e:
                return None, f"设置日期筛选失败: {str(e)[:100]}"

        # 搜索
        if config.get("has_search") and config.get("search_button_id"):
            try:
                await self.click_search(config["search_button_id"])
            except Exception as e:
                return None, f"点击查询按钮失败: {str(e)[:100]}"

        # 导出下载
        try:
            file_path = await self.export_and_download(module_name)
            if file_path:
                return file_path, None
            return None, "导出下载失败，未收到文件（可能无数据或导出按钮不可用）"
        except ExportError as e:
            return None, str(e)
        except Exception as e:
            return None, f"导出下载异常: {str(e)[:150]}"

    async def run_all(self, modules: list[str], username: str, password: str, login_url: str,
                      on_module_done: "callable | None" = None) -> dict:
        """
        执行所有模块下载，返回结果字典
        {module_name: {"success": bool, "file": str|None, "error": str|None, "duration": int}}

        on_module_done(module_name, result_dict): 每个模块完成后回调（在事件循环内同步调用）
        """
        results = {}
        try:
            await self.start()
        except Exception as e:
            err_msg = f"浏览器启动失败: {str(e)[:150]}"
            for m in modules:
                results[m] = {"success": False, "file": None, "error": err_msg, "duration": 0}
            return results

        try:
            await self.login(login_url, username, password)
        except LoginError as e:
            err_msg = e.message
            if e.cause:
                err_msg += f"（{e.cause}）"
            for m in modules:
                results[m] = {"success": False, "file": None, "error": err_msg, "duration": 0}
            self._last_results = results
            await self.close()
            return results
        except Exception as e:
            err_msg = f"登录异常: {str(e)[:150]}"
            for m in modules:
                results[m] = {"success": False, "file": None, "error": err_msg, "duration": 0}
            self._last_results = results
            await self.close()
            return results

        for module_name in modules:
            if module_name not in MODULE_CONFIG:
                result = {"success": False, "file": None, "error": f"未知模块: {module_name}", "duration": 0}
                results[module_name] = result
                if on_module_done:
                    on_module_done(module_name, result)
                continue

            import time
            t0 = time.time()
            file_path, error_msg = await self.download_module(module_name)
            duration = int(time.time() - t0)
            result = {
                "success": file_path is not None,
                "file": file_path,
                "error": error_msg,
                "duration": duration,
            }
            results[module_name] = result

            # 每个模块完成后立即回调
            if on_module_done:
                on_module_done(module_name, result)

            await asyncio.sleep(2)

        self._last_results = results
        await self.close()
        return results


def cleanup_old_downloads(download_dir: str, keep_days: int = 7):
    """清理超过 N 天的下载文件"""
    base = Path(download_dir)
    if not base.exists():
        return

    now = datetime.now()
    for date_dir in base.iterdir():
        if not date_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            if (now - dir_date).days > keep_days:
                import shutil
                shutil.rmtree(date_dir)
                logger.info(f"已清理过期目录: {date_dir.name}")
        except ValueError:
            continue
