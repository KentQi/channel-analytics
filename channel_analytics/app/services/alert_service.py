"""
Alert & Notification Service
Provides alert rule evaluation and notification dispatch
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.alert_schemas import AlertRuleConfig, AlertType

logger = logging.getLogger(__name__)


def get_alert_rules(
    db: Session,
    user_id: Optional[str] = None,
    alert_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
) -> List[Dict]:
    """Get alert rules with optional filters"""
    conditions = ["1=1"]
    params = {}

    if user_id:
        conditions.append("created_by = :user_id")
        params["user_id"] = user_id

    if alert_type:
        conditions.append("alert_type = :alert_type")
        params["alert_type"] = alert_type

    if is_enabled is not None:
        conditions.append("is_enabled = :is_enabled")
        params["is_enabled"] = is_enabled

    where_sql = " AND ".join(conditions)
    sql = text(f"""
        SELECT id, name, alert_type, config, check_interval,
               notify_channels, notify_targets, is_enabled,
               created_by, created_at, updated_at
        FROM alert_rule
        WHERE {where_sql}
        ORDER BY created_at DESC
    """)

    df = pd.read_sql(sql, db.bind, params=params)

    rules = []
    for _, row in df.iterrows():
        rules.append({
            "id": int(row["id"]),
            "name": row["name"],
            "alert_type": row["alert_type"],
            "config": json.loads(row["config"]) if row["config"] else {},
            "check_interval": row["check_interval"],
            "notify_channels": json.loads(row["notify_channels"]) if row["notify_channels"] else ["in_app"],
            "notify_targets": json.loads(row["notify_targets"]) if row["notify_targets"] else None,
            "is_enabled": bool(row["is_enabled"]),
            "created_by": row["created_by"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        })

    return rules


def get_alert_rule(db: Session, rule_id: int) -> Optional[Dict]:
    """Get single alert rule by ID"""
    sql = text("""
        SELECT id, name, alert_type, config, check_interval,
               notify_channels, notify_targets, is_enabled,
               created_by, created_at, updated_at
        FROM alert_rule
        WHERE id = :rule_id
    """)

    df = pd.read_sql(sql, db.bind, params={"rule_id": rule_id})

    if df.empty:
        return None

    row = df.iloc[0]
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "alert_type": row["alert_type"],
        "config": json.loads(row["config"]) if row["config"] else {},
        "check_interval": row["check_interval"],
        "notify_channels": json.loads(row["notify_channels"]) if row["notify_channels"] else ["in_app"],
        "notify_targets": json.loads(row["notify_targets"]) if row["notify_targets"] else None,
        "is_enabled": bool(row["is_enabled"]),
        "created_by": row["created_by"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def create_alert_rule(
    db: Session,
    name: str,
    alert_type: str,
    config: Dict,
    check_interval: str,
    notify_channels: List[str],
    notify_targets: Optional[List[str]],
    created_by: str,
) -> int:
    """Create new alert rule"""
    sql = text("""
        INSERT INTO alert_rule (name, alert_type, config, check_interval,
                               notify_channels, notify_targets, created_by)
        VALUES (:name, :alert_type, :config, :check_interval,
                :notify_channels, :notify_targets, :created_by)
    """)

    result = db.execute(sql, {
        "name": name,
        "alert_type": alert_type,
        "config": json.dumps(config, ensure_ascii=False),
        "check_interval": check_interval,
        "notify_channels": json.dumps(notify_channels, ensure_ascii=False),
        "notify_targets": json.dumps(notify_targets, ensure_ascii=False) if notify_targets else None,
        "created_by": created_by,
    })
    db.commit()
    return result.lastrowid


def update_alert_rule(
    db: Session,
    rule_id: int,
    name: Optional[str] = None,
    config: Optional[Dict] = None,
    check_interval: Optional[str] = None,
    notify_channels: Optional[List[str]] = None,
    notify_targets: Optional[List[str]] = None,
    is_enabled: Optional[bool] = None,
) -> bool:
    """Update existing alert rule"""
    updates = []
    params = {"rule_id": rule_id}

    if name is not None:
        updates.append("name = :name")
        params["name"] = name

    if config is not None:
        updates.append("config = :config")
        params["config"] = json.dumps(config, ensure_ascii=False)

    if check_interval is not None:
        updates.append("check_interval = :check_interval")
        params["check_interval"] = check_interval

    if notify_channels is not None:
        updates.append("notify_channels = :notify_channels")
        params["notify_channels"] = json.dumps(notify_channels, ensure_ascii=False)

    if notify_targets is not None:
        updates.append("notify_targets = :notify_targets")
        params["notify_targets"] = json.dumps(notify_targets, ensure_ascii=False)

    if is_enabled is not None:
        updates.append("is_enabled = :is_enabled")
        params["is_enabled"] = is_enabled

    if not updates:
        return False

    updates.append("updated_at = NOW()")

    sql = text(f"""
        UPDATE alert_rule
        SET {', '.join(updates)}
        WHERE id = :rule_id
    """)

    result = db.execute(sql, params)
    db.commit()
    return result.rowcount > 0


def delete_alert_rule(db: Session, rule_id: int) -> bool:
    """Delete alert rule"""
    sql = text("DELETE FROM alert_rule WHERE id = :rule_id")
    result = db.execute(sql, {"rule_id": rule_id})
    db.commit()
    return result.rowcount > 0


def evaluate_sales_decline(db: Session, rule: Dict, months: int = 12) -> List[Dict]:
    """
    Evaluate sales decline alert
    Returns list of materials/customers with declining sales
    """
    config = rule.get("config", {})
    consecutive_months = config.get("consecutive_months", 2)
    decline_threshold = config.get("decline_threshold", 0.2)
    region = config.get("region")

    conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
    params = {}

    if region:
        conditions.append("region = :region")
        params["region"] = region

    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    params["start_date"] = start_date.strftime("%Y-%m-%d")
    params["end_date"] = end_date.strftime("%Y-%m-%d")
    conditions.append("doc_date BETWEEN :start_date AND :end_date")

    where_sql = " AND ".join(conditions)

    sql = text(f"""
        SELECT material_code, material_name,
               DATE_FORMAT(doc_date, '%Y-%m') AS sale_month,
               SUM(tax_included_amount) AS monthly_amount
        FROM rpt_sales_out_wide
        WHERE {where_sql}
        GROUP BY material_code, material_name, DATE_FORMAT(doc_date, '%Y-%m')
        ORDER BY material_code, sale_month
    """)

    df = pd.read_sql(sql, db.bind, params=params)

    if df.empty:
        return []

    # Group by material and check consecutive decline
    results = []
    for (material_code, material_name), mat_df in df.groupby(["material_code", "material_name"]):
        if len(mat_df) < consecutive_months:
            continue

        mat_df = mat_df.sort_values("sale_month").tail(consecutive_months)

        # Check if all recent months show decline
        is_declining = True
        for i in range(1, len(mat_df)):
            prev_amt = mat_df.iloc[i-1]["monthly_amount"]
            curr_amt = mat_df.iloc[i]["monthly_amount"]
            if prev_amt <= 0 or (curr_amt - prev_amt) / prev_amt > -decline_threshold:
                is_declining = False
                break

        if is_declining:
            latest_amount = mat_df.iloc[-1]["monthly_amount"]
            earliest_amount = mat_df.iloc[0]["monthly_amount"]
            decline_rate = (earliest_amount - latest_amount) / earliest_amount if earliest_amount > 0 else 0

            results.append({
                "material_code": material_code,
                "material_name": material_name,
                "latest_amount": float(latest_amount),
                "decline_rate": float(decline_rate),
                "months_count": len(mat_df),
            })

    return results


def evaluate_inventory_overstock(db: Session, rule: Dict) -> List[Dict]:
    """
    Evaluate inventory overstock alert
    Returns items with high turnover days or large inventory amount
    """
    config = rule.get("config", {})
    turnover_days_threshold = config.get("turnover_days_threshold", 180)
    inventory_amount_threshold = config.get("inventory_amount_threshold", 100000)

    sql = text("""
        SELECT material_code, material_name,
               current_stock_qty,
               current_stock_amount,
               turnover_days,
               category
        FROM rpt_stock_current
        WHERE current_stock_qty > 0
        HAVING turnover_days > :turnover_days_threshold
           OR current_stock_amount > :inventory_amount_threshold
        ORDER BY current_stock_amount DESC
        LIMIT 100
    """)

    df = pd.read_sql(sql, db.bind, params={
        "turnover_days_threshold": turnover_days_threshold,
        "inventory_amount_threshold": inventory_amount_threshold,
    })

    results = []
    for _, row in df.iterrows():
        results.append({
            "material_code": row["material_code"],
            "material_name": row["material_name"] if pd.notna(row["material_name"]) else "",
            "current_stock_qty": float(row["current_stock_qty"]) if pd.notna(row["current_stock_qty"]) else 0,
            "current_stock_amount": float(row["current_stock_amount"]) if pd.notna(row["current_stock_amount"]) else 0,
            "turnover_days": float(row["turnover_days"]) if pd.notna(row["turnover_days"]) else 0,
            "category": row["category"] if pd.notna(row["category"]) else "",
        })

    return results


def evaluate_customer_churn(db: Session, rule: Dict, months: int = 12) -> List[Dict]:
    """
    Evaluate customer churn alert
    Returns customers with high recency and low frequency
    """
    config = rule.get("config", {})
    recency_days_threshold = config.get("recency_days_threshold", 90)
    min_frequency = config.get("min_frequency", 2)
    region = config.get("region")

    conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
    params = {}

    if region:
        conditions.append("region = :region")
        params["region"] = region

    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    params["start_date"] = start_date.strftime("%Y-%m-%d")
    params["end_date"] = end_date.strftime("%Y-%m-%d")
    params["recency_days_threshold"] = recency_days_threshold
    params["min_frequency"] = min_frequency
    conditions.append("doc_date BETWEEN :start_date AND :end_date")

    where_sql = " AND ".join(conditions)

    sql = text(f"""
        SELECT customer,
               MAX(doc_date) AS last_purchase_date,
               COUNT(DISTINCT doc_no) AS order_count,
               SUM(tax_included_amount) AS total_amount
        FROM rpt_sales_out_wide
        WHERE {where_sql}
        GROUP BY customer
        HAVING DATEDIFF(NOW(), MAX(doc_date)) > :recency_days_threshold
           AND COUNT(DISTINCT doc_no) >= :min_frequency
        ORDER BY DATEDIFF(NOW(), MAX(doc_date)) DESC
        LIMIT 100
    """)

    df = pd.read_sql(sql, db.bind, params=params)

    results = []
    today = end_date.date()
    for _, row in df.iterrows():
        last_date = row["last_purchase_date"]
        if pd.notna(last_date):
            if isinstance(last_date, datetime):
                recency = (today - last_date.date()).days
            else:
                recency = (today - last_date).days
        else:
            recency = 999

        results.append({
            "customer": row["customer"],
            "last_purchase_date": str(row["last_purchase_date"])[:10] if pd.notna(row["last_purchase_date"]) else "",
            "order_count": int(row["order_count"]) if pd.notna(row["order_count"]) else 0,
            "total_amount": float(row["total_amount"]) if pd.notna(row["total_amount"]) else 0,
            "recency_days": recency,
        })

    return results


def evaluate_expiry_warning(db: Session, rule: Dict) -> List[Dict]:
    """
    Evaluate expiry warning alert
    Returns items expiring within threshold days
    """
    config = rule.get("config", {})
    expiry_days_threshold = config.get("expiry_days_threshold", 30)

    sql = text("""
        SELECT material_code, material_name,
               batch_no,
               expiry_date,
               current_stock_qty,
               DATEDIFF(expiry_date, NOW()) AS days_until_expiry
        FROM rpt_expiry_warning
        WHERE expiry_date IS NOT NULL
          AND DATEDIFF(expiry_date, NOW()) <= :expiry_days_threshold
          AND DATEDIFF(expiry_date, NOW()) >= 0
          AND current_stock_qty > 0
        ORDER BY expiry_date ASC
        LIMIT 100
    """)

    df = pd.read_sql(sql, db.bind, params={"expiry_days_threshold": expiry_days_threshold})

    results = []
    for _, row in df.iterrows():
        results.append({
            "material_code": row["material_code"],
            "material_name": row["material_name"] if pd.notna(row["material_name"]) else "",
            "batch_no": row["batch_no"] if pd.notna(row["batch_no"]) else "",
            "expiry_date": str(row["expiry_date"])[:10] if pd.notna(row["expiry_date"]) else "",
            "current_stock_qty": float(row["current_stock_qty"]) if pd.notna(row["current_stock_qty"]) else 0,
            "days_until_expiry": int(row["days_until_expiry"]) if pd.notna(row["days_until_expiry"]) else 0,
        })

    return results


def execute_alert_rule(db: Session, rule: Dict) -> List[Dict]:
    """
    Execute alert rule and return triggered results
    """
    alert_type = rule.get("alert_type")

    try:
        if alert_type == AlertType.SALES_DECLINE.value:
            return evaluate_sales_decline(db, rule)
        elif alert_type == AlertType.INVENTORY_OVERSTOCK.value:
            return evaluate_inventory_overstock(db, rule)
        elif alert_type == AlertType.CUSTOMER_CHURN.value:
            return evaluate_customer_churn(db, rule)
        elif alert_type == AlertType.EXPIRY_WARNING.value:
            return evaluate_expiry_warning(db, rule)
        else:
            logger.warning(f"Unknown alert type: {alert_type}")
            return []
    except Exception as e:
        logger.error(f"Error executing alert rule {rule.get('id')}: {e}", exc_info=True)
        return []


def create_alert_history(
    db: Session,
    rule_id: int,
    alert_level: str,
    title: str,
    content: str,
    triggered_count: int,
    detail_data: List[Dict],
) -> int:
    """Create alert history record"""
    sql = text("""
        INSERT INTO alert_history (rule_id, alert_level, title, content,
                                 triggered_count, detail_data)
        VALUES (:rule_id, :alert_level, :title, :content,
                :triggered_count, :detail_data)
    """)

    result = db.execute(sql, {
        "rule_id": rule_id,
        "alert_level": alert_level,
        "title": title,
        "content": content,
        "triggered_count": triggered_count,
        "detail_data": json.dumps(detail_data, ensure_ascii=False),
    })
    db.commit()
    return result.lastrowid


def get_alert_history(
    db: Session,
    rule_id: Optional[int] = None,
    is_acknowledged: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict]:
    """Get alert history records"""
    conditions = ["1=1"]
    params = {"limit": limit, "offset": offset}

    if rule_id:
        conditions.append("ah.rule_id = :rule_id")
        params["rule_id"] = rule_id

    if is_acknowledged is not None:
        conditions.append("ah.is_acknowledged = :is_acknowledged")
        params["is_acknowledged"] = is_acknowledged

    where_sql = " AND ".join(conditions)

    sql = text(f"""
        SELECT ah.id, ah.rule_id, ar.name AS rule_name,
               ah.alert_level, ah.title, ah.content,
               ah.triggered_count, ah.detail_data,
               ah.is_acknowledged, ah.acknowledged_by, ah.acknowledged_at,
               ah.created_at
        FROM alert_history ah
        LEFT JOIN alert_rule ar ON ah.rule_id = ar.id
        WHERE {where_sql}
        ORDER BY ah.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    df = pd.read_sql(sql, db.bind, params=params)

    history = []
    for _, row in df.iterrows():
        history.append({
            "id": int(row["id"]),
            "rule_id": int(row["rule_id"]) if pd.notna(row["rule_id"]) else None,
            "rule_name": row["rule_name"] if pd.notna(row["rule_name"]) else None,
            "alert_level": row["alert_level"],
            "title": row["title"],
            "content": row["content"] if pd.notna(row["content"]) else None,
            "triggered_count": int(row["triggered_count"]) if pd.notna(row["triggered_count"]) else 0,
            "detail_data": json.loads(row["detail_data"]) if row["detail_data"] else [],
            "is_acknowledged": bool(row["is_acknowledged"]),
            "acknowledged_by": row["acknowledged_by"] if pd.notna(row["acknowledged_by"]) else None,
            "acknowledged_at": str(row["acknowledged_at"])[:19] if pd.notna(row["acknowledged_at"]) else None,
            "created_at": str(row["created_at"])[:19],
        })

    return history


def acknowledge_alert_history(
    db: Session,
    history_id: int,
    acknowledged_by: str,
) -> bool:
    """Acknowledge an alert history record"""
    sql = text("""
        UPDATE alert_history
        SET is_acknowledged = TRUE,
            acknowledged_by = :acknowledged_by,
            acknowledged_at = NOW()
        WHERE id = :history_id
    """)

    result = db.execute(sql, {
        "history_id": history_id,
        "acknowledged_by": acknowledged_by,
    })
    db.commit()
    return result.rowcount > 0


def get_alert_stats(db: Session, user_id: str) -> Dict:
    """Get alert statistics"""
    # Total and enabled rules
    sql_rules = text("""
        SELECT COUNT(*) AS total_rules,
               SUM(CASE WHEN is_enabled THEN 1 ELSE 0 END) AS enabled_rules
        FROM alert_rule
    """)
    df_rules = pd.read_sql(sql_rules, db.bind)
    total_rules = int(df_rules.iloc[0]["total_rules"]) if not df_rules.empty else 0
    enabled_rules = int(df_rules.iloc[0]["enabled_rules"] or 0) if not df_rules.empty else 0

    # Triggered this month
    sql_month = text("""
        SELECT COUNT(*) AS triggered_this_month
        FROM alert_history
        WHERE created_at >= DATE_FORMAT(NOW(), '%Y-%m-01')
    """)
    df_month = pd.read_sql(sql_month, db.bind)
    triggered_this_month = int(df_month.iloc[0]["triggered_this_month"]) if not df_month.empty else 0

    # Unacknowledged count
    sql_unack = text("SELECT COUNT(*) AS unacknowledged FROM alert_history WHERE is_acknowledged = FALSE")
    df_unack = pd.read_sql(sql_unack, db.bind)
    unacknowledged_count = int(df_unack.iloc[0]["unacknowledged"]) if not df_unack.empty else 0

    # Unread notifications for user
    sql_notif = text("""
        SELECT COUNT(*) AS unread_notifications
        FROM notification
        WHERE user_id = :user_id AND is_read = FALSE
    """)
    df_notif = pd.read_sql(sql_notif, db.bind, params={"user_id": user_id})
    unread_notifications = int(df_notif.iloc[0]["unread_notifications"] or 0) if not df_notif.empty else 0

    return {
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "triggered_this_month": triggered_this_month,
        "unacknowledged_count": unacknowledged_count,
        "unread_notifications": unread_notifications,
    }


def create_notification(
    db: Session,
    user_id: str,
    alert_history_id: Optional[int],
    title: str,
    content: str,
) -> int:
    """Create in-app notification"""
    sql = text("""
        INSERT INTO notification (user_id, alert_history_id, title, content)
        VALUES (:user_id, :alert_history_id, :title, :content)
    """)

    result = db.execute(sql, {
        "user_id": user_id,
        "alert_history_id": alert_history_id,
        "title": title,
        "content": content,
    })
    db.commit()
    return result.lastrowid


def get_notifications(
    db: Session,
    user_id: str,
    is_read: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict]:
    """Get user notifications"""
    conditions = ["user_id = :user_id"]
    params = {"user_id": user_id, "limit": limit, "offset": offset}

    if is_read is not None:
        conditions.append("is_read = :is_read")
        params["is_read"] = is_read

    where_sql = " AND ".join(conditions)

    sql = text(f"""
        SELECT id, user_id, alert_history_id, title, content,
               is_read, read_at, created_at
        FROM notification
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    df = pd.read_sql(sql, db.bind, params=params)

    notifications = []
    for _, row in df.iterrows():
        notifications.append({
            "id": int(row["id"]),
            "user_id": row["user_id"],
            "alert_history_id": int(row["alert_history_id"]) if pd.notna(row["alert_history_id"]) else None,
            "title": row["title"],
            "content": row["content"] if pd.notna(row["content"]) else None,
            "is_read": bool(row["is_read"]),
            "read_at": str(row["read_at"])[:19] if pd.notna(row["read_at"]) else None,
            "created_at": str(row["created_at"])[:19],
        })

    return notifications


def mark_notification_read(db: Session, notification_id: int) -> bool:
    """Mark notification as read"""
    sql = text("""
        UPDATE notification
        SET is_read = TRUE, read_at = NOW()
        WHERE id = :notification_id
    """)

    result = db.execute(sql, {"notification_id": notification_id})
    db.commit()
    return result.rowcount > 0
