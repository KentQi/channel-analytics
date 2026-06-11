"""openpyxl 兼容补丁(对应原仓 rpa_service.py L20-50)。

某些 ERP 导出的 Excel 文件含 `name=None` 的 `_NamedCellStyle`,openpyxl
会抛 `name should be str`。本模块提供一个 monkey-patch:
  - 模块导入时自动 patch
  - apply_openpyxl_compat() 可重复调用做热修补
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def apply_openpyxl_compat() -> None:
    """修补 openpyxl.styles.named_styles._NamedCellStyle,允许 name=None。"""
    global _PATCHED
    try:
        from openpyxl.styles import named_styles as _ns
        if getattr(_ns._NamedCellStyle.__init__, "_patched", False):
            return
        _orig = _ns._NamedCellStyle.__init__

        def _patched(self, name=None, **kw):
            if name is None:
                name = "Normal"
            _orig(self, name=name, **kw)

        _patched._patched = True  # type: ignore[attr-defined]
        _ns._NamedCellStyle.__init__ = _patched
        _PATCHED = True
    except Exception as e:
        logger.warning("openpyxl 兼容补丁失败(不影响主流程): %s", e)


def safe_read_excel(path: str | Path):
    """读 Excel,遇到 openpyxl name 异常时自动热修补再读一次。

    返回 pandas.DataFrame(对齐原仓 _safe_read_excel L33-52)。
    """
    import pandas as pd

    try:
        return pd.read_excel(path)
    except (TypeError, Exception) as e:  # noqa: BLE001
        msg = str(e)
        if "name should be" in msg or "_NamedCellStyle" in msg:
            apply_openpyxl_compat()
            return pd.read_excel(path)
        raise


# 模块导入时自动修补一次
apply_openpyxl_compat()


__all__ = ["apply_openpyxl_compat", "safe_read_excel"]