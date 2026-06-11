"""
Excel reading utilities — 对齐原版 utils/excel.py 的三级降级 + openpyxl patch + 垃圾行检测 + 合计行清理
"""
import os
import re
import warnings
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict

import pandas as pd

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

_OPENPYXL_PATCH_DONE = False


def _patch_openpyxl_once():
    """仅执行一次的 openpyxl 样式 patch，避免 NamedStyle 崩溃"""
    global _OPENPYXL_PATCH_DONE
    if _OPENPYXL_PATCH_DONE:
        return
    _OPENPYXL_PATCH_DONE = True
    try:
        from openpyxl.descriptors.base import Typed
        # Patch ALL Typed descriptors to allow None for str type
        for _mod_name in ['openpyxl.styles', 'openpyxl.styles.named_styles', 'openpyxl.styles.table']:
            try:
                _mod = __import__(_mod_name, fromlist=[''])
                for _cls_name in dir(_mod):
                    _cls = getattr(_mod, _cls_name, None)
                    if isinstance(_cls, type) and hasattr(_cls, '__dict__'):
                        for _attr, _desc in _cls.__dict__.items():
                            if isinstance(_desc, Typed) and _desc.expected_type is str and not _desc.allow_none:
                                _desc.allow_none = True
            except Exception:
                pass

        # Direct patch: allow None name in NamedCellStyle
        try:
            from openpyxl.styles.named_styles import NamedCellStyle, _NamedCellStyle
            for _cls in [NamedCellStyle, _NamedCellStyle]:
                if hasattr(_cls, '__dict__') and 'name' in _cls.__dict__:
                    _desc = _cls.__dict__['name']
                    if isinstance(_desc, Typed):
                        _desc.allow_none = True
        except Exception:
            pass

        # Patch _NamedCellStyle to handle None name in __init__
        try:
            from openpyxl.styles.named_styles import _NamedCellStyle
            _original_init = _NamedCellStyle.__init__
            def _safe_init(self, *args, **kwargs):
                _original_init(self, *args, **kwargs)
                # Check all name-related attributes
                for _attr in dir(self):
                    if 'name' in _attr.lower():
                        try:
                            _val = getattr(type(self), _attr, None)
                            if isinstance(_val, property):
                                _cur = getattr(self, _attr)
                                if _cur is None:
                                    setattr(self, _attr, "")
                        except Exception:
                            pass
                # Also check private name attribute directly
                if hasattr(self, '_name') and self._name is None:
                    self._name = ""
                if hasattr(self, '_NamedCellStyle__name') and self._NamedCellStyle__name is None:
                    self._NamedCellStyle__name = ""
            _NamedCellStyle.__init__ = _safe_init
        except Exception:
            pass

        # Patch NamedStyle.__init__
        try:
            from openpyxl.styles.named_styles import NamedStyle
            from openpyxl.descriptors.base import Bool as BoolDesc
            _original_ns_init = NamedStyle.__init__
            def _safe_ns_init(self, *args, **kwargs):
                _original_ns_init(self, *args, **kwargs)
                # Ensure _NamedCellStyle__name is not None
                if hasattr(self, '_NamedCellStyle__name') and self._NamedCellStyle__name is None:
                    self._NamedCellStyle__name = ""
            NamedStyle.__init__ = _safe_ns_init
        except Exception:
            pass

        # Patch openpyxl cell style assignment to handle None name
        try:
            import openpyxl.cell
            from openpyxl.cell import Cell
            _original_cell_init = Cell.__init__
            def _safe_cell_init(self, *args, **kwargs):
                _original_cell_init(self, *args, **kwargs)
                # Ensure style-related attributes don't cause issues
                if hasattr(self, '_style') and self._style is None:
                    self._style = ""
            Cell.__init__ = _safe_cell_init
        except Exception:
            pass

        # Monkey-patch openpyxl's style loading to skip invalid NamedCellStyles
        try:
            import openpyxl.styles
            _orig_from_tree = getattr(openpyxl.styles, '_styleable_from_tree', None)
            if _orig_from_tree:
                def _safe_from_tree(tag, styles):
                    try:
                        return _orig_from_tree(tag, styles)
                    except (TypeError, ValueError):
                        return None
                openpyxl.styles._styleable_from_tree = _safe_from_tree
        except Exception:
            pass

        # Critical: Patch the descriptor validation itself
        try:
            from openpyxl.descriptors.base import Convertible, Typed, Bool as BoolDesc
            import openpyxl.descriptors.base as _base

            # Patch _convert function directly in the module
            if hasattr(_base, '_convert'):
                _original_convert = _base._convert
                def _safe_convert(expected_type, value):
                    if value is None:
                        return value
                    # Handle Bool to int conversion
                    if expected_type is int and isinstance(value, BoolDesc):
                        try:
                            v = value._value
                            if v is None:
                                return 0
                            if isinstance(v, bool):
                                return 1 if v else 0
                            return int(v)
                        except Exception:
                            return 0
                    if not isinstance(value, expected_type):
                        try:
                            value = expected_type(value)
                        except:
                            raise TypeError('expected ' + str(expected_type))
                    return value
                _base._convert = _safe_convert

            # Also patch Typed.__set__ to handle Bool to int and None str
            _original_typed_set = Typed.__set__
            def _safe_typed_set(self, instance, value):
                if value is None and self.allow_none:
                    instance.__dict__[self.name] = value
                    return
                # Handle None value for str type - convert to empty string
                if value is None and self.expected_type is str:
                    value = ""
                # Handle Bool to int conversion
                if self.expected_type is int and isinstance(value, BoolDesc):
                    try:
                        v = value._value
                        if v is None:
                            return
                        if isinstance(v, bool):
                            value = 1 if v else 0
                        else:
                            value = int(v)
                    except Exception:
                        return
                if not isinstance(value, self.expected_type):
                    if (not self.allow_none or (self.allow_none and value is not None)):
                        msg = f"{instance.__class__}.{self.name} should be {self.expected_type} but value is {type(value)}"
                        raise TypeError(msg)
                instance.__dict__[self.name] = value
            Typed.__set__ = _safe_typed_set

            # Also patch Convertible.__set__ to handle None str
            _original_convertible_set = Convertible.__set__
            def _safe_convertible_set(self, instance, value):
                if value is None and self.allow_none:
                    instance.__dict__[self.name] = value
                    return
                # Handle None value for str type - convert to empty string
                if value is None and self.expected_type is str:
                    value = ""
                # Handle Bool to int conversion
                if self.expected_type is int and isinstance(value, BoolDesc):
                    try:
                        v = value._value
                        if v is None:
                            return
                        if isinstance(v, bool):
                            value = 1 if v else 0
                        else:
                            value = int(v)
                    except Exception:
                        return
                if ((self.allow_none and value is not None) or not self.allow_none):
                    value = _base._convert(self.expected_type, value)
                instance.__dict__[self.name] = value
            Convertible.__set__ = _safe_convertible_set
        except Exception:
            pass

        # Critical: Patch Text.content to handle NestedText in join()
        try:
            from openpyxl.cell.text import Text
            _original_content_getter = Text.content.fget
            def _safe_content_getter(self):
                try:
                    return _original_content_getter(self)
                except TypeError as e:
                    if "NestedText" in str(e) or "expected str instance" in str(e):
                        # Handle NestedText by converting each item to string
                        snippets = []
                        if self.plain is not None:
                            snippets.append(str(self.plain) if hasattr(self.plain, '__str__') else self.plain)
                        for block in (self.formatted or []):
                            if block.t is not None:
                                snippets.append(str(block.t) if hasattr(block.t, '__str__') else block.t)
                        return u"".join(snippets)
                    raise
            Text.content = property(_safe_content_getter, Text.content.fset)
        except Exception:
            pass

        # Also patch NestedText itself to be string-like
        try:
            from openpyxl.cell.text import NestedText
            _original_str = NestedText.__str__
            def _safe_str(self):
                try:
                    return _original_str(self)
                except Exception:
                    return str(self._value) if hasattr(self, '_value') else u""
            NestedText.__str__ = _safe_str
        except Exception:
            pass

        # Patch CellStyle.to_array to handle Bool values
        try:
            from openpyxl.styles.cell_style import CellStyle, ArrayDescriptor, StyleArray
            from openpyxl.descriptors.base import Bool

            # Helper to convert Bool to int
            def _bool_to_int(value):
                if value is None:
                    return 0
                if isinstance(value, Bool):
                    # Extract the actual value from Bool descriptor
                    try:
                        v = value._value
                        if v is None:
                            return 0
                        if isinstance(v, bool):
                            return 1 if v else 0
                        return int(v) if v else 0
                    except Exception:
                        return 0
                if hasattr(value, '__int__') and not isinstance(value, int):
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        return 0
                return value

            # Patch ArrayDescriptor.__set__ to convert Bool to int
            _original_arr_set = ArrayDescriptor.__set__
            def _safe_arr_set(self, instance, value):
                value = _bool_to_int(value)
                _original_arr_set(self, instance, value)
            ArrayDescriptor.__set__ = _safe_arr_set

            # Also patch StyleArray.__setitem__ directly
            _original_style_setitem = StyleArray.__setitem__
            def _safe_style_setitem(self, key, value):
                value = _bool_to_int(value)
                _original_style_setitem(self, key, value)
            StyleArray.__setitem__ = _safe_style_setitem

            # Patch CellStyle.to_array to handle Bool values
            _original_to_array = CellStyle.to_array
            def _safe_to_array(self):
                style = StyleArray()
                for k in ("fontId", "fillId", "borderId", "numFmtId", "pivotButton",
                          "quotePrefix", "xfId"):
                    v = getattr(self, k, 0)
                    v = _bool_to_int(v)
                    if v is not None:
                        setattr(style, k, v)
                return style
            CellStyle.to_array = _safe_to_array
        except Exception:
            pass

    except Exception:
        pass


def _read_excel_from_zip(buf):
    """纯 zipfile 解析器：处理 inlineStr 类型的单元格"""
    import zipfile
    try:
        with zipfile.ZipFile(buf, 'r') as zin:
            shared = []
            if 'xl/sharedStrings.xml' in zin.namelist():
                sst = zin.read('xl/sharedStrings.xml').decode('utf-8')
                for m in re.finditer(r'<si>(.*?)</si>', sst, re.DOTALL):
                    content = m.group(1)
                    t = re.search(r'<t[^>]*>(.*?)</t>', content)
                    shared.append(t.group(1) if t else '')
            sheet_xml = None
            for item in zin.namelist():
                if re.match(r'xl/worksheets/sheet1\.xml', item):
                    sheet_xml = zin.read(item).decode('utf-8')
                    break
            if not sheet_xml:
                return None
            rows_data = []
            for _rn, row_xml in re.finditer(r'<row[^>]*r="(\d+)"[^>]*>(.*?)</row>', sheet_xml, re.DOTALL):
                row_vals = []
                for _ca, cc in re.finditer(r'<c([^>]*)>(.*?)</c>', row_xml, re.DOTALL):
                    v = re.search(r'<v>(.*?)</v>', cc)
                    if v:
                        row_vals.append(shared[int(v.group(1))] if 't="s"' in _ca and shared else v.group(1))
                    else:
                        ist = re.search(r'<is><t[^>]*>(.*?)</t></is>', cc)
                        row_vals.append(ist.group(1) if ist else '')
                rows_data.append(row_vals)
            if not rows_data:
                return None
            max_cols = max(len(r) for r in rows_data)
            return pd.DataFrame([r + [''] * (max_cols - len(r)) for r in rows_data])
    except Exception:
        return None


def _clean_合计(df):
    """删除合计行（首列值为 '合计' 的行，不限位置）"""
    rows_to_delete = []
    for idx, row in df.iterrows():
        cell = row.iloc[0]
        val = str(cell).strip() if not pd.isna(cell) else ""
        if val == "合计":
            rows_to_delete.append(idx)
    return df.drop(rows_to_delete).reset_index(drop=True) if rows_to_delete else df


def _read_excel_safe(src, sheet_type=None):
    """
    三级降级读取 Excel，对齐原版 utils/excel._read_excel_safe。

    策略：
    1. header=0 标准读取，列名正常则直接返回（删合计行）
    2. header=None 处理有垃圾标题行的文件
    3. zipfile XML 解析兜底

    Args:
        src: 文件路径(str) 或 file-like 对象
        sheet_type: 源文件类型（"请购单"/"采购单"/"入库单"/"销售出库单"/"现存量"），
                    用于决定是否清理合计行和垃圾行
    """
    warnings.simplefilter("ignore")

    if hasattr(src, 'read'):
        src.seek(0)
        data = src.read()
    else:
        with open(src, 'rb') as f:
            data = f.read()

    buf = BytesIO(data)
    _patch_openpyxl_once()

    # ---- 尝试 1：header=0 ----
    try:
        df = pd.read_excel(buf, engine="openpyxl", header=0)
    except Exception:
        df = None

    if df is not None and not df.empty:
        if df.columns.dtype.kind == 'O':
            has_unnamed = any(str(c).startswith("Unnamed") for c in df.columns)
            if has_unnamed:
                df = None
            else:
                nan_ratio = sum(1 for c in df.columns if pd.isna(c)) / len(df.columns)
                if nan_ratio > 0.5:
                    df = None
                else:
                    if sheet_type in ("入库单", "销售出库单", "现存量", "请购单", "采购单"):
                        df = _clean_合计(df)
                    return df
        else:
            df = None

    # ---- 尝试 2：header=None ----
    buf.seek(0)
    try:
        df = pd.read_excel(buf, engine="openpyxl", header=None)
    except Exception:
        df = _read_excel_from_zip(buf)

    if df is None or df.empty:
        raise ValueError("无法读取 Excel 文件")

    first_cell = str(df.iloc[0, 0]).strip() if not pd.isna(df.iloc[0, 0]) else ""

    # 检测垃圾标题行
    row0 = df.iloc[0]
    row0_non_null = row0.notna().sum()
    row0_total = len(row0)
    is_sparse_header = row0_total > 0 and (row0_non_null / row0_total) < 0.2 and row0_non_null <= 2

    has_junk_header = (first_cell == "存量分析头") or first_cell.startswith("Unnamed:") or is_sparse_header

    if has_junk_header:
        true_col_names = df.iloc[1].tolist()
        df = df.iloc[2:].reset_index(drop=True)
        df.columns = true_col_names
    else:
        if df.columns.dtype.kind == 'i':
            true_col_names = df.iloc[0].tolist()
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = true_col_names

    if sheet_type in ("入库单", "销售出库单", "现存量"):
        df = _clean_合计(df)

    return df


# ============================================================
# 统一入口
# ============================================================

def read_excel_file(file_path: str, sheet_names=None) -> Dict[str, pd.DataFrame]:
    """
    统一读取入口。支持单 sheet 或全部 sheets。

    Args:
        file_path: 文件路径
        sheet_names: 可选 sheet 名列表，None 则读全部

    Returns:
        {sheet_name: DataFrame} 字典
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    # Apply openpyxl patch before any Excel operations
    _patch_openpyxl_once()

    try:
        if sheet_names is None:
            xl = pd.ExcelFile(file_path)
            # 确保 sheet_names 是字符串列表
            sheet_names = [str(s) if s is not None else f"Sheet{i+1}" for i, s in enumerate(xl.sheet_names)]

        result = {}
        for sheet in sheet_names:
            # Read each specific sheet with safe fallback
            sheet_str = str(sheet) if sheet is not None else "Sheet"
            logger.info(f"Reading sheet: {sheet_str} from {file_path}")
            df = _read_single_sheet_safe(str(file_path), sheet_str)
            result[sheet_str] = df

        return result
    except Exception as e:
        import traceback
        logger.error(f"Failed to read Excel file: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def _read_single_sheet_safe(file_path: str, sheet_name: str) -> pd.DataFrame:
    """安全读取单个 sheet，带错误处理"""
    _patch_openpyxl_once()

    # 尝试方法1：标准读取
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl", header=0)
        if _is_valid_df(df):
            return df
    except Exception as e:
        logger.warning(f"Sheet {sheet_name} read failed with header=0: {e}")

    # 尝试方法2：无表头读取
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl", header=None)
        if not df.empty:
            # 检测真正的表头行
            df = _detect_and_fix_header(df)
            return df
    except Exception as e:
        logger.warning(f"Sheet {sheet_name} read failed with header=None: {e}")

    # 尝试方法3：xlrd 引擎
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd')
        if _is_valid_df(df):
            return df
    except Exception:
        pass

    # 方法4：使用 _read_excel_safe 兜底
    return _read_excel_safe(file_path, sheet_type=sheet_name)


def _is_valid_df(df: pd.DataFrame) -> bool:
    """检查 DataFrame 是否有效"""
    if df is None or df.empty:
        return False
    if df.columns.dtype.kind == 'O':
        has_unnamed = any(str(c).startswith("Unnamed") for c in df.columns)
        if has_unnamed:
            return False
        nan_ratio = sum(1 for c in df.columns if pd.isna(c)) / len(df.columns) if len(df.columns) > 0 else 0
        if nan_ratio > 0.5:
            return False
    return True


def _detect_and_fix_header(df: pd.DataFrame) -> pd.DataFrame:
    """检测并修复表头"""
    if df.empty:
        return df

    first_cell = str(df.iloc[0, 0]).strip() if not pd.isna(df.iloc[0, 0]) else ""

    # 检测垃圾标题行
    row0 = df.iloc[0]
    row0_non_null = row0.notna().sum()
    row0_total = len(row0)
    is_sparse_header = row0_total > 0 and (row0_non_null / row0_total) < 0.2 and row0_non_null <= 2

    has_junk_header = (first_cell == "存量分析头") or first_cell.startswith("Unnamed:") or is_sparse_header

    if has_junk_header:
        true_col_names = df.iloc[1].tolist()
        df = df.iloc[2:].reset_index(drop=True)
        df.columns = true_col_names
    else:
        if df.columns.dtype.kind == 'i':
            true_col_names = df.iloc[0].tolist()
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = true_col_names

    return df


def read_single_sheet(file_path: str, sheet_type: str = None) -> pd.DataFrame:
    """
    读取单个 sheet（带 sheet_type 清理）。

    Args:
        file_path: 文件路径
        sheet_type: 源文件类型，用于决定清理规则

    Returns:
        DataFrame
    """
    return _read_excel_safe(str(file_path), sheet_type=sheet_type)
