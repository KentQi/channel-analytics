"""
Pydantic models for the application.
Defines request and response schemas for all endpoints.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with JWT token."""

    token: str
    username: str
    display_name: str
    role: str
    user_id: int
    modules: Optional[List[str]] = None
    sales_tabs: Optional[List[str]] = None
    regions: Optional[List[str]] = None


class ChangePasswordRequest(BaseModel):
    """Change password request payload."""

    old_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User information response."""

    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    role_permissions: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 数据维护请求模型 ==========

class ProductAttrUpdate(BaseModel):
    material_name: Optional[str] = None
    category: Optional[str] = None
    first_stock_in_date: Optional[str] = None
    abc_class: Optional[str] = None
    lifecycle_status: Optional[str] = None
    custom_flag: Optional[str] = None
    promoted_flag: Optional[str] = None


class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    sales_area: Optional[str] = None
    channel: Optional[str] = None
    cooperation_status: Optional[str] = None
    account_manager: Optional[str] = None


class RegionIndicatorUpdate(BaseModel):
    region: Optional[str] = None
    province: Optional[str] = None
    sales_area: Optional[str] = None
    manager: Optional[str] = None
    monthly_target: Optional[float] = None


class CustomerIndicatorUpdate(BaseModel):
    region: Optional[str] = None
    province: Optional[str] = None
    sales_area: Optional[str] = None
    manager: Optional[str] = None
    customer_name: Optional[str] = None
    monthly_target: Optional[float] = None


class FilterConfigSave(BaseModel):
    values: List[str] = []


class FilterConfigUpdate(BaseModel):
    filter_type: Optional[str] = None
    filter_value: Optional[str] = None


class BrandUpdate(BaseModel):
    brand_name: Optional[str] = None
    remark: Optional[str] = None
