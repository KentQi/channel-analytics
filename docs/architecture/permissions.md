# 权限模型

三维权限(role → modules / sales_tabs / regions)。

## 数据结构

```python
@dataclass
class RolePermissions:
    modules: list[str]            # 该 role 可访问的功能模块
    sales_tabs: list[str] | None  # 销售 Tab 过滤(None = 全部)
    regions: list[str] | None    # 区域过滤(None = 全部)
```

## 存储

表 `role_permission`:

| 列 | 类型 | 说明 |
|----|------|------|
| role | VARCHAR | 角色名 |
| permission_type | VARCHAR | module / sales_tab / region |
| permission_value | TEXT | 数组 JSON(仅 sales_tab / region 用) |
| module_ext | VARCHAR | 模块名(仅 module 用) |

## 用法

```python
from channel_analytics.auth.permissions import (
    load_role_permissions,
    check_role_exists,
    update_role_permissions,
)

# 查
rp = load_role_permissions(db, "admin")
print(rp.modules)      # ['dashboard', 'etl', 'reports']
print(rp.sales_tabs)  # ['sales_today', 'sales_week']
print(rp.regions)     # None  = 全部

# 检查
if check_role_exists(db, "viewer"): ...

# 改(覆盖式)
update_role_permissions(db, "admin", {
    "modules": ["dashboard", "reports"],
    "sales_tabs": ["sales_today"],
    "regions": ["north"],
})
```

## 三维过滤示例

```python
# 数据查询时:
if rp.sales_tabs:
    df = df[df["sales_tab"].isin(rp.sales_tabs)]
if rp.regions:
    df = df[df["region"].isin(rp.regions)]
```

## 与 FastAPI 集成

`get_current_user` dependency 返回 `{username, role, modules}`,路由可直接判断:

```python
@router.get("/admin")
async def admin_only(user=Depends(get_current_user)):
    if "admin" not in user.get("modules", []):
        raise HTTPException(403, "Forbidden")
    ...
```