# 数据库迁移

Alembic 管理 17 张表(STG 5 + RPT 7 + dim 5)的 schema 演进。

## 一次性初始化

```bash
# 安装 alembic
pip install alembic

# 用 .env 的 DATABASE_URL 跑迁移
alembic upgrade head
```

## 常用命令

```bash
# 当前 schema 状态
alembic current

# 生成新的迁移脚本(改 ORM 模型后)
alembic revision --autogenerate -m "add_new_column"

# 应用迁移
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

## 切换 DB 类型

通过环境变量覆盖 `DATABASE_URL`:

```bash
# SQLite
export DATABASE_URL="sqlite:///./data/dev.db"

# MySQL
export DATABASE_URL="mysql+pymysql://user:pass@host:3306/db?charset=utf8mb4"

# Postgres
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db"
alembic upgrade head
```

## Schema 总览

- **STG**(5 张):清洗后的原始数据写入区,Pipeline 步骤 1 之后写入
- **RPT**(7 张):聚合后的报表,Writer 步骤写入
- **dim**(5 张):维度表,ETL 末尾自动同步

完整字段定义见 `channel_analytics/db/models/`。