#!/usr/bin/env bash
# 恢复脚本 — 从备份恢复 data 目录 + 数据库
#
# 用法:
#   deploy/scripts/restore.sh <backup_file>
#
# 警告:会覆盖当前 data 目录和数据库,使用前请确认。

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file>" >&2
    echo "  backup_file: data_*.tar.gz 或 db_*.sql.gz" >&2
    exit 1
fi

BACKUP="$1"

if [ ! -f "$BACKUP" ]; then
    echo "Backup file not found: $BACKUP" >&2
    exit 1
fi

echo "[restore] WARNING: this will overwrite current data and database."
read -rp "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "[restore] aborted"
    exit 0
fi

case "$BACKUP" in
    *.tar.gz)
        tar --no-same-owner -xzf "$BACKUP" -C .
        echo "[restore] data/ restored from $BACKUP"
        ;;
    *.sql.gz)
        gunzip -c "$BACKUP" > /tmp/restore.sql
        case "${DATABASE_URL:-}" in
            mysql*)
                # 解析 SQLAlchemy URL
                MYSQL_URL="${DATABASE_URL#mysql+pymysql://}"
                MYSQL_URL="${MYSQL_URL#mysql://}"
                DB_USER=$(echo "$MYSQL_URL" | sed -E 's|://([^:]+):.*|\1|')
                DB_PASS=$(echo "$MYSQL_URL" | sed -E 's|://[^:]+:([^@]+)@.*|\1|')
                DB_HOST=$(echo "$MYSQL_URL" | sed -E 's|.*@([^:/]+).*|\1|')
                DB_PORT=$(echo "$MYSQL_URL" | sed -E 's|.*@[^:/]+:([0-9]+).*|\1|')
                DB_PORT="${DB_PORT:-3306}"
                DB_NAME=$(echo "$MYSQL_URL" | sed -E 's|.*/([^?]+).*|\1|')
                MYSQL_PWD="$DB_PASS" mysql --user="$DB_USER" --host="$DB_HOST" \
                    --port="$DB_PORT" "$DB_NAME" < /tmp/restore.sql
                ;;
            postgresql*)
                PG_URL="${DATABASE_URL#postgresql+psycopg://}"
                PG_URL="${PG_URL#postgresql://}"
                DB_USER=$(echo "$PG_URL" | sed -E 's|://([^:]+):.*|\1|')
                DB_PASS=$(echo "$PG_URL" | sed -E 's|://[^:]+:([^@]+)@.*|\1|')
                DB_HOST=$(echo "$PG_URL" | sed -E 's|.*@([^:/]+).*|\1|')
                DB_PORT=$(echo "$PG_URL" | sed -E 's|.*@[^:/]+:([0-9]+).*|\1|')
                DB_PORT="${DB_PORT:-5432}"
                DB_NAME=$(echo "$PG_URL" | sed -E 's|.*/([^?]+).*|\1|')
                PGPASSWORD="$DB_PASS" psql --username="$DB_USER" --host="$DB_HOST" \
                    --port="$DB_PORT" --dbname="$DB_NAME" < /tmp/restore.sql
                ;;
            *)
                echo "[restore] unknown DB URL: $DATABASE_URL" >&2
                exit 2
                ;;
        esac
        rm -f /tmp/restore.sql
        echo "[restore] database restored from $BACKUP"
        ;;
    *.db)
        cp "$BACKUP" "${DATABASE_URL#sqlite:///}"
        echo "[restore] SQLite restored from $BACKUP"
        ;;
    *)
        echo "[restore] unknown backup format: $BACKUP" >&2
        exit 2
        ;;
esac

echo "[restore] done"