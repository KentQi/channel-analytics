"""ETL 共享类型(被 pipeline.py 和 steps/*.py 共同依赖,避免循环导入)。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

import pandas as pd


@dataclass
class EtlContext:
    """一次 ETL 运行期间的共享状态(对应原仓函数间传递的 DataFrame 集合)。"""
    raw_data: dict[str, pd.DataFrame] = field(default_factory=dict)
    stg: dict[str, pd.DataFrame] = field(default_factory=dict)        # 5 张 STG
    rpt: dict[str, pd.DataFrame] = field(default_factory=dict)        # 7 张 RPT
    extras: dict[str, pd.DataFrame] = field(default_factory=dict)     # rpt_sales_out_wide 等
    meta: dict[str, Any] = field(default_factory=dict)                # current_date / brand_provider / ...


class Step(ABC):
    """ETL 单个步骤。所有步骤都接收 EtlContext,原地修改 ctx 并返回。"""
    name: ClassVar[str] = ""

    @abstractmethod
    def run(self, ctx: EtlContext) -> EtlContext:
        raise NotImplementedError


class Loader(Step):
    """读取原始数据 → ctx.raw_data / ctx.stg。"""


class Transformer(Step):
    """ctx.stg / ctx.raw_data → ctx.stg / ctx.rpt。"""


class Writer(Step):
    """ctx.rpt / ctx.stg 写入 DB。开源仓默认 no-op(W4+ 接入 SQLAlchemy)。"""


__all__ = ["EtlContext", "Step", "Loader", "Transformer", "Writer"]
