"""
Mock 数据 fixtures — 用于开发/演示环境。

原项目使用 RPA 抓取真实 ERP 数据(销售出库/采购单/库存/请购单),
本仓已脱敏,所有数据替换为虚构数据。

使用:
    from channel_analytics.data.fixtures import (
        load_sales_out_mock,
        load_purchase_order_mock,
        load_stock_in_mock,
        load_purchase_req_mock,
        load_stock_current_mock,
    )

    df = load_sales_out_mock(months=3)

数据结构对齐原仓 STG 表:
- 销售出库: stg_sales_out (24 列)
- 采购单: stg_purchase_order (13 列)
- 入库单: stg_stock_in (19 列)
- 请购单: stg_purchase_req (14 列)
- 库存: stg_stock_current (13 列)

所有品牌名都是占位(Brand A-L),不包含真实客户/品牌信息。
"""
from __future__ import annotations

import io
from datetime import date, datetime, timedelta
from typing import List

import pandas as pd
import numpy as np


# 12 个自营品牌占位
BRANDS = [
    "Brand A", "Brand B", "Brand C", "Brand D", "Brand E", "Brand F",
    "Brand G", "Brand H", "Brand I", "Brand J", "Brand K", "Brand L",
]

CHANNELS = ["批发", "零售", "电商", "直营"]
WAREHOUSES = ["WH-001-主仓", "WH-002-次仓", "WH-003-电商仓"]
CUSTOMERS = [f"客户{i:03d}" for i in range(1, 51)]  # 50 个虚拟客户
MATERIALS = [
    f"SKU-{i:04d}" for i in range(1, 31)
]  # 30 个虚拟 SKU
MATERIAL_NAMES = [
    f"物料-{i:02d}" for i in range(1, 31)
]
ABC_CLASSES = ["引流品", "主推品", "利润品"]
LIFECYCLE_STATUSES = ["新品", "持续销售", "售完即止", "重新上架", "淘汰"]
CUST_STATUSES = ["合作中", "已暂停", "已终止"]


def _rand_dates(n: int, start: date, end: date) -> List[date]:
    """生成 n 个 [start, end] 之间的随机日期"""
    days = (end - start).days
    return [start + timedelta(days=int(x)) for x in np.random.randint(0, days + 1, n)]


def _brand_choice(n: int) -> List[str]:
    """随机选品牌(80% 自营 12 个 + 20% 未知)"""
    p = [1.0 / 12] * 12
    result = np.random.choice(BRANDS, n, p=p)
    # 注入一些"非自营"
    non_self = np.random.choice(n, max(1, n // 5), replace=False)
    for i in non_self:
        result[i] = f"非自营-{i:02d}"
    return list(result)


def load_sales_out_mock(months: int = 3, n: int = 2000) -> pd.DataFrame:
    """
    销售出库单 mock 数据
    字段: 24 列, 对齐 stg_sales_out 表
    """
    end = date(2026, 6, 10)
    start = end - timedelta(days=months * 30)
    doc_dates = _rand_dates(n, start, end)
    audit_dates = [d + timedelta(days=int(x)) for d, x in zip(doc_dates, np.random.randint(0, 5, n))]

    df = pd.DataFrame({
        "doc_date": doc_dates,
        "doc_no": [f"SO-{i:08d}" for i in range(1, n + 1)],
        "source_tx_type": np.random.choice(["01", "02", "03", "04"], n),
        "tx_type_name": np.random.choice(["正常出库", "退货出库", "调拨出库", "报损出库"], n),
        "customer": np.random.choice(CUSTOMERS, n),
        "customer_class": np.random.choice(["A类", "B类", "C类"], n),
        "region_manager": np.random.choice([f"大区经理{i}" for i in range(1, 6)], n),
        "warehouse": np.random.choice(WAREHOUSES, n),
        "material_code": np.random.choice(MATERIALS, n),
        "material_name": np.random.choice(MATERIAL_NAMES, n),
        "brand": _brand_choice(n),
        "tax_included_amount": np.round(np.random.uniform(100, 50000, n), 2),
        "batch_no": [f"B{str(d).replace('-', '')}-{i:04d}" for i, d in enumerate(doc_dates, 1)],
        "shipping_channel": np.random.choice(CHANNELS, n),
        "audit_date": audit_dates,
        "creator": np.random.choice([f"员工{i}" for i in range(1, 11)], n),
        "sales_out_qty": np.random.randint(1, 100, n),
        "dispatch_qty": np.random.randint(1, 100, n),
        "invoiced_qty": np.random.randint(0, 100, n),
        "tx_type": np.random.choice(["XSCK01", "XSCK02", "XSCK03"], n),
        "audit_time": [datetime.combine(d, datetime.min.time()) + timedelta(hours=int(h))
                       for d, h in zip(audit_dates, np.random.randint(8, 20, n))],
        "remark": np.random.choice(["", "正常", "促销", "样品", ""], n),
        "source_doc_tx_type": np.random.choice(["", "DDCK01", "DDCK02"], n),
        "entry_method": np.random.choice(["普通", "调拨", ""], n),
        "tax_included_unit_price": np.round(np.random.uniform(10, 500, n), 2),
        "source_doc_no": [f"SRC-{i:08d}" if i % 3 == 0 else "" for i in range(1, n + 1)],
    })
    return df


def load_purchase_order_mock(months: int = 3, n: int = 500) -> pd.DataFrame:
    """
    采购单 mock 数据
    字段: 13 列, 对齐 stg_purchase_order 表
    """
    end = date(2026, 6, 10)
    start = end - timedelta(days=months * 30)
    delivery_dates = _rand_dates(n, start, end)

    df = pd.DataFrame({
        "delivery_date": delivery_dates,
        "order_no": [f"PO-{i:08d}" for i in range(1, n + 1)],
        "brand": _brand_choice(n),
        "material_code": np.random.choice(MATERIALS, n),
        "material_name": np.random.choice(MATERIAL_NAMES, n),
        "factory_delivery_qty": np.random.randint(10, 1000, n),
        "batch_no": [f"P{str(d).replace('-', '')}-{i:04d}" for i, d in enumerate(delivery_dates, 1)],
        "expiry_date": [d + timedelta(days=int(x)) for d, x in zip(delivery_dates, np.random.randint(180, 720, n))],
        "brand_sales_no": [f"BS-{i:08d}" for i in range(1, n + 1)],
        "remark": np.random.choice(["", "正常", "加急"], n),
        "pickup_qty": np.random.randint(0, 1000, n),
        "production_date": [d - timedelta(days=int(x)) for d, x in zip(delivery_dates, np.random.randint(30, 180, n))],
        "is_billed": np.random.choice([True, False], n, p=[0.7, 0.3]),
    })
    return df


def load_stock_in_mock(months: int = 3, n: int = 800) -> pd.DataFrame:
    """
    入库单 mock 数据
    字段: 19 列, 对齐 stg_stock_in 表
    """
    end = date(2026, 6, 10)
    start = end - timedelta(days=months * 30)
    stock_in_dates = _rand_dates(n, start, end)
    audit_dates = [d + timedelta(days=int(x)) for d, x in zip(stock_in_dates, np.random.randint(0, 3, n))]

    df = pd.DataFrame({
        "brand_sales_no": [f"BS-{i:08d}" for i in range(1, n + 1)],
        "stock_in_date": stock_in_dates,
        "doc_no": [f"RK-{i:08d}" for i in range(1, n + 1)],
        "order_tx_type": np.random.choice(["01", "02", "03"], n),
        "audit_date": audit_dates,
        "material_code": np.random.choice(MATERIALS, n),
        "material_name": np.random.choice(MATERIAL_NAMES, n),
        "receivable_qty": np.random.randint(10, 1000, n),
        "batch_no": [f"R{str(d).replace('-', '')}-{i:04d}" for i, d in enumerate(stock_in_dates, 1)],
        "warehouse": np.random.choice(WAREHOUSES, n),
        "doc_status": np.random.choice(["已审核", "未审核"], n, p=[0.85, 0.15]),
        "expiry_date": [d + timedelta(days=int(x)) for d, x in zip(stock_in_dates, np.random.randint(180, 720, n))],
        "model": np.random.choice(["A型", "B型", "C型", "D型"], n),
        "stock_in_qty": np.random.randint(10, 1000, n),
        "remark": np.random.choice(["", "正常", "破损"], n),
        "logistics_no": [f"LG{str(d).replace('-', '')}{i:04d}" for i, d in enumerate(stock_in_dates, 1)],
        "logistics_company": np.random.choice(["Carrier A", "Carrier B", "Carrier C", "Carrier D"], n),
        "supplier_material_code": [f"SUP-{i:06d}" for i in range(1, n + 1)],
        "supplier_material_name": [f"供应商物料-{i:02d}" for i in range(1, n + 1)],
    })
    return df


def load_purchase_req_mock(months: int = 3, n: int = 300) -> pd.DataFrame:
    """
    请购单 mock 数据
    字段: 14 列, 对齐 stg_purchase_req 表
    """
    end = date(2026, 6, 10)
    start = end - timedelta(days=months * 30)
    order_dates = _rand_dates(n, start, end)

    df = pd.DataFrame({
        "order_date": order_dates,
        "order_no": [f"PR-{i:08d}" for i in range(1, n + 1)],
        "channel_contact": np.random.choice([f"对接人{i}" for i in range(1, 8)], n),
        "delivery_cycle": np.random.choice([7, 15, 30, 45], n),
        "brand": _brand_choice(n),
        "promotion_tags": np.random.choice(["", "618", "双11", "新品", "限时"], n),
        "material_code": np.random.choice(MATERIALS, n),
        "material_name": np.random.choice(MATERIAL_NAMES, n),
        "channel": np.random.choice(CHANNELS, n),
        "order_qty": np.random.randint(10, 500, n),
        "order_remark": np.random.choice(["", "加急", "正常", "样品"], n),
        "expected_delivery_date": [d + timedelta(days=int(x)) for d, x in zip(order_dates, np.random.randint(7, 45, n))],
        "actual_manual_stock_qty": np.random.choice([0, np.random.randint(0, 500)], n),
        "special_remark": np.random.choice(["", "", "", "需特殊处理"], n),
        "is_delivered": np.random.choice([True, False], n, p=[0.6, 0.4]),
    })
    return df


def load_stock_current_mock(n: int = 1500) -> pd.DataFrame:
    """
    现存量 mock 数据
    字段: 13 列, 对齐 stg_stock_current 表
    """
    production_dates = _rand_dates(n, date(2024, 1, 1), date(2026, 6, 1))

    df = pd.DataFrame({
        "warehouse": np.random.choice(WAREHOUSES, n),
        "brand": _brand_choice(n),
        "material_code": np.random.choice(MATERIALS, n),
        "material_name": np.random.choice(MATERIAL_NAMES, n),
        "batch_no": [f"B{str(d).replace('-', '')}-{i:04d}" for i, d in enumerate(production_dates, 1)],
        "production_date": production_dates,
        "expiry_date": [d + timedelta(days=int(x)) for d, x in zip(production_dates, np.random.randint(180, 720, n))],
        "spec": np.random.choice(["100ml", "200ml", "500ml", "1L"], n),
        "current_stock": np.random.randint(0, 500, n),
        "available_qty": np.random.randint(0, 500, n),
        "brand_class": np.random.choice(["A类", "B类", "C类", "D类"], n),
        "estimated_shipping_qty": np.random.randint(0, 50, n),
        "estimated_order_qty": np.random.randint(0, 50, n),
    })
    return df


def get_fixture_path(name: str) -> io.BytesIO:
    """
    把 mock DataFrame 写成 xlsx 字节流(用于模拟 RPA 下载文件)
    """
    loaders = {
        "sales_out": load_sales_out_mock,
        "purchase_order": load_purchase_order_mock,
        "stock_in": load_stock_in_mock,
        "purchase_req": load_purchase_req_mock,
        "stock_current": load_stock_current_mock,
    }
    if name not in loaders:
        raise ValueError(f"Unknown fixture: {name}. Available: {list(loaders.keys())}")
    df = loaders[name]()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    buf.seek(0)
    return buf


if __name__ == "__main__":
    # 生成所有 mock 数据并写到磁盘,方便 ETL/RPA demo 使用
    import os
    out_dir = Path(__file__).parent.parent.parent / "data" / "fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating mock fixtures to {out_dir}...")
    for name, loader in [
        ("sales_out", load_sales_out_mock),
        ("purchase_order", load_purchase_order_mock),
        ("stock_in", load_stock_in_mock),
        ("purchase_req", load_purchase_req_mock),
        ("stock_current", load_stock_current_mock),
    ]:
        df = loader()
        path = out_dir / f"{name}_mock.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  {name}: {len(df)} rows -> {path.name}")
    print("Done.")
