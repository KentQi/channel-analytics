"""
返单分析服务
提供客户留存、商品生命周期、流失预警等复购分析功能
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ===================== 客户留存热力图数据 =====================
def get_cohort_matrix(
    db: Session,
    months: int = 12,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    customer: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取客户留存热力图数据

    Args:
        db: Database session
        months: 追溯月数
        region: 大区
        manager: 客户经理
        customer: 客户名称关键词
        allowed_regions: 用户允许访问的大区列表

    Returns:
        包含留存矩阵和客户统计的字典
    """
    try:
        # 构建WHERE条件
        # 口径：与 rpt_sales_out_wide 一致（含退货），保证累计金额/单数对得上销售宽表
        conditions = ["doc_date IS NOT NULL"]
        params = {}

        # 添加用户权限过滤
        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if customer:
            conditions.append("customer LIKE :customer")
            params["customer"] = f"%{customer}%"

        where_sql = " AND ".join(conditions)

        # 查询月度销售数据
        sql = text("""
            SELECT customer, material_code, material_name,
                   DATE_FORMAT(doc_date, '%Y%m') AS sale_month,
                   SUM(tax_included_amount) AS monthly_amount,
                   SUM(sales_out_qty) AS monthly_qty,
                   COUNT(DISTINCT doc_no) AS order_count
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            GROUP BY customer, material_code, material_name, DATE_FORMAT(doc_date, '%Y%m')
            ORDER BY customer, material_code, sale_month
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"cohort_matrix": [], "customer_stats": [], "metrics": {}}

        # 查询客户首次/最后进货期间
        sql_dates = text("""
            SELECT customer,
                   DATE_FORMAT(MIN(doc_date), '%Y%m%d') AS first_period,
                   DATE_FORMAT(MAX(doc_date), '%Y%m%d') AS last_period
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            GROUP BY customer
        """)
        df_dates = pd.read_sql(sql_dates, db.bind, params=params)
        df = df.merge(df_dates, on="customer", how="left")

        # 查询客户进货日期（用于计算间隔）
        sql_purchase = text("""
            SELECT DISTINCT customer, doc_date
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            ORDER BY customer, doc_date
        """)
        df_purchase = pd.read_sql(sql_purchase, db.bind, params=params)

        # 计算首次月份
        first_month = df.groupby("material_code")["sale_month"].min().reset_index()
        first_month.columns = ["material_code", "first_month"]
        df = df.merge(first_month, on="material_code", how="left")

        # 计算月份偏移
        df["first_year"] = df["first_month"].str[:4].astype(int)
        df["first_month_idx"] = df["first_month"].str[4:6].astype(int)
        df["sale_year"] = df["sale_month"].str[:4].astype(int)
        df["sale_month_idx"] = df["sale_month"].str[4:6].astype(int)
        df["month_offset"] = (df["sale_year"] - df["first_year"]) * 12 + (df["sale_month_idx"] - df["first_month_idx"])

        # 过滤有效范围
        df = df[df["month_offset"] >= 0]
        df = df[df["month_offset"] <= months]

        # 构建客户统计
        customer_month_count = df.groupby("customer")["month_offset"].nunique().reset_index()
        customer_month_count.columns = ["customer", "purchase_months"]

        customer_dates = df.groupby("customer").agg(
            first_period=("first_period", "first"),
            last_period=("last_period", "first")
        ).reset_index()

        # 计算进货间隔
        df_sorted = df_purchase.copy()
        df_sorted["doc_date"] = pd.to_datetime(df_sorted["doc_date"])
        df_sorted = df_sorted.sort_values(["customer", "doc_date"])
        df_sorted["prev_date"] = df_sorted.groupby("customer")["doc_date"].shift(1)
        df_sorted["interval_days"] = (df_sorted["doc_date"] - df_sorted["prev_date"]).dt.days

        max_intervals = df_sorted.groupby("customer")["interval_days"].max().reset_index()
        max_intervals.columns = ["customer", "max_interval_days"]
        max_intervals["max_interval_days"] = max_intervals["max_interval_days"].fillna(0).astype(int)

        sum_intervals = df_sorted.groupby("customer")["interval_days"].sum().reset_index()
        sum_intervals.columns = ["customer", "sum_interval_days"]
        sum_intervals["sum_interval_days"] = sum_intervals["sum_interval_days"].fillna(0).astype(int)

        purchase_counts = df_purchase.groupby("customer").size().reset_index(name="purchase_count")
        purchase_counts.columns = ["customer", "purchase_count"]

        # 客户汇总统计
        customer_stats = df.groupby("customer").agg(
            first_month=("first_month", "first"),
            total_amount=("monthly_amount", "sum"),
            total_orders=("order_count", "sum"),
            max_offset=("month_offset", "max")
        ).reset_index()

        customer_stats = customer_stats.merge(customer_month_count, on="customer", how="left")
        customer_stats = customer_stats.merge(customer_dates, on="customer", how="left")
        customer_stats = customer_stats.merge(max_intervals, on="customer", how="left")
        customer_stats = customer_stats.merge(sum_intervals, on="customer", how="left")
        customer_stats = customer_stats.merge(purchase_counts, on="customer", how="left")

        customer_stats["max_interval_days"] = customer_stats["max_interval_days"].fillna(0).astype(int)
        customer_stats["sum_interval_days"] = customer_stats["sum_interval_days"].fillna(0).astype(int)
        customer_stats["purchase_count"] = customer_stats["purchase_count"].fillna(0).astype(int)
        customer_stats["repurchase_count"] = (customer_stats["purchase_count"] - 1).clip(lower=0)
        customer_stats["avg_interval_days"] = np.where(
            customer_stats["repurchase_count"] > 0,
            customer_stats["sum_interval_days"] / customer_stats["repurchase_count"],
            0.0
        )

        # 判断60天内是否有进货
        today = datetime.today()
        customer_stats["last_period"] = pd.to_datetime(customer_stats["last_period"], format="%Y%m%d", errors="coerce")
        customer_stats["active_60d"] = ((today - customer_stats["last_period"]).dt.days <= 60).map({True: "是", False: "否"})

        # 构建留存矩阵
        pivot = df.pivot_table(
            index="first_month", columns="month_offset", values="customer", aggfunc="nunique", fill_value=0
        )
        cohort_size = df.groupby("first_month")["customer"].nunique()
        retention_matrix = pivot.div(cohort_size, axis=0) * 100

        # 格式化留存矩阵
        cohort_data = []
        for idx in retention_matrix.index:
            row = {"first_month": str(idx)}
            for col in retention_matrix.columns:
                val = retention_matrix.loc[idx, col]
                col_name = "首月" if col == 0 else f"+{int(col)}月"
                row[col_name] = round(val, 1) if pd.notna(val) and val > 0 else 0
            cohort_data.append(row)

        # 格式化客户统计
        customer_list = []
        for _, row in customer_stats.iterrows():
            first_period = row.get("first_period")
            last_period = row.get("last_period")
            # 确保日期格式为 YYYYMMDD（截取前8位）
            if first_period and pd.notna(first_period):
                first_period = str(first_period)[:8]
            else:
                first_period = ""
            if last_period and pd.notna(last_period):
                if isinstance(last_period, (pd.Timestamp, datetime)):
                    last_period = last_period.strftime("%Y%m%d")
                else:
                    last_period = str(last_period)[:8]
            else:
                last_period = ""
            customer_list.append({
                "customer": row["customer"],
                "first_month": first_period,
                "last_period": last_period,
                "total_amount": float(row["total_amount"]),
                "total_orders": int(row["total_orders"]),
                "max_interval_days": int(row["max_interval_days"]),
                "avg_interval_days": round(float(row["avg_interval_days"]), 1),
                "purchase_count": int(row["purchase_count"]),
                "active_60d": row["active_60d"],
            })

        # 计算核心指标
        total_customers = len(customer_stats)
        active_customers = len(customer_stats[customer_stats["active_60d"] == "是"])

        # 计算留存率：首月在追溯周期内（前N个月）的客户，在最后1个月返单的比例
        max_offset = df["month_offset"].max()
        first_period_threshold = max_offset - 11 if max_offset > 11 else 0  # 前12个月的首月客户

        # 首月在统计范围内的客户
        first_month_customers = df[df["month_offset"] <= first_period_threshold]["customer"].unique()
        # 这些客户中，在最后1个月有返单的
        last_month_repurchase = df[(df["month_offset"] == max_offset) & (df["customer"].isin(first_month_customers))]["customer"].nunique()

        repurchase_rate = (last_month_repurchase / len(first_month_customers) * 100) if len(first_month_customers) > 0 else 0

        metrics = {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "inactive_customers": total_customers - active_customers,
            "retention_rate": f"{repurchase_rate:.1f}%",
        }

        return {
            "cohort_matrix": cohort_data,
            "customer_stats": customer_list,
            "metrics": metrics,
        }
    except Exception as e:
        logger.error(f"获取留存热力图失败: {e}")
        return {"cohort_matrix": [], "customer_stats": [], "metrics": {}, "error": "数据获取失败"}


# ===================== 单品客户 Cohort 矩阵 =====================
def get_product_customer_cohort(
    db: Session,
    material_code: str,
    months: int = 12,
    view_mode: str = 'offset',
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取指定物料的客户 Cohort 矩阵

    Args:
        db: Database session
        material_code: 物料编码
        months: 追溯月数
        view_mode: 视图模式，offset=偏移模式(首月/+1月)，absolute=动态日期模式
        category: 品类（可选，与物料编码联合限定；通常二者之一即可定位物料）

    Returns:
        客户商品 Cohort 矩阵数据
    """
    try:
        # 查询购买过该物料的所有客户数据
        sql = text("""
            SELECT customer, material_name, doc_date, sales_out_qty,
                   DATE_FORMAT(doc_date, '%Y%m') AS sale_month,
                   MIN(doc_date) OVER (PARTITION BY customer) AS first_order_date
            FROM rpt_sales_out_wide
            WHERE material_code = :material_code
            AND doc_date IS NOT NULL
            AND sales_out_qty > 0
            ORDER BY customer, doc_date
        """)
        df = pd.read_sql(sql, db.bind, params={"material_code": material_code})

        if df.empty:
            return {"cohort_data": [], "month_columns": [], "material_code": material_code, "material_name": "", "summary": None}

        # 品类过滤：如果传了 category，从 dim_product_attr 校验并应用
        if category:
            sql_cat = text("SELECT category FROM dim_product_attr WHERE material_code = :material_code")
            row = db.execute(sql_cat, {"material_code": material_code}).fetchone()
            material_category = row[0] if row else None
            if material_category != category:
                return {
                    "cohort_data": [],
                    "month_columns": [],
                    "material_code": material_code,
                    "material_name": "",
                    "summary": None,
                }

        # ---------- 商品摘要统计 ----------
        from datetime import datetime, timedelta
        today = datetime.today().date()

        sql_summary = text("""
            SELECT customer, doc_date, tax_included_amount
            FROM rpt_sales_out_wide
            WHERE material_code = :material_code AND doc_date IS NOT NULL
        """)
        df_summary = pd.read_sql(sql_summary, db.bind, params={"material_code": material_code})

        summary = None
        if not df_summary.empty:
            df_summary["doc_date"] = pd.to_datetime(df_summary["doc_date"]).dt.date
            first_date = df_summary["doc_date"].min()
            days_since_first = (today - first_date).days
            total_customers = df_summary["customer"].nunique()
            total_amount = round(df_summary["tax_included_amount"].sum(), 2)

            # 开始3个月内进货
            first_90d_end = first_date + timedelta(days=90)
            df_first_90d = df_summary[
                (df_summary["doc_date"] >= first_date) & (df_summary["doc_date"] <= first_90d_end)
            ]
            customers_first_3m = df_first_90d["customer"].nunique()
            amount_first_3m = round(df_first_90d["tax_included_amount"].sum(), 2)

            # 最近3个月内进货
            last_90d_start = today - timedelta(days=90)
            df_last_90d = df_summary[df_summary["doc_date"] >= last_90d_start]
            customers_last_3m = df_last_90d["customer"].nunique()
            amount_last_3m = round(df_last_90d["tax_included_amount"].sum(), 2)

            summary = {
                "days_since_first": days_since_first,
                "total_customers": total_customers,
                "total_amount": total_amount,
                "customers_first_3m": customers_first_3m,
                "amount_first_3m": amount_first_3m,
                "customers_last_3m": customers_last_3m,
                "amount_last_3m": amount_last_3m,
            }

        # 获取物料名称（所有记录相同）
        material_name = df["material_name"].iloc[0]

        # 获取每个客户首次购买该物料的月份
        first_purchase = df.groupby("customer")["sale_month"].min().reset_index()
        first_purchase.columns = ["customer", "first_month"]

        # 合并首次购买信息
        df = df.merge(first_purchase, on="customer", how="left")

        # 计算月份偏移（相对于首次购买该物料）
        df["first_year"] = df["first_month"].str[:4].astype(int)
        df["first_month_idx"] = df["first_month"].str[4:6].astype(int)
        df["sale_year"] = df["sale_month"].str[:4].astype(int)
        df["sale_month_idx"] = df["sale_month"].str[4:6].astype(int)
        df["month_offset"] = (df["sale_year"] - df["first_year"]) * 12 + (df["sale_month_idx"] - df["first_month_idx"])

        # 过滤有效范围
        df = df[df["month_offset"] >= 0]
        df = df[df["month_offset"] <= months]

        # 构建客户统计
        customer_stats = df.groupby("customer").agg(
            first_month=("first_month", "first"),
            first_order_date=("first_order_date", "first"),
            total_qty=("sales_out_qty", "sum")
        ).reset_index()

        # 按首次购买月份排序
        customer_stats = customer_stats.sort_values("first_month", ascending=False)

        # 构建月份偏移矩阵（每个客户在各月的销量）
        pivot = df.pivot_table(
            index="customer", columns="month_offset", values="sales_out_qty", aggfunc="sum", fill_value=0
        )

        # 计算最大偏移月
        max_offset = int(df["month_offset"].max()) if not df.empty else 0

        if view_mode == 'absolute':
            # 动态日期模式：以所有客户中最早的首月作为基准
            from datetime import datetime

            # 找到最早的首月
            if 'first_month' in customer_stats.columns and not customer_stats.empty:
                valid_first_months = customer_stats['first_month'].dropna()
                if len(valid_first_months) > 0:
                    earliest_month = valid_first_months.min()
                    first_y = int(str(earliest_month)[:4])
                    first_m = int(str(earliest_month)[4:6])
                else:
                    first_y = datetime.now().year
                    first_m = datetime.now().month
            else:
                first_y = datetime.now().year
                first_m = datetime.now().month

            # 生成从最早首月开始的 months 个月份（YYYYMM格式用于匹配）
            absolute_months = []
            absolute_months_label = []
            for i in range(months):
                total_months = first_y * 12 + first_m - 1 + i
                year = total_months // 12
                month = total_months % 12 + 1
                absolute_months.append(f"{year}{month:02d}")  # YYYYMM格式用于匹配
                absolute_months_label.append(f"{year}-{month:02d}")  # YYYY-MM格式用于显示

            # 构建 sales_map（按实际月份索引，用于动态日期模式直接匹配）
            sales_map = df.pivot_table(
                index="customer", columns="sale_month", values="sales_out_qty", aggfunc="sum", fill_value=0
            )

            month_columns = absolute_months_label
        else:
            # 偏移模式：首月/+1月/+2月...
            all_offsets = list(range(0, max_offset + 1))
            month_columns = ["首月" if col == 0 else f"+{col}月" for col in all_offsets]

        # 构建返回数据
        cohort_data = []
        for _, row in customer_stats.iterrows():
            cust = row["customer"]
            first_order = str(row["first_order_date"])[:10] if pd.notna(row["first_order_date"]) else ""
            first_month = str(row["first_month"]) if pd.notna(row["first_month"]) else ""
            row_data = {
                "customer": cust,
                "first_order_date": first_order,
                "first_month": first_month,
                "total_qty": int(row["total_qty"]) if pd.notna(row.get("total_qty")) else 0,
            }

            if view_mode == 'absolute':
                # 动态日期模式：数据按实际月份对齐
                # 使用 absolute_months_label (YYYY-MM格式) 作为 key，与 month_columns 一致
                for i, col in enumerate(absolute_months):  # col 是 YYYYMM 格式
                    col_label = absolute_months_label[i]  # YYYY-MM 格式，用于前端显示
                    if cust in sales_map.index and col in sales_map.columns:
                        value = int(sales_map.loc[cust, col])
                        row_data[col_label] = value if value > 0 else None
                    else:
                        row_data[col_label] = None
            else:
                # 偏移模式：首月/+1月/+2月...
                all_offsets = list(range(0, max_offset + 1))
                for col in all_offsets:
                    col_name = "首月" if col == 0 else f"+{col}月"
                    if col in pivot.columns and cust in pivot.index:
                        row_data[col_name] = int(pivot.loc[cust, col])
                    else:
                        row_data[col_name] = 0
            cohort_data.append(row_data)

        return {
            "cohort_data": cohort_data,
            "month_columns": month_columns,
            "material_code": material_code,
            "material_name": material_name,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取单品客户Cohort矩阵失败: {e}")
        return {"cohort_data": [], "month_columns": [], "error": "数据获取失败"}


# ===================== 客户价值散点图数据 =====================
def get_customer_value_scatter(
    db: Session,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    customer: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取客户价值散点图数据

    Args:
        db: Database session
        region: 大区
        manager: 客户经理
        customer: 客户名称关键词
        allowed_regions: 用户允许访问的大区列表

    Returns:
        包含散点图数据的字典
    """
    try:
        # 构建WHERE条件
        # 口径：与 rpt_sales_out_wide 一致（含退货），保证累计金额/单数对得上销售宽表
        conditions = ["doc_date IS NOT NULL"]
        params = {}

        # 添加用户权限过滤
        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if customer:
            conditions.append("customer LIKE :customer")
            params["customer"] = f"%{customer}%"

        where_sql = " AND ".join(conditions)

        # 查询客户汇总数据
        sql = text("""
            SELECT customer,
                   SUM(tax_included_amount) AS total_amount,
                   COUNT(DISTINCT doc_no) AS order_count
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            GROUP BY customer
        """)
        result = db.execute(sql, params)
        rows = result.fetchall()

        # 查询60天内是否有进货
        today = datetime.today()
        cutoff_date = (today - timedelta(days=60)).strftime("%Y-%m-%d")

        active_sql = text("""
            SELECT DISTINCT customer
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """ AND doc_date >= :cutoff_date
        """)
        active_params = {**params, "cutoff_date": cutoff_date}
        active_result = db.execute(active_sql, active_params)
        active_customers = {row[0] for row in active_result.fetchall()}

        # 格式化数据
        scatter_data = []
        for row in rows:
            customer = row[0]
            total_amount = float(row[1]) if row[1] else 0
            order_count = int(row[2]) if row[2] else 0
            active_60d = "是" if customer in active_customers else "否"

            scatter_data.append({
                "customer": customer,
                "total_amount": total_amount,
                "order_count": order_count,
                "active_60d": active_60d,
            })

        return {"scatter_data": scatter_data}
    except Exception as e:
        logger.error(f"获取客户价值散点图失败: {e}")
        return {"scatter_data": [], "error": "数据获取失败"}


# ===================== 流失预警客户列表 =====================
def get_churn_warning(
    db: Session,
    days: int = 90,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    customer: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取流失预警客户列表

    Args:
        db: Database session
        days: 流失阈值天数
        region: 大区
        manager: 客户经理
        customer: 客户名称关键词
        allowed_regions: 用户允许访问的大区列表

    Returns:
        流失预警客户列表
    """
    try:
        # 构建WHERE条件
        # 口径：与 rpt_sales_out_wide 一致（含退货），保证累计金额/单数对得上销售宽表
        conditions = ["doc_date IS NOT NULL"]
        params = {}

        # 添加用户权限过滤
        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if customer:
            conditions.append("customer LIKE :customer")
            params["customer"] = f"%{customer}%"

        where_sql = " AND ".join(conditions)

        # 查询客户汇总数据
        sql = text("""
            SELECT customer,
                   DATE_FORMAT(MIN(doc_date), '%Y%m') AS first_month,
                   DATE_FORMAT(MAX(doc_date), '%Y%m%d') AS last_period,
                   SUM(tax_included_amount) AS total_amount,
                   COUNT(DISTINCT doc_no) AS order_count
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            GROUP BY customer
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"churn_customers": [], "summary": {}}

        # 查询客户进货日期用于计算间隔
        sql_purchase = text("""
            SELECT DISTINCT customer, doc_date
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            ORDER BY customer, doc_date
        """)
        df_purchase = pd.read_sql(sql_purchase, db.bind, params=params)

        # 计算最大进货间隔
        df_sorted = df_purchase.copy()
        df_sorted["doc_date"] = pd.to_datetime(df_sorted["doc_date"])
        df_sorted = df_sorted.sort_values(["customer", "doc_date"])
        df_sorted["prev_date"] = df_sorted.groupby("customer")["doc_date"].shift(1)
        df_sorted["interval_days"] = (df_sorted["doc_date"] - df_sorted["prev_date"]).dt.days

        max_intervals = df_sorted.groupby("customer")["interval_days"].max().reset_index()
        max_intervals.columns = ["customer", "max_interval_days"]
        max_intervals["max_interval_days"] = max_intervals["max_interval_days"].fillna(0).astype(int)

        df = df.merge(max_intervals, on="customer", how="left")
        df["max_interval_days"] = df["max_interval_days"].fillna(0).astype(int)

        # 判断60天内是否有进货
        today = datetime.today()
        cutoff_date = today - timedelta(days=60)
        df["last_period_dt"] = pd.to_datetime(df["last_period"], format="%Y%m%d", errors="coerce")
        df["active_60d"] = (df["last_period_dt"] >= cutoff_date).map({True: "是", False: "否"})

        # 筛选流失客户
        churn_df = df[(df["max_interval_days"] >= days) & (df["active_60d"] == "否")]
        churn_df = churn_df.nlargest(20, "max_interval_days")

        churn_customers = []
        for _, row in churn_df.iterrows():
            first_month_str = str(row["first_month"]) if pd.notna(row["first_month"]) else ""
            first_formatted = f"{first_month_str[:4]}-{first_month_str[4:6]}" if len(first_month_str) >= 6 else first_month_str
            last_formatted = row["last_period_dt"].strftime("%Y-%m-%d") if pd.notna(row["last_period_dt"]) else ""

            churn_customers.append({
                "customer": row["customer"],
                "first_month": first_formatted,
                "last_period": last_formatted,
                "total_amount": float(row["total_amount"]),
                "order_count": int(row["order_count"]),
                "max_interval_days": int(row["max_interval_days"]),
            })

        summary = {
            "total_churn_customers": len(churn_df),
            "threshold_days": days,
        }

        return {
            "churn_customers": churn_customers,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取流失预警失败: {e}")
        return {"churn_customers": [], "summary": {}, "error": "数据获取失败"}


# ===================== 新客户返单监控 =====================
def get_new_customer_repurchase(
    db: Session,
    days: int = 90,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    customer: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取新客户返单监控数据

    Args:
        db: Database session
        days: 新客户定义天数
        region: 大区
        manager: 客户经理
        customer: 客户名称关键词
        allowed_regions: 用户允许访问的大区列表

    Returns:
        新客户返单监控数据
    """
    try:
        # 构建WHERE条件
        # 口径：与 rpt_sales_out_wide 一致（含退货），保证累计金额/单数对得上销售宽表
        conditions = ["doc_date IS NOT NULL"]
        params = {}

        # 添加用户权限过滤
        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("region = :region")
            params["region"] = region
        if manager:
            conditions.append("account_manager = :manager")
            params["manager"] = manager
        if customer:
            conditions.append("customer LIKE :customer")
            params["customer"] = f"%{customer}%"

        where_sql = " AND ".join(conditions)

        # 多加载2个月数据，确保能覆盖首单后8周
        min_date = (datetime.today() - timedelta(days=days * 30 + 60)).strftime("%Y-%m-%d")

        # 查询客户日维度销售数据
        sql = text("""
            SELECT customer, doc_date, SUM(sales_out_qty) AS daily_qty
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """ AND doc_date >= :min_date
            GROUP BY customer, doc_date
            ORDER BY customer, doc_date
        """)
        df = pd.read_sql(sql, db.bind, params={**params, "min_date": min_date})

        if df.empty:
            return {"weekly_data": [], "summary": {}}

        # 计算每个客户的首次订单日期
        customer_first = df.groupby("customer")["doc_date"].min().reset_index()
        customer_first.columns = ["customer", "first_order_date"]

        # 计算有效首单日期（超过365天无订单则重新计算）
        def get_effective_first(dates: list, reset_days: int = 365) -> datetime:
            if not dates:
                return None
            sorted_dates = sorted(set(dates))
            if len(sorted_dates) == 1:
                return sorted_dates[0]
            effective = sorted_dates[0]
            for i in range(1, len(sorted_dates)):
                gap = (sorted_dates[i] - sorted_dates[i - 1]).days
                if gap > reset_days:
                    effective = sorted_dates[i]
            return effective

        # 获取每个客户的有效首单日期
        customer_dates = df.groupby("customer")["doc_date"].apply(
            lambda x: [d for d in x.dropna().unique()]
        ).to_dict()

        effective_first = {}
        for cust, dates in customer_dates.items():
            ef = get_effective_first(dates, reset_days=365)
            if ef:
                effective_first[cust] = ef

        # 只保留新客户（首单在days天内）
        today = datetime.today().date()
        new_customers = {
            cust: ef for cust, ef in effective_first.items()
            if (today - ef.date()).days <= days
        }

        if not new_customers:
            return {"weekly_data": [], "summary": {"message": f"暂无符合条件的新客户（首单后{days}天内）"}}

        # 构建有效首单DataFrame
        first_order_df = pd.DataFrame([
            {"customer": cust, "first_order_date": ef} for cust, ef in new_customers.items()
        ])

        # 合并首单日期并计算周偏移
        df = df.merge(first_order_df, on="customer", how="inner")
        df["doc_date"] = pd.to_datetime(df["doc_date"])
        df["first_order_date"] = pd.to_datetime(df["first_order_date"])
        df["days_diff"] = (df["doc_date"] - df["first_order_date"]).dt.days
        df["week_offset"] = (df["days_diff"] // 7) + 1

        # 只保留第1-8周的数据
        df = df[(df["week_offset"] >= 1) & (df["week_offset"] <= 8)]

        if df.empty:
            return {"weekly_data": [], "summary": {"message": "暂无新客户返单数据"}}

        # 按客户和周偏移汇总销量
        weekly = df.groupby(["customer", "week_offset"])["daily_qty"].sum().reset_index()
        pivot = weekly.pivot(index="customer", columns="week_offset", values="daily_qty").fillna(0)

        # 确保有1-8周的列
        for w in range(1, 9):
            if w not in pivot.columns:
                pivot[w] = 0
        pivot = pivot[[w for w in range(1, 9)]]

        # 构建显示数据
        first_order_fmt = first_order_df.set_index("customer")["first_order_date"]
        first_order_fmt = pd.to_datetime(first_order_fmt).dt.strftime("%Y-%m-%d")

        weekly_data = []
        for customer in pivot.index:
            row_data = {
                "customer": customer,
                "first_order_date": first_order_fmt.get(customer, ""),
            }
            for w in range(1, 9):
                row_data[f"week_{w}"] = int(pivot.loc[customer, w]) if customer in pivot.index else 0
            weekly_data.append(row_data)

        summary = {
            "new_customer_count": len(new_customers),
            "definition_days": days,
            "reset_days": 365,
        }

        return {
            "weekly_data": weekly_data,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取新客户返单监控失败: {e}")
        return {"weekly_data": [], "summary": {}, "error": "数据获取失败"}


# ===================== 商品生命周期表 =====================
def get_product_lifecycle(
    db: Session,
    months: int = 18,
    region: Optional[str] = None,
    abc_class: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取商品生命周期表

    Args:
        db: Database session
        months: 追溯月数
        region: 大区
        abc_class: ABC分类
        lifecycle_status: 生命周期
        product_name: 物料名称
        category: 品类
        allowed_regions: 用户允许访问的大区列表

    Returns:
        商品生命周期表数据
    """
    try:
        # 构建WHERE条件（商品维度过滤下推到主SQL，通过 JOIN dim_product_attr 实现）
        conditions = ["rpt.doc_date IS NOT NULL", "rpt.sales_out_qty > 0"]
        params = {}

        # 用户权限过滤
        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"rpt.region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("rpt.region = :region")
            params["region"] = region

        # 商品属性下推到 SQL（关键优化：避免拉全量再过滤）
        if category:
            conditions.append("dpa.category = :category")
            params["category"] = category
        if abc_class:
            conditions.append("dpa.abc_class = :abc_class")
            params["abc_class"] = abc_class
        if lifecycle_status:
            conditions.append("dpa.lifecycle_status = :lifecycle_status")
            params["lifecycle_status"] = lifecycle_status
        if product_name:
            conditions.append("rpt.material_name LIKE :product_name")
            params["product_name"] = f"%{product_name}%"

        where_sql = " AND ".join(conditions)

        # 查询商品月度销售数据（INNER JOIN 缩窄到符合品类/ABC/生命周期的物料）
        sql = text("""
            SELECT rpt.material_code, rpt.material_name,
                   DATE_FORMAT(rpt.doc_date, '%Y%m') AS sale_month,
                   SUM(rpt.sales_out_qty) AS monthly_qty,
                   SUM(rpt.tax_included_amount) AS monthly_amount,
                   MAX(dpa.first_stock_in_date) AS first_stock_in_date,
                   MAX(dpa.abc_class) AS abc_class,
                   MAX(dpa.lifecycle_status) AS lifecycle_status
            FROM rpt_sales_out_wide rpt
            INNER JOIN dim_product_attr dpa ON rpt.material_code = dpa.material_code
            WHERE """ + where_sql + """
            GROUP BY rpt.material_code, rpt.material_name, DATE_FORMAT(rpt.doc_date, '%Y%m')
            ORDER BY rpt.material_code, sale_month
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"lifecycle_data": [], "summary": {}}

        # 首销时间
        sql_first = text("""
            SELECT material_code, MIN(doc_date) AS first_sale_date
            FROM rpt_sales_out_wide
            WHERE doc_date IS NOT NULL AND sales_out_qty > 0
            GROUP BY material_code
        """)
        df_first = pd.read_sql(sql_first, db.bind)
        df = df.merge(df_first, on="material_code", how="left")

        # 查询首销时间
        sql_first = text("""
            SELECT material_code, MIN(doc_date) AS first_sale_date
            FROM rpt_sales_out_wide
            WHERE doc_date IS NOT NULL AND sales_out_qty > 0
            GROUP BY material_code
        """)
        df_first = pd.read_sql(sql_first, db.bind)
        df = df.merge(df_first, on="material_code", how="left")

        # 计算首次月份和月份偏移
        first_month = df.groupby("material_code")["sale_month"].min().reset_index()
        first_month.columns = ["material_code", "first_month"]
        df = df.merge(first_month, on="material_code", how="left")

        df["first_year"] = df["first_month"].str[:4].astype(int)
        df["first_month_idx"] = df["first_month"].str[4:6].astype(int)
        df["sale_year"] = df["sale_month"].str[:4].astype(int)
        df["sale_month_idx"] = df["sale_month"].str[4:6].astype(int)
        df["month_offset"] = (df["sale_year"] - df["first_year"]) * 12 + (df["sale_month_idx"] - df["first_month_idx"])

        df = df[df["month_offset"] >= 0]
        df = df[df["month_offset"] <= months]

        # 商品级过滤已下推到主 SQL（见上方 WHERE 条件），此处无需再次过滤

        if df.empty:
            return {"lifecycle_data": [], "summary": {}}

        # 查询在库量
        mat_codes = df["material_code"].unique().tolist()
        if mat_codes:
            placeholders = ",".join([f":code{i}" for i in range(len(mat_codes))])
            stock_params = {f"code{i}": code for i, code in enumerate(mat_codes)}
            sql_stock = text(f"""
                SELECT material_code, SUM(current_stock) AS current_stock
                FROM stg_stock_current
                WHERE material_code IN ({placeholders}) AND current_stock > 0
                GROUP BY material_code
            """)
            df_stock = pd.read_sql(sql_stock, db.bind, params=stock_params)
            stock_map = dict(zip(df_stock["material_code"], df_stock["current_stock"]))
        else:
            stock_map = {}

        # 构建商品统计
        product_stats = df.groupby("material_code").agg(
            material_name=("material_name", "first"),
            first_month=("first_month", "first"),
            total_qty=("monthly_qty", "sum"),
            total_amount=("monthly_amount", "sum"),
            max_offset=("month_offset", "max"),
            first_stock_in_date=("first_stock_in_date", "first"),
            abc_class=("abc_class", "first"),
            lifecycle_status=("lifecycle_status", "first"),
            first_sale_date=("first_sale_date", "first"),
        ).reset_index()

        product_stats["current_stock"] = product_stats["material_code"].map(stock_map).fillna(0).astype(int)
        product_stats["has_repurchase"] = product_stats["max_offset"].apply(lambda x: "是" if x > 0 else "否")

        # 构建透视表
        pivot = df.pivot_table(
            index=["material_code", "material_name"], columns="month_offset", values="monthly_qty", aggfunc="sum", fill_value=0
        )

        # 合并元数据
        lifecycle_data = []
        for idx, row in pivot.iterrows():
            mat_code = idx[0] if isinstance(idx, tuple) else idx
            mat_name = idx[1] if isinstance(idx, tuple) and len(idx) > 1 else ""

            # 从product_stats获取元数据
            stats = product_stats[product_stats["material_code"] == mat_code]
            if stats.empty:
                continue
            stat = stats.iloc[0]

            row_data = {
                "material_code": mat_code,
                "material_name": mat_name,
                "lifecycle_status": stat.get("lifecycle_status", ""),
                "abc_class": stat.get("abc_class", ""),
                "first_stock_in_date": str(stat.get("first_stock_in_date", ""))[:10] if pd.notna(stat.get("first_stock_in_date")) else "",
                "first_sale_date": str(stat.get("first_sale_date", ""))[:10] if pd.notna(stat.get("first_sale_date")) else "",
                "current_stock": int(stat["current_stock"]),
                "total_qty": int(stat["total_qty"]),
                "total_amount": float(stat["total_amount"]),
            }

            # 添加月份销量
            for col in pivot.columns:
                col_name = "首月" if col == 0 else f"+{int(col)}月"
                row_data[col_name] = int(row[col]) if col in pivot.columns and pd.notna(row[col]) else 0

            lifecycle_data.append(row_data)

        # 按首批入库时间排序
        lifecycle_data.sort(key=lambda x: x.get("first_stock_in_date", ""), reverse=True)

        summary = {
            "total_products": len(lifecycle_data),
            "with_repurchase": len([d for d in lifecycle_data if d.get("has_repurchase") == "是"]),
        }

        # 确保所有数值中的 NaN 被替换为 None
        def clean_value(v):
            if isinstance(v, float) and (v != v):  # NaN check
                return None
            return v

        def clean_row(row):
            return {k: clean_value(v) for k, v in row.items()}

        lifecycle_data = [clean_row(row) for row in lifecycle_data]

        return {
            "lifecycle_data": lifecycle_data,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取商品生命周期表失败: {e}")
        return {"lifecycle_data": [], "summary": {}, "error": "数据获取失败"}


# ===================== 客户留存率表 =====================
def get_customer_retention_rate(
    db: Session,
    months: int = 18,
    region: Optional[str] = None,
    abc_class: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取客户留存率表

    Args:
        db: Database session
        months: 追溯月数
        region: 大区
        abc_class: ABC分类
        lifecycle_status: 生命周期
        product_name: 物料名称
        category: 品类
        allowed_regions: 用户允许访问的大区列表

    Returns:
        客户留存率表数据
    """
    try:
        # 构建WHERE条件（品类/ABC/生命周期/名称下推到主SQL）
        conditions = ["rpt.doc_date IS NOT NULL", "rpt.sales_out_qty > 0"]
        params = {}

        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"rpt.region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("rpt.region = :region")
            params["region"] = region

        if category:
            conditions.append("dpa.category = :category")
            params["category"] = category
        if abc_class:
            conditions.append("dpa.abc_class = :abc_class")
            params["abc_class"] = abc_class
        if lifecycle_status:
            conditions.append("dpa.lifecycle_status = :lifecycle_status")
            params["lifecycle_status"] = lifecycle_status
        if product_name:
            conditions.append("rpt.material_name LIKE :product_name")
            params["product_name"] = f"%{product_name}%"

        where_sql = " AND ".join(conditions)

        # 查询商品月度销售数据（INNER JOIN 缩窄物料）
        sql = text("""
            SELECT rpt.material_code, rpt.material_name, rpt.customer,
                   DATE_FORMAT(rpt.doc_date, '%Y%m') AS sale_month,
                   SUM(rpt.sales_out_qty) AS monthly_qty
            FROM rpt_sales_out_wide rpt
            INNER JOIN dim_product_attr dpa ON rpt.material_code = dpa.material_code
            WHERE """ + where_sql + """
            GROUP BY rpt.material_code, rpt.material_name, rpt.customer, DATE_FORMAT(rpt.doc_date, '%Y%m')
            ORDER BY rpt.material_code, rpt.customer, sale_month
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"retention_data": [], "summary": {}}

        # 查询商品属性（仅取符合筛选的物料子集，减少数据量）
        mat_codes_sub = df["material_code"].unique().tolist()
        if mat_codes_sub:
            placeholders = ",".join([f":mc{i}" for i in range(len(mat_codes_sub))])
            sql_goods = text(f"""
                SELECT material_code, first_stock_in_date, abc_class, lifecycle_status, category
                FROM dim_product_attr
                WHERE material_code IN ({placeholders})
            """)
            df_goods = pd.read_sql(sql_goods, db.bind, params={f"mc{i}": c for i, c in enumerate(mat_codes_sub)})
        else:
            df_goods = pd.DataFrame()
        meta_map = df_goods.set_index("material_code")[["first_stock_in_date", "abc_class", "lifecycle_status", "category"]].to_dict("index")

        mat_codes = df["material_code"].unique().tolist()

        # 计算有效最大月份偏移
        first_month_map = df.groupby("material_code")["sale_month"].min().to_dict()

        effective_max = 0
        for mat in mat_codes:
            mat_data = df[df["material_code"] == mat].copy()
            if mat_data.empty:
                continue
            first_m = first_month_map.get(mat, "")
            if not first_m:
                continue
            first_y, first_mo = int(first_m[:4]), int(first_m[4:6])
            mat_data["sale_year"] = mat_data["sale_month"].str[:4].astype(int)
            mat_data["sale_month_idx"] = mat_data["sale_month"].str[4:6].astype(int)
            mat_data["month_offset"] = (mat_data["sale_year"] - first_y) * 12 + (mat_data["sale_month_idx"] - first_mo)
            effective_max = max(effective_max, int(mat_data["month_offset"].max()))

        effective_max = min(effective_max, months)

        # 计算留存率
        results = []
        for mat in mat_codes:
            mat_data = df[df["material_code"] == mat].copy()
            if mat_data.empty:
                continue
            first_m = first_month_map.get(mat, "")
            if not first_m:
                continue
            first_y, first_mo = int(first_m[:4]), int(first_m[4:6])
            mat_data["sale_year"] = mat_data["sale_month"].str[:4].astype(int)
            mat_data["sale_month_idx"] = mat_data["sale_month"].str[4:6].astype(int)
            mat_data["month_offset"] = (mat_data["sale_year"] - first_y) * 12 + (mat_data["sale_month_idx"] - first_mo)
            mat_data = mat_data.drop_duplicates(subset=["material_code", "customer", "month_offset"])

            first_offset = mat_data.groupby("customer")["month_offset"].min()
            row_result = {"material_code": mat}

            for j in range(1, effective_max + 1):
                cumulative_new = int((first_offset < j).sum())
                current_mask = mat_data["month_offset"] == j
                repurchase_mask = current_mask & mat_data["customer"].isin(first_offset[first_offset < j].index)
                repurchase_count = int(mat_data.loc[repurchase_mask, "customer"].nunique())
                repurchase_count = min(repurchase_count, cumulative_new)
                rate = (repurchase_count / cumulative_new * 100) if cumulative_new > 0 else 0
                row_result[f"+{j}月"] = round(rate, 1)

            results.append(row_result)

        if not results:
            return {"retention_data": [], "summary": {}}

        retention_df = pd.DataFrame(results)

        # 商品级过滤已下推到主 SQL，无需再过滤

        # 添加元数据
        retention_df["first_stock_in_date"] = retention_df["material_code"].map(lambda x: meta_map.get(x, {}).get("first_stock_in_date", ""))
        retention_df["abc_class"] = retention_df["material_code"].map(lambda x: meta_map.get(x, {}).get("abc_class", ""))
        retention_df["lifecycle_status"] = retention_df["material_code"].map(lambda x: meta_map.get(x, {}).get("lifecycle_status", ""))

        # 添加material_name
        mat_name_map = df.groupby("material_code")["material_name"].first().to_dict()
        retention_df["material_name"] = retention_df["material_code"].map(mat_name_map)

        # 排序
        retention_df["first_stock_in_date_dt"] = pd.to_datetime(retention_df["first_stock_in_date"], errors="coerce")
        retention_df = retention_df.sort_values("first_stock_in_date_dt", ascending=False).drop(columns=["first_stock_in_date_dt"])

        # 格式化输出
        retention_data = []
        cols = ["lifecycle_status", "abc_class", "material_code", "material_name", "first_stock_in_date"] + [f"+{j}月" for j in range(1, effective_max + 1)]
        for _, row in retention_df.iterrows():
            row_data = {}
            for col in cols:
                if col in row.index:
                    val = row[col]
                    if pd.isna(val):
                        val = ""
                    elif isinstance(val, float):
                        val = val if not np.isnan(val) else ""
                    row_data[col] = val
            retention_data.append(row_data)

        summary = {
            "total_products": len(retention_data),
            "max_months": effective_max,
        }

        return {
            "retention_data": retention_data,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取客户留存率表失败: {e}")
        return {"retention_data": [], "summary": {}, "error": "数据获取失败"}


# ===================== 新品预警表 =====================
def get_new_product_warning(
    db: Session,
    days: int = 90,
) -> Dict[str, Any]:
    """
    获取新品预警表

    Args:
        db: Database session
        days: 建档天数范围（显示多少天内建档的产品）

    Returns:
        新品预警表数据
    """
    try:
        # 构建WHERE条件 - 新品预警按产品维度，不按大区过滤
        conditions = ["doc_date IS NOT NULL", "sales_out_qty > 0"]
        params = {}

        where_sql = " AND ".join(conditions)

        # 计算日期过滤条件（距今days天内建档的产品）
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        logger.info(f"[新品预警] days={days}, cutoff_date={cutoff_date}")

        # 查询建档天数内入库的产品
        sql = text("""
            SELECT material_code, material_name, first_stock_in_date
            FROM dim_product_attr
            WHERE first_stock_in_date IS NOT NULL
            AND first_stock_in_date >= :cutoff_date
        """)
        df_new = pd.read_sql(sql, db.bind, params={"cutoff_date": cutoff_date})
        logger.info(f"[新品预警] 查询到产品数量: {len(df_new)}")

        if df_new.empty:
            logger.info(f"[新品预警] 截止日期 {cutoff_date} 内无产品，返回空")
            return {"new_products": [], "summary": {"message": "暂无新品数据"}}

        df_new = df_new.drop_duplicates(subset=["material_code"])

        mat_codes = df_new["material_code"].tolist()
        logger.info(f"[新品预警] 产品编码列表前10个: {mat_codes[:10]}")
        if not mat_codes:
            return {"new_products": [], "summary": {}}

        # 查询新品日销量
        placeholders = ",".join([f":code{i}" for i in range(len(mat_codes))])
        sale_params = {**params, **{f"code{i}": code for i, code in enumerate(mat_codes)}}
        sql_sales = text(f"""
            SELECT material_code, doc_date, SUM(sales_out_qty) AS daily_qty
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + f""" AND material_code IN ({placeholders})
            GROUP BY material_code, doc_date
        """)
        df_sales = pd.read_sql(sql_sales, db.bind, params=sale_params)
        logger.info(f"[新品预警] 查询到销量记录数: {len(df_sales)}")

        if df_sales.empty:
            logger.info(f"[新品预警] 产品无销量数据，返回空")
            return {"new_products": [], "summary": {"message": "暂无新品销售数据"}}

        # 计算距建档天数
        filing_map = dict(zip(df_new["material_code"], df_new["first_stock_in_date"]))
        df_sales["first_stock_in_date"] = df_sales["material_code"].map(filing_map)
        df_sales = df_sales.dropna(subset=["first_stock_in_date"])

        df_sales["first_stock_in_date"] = pd.to_datetime(df_sales["first_stock_in_date"])
        df_sales["doc_date"] = pd.to_datetime(df_sales["doc_date"])
        df_sales["days_from_filing"] = (df_sales["doc_date"] - df_sales["first_stock_in_date"]).dt.days

        # 按区间分组 - 根据days参数动态调整bins
        if days <= 60:
            bins = [0, 7, 15, 30, 45, 60, float("inf")]
            labels = ["0-7", "7-15", "15-30", "30-45", "45-60", "60+"]
        elif days <= 90:
            bins = [0, 7, 15, 30, 45, 60, 90, float("inf")]
            labels = ["0-7", "7-15", "15-30", "30-45", "45-60", "60-90", "90+"]
        else:
            bins = [0, 7, 15, 30, 45, 60, 90, 180, float("inf")]
            labels = ["0-7", "7-15", "15-30", "30-45", "45-60", "60-90", "90-180", "180+"]
        df_sales["interval"] = pd.to_numeric(df_sales["days_from_filing"], errors="coerce")
        df_sales = df_sales.dropna(subset=["interval"])
        df_sales["interval_bin"] = pd.cut(df_sales["interval"], bins=bins, labels=labels, right=False)

        # 透视
        pivot = df_sales[df_sales["interval_bin"] != ""].pivot_table(
            index="material_code", columns="interval_bin", values="daily_qty", aggfunc="sum", fill_value=0
        )
        pivot = pivot[[c for c in labels if c in pivot.columns]]

        # 查询在库量
        stock_params = {f"code{i}": code for i, code in enumerate(mat_codes)}
        sql_stock = text(f"""
            SELECT material_code, SUM(current_stock) AS current_stock
            FROM stg_stock_current
            WHERE material_code IN ({placeholders}) AND current_stock > 0
            GROUP BY material_code
        """)
        df_stock = pd.read_sql(sql_stock, db.bind, params=stock_params)
        stock_map = dict(zip(df_stock["material_code"], df_stock["current_stock"]))

        # 查询首销时间
        sql_first = text(f"""
            SELECT material_code, MIN(doc_date) AS first_sale_date
            FROM rpt_sales_out_wide
            WHERE material_code IN ({placeholders}) AND doc_date IS NOT NULL AND sales_out_qty > 0
            GROUP BY material_code
        """)
        df_first = pd.read_sql(sql_first, db.bind, params=stock_params)
        first_sale_map = dict(zip(df_first["material_code"], df_first["first_sale_date"]))

        # 合并数据
        df_new = df_new.copy()
        df_new["first_sale_date"] = df_new["material_code"].map(first_sale_map)

        # 获取ABC分类
        sql_abc = text(f"""
            SELECT material_code, abc_class
            FROM dim_product_attr
            WHERE material_code IN ({placeholders})
        """)
        df_abc = pd.read_sql(sql_abc, db.bind, params=stock_params)
        abc_map = dict(zip(df_abc["material_code"], df_abc["abc_class"]))

        new_products = []
        for _, row in df_new.iterrows():
            mat_code = row["material_code"]
            first_filing = str(row["first_stock_in_date"])[:10] if pd.notna(row["first_stock_in_date"]) else ""
            first_sale = str(row["first_sale_date"])[:10] if pd.notna(row["first_sale_date"]) else ""

            row_data = {
                "material_code": mat_code,
                "material_name": row["material_name"],
                "abc_class": abc_map.get(mat_code, ""),
                "first_stock_in_date": first_filing,
                "first_sale_date": first_sale,
                "current_stock": int(stock_map.get(mat_code, 0)),
                "lifecycle_status": "新品",
            }

            # 添加各区间销量
            for col in labels:
                if col in pivot.columns and mat_code in pivot.index:
                    row_data[col] = int(pivot.loc[mat_code, col])
                else:
                    row_data[col] = 0

            new_products.append(row_data)

        # 按物料编码排序
        new_products.sort(key=lambda x: x.get("material_code", ""))

        summary = {
            "total_new_products": len(new_products),
            "interval_days": days,
        }

        return {
            "new_products": new_products,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取新品预警表失败: {e}")
        return {"new_products": [], "summary": {}, "error": "数据获取失败"}


# ===================== 客户商品 Cohort 矩阵 =====================
def get_customer_product_matrix(
    db: Session,
    customer: str,
    months: int = 12,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    view_mode: str = 'offset',
) -> Dict[str, Any]:
    """
    获取指定客户的商品 Cohort 矩阵

    Args:
        db: Database session
        customer: 客户名称
        months: 追溯月数
        region: 大区（已废弃，仅保留参数兼容）
        manager: 客户经理（已废弃，仅保留参数兼容）
        view_mode: 视图模式，offset=偏移模式(首月/+1月)，absolute=动态日期模式

    Returns:
        客户商品 Cohort 矩阵数据
    """
    try:
        conditions = ["customer = :customer", "doc_date IS NOT NULL", "sales_out_qty > 0"]
        params = {"customer": customer}

        where_sql = " AND ".join(conditions)

        # 查询该客户的月度物料销售数据
        sql = text("""
            SELECT material_code, material_name,
                   DATE_FORMAT(doc_date, '%Y%m') AS sale_month,
                   SUM(sales_out_qty) AS monthly_qty
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            GROUP BY material_code, material_name, DATE_FORMAT(doc_date, '%Y%m')
            ORDER BY material_code, sale_month
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"matrix_data": [], "month_columns": [], "summary": None}

        # ---------- 客户摘要统计 ----------
        from datetime import datetime, timedelta
        today = datetime.today().date()

        # 该客户全量明细（不限 sales_out_qty > 0，用于金额统计）
        sql_summary = text("""
            SELECT doc_date, tax_included_amount
            FROM rpt_sales_out_wide
            WHERE customer = :customer AND doc_date IS NOT NULL
        """)
        df_summary = pd.read_sql(sql_summary, db.bind, params={"customer": customer})

        summary = None
        if not df_summary.empty:
            df_summary["doc_date"] = pd.to_datetime(df_summary["doc_date"]).dt.date
            first_date = df_summary["doc_date"].min()
            cooperation_days = (today - first_date).days
            total_amount = round(df_summary["tax_included_amount"].sum(), 2)

            # 首次合作90天内
            first_90d_end = first_date + timedelta(days=90)
            amount_first_90d = round(df_summary[
                (df_summary["doc_date"] >= first_date) & (df_summary["doc_date"] <= first_90d_end)
            ]["tax_included_amount"].sum(), 2)

            # 合作90-180天内
            first_180d_end = first_date + timedelta(days=180)
            amount_90_to_180d = round(df_summary[
                (df_summary["doc_date"] > first_90d_end) & (df_summary["doc_date"] <= first_180d_end)
            ]["tax_included_amount"].sum(), 2)

            # 最近90天内
            last_90d_start = today - timedelta(days=90)
            amount_last_90d = round(df_summary[
                df_summary["doc_date"] >= last_90d_start
            ]["tax_included_amount"].sum(), 2)

            summary = {
                "cooperation_days": cooperation_days,
                "total_amount": total_amount,
                "amount_first_90d": amount_first_90d,
                "amount_90_to_180d": amount_90_to_180d,
                "amount_last_90d": amount_last_90d,
            }

        # 查询该客户首次进货月份（按物料）
        sql_first = text("""
            SELECT material_code,
                   DATE_FORMAT(MIN(doc_date), '%Y%m') AS first_month
            FROM rpt_sales_out_wide
            WHERE """ + where_sql + """
            GROUP BY material_code
        """)
        df_first = pd.read_sql(sql_first, db.bind, params=params)
        first_map = dict(zip(df_first["material_code"], df_first["first_month"]))

        # 计算月份偏移
        df["first_month"] = df["material_code"].map(first_map)
        df["first_year"] = df["first_month"].str[:4].astype(int)
        df["first_month_idx"] = df["first_month"].str[4:6].astype(int)
        df["sale_year"] = df["sale_month"].str[:4].astype(int)
        df["sale_month_idx"] = df["sale_month"].str[4:6].astype(int)
        df["month_offset"] = (df["sale_year"] - df["first_year"]) * 12 + (df["sale_month_idx"] - df["first_month_idx"])

        # 过滤有效范围
        df = df[df["month_offset"] >= 0]
        df = df[df["month_offset"] <= months]

        # 构建物料统计（按首次进货月份分组）
        material_stats = df.groupby("material_code").agg(
            material_name=("material_name", "first"),
            first_month=("first_month", "first"),
            total_qty=("monthly_qty", "sum")
        ).reset_index()

        # 构建月份偏移矩阵
        pivot = df.pivot_table(
            index="material_code", columns="month_offset", values="monthly_qty", aggfunc="sum", fill_value=0
        )

        # 计算最大偏移月
        max_offset = int(df["month_offset"].max()) if not df.empty else 0

        if view_mode == 'absolute':
            # 动态日期模式：以每个物料的首月作为基准
            from datetime import datetime

            # 找到最早的首月（用于生成列名）
            if 'first_month' in material_stats.columns and not material_stats.empty:
                valid_first_months = material_stats['first_month'].dropna()
                if len(valid_first_months) > 0:
                    earliest_month = valid_first_months.min()
                    first_y = int(str(earliest_month)[:4])
                    first_m = int(str(earliest_month)[4:6])
                    logger.info(f"[Cohort ABSOLUTE] earliest_month={earliest_month}, first_y={first_y}, first_m={first_m}")
                else:
                    first_y = datetime.now().year
                    first_m = datetime.now().month
            else:
                first_y = datetime.now().year
                first_m = datetime.now().month

            # 生成从最早首月开始的 months 个月份
            absolute_months = []
            absolute_months_label = []
            for i in range(months):
                total_months = first_y * 12 + first_m - 1 + i
                year = total_months // 12
                month = total_months % 12 + 1
                absolute_months.append(f"{year}{month:02d}")  # YYYYMM 格式用于匹配
                absolute_months_label.append(f"{year}-{month:02d}")  # YYYY-MM 格式用于显示

            logger.info(f"[Cohort ABSOLUTE] Generated absolute_months (YYYYMM): {absolute_months}")
            logger.info(f"[Cohort ABSOLUTE] pivot.index: {list(pivot.index)}")
            logger.info(f"[Cohort ABSOLUTE] pivot.columns: {list(pivot.columns)}")
            logger.info(f"[Cohort ABSOLUTE] max_offset: {max_offset}")
            logger.info(f"[Cohort ABSOLUTE] material_stats: {material_stats[['material_code', 'first_month']].to_dict('records')}")

            # 动态日期模式：提前构建 sales_map 用于按实际月份匹配
            sales_map = df.pivot_table(
                index="material_code", columns="sale_month", values="monthly_qty", aggfunc="sum", fill_value=0
            )
            logger.info(f"[Cohort ABSOLUTE] sales_map.columns (actual sale months): {list(sales_map.columns)}")
            month_columns = absolute_months_label
        else:
            # 偏移模式：首月/+1月/+2月...
            all_offsets = list(range(0, max_offset + 1))
            month_columns = ["首月" if col == 0 else f"+{col}月" for col in all_offsets]

        # 构建返回数据
        matrix_data = []

        if view_mode == 'absolute':
            # 动态日期模式：数据按实际月份对齐
            for mat_code in material_stats['material_code']:
                row = material_stats[material_stats['material_code'] == mat_code].iloc[0]
                first_month = str(row['first_month']) if pd.notna(row['first_month']) else ""
                first_period = first_month + "01" if first_month else ""
                row_data = {
                    "material_code": mat_code,
                    "material_name": row['material_name'],
                    "first_period": first_period,
                    "first_month": first_month,
                    "total_amount": 0,
                }
                logger.info(f"[Cohort ABSOLUTE] Processing mat_code={mat_code}, first_month={first_month}")

                for i, col in enumerate(absolute_months):
                    col_label = absolute_months_label[i]  # YYYY-MM 格式，用于前端显示
                    if mat_code in sales_map.index and col in sales_map.columns:
                        value = int(sales_map.loc[mat_code, col])
                        row_data[col_label] = value if value > 0 else None
                        logger.info(f"  col={col}: value={value}")
                    else:
                        row_data[col_label] = None
                        logger.info(f"  col={col}: no data")

                matrix_data.append(row_data)
        else:
            # 偏移模式：首月/+1月...
            for _, row in material_stats.iterrows():
                mat_code = row["material_code"]
                first_month = str(row["first_month"]) if pd.notna(row["first_month"]) else ""
                first_period = first_month + "01" if first_month else ""
                row_data = {
                    "material_code": mat_code,
                    "material_name": row["material_name"],
                    "first_period": first_period,
                    "first_month": first_month,
                    "total_amount": 0,
                }

                all_offsets = list(range(0, max_offset + 1))
                for col in all_offsets:
                    col_name = "首月" if col == 0 else f"+{col}月"
                    if col in pivot.columns and mat_code in pivot.index:
                        row_data[col_name] = int(pivot.loc[mat_code, col])
                    else:
                        row_data[col_name] = 0

                matrix_data.append(row_data)

        # 按物料编码排序
        matrix_data.sort(key=lambda x: x.get("material_code", ""))

        return {
            "matrix_data": matrix_data,
            "month_columns": month_columns,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"获取客户商品 Cohort 矩阵失败: {e}")
        return {"matrix_data": [], "month_columns": [], "error": "数据获取失败"}
