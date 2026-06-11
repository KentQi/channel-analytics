# 首次运行

5 步从 0 跑到第一条 RPT。

## 1. 初始化 secrets

```bash
cp .env.example .env
channel-analytics init-secrets
```

`init-secrets` 会把 `.env` 中的 `GENERATE-ON-FIRST-RUN` 占位符替换成 64 字符的随机串。

## 2. 建数据库表

```bash
alembic upgrade head
```

会创建 17 张表(5 STG + 7 RPT + 5 dim)。

## 3. 启动 API

```bash
uvicorn channel_analytics.api.app:app --reload
```

打开 http://localhost:8000/docs 看 OpenAPI 文档。

## 4. 跑 ETL

通过 API:

```bash
curl -X POST http://localhost:8000/etl/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"raw_data": {}}'
```

或在 Python:

```python
from channel_analytics.etl.pipeline import run_default_etl
ctx = run_default_etl({}, brand_provider_dotted="channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider")
print(ctx.rpt.keys())
```

## 5. 查询 RPT

```bash
curl http://localhost:8000/reports/rpt_expiry_warning \
  -H "Authorization: Bearer $TOKEN"
```

## 常见问题

### Q: `init-secrets` 失败说 "RefuseToStart"?

`init-secrets` 自动写入,但启动时仍占位 → 检查 `.env` 里的 `SESSION_SECRET`/`JWT_SECRET` 是否被 `init-secrets` 替换。

### Q: 端口 8000 被占用?

```bash
uvicorn channel_analytics.api.app:app --port 8001
```

### Q: 想用 MySQL 而非 SQLite?

```bash
# .env
DATABASE_URL=mysql+pymysql://channel:changeme@localhost:3306/channel_analytics

# 重跑迁移
alembic upgrade head
```