"""三维权限服务(对应原仓 permission_service.py 平移)。

三维结构:
  - modules: list[str]       — 该 role 可访问的功能模块名
  - sales_tabs: list[str]|None — 销售 Tab 过滤,None = 全部
  - regions: list[str]|None   — 区域过滤,None = 全部

存储: role_permission 表(role, permission_type, permission_value, module_ext)

兼容:
  - SQLAlchemy Session(主路径)
  - 原生 DB-API cursor(回退,部署期遗留代码)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class Permission:
    """单条权限记录(对应 role_permission 一行)。"""
    role: str
    permission_type: str  # module / sales_tab / region
    permission_value: str | None = None
    module_ext: str | None = None


@dataclass
class RolePermissions:
    """三维权限聚合结果。"""
    modules: list[str] = field(default_factory=list)
    sales_tabs: list[str] | None = None
    regions: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "modules": list(self.modules),
            "sales_tabs": list(self.sales_tabs) if self.sales_tabs is not None else None,
            "regions": list(self.regions) if self.regions is not None else None,
        }


# ---------------------------------------------------------------------------
# 加载
# ---------------------------------------------------------------------------

def load_role_permissions(
    db: Any,
    role: str,
) -> RolePermissions:
    """从 role_permission 表读 role 的三维权限。"""
    result = RolePermissions()
    rows = _execute(db, _SQL_LOAD, {"role": role})
    for ptype, pval, module_ext in rows:
        if ptype == "module" and module_ext:
            result.modules.append(module_ext)
        elif ptype == "sales_tab":
            result.sales_tabs = _parse_json(pval)
        elif ptype == "region":
            result.regions = _parse_json(pval)
    return result


def check_role_exists(db: Any, role: str) -> bool:
    """role 在 role_permission 表是否存在(任何 permission_type 都算)。"""
    rows = _execute(db, _SQL_EXISTS, {"role": role})
    return len(rows) > 0


def get_all_roles(db: Any) -> list[str]:
    """返回所有 role 名(DISTINCT)。"""
    rows = _execute(db, _SQL_ALL_ROLES, {})
    return [r[0] for r in rows]


def update_role_permissions(
    db: Any,
    role: str,
    permissions: RolePermissions | dict[str, Any],
) -> None:
    """覆盖式更新 role 的权限(原仓是 DELETE + INSERT)。"""
    if isinstance(permissions, dict):
        permissions = RolePermissions(
            modules=list(permissions.get("modules", [])),
            sales_tabs=permissions.get("sales_tabs"),
            regions=permissions.get("regions"),
        )

    # DELETE 现有
    _execute(db, _SQL_DELETE_ROLE, {"role": role})

    # INSERT modules
    for m in permissions.modules:
        _execute(db, _SQL_INSERT_MODULE, {"role": role, "module_ext": m})

    # INSERT sales_tabs
    if permissions.sales_tabs is not None:
        _execute(
            db,
            _SQL_INSERT_VALUE,
            {"role": role, "ptype": "sales_tab", "pval": json.dumps(permissions.sales_tabs, ensure_ascii=False)},
        )

    # INSERT regions
    if permissions.regions is not None:
        _execute(
            db,
            _SQL_INSERT_VALUE,
            {"role": role, "ptype": "region", "pval": json.dumps(permissions.regions, ensure_ascii=False)},
        )

    _commit(db)


# ---------------------------------------------------------------------------
# SQL 模板 + DB-API 适配
# ---------------------------------------------------------------------------

_SQL_LOAD = """
    SELECT permission_type, permission_value, module_ext
    FROM role_permission WHERE role = :role
"""
_SQL_EXISTS = """
    SELECT 1 FROM role_permission WHERE role = :role LIMIT 1
"""
_SQL_ALL_ROLES = """
    SELECT DISTINCT role FROM role_permission ORDER BY role
"""
_SQL_DELETE_ROLE = "DELETE FROM role_permission WHERE role = :role"
_SQL_INSERT_MODULE = """
    INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
    VALUES (:role, 'module', 'module', NULL, :module_ext)
"""
_SQL_INSERT_VALUE = """
    INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
    VALUES (:role, :ptype, :ptype, :pval, NULL)
"""


def _execute(db: Any, sql: str, params: dict[str, Any]) -> list[tuple]:
    """执行 SQL,返回 fetchall 结果行。

    兼容:
      - SQLAlchemy Session(db.execute(text(sql), params).fetchall())
      - 原生 cursor(db.execute(sql, params).fetchall())
      - 内存 stub(用于测试)— 暴露 _permissions_fake 或直接有 execute() 方法
    """
    # 内存 stub 优先:有 fake 对象走 fake,没有走 SQLAlchemy
    fake = getattr(db, "_permissions_fake", None)
    if fake is not None:
        return fake.execute(sql, params)

    # SQLAlchemy 2.x: db.execute(text(sql), params)
    try:
        from sqlalchemy import text
        result = db.execute(text(sql), params)
        return list(result.fetchall())
    except (TypeError, ImportError, AttributeError):
        pass

    # 原生 cursor / DB-API
    result = db.execute(sql, params)
    return list(result.fetchall())


def _commit(db: Any) -> None:
    if hasattr(db, "commit"):
        try:
            db.commit()
        except Exception:
            pass


def _parse_json(val: str | None) -> list[str] | None:
    if val is None:
        return None
    try:
        data = json.loads(val)
        if isinstance(data, list):
            return [str(x) for x in data]
    except (json.JSONDecodeError, TypeError):
        pass
    return None


__all__ = [
    "Permission",
    "RolePermissions",
    "load_role_permissions",
    "check_role_exists",
    "get_all_roles",
    "update_role_permissions",
]