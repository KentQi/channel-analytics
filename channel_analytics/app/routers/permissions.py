"""
权限配置API路由
提供角色权限管理和用户管理接口
"""
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.schemas import UserResponse
from app.utils.audit import log_permission_change
from app.limiter import limiter
from app.services.permission_service import (
    load_role_permissions,
    check_role_exists,
    get_all_roles,
    update_role_permissions as update_role_permissions_service,
)

router = APIRouter(prefix="/permissions", tags=["权限配置"])
logger = logging.getLogger(__name__)


# Pydantic model：确保 PUT body 正确解析（不用 Dict 默认会被当成 Query 参数）
class PermissionsUpdate(BaseModel):
    modules: Optional[List[str]] = []
    sales_tabs: Optional[List[str]] = None
    regions: Optional[List[str]] = None


# ===================== 角色权限管理 =====================
@router.get("/roles")
async def list_roles(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    获取所有角色权限配置

    返回系统中的所有角色及其权限设置
    """
    # 检查用户角色权限
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以查看角色权限")

    # 查询所有角色
    role_rows = db.execute(
        text("SELECT DISTINCT role FROM role_permission ORDER BY role")
    ).fetchall()

    roles = []
    for (role_name,) in role_rows:
        perms = load_role_permissions(db, role_name)
        roles.append({
            "role": role_name,
            "permissions": perms,
        })

    return roles


@router.get("/roles/{role}")
async def get_role(
    role: str,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取指定角色的权限配置

    Args:
        role: 角色名称
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以查看角色权限")

    perms = load_role_permissions(db, role)

    # 检查角色是否存在于 role_permission 表
    role_exists = db.execute(
        text("SELECT COUNT(*) FROM role_permission WHERE role = :role"),
        {"role": role}
    ).scalar()

    if role_exists == 0:
        raise HTTPException(status_code=404, detail="角色不存在")

    return {
        "role": role,
        "permissions": perms,
    }


@router.put("/roles/{role}")
@limiter.limit("300/minute")
async def update_role_permissions(
    request: Request,
    role: str,
    body: PermissionsUpdate,
    new_role_name: Optional[str] = None,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, str]:
    """
    更新角色权限配置

    Args:
        role: 角色名称
        body: 权限配置（modules/sales_tabs/regions）
        new_role_name: 新角色名称（用于重命名角色）
    """
    permissions = body.model_dump()
    # 兼容旧字段：modules=[] 等价于 None（不限制）
    if not permissions.get("modules"):
        permissions["modules"] = None
    if permissions.get("sales_tabs") is None:
        permissions["sales_tabs"] = None
    if permissions.get("regions") is None:
        permissions["regions"] = None

    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以更新权限")

    # 如果提供了新角色名称，则重命名角色
    if new_role_name and new_role_name != role:
        # 检查新名称是否已存在
        check = db.execute(
            text("SELECT COUNT(*) FROM role_permission WHERE role = :role"),
            {"role": new_role_name}
        ).scalar()
        if check > 0:
            raise HTTPException(status_code=400, detail="新角色名称已存在")

        # 更新关联用户的角色
        db.execute(
            text("UPDATE system_user SET role = :new_role WHERE role = :old_role"),
            {"new_role": new_role_name, "old_role": role}
        )

        # 更新角色权限记录
        db.execute(
            text("UPDATE role_permission SET role = :new_role WHERE role = :old_role"),
            {"new_role": new_role_name, "old_role": role}
        )

        log_permission_change(user.username, role, f"重命名角色为 {new_role_name}")
        role = new_role_name  # 后续操作使用新名称

    # 检查角色是否存在
    check = db.execute(
        text("SELECT COUNT(*) FROM role_permission WHERE role = :role"),
        {"role": role}
    ).scalar()
    if check == 0:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 委托给 service 层（参数化 SQL + 统一行为）
    update_role_permissions_service(db, role, permissions)

    log_permission_change(user.username, role, "更新权限配置")

    return {"message": "权限更新成功"}


@router.post("/roles")
@limiter.limit("300/minute")
async def create_role(
    request: Request,
    role: str,
    permissions: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, str]:
    """
    创建新角色

    Args:
        role: 角色名称
        permissions: 初始权限配置
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以创建角色")

    try:
        # 检查角色是否已存在(参数化 SQL)
        check = db.execute(
            text("SELECT COUNT(*) FROM role_permission WHERE role = :role"),
            {"role": role}
        ).scalar()

        if check > 0:
            raise HTTPException(status_code=400, detail="角色已存在")

        # 创建角色: 插入三条默认记录(module/sales_tab/region 各一条,参数化 SQL)
        db.execute(
            text("""
                INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
                VALUES (:role, 'module', 'module', NULL, NULL)
            """),
            {"role": role}
        )
        db.execute(
            text("""
                INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
                VALUES (:role, 'sales_tab', 'sales_tab', NULL, NULL)
            """),
            {"role": role}
        )
        db.execute(
            text("""
                INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext)
                VALUES (:role, 'region', 'region', NULL, NULL)
            """),
            {"role": role}
        )
        db.commit()
    except HTTPException:
        # HTTPException(400) 已 raise,需要回滚前面的检查
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"create_role failed for role={role}: {e}")
        raise HTTPException(status_code=500, detail="角色创建失败")

    log_permission_change(user.username, role, "创建角色")

    return {"message": "角色创建成功"}


@router.delete("/roles/{role}")
@limiter.limit("300/minute")
async def delete_role(
    request: Request,
    role: str,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, str]:
    """
    删除角色
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以删除角色")

    if role == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员角色")

    try:
        # 先将关联用户的 role 设为 NULL(参数化 SQL)
        db.execute(
            text("UPDATE system_user SET role = NULL WHERE role = :role"),
            {"role": role}
        )

        # 删除角色权限记录(参数化 SQL)
        result = db.execute(
            text("DELETE FROM role_permission WHERE role = :role"),
            {"role": role}
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"delete_role failed for role={role}: {e}")
        raise HTTPException(status_code=500, detail="角色删除失败")

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="角色不存在")

    log_permission_change(user.username, role, "删除角色")

    return {"message": "角色删除成功"}


# ===================== 用户管理 =====================
@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索用户名或显示名"),
    role: Optional[str] = Query(None, description="角色筛选"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取用户列表

    支持分页、用户名搜索和角色筛选
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以查看用户列表")

    offset = (page - 1) * page_size
    params = {"limit": page_size, "offset": offset}

    # 构建条件
    conditions = []
    if search:
        conditions.append("(username LIKE :search OR display_name LIKE :search)")
        params["search"] = f"%{search}%"
    if role:
        conditions.append("role = :role")
        params["role"] = role

    # 列名是硬编码白名单(不来自用户输入),只有值通过 :param 参数化
    # — 这是 SQLAlchemy 官方推荐的标准做法,非 SQL 注入
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # 获取总数(条件已全部参数化,WHERE 子句由安全的列名拼接)
    count_sql = text(f"SELECT COUNT(*) FROM system_user {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    # 获取用户列表
    data_sql = text(f"""
        SELECT id, username, display_name, role, status, created_at, updated_at
        FROM system_user
        {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)
    results = db.execute(data_sql, params).fetchall()

    items = [
        {
            "id": r[0],
            "username": r[1],
            "display_name": r[2],
            "role": r[3],
            "is_active": bool(r[4]),
            "created_at": r[5].isoformat() if r[5] else None,
            "updated_at": r[6].isoformat() if r[6] else None,
        }
        for r in results
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取指定用户详情

    Args:
        user_id: 用户ID
    """
    if user.role not in ["admin", "创建人"] and user.id != user_id:
        raise HTTPException(status_code=403, detail="无权限查看该用户信息")

    result = db.execute(
        text("""
            SELECT id, username, display_name, role, status, created_at, updated_at
            FROM system_user WHERE id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": result[0],
        "username": result[1],
        "display_name": result[2],
        "role": result[3],
        "is_active": bool(result[4]),
        "created_at": result[5].isoformat() if result[5] else None,
        "updated_at": result[6].isoformat() if result[6] else None,
    }


@router.put("/users/{user_id}")
@limiter.limit("300/minute")
async def update_user(
    request: Request,
    user_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, str]:
    """
    更新用户信息

    Args:
        user_id: 用户ID
        data: 更新数据 (display_name, role, is_active)
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以更新用户信息")

    # 禁止修改管理员角色
    if user_id == 1:  # 假设ID=1是超级管理员
        raise HTTPException(status_code=400, detail="不能修改超级管理员信息")

    allowed_fields = ["display_name", "role", "is_active"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_fields:
        raise HTTPException(status_code=400, detail="没有有效的更新字段")

    # Map is_active to status for database
    if "is_active" in update_fields:
        update_fields["status"] = int(update_fields.pop("is_active"))

    # 白名单列名拼接(列名是硬编码,不来自用户输入),值通过 :param 参数化
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()]) + ", updated_at = NOW()"
    sql = text(f"""
        UPDATE system_user
        SET {set_clause}
        WHERE id = :user_id
    """)
    update_fields["user_id"] = user_id

    try:
        result = db.execute(sql, update_fields)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(f"update_user failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail="用户更新失败")

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取被更新用户的用户名
    user_row = db.execute(
        text("SELECT username FROM system_user WHERE id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    target_username = user_row[0] if user_row else str(user_id)

    log_permission_change(user.username, target_username, f"更新账号 (变更: {list(update_fields.keys())})")

    return {"message": "用户更新成功"}


@router.post("/users")
@limiter.limit("300/minute")
async def create_user(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    创建新用户(body: {username, display_name, password, role})

    安全:密码放 Body 而非 query,避免 URL 日志泄露。
    """
    username = payload.get("username", "").strip()
    display_name = payload.get("display_name", "").strip()
    password = payload.get("password", "")
    role = payload.get("role", "viewer").strip()
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以创建用户")

    # 检查用户名是否已存在
    check = db.execute(
        text("SELECT COUNT(*) FROM system_user WHERE username = :username"),
        {"username": username}
    ).scalar()

    if check > 0:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 获取密码哈希
    from app.services.auth_service import get_password_hash
    password_hash = get_password_hash(password)

    # 创建用户
    try:
        result = db.execute(
            text("""
                INSERT INTO system_user (username, display_name, password, role, status)
                VALUES (:username, :display_name, :password_hash, :role, 1)
            """),
            {
                "username": username,
                "display_name": display_name,
                "password_hash": password_hash,
                "role": role,
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(f"create_user failed for username={username}: {e}")
        raise HTTPException(status_code=500, detail="用户创建失败")

    log_permission_change(user.username, username, f"创建账号 (角色: {role})")

    return {
        "message": "用户创建成功",
        "user_id": result.lastrowid,
    }


@router.delete("/users/{user_id}")
@limiter.limit("300/minute")
async def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, str]:
    """
    删除用户

    Args:
        user_id: 用户ID
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以删除用户")

    # 禁止删除自己
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")

    # 禁止删除超级管理员
    if user_id == 1:
        raise HTTPException(status_code=400, detail="不能删除超级管理员")

    # 获取被删除用户的用户名用于日志
    user_row = db.execute(
        text("SELECT username FROM system_user WHERE id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    target_username = user_row[0] if user_row else str(user_id)

    try:
        result = db.execute(
            text("DELETE FROM system_user WHERE id = :user_id"),
            {"user_id": user_id}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(f"delete_user failed for user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail="用户删除失败")

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    log_permission_change(user.username, target_username, "删除账号")

    return {"message": "用户删除成功"}


# ===================== 权限配置模板 =====================
@router.get("/permission-template")
async def get_permission_template(
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取权限配置模板

    返回默认的权限配置结构
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以查看权限模板")

    return {
        "modules": [],
        "sales_tabs": None,
        "regions": None,
        "dashboard_visible": True,
        "export_enabled": True,
    }


# ===================== 可用区域列表 =====================
@router.get("/regions")
async def get_available_regions(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """
    获取 rpt_sales_out_wide 中所有可用区域列表
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以查看区域列表")

    results = db.execute(
        text("SELECT DISTINCT region FROM rpt_sales_out_wide WHERE region IS NOT NULL AND region != '' ORDER BY region")
    ).fetchall()

    regions = [r[0] for r in results if r[0]]

    return {"regions": regions}


# ===================== 可用角色列表 =====================
@router.get("/available-roles")
async def get_available_roles(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """
    获取系统中所有可用的角色列表
    """
    if user.role not in ["admin", "创建人"]:
        raise HTTPException(status_code=403, detail="只有管理员可以查看角色列表")

    results = db.execute(
        text("SELECT DISTINCT role FROM system_user ORDER BY role")
    ).fetchall()

    roles = [r[0] for r in results if r[0]]

    return {"roles": roles}
