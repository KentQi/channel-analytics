"""Auth router — login / me / logout(脱敏后保留契约,具体业务字段由部署方补)。

新仓实现:
  - POST /auth/login     — 接收 username/password,签发 JWT
  - GET  /auth/me        — 当前用户信息(role / modules)
  - POST /auth/logout    — 失效 token(可选,需要 DB 存 jti 黑名单)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from channel_analytics.api.deps import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class MeResponse(BaseModel):
    username: str
    role: str
    modules: list[str]


# 部署期应替换为真实用户存储(原仓用了 DB table,新仓抽象为 callable)
def _authenticate(username: str, password: str) -> dict[str, Any] | None:
    """返回 {username, role, password_hash} 或 None。

    新仓默认实现:无 DB 连接时使用 dev 默认用户(仅 development 模式)。

    部署方应替换为查 user 表 + verify_password。
    """
    # TODO: 由部署方实现真实用户查询
    return None


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = _authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    expires = timedelta(hours=1)
    token = create_access_token(
        subject=user["username"],
        extra={"role": user["role"]},
        expires_delta=expires,
    )
    return TokenResponse(access_token=token, expires_in=int(expires.total_seconds()))


@router.get("/me", response_model=MeResponse)
async def me(current_user=Depends(get_current_user)) -> MeResponse:
    """当前登录用户信息(role + modules)。

    部署方应注入 role -> modules 映射(从 permissions 表读)。
    """
    return MeResponse(
        username=current_user["username"],
        role=current_user.get("role", "viewer"),
        modules=current_user.get("modules", []),
    )


@router.post("/logout", status_code=204)
async def logout() -> None:
    """失效 token(简化版:无状态 JWT 模式下返回 204,需配合前端清 cookie)。

    生产实现应:把 token jti 加入 Redis 黑名单 + 设过期时间。
    """
    return None


__all__ = ["router"]