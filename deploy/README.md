# deploy/

生产部署脚本和容器化配置。

## 文件清单

| 文件 | 用途 |
|------|------|
| `docker/Dockerfile` | 多阶段构建,最终镜像 ~400MB |
| `docker/docker-compose.yml` | 一键起 API + 可选 MySQL/Postgres |
| `scripts/start.sh` | 容器内启动脚本(先 alembic upgrade,再 uvicorn) |
| `scripts/backup.sh` | 备份 data 目录 + DB dump |
| `scripts/restore.sh` | 从备份恢复 |

## 快速开始

### 开发模式(SQLite,无需 Docker)

```bash
pip install -e ".[dev]"
cp .env.example .env
channel-analytics init-secrets
alembic upgrade head
uvicorn channel_analytics.api.app:app --reload
```

### Docker 自部署

```bash
docker compose -f deploy/docker/docker-compose.yml up -d
```

### 备份与恢复

```bash
# 备份(默认 ./backups/)
deploy/scripts/backup.sh

# 恢复(需要 yes 确认)
deploy/scripts/restore.sh ./backups/data_20260610_120000.tar.gz
```

## 自定义 deploy

部署方可:
- 把 Dockerfile 改成 multi-arch build(linux/amd64 + linux/arm64)
- 加 nginx 反向代理 + TLS
- 用 docker secrets 管理 .env 凭据
- 加 Prometheus exporter(API metrics)