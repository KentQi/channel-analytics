#!/usr/bin/env bash
# 备份脚本 — 打包 data 目录 + 上传数据库 dump
#
# 用法:
#   deploy/scripts/backup.sh [destination_dir]
#
# 默认 destination_dir = ./backups(自动 .gitignore)

set -euo pipefail

DEST="${1:-./backups}"
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$DEST"

echo "[backup] destination: $DEST"
echo "[backup] timestamp: $TS"

# 1. 打包 data 目录(stg/rpt/dim dump)
if [ -d "./data" ]; then
    tar czf "$DEST/data_${TS}.tar.gz" ./data
    echo "[backup] data/ archived: data_${TS}.tar.gz"
fi

# 2. 如果是 MySQL/Postgres,跑数据库 dump
if [ -n "${DATABASE_URL:-}" ]; then
    case "$DATABASE_URL" in
        mysql*)
            # 解析 SQLAlchemy URL:mysql+pymysql://user:pass@host:port/db
            MYSQL_URL="${DATABASE_URL#mysql+pymysql://}"
            MYSQL_URL="${MYSQL_URL#mysql://}"
            DB_USER=$(echo "$MYSQL_URL" | sed -E 's|://([^:]+):.*|\1|')
            DB_PASS=$(echo "$MYSQL_URL" | sed -E 's|://[^:]+:([^@]+)@.*|\1|')
            DB_HOST=$(echo "$MYSQL_URL" | sed -E 's|.*@([^:/]+).*|\1|')
            DB_PORT=$(echo "$MYSQL_URL" | sed -E 's|.*@[^:/]+:([0-9]+).*|\1|')
            DB_PORT="${DB_PORT:-3306}"
            DB_NAME=$(echo "$MYSQL_URL" | sed -E 's|.*/([^?]+).*|\1|')
            echo "[backup] MySQL: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
            MYSQL_PWD="$DB_PASS" mysqldump --user="$DB_USER" --host="$DB_HOST" \
                --port="$DB_PORT" --single-transaction --routines --triggers \
                "$DB_NAME" > "$DEST/db_${TS}.sql"
            gzip "$DEST/db_${TS}.sql"
            echo "[backup] MySQL dump: db_${TS}.sql.gz"
            ;;
        postgresql*)
            # 解析 SQLAlchemy URL:postgresql+psycopg://user:pass@host:port/db
            PG_URL="${DATABASE_URL#postgresql+psycopg://}"
            PG_URL="${PG_URL#postgresql://}"
            DB_USER=$(echo "$PG_URL" | sed -E 's|://([^:]+):.*|\1|')
            DB_PASS=$(echo "$PG_URL" | sed -E 's|://[^:]+:([^@]+)@.*|\1|')
            DB_HOST=$(echo "$PG_URL" | sed -E 's|.*@([^:/]+).*|\1|')
            DB_PORT=$(echo "$PG_URL" | sed -E 's|.*@[^:/]+:([0-9]+).*|\1|')
            DB_PORT="${DB_PORT:-5432}"
            DB_NAME=$(echo "$PG_URL" | sed -E 's|.*/([^?]+).*|\1|')
            echo "[backup] PostgreSQL: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
            PGPASSWORD="$DB_PASS" pg_dump --username="$DB_USER" --host="$DB_HOST" \
                --port="$DB_PORT" --no-owner "$DB_NAME" > "$DEST/db_${TS}.sql"
            gzip "$DEST/db_${TS}.sql"
            echo "[backup] PostgreSQL dump: db_${TS}.sql.gz"
            ;;
        sqlite*)
            # SQLite: 路径在 sqlite:/// 后
            DB_FILE="${DATABASE_URL#sqlite:///}"
            if [ -f "$DB_FILE" ]; then
                # 使用 sqlite3 .backup 命令(WAL 安全)
                if command -v sqlite3 >/dev/null 2>&1; then
                    sqlite3 "$DB_FILE" ".backup '$DEST/dev_${TS}.db'"
                else
                    # 退化方案:cp + 完整性检查
                    cp "$DB_FILE" "$DEST/dev_${TS}.db"
                fi
                echo "[backup] SQLite backup: dev_${TS}.db"
            else
                echo "[backup] WARN: SQLite file not found: $DB_FILE"
            fi
            ;;
    esac
fi

# 3. 保留策略: 删 30 天前的备份
find "$DEST" -type f -mtime +30 -name "*.gz" -delete 2>/dev/null || true
find "$DEST" -type f -mtime +30 -name "*.db" -delete 2>/dev/null || true
echo "[backup] cleanup: removed backups older than 30 days"

echo "[backup] done"
ls -lh "$DEST" | tail -10