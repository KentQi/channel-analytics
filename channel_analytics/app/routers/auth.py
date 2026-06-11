"""
Authentication router.
Provides login, logout, and user management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import (
    LoginRequest,
    LoginResponse,
    ChangePasswordRequest,
    UserResponse,
)
from app.services.auth_service import authenticate_user, create_access_token, change_password
from app.utils.audit import log_password_change, log_logout

# Create router
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.

    Args:
        request: Login credentials (username and password)
        db: Database session

    Returns:
        LoginResponse with JWT token and user info

    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(db, request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户名或密码错误",
        )

    # 加载角色权限（admin/创建人不受限，返回 None 表示"全部可用"）
    from app.services.auth_service import load_role_permissions
    if user.role in ["admin", "创建人"]:
        modules: Optional[List[str]] = None  # None = 不限制
        sales_tabs: Optional[List[str]] = None
        regions: Optional[List[str]] = None
    else:
        perms = load_role_permissions(db, user.role)
        modules = perms.get("modules") or []  # [] = 没有可用模块（非 null，否则前端会当成"不限制"）
        sales_tabs = perms.get("sales_tabs")
        regions = perms.get("regions")

    # Create JWT token
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

    return LoginResponse(
        token=token,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        user_id=user.id,
        modules=modules,
        sales_tabs=sales_tabs,
        regions=regions,
    )


@auth_router.post("/change-password")
async def change_user_password(
    request: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change the current user's password.

    Args:
        request: Old and new password
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If old password is incorrect
    """
    success = change_password(
        db=db,
        user_id=current_user.id,
        old_password=request.old_password,
        new_password=request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

    log_password_change(current_user.username)

    return {"message": "Password changed successfully"}


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """
    Get current authenticated user's information.

    Args:
        current_user: Authenticated user from token

    Returns:
        UserResponse with user details
    """
    return current_user


@auth_router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    Logout current user.

    Args:
        current_user: Authenticated user from token

    Returns:
        Success message
    """
    log_logout(current_user.username)
    return {"message": "Logged out successfully"}
