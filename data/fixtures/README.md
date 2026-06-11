# Mock Data Fixtures

脱敏后的虚构数据,用于开发/演示/测试。

## 目录结构

```
data/fixtures/
├── sales_out.csv          (2000 行)  销售出库单
├── purchase_order.csv     ( 500 行)  采购单
├── stock_in.csv           ( 800 行)  入库单
├── purchase_req.csv       ( 300 行)  请购单
├── stock_current.csv      (1500 行)  现存量
└── dim/
    ├── product_attr.csv         (30 行)  物料属性
    ├── customer.csv             (50 行)  客户档案
    ├── self_operated_brand.csv  (12 行)  自营品牌白名单
    ├── user.csv                 ( 5 行)  系统用户(admin/alice/bob/charlie/diana)
    └── role_permissions.csv     ( 4 行)  角色权限
```

## 占位说明

| 字段 | 占位 |
|------|------|
| 12 个品牌名 | `Brand A` - `Brand L` |
| 客户名 | `客户001` - `客户050` |
| 物料编码 | `SKU-0001` - `SKU-0030` |
| 物料名称 | `物料-01` - `物料-30` |
| 区域 | `East` / `South` / `North` / ...(7 档抽象) |
| 用户名 | `admin` / `alice` / `bob` / `charlie` / `diana` |
| 角色 | `admin` / `manager` / `analyst` / `viewer` |

## 重新生成

```bash
python -m channel_analytics.data.fixtures
# 重新生成 5 个 STG 表
```

## 自动注入数据库

```bash
python -m channel_analytics.data.seed
# 读取 data/fixtures/*.csv → 灌入 ORM → 触发 ETL
```

## 默认登录

**注意**: 这些密码 hash 在 user.csv 里是 `PLACEHOLDER_NOT_REAL_HASH`,seed 脚本会用 bcrypt 重写为真 hash。
