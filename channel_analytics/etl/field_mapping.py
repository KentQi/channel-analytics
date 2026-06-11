"""字段映射(对应原仓 field_mapping.py,通用化)。

设计:
  - 用户通过 YAML/JSON 注入映射(避免硬编码中文列名进开源仓)
  - 提供 forward / reverse 双向查找 + DataFrame rename 工具函数
  - rename_for_display 改名但保留原列(用于前端展示时把英文翻回中文)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------

def load_mapping(source: str | Path | dict) -> dict[str, str]:
    """从 JSON/YAML 文件或 dict 加载 forward 映射(中文 -> 英文)。"""
    if isinstance(source, dict):
        return {str(k): str(v) for k, v in source.items()}
    path = Path(source)
    if not path.exists():
        return {}
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
            data = yaml.safe_load(text) or {}
            return {str(k): str(v) for k, v in data.items()}
        except ImportError:
            return {}
    if suffix == ".json":
        data = json.loads(text) if text.strip() else {}
        return {str(k): str(v) for k, v in data.items()}
    return {}


def build_reverse_map(forward_map: dict[str, str]) -> dict[str, str]:
    """从 forward(中文->英文)构造 reverse(英文->中文)。"""
    out: dict[str, str] = {}
    for k, v in forward_map.items():
        # 冲突时后者覆盖前者(便于后续覆盖)
        out[str(v)] = str(k)
    return out


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------

def rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """重命名列(只重命名 mapping 中存在的列,其他保留)。"""
    cols_to_rename = {c: mapping[c] for c in df.columns if c in mapping}
    return df.rename(columns=cols_to_rename)


def rename_for_display(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """改名用于前端展示(英文 → 中文),不改原 df。

    与 rename_columns 不同:不存在的列保持原样;返回新 DataFrame。
    """
    reverse = build_reverse_map(mapping)
    return rename_columns(df, reverse)


# ---------------------------------------------------------------------------
# 推断(辅助工具,从 DataFrame 推断建议的映射)
# ---------------------------------------------------------------------------

def suggest_mapping_from_columns(columns: list[str]) -> dict[str, str]:
    """从列名推断建议的英文映射(简单的 snake_case 转换)。

    示例:
      "物料编码" → "material_code"  (无法识别,返回原名)
      "Brand Name" → "brand_name"
      "Sales Qty (90d)" → "sales_qty_90d"
    """
    out: dict[str, str] = {}
    for c in columns:
        if not c or not c.strip():
            continue
        if _is_already_english(c):
            out[c] = c.lower().replace(" ", "_")
        else:
            # 中文/混合 — 不自动翻译(避免瞎猜),保留原名
            out[c] = c
    return out


def _is_already_english(s: str) -> bool:
    """粗判:字符串中 ASCII 字母 + 数字 / 下划线 占比 >= 80%。"""
    if not s:
        return False
    ascii_count = sum(1 for ch in s if ch.isascii() and (ch.isalnum() or ch == "_"))
    return ascii_count / len(s) >= 0.8


__all__ = [
    "load_mapping",
    "build_reverse_map",
    "rename_columns",
    "rename_for_display",
    "suggest_mapping_from_columns",
]