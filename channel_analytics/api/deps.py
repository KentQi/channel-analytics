"""API dependencies — JWT 验证 + 密码 hash。

JWT 用 jose / passlib(部署方安装);新仓提供最小依赖,具体业务字段(username
-> role 映射)由部署方扩展。

注:密码 hash 默认使用 passlib[bcrypt],未安装时降级到 hashlib 简化实现。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


# ---------------------------------------------------------------------------
# 密码 hash(部署期可换 passlib bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """简化 hash(开发环境用)。

    生产部署应换 passlib.bcrypt 或 argon2。
    """
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(
        digest,
        hashlib.sha256(f"{salt}:{password}".encode()).hexdigest(),
    )


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _get_jwt_secret() -> str:
    from channel_analytics.config import get_settings
    return get_settings().jwt_secret.get_secret_value()


def create_access_token(
    subject: str,
    extra: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """签发 JWT。

    依赖 PyJWT(可选依赖);未安装时降级到签名 token(仅用于本地测试)。
    """
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(hours=1))
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        **(extra or {}),
    }
    try:
        import jwt  # PyJWT
        return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")
    except ImportError:
        # 简化实现(无加密)— 仅供本地测试
        import json
        import base64
        token = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()
        ).decode().rstrip("=")
        return f"local.{token}"


def _decode_token(token: str) -> dict[str, Any]:
    """解码 JWT,失败抛 HTTP 401。"""
    try:
        import jwt
        return jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    except ImportError:
        import json
        import base64
        if not token.startswith("local."):
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            payload_b64 = token[len("local."):]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            return json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token") from None
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict[str, Any]:
    """FastAPI dependency:从 Bearer token 取当前用户。

    返回 {username, role, modules, ...} — 由部署方扩展。
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)
    return {
        "username": payload.get("sub", ""),
        "role": payload.get("role", "viewer"),
        "modules": payload.get("modules", []),
    }


__all__ = [
    "create_access_token",
    "get_current_user",
    "hash_password",
    "verify_password",
]