"""RPA adapter 实现集合。

本仓只保留一个 no-op 模板(example_minimal.py),不绑定任何具体 ERP 厂商。

具体厂商接入:
  1. 在用户自己的包里继承 ErpAdapter,实现 5 个钩子
  2. 通过 pyproject.toml entry_points 注册:
     [project.entry-points."channel_analytics.rpa_adapters"]
     my_erp = "my_pkg.my_module:MyAdapter"
  3. 安装后通过 settings.rpa_adapter 或 RPA_ADAPTER 环境变量指定
"""
from channel_analytics.rpa.adapters.example_minimal import ExampleMinimalAdapter

__all__ = ["ExampleMinimalAdapter"]