"""
销售分析服务
提供销售出库、仪表盘、指标达成等分析功能
"""
import logging
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db_context
from app.services.field_mapping import rename_for_display

logger = logging.getLogger(__name__)


def _in_clause(param_name: str, values: list, params: dict) -> str:
    """生成 IN (:p0, :p1, ...) 子句，兼容 SQLAlchemy text()"""
    placeholders = []
    for i, v in enumerate(values):
        key = f"{param_name}_{i}"
        placeholders.append(f":{key}")
        params[key] = v
    return f"({', '.join(placeholders)})"


def _year_month(date_col: str) -> str:
    """生成 YYYY/MM 格式的年月表达式，避免 DATE_FORMAT 在 SQLAlchemy text() 中的转义问题"""
    return f"CONCAT(CAST(YEAR({date_col}) AS CHAR), '/', LPAD(CAST(MONTH({date_col}) AS CHAR), 2, '0'))"


def _year_month_group_by(date_col: str, prefix: str = "") -> tuple:
    """生成用于 GROUP BY 和 ORDER BY 的年月表达式"""
    y_expr = f"YEAR({date_col})"
    m_expr = f"MONTH({date_col})"
    group_by = f"{y_expr}, {m_expr}"
    order_by = f"{y_expr} DESC, {m_expr} DESC"
    concat_expr = f"CONCAT(CAST({y_expr} AS CHAR), '/', LPAD(CAST({m_expr} AS CHAR), 2, '0'))"
    return group_by, order_by, concat_expr


# ===================== 筛选器选项 =====================
def get_filter_options(db: Session, allowed_regions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    获取级联筛选器选项（大区、业务经理、客户、渠道）

    Args:
        db: Database session
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        包含各维度选项的字典
    """
    try:
        # 获取大区和业务经理组合
        region_manager_sql = """
            SELECT DISTINCT region, account_manager
            FROM rpt_sales_out_wide
            WHERE region IS NOT NULL AND region != ''
              AND account_manager IS NOT NULL AND account_manager != ''
            ORDER BY region, account_manager
        """
        result = db.execute(text(region_manager_sql))
        pairs = [(row[0], row[1]) for row in result.fetchall()]

        # 应用区域权限过滤
        if allowed_regions is not None:
            pairs = [(r, m) for r, m in pairs if r in allowed_regions]

        regions = sorted(set(p[0] for p in pairs))
        managers = sorted(set(p[1] for p in pairs))

        # 获取其他筛选选项
        distinct_fields = ["customer", "channel", "category", "abc_class", "lifecycle_status", "custom_flag", "promoted_flag", "material_code"]
        # 字段名映射：数据库字段名 -> API返回的key
        field_key_map = {
            "category": "categories",
            "abc_class": "abc_classes",
            "lifecycle_status": "lifecycle_statuses",
            "custom_flag": "custom_flags",
            "promoted_flag": "promoted_flags",
            "material_code": "material_codes",
            "channel": "channels",
            "customer": "customers",
        }
        options = {
            "region_manager_pairs": [{"region": r, "manager": m} for r, m in pairs],
            "regions": regions,
            "managers": managers,
        }

        for field in distinct_fields:
            sql = text(f"""
                SELECT DISTINCT {field}
                FROM rpt_sales_out_wide
                WHERE {field} IS NOT NULL AND {field} != ''
                ORDER BY {field}
            """)
            result = db.execute(sql)
            key = field_key_map.get(field, field + "s")
            options[key] = [str(row[0]) for row in result.fetchall() if row[0]]

        # 获取日期范围
        date_sql = """
            SELECT MIN(doc_date) as min_doc, MAX(doc_date) as max_doc,
                   MIN(audit_date) as min_audit, MAX(audit_date) as max_audit
            FROM rpt_sales_out_wide
            WHERE doc_date IS NOT NULL OR audit_date IS NOT NULL
        """
        result = db.execute(text(date_sql))
        row = result.fetchone()
        options["date_range"] = {
            "doc_date": {"min": str(row[0]) if row[0] else None, "max": str(row[1]) if row[1] else None},
            "audit_date": {"min": str(row[2]) if row[2] else None, "max": str(row[3]) if row[3] else None},
        }

        return options
    except Exception as e:
        logger.error(f"获取筛选器选项失败: {e}")
        return {
            "region_manager_pairs": [],
            "regions": [],
            "managers": [],
            "date_range": {}
        }


# ===================== 销售出库宽表 =====================
def search_material_name_options(
    db: Session,
    keyword: str = "",
    allowed_regions: Optional[List[str]] = None,
) -> List[str]:
    """
    根据关键词模糊搜索物料名称选项

    Args:
        db: Database session
        keyword: 物料名称关键词
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        去重的物料名称列表（最多50条）
    """
    try:
        conditions = ["material_name IS NOT NULL", "material_name != ''"]
        params = {}
        if keyword:
            conditions.append("material_name LIKE :keyword")
            params["keyword"] = f"%{keyword}%"
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")
        where_clause = " AND ".join(conditions)
        sql = text(f"""
            SELECT DISTINCT material_name
            FROM rpt_sales_out_wide
            WHERE {where_clause}
            ORDER BY material_name
            LIMIT 50
        """)
        result = db.execute(sql, params)
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"搜索物料名称失败: {e}")
        return []


def get_wide_table_data(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    customer: Optional[str] = None,
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    abc_class: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    custom_flag: Optional[str] = None,
    promoted_flag: Optional[str] = None,
    material_code: Optional[str] = None,
    material_name: Optional[str] = None,
    doc_date_from: Optional[str] = None,
    doc_date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 1000,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取销售出库宽表数据

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        customer: 客户
        channel: 渠道
        date_from: 审核日期开始
        date_to: 审核日期结束
        category: 品类
        abc_class: ABC分类
        lifecycle_status: 生命周期
        custom_flag: 定制标记
        promoted_flag: 主推标记
        material_code: 物料编码
        material_name: 物料名称（模糊搜索）
        doc_date_from: 单据日期开始
        doc_date_to: 单据日期结束
        page: 页码
        page_size: 每页数量
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        包含数据和统计信息的字典
    """
    try:
        # 构建WHERE条件
        conditions = []
        params = {}

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if customer:
            conditions.append("customer = :customer")
            params["customer"] = customer
        if channel:
            conditions.append("channel = :channel")
            params["channel"] = channel
        if date_from:
            conditions.append("DATE(audit_date) >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("DATE(audit_date) <= :date_to")
            params["date_to"] = date_to
        if category:
            conditions.append("category = :category")
            params["category"] = category
        if abc_class:
            conditions.append("abc_class = :abc_class")
            params["abc_class"] = abc_class
        if lifecycle_status:
            conditions.append("lifecycle_status = :lifecycle_status")
            params["lifecycle_status"] = lifecycle_status
        if custom_flag:
            conditions.append("custom_flag = :custom_flag")
            params["custom_flag"] = custom_flag
        if promoted_flag:
            conditions.append("promoted_flag = :promoted_flag")
            params["promoted_flag"] = promoted_flag
        if material_code:
            conditions.append("material_code = :material_code")
            params["material_code"] = material_code
        if material_name:
            conditions.append("material_name LIKE :material_name")
            params["material_name"] = f"%{material_name}%"
        if doc_date_from:
            conditions.append("DATE(doc_date) >= :doc_date_from")
            params["doc_date_from"] = doc_date_from
        if doc_date_to:
            conditions.append("DATE(doc_date) <= :doc_date_to")
            params["doc_date_to"] = doc_date_to
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 获取总数
        count_sql = text(f"""
            SELECT COUNT(*) as total FROM rpt_sales_out_wide WHERE {where_clause}
        """)
        count_result = db.execute(count_sql, params)
        total = count_result.fetchone()[0]

        # 获取数据
        offset = (page - 1) * page_size
        data_sql = text(f"""
            SELECT * FROM rpt_sales_out_wide
            WHERE {where_clause}
            ORDER BY audit_date DESC
            LIMIT :limit OFFSET :offset
        """)

        params["limit"] = page_size
        params["offset"] = offset

        result = db.execute(data_sql, params)
        columns = result.keys()
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

        # 将 NaN 替换为 None 以便 JSON 序列化
        if not df.empty:
            df = df.replace({np.nan: None})

        # 计算汇总统计 - 使用不带 LIMIT 的查询获取全部数据
        summary = {
            "total_count": int(total),
            "total_amount": 0.0,
            "total_quantity": 0,
            "inbound_amount": 0.0,
            "outbound_amount": 0.0,
            "inbound_customer_count": 0,
            "outbound_customer_count": 0,
            "inbound_sku_count": 0,
            "outbound_sku_count": 0,
        }

        # 查询全部数据的汇总（不受分页限制）
        summary_sql = text(f"""
            SELECT
                COUNT(*) as total_count,
                SUM(IFNULL(tax_included_amount, 0)) as total_amount,
                SUM(IFNULL(sales_out_qty, 0)) as total_quantity,
                SUM(CASE WHEN tax_included_amount > 0 THEN tax_included_amount ELSE 0 END) as inbound_amount,
                ABS(SUM(CASE WHEN tax_included_amount < 0 THEN tax_included_amount ELSE 0 END)) as outbound_amount,
                COUNT(DISTINCT CASE WHEN tax_included_amount > 0 THEN customer END) as inbound_customer_count,
                COUNT(DISTINCT CASE WHEN tax_included_amount < 0 THEN customer END) as outbound_customer_count,
                COUNT(DISTINCT CASE WHEN tax_included_amount > 0 THEN material_code END) as inbound_sku_count,
                COUNT(DISTINCT CASE WHEN tax_included_amount < 0 THEN material_code END) as outbound_sku_count
            FROM rpt_sales_out_wide WHERE {where_clause}
        """)
        summary_result = db.execute(summary_sql, params).fetchone()
        if summary_result:
            summary["total_amount"] = float(summary_result[1] or 0)
            summary["total_quantity"] = int(summary_result[2] or 0)
            summary["inbound_amount"] = float(summary_result[3] or 0)
            summary["outbound_amount"] = float(summary_result[4] or 0)
            summary["inbound_customer_count"] = int(summary_result[5] or 0)
            summary["outbound_customer_count"] = int(summary_result[6] or 0)
            summary["inbound_sku_count"] = int(summary_result[7] or 0)
            summary["outbound_sku_count"] = int(summary_result[8] or 0)

        # 将字段名转换为中文用于前端展示
        df_display = rename_for_display(df.copy(), "rpt_sales_out_wide")

        return {
            "data": df_display.to_dict(orient="records") if not df_display.empty else [],
            "summary": summary,
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"获取宽表数据失败: {e}")
        return {
            "data": [],
            "summary": {},
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
            "error": str(e)
        }


# ===================== 出货仪表盘 =====================
def get_dashboard_data(
    db: Session,
    region: Optional[str] = None,
    start_year_month: Optional[str] = None,
    end_year_month: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取出货仪表盘数据（用户选择的时间范围内数据、完成率、同比环比）

    Args:
        db: Database session
        region: 大区筛选
        start_year_month: 起始期间，格式 YYYY/MM
        end_year_month: 结束期间，格式 YYYY/MM
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        仪表盘数据
    """
    try:
        # 默认：结束月份为当前月份，起始月份为12个月前
        now = datetime.now()
        if not end_year_month:
            end_year_month = f"{now.year}/{now.month:02d}"
        if not start_year_month:
            prev12_month = now.month - 11
            prev12_year = now.year + (prev12_month - 1) // 12
            prev12_month = (prev12_month - 1) % 12 + 1
            start_year_month = f"{prev12_year}/{prev12_month:02d}"

        y, m = start_year_month.split("/")
        yi, mi = int(y), int(m)
        y_end, m_end = end_year_month.split("/")
        yi_end, mi_end = int(y_end), int(m_end)

        # 计算从起始到结束的月份列表
        all_months = []
        current_y, current_m = yi, mi
        while (current_y < yi_end) or (current_y == yi_end and current_m <= mi_end):
            all_months.append(f"{current_y}/{current_m:02d}")
            current_m += 1
            if current_m > 12:
                current_m = 1
                current_y += 1

        # 去年同期
        yoy_months = []
        for m_str in all_months:
            y2, m2 = m_str.split("/")
            y2i, m2i = int(y2), int(m2)
            prev_y = y2i - 1
            yoy_months.append(f"{prev_y}/{m2i:02d}")

        # 构建WHERE条件（区域权限过滤 + 用户选择的大区）
        conditions = []
        params = {}

        # 添加用户选择的大区筛选
        if region:
            conditions.append("region = :region")
            params["region"] = region
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询当前期数据（使用子查询避免 only_full_group_by 问题）
        current_sql = text(f"""
            SELECT ym, SUM(amount) AS amount
            FROM (
                SELECT CONCAT(CAST(YEAR(audit_date) AS CHAR), '/', LPAD(CAST(MONTH(audit_date) AS CHAR), 2, '0')) AS ym,
                       IFNULL(tax_included_amount, 0) AS amount
                FROM rpt_sales_out_wide
                WHERE audit_date IS NOT NULL
                  AND {where_clause}
            ) t
            WHERE ym >= :start_month AND ym <= :end_month
            GROUP BY ym
            ORDER BY ym
        """)
        current_params = {**params, "start_month": start_year_month, "end_month": end_year_month}
        current_result = db.execute(current_sql, current_params)
        current_data = {str(row[0]): float(row[1]) for row in current_result.fetchall()}

        # 查询去年同期数据（使用子查询避免 only_full_group_by 问题）
        prev_sql = text(f"""
            SELECT ym, SUM(amount) AS amount
            FROM (
                SELECT CONCAT(CAST(YEAR(audit_date) AS CHAR), '/', LPAD(CAST(MONTH(audit_date) AS CHAR), 2, '0')) AS ym,
                       IFNULL(tax_included_amount, 0) AS amount
                FROM rpt_sales_out_wide
                WHERE audit_date IS NOT NULL
                  AND {where_clause}
            ) t
            WHERE ym >= :prev_start AND ym <= :prev_end
            GROUP BY ym
            ORDER BY ym
        """)
        prev_params = {**params, "prev_start": yoy_months[0], "prev_end": yoy_months[-1]}
        prev_result = db.execute(prev_sql, prev_params)
        prev_data = {str(row[0]): float(row[1]) for row in prev_result.fetchall()}

        # 查询KPI数据
        kpi_conditions = ["period >= :start_month", "period <= :end_month"]
        kpi_params = {"start_month": start_year_month, "end_month": end_year_month}
        if region:
            kpi_conditions.append("region = :kpi_region")
            kpi_params["kpi_region"] = region
        if allowed_regions is not None and len(allowed_regions) > 0:
            kpi_conditions.append(f"region IN {_in_clause('ar', allowed_regions, kpi_params)}")
        kpi_where = " AND ".join(kpi_conditions)
        kpi_sql = text(f"""
            SELECT period, SUM(monthly_target) as target
            FROM dim_business_indicator_region
            WHERE {kpi_where}
            GROUP BY period
        """)
        kpi_result = db.execute(kpi_sql, kpi_params)
        kpi_data = {str(row[0]): float(row[1]) for row in kpi_result.fetchall()}

        # 查询大区×经理数据（使用子查询避免 only_full_group_by 问题）
        region_sql = text(f"""
            SELECT ym, region, account_manager, SUM(amount) AS amount
            FROM (
                SELECT CONCAT(CAST(YEAR(audit_date) AS CHAR), '/', LPAD(CAST(MONTH(audit_date) AS CHAR), 2, '0')) AS ym,
                       region, account_manager, IFNULL(tax_included_amount, 0) AS amount
                FROM rpt_sales_out_wide
                WHERE audit_date IS NOT NULL
                  AND {where_clause}
            ) t
            WHERE ym >= :start_month AND ym <= :end_month
            GROUP BY ym, region, account_manager
            ORDER BY ym
        """)
        region_result = db.execute(region_sql, current_params)
        region_data = [
            {"year_month": str(row[0]), "region": row[1], "manager": row[2], "amount": float(row[3])}
            for row in region_result.fetchall()
        ]

        # 计算各项指标
        table_data = []
        prev_month_amount = None

        for i, month in enumerate(all_months):
            current_amount = current_data.get(month, 0)
            prev_amount = prev_data.get(yoy_months[i], 0)
            kpi_target = kpi_data.get(month, 0)

            # 指标完成率
            completion_rate = 0.0
            if kpi_target and kpi_target > 0:
                completion_rate = round((current_amount / (kpi_target * 10000)) * 100, 2)

            # 同比
            yoy = 0.0
            if prev_amount and prev_amount > 0:
                yoy = round((current_amount / prev_amount - 1) * 100, 2)

            # 环比
            mom = 0.0
            if prev_month_amount is not None and prev_month_amount > 0:
                mom = round((current_amount / prev_month_amount - 1) * 100, 2)

            table_data.append({
                "year_month": month,
                "target": round(kpi_target, 2) if kpi_target else None,
                "amount_wan": round(current_amount / 10000, 2),
                "completion_rate": completion_rate,
                "yoy": yoy,
                "mom": mom,
            })

            prev_month_amount = current_amount

        return {
            "months": all_months,
            "table_data": table_data,
            "region_data": region_data,
        }
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        return {
            "months": [],
            "table_data": [],
            "region_data": [],
            "error": str(e)
        }


# ===================== 指标达成进度 =====================
def get_indicator_progress(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    year_month: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取指标达成进度数据

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        year_month: 期间，格式 YYYY/MM
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        指标达成进度数据
    """
    try:
        # 默认当前月份
        if not year_month:
            now = datetime.now()
            year_month = f"{now.year}/{now.month:02d}"

        y, m = year_month.split("/")
        target_year, target_month = int(y), int(m)

        # 计算周日期范围
        _, last_day = calendar.monthrange(target_year, target_month)
        month_start = f"{target_year}-{target_month:02d}-01"
        month_end = f"{target_year}-{target_month:02d}-{last_day:02d}"

        # 上月
        last_month_year = target_year if target_month > 1 else target_year - 1
        last_month_num = target_month - 1 if target_month > 1 else 12
        _, lm_last = calendar.monthrange(last_month_year, last_month_num)
        last_month_start = f"{last_month_year}-{last_month_num:02d}-01"
        last_month_end = f"{last_month_year}-{last_month_num:02d}-{lm_last:02d}"

        # 去年同期
        last_year_start = f"{target_year-1}-{target_month:02d}-01"
        _, ly_last = calendar.monthrange(target_year - 1, target_month)
        last_year_end = f"{target_year-1}-{target_month:02d}-{ly_last:02d}"

        # 周定义
        weeks = [
            ("W1", 1, 7),
            ("W2", 8, 14),
            ("W3", 15, 21),
            ("W4", 22, last_day),
        ]

        # 构建KPI基准SQL
        kpi_conditions = ["manager IS NOT NULL AND manager != ''", "period = :period"]
        kpi_params = {"period": year_month}
        if region:
            kpi_conditions.append("region = :kpi_region")
            kpi_params["kpi_region"] = region
        if manager:
            kpi_conditions.append("manager = :kpi_manager")
            kpi_params["kpi_manager"] = manager

        kpi_sql = text(f"""
            SELECT region, manager, SUM(monthly_target) as task
            FROM dim_business_indicator_region
            WHERE {' AND '.join(kpi_conditions)}
            GROUP BY region, manager
        """)

        # 构建销售数据SQL
        sales_conditions = ["audit_date IS NOT NULL"]
        sales_params = {
            "month_start": month_start,
            "month_end": month_end,
            "last_month_start": last_month_start,
            "last_month_end": last_month_end,
            "last_year_start": last_year_start,
            "last_year_end": last_year_end,
        }

        if region:
            sales_conditions.append("region = :sales_region")
            sales_params["sales_region"] = region
        if manager:
            sales_conditions.append("account_manager = :sales_manager")
            sales_params["sales_manager"] = manager
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            sales_conditions.append(f"region IN {_in_clause('ar', allowed_regions, sales_params)}")

        # 添加周日期参数（用于SELECT中的CASE WHEN，不用于WHERE）
        for i, (w_name, w_start, w_end) in enumerate(weeks):
            sales_params[f"w{i}_start"] = f"{target_year}-{target_month:02d}-{w_start:02d}"
            sales_params[f"w{i}_end"] = f"{target_year}-{target_month:02d}-{min(w_end, last_day):02d}"

        sales_sql = text(f"""
            SELECT region, account_manager as manager,
                   SUM(CASE WHEN audit_date BETWEEN :month_start AND :month_end
                        THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS current_month,
                   SUM(CASE WHEN audit_date BETWEEN :last_month_start AND :last_month_end
                        THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS last_month,
                   SUM(CASE WHEN audit_date BETWEEN :last_year_start AND :last_year_end
                        THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS last_year
            """)
        # 构建周数据列
        week_cols = []
        for i, (w_name, _, _) in enumerate(weeks):
            week_cols.append(f"SUM(CASE WHEN audit_date BETWEEN :w{i}_start AND :w{i}_end THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS {w_name.lower()}")

        # 完整SELECT语句
        select_stmt = f"""
            SELECT region, account_manager as manager,
                   SUM(CASE WHEN audit_date BETWEEN :month_start AND :month_end THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS current_month,
                   SUM(CASE WHEN audit_date BETWEEN :last_month_start AND :last_month_end THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS last_month,
                   SUM(CASE WHEN audit_date BETWEEN :last_year_start AND :last_year_end THEN IFNULL(tax_included_amount, 0) ELSE 0 END) AS last_year
                   {', ' + ', '.join(week_cols) if week_cols else ''}
            FROM rpt_sales_out_wide
            WHERE {' AND '.join(sales_conditions)}
            GROUP BY region, account_manager
        """
        sales_sql = text(select_stmt)

        # 查询KPI数据
        kpi_result = db.execute(kpi_sql, kpi_params)
        kpi_data = {f"{row[0]}|{row[1]}": float(row[2]) for row in kpi_result.fetchall()}

        # 查询销售数据
        sales_result = db.execute(sales_sql, sales_params)
        sales_rows = []
        for row in sales_result.fetchall():
            sales_rows.append({
                "region": row[0],
                "manager": row[1],
                "current_month": float(row[2]) if row[2] else 0,
                "last_month": float(row[3]) if row[3] else 0,
                "last_year": float(row[4]) if row[4] else 0,
                "w1": float(row[5]) if len(row) > 5 and row[5] else 0,
                "w2": float(row[6]) if len(row) > 6 and row[6] else 0,
                "w3": float(row[7]) if len(row) > 7 and row[7] else 0,
                "w4": float(row[8]) if len(row) > 8 and row[8] else 0,
            })

        # 合并数据
        result = []
        for row in sales_rows:
            key = f"{row['region']}|{row['manager']}"
            kpi_task = kpi_data.get(key, 0)

            # 转换为万元
            current_month = row["current_month"] / 10000
            last_month = row["last_month"] / 10000
            last_year = row["last_year"] / 10000
            weekly_tasks = [kpi_task / 4] * 4 if kpi_task else [0] * 4

            # 计算完成率和变动
            completion_rate = 0.0
            if kpi_task and kpi_task > 0:
                completion_rate = round((row["current_month"] / (kpi_task * 10000)) * 100, 2)

            mom_change = 0.0
            if last_month > 0:
                mom_change = round((current_month / last_month - 1) * 100, 2)

            yoy_change = 0.0
            if last_year > 0:
                yoy_change = round((current_month / last_year - 1) * 100, 2)

            item = {
                "region": row["region"],
                "manager": row["manager"],
                "current_month": round(current_month, 2),
                "last_month": round(last_month, 2),
                "last_year": round(last_year, 2),
                "task": round(kpi_task, 2) if kpi_task else 0,
                "week_task": [round(t, 2) for t in weekly_tasks],
                "completion_rate": completion_rate,
                "mom": mom_change,
                "yoy": yoy_change,
            }

            # 添加周数据
            for i, w_name in enumerate(["w1", "w2", "w3", "w4"]):
                week_amount = row[w_name] / 10000
                week_rate = 0.0
                if weekly_tasks[i] > 0:
                    week_rate = round((row[w_name] / (weekly_tasks[i] * 10000)) * 100, 2)
                item[w_name] = round(week_amount, 2)
                item[f"{w_name}_rate"] = week_rate

            result.append(item)

        # 计算汇总行
        if result:
            total_current = sum(r["current_month"] for r in result)
            total_last = sum(r["last_month"] for r in result)
            total_last_year = sum(r["last_year"] for r in result)
            total_task = sum(r["task"] for r in result)

            total_completion = 0.0
            if total_task > 0:
                total_completion = round((total_current / total_task) * 100, 2)

            total_mom = 0.0
            if total_last > 0:
                total_mom = round((total_current / total_last - 1) * 100, 2)

            total_yoy = 0.0
            if total_last_year > 0:
                total_yoy = round((total_current / total_last_year - 1) * 100, 2)

            summary = {
                "region": "渠道事业部小计",
                "manager": "",
                "current_month": round(total_current, 2),
                "last_month": round(total_last, 2),
                "last_year": round(total_last_year, 2),
                "task": round(total_task, 2),
                "completion_rate": total_completion,
                "mom": total_mom,
                "yoy": total_yoy,
            }
            for w_name in ["w1", "w2", "w3", "w4"]:
                summary[w_name] = round(sum(r.get(w_name, 0) for r in result), 2)
                summary[f"{w_name}_rate"] = round(sum(r.get(f"{w_name}_rate", 0) for r in result), 2)
        else:
            summary = {}

        return {
            "data": result,
            "summary": summary,
            "period": year_month,
        }
    except Exception as e:
        logger.error(f"获取指标达成进度失败: {e}")
        return {
            "data": [],
            "summary": {},
            "period": year_month,
            "error": str(e)
        }


# ===================== 销售出库明细 =====================
def get_sales_detail(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    customer: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    abc_class: Optional[str] = None,
    material_code: Optional[str] = None,
    group_by: str = "material",
    page: int = 1,
    page_size: int = 100,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取销售出库明细数据

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        customer: 客户
        date_from: 开始日期
        date_to: 结束日期
        category: 品类
        abc_class: ABC分类
        material_code: 物料编码
        group_by: 分组维度 (material/region_customer/region_material/customer_material)
        page: 页码
        page_size: 每页数量
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        销售明细数据
    """
    try:
        # 计算YoY/MoM日期
        if date_from and date_to:
            start_dt = datetime.strptime(date_from, "%Y-%m-%d")
            end_dt = datetime.strptime(date_to, "%Y-%m-%d")

            # YoY: 去年相同时期
            def shift_months(dt, months):
                target_month = dt.month - months
                target_year = dt.year + (target_month - 1) // 12
                target_month = ((target_month - 1) % 12) + 1
                last_day = calendar.monthrange(target_year, target_month)[1]
                return dt.replace(year=target_year, month=target_month, day=min(dt.day, last_day))

            yoy_start = shift_months(start_dt, 12)
            yoy_end = shift_months(end_dt, 12)

            # MoM: 上月同期
            n_days = (end_dt - start_dt).days + 1
            if start_dt.day == 1 and end_dt.day == calendar.monthrange(end_dt.year, end_dt.month)[1]:
                prev_month = start_dt.month - 1
                prev_year = start_dt.year
                if prev_month == 0:
                    prev_month = 12
                    prev_year -= 1
                last_day = calendar.monthrange(prev_year, prev_month)[1]
                mom_start = date(prev_year, prev_month, 1)
                mom_end = date(prev_year, prev_month, last_day)
            else:
                target_month = start_dt.month - 1
                target_year = start_dt.year
                if target_month == 0:
                    target_month = 12
                    target_year -= 1
                last_day = calendar.monthrange(target_year, target_month)[1]
                mom_start = start_dt.replace(year=target_year, month=target_month, day=min(start_dt.day, last_day))
                mom_end = mom_start + timedelta(days=n_days - 1)
        else:
            return {"data": [], "total": 0, "error": "日期范围必须指定"}

        # 构建WHERE条件
        conditions = ["audit_date IS NOT NULL"]
        params = {}

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if customer:
            conditions.append("customer = :customer")
            params["customer"] = customer
        if date_from:
            conditions.append("audit_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("audit_date <= :date_to")
            params["date_to"] = date_to
        if category:
            conditions.append("category = :category")
            params["category"] = category
        if abc_class:
            conditions.append("abc_class = :abc_class")
            params["abc_class"] = abc_class
        if material_code:
            conditions.append("material_code = :material_code")
            params["material_code"] = material_code
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions)

        # 根据group_by确定分组字段
        group_fields = {
            "material": ["material_code", "material_name"],
            "region_customer": ["region", "customer"],
            "region_material": ["region", "material_code", "material_name"],
            "customer_material": ["customer", "material_code", "material_name"],
        }
        selected_fields = group_fields.get(group_by, group_fields["material"])

        # 主查询
        select_cols = ", ".join(selected_fields)
        data_sql = text(f"""
            SELECT {select_cols},
                   SUM(IFNULL(tax_included_amount, 0)) AS amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS quantity,
                   COUNT(DISTINCT doc_no) AS order_count
            FROM rpt_sales_out_wide
            WHERE {where_clause}
            GROUP BY {select_cols}
            ORDER BY SUM(IFNULL(tax_included_amount, 0)) DESC
        """)

        result = db.execute(data_sql, params)
        columns = list(result.keys())
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

        if df.empty:
            return {"data": [], "total": 0, "columns": selected_fields}

        # 合并YoY和MoM数据（YoY/MoM只应用非日期过滤条件）
        # 构建YoY/MoM查询专用的WHERE条件（排除日期范围和allowed_regions）
        yoy_conditions = ["audit_date IS NOT NULL"]
        yoy_params = {}
        if region:
            yoy_conditions.append("region = :region")
            yoy_params["region"] = region
        if manager:
            yoy_conditions.append("account_manager = :manager")
            yoy_params["manager"] = manager
        if customer:
            yoy_conditions.append("customer = :customer")
            yoy_params["customer"] = customer
        if category:
            yoy_conditions.append("category = :category")
            yoy_params["category"] = category
        if abc_class:
            yoy_conditions.append("abc_class = :abc_class")
            yoy_params["abc_class"] = abc_class
        if material_code:
            yoy_conditions.append("material_code = :material_code")
            yoy_params["material_code"] = material_code

        yoy_where = " AND ".join(yoy_conditions)

        yoy_sql = text(f"""
            SELECT {select_cols},
                   SUM(IFNULL(tax_included_amount, 0)) AS yoy_amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS yoy_quantity
            FROM rpt_sales_out_wide
            WHERE audit_date >= :yoy_start AND audit_date <= :yoy_end
              AND {yoy_where}
            GROUP BY {select_cols}
        """)

        mom_sql = text(f"""
            SELECT {select_cols},
                   SUM(IFNULL(tax_included_amount, 0)) AS mom_amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS mom_quantity
            FROM rpt_sales_out_wide
            WHERE audit_date >= :mom_start AND audit_date <= :mom_end
              AND {yoy_where}
            GROUP BY {select_cols}
        """)

        # 构建YoY/MoM查询参数
        yoy_mom_params = {
            "yoy_start": yoy_start.strftime("%Y-%m-%d"),
            "yoy_end": yoy_end.strftime("%Y-%m-%d"),
            "mom_start": mom_start.strftime("%Y-%m-%d") if isinstance(mom_start, date) else mom_start.strftime("%Y-%m-%d"),
            "mom_end": mom_end.strftime("%Y-%m-%d") if isinstance(mom_end, date) else mom_end.strftime("%Y-%m-%d"),
        }
        # 添加其他过滤参数（排除allowed_regions，因为yoy_where已处理）
        for key in ["region", "manager", "customer", "category", "abc_class", "material_code"]:
            if key in params:
                yoy_mom_params[key] = params[key]

        df_yoy = pd.read_sql(yoy_sql, db.bind, params=yoy_mom_params)
        df_mom = pd.read_sql(mom_sql, db.bind, params=yoy_mom_params)

        # 合并YoY/MoM - 使用所有分组字段作为merge key
        merge_keys = [f for f in selected_fields if f in df.columns and f in df_yoy.columns]

        if not df_yoy.empty:
            df = df.merge(df_yoy, on=merge_keys, how="left")
        if not df_mom.empty:
            df = df.merge(df_mom, on=merge_keys, how="left")

        # 将 NaN 替换为 None 以便 JSON 序列化
        for col in df.columns:
            try:
                df[col] = df[col].where(pd.notna(df[col]), None)
            except Exception:
                # 如果某列无法处理，直接移除该列
                df = df.drop(columns=[col])
                logger.warning(f"移除无法处理的列: {col}")

        # 填充缺失值
        for col in ["yoy_amount", "yoy_quantity", "mom_amount", "mom_quantity"]:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        # 计算YoY/MoM变动
        df["yoy_change"] = df["amount"] - df.get("yoy_amount", pd.Series(0, index=df.index))
        df["mom_change"] = df["amount"] - df.get("mom_amount", pd.Series(0, index=df.index))

        total_amount = df["amount"].sum()

        # 计算占比
        df["share"] = df["amount"] / total_amount * 100 if total_amount > 0 else 0

        # 获取上期金额和数量（用于百分比计算）
        yoy_amount = df.get("yoy_amount", pd.Series(0, index=df.index)).fillna(0)
        mom_amount = df.get("mom_amount", pd.Series(0, index=df.index)).fillna(0)
        yoy_quantity = df.get("yoy_quantity", pd.Series(0, index=df.index)).fillna(0)
        mom_quantity = df.get("mom_quantity", pd.Series(0, index=df.index)).fillna(0)
        current_quantity = df["quantity"]

        # 计算YoY/MoM百分比（避免除零 - 使用 boolean indexing 避免 np.where 的提前计算问题）
        abs_yoy_amount = np.abs(yoy_amount)
        abs_mom_amount = np.abs(mom_amount)
        abs_yoy_quantity = np.abs(yoy_quantity)
        abs_mom_quantity = np.abs(mom_quantity)

        df["amount_yoy_pct"] = 0.0
        df["amount_mom_pct"] = 0.0
        df["qty_yoy_pct"] = 0.0
        df["qty_mom_pct"] = 0.0

        mask_yoy_amt = abs_yoy_amount > 0
        if mask_yoy_amt.any():
            df.loc[mask_yoy_amt, "amount_yoy_pct"] = (df.loc[mask_yoy_amt, "yoy_change"] / abs_yoy_amount.loc[mask_yoy_amt]) * 100

        mask_mom_amt = abs_mom_amount > 0
        if mask_mom_amt.any():
            df.loc[mask_mom_amt, "amount_mom_pct"] = (df.loc[mask_mom_amt, "mom_change"] / abs_mom_amount.loc[mask_mom_amt]) * 100

        mask_yoy_qty = abs_yoy_quantity > 0
        if mask_yoy_qty.any():
            df.loc[mask_yoy_qty, "qty_yoy_pct"] = ((current_quantity.loc[mask_yoy_qty] - yoy_quantity.loc[mask_yoy_qty]) / abs_yoy_quantity.loc[mask_yoy_qty]) * 100

        mask_mom_qty = abs_mom_quantity > 0
        if mask_mom_qty.any():
            df.loc[mask_mom_qty, "qty_mom_pct"] = ((current_quantity.loc[mask_mom_qty] - mom_quantity.loc[mask_mom_qty]) / abs_mom_quantity.loc[mask_mom_qty]) * 100

        # 计算数量差值
        df["yoy_qty_diff"] = current_quantity - yoy_quantity
        df["mom_qty_diff"] = current_quantity - mom_quantity

        # 计算数量占比
        total_quantity = current_quantity.sum()
        df["qty_share_pct"] = (current_quantity / total_quantity * 100) if total_quantity > 0 else 0

        # 格式化输出
        result_data = []
        for _, row in df.iterrows():
            item = {k: v for k, v in row.items() if pd.notna(k)}
            item["tax_included_amount_sum"] = round(item.get("amount", 0) / 10000, 2)
            item["yoy_amount_diff"] = round(item.get("yoy_change", 0) / 10000, 2)
            item["mom_amount_diff"] = round(item.get("mom_change", 0) / 10000, 2)
            item["amount_yoy_pct"] = round(item.get("amount_yoy_pct", 0), 1)
            item["amount_mom_pct"] = round(item.get("amount_mom_pct", 0), 1)
            item["amount_share_pct"] = round(item.get("share", 0), 1)
            item["quantity_sum"] = item.get("quantity", 0)
            item["yoy_qty_diff"] = item.get("yoy_qty_diff", 0)
            item["mom_qty_diff"] = item.get("mom_qty_diff", 0)
            item["qty_yoy_pct"] = round(item.get("qty_yoy_pct", 0), 1)
            item["qty_mom_pct"] = round(item.get("qty_mom_pct", 0), 1)
            item["qty_share_pct"] = round(item.get("qty_share_pct", 0), 1)
            result_data.append(item)

        # 分页
        total = len(result_data)
        offset = (page - 1) * page_size
        paginated_data = result_data[offset:offset + page_size]

        return {
            "data": paginated_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    except Exception as e:
        logger.error(f"获取销售明细失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        error_msg = str(e)
        # 如果错误消息太长，只显示前100个字符
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + "..."
        return {"data": [], "total": 0, "error": error_msg}


# ===================== 单品货流明细 =====================
def get_product_flow_detail(
    db: Session,
    material_code: Optional[str] = None,
    batch_no: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    customer: Optional[str] = None,
    order_type: Optional[str] = None,
    region: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 100,
) -> Dict[str, Any]:
    """
    获取单品货流明细 - 对齐前端期望格式

    Args:
        db: Database session
        material_code: 物料编码
        batch_no: 批次号
        date_from: 开始日期
        date_to: 结束日期
        customer: 客户
        order_type: 交易类型 (销售出库/退货入库)
        region: 大区
        allowed_regions: 允许访问的大区列表，None表示无限制
        page: 页码
        page_size: 每页数量

    Returns:
        货流明细数据
    """
    try:
        # 构建WHERE条件
        conditions = ["audit_date IS NOT NULL"]
        params = {}

        if material_code and material_code.strip():
            conditions.append("material_code = :material_code")
            params["material_code"] = material_code.strip()
        if batch_no and batch_no.strip():
            conditions.append("batch_no = :batch_no")
            params["batch_no"] = batch_no.strip()
        if date_from:
            conditions.append("audit_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("audit_date <= :date_to")
            params["date_to"] = date_to
        if customer and str(customer).strip():
            conditions.append("customer = :customer")
            params["customer"] = str(customer).strip()
        if order_type == "销售出库":
            conditions.append("tax_included_amount >= 0")
        elif order_type == "退货入库":
            conditions.append("tax_included_amount < 0")
        if region:
            conditions.append("region = :region")
            params["region"] = region
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions)

        # 统计汇总 - 对齐前端字段名
        stats_sql = text(f"""
            SELECT
                COALESCE(SUM(IFNULL(tax_included_amount, 0)), 0) AS total_amount,
                COALESCE(SUM(IFNULL(sales_out_qty, 0)), 0) AS total_quantity,
                COUNT(DISTINCT batch_no) AS total_batches,
                COUNT(DISTINCT customer) AS total_customers
            FROM rpt_sales_out_wide
            WHERE {where_clause}
        """)
        stats_result = db.execute(stats_sql, params)
        stats_row = stats_result.fetchone()

        summary = {
            "totalAmount": float(stats_row[0]) if stats_row and stats_row[0] else 0,
            "totalQuantity": int(float(stats_row[1])) if stats_row and stats_row[1] else 0,
            "totalBatches": int(stats_row[2]) if stats_row and stats_row[2] else 0,
            "totalCustomers": int(stats_row[3]) if stats_row and stats_row[3] else 0,
        }

        # 计算分页 - 使用 COUNT(*) 返回原始行数
        total_result = db.execute(text(f"""
            SELECT COUNT(*) FROM rpt_sales_out_wide WHERE {where_clause}
        """), params)
        total = total_result.fetchone()[0] or 0
        offset = (page - 1) * page_size

        # 获取原始明细数据（不按 doc_no 分组）
        data_sql = text(f"""
            SELECT
                doc_no AS 单据编号,
                invoiced_qty AS 已开票数量,
                source_tx_type AS 源头交易类型,
                tx_type AS 交易类型,
                customer AS 客户,
                customer_class AS 客户分类,
                warehouse AS 仓库,
                DATE_FORMAT(audit_date, '%Y-%m-%d') AS 审核日期,
                material_code AS 物料编码,
                material_name AS 物料名称,
                batch_no AS 批次号,
                tax_included_amount AS 含税金额,
                sales_out_qty AS 销售出库数量
            FROM rpt_sales_out_wide
            WHERE {where_clause}
            ORDER BY audit_date DESC
            LIMIT :limit OFFSET :offset
        """)

        params["limit"] = page_size
        params["offset"] = offset

        result = db.execute(data_sql, params)
        columns = list(result.keys())
        rows = result.fetchall()

        # 格式化输出
        items = []
        for row in rows:
            item = {columns[i]: (row[i] if row[i] is not None else None) for i in range(len(columns))}
            # 格式化金额
            if item.get("含税金额") is not None:
                item["含税金额"] = float(item["含税金额"])
            # 格式化审核日期
            if item.get("审核日期"):
                item["审核日期"] = str(item["审核日期"])
            items.append(item)

        # 获取趋势图数据（按日期汇总）- 入库从采购入库表，出库从销售出库表
        # 构建入库查询条件
        in_conditions = ["audit_date IS NOT NULL"]
        in_params = {}
        if date_from:
            in_conditions.append("audit_date >= :date_from")
            in_params["date_from"] = date_from
        if date_to:
            in_conditions.append("audit_date <= :date_to")
            in_params["date_to"] = date_to
        if material_code and material_code.strip():
            in_conditions.append("material_code = :material_code")
            in_params["material_code"] = material_code.strip()
        if batch_no and batch_no.strip():
            in_conditions.append("batch_no = :batch_no")
            in_params["batch_no"] = batch_no.strip()
        in_where_clause = " AND ".join(in_conditions)

        # 构建出库查询条件
        out_conditions = ["audit_date IS NOT NULL"]
        out_params = {}
        if date_from:
            out_conditions.append("audit_date >= :date_from")
            out_params["date_from"] = date_from
        if date_to:
            out_conditions.append("audit_date <= :date_to")
            out_params["date_to"] = date_to
        if material_code and material_code.strip():
            out_conditions.append("material_code = :material_code")
            out_params["material_code"] = material_code.strip()
        if batch_no and batch_no.strip():
            out_conditions.append("batch_no = :batch_no")
            out_params["batch_no"] = batch_no.strip()
        if customer and str(customer).strip():
            out_conditions.append("customer = :customer")
            out_params["customer"] = str(customer).strip()
        if order_type == "销售出库":
            out_conditions.append("tax_included_amount >= 0")
        elif order_type == "退货入库":
            out_conditions.append("tax_included_amount < 0")
        out_where_clause = " AND ".join(out_conditions)

        # 查询入库数量 (应收数量)
        inbound_sql = text(f"""
            SELECT
                DATE(audit_date) AS date,
                SUM(IFNULL(receivable_qty, 0)) AS inbound_qty
            FROM stg_stock_in
            WHERE {in_where_clause}
            GROUP BY DATE(audit_date)
            ORDER BY DATE(audit_date)
        """)
        inbound_result = db.execute(inbound_sql, in_params)
        inbound_rows = inbound_result.fetchall()

        # 查询出库数量 (应发数量)
        outbound_sql = text(f"""
            SELECT
                DATE(audit_date) AS date,
                SUM(IFNULL(dispatch_qty, 0)) AS outbound_qty
            FROM stg_sales_out
            WHERE {out_where_clause}
            GROUP BY DATE(audit_date)
            ORDER BY DATE(audit_date)
        """)
        outbound_result = db.execute(outbound_sql, out_params)
        outbound_rows = outbound_result.fetchall()

        # 合并数据
        date_map = {}
        for row in inbound_rows:
            date_str = str(row[0])
            date_map[date_str] = {"inbound": float(row[1]), "outbound": 0}
        for row in outbound_rows:
            date_str = str(row[0])
            if date_str in date_map:
                date_map[date_str]["outbound"] = float(row[1])
            else:
                date_map[date_str] = {"inbound": 0, "outbound": float(row[1])}

        # 按日期排序
        dates = sorted(date_map.keys())
        inbounds = [date_map[d]["inbound"] for d in dates]
        outbounds = [date_map[d]["outbound"] for d in dates]

        return {
            "items": items,
            "summary": summary,
            "dates": dates,
            "inbounds": inbounds,
            "outbounds": outbounds,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"获取货流明细失败: {e}")
        return {"items": [], "summary": {}, "total": 0, "error": str(e)}


# ===================== 明星商品评分 =====================
def get_star_products(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    top_n: int = 30,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取明星商品评分

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        date_from: 开始日期 YYYY-MM-DD
        date_to: 结束日期 YYYY-MM-DD
        top_n: 返回前N个商品
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        明星商品评分数据
    """
    try:
        import calendar
        from datetime import timedelta

        # 默认日期范围：最近12个月
        if not date_from or not date_to:
            now = datetime.now()
            start_y, start_m = now.year, now.month - 11
            if start_m <= 0:
                start_m += 12
                start_y -= 1
            date_from = f"{start_y}-{start_m:02d}-01"
            # 计算结束日期（当前日期）
            date_to = now.strftime("%Y-%m-%d")

        # 解析日期
        start_dt = datetime.strptime(date_from, "%Y-%m-%d")
        end_dt = datetime.strptime(date_to, "%Y-%m-%d")

        # Helper函数
        def _is_month_end(dt):
            return dt.day == calendar.monthrange(dt.year, dt.month)[1]

        def _shift_months(dt, months):
            """将日期平移指定月数，保持相同日期（但不超过月末）"""
            target_month = dt.month - months
            target_year = dt.year + (target_month - 1) // 12
            target_month = ((target_month - 1) % 12) + 1
            last_day = calendar.monthrange(target_year, target_month)[1]
            return dt.replace(year=target_year, month=target_month, day=min(dt.day, last_day))

        def _get_mom_period(start_dt, end_dt):
            """返回上月同期：整月选区则对齐到完整上月1日~月末，否则保持天数逐日平移"""
            n_days = (end_dt - start_dt).days + 1
            if start_dt.day == 1 and _is_month_end(end_dt):
                # 整月选择：取上月完整月
                prev_month = start_dt.month - 1
                prev_year = start_dt.year
                if prev_month == 0:
                    prev_month = 12
                    prev_year -= 1
                last_day = calendar.monthrange(prev_year, prev_month)[1]
                return date(prev_year, prev_month, 1), date(prev_year, prev_month, last_day)
            else:
                # 非整月：按天数平移
                target_month = start_dt.month - 1
                target_year = start_dt.year
                if target_month == 0:
                    target_month = 12
                    target_year -= 1
                last_day = calendar.monthrange(target_year, target_month)[1]
                prev_start = start_dt.replace(year=target_year, month=target_month, day=min(start_dt.day, last_day))
                prev_end = prev_start + timedelta(days=n_days - 1)
                return prev_start.date(), prev_end.date()

        # 计算同比期间（日期平移12个月）
        yoy_start = _shift_months(start_dt, 12)
        yoy_end = _shift_months(end_dt, 12)

        # 计算环比期间
        mom_start, mom_end = _get_mom_period(start_dt, end_dt)

        # 构建WHERE条件
        conditions = []
        params = {}

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询TOP商品（当前期）
        sql = text(f"""
            SELECT material_code, material_name, brand,
                   SUM(IFNULL(tax_included_amount, 0)) AS sales_amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS sales_qty,
                   COUNT(DISTINCT doc_no) AS order_count
            FROM rpt_sales_out_wide
            WHERE audit_date IS NOT NULL
              AND audit_date >= :date_from
              AND audit_date <= :date_to
              AND {where_clause}
            GROUP BY material_code, material_name, brand
            ORDER BY sales_amount DESC
            LIMIT :top_n
        """)
        sql_params = {**params, "date_from": date_from, "date_to": date_to, "top_n": top_n}

        result = db.execute(sql, sql_params)
        columns = list(result.keys())
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

        if df.empty:
            return {"products": [], "total_sales": 0}

        # 去年同期数据
        prev_sql = text(f"""
            SELECT material_code,
                   SUM(IFNULL(tax_included_amount, 0)) AS prev_amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS prev_qty,
                   COUNT(DISTINCT doc_no) AS prev_order_count
            FROM rpt_sales_out_wide
            WHERE audit_date IS NOT NULL
              AND audit_date >= :yoy_start
              AND audit_date <= :yoy_end
              AND {where_clause}
            GROUP BY material_code
        """)
        prev_params = {k: v for k, v in params.items() if k not in ["date_from", "date_to", "top_n"]}
        prev_params["yoy_start"] = yoy_start.strftime("%Y-%m-%d")
        prev_params["yoy_end"] = yoy_end.strftime("%Y-%m-%d")

        df_prev = pd.read_sql(prev_sql, db.bind, params=prev_params)

        # 上月同期数据（环比）
        mom_sql = text(f"""
            SELECT material_code,
                   SUM(IFNULL(tax_included_amount, 0)) AS mom_amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS mom_qty
            FROM rpt_sales_out_wide
            WHERE audit_date IS NOT NULL
              AND audit_date >= :mom_start
              AND audit_date <= :mom_end
              AND {where_clause}
            GROUP BY material_code
        """)
        mom_params = {k: v for k, v in params.items() if k not in ["date_from", "date_to", "top_n"]}
        mom_params["mom_start"] = mom_start.strftime("%Y-%m-%d") if isinstance(mom_start, date) else str(mom_start)
        mom_params["mom_end"] = mom_end.strftime("%Y-%m-%d") if isinstance(mom_end, date) else str(mom_end)

        df_mom = pd.read_sql(mom_sql, db.bind, params=mom_params)

        # 合并数据
        df = df.merge(df_prev, on="material_code", how="left")
        df = df.merge(df_mom, on="material_code", how="left")

        # 计算衍生指标
        total_sales = df["sales_amount"].sum()

        df["market_share"] = df["sales_amount"] / total_sales * 100 if total_sales > 0 else 0
        df["unit_price"] = df["sales_amount"] / df["sales_qty"] if df["sales_qty"].sum() > 0 else 0
        df["avg_units_per_order"] = df["sales_qty"] / df["order_count"].where(df["order_count"] > 0, 0)

        # 同比
        df["yoy_amount"] = ((df["sales_amount"] - df["prev_amount"]) / df["prev_amount"] * 100).where(df["prev_amount"] > 0, 0)
        df["yoy_qty"] = ((df["sales_qty"] - df["prev_qty"]) / df["prev_qty"] * 100).where(df["prev_qty"] > 0, 0)
        df["yoy_order"] = ((df["order_count"] - df["prev_order_count"]) / df["prev_order_count"] * 100).where(df["prev_order_count"] > 0, 0)

        # 环比
        df["mom_amount"] = ((df["sales_amount"] - df["mom_amount"]) / df["mom_amount"] * 100).where(df["mom_amount"] > 0, 0)
        df["mom_qty"] = ((df["sales_qty"] - df["mom_qty"]) / df["mom_qty"] * 100).where(df["mom_qty"] > 0, 0)

        # 格式化输出
        products = []
        for idx, row in df.iterrows():
            products.append({
                "rank": idx + 1,
                "material_code": row["material_code"],
                "material_name": row["material_name"],
                "brand": row.get("brand", ""),
                "sales_amount": float(row["sales_amount"]),
                "sales_amount_wan": round(float(row["sales_amount"]) / 10000, 2),
                "market_share": round(float(row["market_share"]), 2),
                "sales_qty": int(row["sales_qty"]),
                "order_count": int(row["order_count"]),
                "unit_price": round(float(row["unit_price"]), 2),
                "avg_units_per_order": round(float(row["avg_units_per_order"]), 2),
                "yoy_amount": round(float(row["yoy_amount"]), 2),
                "yoy_qty": round(float(row["yoy_qty"]), 2),
                "mom_amount": round(float(row["mom_amount"]), 2) if pd.notna(row["mom_amount"]) else None,
                "mom_qty": round(float(row["mom_qty"]), 2) if pd.notna(row["mom_qty"]) else None,
            })

        return {
            "products": products,
            "total_sales": float(total_sales),
            "period": {"start": date_from, "end": date_to},
        }
    except Exception as e:
        logger.error(f"获取明星商品失败: {e}")
        return {"products": [], "total_sales": 0, "error": str(e)}


# ===================== 客户分层数据 =====================
def get_customer_tier_data(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    start_year_month: Optional[str] = None,
    end_year_month: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取客户分层数据

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        start_year_month: 起始期间 YYYY/MM
        end_year_month: 结束期间 YYYY/MM
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        客户分层数据
    """
    try:
        # 默认：结束月份为当前月份，起始月份为12个月前
        now = datetime.now()
        if not end_year_month:
            end_year_month = f"{now.year}/{now.month:02d}"
        if not start_year_month:
            prev12_month = now.month - 11
            prev12_year = now.year + (prev12_month - 1) // 12
            prev12_month = (prev12_month - 1) % 12 + 1
            start_year_month = f"{prev12_year}/{prev12_month:02d}"

        # 计算从起始到结束的月份列表
        y, m = start_year_month.split("/")
        yi, mi = int(y), int(m)
        y_end, m_end = end_year_month.split("/")
        yi_end, mi_end = int(y_end), int(m_end)

        all_months = []
        current_y, current_m = yi, mi
        while (current_y < yi_end) or (current_y == yi_end and current_m <= mi_end):
            all_months.append(f"{current_y}/{current_m:02d}")
            current_m += 1
            if current_m > 12:
                current_m = 1
                current_y += 1

        end_month = all_months[-1] if all_months else end_year_month

        # 构建WHERE条件
        conditions = []
        params = {}

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询客户金额 - 使用DATE_FORMAT避免GROUP BY别名问题
        # 注意: 需要在text()中使用%Y/%m格式
        inner_sql = """
            SELECT DATE_FORMAT(audit_date, '%Y/%m') AS ym,
                   customer,
                   IFNULL(tax_included_amount, 0) AS amount
            FROM rpt_sales_out_wide
            WHERE audit_date IS NOT NULL
              AND {where_clause}
        """.format(where_clause=where_clause)
        sql = text("""
            SELECT ym, customer, SUM(amount) AS total_amount
            FROM (
                """ + inner_sql + """
            ) AS derived
            WHERE ym >= :start_month AND ym <= :end_month
            GROUP BY ym, customer
            ORDER BY ym
        """)
        sql_params = {**params, "start_month": start_year_month, "end_month": end_month}

        result = db.execute(sql, sql_params)
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=["year_month", "customer", "amount"]) if rows else pd.DataFrame()

        if df.empty:
            return {"tier_distribution": [], "tier_by_month": {}}

        # 先按年月×客户聚合（明细数据聚合）
        df = df.groupby(["year_month", "customer"])["amount"].sum().reset_index()

        # 分类函数
        def classify_tier(amount):
            if amount < 50000:
                return "<5万"
            elif amount < 100000:
                return "5-10万"
            elif amount < 200000:
                return "10-20万"
            elif amount < 500000:
                return "20-50万"
            elif amount < 1000000:
                return "50-100万"
            else:
                return ">=100万"

        tier_order = ["<5万", "5-10万", "10-20万", "20-50万", "50-100万", ">=100万"]

        # 按等级分类
        df["tier"] = df["amount"].apply(classify_tier)

        # 按月×等级聚合
        tier_amt = df.groupby(["year_month", "tier"])["amount"].sum().reset_index()
        tier_amt["amount_wan"] = tier_amt["amount"] / 10000

        # 客户数量
        tier_cnt = df.groupby(["year_month", "tier"])["customer"].nunique().reset_index()
        tier_cnt.columns = ["year_month", "tier", "customer_count"]

        # 转为透视表
        pivot_amt = tier_amt.pivot_table(
            index="year_month", columns="tier", values="amount_wan", aggfunc="sum", fill_value=0
        )
        pivot_amt = pivot_amt.reindex(all_months, fill_value=0)
        pivot_amt = pivot_amt.reindex(columns=[c for c in tier_order if c in pivot_amt.columns], fill_value=0)

        pivot_cnt = tier_cnt.pivot_table(
            index="year_month", columns="tier", values="customer_count", aggfunc="sum", fill_value=0
        )
        pivot_cnt = pivot_cnt.reindex(all_months, fill_value=0)
        pivot_cnt = pivot_cnt.reindex(columns=[c for c in tier_order if c in pivot_cnt.columns], fill_value=0)

        return {
            "tier_order": tier_order,
            "tier_by_month": {
                "months": all_months,
                "amount_data": pivot_amt.to_dict(orient="list"),
                "customer_data": pivot_cnt.to_dict(orient="list"),
            },
        }
    except Exception as e:
        logger.error(f"获取客户分层数据失败: {e}")
        return {"tier_distribution": [], "tier_by_month": {}, "error": str(e)}


# ===================== 区域×客户排名 =====================
def get_region_customer_ranking(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    top_n: int = 50,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取区域×客户排名

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        date_from: 开始日期
        date_to: 结束日期
        top_n: 返回前N个
        allowed_regions: 允许访问的大区列表，None表示无限制

    Returns:
        区域×客户排名数据
    """
    try:
        # 构建WHERE条件
        conditions = ["audit_date IS NOT NULL"]
        params = {}

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if date_from:
            conditions.append("audit_date >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("audit_date <= :date_to")
            params["date_to"] = date_to
        # 添加区域权限过滤
        if allowed_regions is not None and len(allowed_regions) > 0:
            conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

        where_clause = " AND ".join(conditions)

        # 查询数据
        sql = text(f"""
            SELECT region, customer,
                   SUM(IFNULL(tax_included_amount, 0)) AS amount,
                   SUM(IFNULL(sales_out_qty, 0)) AS quantity,
                   COUNT(DISTINCT doc_no) AS order_count
            FROM rpt_sales_out_wide
            WHERE {where_clause}
            GROUP BY region, customer
            ORDER BY amount DESC
            LIMIT :top_n
        """)
        sql_params = {**params, "top_n": top_n}

        result = db.execute(sql, sql_params)
        columns = list(result.keys())
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame()

        if df.empty:
            return {"rankings": []}

        # 计算总计和占比
        total_amount = df["amount"].sum()
        df["rank"] = range(1, len(df) + 1)
        df["amount_wan"] = df["amount"] / 10000
        df["share_pct"] = df["amount"] / total_amount * 100 if total_amount > 0 else 0
        df["cumsum_pct"] = df["share_pct"].cumsum()

        # 格式化输出
        rankings = []
        for _, row in df.iterrows():
            rankings.append({
                "rank": int(row["rank"]),
                "region": row["region"],
                "customer": row["customer"],
                "amount": float(row["amount"]),
                "amount_wan": round(float(row["amount_wan"]), 2),
                "quantity": int(row["quantity"]),
                "order_count": int(row["order_count"]),
                "share_pct": round(float(row["share_pct"]), 1),
                "cumsum_pct": round(float(row["cumsum_pct"]), 1),
            })

        return {
            "rankings": rankings,
            "total_amount": float(total_amount),
        }
    except Exception as e:
        logger.error(f"获取区域客户排名失败: {e}")
        return {"rankings": [], "error": str(e)}


# ===================== 品类分布 =====================
def get_category_distribution(db: Session, start_month: str = None, end_month: str = None,
                              allowed_regions: Optional[List[str]] = None, region: Optional[str] = None) -> Dict:
    """按品类统计销售金额分布（按月分组）"""
    if not start_month:
        today = datetime.now()
        start_month_num = today.month - 11
        start_year = today.year + (start_month_num - 1) // 12
        start_month_num = (start_month_num - 1) % 12 + 1
        if start_month_num <= 0:
            start_month_num += 12
            start_year -= 1
        start_month = f"{start_year}/{start_month_num:02d}"
        end_month = f"{today.year}/{today.month:02d}"

    month_filter = "CONCAT(YEAR(audit_date), '/', LPAD(MONTH(audit_date), 2, '0'))"

    conditions = ["category IS NOT NULL AND category != ''", f"{month_filter} >= :start_month", f"{month_filter} <= :end_month"]
    params = {"start_month": start_month, "end_month": end_month}
    if region:
        conditions.append("region = :region")
        params["region"] = region
    if allowed_regions:
        conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

    where = " AND ".join(conditions)
    # 按月分组查询
    month_expr = "DATE_FORMAT(audit_date, '%Y/%m')"
    sql = text(f"""
        SELECT {month_expr} AS ym, category,
               SUM(tax_included_amount) as amount, COUNT(DISTINCT material_code) as sku_count
        FROM rpt_sales_out_wide WHERE {where}
        GROUP BY {month_expr}, category
        ORDER BY ym, amount DESC
    """)
    rows = db.execute(sql, params).fetchall()

    # 转换为透视表格式：{ months: [], categories: { categoryName: [values by month] } }
    month_set = set()
    cat_data = {}
    cat_totals = {}
    for row in rows:
        ym, cat, amt, sku = row
        ym_str = ym.decode() if isinstance(ym, bytes) else str(ym)
        cat_str = cat.decode() if isinstance(cat, bytes) else str(cat) if cat else ''
        month_set.add(ym_str)
        if cat_str not in cat_data:
            cat_data[cat_str] = {}
            cat_totals[cat_str] = 0
        cat_data[cat_str][ym_str] = float(amt or 0)
        cat_totals[cat_str] += float(amt or 0)

    months = sorted(month_set)
    # 按总金额降序排列品类
    sorted_cats = sorted(cat_totals.keys(), key=lambda x: cat_totals[x], reverse=True)

    # 构建透视数据
    categories = {}
    for cat in sorted_cats:
        categories[cat] = [cat_data[cat].get(m, 0) for m in months]

    total = sum(cat_totals.values())
    return {
        "months": months,
        "categories": categories,
        "items": [{"category": cat, "amount": cat_totals[cat], "sku_count": len(set(d.get(ym, 0) for d in [cat_data[cat]]))} for cat in sorted_cats]
    }


# ===================== TOP30 / 明星产品 =====================
def get_top_products_simple(db: Session, limit: int = 30, start_month: str = None, end_month: str = None,
                      allowed_regions: Optional[List[str]] = None) -> Dict:
    """获取销售 TOP N 产品"""
    if not start_month:
        today = datetime.now()
        start_month = f"{today.year}/01"
        end_month = f"{today.year}/{today.month:02d}"

    # 使用 CONCAT(YEAR, LPAD) 方式过滤月份
    month_filter = "CONCAT(YEAR(audit_date), '/', LPAD(MONTH(audit_date), 2, '0'))"

    conditions = ["material_code IS NOT NULL", f"{month_filter} >= :start_month", f"{month_filter} <= :end_month"]
    params = {"start_month": start_month, "end_month": end_month, "limit": limit}
    if allowed_regions:
        conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

    where = " AND ".join(conditions)
    sql = text(f"""
        SELECT material_code, material_name, brand, category,
               SUM(tax_included_amount) as total_amount,
               SUM(sales_out_qty) as total_qty
        FROM rpt_sales_out_wide WHERE {where}
        GROUP BY material_code, material_name, brand, category
        ORDER BY total_amount DESC LIMIT :limit
    """)
    rows = db.execute(sql, params).fetchall()
    items = [{
        "rank": i + 1, "material_code": r[0], "material_name": r[1],
        "brand": r[2], "category": r[3],
        "total_amount": float(r[4] or 0), "total_qty": float(r[5] or 0),
    } for i, r in enumerate(rows)]
    return {"items": items, "total_count": len(items)}


# ===================== 主推品渗透分析 =====================
def get_promoted_penetration(db: Session, start_month: str = None, end_month: str = None,
                              allowed_regions: Optional[List[str]] = None, region: Optional[str] = None) -> Dict:
    """按 promoted_flag 分析主推品渗透率（按月分组）"""
    if not start_month:
        today = datetime.now()
        start_month_num = today.month - 11
        start_year = today.year + (start_month_num - 1) // 12
        start_month_num = (start_month_num - 1) % 12 + 1
        if start_month_num <= 0:
            start_month_num += 12
            start_year -= 1
        start_month = f"{start_year}/{start_month_num:02d}"
        end_month = f"{today.year}/{today.month:02d}"

    month_filter = "CONCAT(YEAR(audit_date), '/', LPAD(MONTH(audit_date), 2, '0'))"

    conditions = [f"{month_filter} >= :start_month", f"{month_filter} <= :end_month"]
    params = {"start_month": start_month, "end_month": end_month}
    if region:
        conditions.append("region = :region")
        params["region"] = region
    if allowed_regions:
        conditions.append(f"region IN {_in_clause('ar', allowed_regions, params)}")

    where = " AND ".join(conditions) if conditions else "1=1"
    month_expr = "DATE_FORMAT(audit_date, '%Y/%m')"

    # 按月分组查询金额
    sql_amount = text(f"""
        SELECT {month_expr} AS ym,
               COALESCE(promoted_flag, '未标记') as flag,
               SUM(tax_included_amount) as amount
        FROM rpt_sales_out_wide WHERE {where}
        GROUP BY {month_expr}, COALESCE(promoted_flag, '未标记')
        ORDER BY ym, amount DESC
    """)
    rows_amount = db.execute(sql_amount, params).fetchall()

    # 按月×promoted_flag去重统计customer数
    sql_customer = text(f"""
        SELECT {month_expr} AS ym,
               COALESCE(promoted_flag, '未标记') as flag,
               customer
        FROM rpt_sales_out_wide WHERE {where}
        GROUP BY {month_expr}, COALESCE(promoted_flag, '未标记'), customer
    """)
    rows_customer = db.execute(sql_customer, params).fetchall()

    # 构建透视数据
    month_set = set()
    flag_amounts = {}  # { flag: { month: amount } }
    flag_customers = {}  # { flag: { month: customer_set } }

    def to_str(val):
        return val.decode() if isinstance(val, bytes) else str(val) if val else ''

    def get_category(flag):
        """根据promoted_flag返回简化分组"""
        if '下午茶' in flag:
            return '下午茶系列'
        elif '小狗' in flag:
            return '小狗系列'
        else:
            return '其他'

    for row in rows_amount:
        ym, flag, amt = row
        ym_str = to_str(ym)
        flag_str = to_str(flag)
        cat = get_category(flag_str)
        month_set.add(ym_str)
        if cat not in flag_amounts:
            flag_amounts[cat] = {}
        flag_amounts[cat][ym_str] = flag_amounts[cat].get(ym_str, 0) + float(amt or 0)

    for row in rows_customer:
        ym, flag, cust = row
        ym_str = to_str(ym)
        flag_str = to_str(flag)
        cust_str = to_str(cust)
        cat = get_category(flag_str)
        month_set.add(ym_str)
        if cat not in flag_customers:
            flag_customers[cat] = {}
        if ym_str not in flag_customers[cat]:
            flag_customers[cat][ym_str] = set()
        flag_customers[cat][ym_str].add(cust_str)

    months = sorted(month_set)
    # 按总金额降序排列
    flag_totals = {f: sum(flag_amounts.get(f, {}).values()) for f in flag_amounts}
    sorted_flags = sorted(flag_totals.keys(), key=lambda x: flag_totals[x], reverse=True)

    # 构建透视数据
    amounts_by_flag = {}
    customers_by_flag = {}
    for f in sorted_flags:
        amounts_by_flag[f] = [flag_amounts.get(f, {}).get(m, 0) for m in months]
        customers_by_flag[f] = [len(flag_customers.get(f, {}).get(m, set())) for m in months]

    # 计算各月总customer数
    total_customers_by_month = []
    for i, m in enumerate(months):
        total = 0
        for f in sorted_flags:
            total += customers_by_flag[f][i]
        total_customers_by_month.append(total)

    # 计算渗透率
    penetration_by_flag = {}
    for f in sorted_flags:
        penetration_by_flag[f] = []
        for i in range(len(months)):
            if total_customers_by_month[i] > 0:
                pct = customers_by_flag[f][i] / total_customers_by_month[i] * 100
                penetration_by_flag[f].append(round(pct, 1))
            else:
                penetration_by_flag[f].append(0)

    return {
        "months": months,
        "amounts": amounts_by_flag,
        "customers": customers_by_flag,
        "penetration": penetration_by_flag,
        "items": [{
            "flag": f,
            "amount": flag_totals[f],
            "customer_count": sum(customers_by_flag[f]),
            "penetration": round(sum(penetration_by_flag[f]) / len(months), 1) if months else 0
        } for f in sorted_flags]
    }
