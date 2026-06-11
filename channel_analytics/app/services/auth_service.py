"""
Authentication service.
Handles user authentication, password hashing, and JWT token management.
"""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_session_secret
from app.models.schemas import UserResponse
from app.utils.audit import log_login

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.

    Args:
        plain_password: The plain text password
        hashed_password: The bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    password_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The bcrypt hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(user_id: int, username: str, role: str) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user's ID
        username: The user's username
        role: The user's role

    Returns:
        Encoded JWT token string
    """
    secret = get_session_secret()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token string

    Returns:
        Decoded payload dict if valid, None if invalid
    """
    try:
        secret = get_session_secret()
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[UserResponse]:
    """
    Authenticate a user from the system_user table.

    Args:
        db: SQLAlchemy database session
        username: The username to authenticate
        password: The plain text password

    Returns:
        UserResponse if authentication successful, None otherwise
    """
    query = text("""
        SELECT id, username, password, role, display_name, status
        FROM system_user
        WHERE username = :username
    """)
    result = db.execute(query, {"username": username}).fetchone()

    if result is None:
        log_login(username, success=False)
        return None

    user_id, db_username, pwd_hash, role, display_name, status = result

    # Check if user is active (status=1 means active)
    if status != 1:
        log_login(username, success=False)
        return None

    # Verify password (bcrypt only)
    if not verify_password(password, pwd_hash):
        log_login(username, success=False)
        return None

    log_login(username, success=True)
    return UserResponse(
        id=user_id,
        username=db_username,
        display_name=display_name,
        role=role,
        is_active=status == 1,
    )


def change_password(
    db: Session, user_id: int, old_password: str, new_password: str
) -> bool:
    """
    Change a user's password.

    Args:
        db: SQLAlchemy database session
        user_id: The user's ID
        old_password: The current password
        new_password: The new password to set

    Returns:
        True if password changed successfully, False otherwise
    """
    # Get current password
    query = text("""
        SELECT password
        FROM system_user
        WHERE id = :user_id
    """)
    result = db.execute(query, {"user_id": user_id}).fetchone()

    if result is None:
        return False

    current_hash = result[0]

    # Verify old password (bcrypt only)
    if not verify_password(old_password, current_hash):
        return False

    # Hash new password and update
    new_hash = get_password_hash(new_password)

    update_query = text("""
        UPDATE system_user
        SET password = :new_hash
        WHERE id = :user_id
    """)
    db.execute(
        update_query,
        {"new_hash": new_hash, "user_id": user_id},
    )
    db.commit()

    return True


def get_user_by_id(db: Session, user_id: int) -> Optional[UserResponse]:
    """
    Get user information by ID.

    Args:
        db: SQLAlchemy database session
        user_id: The user's ID

    Returns:
        UserResponse if user found, None otherwise
    """
    query = text("""
        SELECT id, username, display_name, role, status, created_at
        FROM system_user
        WHERE id = :user_id
    """)
    result = db.execute(query, {"user_id": user_id}).fetchone()

    if result is None:
        return None

    return UserResponse(
        id=result[0],
        username=result[1],
        display_name=result[2],
        role=result[3],
        is_active=result[4] == 1,
        role_permissions=load_role_permissions(db, result[3]),
        created_at=result[5],
        updated_at=None,
    )


def load_role_permissions(db: Session, role: str) -> dict:
    """从 role_permission 表加载角色权限"""
    import json
    result = {"modules": [], "sales_tabs": None, "regions": None}
    try:
        rows = db.execute(
            text("SELECT permission_type, permission_value, module_ext FROM role_permission WHERE role = :r"),
            {"r": role}
        ).fetchall()
        for ptype, pval, module_ext in rows:
            if ptype == "module" and module_ext:
                result["modules"].append(module_ext)
            elif ptype == "sales_tab":
                result["sales_tabs"] = json.loads(pval) if pval else None
            elif ptype == "region":
                result["regions"] = json.loads(pval) if pval else None
    except Exception:
        pass
    return result
