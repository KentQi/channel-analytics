# 多阶段构建:减小镜像 + 隔离构建依赖
FROM python:3.11-slim AS builder

WORKDIR /build

# 系统依赖(psycopg/bcrypt 等需要 gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml ./
COPY channel_analytics ./channel_analytics
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels \
        ".[mysql,postgres]" \
    && pip wheel --no-cache-dir --wheel-dir /wheels alembic

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 运行时系统依赖(Playwright 浏览器需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制 wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links /wheels \
        "channel-analytics[mysql,postgres]" \
        alembic \
    && rm -rf /wheels

# Playwright 浏览器(可选,部署期按需安装)
# RUN playwright install --with-deps chromium

# 复制应用
COPY channel_analytics ./channel_analytics
COPY alembic ./alembic
COPY alembic.ini ./
COPY deploy/scripts/start.sh ./start.sh
RUN chmod +x ./start.sh

# 数据/上传/日志目录
RUN mkdir -p /app/data/rpa_downloads /app/logs && chown -R appuser:appuser /app

# 非 root 用户运行(满足 K8s restricted PSP / Docker security best practice)
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

CMD ["./start.sh"]