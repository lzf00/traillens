#!/usr/bin/env bash
# Postgres 定时备份 → 打包上传 COS,保留 7 天。
# 装法(在服务器):
#   cp infra/prod/backup_pg.sh /usr/local/bin/traillens-backup.sh && chmod +x !$
#   crontab -e  →  加下面这行(每天 03:00 备份):
#     0 3 * * * /usr/local/bin/traillens-backup.sh >> /var/log/traillens-backup.log 2>&1

set -euo pipefail

# ── 配置(env 优先) ─────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/var/backups/traillens}"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/traillens/infra/prod/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-/opt/traillens/.env}"
PG_USER="${PG_USER:-traillens}"
PG_DB="${PG_DB:-traillens}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
COS_BUCKET_URL="${COS_BUCKET_URL:-}"    # 例:https://traillens-backups-xxx.cos.ap-shanghai.myqcloud.com/pg/

# ── 备份 ─────────────────────────────────
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d-%H%M%S)
OUT="$BACKUP_DIR/pg-$TS.sql.gz"

echo "[$(date -Iseconds)] backup start → $OUT"

# 用 pg_dump 走 docker exec(不用装本地 pg client)
docker exec -e PGPASSWORD="$(grep '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d= -f2)" \
  traillens-pg pg_dump -U "$PG_USER" -d "$PG_DB" --format=plain --no-owner --clean --if-exists \
  | gzip -9 > "$OUT"

SIZE=$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT")
echo "[$(date -Iseconds)] dumped $((SIZE/1024))KB"

# ── 上传 COS(如果配了) ────────────────────
if [ -n "$COS_BUCKET_URL" ] && command -v coscli >/dev/null 2>&1; then
  coscli cp "$OUT" "$COS_BUCKET_URL/pg-$TS.sql.gz" && echo "[$(date -Iseconds)] uploaded to COS"
elif [ -n "$COS_BUCKET_URL" ]; then
  echo "[$(date -Iseconds)] WARN: coscli 未装,跳过 COS 上传(备份仅在本地 $BACKUP_DIR)"
fi

# ── 清理旧备份 ───────────────────────────
find "$BACKUP_DIR" -name 'pg-*.sql.gz' -mtime +"$RETAIN_DAYS" -delete
echo "[$(date -Iseconds)] retention: 保留最近 $RETAIN_DAYS 天;当前留:"
ls -lh "$BACKUP_DIR"/pg-*.sql.gz 2>/dev/null | tail -10

echo "[$(date -Iseconds)] done"
