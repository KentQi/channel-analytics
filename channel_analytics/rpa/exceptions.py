"""RPA 异常体系(对应原仓 rpa_engine.py L15-58)。"""
from __future__ import annotations


class RpaError(Exception):
    """RPA 框架基础异常。"""


class LoginError(RpaError):
    """登录失败(账号错 / 验证码 / iframe 找不到)。"""


class NavigateError(RpaError):
    """导航到模块失败(菜单未展开 / iframe 切错 / 模块不存在)。"""


class SearchError(RpaError):
    """点击查询按钮后未触发下载或结果超时。"""


class ExportError(RpaError):
    """导出失败(下载未触发 / 文件损坏 / 文件名异常)。"""


__all__ = ["RpaError", "LoginError", "NavigateError", "SearchError", "ExportError"]