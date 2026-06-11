# REST API

Base URL: `http://localhost:8000`

OpenAPI 文档: http://localhost:8000/docs(交互式)
ReDoc: http://localhost:8000/redoc

## 通用

### GET /healthz
存活探针(无 auth)。

```json
{"status": "ok", "version": "0.1.0"}
```

## /auth

### POST /auth/login
```json
{"username": "alice", "password": "secret"}
```
→ `{"access_token": "...", "token_type": "bearer", "expires_in": 3600}`

### GET /auth/me
需要 `Authorization: Bearer <token>`。
→ `{"username": "alice", "role": "admin", "modules": ["dashboard", "etl"]}`

### POST /auth/logout
→ 204 No Content

## /rpa

### GET /rpa/tasks
列出所有 RPA 任务。

### POST /rpa/tasks
```json
{"name": "daily_inventory", "module_names": ["m1", "m2"], "schedule_cron": "0 9 * * *"}
```

### GET /rpa/tasks/{id}
任务详情。

### POST /rpa/tasks/{id}/run
立即触发(异步) → `{"status": "queued", "task_id": "1"}`

### GET /rpa/logs?task_id=1
执行日志列表。

## /etl

### POST /etl/run
```json
{
  "raw_data": {
    "purchase_req": [{"order_no": "O1", "material_code": "M1", "order_qty": 100}]
  },
  "brand_provider_dotted": "channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider"
}
```
→ `{"run_id": "uuid", "status": "queued"}`

### GET /etl/status/{run_id}
→ `{"run_id": "...", "status": "running"}`

### GET /etl/pipeline
列出 Pipeline 步骤。

## /reports

### GET /reports
列出所有 RPT 表(7 张默认 + 自定义)。

### GET /reports/catalog
报表目录(name → description + columns)。

### GET /reports/{name}?limit=10&offset=0
查询 RPT 表(分页)。

## 错误码

| 状态 | 含义 |
|------|------|
| 401 | 未登录或 token 无效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 请求体校验失败 |