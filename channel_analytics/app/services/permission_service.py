"""
Permission service.
Business logic for role and permission management.
"""
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


def load_role_permissions(db: Session, role: str) -> Dict[str, Any]:
    """
    Load three-dimensional permissions (modules/sales_tabs/regions) for a role.

    Args:
        db: Database session
        role: Role name

    Returns:
        Dict with modules, sales_tabs, and regions
    """
    result = {"modules": [], "sales_tabs": None, "regions": None}
    rows = db.execute(
        text("""
            SELECT permission_type, permission_value, module_ext
            FROM role_permission WHERE role = :role
        """),
        {"role": role}
    ).fetchall()
    for ptype, pval, module_ext in rows:
        if ptype == "module" and module_ext:
            result["modules"].append(module_ext)
        elif ptype == "sales_tab":
            result["sales_tabs"] = json.loads(pval) if pval else None
        elif ptype == "region":
            result["regions"] = json.loads(pval) if pval else None
    return result


def check_role_exists(db: Session, role: str) -> bool:
    """
    Check if a role exists in the database.

    Args:
        db: Database session
        role: Role name

    Returns:
        True if role exists
    """
    count = db.execute(
        text("SELECT COUNT(*) FROM role_permission WHERE role = :role"),
        {"role": role}
    ).scalar()
    return count > 0


def get_all_roles(db: Session) -> List[str]:
    """
    Get all role names.

    Args:
        db: Database session

    Returns:
        List of role names
    """
    rows = db.execute(
        text("SELECT DISTINCT role FROM role_permission ORDER BY role")
    ).fetchall()
    return [row[0] for row in rows]


def update_role_permissions(
    db: Session,
    role: str,
    permissions: Dict[str, Any]
) -> None:
    """
    Update permissions for a role (replace all existing).

    Args:
        db: Database session
        role: Role name
        permissions: Dict with modules, sales_tabs, regions
    """
    # Delete existing permissions
    db.execute(text("DELETE FROM role_permission WHERE role = :role"), {"role": role})

    # Insert modules
    for module_name in permissions.get("modules", []):
        db.execute(
            text("""
                INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
                VALUES (:role, 'module', 'module', NULL, :module_ext)
            """),
            {"role": role, "module_ext": module_name}
        )

    # Insert sales_tabs
    sales_tabs = permissions.get("sales_tabs")
    if sales_tabs:
        db.execute(
            text("""
                INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
                VALUES (:role, 'sales_tab', 'sales_tab', :pval, NULL)
            """),
            {"role": role, "pval": json.dumps(sales_tabs, ensure_ascii=False)}
        )

    # Insert regions
    regions = permissions.get("regions")
    if regions:
        db.execute(
            text("""
                INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
                VALUES (:role, 'region', 'region', :pval, NULL)
            """),
            {"role": role, "pval": json.dumps(regions, ensure_ascii=False)}
        )

    db.commit()
