# CLI 命令

## channel-analytics

主 CLI 入口(`pyproject.toml` 注册)。

### `channel-analytics init-secrets`

把 `.env` 中的 `GENERATE-ON-FIRST-RUN` 占位符替换为 `secrets.token_urlsafe(48)`(64 字符)。

```bash
$ cp .env.example .env
$ channel-analytics init-secrets
[init-secrets] SESSION_SECRET: replaced placeholder
[init-secrets] JWT_SECRET: replaced placeholder
[init-secrets] .env permissions set to 0o600
```

### `channel-analytics check-config`

校验 `.env` 配置(无实际启动服务)。

```bash
$ channel-analytics check-config
OK: env=development session_len=64 db='sqlite:///./data/dev.db'
```

### `channel-analytics run-etl`

同步跑 ETL(无 API / 无 scheduler)。适合 cron + CLI。

```bash
$ channel-analytics run-etl
```

### `channel-analytics run-rpa`

启动 RPA worker 子进程(对应 `python -m channel_analytics.rpa.worker`)。

```bash
$ channel-analytics run-rpa --task-id 1 --module "m1"
```

## 子命令工具

### `alembic`

```bash
alembic upgrade head     # 应用迁移
alembic downgrade -1     # 回滚 1 步
alembic revision -m "..." # 新建迁移
```

### `uvicorn`

```bash
uvicorn channel_analytics.api.app:app --reload
```

### `pytest`

```bash
pytest                    # 全跑
pytest tests/unit        # 只跑 unit
pytest --cov=channel_analytics  # 带覆盖
```

### `ruff`

```bash
ruff check .
ruff format .
```