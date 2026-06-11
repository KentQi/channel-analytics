"""
高级分析服务
提供商品生命周期分析、客户生命周期分析、商品聚类、客户聚类
"""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.metrics import (
    PRODUCT_LIFECYCLE_REQUESTS,
    CUSTOMER_LIFECYCLE_REQUESTS,
    PRODUCT_CLUSTER_REQUESTS,
    CUSTOMER_CLUSTER_REQUESTS,
    PRODUCT_LIFECYCLE_DURATION,
    CUSTOMER_LIFECYCLE_DURATION,
    PRODUCT_CLUSTER_DURATION,
    CUSTOMER_CLUSTER_DURATION,
    PRODUCT_LIFECYCLE_DATA_POINTS,
    CUSTOMER_LIFECYCLE_DATA_POINTS,
    PRODUCT_CLUSTER_DATA_POINTS,
    CUSTOMER_CLUSTER_DATA_POINTS,
)

logger = logging.getLogger(__name__)

# 加载配置文件
_config = None


def _load_config():
    """加载高级分析配置"""
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "advanced_analysis.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _config = yaml.safe_load(f)
            logger.info(f"已加载高级分析配置: {config_path}")
        except Exception as e:
            logger.warning(f"加载配置文件失败，使用默认配置: {e}")
            _config = {}
    return _config


def _get_config():
    """获取配置，如果加载失败返回空字典"""
    return _load_config() or {}


def _to_date(val):
    """将各种类型转换为date对象，无法转换则返回None"""
    if val is None:
        return None
    if isinstance(val, float):
        return None  # NaN from pandas
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, pd.Timestamp):
        return val.date()
    if hasattr(val, 'date'):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        if not val or val == 'NaT' or val == 'None':
            return None
        try:
            return datetime.strptime(val.replace("/", "-"), "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(val, "%Y/%m/%d").date()
            except ValueError:
                return None
    # date 对象直接返回
    if isinstance(val, type(datetime.now().date())):
        return val
    return None


# ============================================================
# 趋势分析工具函数（批发行业出货数据衰退检测）
# ============================================================

def _linear_trend(monthly_values):
    """
    线性回归趋势分析

    Returns:
        dict: slope(绝对斜率), normalized_slope(归一化斜率%), intercept, r_squared
    """
    n = len(monthly_values)
    if n < 3:
        return {"slope": 0, "normalized_slope": 0, "intercept": 0, "r_squared": 0}

    t = np.arange(1, n + 1, dtype=float)
    y = np.array(monthly_values, dtype=float)

    # 最小二乘法
    t_mean = np.mean(t)
    y_mean = np.mean(y)
    ss_tt = np.sum((t - t_mean) ** 2)
    if ss_tt == 0:
        return {"slope": 0, "normalized_slope": 0, "intercept": y_mean, "r_squared": 0}

    slope = np.sum((t - t_mean) * (y - y_mean)) / ss_tt
    intercept = y_mean - slope * t_mean

    # R²
    y_pred = intercept + slope * t
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # 归一化斜率（占均值的百分比）
    denom = abs(y_mean) if abs(y_mean) > 1 else 1  # 避免除以极小值
    normalized_slope = slope / denom * 100

    return {
        "slope": float(slope),
        "normalized_slope": float(normalized_slope),
        "intercept": float(intercept),
        "r_squared": float(max(0, r_squared)),
    }


def _mann_kendall_test(monthly_values):
    """
    Mann-Kendall 趋势检验（非参数，抗异常值）

    Returns:
        dict: S(统计量), Z(Z值), p_value, sen_slope(Sen斜率), direction(趋势方向)
    """
    n = len(monthly_values)
    if n < 4:
        return {"S": 0, "Z": 0, "p_value": 1.0, "sen_slope": 0, "direction": "no_trend"}

    y = np.array(monthly_values, dtype=float)

    # 计算 S 统计量
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = y[j] - y[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    # 方差（含并列修正）
    unique_vals, counts = np.unique(y, return_counts=True)
    tp = counts[counts > 1]
    var_s = (n * (n - 1) * (2 * n + 5) - np.sum(tp * (tp - 1) * (2 * tp + 5))) / 18.0

    if var_s <= 0:
        return {"S": s, "Z": 0, "p_value": 1.0, "sen_slope": 0, "direction": "no_trend"}

    # Z 统计量
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0

    # 近似 p 值（正态分布）
    # 使用近似公式避免 scipy 依赖
    abs_z = abs(z)
    if abs_z > 8:
        p_value = 0.0
    else:
        # Abramowitz and Stegun 近似
        t_val = 1.0 / (1.0 + 0.2316419 * abs_z)
        d = 0.3989422804014327  # 1/sqrt(2*pi)
        p_val_one_tail = d * np.exp(-abs_z * abs_z / 2) * (
            t_val * (0.319381530 + t_val * (-0.356563782 + t_val * (1.781477937 +
            t_val * (-1.821255978 + t_val * 1.330274429))))
        )
        p_value = 2 * p_val_one_tail

    # Sen's 斜率（中位数斜率，抗异常值）
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            if j != i:
                slopes.append((y[j] - y[i]) / (j - i))
    sen_slope = float(np.median(slopes)) if slopes else 0

    # 趋势方向
    if p_value < 0.05:
        direction = "declining" if s < 0 else "rising"
    else:
        direction = "no_trend"

    return {
        "S": int(s),
        "Z": float(z),
        "p_value": float(p_value),
        "sen_slope": sen_slope,
        "direction": direction,
    }


def _ema_crossover(monthly_values, short_period=3, long_period=6):
    """
    EMA交叉检测（死亡交叉 = 衰退信号）

    Returns:
        dict: ema_short, ema_long, gap_pct(交叉缺口%), death_cross(是否死叉)
    """
    n = len(monthly_values)
    if n < long_period:
        return {"ema_short": 0, "ema_long": 0, "gap_pct": 0, "death_cross": False}

    y = np.array(monthly_values, dtype=float)

    # 计算 EMA
    alpha_short = 2.0 / (short_period + 1)
    alpha_long = 2.0 / (long_period + 1)

    ema_s = y[0]
    ema_l = y[0]
    for i in range(1, n):
        ema_s = alpha_short * y[i] + (1 - alpha_short) * ema_s
        ema_l = alpha_long * y[i] + (1 - alpha_long) * ema_l

    # 交叉缺口
    gap_pct = 0
    if ema_l > 0:
        gap_pct = (ema_l - ema_s) / ema_l * 100

    # 死叉：短期EMA < 长期EMA
    death_cross = ema_s < ema_l

    return {
        "ema_short": float(ema_s),
        "ema_long": float(ema_l),
        "gap_pct": float(gap_pct),
        "death_cross": bool(death_cross),
    }


def _compute_decline_confidence(
    linear_trend_result,
    mann_kendall_result,
    ema_result,
    consecutive_negative_months,
    r_squared_min=0.4,
):
    """
    衰退置信度评分（0~100）

    信号权重：
    - 线性回归斜率 + R²: 40分
    - Mann-Kendall Z值:    30分
    - EMA死叉:            15分
    - 连续负增长月数:      15分
    """
    score = 0
    reasons = []

    # 信号1：线性回归（40分）
    norm_slope = linear_trend_result["normalized_slope"]
    r_sq = linear_trend_result["r_squared"]
    if norm_slope < 0 and r_sq >= r_squared_min:
        if norm_slope < -10:
            score += 40
            reasons.append(f"趋势斜率{norm_slope:.1f}%（严重）")
        elif norm_slope < -5:
            score += 30
            reasons.append(f"趋势斜率{norm_slope:.1f}%（中度）")
        elif norm_slope < -2:
            score += 20
            reasons.append(f"趋势斜率{norm_slope:.1f}%（轻度）")
        else:
            score += 5
    elif norm_slope < 0 and r_sq >= 0.2:
        # R²较低但有下降趋势，给部分分
        if norm_slope < -5:
            score += 15
            reasons.append(f"趋势斜率{norm_slope:.1f}%（R²={r_sq:.2f}，弱信号）")

    # 信号2：Mann-Kendall（30分）
    mk = mann_kendall_result
    if mk["direction"] == "declining":
        abs_z = abs(mk["Z"])
        if abs_z > 2.576:
            score += 30
            reasons.append(f"Mann-Kendall显著下降(p={mk['p_value']:.3f})")
        elif abs_z > 1.96:
            score += 20
            reasons.append(f"Mann-Kendall下降(p={mk['p_value']:.3f})")
        else:
            score += 10

    # 信号3：EMA死叉（15分）
    if ema_result["death_cross"]:
        gap = ema_result["gap_pct"]
        if gap > 10:
            score += 15
            reasons.append(f"EMA死叉缺口{gap:.1f}%")
        elif gap > 5:
            score += 10
            reasons.append(f"EMA死叉缺口{gap:.1f}%")
        else:
            score += 5

    # 信号4：连续负增长（15分）
    if consecutive_negative_months >= 6:
        score += 15
        reasons.append(f"连续{consecutive_negative_months}月负增长")
    elif consecutive_negative_months >= 3:
        score += 10
        reasons.append(f"连续{consecutive_negative_months}月负增长")
    elif consecutive_negative_months >= 2:
        score += 5

    # 结构性衰退判定
    is_structural = False
    short_slope = linear_trend_result.get("normalized_slope", 0)
    # 如果有长期斜率数据（在调用方传入），判断结构性
    # 这里简化：R² > 0.4 且斜率 < -5% 视为结构性
    if r_sq >= 0.4 and norm_slope < -5:
        is_structural = True

    return {
        "score": min(score, 100),
        "is_decline": score >= 70,
        "is_suspected": 40 <= score < 70,
        "is_structural": is_structural,
        "reasons": reasons,
    }


def get_product_lifecycle(
    db: Session,
    months: int = 18,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    category: Optional[str] = None,
    abc_class: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    material_code: Optional[str] = None,
    brand_class: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    商品生命周期分析（供应链PLC模型）

    基于累计出库量 + 销售趋势的MECE级联判定：
    1. 累计出库 < 5000 → 导入期
    2. 连续负增长 ≥ 3月 → 衰退期
    3. 累计出库 ≥ 20000 且 |增长率| ≤ 10% → 成熟期
    4. 累计出库 ≥ 5000 且 增长率 > 0 → 成长期
    5. 累计出库 ≥ 5000 且 增长率 ≤ 0 且 < 20000 → 成熟期（平台过渡）

    新品S曲线子阶段（lifecycle_status == "新品"）：
    - 试销期: 上市 ≤ 30天
    - 爬坡期: 31-60天
    - 稳定期: 61-90天

    Returns:
        包含lifecycle_data(明细)、metrics(汇总)、demand_signals(需求信号)的字典
    """
    start_time = time.time()
    try:
        # ──────────────────────────────────────────────
        # 1. 构建WHERE条件
        # ──────────────────────────────────────────────
        conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
        params = {}

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
        if category:
            conditions.append("category = :category")
            params["category"] = category
        if abc_class:
            conditions.append("abc_class = :abc_class")
            params["abc_class"] = abc_class
        if material_code:
            conditions.append("material_code = :material_code")
            params["material_code"] = material_code

        # 日期范围占位 - 主查询先取全量，追溯周期窗口在 pandas 里按每物料 first_stock_in_date 过滤
        end_date = datetime.now()
        params["end_date"] = end_date.strftime("%Y-%m-%d")
        params["months"] = months
        # 不加 doc_date BETWEEN 条件，pandas 里逐物料窗口过滤

        where_sql = " AND ".join(conditions)

        # ──────────────────────────────────────────────
        # 2. 查询月度销售数据（先取全量，按物料 first_stock_in_date 追溯周期在 pandas 过滤）
        # ──────────────────────────────────────────────
        sql = text(f"""
            SELECT material_code, material_name,
                   DATE_FORMAT(doc_date, '%Y-%m') AS sale_month,
                   SUM(tax_included_amount) AS monthly_amount,
                   SUM(sales_out_qty) AS monthly_qty,
                   COUNT(DISTINCT customer) AS customer_count
            FROM rpt_sales_out_wide
            WHERE {where_sql}
            GROUP BY material_code, material_name, DATE_FORMAT(doc_date, '%Y-%m')
            ORDER BY material_code, sale_month
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"lifecycle_data": [], "metrics": {}, "demand_signals": {}}

        # ──────────────────────────────────────────────
        # 3. 查询商品属性（dim_product_attr）
        # ──────────────────────────────────────────────
        sql_goods = text("""
            SELECT material_code, first_stock_in_date, abc_class, lifecycle_status
            FROM dim_product_attr
            WHERE material_code IS NOT NULL AND material_code != ''
        """)
        df_goods = pd.read_sql(sql_goods, db.bind)
        df = df.merge(df_goods, on="material_code", how="left")

        # ──────────────────────────────────────────────
        # 3.1 追溯周期窗口过滤：每个物料从 first_stock_in_date 起往后看 months 月
        # 没有 first_stock_in_date 的物料以该物料首销月为窗口起点（避免数据丢失）
        # ──────────────────────────────────────────────
        if not df.empty and "sale_month" in df.columns:
            df["sale_date"] = pd.to_datetime(df["sale_month"] + "-01", errors="coerce")
            # 用首销月回填 NULL first_stock_in_date
            first_sale_map = df.groupby("material_code")["sale_date"].min()
            window_start = pd.to_datetime(df["first_stock_in_date"], errors="coerce")
            fallback_fsd = df["material_code"].map(first_sale_map)
            window_start = window_start.fillna(fallback_fsd)
            window_end = window_start + pd.DateOffset(months=months)
            mask = (df["sale_date"] >= window_start) & (df["sale_date"] < window_end)
            df = df[mask].drop(columns=["sale_date"])
            if df.empty:
                return {"lifecycle_data": [], "metrics": {}, "demand_signals": {}}

        # ──────────────────────────────────────────────
        # 3.5 品牌类型（brand_class）筛选
        # ──────────────────────────────────────────────
        # 记录经过 brand_class 过滤后的物料编码，用于后续查询
        filtered_material_codes = None

        if brand_class:
            # 读取自营品牌白名单
            try:
                self_brand_rows = db.execute(
                    text("SELECT brand_name FROM dim_self_operated_brand")
                ).fetchall()
                self_brands = {r[0] for r in self_brand_rows if r[0]}
            except Exception:
                self_brands = set()

            # 查询每个物料的品牌
            sql_brand = text("""
                SELECT material_code, brand
                FROM rpt_sales_out_wide
                WHERE brand IS NOT NULL AND brand != ''
                GROUP BY material_code, brand
            """)
            df_brand = pd.read_sql(sql_brand, db.bind)
            if not df_brand.empty:
                df_brand["brand_class"] = df_brand["brand"].apply(
                    lambda x: "自营" if x in self_brands else "非自营"
                )
                df_brand = df_brand.drop_duplicates(subset=["material_code"], keep="first")
                df = df.merge(df_brand[["material_code", "brand_class"]],
                              on="material_code", how="left")
                df["brand_class"] = df["brand_class"].fillna("非自营")
                df = df[df["brand_class"] == brand_class]
                if df.empty:
                    return {"lifecycle_data": [], "metrics": {}, "demand_signals": {}}
                filtered_material_codes = df["material_code"].unique().tolist()

        # 按lifecycle_status筛选（如果有）
        if lifecycle_status:
            df = df[df["lifecycle_status"] == lifecycle_status]
            if df.empty:
                return {"lifecycle_data": [], "metrics": {}, "demand_signals": {}}
            filtered_material_codes = df["material_code"].unique().tolist()

        # ──────────────────────────────────────────────
        # 4. 累计出库量直接从主查询 df 聚合（df 已按追溯周期窗口过滤）
        # ──────────────────────────────────────────────
        df_cumulative = (
            df.groupby("material_code", as_index=False)["monthly_qty"]
            .sum()
            .rename(columns={"monthly_qty": "cumulative_out_qty"})
        )

        # ──────────────────────────────────────────────
        # 4.5 查询在库量（从 stg_stock_current 聚合，按物料）
        # 在库量是物料维度属性，不受 region / manager 等条件影响
        # 但仍受 brand_class / lifecycle_status / material_code 过滤
        # ──────────────────────────────────────────────
        stock_conditions = ["material_code IS NOT NULL", "material_code != ''"]
        stock_params = {}
        if material_code:
            stock_conditions.append("material_code = :material_code")
            stock_params["material_code"] = material_code
        if filtered_material_codes is not None:
            mc_placeholders = [f":mc_{i}" for i in range(len(filtered_material_codes))]
            stock_conditions.append(f"material_code IN ({','.join(mc_placeholders)})")
            for i, mc in enumerate(filtered_material_codes):
                stock_params[f"mc_{i}"] = mc
        stock_where = " AND ".join(stock_conditions)

        sql_stock = text(f"""
            SELECT material_code,
                   COALESCE(SUM(current_stock), 0) AS current_stock_qty
            FROM stg_stock_current
            WHERE {stock_where}
            GROUP BY material_code
        """)
        df_stock = pd.read_sql(sql_stock, db.bind, params=stock_params)

        # ──────────────────────────────────────────────
        # 5. 查询每个商品的去重客户数（追溯周期窗口内）
        # 用 pandas merge 替代 COLLATE SQL JOIN，规避 collation 不一致
        # ──────────────────────────────────────────────
        if filtered_material_codes is not None:
            target_materials = set(filtered_material_codes)
        else:
            target_materials = set(df["material_code"].unique().tolist())
        if material_code and material_code not in target_materials:
            target_materials.add(material_code)
        if not target_materials:
            total_customers = 1
            df_product_cust = pd.DataFrame(columns=["material_code", "distinct_customer_count"])
        else:
            # 查询目标物料的销售明细（doc_date, material_code, customer, region）
            mc_list = list(target_materials)
            mc_ph = ",".join([f":mc{i}" for i in range(len(mc_list))])
            mc_params = {f"mc{i}": v for i, v in enumerate(mc_list)}
            cust_conditions = [
                "doc_date IS NOT NULL",
                f"material_code IN ({mc_ph})",
            ]
            if allowed_regions:
                ar_ph = ",".join([f":ar{i}" for i in range(len(allowed_regions))])
                cust_conditions.append(f"region IN ({ar_ph})")
                for i, r in enumerate(allowed_regions):
                    mc_params[f"ar{i}"] = r
            if region:
                cust_conditions.append("region = :region")
                mc_params["region"] = region
            cust_where = " AND ".join(cust_conditions)

            sql_cust_detail = text(f"""
                SELECT material_code, customer, doc_date
                FROM rpt_sales_out_wide
                WHERE {cust_where}
            """)
            df_cust_detail = pd.read_sql(sql_cust_detail, db.bind, params=mc_params)

            if not df_cust_detail.empty:
                # 查询 dim_product_attr 的 first_stock_in_date
                sql_fsd = text("""
                    SELECT material_code, first_stock_in_date
                    FROM dim_product_attr
                    WHERE material_code IS NOT NULL AND material_code != ''
                """)
                df_fsd = pd.read_sql(sql_fsd, db.bind)
                # pandas merge 替代 COLLATE SQL JOIN
                df_cust_detail = df_cust_detail.merge(df_fsd, on="material_code", how="left")
                # 回填 NULL fsd：用该物料的最早 doc_date
                df_cust_detail["doc_date_dt"] = pd.to_datetime(df_cust_detail["doc_date"], errors="coerce")
                first_doc_map = df_cust_detail.groupby("material_code")["doc_date_dt"].min()
                fsd_dt = pd.to_datetime(df_cust_detail["first_stock_in_date"], errors="coerce")
                fallback = df_cust_detail["material_code"].map(first_doc_map)
                fsd_dt = fsd_dt.fillna(fallback)
                fsd_end = fsd_dt + pd.DateOffset(months=months)
                mask = (df_cust_detail["doc_date_dt"] >= fsd_dt) & (df_cust_detail["doc_date_dt"] < fsd_end)
                df_cust_windowed = df_cust_detail[mask]
                # 每物料去重客户数
                df_product_cust = (
                    df_cust_windowed.groupby("material_code", as_index=False)["customer"]
                    .nunique()
                    .rename(columns={"customer": "distinct_customer_count"})
                )
                # 总客户数
                total_customers = df_cust_windowed["customer"].nunique()
                if total_customers == 0:
                    total_customers = 1
            else:
                df_product_cust = pd.DataFrame(columns=["material_code", "distinct_customer_count"])
                total_customers = 1

        # ──────────────────────────────────────────────
        # 6. 计算每个商品的汇总指标
        # ──────────────────────────────────────────────
        product_stats = df.groupby(["material_code", "material_name"]).agg(
            total_amount=("monthly_amount", "sum"),
            total_qty=("monthly_qty", "sum"),
            months_active=("sale_month", "count"),
            first_sale_month=("sale_month", "min"),
            last_sale_month=("sale_month", "max"),
        ).reset_index()

        # 合并实际去重客户数
        product_stats = product_stats.merge(df_product_cust, on="material_code", how="left")
        product_stats["customer_count"] = product_stats["distinct_customer_count"].fillna(0).astype(int)

        product_stats["avg_monthly_qty"] = product_stats["total_qty"] / product_stats["months_active"]

        # 合并累计出库量
        product_stats = product_stats.merge(df_cumulative, on="material_code", how="left")
        product_stats["cumulative_out_qty"] = product_stats["cumulative_out_qty"].fillna(0).astype(int)

        # 合并在库量
        product_stats = product_stats.merge(df_stock, on="material_code", how="left")
        product_stats["current_stock_qty"] = product_stats["current_stock_qty"].fillna(0).astype(int)

        # 合并商品属性（去重，每个material_code只取一条）
        goods_unique = df_goods.drop_duplicates(subset=["material_code"])
        product_stats = product_stats.merge(goods_unique, on="material_code", how="left")

        # 计算上市天数
        today = end_date.date()
        product_stats["days_since_launch"] = product_stats["first_stock_in_date"].apply(
            lambda x: (today - _to_date(x)).days if _to_date(x) else None
        )

        # 客户渗透率
        product_stats["customer_penetration"] = (product_stats["customer_count"] / total_customers).round(4)

        # ──────────────────────────────────────────────
        # 7. 计算需求感知指标 + 趋势分析（三重信号模型）
        # ──────────────────────────────────────────────
        demand_metrics = []
        for material_code in df["material_code"].unique():
            mat_df = df[df["material_code"] == material_code].sort_values("sale_month")

            # 月度销售额序列（用于趋势分析）
            monthly_amounts = mat_df["monthly_amount"].values.tolist()

            # 环比增长率序列
            growth_rates = []
            if len(mat_df) >= 2:
                for i in range(1, len(mat_df)):
                    prev = mat_df.iloc[i - 1]["monthly_amount"]
                    curr = mat_df.iloc[i]["monthly_amount"]
                    if prev > 0:
                        growth_rates.append((curr - prev) / prev)
                    else:
                        growth_rates.append(0)

            # 近3月平均增长率
            if growth_rates:
                recent_growth = float(np.mean(growth_rates[-3:]))
            else:
                recent_growth = 0.0

            # 销售加速度
            if len(growth_rates) >= 2:
                acceleration = float(growth_rates[-1] - growth_rates[-2])
            else:
                acceleration = 0.0

            # 连续负/正增长月数
            consecutive_negative = 0
            for r in reversed(growth_rates):
                if r < 0:
                    consecutive_negative += 1
                else:
                    break
            consecutive_positive = 0
            for r in reversed(growth_rates):
                if r > 0:
                    consecutive_positive += 1
                else:
                    break

            # 需求稳定性 CV
            monthly_qtys = mat_df["monthly_qty"].values
            if len(monthly_qtys) >= 2 and np.mean(monthly_qtys) > 0:
                cv = float(np.std(monthly_qtys, ddof=1) / np.mean(monthly_qtys))
            else:
                cv = 0.0

            # ── 趋势分析三重信号 ──
            # 信号1：线性回归趋势线
            trend_result = _linear_trend(monthly_amounts)

            # 信号2：Mann-Kendall 检验
            mk_result = _mann_kendall_test(monthly_amounts)

            # 信号3：EMA 交叉
            ema_result = _ema_crossover(monthly_amounts, short_period=3, long_period=6)

            # 衰退置信度评分
            decline_result = _compute_decline_confidence(
                trend_result, mk_result, ema_result, consecutive_negative
            )

            demand_metrics.append({
                "material_code": material_code,
                "growth_rate": recent_growth,
                "sales_acceleration": acceleration,
                "consecutive_negative_months": consecutive_negative,
                "consecutive_positive_months": consecutive_positive,
                "cv": cv,
                # 趋势分析指标
                "trend_slope": trend_result["slope"],
                "trend_normalized_slope": trend_result["normalized_slope"],
                "trend_r_squared": trend_result["r_squared"],
                "mk_direction": mk_result["direction"],
                "mk_p_value": mk_result["p_value"],
                "mk_sen_slope": mk_result["sen_slope"],
                "ema_short": ema_result["ema_short"],
                "ema_long": ema_result["ema_long"],
                "ema_gap_pct": ema_result["gap_pct"],
                "ema_death_cross": ema_result["death_cross"],
                "decline_score": decline_result["score"],
                "decline_confirmed": decline_result["is_decline"],
                "decline_suspected": decline_result["is_suspected"],
                "decline_structural": decline_result["is_structural"],
                "decline_reasons": "; ".join(decline_result["reasons"]),
            })

        demand_df = pd.DataFrame(demand_metrics)
        product_stats = product_stats.merge(demand_df, on="material_code", how="left")
        # 填充NaN
        fill_cols = [
            "growth_rate", "sales_acceleration", "consecutive_negative_months",
            "consecutive_positive_months", "cv",
            "trend_slope", "trend_normalized_slope", "trend_r_squared",
            "mk_p_value", "mk_sen_slope",
            "ema_short", "ema_long", "ema_gap_pct",
            "decline_score",
        ]
        for col in fill_cols:
            product_stats[col] = product_stats[col].fillna(0)
        for col in ["mk_direction"]:
            product_stats[col] = product_stats[col].fillna("no_trend")
        for col in ["ema_death_cross", "decline_confirmed", "decline_suspected", "decline_structural"]:
            product_stats[col] = product_stats[col].fillna(False)
        for col in ["decline_reasons"]:
            product_stats[col] = product_stats[col].fillna("")

        # ──────────────────────────────────────────────
        # 8. 加载配置阈值
        # ──────────────────────────────────────────────
        config = _get_config()
        plc_config = config.get("product_lifecycle", {})
        thresholds = plc_config.get("thresholds", {})
        growth_config = plc_config.get("growth", {})
        decline_config = plc_config.get("decline", {})
        new_product_config = plc_config.get("new_product", {})
        maturity_config = plc_config.get("maturity", {})

        growth_qty_min = thresholds.get("growth_qty_min", 5000)
        mature_qty_min = thresholds.get("mature_qty_min", 20000)
        stable_range = growth_config.get("stable_range", 0.10)
        strong_growth = growth_config.get("strong_growth", 0.10)
        decel_threshold = growth_config.get("deceleration_threshold", -0.05)

        trial_days = new_product_config.get("trial_days", 30)
        ramp_up_days = new_product_config.get("ramp_up_days", 60)
        stab_days = new_product_config.get("stabilization_days", 90)

        early_mature_months = maturity_config.get("early_months_max", 12)
        peak_cv_max = maturity_config.get("peak_cv_max", 0.30)
        late_penetration = maturity_config.get("late_penetration_min", 0.80)

        # ──────────────────────────────────────────────
        # 9. MECE阶段判定 — 优先级级联（出库量 + 上市时间 + 趋势置信度）
        # ──────────────────────────────────────────────
        def determine_plc_stage(row):
            cum_qty = row["cumulative_out_qty"]
            growth = row["growth_rate"]
            days = row.get("days_since_launch")

            # 级联判定（严格互斥，每条规则互不重叠）
            # 1. 累计出库 < 阈值 → 可能是导入期，但需结合上市时间
            if cum_qty < growth_qty_min:
                if days is not None and days > 90:
                    if cum_qty < 500:
                        return "导入期"
                    return "成熟期"
                return "导入期"

            # 2. 衰退期判定：趋势线置信度 ≥ 70分（三重信号融合）
            decline_confirmed = row.get("decline_confirmed", False)
            if decline_confirmed:
                return "衰退期"

            # 3. 累计出库 ≥ 20000 且增长稳定 → 成熟期
            if cum_qty >= mature_qty_min and abs(growth) <= stable_range:
                return "成熟期"

            # 4. 累计出库 ≥ 5000 且正增长 → 成长期
            if cum_qty >= growth_qty_min and growth > 0:
                return "成长期"

            # 5. 累计出库 ≥ 5000 且非正增长且未达成熟阈值 → 成熟期（平台过渡）
            return "成熟期"

        product_stats["plc_stage"] = product_stats.apply(determine_plc_stage, axis=1)

        # ──────────────────────────────────────────────
        # 10. 子阶段判定
        # ──────────────────────────────────────────────
        def determine_sub_stage(row):
            stage = row["plc_stage"]
            growth = row["growth_rate"]
            acceleration = row["sales_acceleration"]
            consec_neg = int(row["consecutive_negative_months"])
            cv = row["cv"]
            days = row.get("days_since_launch")
            months_active = int(row["months_active"])
            penetration = row["customer_penetration"]
            is_new = row.get("lifecycle_status") == "新品"

            if stage == "导入期":
                # 新品S曲线子阶段
                if days is not None:
                    if days <= trial_days:
                        return "试销期"
                    elif days <= ramp_up_days:
                        return "爬坡期"
                    elif days <= stab_days:
                        return "稳定期"
                # 非新品但累计出库低
                if months_active <= 3:
                    return "试销期"
                elif growth > 0:
                    return "爬坡期"
                return "稳定期"

            elif stage == "成长期":
                if acceleration > 0 and growth > strong_growth:
                    return "加速增长"
                elif acceleration < decel_threshold:
                    return "增长放缓"
                return "稳定增长"

            elif stage == "成熟期":
                if months_active <= early_mature_months:
                    return "早期成熟"
                elif cv < peak_cv_max and penetration < late_penetration:
                    return "峰值稳定"
                elif penetration >= late_penetration:
                    return "后期饱和"
                return "峰值稳定"

            elif stage == "衰退期":
                # 基于置信度分数 + 趋势斜率判定衰退严重程度
                decline_score = row.get("decline_score", 0)
                norm_slope = row.get("trend_normalized_slope", 0)
                if decline_score >= 90 or norm_slope < -10:
                    return "严重衰退"
                elif decline_score >= 70 or norm_slope < -5:
                    return "加速衰退"
                return "温和衰退"

            return "未知"

        product_stats["sub_stage"] = product_stats.apply(determine_sub_stage, axis=1)

        # ──────────────────────────────────────────────
        # 11. 静态行动建议（LLM建议通过独立API端点生成）
        # ──────────────────────────────────────────────
        STATIC_ADVICE = {
            "导入期": {
                "试销期": "观察市场反应，控制首批铺货量，收集终端反馈",
                "爬坡期": "验证增长趋势，适当增加库存，拓展销售渠道",
                "稳定期": "确认市场接受度，制定正式铺货计划",
            },
            "成长期": {
                "加速增长": "加大备货力度，拓展客户覆盖，抢占市场份额",
                "稳定增长": "维持增长节奏，优化供应链响应速度",
                "增长放缓": "分析放缓原因，调整促销策略，防止进入衰退",
            },
            "成熟期": {
                "早期成熟": "巩固市场地位，优化成本结构，建立品牌壁垒",
                "峰值稳定": "维持市场份额，关注竞品动态，控制运营成本",
                "后期饱和": "开发新场景/新渠道，考虑产品升级换代",
            },
            "衰退期": {
                "温和衰退": "减少采购量，针对性促销清库存，评估挽救方案",
                "加速衰退": "紧急清理库存，暂停补货，评估是否淘汰",
                "严重衰退": "立即停止采购，全力清库存，建议淘汰或重新定位",
            },
        }

        def get_static_advice(row):
            stage = row["plc_stage"]
            sub = row["sub_stage"]
            return STATIC_ADVICE.get(stage, {}).get(sub, "监控销售表现，评估市场潜力")

        product_stats["action_recommendation"] = product_stats.apply(get_static_advice, axis=1)

        # ──────────────────────────────────────────────
        # 12. 构建返回数据
        # ──────────────────────────────────────────────
        lifecycle_data = []
        for _, row in product_stats.iterrows():
            fsd = row.get("first_stock_in_date")
            lifecycle_data.append({
                "material_code": row["material_code"],
                "material_name": row["material_name"] if pd.notna(row["material_name"]) else "",
                "lifecycle_status": row.get("lifecycle_status") or "",
                "plc_stage": row["plc_stage"],
                "sub_stage": row["sub_stage"],
                "abc_class": row.get("abc_class") or "",
                "first_stock_in_date": str(_to_date(fsd)) if fsd and pd.notna(fsd) else "",
                "days_since_launch": int(row["days_since_launch"]) if row["days_since_launch"] is not None and pd.notna(row["days_since_launch"]) else None,
                "current_stock_qty": int(row["current_stock_qty"]) if pd.notna(row["current_stock_qty"]) else 0,
                "cumulative_out_qty": int(row["cumulative_out_qty"]) if pd.notna(row["cumulative_out_qty"]) else 0,
                "total_amount": float(row["total_amount"]) if pd.notna(row["total_amount"]) else 0,
                "total_qty": int(row["total_qty"]) if pd.notna(row["total_qty"]) else 0,
                "avg_monthly_qty": float(row["avg_monthly_qty"]) if pd.notna(row["avg_monthly_qty"]) else 0,
                "customer_count": int(row["customer_count"]) if pd.notna(row["customer_count"]) else 0,
                "customer_penetration": float(row["customer_penetration"]) if pd.notna(row["customer_penetration"]) else 0,
                "growth_rate": float(row["growth_rate"]) if pd.notna(row["growth_rate"]) else 0,
                "sales_acceleration": float(row["sales_acceleration"]) if pd.notna(row["sales_acceleration"]) else 0,
                "cv": float(row["cv"]) if pd.notna(row["cv"]) else 0,
                "consecutive_negative_months": int(row["consecutive_negative_months"]) if pd.notna(row["consecutive_negative_months"]) else 0,
                "consecutive_positive_months": int(row["consecutive_positive_months"]) if pd.notna(row["consecutive_positive_months"]) else 0,
                # 趋势分析指标
                "trend_normalized_slope": float(row["trend_normalized_slope"]) if pd.notna(row["trend_normalized_slope"]) else 0,
                "trend_r_squared": float(row["trend_r_squared"]) if pd.notna(row["trend_r_squared"]) else 0,
                "mk_direction": row.get("mk_direction") or "no_trend",
                "mk_p_value": float(row["mk_p_value"]) if pd.notna(row["mk_p_value"]) else 1.0,
                "ema_gap_pct": float(row["ema_gap_pct"]) if pd.notna(row["ema_gap_pct"]) else 0,
                "ema_death_cross": bool(row.get("ema_death_cross", False)),
                "decline_score": int(row["decline_score"]) if pd.notna(row["decline_score"]) else 0,
                "decline_confirmed": bool(row.get("decline_confirmed", False)),
                "decline_structural": bool(row.get("decline_structural", False)),
                "decline_reasons": row.get("decline_reasons") or "",
                "is_new_product": (row.get("lifecycle_status") == "新品"),
                "action_recommendation": row["action_recommendation"],
                "first_sale_month": str(row["first_sale_month"]) if pd.notna(row["first_sale_month"]) else "",
                "last_sale_month": str(row["last_sale_month"]) if pd.notna(row["last_sale_month"]) else "",
                "months_active": int(row["months_active"]) if pd.notna(row["months_active"]) else 0,
            })

        # 替换NaN
        lifecycle_data = [
            {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in row.items()}
            for row in lifecycle_data
        ]

        # ──────────────────────────────────────────────
        # 13. 汇总指标
        # ──────────────────────────────────────────────
        stage_counts = product_stats.groupby("plc_stage").size().to_dict()
        status_counts = product_stats.groupby("lifecycle_status").size().to_dict()

        metrics = {
            "total_products": len(product_stats),
            # PLC阶段分布
            "intro_count": stage_counts.get("导入期", 0),
            "growth_count": stage_counts.get("成长期", 0),
            "mature_count": stage_counts.get("成熟期", 0),
            "decline_count": stage_counts.get("衰退期", 0),
            # 数据库生命周期状态分布
            "new_product_count": status_counts.get("新品", 0),
            "sustained_count": status_counts.get("持续销售", 0),
            "one_time_count": status_counts.get("售完即止", 0),
            "relisted_count": status_counts.get("重新上架", 0),
            "discontinued_count": status_counts.get("淘汰", 0),
        }

        # 需求信号汇总
        demand_signals = {
            "avg_growth_rate": float(product_stats["growth_rate"].mean()) if not product_stats["growth_rate"].isna().all() else 0,
            "avg_cv": float(product_stats["cv"].mean()) if not product_stats["cv"].isna().all() else 0,
            "avg_penetration": float(product_stats["customer_penetration"].mean()) if not product_stats["customer_penetration"].isna().all() else 0,
        }

        PRODUCT_LIFECYCLE_DATA_POINTS.set(len(lifecycle_data))
        PRODUCT_LIFECYCLE_REQUESTS.labels(status="success").inc()
        return {"lifecycle_data": lifecycle_data, "metrics": metrics, "demand_signals": demand_signals}

    except Exception as e:
        logger.error(f"商品生命周期分析失败: {e}", exc_info=True)
        PRODUCT_LIFECYCLE_REQUESTS.labels(status="error").inc()
        return {"lifecycle_data": [], "metrics": {}, "demand_signals": {}, "error": str(e)}
    finally:
        duration = time.time() - start_time
        PRODUCT_LIFECYCLE_DURATION.observe(duration)


def get_customer_lifecycle(
    db: Session,
    months: int = 18,
    region: Optional[str] = None,
    manager: Optional[str] = None,
    channel: Optional[str] = None,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    客户生命周期分析

    基于RFM模型 + CLV，划分客户阶段：
    - 新客户: F=1 且 R < 30
    - 成长客户: F 递增趋势 且 R < 60
    - 成熟客户: F >= 3 且 R < 90 且 M高
    - 衰退客户: R > 90 但 F >= 2
    - 流失客户: R > 180

    Returns:
        包含customer_data(明细)、metrics(汇总)的字典
    """
    start_time = time.time()
    try:
        # 构建WHERE条件
        conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
        params = {}

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
        if channel:
            conditions.append("channel = :channel")
            params["channel"] = channel

        where_sql = " AND ".join(conditions)

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        params["start_date"] = start_date.strftime("%Y-%m-%d")
        params["end_date"] = end_date.strftime("%Y-%m-%d")
        conditions.append("doc_date BETWEEN :start_date AND :end_date")

        where_sql = " AND ".join(conditions)

        # 查询客户销售汇总
        sql = text(f"""
            SELECT customer,
                   SUM(tax_included_amount) AS total_amount,
                   SUM(sales_out_qty) AS total_qty,
                   COUNT(DISTINCT doc_no) AS order_count,
                   COUNT(DISTINCT material_code) AS category_count,
                   MIN(doc_date) AS first_purchase_date,
                   MAX(doc_date) AS last_purchase_date
            FROM rpt_sales_out_wide
            WHERE {where_sql}
            GROUP BY customer
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"customer_data": [], "metrics": {}}

        # 计算RFM
        today = end_date.date()
        df["recency"] = df["last_purchase_date"].apply(
            lambda x: (today - _to_date(x)).days if _to_date(x) else 0
        )
        df["frequency"] = df["order_count"]
        df["monetary"] = df["total_amount"]
        df["avg_order_value"] = df["monetary"] / df["frequency"].replace(0, 1)

        # 获取配置参数
        config = _get_config()
        cl_config = config.get("customer_lifecycle", {})
        rfm_bins = cl_config.get("rfm_bins", {})
        stage_thresholds = cl_config.get("stage_thresholds", {})
        clv_config = cl_config.get("clv", {})

        recency_bins = rfm_bins.get("recency", [30, 90, 365])
        frequency_bins = rfm_bins.get("frequency", [2, 5])
        monetary_bins = rfm_bins.get("monetary", [10000, 50000])
        avg_lifespan_months = clv_config.get("avg_lifespan_months", 24)

        # RFM分箱 (1-3分)
        # R: 最近购买天数越少分越高 → [-1,30]=3, (30,90]=2, (90,365]=1, (365+]=1
        r_bins = [-1] + recency_bins + [float('inf')]
        r_labels = [3, 2, 1, 1][: len(r_bins) - 1]
        df["r_score"] = pd.cut(df["recency"], bins=r_bins, labels=r_labels, ordered=False).astype(float).fillna(1)
        # F: 购买次数越多分越高
        f_bins = [0] + frequency_bins + [float('inf')]
        f_labels = list(range(1, len(f_bins)))  # [1,2,3]
        df["f_score"] = pd.cut(df["frequency"].clip(lower=1), bins=f_bins, labels=f_labels, ordered=False).astype(float).fillna(1)
        # M: 累计金额越高分越高
        m_bins = [-1] + monetary_bins + [float('inf')]
        m_labels = list(range(1, len(m_bins)))  # [1,2,3]
        df["m_score"] = pd.cut(df["monetary"], bins=m_bins, labels=m_labels, ordered=False).astype(float).fillna(1)

        # CLV估算 (简化公式: 平均订单值 * 月均频次 * 预期生命周期月数)
        df["clv"] = (df["avg_order_value"] * (df["frequency"] / max(months, 1)) * avg_lifespan_months).round(2)

        # 获取阶段判定阈值
        new_r_max = stage_thresholds.get("new_r_max", 30)
        new_f_eq = stage_thresholds.get("new_f_eq", 1)
        growth_r_max = stage_thresholds.get("growth_r_max", 60)
        decline_r_min = stage_thresholds.get("decline_r_min", 90)
        decline_f_min = stage_thresholds.get("decline_f_min", 2)
        churn_r_min = stage_thresholds.get("churn_r_min", 180)

        # 阶段判定
        def determine_stage(row):
            r = row["recency"]
            f = row["frequency"]
            m = row["monetary"]

            if f == new_f_eq and r < new_r_max:
                return "新客户"
            elif r > churn_r_min:
                return "流失客户"
            elif r > decline_r_min and f >= decline_f_min:
                return "衰退客户"
            elif f >= 3 and r < 90 and m > 30000:
                return "成熟客户"
            elif f >= 2 and r < growth_r_max:
                return "成长客户"
            return "一般客户"

        df["stage"] = df.apply(determine_stage, axis=1)

        # ===== 客户阶段 × 品类 交叉分析 =====
        cross_tab_data = {"stages": [], "categories": [], "customer_matrix": [], "amount_matrix": []}
        try:
            # 查询每个客户的品类销售分布
            cat_conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
            cat_params = {}
            if allowed_regions:
                ph = [f":car{i}" for i in range(len(allowed_regions))]
                cat_conditions.append(f"region IN ({','.join(ph)})")
                for i, r in enumerate(allowed_regions):
                    cat_params[f"car{i}"] = r
            if region:
                cat_conditions.append("region = :region")
                cat_params["region"] = region
            if manager:
                cat_conditions.append("account_manager = :manager")
                cat_params["manager"] = manager
            if channel:
                cat_conditions.append("channel = :channel")
                cat_params["channel"] = channel
            cat_conditions.append("doc_date BETWEEN :start_date AND :end_date")
            cat_params["start_date"] = params["start_date"]
            cat_params["end_date"] = params["end_date"]

            cat_where = " AND ".join(cat_conditions)
            sql_cat = text(f"""
                SELECT customer, category, SUM(tax_included_amount) AS amount
                FROM rpt_sales_out_wide
                WHERE {cat_where}
                GROUP BY customer, category
            """)
            df_cat = pd.read_sql(sql_cat, db.bind, params=cat_params)

            if not df_cat.empty and not df.empty:
                # 品类 Top 8 + 其他
                TOP_N = 8
                cat_totals = df_cat.groupby("category")["amount"].sum().sort_values(ascending=False)
                top_cats = cat_totals.head(TOP_N).index.tolist()
                df_cat["category_display"] = df_cat["category"].apply(
                    lambda x: x if x in top_cats else "其他"
                )
                # 合并 "其他" 类别
                df_cat_agg = df_cat.groupby(["customer", "category_display"]).agg(
                    amount=("amount", "sum")
                ).reset_index()

                # merge 阶段信息
                stage_map = df[["customer", "stage"]].drop_duplicates()
                df_cross = df_cat_agg.merge(stage_map, on="customer", how="inner")

                # 构建矩阵
                all_stages = ["新客户", "成长客户", "成熟客户", "衰退客户", "流失客户", "一般客户"]
                present_stages = [s for s in all_stages if s in df_cross["stage"].values]
                # 排序品类：Top N 按金额降序 + "其他" 在最后
                present_cats = [c for c in top_cats if c in df_cross["category_display"].values]
                if "其他" in df_cross["category_display"].values:
                    present_cats.append("其他")

                cust_matrix = []
                amt_matrix = []
                for stage in present_stages:
                    cust_row = []
                    amt_row = []
                    for cat in present_cats:
                        subset = df_cross[(df_cross["stage"] == stage) & (df_cross["category_display"] == cat)]
                        cust_row.append(int(subset["customer"].nunique()) if not subset.empty else 0)
                        amt_row.append(float(subset["amount"].sum()) if not subset.empty else 0)
                    cust_matrix.append(cust_row)
                    amt_matrix.append(amt_row)

                cross_tab_data = {
                    "stages": present_stages,
                    "categories": present_cats,
                    "customer_matrix": cust_matrix,
                    "amount_matrix": amt_matrix,
                }
        except Exception as ct_err:
            logger.warning(f"交叉分析计算失败（不影响主流程）: {ct_err}")

        # 构建返回数据
        customer_data = []
        for _, row in df.iterrows():
            customer_data.append({
                "customer": row["customer"] if pd.notna(row["customer"]) else "",
                "r": int(row["recency"]) if pd.notna(row["recency"]) else 0,
                "f": int(row["frequency"]) if pd.notna(row["frequency"]) else 0,
                "m": float(row["monetary"]) if pd.notna(row["monetary"]) else 0,
                "r_score": float(row["r_score"]) if pd.notna(row["r_score"]) else 1,
                "f_score": float(row["f_score"]) if pd.notna(row["f_score"]) else 1,
                "m_score": float(row["m_score"]) if pd.notna(row["m_score"]) else 1,
                "stage": row["stage"],
                "clv": float(row["clv"]) if pd.notna(row["clv"]) else 0,
                "avg_order_value": float(row["avg_order_value"]) if pd.notna(row["avg_order_value"]) else 0,
                "category_count": int(row["category_count"]) if pd.notna(row["category_count"]) else 0,
                "first_purchase_date": str(row["first_purchase_date"])[:10] if pd.notna(row["first_purchase_date"]) else "",
                "last_purchase_date": str(row["last_purchase_date"])[:10] if pd.notna(row["last_purchase_date"]) else "",
                "total_qty": int(row["total_qty"]) if pd.notna(row["total_qty"]) else 0,
            })

        # 替换NaN
        customer_data = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in row.items()} for row in customer_data]

        # 汇总指标
        stage_counts = df.groupby("stage").size().to_dict()
        avg_clv = df["clv"].mean() if not df["clv"].isna().all() else 0
        metrics = {
            "total_customers": len(df),
            "new_count": stage_counts.get("新客户", 0),
            "growth_count": stage_counts.get("成长客户", 0),
            "mature_count": stage_counts.get("成熟客户", 0),
            "decline_count": stage_counts.get("衰退客户", 0),
            "churned_count": stage_counts.get("流失客户", 0),
            "general_count": stage_counts.get("一般客户", 0),
            "avg_clv": float(avg_clv),
        }

        CUSTOMER_LIFECYCLE_DATA_POINTS.set(len(customer_data))
        CUSTOMER_LIFECYCLE_REQUESTS.labels(status="success").inc()
        return {"customer_data": customer_data, "metrics": metrics, "cross_tab": cross_tab_data}

    except Exception as e:
        logger.error(f"客户生命周期分析失败: {e}", exc_info=True)
        CUSTOMER_LIFECYCLE_REQUESTS.labels(status="error").inc()
        return {"customer_data": [], "metrics": {}, "cross_tab": {"stages": [], "categories": [], "customer_matrix": [], "amount_matrix": []}, "error": str(e)}
    finally:
        duration = time.time() - start_time
        CUSTOMER_LIFECYCLE_DURATION.observe(duration)


def get_product_cluster(
    db: Session,
    months: int = 18,
    region: Optional[str] = None,
    n_clusters: int = 4,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    商品聚类分析

    基于K-Means聚类，特征包括销售额、销量、频次、客户覆盖、波动率
    结果映射到BCG矩阵风格标签：
    - 明星商品（高金额+高增长）
    - 现金牛（高金额+稳定）
    - 问题商品（高波动+低渗透）
    - 瘦狗商品（低金额+低频次）

    Returns:
        包含cluster_data(明细)、cluster_summary(聚类汇总)、metrics(汇总)的字典
    """
    start_time = time.time()
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans

        # 构建WHERE条件
        conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
        params = {}

        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("region = :region")
            params["region"] = region

        where_sql = " AND ".join(conditions)

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        params["start_date"] = start_date.strftime("%Y-%m-%d")
        params["end_date"] = end_date.strftime("%Y-%m-%d")
        conditions.append("doc_date BETWEEN :start_date AND :end_date")

        where_sql = " AND ".join(conditions)

        # 查询月度销售数据用于特征工程
        sql = text(f"""
            SELECT material_code, material_name,
                   DATE_FORMAT(doc_date, '%Y-%m') AS sale_month,
                   SUM(tax_included_amount) AS monthly_amount,
                   SUM(sales_out_qty) AS monthly_qty,
                   COUNT(DISTINCT customer) AS customer_count
            FROM rpt_sales_out_wide
            WHERE {where_sql}
            GROUP BY material_code, material_name, DATE_FORMAT(doc_date, '%Y-%m')
            ORDER BY material_code, sale_month
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"cluster_data": [], "cluster_summary": [], "metrics": {}}

        # 特征工程
        product_features = df.groupby(["material_code", "material_name"]).agg(
            total_amount=("monthly_amount", "sum"),
            total_qty=("monthly_qty", "sum"),
            avg_monthly_qty=("monthly_qty", "mean"),
            customer_count=("customer_count", "mean"),
            months_active=("sale_month", "count"),
        ).reset_index()

        # 波动率（月销量标准差/月均销量）
        volatility_data = df.groupby("material_code").agg(
            std_monthly_qty=("monthly_qty", "std"),
            mean_monthly_qty=("monthly_qty", "mean"),
        ).reset_index()
        volatility_data["volatility"] = (volatility_data["std_monthly_qty"] / volatility_data["mean_monthly_qty"].replace(0, 1)).fillna(0)
        product_features = product_features.merge(volatility_data[["material_code", "volatility"]], on="material_code", how="left")

        # 计算增长率（首尾月对比）
        growth_data = []
        for material_code in df["material_code"].unique():
            mat_df = df[df["material_code"] == material_code].sort_values("sale_month")
            if len(mat_df) >= 2:
                first_amt = mat_df.iloc[0]["monthly_amount"]
                last_amt = mat_df.iloc[-1]["monthly_amount"]
                if first_amt > 0:
                    growth_rate = (last_amt - first_amt) / first_amt
                else:
                    growth_rate = 0
            else:
                growth_rate = 0
            growth_data.append({"material_code": material_code, "growth_rate": growth_rate})

        growth_df = pd.DataFrame(growth_data)
        product_features = product_features.merge(growth_df, on="material_code", how="left")

        # 平均单价
        product_features["avg_price"] = (product_features["total_amount"] / product_features["total_qty"].replace(0, 1)).fillna(0)

        # 渗透率
        total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
        product_features["penetration"] = product_features["months_active"] / total_months

        # 准备聚类特征
        features_for_clustering = ["total_amount", "total_qty", "avg_monthly_qty", "customer_count", "avg_price", "volatility"]
        X = product_features[features_for_clustering].fillna(0).values

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans聚类
        n_clusters = min(n_clusters, len(product_features))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        product_features["cluster_id"] = kmeans.fit_predict(X_scaled)

        # 按聚类中心排序并映射标签 - 多维度BCG矩阵风格
        cluster_centers = pd.DataFrame(kmeans.cluster_centers_, columns=features_for_clustering)
        cluster_centers["cluster_id"] = range(n_clusters)

        # 计算每个聚类的平均增长率（从产品特征汇总）
        cluster_growth = product_features.groupby("cluster_id").agg(
            avg_growth_rate=("growth_rate", "mean")
        ).reset_index()
        cluster_centers = cluster_centers.merge(cluster_growth, on="cluster_id", how="left")

        # 金额和增长率中位数用于分类
        amount_median = cluster_centers["total_amount"].median()
        growth_median = cluster_centers["avg_growth_rate"].median()

        # 获取配置中的聚类标签
        config = _get_config()
        product_cluster_config = config.get("product_cluster", {})
        default_labels = ["明星商品", "现金牛", "问题商品", "瘦狗商品"]
        cluster_labels = product_cluster_config.get("labels", default_labels)

        # 多维度标签映射：基于金额和增长两维度
        # 明星: 高金额+高增长; 现金牛: 高金额+低增长; 问题: 低金额+高增长; 瘦狗: 低金额+低增长
        label_mapping = {}
        for _, center_row in cluster_centers.iterrows():
            cid = center_row["cluster_id"]
            amount = center_row["total_amount"]
            growth = center_row.get("avg_growth_rate", 0)

            if amount >= amount_median and growth >= growth_median:
                label = cluster_labels[0] if len(cluster_labels) > 0 else "明星商品"  # 明星
            elif amount >= amount_median and growth < growth_median:
                label = cluster_labels[1] if len(cluster_labels) > 1 else "现金牛"  # 现金牛
            elif amount < amount_median and growth >= growth_median:
                label = cluster_labels[2] if len(cluster_labels) > 2 else "问题商品"  # 问题
            else:
                label = cluster_labels[3] if len(cluster_labels) > 3 else "瘦狗商品"  # 瘦狗

            label_mapping[cid] = label

        product_features["cluster_label"] = product_features["cluster_id"].map(label_mapping).fillna("一般商品")

        # 聚类汇总
        cluster_summary = []
        for cluster_id in range(n_clusters):
            cluster_data = product_features[product_features["cluster_id"] == cluster_id]
            cluster_summary.append({
                "cluster_id": int(cluster_id),
                "cluster_label": label_mapping.get(cluster_id, "一般商品"),
                "count": len(cluster_data),
                "avg_total_amount": float(cluster_data["total_amount"].mean()) if len(cluster_data) > 0 else 0,
                "avg_total_qty": float(cluster_data["total_qty"].mean()) if len(cluster_data) > 0 else 0,
                "avg_volatility": float(cluster_data["volatility"].mean()) if len(cluster_data) > 0 else 0,
                "avg_penetration": float(cluster_data["penetration"].mean()) if len(cluster_data) > 0 else 0,
                "avg_growth_rate": float(cluster_data["growth_rate"].mean()) if len(cluster_data) > 0 else 0,
            })

        # 聚类特征雷达图数据
        radar_data = []
        for _, center in cluster_centers.iterrows():
            # 标准化到0-1范围用于雷达图展示
            max_vals = X_scaled.max(axis=0)
            min_vals = X_scaled.min(axis=0)
            range_vals = max_vals - min_vals
            range_vals[range_vals == 0] = 1
            normalized = (center[features_for_clustering].values - min_vals) / range_vals
            radar_data.append({
                "cluster_id": int(center["cluster_id"]),
                "cluster_label": label_mapping.get(int(center["cluster_id"]), "一般商品"),
                "values": normalized.tolist(),
            })

        # 构建返回数据
        cluster_data = []
        for _, row in product_features.iterrows():
            cluster_data.append({
                "material_code": row["material_code"],
                "material_name": row["material_name"] if pd.notna(row["material_name"]) else "",
                "cluster_id": int(row["cluster_id"]) if pd.notna(row["cluster_id"]) else 0,
                "cluster_label": row["cluster_label"],
                "total_amount": float(row["total_amount"]) if pd.notna(row["total_amount"]) else 0,
                "total_qty": int(row["total_qty"]) if pd.notna(row["total_qty"]) else 0,
                "avg_monthly_qty": float(row["avg_monthly_qty"]) if pd.notna(row["avg_monthly_qty"]) else 0,
                "customer_count": int(row["customer_count"]) if pd.notna(row["customer_count"]) else 0,
                "avg_price": float(row["avg_price"]) if pd.notna(row["avg_price"]) else 0,
                "volatility": float(row["volatility"]) if pd.notna(row["volatility"]) else 0,
                "penetration": float(row["penetration"]) if pd.notna(row["penetration"]) else 0,
                "growth_rate": float(row["growth_rate"]) if pd.notna(row["growth_rate"]) else 0,
            })

        # 替换NaN
        cluster_data = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in row.items()} for row in cluster_data]

        metrics = {
            "total_skus": len(product_features),
            "n_clusters": n_clusters,
            "max_cluster_size": int(product_features.groupby("cluster_id").size().max()),
        }

        PRODUCT_CLUSTER_DATA_POINTS.set(len(cluster_data))
        PRODUCT_CLUSTER_REQUESTS.labels(status="success").inc()
        return {
            "cluster_data": cluster_data,
            "cluster_summary": cluster_summary,
            "radar_data": radar_data,
            "feature_names": ["销售额", "销量", "月均销量", "客户数", "平均单价", "波动率"],
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"商品聚类分析失败: {e}", exc_info=True)
        PRODUCT_CLUSTER_REQUESTS.labels(status="error").inc()
        return {"cluster_data": [], "cluster_summary": [], "radar_data": [], "metrics": {}, "error": str(e)}
    finally:
        duration = time.time() - start_time
        PRODUCT_CLUSTER_DURATION.observe(duration)


def get_customer_cluster(
    db: Session,
    months: int = 18,
    region: Optional[str] = None,
    n_clusters: int = 5,
    allowed_regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    客户聚类分析

    基于RFM特征的K-Means聚类
    标签: VIP客户、高价值客户、潜力客户、一般客户、流失风险客户

    Returns:
        包含cluster_data(明细)、cluster_summary(聚类汇总)、radar_data(RFM雷达图)的字典
    """
    start_time = time.time()
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans

        # 构建WHERE条件
        conditions = ["doc_date IS NOT NULL", "tax_included_amount > 0"]
        params = {}

        if allowed_regions:
            placeholders = [f":allowed_region{i}" for i in range(len(allowed_regions))]
            conditions.append(f"region IN ({','.join(placeholders)})")
            for i, r in enumerate(allowed_regions):
                params[f"allowed_region{i}"] = r

        if region:
            conditions.append("region = :region")
            params["region"] = region

        where_sql = " AND ".join(conditions)

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        params["start_date"] = start_date.strftime("%Y-%m-%d")
        params["end_date"] = end_date.strftime("%Y-%m-%d")
        conditions.append("doc_date BETWEEN :start_date AND :end_date")

        where_sql = " AND ".join(conditions)

        # 查询客户销售汇总
        sql = text(f"""
            SELECT customer,
                   region, channel,
                   SUM(tax_included_amount) AS total_amount,
                   SUM(sales_out_qty) AS total_qty,
                   COUNT(DISTINCT doc_no) AS order_count,
                   COUNT(DISTINCT material_code) AS category_count,
                   MAX(doc_date) AS last_purchase_date
            FROM rpt_sales_out_wide
            WHERE {where_sql}
            GROUP BY customer, region, channel
        """)
        df = pd.read_sql(sql, db.bind, params=params)

        if df.empty:
            return {"cluster_data": [], "cluster_summary": [], "radar_data": [], "metrics": {}}

        # 计算RFM
        today = end_date.date()
        df["recency"] = df["last_purchase_date"].apply(
            lambda x: (today - _to_date(x)).days if _to_date(x) else 0
        )
        df["frequency"] = df["order_count"]
        df["monetary"] = df["total_amount"]
        df["avg_order_value"] = df["monetary"] / df["frequency"].replace(0, 1)

        # 准备聚类特征
        features_for_clustering = ["recency", "frequency", "monetary", "avg_order_value", "category_count"]
        X = df[features_for_clustering].fillna(0).values

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans聚类
        n_clusters = min(n_clusters, len(df))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["cluster_id"] = kmeans.fit_predict(X_scaled)

        # 按monetary排序，确定VIP/高价值/潜力/一般/流失风险
        cluster_centers = pd.DataFrame(kmeans.cluster_centers_, columns=features_for_clustering)
        cluster_centers["cluster_id"] = range(n_clusters)
        cluster_centers = cluster_centers.sort_values("monetary", ascending=False).reset_index(drop=True)

        # 获取配置中的聚类标签
        config = _get_config()
        customer_cluster_config = config.get("customer_cluster", {})
        default_labels = ["VIP客户", "高价值客户", "潜力客户", "一般客户", "流失风险客户"]
        cluster_labels = customer_cluster_config.get("labels", default_labels)

        # 标签映射（按M值从高到低）
        label_map = {}
        for i, cid in enumerate(cluster_centers["cluster_id"].values):
            if i < len(cluster_labels):
                label_map[cid] = cluster_labels[i]
            else:
                label_map[cid] = "一般客户"

        df["cluster_label"] = df["cluster_id"].map(label_map).fillna("一般客户")

        # 聚类汇总
        cluster_summary = []
        for cluster_id in range(n_clusters):
            cluster_subset = df[df["cluster_id"] == cluster_id]
            cluster_summary.append({
                "cluster_id": int(cluster_id),
                "cluster_label": label_map.get(cluster_id, "一般客户"),
                "count": len(cluster_subset),
                "avg_recency": float(cluster_subset["recency"].mean()) if len(cluster_subset) > 0 else 0,
                "avg_frequency": float(cluster_subset["frequency"].mean()) if len(cluster_subset) > 0 else 0,
                "avg_monetary": float(cluster_subset["monetary"].mean()) if len(cluster_subset) > 0 else 0,
            })

        # RFM雷达图数据（标准化到0-1）
        radar_data = []
        for _, center in cluster_centers.iterrows():
            max_vals = X_scaled.max(axis=0)
            min_vals = X_scaled.min(axis=0)
            range_vals = max_vals - min_vals
            range_vals[range_vals == 0] = 1
            normalized = (center[features_for_clustering].values - min_vals) / range_vals
            radar_data.append({
                "cluster_id": int(center["cluster_id"]),
                "cluster_label": label_map.get(int(center["cluster_id"]), "一般客户"),
                "values": normalized.tolist(),
            })

        # 构建返回数据
        cluster_data = []
        for _, row in df.iterrows():
            cluster_data.append({
                "customer": row["customer"] if pd.notna(row["customer"]) else "",
                "region": row["region"] if pd.notna(row["region"]) else "",
                "channel": row["channel"] if pd.notna(row["channel"]) else "",
                "cluster_id": int(row["cluster_id"]) if pd.notna(row["cluster_id"]) else 0,
                "cluster_label": row["cluster_label"],
                "r": int(row["recency"]) if pd.notna(row["recency"]) else 0,
                "f": int(row["frequency"]) if pd.notna(row["frequency"]) else 0,
                "m": float(row["monetary"]) if pd.notna(row["monetary"]) else 0,
                "avg_order_value": float(row["avg_order_value"]) if pd.notna(row["avg_order_value"]) else 0,
                "category_count": int(row["category_count"]) if pd.notna(row["category_count"]) else 0,
                "total_qty": int(row["total_qty"]) if pd.notna(row["total_qty"]) else 0,
            })

        # 替换NaN
        cluster_data = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in row.items()} for row in cluster_data]

        metrics = {
            "total_customers": len(df),
            "n_clusters": n_clusters,
        }

        CUSTOMER_CLUSTER_DATA_POINTS.set(len(cluster_data))
        CUSTOMER_CLUSTER_REQUESTS.labels(status="success").inc()
        return {
            "cluster_data": cluster_data,
            "cluster_summary": cluster_summary,
            "radar_data": radar_data,
            "feature_names": ["最近购买(R)", "购买频次(F)", "累计金额(M)", "客单价", "品类数"],
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"客户聚类分析失败: {e}", exc_info=True)
        CUSTOMER_CLUSTER_REQUESTS.labels(status="error").inc()
        return {"cluster_data": [], "cluster_summary": [], "radar_data": [], "metrics": {}, "error": str(e)}
    finally:
        duration = time.time() - start_time
        CUSTOMER_CLUSTER_DURATION.observe(duration)
