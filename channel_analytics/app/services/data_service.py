"""
数据维护服务 — 对齐原版 info_maint.py 的 6 张维表 CRUD + 导入校验逻辑
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.field_mapping import (
    ABC_VALID, LIFECYCLE_VALID, CUST_CHANNEL_VALID, CUST_STATUS_VALID,
    MAX_IMPORT_ROWS,
)

logger = logging.getLogger(__name__)


# ============================================================
# 通用工具
# ============================================================

def clean_value(val):
    """空值/NaN/NaT 统一归 None，字符串 strip"""
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.strip()
        return val if val else None
    return val


def validate_enum(val, valid_list, field_name):
    """枚举校验，返回错误信息或 None"""
    if val is None or val == "":
        return None
    if val not in valid_list:
        return f"{field_name} 必须是以下之一: {', '.join(valid_list)}"
    return None


def normalize_time_to_month(val):
    """202601 / 2026/01 / 2026/01/01 → 2026/01"""
    if val is None:
        return None
    s = str(val).strip().replace("-", "/")
    # 纯数字 6 位: 202601
    if s.isdigit() and len(s) == 6:
        return f"{s[:4]}/{s[4:]}"
    # 已经是 2026/01 格式
    parts = s.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1].zfill(2)}"
    return s


def parse_pagination_params(page: int = 1, page_size: int = 100):
    offset = (page - 1) * page_size
    return offset, page_size


def build_pagination_response(items, total, page, page_size):
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


# ============================================================
# 商品属性 dim_product_attr
# ============================================================

GOODS_FIELDS = [
    "material_code", "material_name", "category", "first_stock_in_date",
    "abc_class", "lifecycle_status", "custom_flag", "promoted_flag",
]
GOODS_REQUIRED_COLS = ["material_code", "material_name", "category", "lifecycle_status"]

# 用户可编辑的字段（ETL 字段：material_name/category/first_stock_in_date 由 ETL 维护）
USER_EDITABLE_FIELDS = {"abc_class", "lifecycle_status", "custom_flag", "promoted_flag"}


def get_product_attrs(db: Session, page: int = 1, page_size: int = 100,
                      search: Optional[str] = None) -> Dict:
    offset, limit = parse_pagination_params(page, page_size)
    where_clause = ""
    params = {}
    if search:
        where_clause = "WHERE material_code LIKE :search OR material_name LIKE :search"
        params["search"] = f"%{search}%"

    count_sql = text(f"SELECT COUNT(*) FROM dim_product_attr {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    data_sql = text(f"""
        SELECT id, material_code, material_name, category, first_stock_in_date,
               abc_class, lifecycle_status, custom_flag, promoted_flag,
               created_at, updated_at
        FROM dim_product_attr {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)
    params.update({"limit": limit, "offset": offset})
    results = db.execute(data_sql, params).fetchall()
    items = [
        {
            "id": r[0], "material_code": r[1], "material_name": r[2],
            "category": r[3], "first_stock_in_date": r[4],
            "abc_class": r[5], "lifecycle_status": r[6],
            "custom_flag": r[7], "promoted_flag": r[8],
            "created_at": r[9].isoformat() if r[9] else None,
            "updated_at": r[10].isoformat() if r[10] else None,
        }
        for r in results
    ]
    return build_pagination_response(items, total, page, page_size)


def update_product_attr(db: Session, material_code: str, data: Dict) -> bool:
    """手动编辑商品属性 - 只允许用户字段"""
    update_fields = {k: v for k, v in data.items() if k in USER_EDITABLE_FIELDS}
    if not update_fields:
        return False
    update_fields["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    sql = text(f"UPDATE dim_product_attr SET {set_clause} WHERE material_code = :mc")
    update_fields["mc"] = material_code
    result = db.execute(sql, update_fields)
    db.commit()
    return result.rowcount > 0


def import_product_attrs(db: Session, records: List[Dict]) -> Dict:
    """导入商品属性 - 只更新 4 个用户字段

    ETL 字段（material_name/category/first_stock_in_date）由 ETL 维护，不通过导入写入。
    如果物料编码在 stg_stock_in 中不存在（dim_product_attr 也没有），自动插入占位记录，
    ETL 字段留空，下次 ETL 会被回填。
    """
    # 校验行数
    if len(records) > MAX_IMPORT_ROWS:
        return {"success": 0, "error": len(records),
                "errors": [{"row": 0, "error": f"导入行数超过上限 {MAX_IMPORT_ROWS}"}]}

    success_count = 0
    error_count = 0
    errors = []

    for idx, record in enumerate(records):
        try:
            # 提取物料编码 + 4 个用户字段
            mc = clean_value(record.get("material_code") or record.get("物料编码"))
            abc = clean_value(record.get("abc_class") or record.get("ABC分类"))
            lc = clean_value(record.get("lifecycle_status") or record.get("生命周期"))
            cf = clean_value(record.get("custom_flag") or record.get("定制标记"))
            pf = clean_value(record.get("promoted_flag") or record.get("主推标记"))

            # 必填校验
            if not mc:
                error_count += 1
                errors.append({"row": idx + 1, "error": "物料编码不能为空"})
                continue

            # 枚举校验
            if abc:
                err = validate_enum(abc, list(ABC_VALID), "ABC分类")
                if err:
                    error_count += 1
                    errors.append({"row": idx + 1, "error": err})
                    continue
            if lc:
                err = validate_enum(lc, list(LIFECYCLE_VALID), "生命周期")
                if err:
                    error_count += 1
                    errors.append({"row": idx + 1, "error": err})
                    continue

            # 检查物料是否存在
            exists = db.execute(
                text("SELECT id FROM dim_product_attr WHERE material_code = :mc"),
                {"mc": mc}
            ).fetchone()

            user_fields = {k: v for k, v in {
                "abc_class": abc, "lifecycle_status": lc,
                "custom_flag": cf, "promoted_flag": pf,
            }.items() if v is not None and v != ""}

            now = datetime.now()

            if not exists:
                # 物料在 dim_product_attr 中不存在，自动插入占位记录
                # ETL 字段留空，lifecycle_status 默认为 '持续销售'（导入场景下用户主动设的）
                db.execute(text("""
                    INSERT INTO dim_product_attr
                        (material_code, material_name, category, first_stock_in_date,
                         abc_class, lifecycle_status, custom_flag, promoted_flag,
                         created_at, updated_at)
                    VALUES (:mc, '', '', NULL,
                            :abc, :lc, :cf, :pf,
                            :u, :u)
                """), {
                    "mc": mc,
                    "abc": abc or "",
                    "lc": lc or "持续销售",
                    "cf": int(cf) if cf and cf.isdigit() else (1 if cf else 0),
                    "pf": int(pf) if pf and pf.isdigit() else (1 if pf else 0),
                    "u": now,
                })
            else:
                # 更新 4 个用户字段
                if user_fields:
                    user_fields["updated_at"] = now
                    set_clause = ", ".join([f"{k} = :{k}" for k in user_fields.keys()])
                    user_fields["mc"] = mc
                    db.execute(
                        text(f"UPDATE dim_product_attr SET {set_clause} WHERE material_code = :mc"),
                        user_fields
                    )

            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"row": idx + 1, "error": str(e)})

    db.commit()
    return {"success": success_count, "error": error_count, "errors": errors}


def _get_earliest_stock_in_date(db: Session, material_code: str) -> Optional[str]:
    """从 stg_stock_in 取最早审核日期"""
    try:
        sql = text("""
            SELECT MIN(audit_date) FROM stg_stock_in
            WHERE material_code = :mc AND audit_date IS NOT NULL
        """)
        result = db.execute(sql, {"mc": material_code}).scalar()
        if result:
            if hasattr(result, 'strftime'):
                return result.strftime('%Y/%m/%d')
            return str(result)[:10]
    except Exception:
        pass
    return None


def update_first_stock_in_date(db: Session) -> Dict:
    """兼容旧调用：转发到 sync_product_dimension_from_stock_in"""
    return sync_product_dimension_from_stock_in(db)


def sync_product_dimension_from_stock_in(db: Session) -> Dict:
    """从 stg_stock_in + stg_stock_current 同步物料维度到 dim_product_attr

    数据源合并：
    - stg_stock_in（主）：提供 material_code, material_name, first_stock_in_date
    - stg_stock_current（辅）：补充只有库存没有入库的物料

    ETL 字段：material_code, material_name, first_stock_in_date
    用户字段：abc_class, lifecycle_status, custom_flag, promoted_flag（不触碰）

    没有 first_stock_in_date 的物料（只有库存）默认填 2025-01-01
    """
    # 1. 从 stg_stock_in 取
    sql_in = text("""
        SELECT material_code,
               MAX(material_name) AS material_name,
               MIN(audit_date) AS first_stock_in_date
        FROM stg_stock_in
        WHERE material_code IS NOT NULL AND material_code != ''
        GROUP BY material_code
    """)
    rows_in = {r[0]: (r[1], r[2]) for r in db.execute(sql_in).fetchall()}

    # 2. 从 stg_stock_current 取（补充）
    sql_cur = text("""
        SELECT material_code, MAX(material_name) AS material_name
        FROM stg_stock_current
        WHERE material_code IS NOT NULL AND material_code != ''
        GROUP BY material_code
    """)
    rows_cur = {r[0]: r[1] for r in db.execute(sql_cur).fetchall()}

    # 3. 合并物料集合
    all_codes = set(rows_in.keys()) | set(rows_cur.keys())

    inserted = 0
    updated = 0
    now = datetime.now()
    default_fsd = "2025-01-01"  # 没有入库时间的物料默认值

    for mc in all_codes:
        # 优先取入库单的名称，没有则取现存量
        in_data = rows_in.get(mc)
        name = (in_data[0] if in_data else None) or rows_cur.get(mc)
        fsd_date = in_data[1] if in_data else None
        fsd_str = fsd_date.strftime("%Y-%m-%d") if fsd_date else default_fsd

        exists_row = db.execute(
            text("SELECT id FROM dim_product_attr WHERE material_code = :mc"),
            {"mc": mc}
        ).fetchone()

        if exists_row:
            db.execute(text("""
                UPDATE dim_product_attr
                SET material_name = :name,
                    first_stock_in_date = :fsd,
                    updated_at = :u
                WHERE material_code = :mc
            """), {"mc": mc, "name": name or "", "fsd": fsd_str, "u": now})
            updated += 1
        else:
            db.execute(text("""
                INSERT INTO dim_product_attr
                    (material_code, material_name, category, first_stock_in_date,
                     abc_class, lifecycle_status, custom_flag, promoted_flag,
                     created_at, updated_at)
                VALUES (:mc, :name, '', :fsd,
                        '', '新品', 0, 0,
                        :u, :u)
            """), {"mc": mc, "name": name or "", "fsd": fsd_str, "u": now})
            inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated}


def update_lifecycle_status(db: Session) -> Dict:
    """简化的生命周期状态机

    规则：
    1. 售完即止 + 现存量总库存=0 → '淘汰'
    2. '新品' / '持续销售' / 空值：按 today 与 first_stock_in_date 重算
       - ≤ 90 天 → '新品'
       - > 90 天 → '持续销售'
       - 没有 first_stock_in_date → '持续销售'
    3. 不覆盖用户已设置的'重新上架'等手动状态
    """
    today = date.today()
    now = datetime.now()
    updated = 0
    skipped = 0

    prods = db.execute(text("""
        SELECT id, material_code, lifecycle_status, first_stock_in_date
        FROM dim_product_attr
    """)).fetchall()

    for prod_id, mc, current_status, fsd in prods:
        # 字符串归一
        cur = (current_status or "").strip()

        # 规则 3: 用户手动设置的状态（重新上架）不覆盖
        if cur == "重新上架":
            skipped += 1
            continue

        new_status = None

        if cur == "售完即止":
            stock = db.execute(text("""
                SELECT COALESCE(SUM(current_stock), 0) FROM stg_stock_current
                WHERE material_code = :mc
            """), {"mc": mc}).scalar() or 0
            if stock <= 0:
                new_status = "淘汰"
        elif cur in ("", "新品", "持续销售", "淘汰"):
            # 规则 2: 重算
            fsd_date = _to_date_local(fsd)
            if fsd_date:
                days = (today - fsd_date).days
                new_status = "新品" if days <= 90 else "持续销售"
            else:
                new_status = "持续销售"

        if new_status and new_status != cur:
            db.execute(text("""
                UPDATE dim_product_attr SET lifecycle_status = :s, updated_at = :u
                WHERE id = :id
            """), {"s": new_status, "u": now, "id": prod_id})
            updated += 1

    db.commit()
    return {"updated": updated, "skipped": skipped}


def _to_date_local(val) -> Optional[date]:
    """本地辅助：将各种类型转换为 date"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val or val in ("NaT", "None"):
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


# ============================================================
# 客户信息 dim_customer
# ============================================================

CUST_FIELDS = [
    "customer_name", "region", "province", "sales_area",
    "channel", "cooperation_status", "account_manager",
]
CUST_REQUIRED_COLS = [
    "customer_name", "region", "province", "sales_area",
    "channel", "cooperation_status", "account_manager",
]


def get_customers(db: Session, page: int = 1, page_size: int = 100,
                  search: Optional[str] = None, region: Optional[str] = None) -> Dict:
    offset, limit = parse_pagination_params(page, page_size)
    conditions = []
    params = {}
    if search:
        conditions.append("(customer_name LIKE :search OR region LIKE :search)")
        params["search"] = f"%{search}%"
    if region:
        conditions.append("region = :region")
        params["region"] = region
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_sql = text(f"SELECT COUNT(*) FROM dim_customer {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    data_sql = text(f"""
        SELECT id, customer_name, region, province, sales_area,
               channel, cooperation_status, account_manager,
               created_at, updated_at
        FROM dim_customer {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)
    params.update({"limit": limit, "offset": offset})
    results = db.execute(data_sql, params).fetchall()
    items = [
        {
            "id": r[0], "customer_name": r[1], "region": r[2],
            "province": r[3], "sales_area": r[4], "channel": r[5],
            "cooperation_status": r[6], "account_manager": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
            "updated_at": r[9].isoformat() if r[9] else None,
        }
        for r in results
    ]
    return build_pagination_response(items, total, page, page_size)


def update_customer(db: Session, customer_name: str, data: Dict) -> bool:
    allowed_fields = CUST_FIELDS
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_fields:
        return False
    update_fields["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    sql = text(f"UPDATE dim_customer SET {set_clause} WHERE customer_name = :cn")
    update_fields["cn"] = customer_name
    result = db.execute(sql, update_fields)
    db.commit()
    return result.rowcount > 0


def import_customers(db: Session, records: List[Dict]) -> Dict:
    if len(records) > MAX_IMPORT_ROWS:
        return {"success": 0, "error": len(records),
                "errors": [{"row": 0, "error": f"导入行数超过上限 {MAX_IMPORT_ROWS}"}]}

    success_count = 0
    error_count = 0
    errors = []

    for idx, record in enumerate(records):
        try:
            cn = clean_value(record.get("customer_name") or record.get("客户名称"))
            region = clean_value(record.get("region") or record.get("大区"))
            province = clean_value(record.get("province") or record.get("省区"))
            sa = clean_value(record.get("sales_area") or record.get("销售区域"))
            ch = clean_value(record.get("channel") or record.get("客户渠道"))
            cs = clean_value(record.get("cooperation_status") or record.get("合作状态"))
            am = clean_value(record.get("account_manager") or record.get("客户经理"))

            # 必填校验
            missing = []
            if not cn: missing.append("客户名称")
            if not region: missing.append("大区")
            if not province: missing.append("省区")
            if not sa: missing.append("销售区域")
            if missing:
                error_count += 1
                errors.append({"row": idx + 1, "error": f"必填字段为空: {', '.join(missing)}"})
                continue

            # 枚举校验
            if ch:
                err = validate_enum(ch, CUST_CHANNEL_VALID, "客户渠道")
                if err:
                    error_count += 1
                    errors.append({"row": idx + 1, "error": err})
                    continue
            if cs:
                err = validate_enum(cs, CUST_STATUS_VALID, "合作状态")
                if err:
                    error_count += 1
                    errors.append({"row": idx + 1, "error": err})
                    continue

            now = datetime.now()
            fields = {
                "customer_name": cn, "region": region, "province": province,
                "sales_area": sa, "channel": ch, "cooperation_status": cs,
                "account_manager": am,
            }

            check = text("SELECT id FROM dim_customer WHERE customer_name = :cn")
            exists = db.execute(check, {"cn": cn}).fetchone()

            if exists:
                set_fields = {k: v for k, v in fields.items() if k != "customer_name"}
                set_fields["updated_at"] = now
                set_clause = ", ".join([f"{k} = :{k}" for k in set_fields.keys()])
                sql = text(f"UPDATE dim_customer SET {set_clause} WHERE customer_name = :cn")
                set_fields["cn"] = cn
                db.execute(sql, set_fields)
            else:
                fields["created_at"] = now
                fields["updated_at"] = now
                columns = ", ".join(fields.keys())
                placeholders = ", ".join([f":{k}" for k in fields.keys()])
                sql = text(f"INSERT INTO dim_customer ({columns}) VALUES ({placeholders})")
                db.execute(sql, fields)

            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"row": idx + 1, "error": str(e)})

    db.commit()
    return {"success": success_count, "error": error_count, "errors": errors}


# ============================================================
# 省区指标 dim_business_indicator_region
# ============================================================

REGION_IND_FIELDS = ["period", "region", "province", "sales_area", "manager", "monthly_target"]
REGION_IND_REQUIRED = ["period", "region", "province", "sales_area", "manager", "monthly_target"]


def get_region_indicators(db: Session, page: int = 1, page_size: int = 100,
                          search: Optional[str] = None) -> Dict:
    offset, limit = parse_pagination_params(page, page_size)
    where_clause = ""
    params = {}
    if search:
        where_clause = "WHERE region LIKE :search OR province LIKE :search"
        params["search"] = f"%{search}%"

    count_sql = text(f"SELECT COUNT(*) FROM dim_business_indicator_region {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    data_sql = text(f"""
        SELECT id, period, region, province, sales_area, manager,
               monthly_target, created_at, updated_at
        FROM dim_business_indicator_region {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)
    params.update({"limit": limit, "offset": offset})
    results = db.execute(data_sql, params).fetchall()
    items = [
        {
            "id": r[0], "period": r[1], "region": r[2],
            "province": r[3], "sales_area": r[4], "manager": r[5],
            "monthly_target": float(r[6]) if r[6] else 0,
            "created_at": r[7].isoformat() if r[7] else None,
            "updated_at": r[8].isoformat() if r[8] else None,
        }
        for r in results
    ]
    return build_pagination_response(items, total, page, page_size)


def update_region_indicator(db: Session, region: str, period: str, data: Dict) -> bool:
    allowed_fields = ["region", "province", "sales_area", "manager", "monthly_target"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_fields:
        return False
    update_fields["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    sql = text(f"""
        UPDATE dim_business_indicator_region SET {set_clause}
        WHERE region = :region AND period = :period
    """)
    update_fields["region"] = region
    update_fields["period"] = period
    result = db.execute(sql, update_fields)
    db.commit()
    return result.rowcount > 0


def import_region_indicators(db: Session, records: List[Dict]) -> Dict:
    if len(records) > MAX_IMPORT_ROWS:
        return {"success": 0, "error": len(records),
                "errors": [{"row": 0, "error": f"导入行数超过上限 {MAX_IMPORT_ROWS}"}]}

    success_count = 0
    error_count = 0
    errors = []

    for idx, record in enumerate(records):
        try:
            period = normalize_time_to_month(clean_value(record.get("period") or record.get("时间")))
            region = clean_value(record.get("region") or record.get("大区"))
            province = clean_value(record.get("province") or record.get("省份"))
            sa = clean_value(record.get("sales_area") or record.get("销售区域"))
            manager = clean_value(record.get("manager") or record.get("负责人"))
            mt_raw = record.get("monthly_target") or record.get("月度指标")

            # 必填校验
            missing = []
            if not period: missing.append("时间")
            if not region: missing.append("大区")
            if not province: missing.append("省份")
            if missing:
                error_count += 1
                errors.append({"row": idx + 1, "error": f"必填字段为空: {', '.join(missing)}"})
                continue

            # 数值校验
            try:
                mt = float(mt_raw) if mt_raw is not None and str(mt_raw).strip() else 0
            except (ValueError, TypeError):
                error_count += 1
                errors.append({"row": idx + 1, "error": "月度指标必须是有效数字"})
                continue

            now = datetime.now()
            # DELETE + INSERT 策略（原版逻辑）
            del_sql = text("""
                DELETE FROM dim_business_indicator_region
                WHERE period = :period AND province = :province
            """)
            db.execute(del_sql, {"period": period, "province": province})

            ins_fields = {
                "period": period, "region": region, "province": province,
                "sales_area": sa, "manager": manager, "monthly_target": mt,
                "updated_at": now, "created_at": now,
            }
            columns = ", ".join(ins_fields.keys())
            placeholders = ", ".join([f":{k}" for k in ins_fields.keys()])
            sql = text(f"INSERT INTO dim_business_indicator_region ({columns}) VALUES ({placeholders})")
            db.execute(sql, ins_fields)
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"row": idx + 1, "error": str(e)})

    db.commit()
    return {"success": success_count, "error": error_count, "errors": errors}


# ============================================================
# 客户指标 dim_business_indicator_customer
# ============================================================

CUST_IND_FIELDS = ["period", "region", "province", "sales_area", "manager", "customer_name", "monthly_target"]
CUST_IND_REQUIRED = ["period", "region", "province", "sales_area", "manager", "customer_name", "monthly_target"]


def get_customer_indicators(db: Session, page: int = 1, page_size: int = 100,
                            search: Optional[str] = None) -> Dict:
    offset, limit = parse_pagination_params(page, page_size)
    where_clause = ""
    params = {}
    if search:
        where_clause = "WHERE customer_name LIKE :search OR region LIKE :search"
        params["search"] = f"%{search}%"

    count_sql = text(f"SELECT COUNT(*) FROM dim_business_indicator_customer {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    data_sql = text(f"""
        SELECT id, period, region, province, sales_area, manager,
               customer_name, monthly_target, created_at, updated_at
        FROM dim_business_indicator_customer {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)
    params.update({"limit": limit, "offset": offset})
    results = db.execute(data_sql, params).fetchall()
    items = [
        {
            "id": r[0], "period": r[1], "region": r[2],
            "province": r[3], "sales_area": r[4], "manager": r[5],
            "customer_name": r[6],
            "monthly_target": float(r[7]) if r[7] else 0,
            "created_at": r[8].isoformat() if r[8] else None,
            "updated_at": r[9].isoformat() if r[9] else None,
        }
        for r in results
    ]
    return build_pagination_response(items, total, page, page_size)


def update_customer_indicator(db: Session, customer: str, period: str, data: Dict) -> bool:
    allowed_fields = ["region", "province", "sales_area", "manager", "customer_name", "monthly_target"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_fields:
        return False
    update_fields["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    sql = text(f"""
        UPDATE dim_business_indicator_customer SET {set_clause}
        WHERE customer_name = :customer AND period = :period
    """)
    update_fields["customer"] = customer
    update_fields["period"] = period
    result = db.execute(sql, update_fields)
    db.commit()
    return result.rowcount > 0


def import_customer_indicators(db: Session, records: List[Dict]) -> Dict:
    if len(records) > MAX_IMPORT_ROWS:
        return {"success": 0, "error": len(records),
                "errors": [{"row": 0, "error": f"导入行数超过上限 {MAX_IMPORT_ROWS}"}]}

    success_count = 0
    error_count = 0
    errors = []

    for idx, record in enumerate(records):
        try:
            period = normalize_time_to_month(clean_value(record.get("period") or record.get("时间")))
            region = clean_value(record.get("region") or record.get("大区"))
            province = clean_value(record.get("province") or record.get("省份"))
            sa = clean_value(record.get("sales_area") or record.get("销售区域"))
            manager = clean_value(record.get("manager") or record.get("负责人"))
            cn = clean_value(record.get("customer_name") or record.get("客户名称"))
            mt_raw = record.get("monthly_target") or record.get("月度指标")

            # 必填校验
            missing = []
            if not period: missing.append("时间")
            if not region: missing.append("大区")
            if not cn: missing.append("客户名称")
            if missing:
                error_count += 1
                errors.append({"row": idx + 1, "error": f"必填字段为空: {', '.join(missing)}"})
                continue

            try:
                mt = float(mt_raw) if mt_raw is not None and str(mt_raw).strip() else 0
            except (ValueError, TypeError):
                error_count += 1
                errors.append({"row": idx + 1, "error": "月度指标必须是有效数字"})
                continue

            now = datetime.now()
            del_sql = text("""
                DELETE FROM dim_business_indicator_customer
                WHERE period = :period AND region = :region AND customer_name = :cn
            """)
            db.execute(del_sql, {"period": period, "region": region, "cn": cn})

            ins_fields = {
                "period": period, "region": region, "province": province,
                "sales_area": sa, "manager": manager, "customer_name": cn,
                "monthly_target": mt, "updated_at": now, "created_at": now,
            }
            columns = ", ".join(ins_fields.keys())
            placeholders = ", ".join([f":{k}" for k in ins_fields.keys()])
            sql = text(f"INSERT INTO dim_business_indicator_customer ({columns}) VALUES ({placeholders})")
            db.execute(sql, ins_fields)
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"row": idx + 1, "error": str(e)})

    db.commit()
    return {"success": success_count, "error": error_count, "errors": errors}


# ============================================================
# 仓别/筛选配置 dim_filter_config
# ============================================================

def get_filter_configs(db: Session, page: int = 1, page_size: int = 100,
                       config_type: Optional[str] = None) -> Dict:
    offset, limit = parse_pagination_params(page, page_size)
    where_clause = ""
    params = {}
    if config_type:
        where_clause = "WHERE filter_type = :ft"
        params["ft"] = config_type

    count_sql = text(f"SELECT COUNT(*) FROM dim_filter_config {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    data_sql = text(f"""
        SELECT id, filter_type, filter_value, created_at, updated_at
        FROM dim_filter_config {where_clause}
        ORDER BY filter_type, filter_value, id
        LIMIT :limit OFFSET :offset
    """)
    params.update({"limit": limit, "offset": offset})
    results = db.execute(data_sql, params).fetchall()
    items = [
        {
            "id": r[0], "filter_type": r[1], "filter_value": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
            "updated_at": r[4].isoformat() if r[4] else None,
        }
        for r in results
    ]
    return build_pagination_response(items, total, page, page_size)


def get_filter_config(db: Session, filter_type: str) -> List[str]:
    """按 filter_type 获取 filter_value 列表（对齐原版 get_filter_config）"""
    sql = text("SELECT filter_value FROM dim_filter_config WHERE filter_type = :ft ORDER BY id")
    return [r[0] for r in db.execute(sql, {"ft": filter_type}).fetchall()]


def save_filter_config(db: Session, filter_type: str, values: List[str]):
    """先 DELETE 再 INSERT（对齐原版 save_filter_config）"""
    db.execute(text("DELETE FROM dim_filter_config WHERE filter_type = :ft"), {"ft": filter_type})
    if values:
        now = datetime.now()
        for v in values:
            db.execute(
                text("INSERT INTO dim_filter_config (filter_type, filter_value, created_at, updated_at) VALUES (:ft, :fv, :c, :u)"),
                {"ft": filter_type, "fv": v, "c": now, "u": now}
            )
    db.commit()


def update_filter_config(db: Session, config_id: int, data: Dict) -> bool:
    allowed_fields = ["filter_type", "filter_value"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_fields:
        return False
    update_fields["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    sql = text(f"UPDATE dim_filter_config SET {set_clause} WHERE id = :cid")
    update_fields["cid"] = config_id
    result = db.execute(sql, update_fields)
    db.commit()
    return result.rowcount > 0


def import_filter_configs(db: Session, records: List[Dict]) -> Dict:
    success_count = 0
    error_count = 0
    errors = []
    for idx, record in enumerate(records):
        try:
            ft = clean_value(record.get("filter_type"))
            fv = clean_value(record.get("filter_value"))
            if not ft or not fv:
                error_count += 1
                errors.append({"row": idx + 1, "error": "filter_type 和 filter_value 不能为空"})
                continue

            now = datetime.now()
            check = text("SELECT id FROM dim_filter_config WHERE filter_type = :ft AND filter_value = :fv")
            exists = db.execute(check, {"ft": ft, "fv": fv}).fetchone()
            if not exists:
                sql = text("""
                    INSERT INTO dim_filter_config (filter_type, filter_value, created_at, updated_at)
                    VALUES (:ft, :fv, :c, :u)
                """)
                db.execute(sql, {"ft": ft, "fv": fv, "c": now, "u": now})
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"row": idx + 1, "error": str(e)})
    db.commit()
    return {"success": success_count, "error": error_count, "errors": errors}


# ============================================================
# 自营品牌 dim_self_operated_brand
# ============================================================

BRAND_FIELDS = ["brand_name", "remark"]


def get_self_operated_brands(db: Session, page: int = 1, page_size: int = 100,
                             search: Optional[str] = None) -> Dict:
    offset, limit = parse_pagination_params(page, page_size)
    where_clause = ""
    params = {}
    if search:
        where_clause = "WHERE brand_name LIKE :search"
        params["search"] = f"%{search}%"

    count_sql = text(f"SELECT COUNT(*) FROM dim_self_operated_brand {where_clause}")
    total = db.execute(count_sql, params).scalar() or 0

    data_sql = text(f"""
        SELECT id, brand_name, remark, created_at, updated_at
        FROM dim_self_operated_brand {where_clause}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """)
    params.update({"limit": limit, "offset": offset})
    results = db.execute(data_sql, params).fetchall()
    items = [
        {
            "id": r[0], "brand_name": r[1], "remark": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
            "updated_at": r[4].isoformat() if r[4] else None,
        }
        for r in results
    ]
    return build_pagination_response(items, total, page, page_size)


def update_self_operated_brand(db: Session, brand_id: int, data: Dict) -> bool:
    allowed_fields = BRAND_FIELDS
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_fields:
        return False
    update_fields["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    sql = text(f"UPDATE dim_self_operated_brand SET {set_clause} WHERE id = :bid")
    update_fields["bid"] = brand_id
    result = db.execute(sql, update_fields)
    db.commit()
    return result.rowcount > 0


def import_self_operated_brands(db: Session, records: List[Dict]) -> Dict:
    success_count = 0
    error_count = 0
    errors = []
    for idx, record in enumerate(records):
        try:
            bn = clean_value(record.get("brand_name") or record.get("品牌名称"))
            remark = clean_value(record.get("remark") or record.get("备注"))
            if not bn:
                error_count += 1
                errors.append({"row": idx + 1, "error": "品牌名称不能为空"})
                continue

            # 重复检查
            check = text("SELECT id FROM dim_self_operated_brand WHERE brand_name = :bn")
            exists = db.execute(check, {"bn": bn}).fetchone()
            if exists:
                error_count += 1
                errors.append({"row": idx + 1, "error": f"品牌 {bn} 已存在"})
                continue

            now = datetime.now()
            sql = text("""
                INSERT INTO dim_self_operated_brand (brand_name, remark, created_at, updated_at)
                VALUES (:bn, :r, :c, :u)
            """)
            db.execute(sql, {"bn": bn, "r": remark, "c": now, "u": now})
            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"row": idx + 1, "error": str(e)})
    db.commit()
    return {"success": success_count, "error": error_count, "errors": errors}


# ============================================================
# stg 数据源选项（渠道客户设定用）
# ============================================================

def get_customer_classes_from_stg(db: Session) -> List[str]:
    """从 stg_sales_out 取 DISTINCT customer_class"""
    sql = text("""
        SELECT DISTINCT customer_class FROM stg_sales_out
        WHERE customer_class IS NOT NULL AND customer_class != ''
        ORDER BY customer_class
    """)
    return [r[0] for r in db.execute(sql).fetchall()]


def get_customers_by_class_from_stg(db: Session, customer_classes: Optional[List[str]] = None) -> List[Dict]:
    """从 stg_sales_out 取 customer_class + customer 组合"""
    if customer_classes:
        placeholders = ", ".join([f":c{i}" for i in range(len(customer_classes))])
        params = {f"c{i}": v for i, v in enumerate(customer_classes)}
        sql = text(f"""
            SELECT DISTINCT customer_class, customer FROM stg_sales_out
            WHERE customer_class IS NOT NULL AND customer_class != ''
            AND customer_class IN ({placeholders})
            AND customer IS NOT NULL AND customer != ''
            ORDER BY customer_class, customer
        """)
    else:
        params = {}
        sql = text("""
            SELECT DISTINCT customer_class, customer FROM stg_sales_out
            WHERE customer_class IS NOT NULL AND customer_class != ''
            AND customer IS NOT NULL AND customer != ''
            ORDER BY customer_class, customer
        """)
    return [{"customer_class": r[0], "customer": r[1]} for r in db.execute(sql, params).fetchall()]


# ============================================================
# 模板下载
# ============================================================

def get_table_template(table_type: str) -> List[str]:
    templates = {
        "product_attr": ["material_code", "abc_class", "lifecycle_status", "custom_flag", "promoted_flag"],
        "customer": ["customer_name", "region", "province", "sales_area",
                     "channel", "cooperation_status", "account_manager"],
        "region_indicator": ["period", "region", "province", "sales_area", "manager", "monthly_target"],
        "customer_indicator": ["period", "region", "province", "sales_area", "manager", "customer_name", "monthly_target"],
        "filter_config": ["filter_type", "filter_value"],
        "self_operated_brand": ["brand_name", "remark"],
    }
    return templates.get(table_type, [])
