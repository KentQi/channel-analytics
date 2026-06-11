"""
FastAPI dependency injection.
Provides authentication and database session dependencies.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import UserResponse
from app.services.auth_service import verify_token, get_user_by_id

# Bearer token security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        UserResponse for the authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify token and extract payload
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token payload
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is still active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # 拼装 role_permissions（admin/创建人 = None = 不限制）
    from app.services.auth_service import load_role_permissions
    if user.role in ["admin", "创建人"]:
        perms = {"modules": None, "sales_tabs": None, "regions": None}
    elif user.role:
        perms = load_role_permissions(db, user.role)
        # 确保 modules 不会是 null（null 在前端 = 不限制）
        if perms.get("modules") is None:
            perms["modules"] = []
    else:
        perms = {"modules": [], "sales_tabs": None, "regions": None}

    # 给 ORM user 挂上 role_permissions（供 UserResponse 序列化）
    user.role_permissions = perms
    return user


def require_role(*allowed_roles: str):
    """
    Role permission check decorator.

    Args:
        allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Depends dependency that validates the user's role
    """
    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此功能",
            )
        return current_user
    return role_checker


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[UserResponse]:
    """
    Dependency to optionally get the current authenticated user.
    Returns None if no valid token is provided.

    Args:
        credentials: Optional HTTP Bearer token credentials
        db: Database session

    Returns:
        UserResponse for the authenticated user, or None
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        user_id = int(user_id_str)
    except ValueError:
        return None

    user = get_user_by_id(db, user_id)
    if user is None:
        return None

    # Check if user is still active
    if not user.is_active:
        return None

    return user
