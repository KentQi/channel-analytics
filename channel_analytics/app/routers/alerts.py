"""
Alert & Notification API Router
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert_schemas import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertHistoryResponse,
    AlertHistoryAck,
    NotificationResponse,
    AlertStats,
)
from app.models.schemas import UserResponse
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["预警通知"])


def json_to_response(data: dict) -> dict:
    """Convert datetime strings to None for Pydantic compatibility"""
    for key, value in data.items():
        if isinstance(value, str) and value in ("None", "null", ""):
            data[key] = None
    return data


@router.get("/rules", response_model=List[AlertRuleResponse])
def list_alert_rules(
    alert_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List alert rules with optional filters"""
    rules = alert_service.get_alert_rules(
        db,
        user_id=None,  # show all rules
        alert_type=alert_type,
        is_enabled=is_enabled,
    )
    return [json_to_response(r) for r in rules]


@router.post("/rules", response_model=AlertRuleResponse)
def create_alert_rule(
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Create new alert rule"""
    rule_id = alert_service.create_alert_rule(
        db,
        name=rule.name,
        alert_type=rule.alert_type.value,
        config=rule.config.model_dump(),
        check_interval=rule.check_interval.value,
        notify_channels=rule.notify_channels,
        notify_targets=rule.notify_targets,
        created_by=current_user,
    )
    return alert_service.get_alert_rule(db, rule_id)


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get alert rule by ID"""
    rule = alert_service.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return json_to_response(rule)


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    rule: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Update alert rule"""
    updates = {}
    if rule.name is not None:
        updates["name"] = rule.name
    if rule.config is not None:
        updates["config"] = rule.config.model_dump()
    if rule.check_interval is not None:
        updates["check_interval"] = rule.check_interval.value
    if rule.notify_channels is not None:
        updates["notify_channels"] = rule.notify_channels
    if rule.notify_targets is not None:
        updates["notify_targets"] = rule.notify_targets
    if rule.is_enabled is not None:
        updates["is_enabled"] = rule.is_enabled

    if updates:
        alert_service.update_alert_rule(db, rule_id, **updates)

    rule = alert_service.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return json_to_response(rule)


@router.delete("/rules/{rule_id}")
def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Delete alert rule"""
    success = alert_service.delete_alert_rule(db, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"message": "删除成功"}


@router.post("/rules/{rule_id}/test")
def test_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Test alert rule (execute once immediately)"""
    rule = alert_service.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    results = alert_service.execute_alert_rule(db, rule)
    return {
        "rule_id": rule_id,
        "triggered_count": len(results),
        "results": results[:10],  # return first 10 for preview
    }


@router.get("/history", response_model=List[AlertHistoryResponse])
def list_alert_history(
    rule_id: Optional[int] = None,
    is_acknowledged: Optional[bool] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List alert history records"""
    history = alert_service.get_alert_history(
        db,
        rule_id=rule_id,
        is_acknowledged=is_acknowledged,
        limit=limit,
        offset=offset,
    )
    return [json_to_response(h) for h in history]


@router.post("/history/{history_id}/ack")
def acknowledge_alert(
    history_id: int,
    ack: AlertHistoryAck,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Acknowledge/close an alert"""
    success = alert_service.acknowledge_alert_history(db, history_id, ack.acknowledged_by)
    if not success:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    return {"message": "确认成功"}


@router.get("/notifications", response_model=List[NotificationResponse])
def list_notifications(
    is_read: Optional[bool] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get user notifications"""
    notifications = alert_service.get_notifications(
        db,
        user_id=current_user,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )
    return [json_to_response(n) for n in notifications]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Mark notification as read"""
    success = alert_service.mark_notification_read(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"message": "标记成功"}


@router.get("/stats", response_model=AlertStats)
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get alert statistics"""
    return alert_service.get_alert_stats(db, current_user.id)
