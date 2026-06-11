"""
Seed: mock fixtures -> SQLite/MySQL (raw SQL, no ORM dependency)

Usage:
    python -m channel_analytics.data.seed              # seed all
    python -m channel_analytics.data.seed --reset       # clear + reseed
    python -m channel_analytics.data.seed --only stg    # only STG tables
    python -m channel_analytics.data.seed --only dim    # only DIM tables
    python -m channel_analytics.data.seed --only user   # only user/role

Default login: admin / admin123
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import logging
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "data" / "fixtures"
DIM_DIR = FIXTURES_DIR / "dim"

# Inject channel_analytics/ into sys.path so "from app.xxx" works in database.py
_ch = str(PROJECT_ROOT / "channel_analytics")
if _ch not in sys.path:
    sys.path.insert(0, _ch)
_rt = str(PROJECT_ROOT)
if _rt not in sys.path:
    sys.path.insert(0, _rt)


# ====================================================================
# Password hash (simple SHA256, same as channel_analytics/api/deps.py)
# ====================================================================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(
        hashlib.sha256(f"{salt}:{password}".encode()).hexdigest(), digest
    )


# ====================================================================
# Table DDL (SQLite / MySQL agnostic)
# ====================================================================

# SQLite INTEGER PRIMARY KEY = autoincrement
# MySQL needs AUTO_INCREMENT keyword; SQLite ignores it

DIALECT_SQLITE = True  # overridden at runtime

STG_TABLES = {
    "stg_sales_out": """
        CREATE TABLE IF NOT EXISTS stg_sales_out (
            id INTEGER PRIMARY KEY,
            doc_date DATE, doc_no VARCHAR(64),
            source_tx_type VARCHAR(32), tx_type_name VARCHAR(64),
            customer VARCHAR(128), customer_class VARCHAR(32),
            region_manager VARCHAR(64), warehouse VARCHAR(64),
            material_code VARCHAR(64), material_name VARCHAR(255),
            brand VARCHAR(128),
            tax_included_amount DOUBLE,
            batch_no VARCHAR(64),
            shipping_channel VARCHAR(64),
            audit_date DATE, audit_time DATETIME,
            creator VARCHAR(64),
            sales_out_qty INTEGER, dispatch_qty INTEGER, invoiced_qty INTEGER,
            tx_type VARCHAR(32),
            remark VARCHAR(512),
            source_doc_tx_type VARCHAR(64), entry_method VARCHAR(32),
            tax_included_unit_price DOUBLE,
            source_doc_no VARCHAR(64)
        )
    """,
    "stg_purchase_order": """
        CREATE TABLE IF NOT EXISTS stg_purchase_order (
            id INTEGER PRIMARY KEY,
            delivery_date DATE, order_no VARCHAR(64),
            brand VARCHAR(128), material_code VARCHAR(64), material_name VARCHAR(255),
            factory_delivery_qty DOUBLE, batch_no VARCHAR(64),
            expiry_date DATE, brand_sales_no VARCHAR(64),
            remark VARCHAR(512), pickup_qty DOUBLE,
            production_date DATE, is_billed BOOLEAN
        )
    """,
    "stg_stock_in": """
        CREATE TABLE IF NOT EXISTS stg_stock_in (
            id INTEGER PRIMARY KEY,
            brand_sales_no VARCHAR(64), stock_in_date DATE, doc_no VARCHAR(64),
            order_tx_type VARCHAR(32), audit_date DATE,
            material_code VARCHAR(64), material_name VARCHAR(255),
            receivable_qty INTEGER, batch_no VARCHAR(64),
            warehouse VARCHAR(64), doc_status VARCHAR(32),
            expiry_date DATE, model VARCHAR(64),
            stock_in_qty INTEGER, remark VARCHAR(512),
            logistics_no VARCHAR(64), logistics_company VARCHAR(64),
            supplier_material_code VARCHAR(64), supplier_material_name VARCHAR(255)
        )
    """,
    "stg_purchase_req": """
        CREATE TABLE IF NOT EXISTS stg_purchase_req (
            id INTEGER PRIMARY KEY,
            order_date DATE, order_no VARCHAR(64),
            channel_contact VARCHAR(64), delivery_cycle INTEGER,
            brand VARCHAR(128), promotion_tags VARCHAR(128),
            material_code VARCHAR(64), material_name VARCHAR(255),
            channel VARCHAR(64), order_qty INTEGER,
            order_remark VARCHAR(512), expected_delivery_date DATE,
            actual_manual_stock_qty INTEGER, special_remark VARCHAR(512),
            is_delivered BOOLEAN
        )
    """,
    "stg_stock_current": """
        CREATE TABLE IF NOT EXISTS stg_stock_current (
            id INTEGER PRIMARY KEY,
            warehouse VARCHAR(64), brand VARCHAR(128),
            material_code VARCHAR(64), material_name VARCHAR(255),
            batch_no VARCHAR(64), production_date DATE,
            expiry_date DATE, spec VARCHAR(64),
            current_stock INTEGER, available_qty INTEGER,
            brand_class VARCHAR(32),
            estimated_shipping_qty INTEGER, estimated_order_qty INTEGER
        )
    """,
}

DIM_TABLES = {
    "dim_brand": """
        CREATE TABLE IF NOT EXISTS dim_brand (
            id INTEGER PRIMARY KEY,
            brand_name VARCHAR(128) UNIQUE NOT NULL,
            remark VARCHAR(255),
            created_at DATETIME, updated_at DATETIME
        )
    """,
    "dim_product_attr": """
        CREATE TABLE IF NOT EXISTS dim_product_attr (
            id INTEGER PRIMARY KEY,
            material_code VARCHAR(64) UNIQUE NOT NULL,
            material_name VARCHAR(255), category VARCHAR(128),
            abc_class VARCHAR(16), lifecycle_status VARCHAR(32),
            custom_flag BOOLEAN, promoted_flag BOOLEAN,
            first_stock_in_date DATE,
            created_at DATETIME, updated_at DATETIME
        )
    """,
    "dim_customer": """
        CREATE TABLE IF NOT EXISTS dim_customer (
            id INTEGER PRIMARY KEY,
            customer_name VARCHAR(255) UNIQUE NOT NULL,
            region VARCHAR(64), province VARCHAR(64),
            sales_area VARCHAR(64), channel VARCHAR(64),
            cooperation_status VARCHAR(32), account_manager VARCHAR(64),
            created_at DATETIME, updated_at DATETIME
        )
    """,
    "dim_self_operated_brand": """
        CREATE TABLE IF NOT EXISTS dim_self_operated_brand (
            id INTEGER PRIMARY KEY,
            brand_name VARCHAR(128) UNIQUE NOT NULL,
            remark VARCHAR(255),
            created_at DATETIME, updated_at DATETIME
        )
    """,
}

USER_TABLES = {
    "system_user": """
        CREATE TABLE IF NOT EXISTS system_user (
            id INTEGER PRIMARY KEY,
            username VARCHAR(64) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(32) NOT NULL,
            display_name VARCHAR(64),
            status INTEGER DEFAULT 1,
            created_at DATETIME, updated_at DATETIME
        )
    """,
    "role_permission": """
        CREATE TABLE IF NOT EXISTS role_permission (
            id INTEGER PRIMARY KEY,
            role VARCHAR(64) NOT NULL,
            module VARCHAR(64),
            permission_type VARCHAR(32) NOT NULL,
            permission_value TEXT,
            module_ext VARCHAR(128),
            created_at DATETIME, updated_at DATETIME
        )
    """,
    "alert_rule": """
        CREATE TABLE IF NOT EXISTS alert_rule (
            id INTEGER PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            alert_type VARCHAR(64),
            config TEXT,
            check_interval INT DEFAULT 60,
            is_enabled BOOLEAN DEFAULT 1,
            is_deleted BOOLEAN DEFAULT 0,
            created_at DATETIME, updated_at DATETIME
        )
    """,
    "alert_history": """
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY,
            rule_id INTEGER,
            triggered_at DATETIME,
            message TEXT,
            acknowledged BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "sys_config": """
        CREATE TABLE IF NOT EXISTS sys_config (
            id INTEGER PRIMARY KEY,
            config_key VARCHAR(128) UNIQUE NOT NULL,
            config_value TEXT,
            description VARCHAR(255),
            updated_at DATETIME
        )
    """,
}


# ====================================================================
# Table creation
# ====================================================================

def create_tables(engine, table_groups: dict[str, str]):
    with engine.connect() as conn:
        for tbl, ddl in table_groups.items():
            try:
                conn.execute(text(ddl))
            except Exception as e:
                logger.debug(f"CREATE TABLE {tbl}: {e}")
        conn.commit()


# ====================================================================
# CSV -> raw SQL insert
# ====================================================================

def _clean(v):
    """Make value safe for SQL insert"""
    if pd.isna(v) if isinstance(v, float) else v is None:
        return None
    if isinstance(v, float) and v != v:  # NaN
        return None
    return v


def insert_csv(engine, table: str, csv_path: Path, column_map: Optional[dict] = None) -> int:
    """
    Insert all rows from a CSV into a table using raw SQL.
    column_map: optional {csv_col_name: db_col_name} for renaming.
    Skips id column (autoincrement).
    """
    df = pd.read_csv(csv_path)
    if df.empty:
        return 0

    if column_map:
        df = df.rename(columns=column_map)

    # Drop 'id' if present (autoincrement)
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # Get table columns (from DDL)
    cols = [c for c in df.columns if c != "id"]
    placeholders = ", ".join([f":{c}" for c in cols])
    col_names = ", ".join(cols)
    sql = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"

    n = 0
    with engine.connect() as conn:
        for _, row in df.iterrows():
            params = {}
            for c in cols:
                v = _clean(row.get(c))
                params[c] = v
            try:
                conn.execute(text(sql), params)
                n += 1
            except Exception as e:
                logger.debug(f"INSERT {table} skip row: {e}")
        conn.commit()
    return n


def insert_csv_mysql(engine, table: str, csv_path: Path, column_map: Optional[dict] = None) -> int:
    """Insert CSV rows using INSERT IGNORE (MySQL)."""
    df = pd.read_csv(csv_path)
    if df.empty:
        return 0
    if column_map:
        df = df.rename(columns=column_map)
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    cols = [c for c in df.columns if c != "id"]
    placeholders = ", ".join([f":{c}" for c in cols])
    col_names = ", ".join(cols)
    sql = f"INSERT IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"

    n = 0
    with engine.connect() as conn:
        for _, row in df.iterrows():
            params = {c: _clean(row.get(c)) for c in cols}
            try:
                conn.execute(text(sql), params)
                n += 1
            except Exception as e:
                logger.debug(f"INSERT {table} skip: {e}")
        conn.commit()
    return n


# ====================================================================
# Seed user + role_permissions (no CSV for these)
# ====================================================================

USERS = [
    ("admin", "admin123", "admin", "Admin", 1),
    ("alice", "admin123", "manager", "Alice Wang", 1),
    ("bob", "admin123", "analyst", "Bob Li", 1),
    ("charlie", "admin123", "analyst", "Charlie Zhang", 1),
    ("diana", "admin123", "viewer", "Diana Chen", 1),
]

ROLES = [
    # (role, modules_list, sales_tabs_list, regions_list)
    ("admin",
     ["sales", "stock", "repurchase", "etl", "permissions", "reports", "alerts",
      "rpa", "custom_report", "advanced", "logs", "todo", "sys_config",
      "data_management", "basis"],
     ["dashboard", "detail", "indicator", "flow_analysis", "wide_table"],
     None),
    ("manager", ["sales", "stock", "repurchase", "reports"],
     ["dashboard", "detail", "indicator"], ["East", "South"]),
    ("analyst", ["sales", "stock", "reports"],
     ["dashboard", "detail"], ["East", "South"]),
    ("viewer", ["sales", "reports"],
     ["dashboard"], ["East"]),
]

SYS_CONFIGS = [
    ("rpa_erp_url", "https://erp.example.com", "ERP server URL"),
    ("rpa_download_dir", "./rpa_downloads", "RPA download dir"),
    ("rpa_keep_days", "7", "Download file retention days"),
    ("rpa_headless", "true", "Headless browser mode"),
]


def seed_users(engine):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Use bcrypt (same as auth_service.py)
    try:
        import bcrypt as _bcrypt
        def _hash(pwd):
            return _bcrypt.hashpw(pwd.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        def _hash(pwd):
            return hash_password(pwd)  # fallback SHA256

    n = 0
    with engine.connect() as conn:
        for username, pwd, role, display_name, status in USERS:
            try:
                conn.execute(text("""
                    INSERT OR IGNORE INTO system_user (username, password, role, display_name, status, created_at, updated_at)
                    VALUES (:u, :p, :r, :d, :s, :c, :u2)
                """), {"u": username, "p": _hash(pwd), "r": role,
                        "d": display_name, "s": status,
                        "c": now, "u2": now})
                n += 1
            except Exception as e:
                logger.debug(f"User {username}: {e}")
        conn.commit()
    return n


def seed_roles(engine):
    """Seed role_permission table using the actual schema (permission_type/permission_value/module_ext)."""
    import json as _json
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = 0
    with engine.connect() as conn:
        for role, modules, sales_tabs, regions in ROLES:
            try:
                # Delete existing
                conn.execute(text("DELETE FROM role_permission WHERE role = :r"), {"r": role})
                # Insert modules (one row per module)
                for mod in modules:
                    conn.execute(text("""
                        INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext, created_at, updated_at)
                        VALUES (:r, 'module', 'module', NULL, :ext, :c, :u)
                    """), {"r": role, "ext": mod, "c": now, "u": now})
                    n += 1
                # Insert sales_tabs
                if sales_tabs:
                    conn.execute(text("""
                        INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext, created_at, updated_at)
                        VALUES (:r, 'sales_tab', 'sales_tab', :pval, NULL, :c, :u)
                    """), {"r": role, "pval": _json.dumps(sales_tabs, ensure_ascii=False),
                            "c": now, "u": now})
                    n += 1
                # Insert regions
                if regions:
                    conn.execute(text("""
                        INSERT INTO role_permission (role, module, permission_type, permission_value, module_ext, created_at, updated_at)
                        VALUES (:r, 'region', 'region', :pval, NULL, :c, :u)
                    """), {"r": role, "pval": _json.dumps(regions, ensure_ascii=False),
                            "c": now, "u": now})
                    n += 1
            except Exception as e:
                logger.debug(f"Role {role}: {e}")
        conn.commit()
    return n


def seed_sys_config(engine):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = 0
    with engine.connect() as conn:
        for key, value, desc in SYS_CONFIGS:
            try:
                conn.execute(text("""
                    INSERT OR IGNORE INTO sys_config (config_key, config_value, description, updated_at)
                    VALUES (:k, :v, :d, :t)
                """), {"k": key, "v": value, "d": desc, "t": now})
                n += 1
            except Exception as e:
                logger.debug(f"Config {key}: {e}")
        conn.commit()
    return n


RPT_TABLES = {
    "rpt_sales_out_wide": """
        CREATE TABLE IF NOT EXISTS rpt_sales_out_wide (
            id INTEGER PRIMARY KEY,
            doc_date DATE, doc_no VARCHAR(64),
            tx_type VARCHAR(32), tx_type_name VARCHAR(64),
            customer VARCHAR(128), customer_class VARCHAR(32),
            region_manager VARCHAR(64), warehouse VARCHAR(64),
            material_code VARCHAR(64), material_name VARCHAR(255),
            brand VARCHAR(128),
            tax_included_amount DOUBLE,
            batch_no VARCHAR(64),
            shipping_channel VARCHAR(64),
            audit_date DATE, audit_time DATETIME,
            creator VARCHAR(64),
            sales_out_qty INTEGER, dispatch_qty INTEGER, invoiced_qty INTEGER,
            source_doc_tx_type VARCHAR(64), entry_method VARCHAR(32),
            tax_included_unit_price DOUBLE,
            source_doc_no VARCHAR(64), source_tx_type VARCHAR(32),
            remark VARCHAR(512),
            -- Enrichment from dim tables
            category VARCHAR(128),
            abc_class VARCHAR(16),
            lifecycle_status VARCHAR(32),
            custom_flag VARCHAR(8),
            promoted_flag VARCHAR(8),
            region VARCHAR(64),
            account_manager VARCHAR(64),
            channel VARCHAR(64),
            creation_time DATETIME
        )
    """,
}


def build_rpt_sales_out_wide(engine) -> int:
    """
    Build rpt_sales_out_wide from stg_sales_out + dim_product_attr + dim_customer.
    Enriches STG sales data with product attributes and customer info.
    """
    import random
    import pandas as pd

    # Read STG sales_out
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT * FROM stg_sales_out"))
            cols = result.keys()
            rows = result.fetchall()
        except Exception:
            return 0

    if not rows:
        return 0

    df = pd.DataFrame(rows, columns=cols)
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # Get dim_product_attr for enrichment
    try:
        pa_rows = conn.execute(text("SELECT material_code, category, abc_class, lifecycle_status, custom_flag, promoted_flag FROM dim_product_attr")).fetchall()
        pa_df = pd.DataFrame(pa_rows, columns=["material_code", "category", "abc_class", "lifecycle_status", "custom_flag", "promoted_flag"])
    except Exception:
        pa_df = pd.DataFrame(columns=["material_code", "category", "abc_class", "lifecycle_status", "custom_flag", "promoted_flag"])

    # Get dim_customer for enrichment
    try:
        cu_rows = conn.execute(text("SELECT customer_name, region, channel, account_manager, cooperation_status FROM dim_customer")).fetchall()
        cu_df = pd.DataFrame(cu_rows, columns=["customer_name", "region", "channel", "account_manager", "cooperation_status"])
    except Exception:
        cu_df = pd.DataFrame(columns=["customer_name", "region", "channel", "account_manager", "cooperation_status"])

    # Merge
    df = df.merge(pa_df, on="material_code", how="left")
    df = df.merge(cu_df, left_on="customer", right_on="customer_name", how="left")

    # Fill defaults
    df["region"] = df["region"].fillna("Unknown")
    df["channel"] = df["channel"].fillna("Unknown")
    df["account_manager"] = df["account_manager"].fillna("Unknown")
    df["category"] = df["category"].fillna("Unknown")
    df["abc_class"] = df["abc_class"].fillna("C")
    df["lifecycle_status"] = df["lifecycle_status"].fillna("Unknown")
    df["custom_flag"] = df["custom_flag"].fillna("否")
    df["promoted_flag"] = df["promoted_flag"].fillna("否")
    df["creation_time"] = df.get("audit_date")

    # Keep only rpt columns
    rpt_cols = [
        "doc_date", "doc_no", "tx_type", "tx_type_name",
        "customer", "customer_class", "region_manager", "warehouse",
        "material_code", "material_name", "brand",
        "tax_included_amount", "batch_no", "shipping_channel",
        "audit_date", "audit_time", "creator",
        "sales_out_qty", "dispatch_qty", "invoiced_qty",
        "source_doc_tx_type", "entry_method",
        "tax_included_unit_price", "source_doc_no", "source_tx_type",
        "remark",
        "category", "abc_class", "lifecycle_status",
        "custom_flag", "promoted_flag",
        "region", "account_manager", "channel", "creation_time",
    ]
    for c in rpt_cols:
        if c not in df.columns:
            df[c] = None

    df = df[rpt_cols]

    # Insert
    placeholders = ", ".join([f":{c}" for c in rpt_cols])
    col_names = ", ".join(rpt_cols)
    n = 0
    with engine.connect() as conn:
        for _, row in df.iterrows():
            params = {c: _clean(row[c]) for c in rpt_cols}
            try:
                conn.execute(text(f"INSERT INTO rpt_sales_out_wide ({col_names}) VALUES ({placeholders})"), params)
                n += 1
            except Exception:
                pass
        conn.commit()
    return n


# ====================================================================
# Main
# ====================================================================

def run(args):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from app.database import main_engine, IS_SQLITE, MAIN_DATABASE_URL

    logger.info(f"Database: {'SQLite' if IS_SQLITE else 'MySQL'} @ {MAIN_DATABASE_URL.split('@')[-1]}")

    # Create tables
    create_tables(main_engine, STG_TABLES)
    create_tables(main_engine, DIM_TABLES)
    create_tables(main_engine, RPT_TABLES)
    create_tables(main_engine, USER_TABLES)

    # Reset?
    if args.reset:
        all_tables = list(STG_TABLES) + list(DIM_TABLES) + list(RPT_TABLES) + list(USER_TABLES)
        with main_engine.connect() as conn:
            for tbl in all_tables:
                try:
                    conn.execute(text(f"DELETE FROM {tbl}"))
                except Exception:
                    pass
            conn.commit()
        logger.info("Tables cleared")

    insert_fn = insert_csv if IS_SQLITE else insert_csv_mysql

    only = args.only or "all"

    # STG
    if only in ("all", "stg"):
        stg_jobs = [
            ("stg_sales_out",       FIXTURES_DIR / "sales_out.csv",       None),
            ("stg_purchase_order",  FIXTURES_DIR / "purchase_order.csv",  None),
            ("stg_stock_in",        FIXTURES_DIR / "stock_in.csv",        None),
            ("stg_purchase_req",    FIXTURES_DIR / "purchase_req.csv",    None),
            ("stg_stock_current",   FIXTURES_DIR / "stock_current.csv",   None),
        ]
        for tbl, path, col_map in stg_jobs:
            if not path.exists():
                logger.warning(f"Skip {tbl}: {path} not found")
                continue
            n = insert_fn(main_engine, tbl, path, col_map)
            logger.info(f"  {tbl}: {n} rows")

    # DIM
    if only in ("all", "dim"):
        dim_jobs = [
            ("dim_brand",                DIM_DIR / "self_operated_brand.csv", None),
            ("dim_product_attr",         DIM_DIR / "product_attr.csv",       None),
            ("dim_customer",             DIM_DIR / "customer.csv",           None),
        ]
        for tbl, path, col_map in dim_jobs:
            if not path.exists():
                logger.warning(f"Skip {tbl}: {path} not found")
                continue
            n = insert_fn(main_engine, tbl, path, col_map)
            logger.info(f"  {tbl}: {n} rows")

    # user / role / sys_config
    if only in ("all", "user"):
        n = seed_users(main_engine)
        logger.info(f"  users: {n} rows")
        n = seed_roles(main_engine)
        logger.info(f"  role_permissions: {n} rows")
        n = seed_sys_config(main_engine)
        logger.info(f"  sys_config: {n} rows")

    # Build RPT wide table (after STG + DIM are seeded)
    if only in ("all", "rpt", "stg", "dim"):
        n = build_rpt_sales_out_wide(main_engine)
        logger.info(f"  rpt_sales_out_wide: {n} rows")

    logger.info("Seed done. Login: admin / admin123")


def main():
    parser = argparse.ArgumentParser(description="Seed mock data (raw SQL)")
    parser.add_argument("--only", choices=["all", "stg", "dim", "user"], default="all")
    parser.add_argument("--reset", action="store_true", help="Clear tables before seed")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
