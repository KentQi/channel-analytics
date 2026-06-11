"""W2补 auth/permissions 单测。"""
from __future__ import annotations

from typing import Any

import pytest

from channel_analytics.auth.permissions import (
    Permission,
    RolePermissions,
    check_role_exists,
    get_all_roles,
    load_role_permissions,
    update_role_permissions,
)


class _FakeDB:
    """最小 DB stub:支持 _permissions_fake 走 + 内存存储。"""

    def __init__(self) -> None:
        # rows: list[(role, ptype, pval, module_ext)]
        self.rows: list[tuple[str, str, str | None, str | None]] = []
        self.commits = 0
        self._permissions_fake = self

    def execute(self, sql: str, params: dict[str, Any]) -> list[tuple]:
        sql_clean = " ".join(sql.split()).lower()
        if "select permission_type, permission_value, module_ext" in sql_clean:
            return [(r[1], r[2], r[3]) for r in self.rows if r[0] == params["role"]]
        if "select 1 from role_permission where" in sql_clean:
            return [(1,)] if any(r[0] == params["role"] for r in self.rows) else []
        if "select distinct role" in sql_clean:
            return sorted({(r[0],) for r in self.rows})
        if sql_clean.startswith("delete from role_permission"):
            self.rows = [r for r in self.rows if r[0] != params["role"]]
            return []
        if "insert into role_permission" in sql_clean and "module_ext" in params:
            self.rows.append((params["role"], "module", None, params["module_ext"]))
            return []
        if "insert into role_permission" in sql_clean and "pval" in params:
            self.rows.append((params["role"], params["ptype"], params["pval"], None))
            return []
        return []

    def commit(self) -> None:
        self.commits += 1


class TestRolePermissionsDataClass:
    def test_default_values(self):
        rp = RolePermissions()
        assert rp.modules == []
        assert rp.sales_tabs is None
        assert rp.regions is None

    def test_to_dict(self):
        rp = RolePermissions(modules=["m1"], sales_tabs=["s1"], regions=["r1"])
        d = rp.to_dict()
        assert d["modules"] == ["m1"]
        assert d["sales_tabs"] == ["s1"]
        assert d["regions"] == ["r1"]


class TestLoadRolePermissions:
    def test_empty_role_returns_empty(self):
        db = _FakeDB()
        rp = load_role_permissions(db, "ghost")
        assert rp.modules == []
        assert rp.sales_tabs is None

    def test_load_modules(self):
        db = _FakeDB()
        db.rows.append(("admin", "module", None, "dashboard"))
        db.rows.append(("admin", "module", None, "etl"))
        rp = load_role_permissions(db, "admin")
        assert rp.modules == ["dashboard", "etl"]

    def test_load_sales_tabs_and_regions(self):
        db = _FakeDB()
        db.rows.append(("viewer", "sales_tab", '["sales_today", "sales_week"]', None))
        db.rows.append(("viewer", "region", '["north", "south"]', None))
        rp = load_role_permissions(db, "viewer")
        assert rp.sales_tabs == ["sales_today", "sales_week"]
        assert rp.regions == ["north", "south"]


class TestCheckRoleExists:
    def test_nonexistent_role(self):
        db = _FakeDB()
        assert check_role_exists(db, "ghost") is False

    def test_existing_role(self):
        db = _FakeDB()
        db.rows.append(("admin", "module", None, "x"))
        assert check_role_exists(db, "admin") is True


class TestGetAllRoles:
    def test_empty_db(self):
        db = _FakeDB()
        assert get_all_roles(db) == []

    def test_distinct_sorted(self):
        db = _FakeDB()
        db.rows.append(("admin", "module", None, "x"))
        db.rows.append(("admin", "region", None, None))
        db.rows.append(("viewer", "module", None, "y"))
        assert get_all_roles(db) == ["admin", "viewer"]


class TestUpdateRolePermissions:
    def test_overwrite_replaces_all(self):
        db = _FakeDB()
        db.rows.append(("admin", "module", None, "old_module"))
        update_role_permissions(db, "admin", {
            "modules": ["m1", "m2"],
            "sales_tabs": ["s1"],
            "regions": None,
        })
        rp = load_role_permissions(db, "admin")
        assert sorted(rp.modules) == ["m1", "m2"]
        assert rp.sales_tabs == ["s1"]
        assert rp.regions is None
        assert db.commits == 1

    def test_accepts_dataclass(self):
        db = _FakeDB()
        update_role_permissions(db, "user", RolePermissions(modules=["m1"]))
        rp = load_role_permissions(db, "user")
        assert rp.modules == ["m1"]

    def test_empty_overwrite_clears_role(self):
        db = _FakeDB()
        db.rows.append(("admin", "module", None, "x"))
        update_role_permissions(db, "admin", RolePermissions())
        assert load_role_permissions(db, "admin").modules == []