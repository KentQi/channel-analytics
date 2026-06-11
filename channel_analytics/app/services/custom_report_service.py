"""
Custom Report Service
Provides dynamic SQL building and report execution
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 表名中文映射
TABLE_NAME_MAPPING = {
    "rpt_sales_out_wide": "销售出库明细",
    "rpt_stock_current": "当前库存",
    "rpt_customer_summary": "客户汇总",
    "rpt_sales_monthly": "月度销售",
    "rpt_repurchase_analysis": "复购分析",
    "rpt_expiry_warning": "过期预警",
}

# 字段中文映射（匹配实际数据库列名）
FIELD_NAME_MAPPING = {
    # 销售出库明细
    "doc_no": "单据编号",
    "doc_date": "单据日期",
    "material_code": "物料编码",
    "material_name": "物料名称",
    "customer": "客户",
    "region": "大区",
    "account_manager": "客户经理",
    "region_manager": "区域经理",
    "warehouse": "仓库",
    "sales_out_qty": "销售出库数量",
    "invoiced_qty": "开票数量",
    "dispatch_qty": "发货数量",
    "tax_included_amount": "含税金额",
    "tax_included_unit_price": "含税单价",
    "batch_no": "批次号",
    "expiry_date": "有效期",
    "category": "商品品类",
    "brand": "品牌",
    "tx_type": "事务类型",
    "tx_type_name": "事务类型名称",
    # 当前库存 - 表不存在，使用占位
    "current_stock_qty": "当前库存数量",
    "current_stock_amount": "当前库存金额",
    "available_qty": "可用数量",
    "turnover_days": "周转天数",
    "avg_cost": "平均成本",
    # 客户汇总 - 表不存在，使用占位
    "total_amount": "累计金额",
    "total_quantity": "累计数量",
    "order_count": "订单次数",
    "avg_order_amount": "平均订单金额",
    "first_purchase_date": "首次购买日期",
    "last_purchase_date": "最后购买日期",
    "customer_type": "客户类型",
    # 月度销售 - 表不存在，使用占位
    "sale_month": "销售月份",
    "monthly_quantity": "月度数量",
    "monthly_amount": "月度金额",
    "yoy_growth": "同比增长率",
    "mom_growth": "环比增长率",
    # 复购分析 - 表不存在，使用占位
    "repurchase_date": "复购日期",
    "repurchase_interval": "复购间隔",
    "initial_amount": "初次购买金额",
    "repurchase_amount": "复购金额",
    # 过期预警
    "material_batch_available_qty": "批次可用数量",
    "remaining_expiry_months": "剩余过期月数",
    "expiry_status": "过期状态",
    "expiry_warning": "过期预警",
    "days_until_expiry": "距过期天数",
}

# White-listed tables and their allowed fields (matching actual DB column names)
ALLOWED_REPORT_TABLES = {
    "rpt_sales_out_wide": {
        "fields": [
            "doc_no", "doc_date", "material_code", "material_name",
            "customer", "region", "account_manager", "region_manager", "warehouse",
            "sales_out_qty", "invoiced_qty", "dispatch_qty",
            "tax_included_amount", "tax_included_unit_price",
            "batch_no", "category", "brand", "tx_type", "tx_type_name"
        ],
        "date_field": "doc_date",
        "numeric_fields": ["sales_out_qty", "invoiced_qty", "dispatch_qty", "tax_included_amount", "tax_included_unit_price"],
    },
    "rpt_stock_current": {
        "fields": [
            "material_code", "material_name", "warehouse",
            "category", "brand"
        ],
        "numeric_fields": [],
    },
    "rpt_customer_summary": {
        "fields": [
            "customer", "region", "account_manager",
            "material_code", "material_name"
        ],
        "numeric_fields": [],
    },
    "rpt_sales_monthly": {
        "fields": [
            "region", "account_manager", "category",
            "material_code", "material_name"
        ],
        "numeric_fields": [],
    },
    "rpt_repurchase_analysis": {
        "fields": [
            "customer", "material_code", "material_name",
            "region", "account_manager"
        ],
        "numeric_fields": [],
    },
    "rpt_expiry_warning": {
        "fields": [
            "material_code", "material_name", "batch_no",
            "expiry_date", "material_batch_available_qty", "remaining_expiry_months",
            "warehouse", "category", "brand", "expiry_status"
        ],
        "numeric_fields": ["material_batch_available_qty", "remaining_expiry_months"],
    },
}


def get_available_tables() -> List[Dict]:
    """Return list of available tables with metadata"""
    tables = []
    for table_name, meta in ALLOWED_REPORT_TABLES.items():
        tables.append({
            "name": table_name,
            "display_name": TABLE_NAME_MAPPING.get(table_name, table_name),
            "field_count": len(meta["fields"]),
            "has_date_field": "date_field" in meta,
        })
    return tables


def get_table_fields(table_name: str) -> List[Dict]:
    """Return field list for a table"""
    if table_name not in ALLOWED_REPORT_TABLES:
        return []
    meta = ALLOWED_REPORT_TABLES[table_name]
    fields = []
    for field in meta["fields"]:
        fields.append({
            "name": field,
            "display_name": FIELD_NAME_MAPPING.get(field, field),
            "is_numeric": field in meta.get("numeric_fields", []),
            "is_date": field == meta.get("date_field"),
        })
    return fields


def validate_config(config: Dict) -> tuple[bool, str]:
    """Validate report config, return (is_valid, error_message)"""
    table = config.get("table")
    if not table:
        return False, "缺少数据表名"
    if table not in ALLOWED_REPORT_TABLES:
        return False, f"不支持的数据表: {table}"

    meta = ALLOWED_REPORT_TABLES[table]
    allowed_fields = set(meta["fields"])

    # Validate date_field exists in fields list
    if "date_field" in meta and meta["date_field"] not in allowed_fields:
        return False, f"date_field '{meta['date_field']}' not in fields list for table {table}"

    # Validate numeric_fields exist in fields list
    for nf in meta.get("numeric_fields", []):
        if nf not in allowed_fields:
            return False, f"numeric_field '{nf}' not in fields list for table {table}"

    fields = config.get("fields", [])
    if not fields:
        return False, "请选择至少一个字段"

    for field in fields:
        if field not in allowed_fields:
            return False, f"字段 {field} 不在表 {table} 中"

    return True, ""


def clean_invalid_fields(config: Dict) -> Dict:
    """Remove fields that are not in the allowed list (for migrating old configs)"""
    table = config.get("table")
    if table not in ALLOWED_REPORT_TABLES:
        return config

    allowed_fields = set(ALLOWED_REPORT_TABLES[table]["fields"])
    valid_fields = [f for f in config.get("fields", []) if f in allowed_fields]

    # Clean filters, sort, group_by - remove references to fields not in allowed list
    valid_filters = [
        f for f in config.get("filters", [])
        if f.get("field") in allowed_fields
    ]
    valid_sort = [
        s for s in config.get("sort", [])
        if s.get("field") in allowed_fields
    ]
    valid_group_by = [
        g for g in config.get("group_by", [])
        if g in allowed_fields
    ]

    return {
        **config,
        "fields": valid_fields,
        "filters": valid_filters,
        "sort": valid_sort,
        "group_by": valid_group_by,
    }


def build_report_sql(config: Dict, page: int = 1, page_size: int = 100,
                     include_pagination: bool = True) -> tuple[str, Dict]:
    """
    Build SQL query from report config
    Returns (sql, params)
    """
    table = config["table"]
    fields = config.get("fields", ["*"])
    filters = config.get("filters", [])
    group_by = config.get("group_by", [])
    sort = config.get("sort", [])

    # Validate fields
    allowed_fields = ALLOWED_REPORT_TABLES[table]["fields"]
    select_fields = []
    for f in fields:
        if f in allowed_fields:
            select_fields.append(f)

    if not select_fields:
        select_fields = ["*"]

    # Build SELECT
    sql = f"SELECT {', '.join(select_fields)} FROM {table}"

    # Build WHERE
    params = {}
    conditions = []

    for i, f in enumerate(filters):
        field = f.get("field")
        op = f.get("op", "=")
        value = f.get("value")

        if not field or value is None:
            continue

        if field not in allowed_fields:
            continue

        param_key = f"p{i}"

        if op == "like":
            conditions.append(f"{field} LIKE :{param_key}")
            params[param_key] = f"%{value}%"
        elif op == "gt":
            conditions.append(f"{field} > :{param_key}")
            params[param_key] = value
        elif op == "gte":
            conditions.append(f"{field} >= :{param_key}")
            params[param_key] = value
        elif op == "lt":
            conditions.append(f"{field} < :{param_key}")
            params[param_key] = value
        elif op == "lte":
            conditions.append(f"{field} <= :{param_key}")
            params[param_key] = value
        elif op == "in":
            if isinstance(value, list):
                placeholders = ", ".join([f":{param_key}_{j}" for j in range(len(value))])
                conditions.append(f"{field} IN ({placeholders})")
                for j, v in enumerate(value):
                    params[f"{param_key}_{j}"] = v
        elif op == "not_in":
            if isinstance(value, list):
                placeholders = ", ".join([f":{param_key}_{j}" for j in range(len(value))])
                conditions.append(f"{field} NOT IN ({placeholders})")
                for j, v in enumerate(value):
                    params[f"{param_key}_{j}"] = v
        else:  # = and other
            conditions.append(f"{field} = :{param_key}")
            params[param_key] = value

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    # Build GROUP BY
    if group_by:
        valid_group_by = [f for f in group_by if f in allowed_fields]
        if valid_group_by:
            sql += f" GROUP BY {', '.join(valid_group_by)}"

    # Build ORDER BY
    if sort:
        order_parts = []
        for s in sort:
            field = s.get("field")
            direction = s.get("direction", "asc").lower()
            if field in allowed_fields and direction in ("asc", "desc"):
                order_parts.append(f"{field} {direction}")
        if order_parts:
            sql += f" ORDER BY {', '.join(order_parts)}"

    # Add LIMIT/OFFSET for pagination
    if include_pagination:
        offset = (page - 1) * page_size
        sql += f" LIMIT {page_size} OFFSET {offset}"

    return sql, params


def execute_report(
    db: Session,
    config: Dict,
    page: int = 1,
    page_size: int = 100,
) -> Dict:
    """
    Execute report query and return results with metadata
    """
    is_valid, error = validate_config(config)
    if not is_valid:
        return {"success": False, "error": error}

    try:
        sql, params = build_report_sql(config, page, page_size)
        df = pd.read_sql(text(sql), db.bind, params=params)

        # Convert DataFrame to records
        records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                if hasattr(val, 'isoformat'):
                    record[col] = val.isoformat()
                elif str(val) == 'NaT':
                    record[col] = None
                elif str(val) == 'nan':
                    record[col] = None
                else:
                    record[col] = val
            records.append(record)

        # Get total count (without LIMIT)
        count_sql, count_params = build_report_sql(config, page=1, page_size=1000000, include_pagination=False)
        try:
            count_df = pd.read_sql(text(count_sql), db.bind, params=count_params)
            total = len(count_df)
        except:
            total = len(records)

        return {
            "success": True,
            "data": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "fields": list(df.columns),
            "field_display_names": {col: FIELD_NAME_MAPPING.get(col, col) for col in df.columns},
        }

    except Exception as e:
        logger.error(f"Error executing report: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def export_report(
    db: Session,
    config: Dict,
    format: str = "csv",
) -> Dict:
    """Export report data"""
    result = execute_report(db, config, page=1, page_size=1000000)
    if not result.get("success"):
        return result
    return result


# ============ Template Management ============

def save_template(
    db: Session,
    name: str,
    config: Dict,
    description: Optional[str],
    is_public: bool,
    created_by: str,
) -> int:
    """Save report template to database"""
    sql = text("""
        INSERT INTO custom_report_template (name, description, config, created_by, is_public)
        VALUES (:name, :description, :config, :created_by, :is_public)
    """)
    result = db.execute(sql, {
        "name": name,
        "description": description,
        "config": json.dumps(config, ensure_ascii=False),
        "created_by": created_by,
        "is_public": is_public,
    })
    db.commit()
    return result.lastrowid


def list_templates(
    db: Session,
    user_id: str,
    include_public: bool = True,
) -> List[Dict]:
    """List report templates visible to user"""
    if include_public:
        sql = text("""
            SELECT id, name, description, config, created_by, created_at,
                   updated_at, is_public
            FROM custom_report_template
            WHERE created_by = :user_id OR is_public = TRUE
            ORDER BY updated_at DESC
        """)
        df = pd.read_sql(sql, db.bind, params={"user_id": user_id})
    else:
        sql = text("""
            SELECT id, name, description, config, created_by, created_at,
                   updated_at, is_public
            FROM custom_report_template
            WHERE created_by = :user_id
            ORDER BY updated_at DESC
        """)
        df = pd.read_sql(sql, db.bind, params={"user_id": user_id})

    templates = []
    for _, row in df.iterrows():
        templates.append({
            "id": int(row["id"]),
            "name": row["name"],
            "description": row["description"] if pd.notna(row["description"]) else None,
            "config": json.loads(row["config"]) if row["config"] else {},
            "created_by": row["created_by"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "is_public": bool(row["is_public"]),
        })
    return templates


def get_template(db: Session, template_id: int) -> Optional[Dict]:
    """Get single template by ID"""
    sql = text("""
        SELECT id, name, description, config, created_by, created_at,
               updated_at, is_public
        FROM custom_report_template
        WHERE id = :template_id
    """)
    df = pd.read_sql(sql, db.bind, params={"template_id": template_id})

    if df.empty:
        return None

    row = df.iloc[0]
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "description": row["description"] if pd.notna(row["description"]) else None,
        "config": json.loads(row["config"]) if row["config"] else {},
        "created_by": row["created_by"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "is_public": bool(row["is_public"]),
    }


def update_template(
    db: Session,
    template_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict] = None,
    is_public: Optional[bool] = None,
) -> bool:
    """Update existing template"""
    updates = []
    params = {"template_id": template_id}

    if name is not None:
        updates.append("name = :name")
        params["name"] = name

    if description is not None:
        updates.append("description = :description")
        params["description"] = description

    if config is not None:
        updates.append("config = :config")
        params["config"] = json.dumps(config, ensure_ascii=False)

    if is_public is not None:
        updates.append("is_public = :is_public")
        params["is_public"] = is_public

    if not updates:
        return False

    updates.append("updated_at = NOW()")

    sql = text(f"""
        UPDATE custom_report_template
        SET {', '.join(updates)}
        WHERE id = :template_id
    """)
    result = db.execute(sql, params)
    db.commit()
    return result.rowcount > 0


def delete_template(db: Session, template_id: int) -> bool:
    """Delete template"""
    sql = text("DELETE FROM custom_report_template WHERE id = :template_id")
    result = db.execute(sql, {"template_id": template_id})
    db.commit()
    return result.rowcount > 0


def share_template(
    db: Session,
    template_id: int,
    target_users: Optional[List[str]] = None,
    target_roles: Optional[List[str]] = None,
) -> bool:
    """Share template to users/roles"""
    # Clean old shares
    sql_delete = text("DELETE FROM custom_report_share WHERE report_id = :report_id")
    db.execute(sql_delete, {"report_id": template_id})

    # Insert new shares
    if target_users:
        for user in target_users:
            sql_insert = text("""
                INSERT INTO custom_report_share (report_id, target_user)
                VALUES (:report_id, :target_user)
            """)
            db.execute(sql_insert, {"report_id": template_id, "target_user": user})

    if target_roles:
        for role in target_roles:
            sql_insert = text("""
                INSERT INTO custom_report_share (report_id, target_role)
                VALUES (:report_id, :target_role)
            """)
            db.execute(sql_insert, {"report_id": template_id, "target_role": role})

    db.commit()
    return True
