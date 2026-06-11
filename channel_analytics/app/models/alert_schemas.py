"""
Pydantic schemas for Alert & Notification System
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AlertType(str, Enum):
    SALES_DECLINE = "sales_decline"
    INVENTORY_OVERSTOCK = "inventory_overstock"
    CUSTOMER_CHURN = "customer_churn"
    EXPIRY_WARNING = "expiry_warning"


class CheckInterval(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ==================== Alert Rule Schemas ====================

class AlertRuleConfig(BaseModel):
    """Alert rule configuration parameters"""
    # Sales decline config
    consecutive_months: int = Field(default=2, description="连续下滑月数")
    decline_threshold: float = Field(default=0.2, description="下滑阈值(如0.2表示下滑超过20%)")

    # Inventory overstock config
    turnover_days_threshold: int = Field(default=180, description="周转天数阈值")
    inventory_amount_threshold: float = Field(default=100000, description="库存金额阈值")

    # Customer churn config
    recency_days_threshold: int = Field(default=90, description="最近购买天数阈值")
    min_frequency: int = Field(default=2, description="最低购买次数")

    # Expiry warning config
    expiry_days_threshold: int = Field(default=30, description="效期预警天数")

    # Common filters
    region: Optional[str] = Field(default=None, description="大区筛选")
    manager: Optional[str] = Field(default=None, description="客户经理筛选")


class AlertRuleCreate(BaseModel):
    """Create alert rule request"""
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    alert_type: AlertType = Field(..., description="预警类型")
    config: AlertRuleConfig = Field(default_factory=AlertRuleConfig, description="规则配置")
    check_interval: CheckInterval = Field(default=CheckInterval.DAILY, description="检测频率")
    notify_channels: List[str] = Field(default=["in_app"], description="通知渠道")
    notify_targets: Optional[List[str]] = Field(default=None, description="通知对象用户ID列表")


class AlertRuleUpdate(BaseModel):
    """Update alert rule request"""
    name: Optional[str] = Field(default=None, max_length=100, description="规则名称")
    config: Optional[AlertRuleConfig] = Field(default=None, description="规则配置")
    check_interval: Optional[CheckInterval] = Field(default=None, description="检测频率")
    notify_channels: Optional[List[str]] = Field(default=None, description="通知渠道")
    notify_targets: Optional[List[str]] = Field(default=None, description="通知对象")
    is_enabled: Optional[bool] = Field(default=None, description="是否启用")


class AlertRuleResponse(BaseModel):
    """Alert rule response"""
    id: int
    name: str
    alert_type: AlertType
    config: AlertRuleConfig
    check_interval: CheckInterval
    notify_channels: List[str]
    notify_targets: Optional[List[str]]
    is_enabled: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Alert History Schemas ====================

class AlertHistoryResponse(BaseModel):
    """Alert history response"""
    id: int
    rule_id: int
    rule_name: Optional[str] = None
    alert_level: AlertLevel
    title: str
    content: Optional[str]
    triggered_count: int
    detail_data: Optional[List[dict]]
    is_acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryAck(BaseModel):
    """Acknowledge alert request"""
    acknowledged_by: str = Field(..., description="确认人")


# ==================== Notification Schemas ====================

class NotificationResponse(BaseModel):
    """Notification response"""
    id: int
    user_id: str
    alert_history_id: Optional[int]
    title: str
    content: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Statistics Schemas ====================

class AlertStats(BaseModel):
    """Alert statistics"""
    total_rules: int = 0
    enabled_rules: int = 0
    triggered_this_month: int = 0
    unacknowledged_count: int = 0
    unread_notifications: int = 0


# ==================== Template Schemas ====================

class ReportConfig(BaseModel):
    """Custom report configuration"""
    table: str = Field(..., description="数据表名")
    fields: List[str] = Field(default_factory=list, description="字段列表")
    filters: List[dict] = Field(default_factory=list, description="筛选条件")
    group_by: List[str] = Field(default_factory=list, description="分组字段")
    sort: List[dict] = Field(default_factory=list, description="排序配置")


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
