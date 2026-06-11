"""auth 包 — 认证与权限(三维权限:moudules / sales_tabs / regions)。

对应原仓 permission_service.py 平移:
  - 三维权限,role -> {modules: [], sales_tabs: None|list, regions: None|list}
  - load / check / get_all / update

新仓改进:
  - SQLAlchemy ORM 风格 + 同步 / 异步两种 session 兼容
  - 不含具体模块名(由部署方配置 role_permission 表)
  - 支持内存 fallback(无 ORM session 时)
"""
from channel_analytics.auth.permissions import (
    Permission,
    RolePermissions,
    check_role_exists,
    get_all_roles,
    load_role_permissions,
    update_role_permissions,
)

__all__ = [
    "Permission",
    "RolePermissions",
    "load_role_permissions",
    "check_role_exists",
    "get_all_roles",
    "update_role_permissions",
]