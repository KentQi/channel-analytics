"""
Pydantic schemas for Custom Report System
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ReportConfig(BaseModel):
    """Custom report configuration"""
    table: str = Field(..., description="数据表名")
    fields: List[str] = Field(default_factory=list, description="字段列表")
    filters: List[dict] = Field(default_factory=list, description="筛选条件")
    group_by: List[str] = Field(default_factory=list, description="分组字段")
    sort: List[dict] = Field(default_factory=list, description="排序配置")


class ReportPreviewRequest(BaseModel):
    """Report preview request"""
    table: str = Field(..., description="数据表名")
    fields: List[str] = Field(default_factory=list, description="字段列表")
    filters: List[dict] = Field(default_factory=list, description="筛选条件")
    group_by: List[str] = Field(default_factory=list, description="分组字段")
    sort: List[dict] = Field(default_factory=list, description="排序配置")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=100, ge=1, le=1000, description="每页行数")


class ReportExecuteRequest(BaseModel):
    """Execute saved report request"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=100, ge=1, le=1000, description="每页行数")


class ReportExportRequest(BaseModel):
    """Export report request"""
    format: str = Field(default="csv", description="导出格式 csv/excel")


class CustomReportCreate(BaseModel):
    """Create custom report request"""
    name: str = Field(..., min_length=1, max_length=100, description="报表名称")
    description: Optional[str] = Field(default=None, max_length=500, description="报表描述")
    config: ReportConfig = Field(..., description="报表配置")
    is_public: bool = Field(default=False, description="是否公开")


class CustomReportUpdate(BaseModel):
    """Update custom report request"""
    name: Optional[str] = Field(default=None, max_length=100, description="报表名称")
    description: Optional[str] = Field(default=None, max_length=500, description="报表描述")
    config: Optional[ReportConfig] = Field(default=None, description="报表配置")
    is_public: Optional[bool] = Field(default=None, description="是否公开")


class CustomReportResponse(BaseModel):
    """Custom report response"""
    id: int
    name: str
    description: Optional[str]
    config: ReportConfig
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_public: bool

    class Config:
        from_attributes = True


class CustomReportShare(BaseModel):
    """Share custom report request"""
    target_users: Optional[List[str]] = Field(default=None, description="分享目标用户")
    target_roles: Optional[List[str]] = Field(default=None, description="分享目标角色")


class TableInfo(BaseModel):
    """Table metadata"""
    name: str
    display_name: Optional[str] = None
    field_count: int
    has_date_field: bool


class FieldInfo(BaseModel):
    """Field metadata"""
    name: str
    display_name: Optional[str] = None
    is_numeric: bool
    is_date: bool
