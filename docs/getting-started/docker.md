# Docker 部署

## 一键起(SQLite 默认)

```bash
docker compose -f deploy/docker/docker-compose.yml up -d
```

打开 http://localhost:8000/healthz 看存活。

## 启用 MySQL

`deploy/docker/docker-compose.yml` 里有注释好的 MySQL service,取消注释 + 改 `DATABASE_URL` 即可:

```bash
# .env
DATABASE_URL=mysql+pymysql://channel:changeme@db:3306/channel_analytics
```

`db` 是 docker-compose 服务名(host 解析为容器 IP)。

## 启用 Postgres

类似,取消注释 postgres service + 改 `DATABASE_URL` 为 `postgresql+psycopg://...`。

## 反向代理 + TLS

部署方应用 nginx / caddy / traefik 反代 + Let's Encrypt。
本仓不内置,见 [deploy/README.md](../../deploy/README.md)。

## 镜像大小

`Dockerfile` 是多阶段构建,最终镜像 ~400MB(无 Playwright 浏览器)。

如需 RPA 浏览器,取消注释 `RUN playwright install --with-deps chromium`,会再加 ~300MB。