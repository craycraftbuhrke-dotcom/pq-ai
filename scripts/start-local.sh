#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT_DIR/.env.local"
set +a

API_PORT="${API_PORT:-8012}"
WEB_PORT="${WEB_PORT:-3012}"
export PYTHONPATH="$ROOT_DIR/services/api/.runtime/site-packages:$ROOT_DIR/services/api"

if [ "${RUN_DB_INIT:-false}" = "true" ]; then
  echo "自动数据库 DDL 已禁用：请通过公司工单审批手动创建/变更数据库结构。" >&2
fi

cleanup() {
  kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd "$ROOT_DIR/services/api"
  python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT"
) &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$API_PORT/api/v1/health/ready" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl -fsS "http://127.0.0.1:$API_PORT/api/v1/health/ready" >/dev/null; then
  echo "API 启动失败，请检查 MySQL 与端口 $API_PORT。" >&2
  exit 1
fi

if [ "${SKIP_WEB_BUILD:-false}" != "true" ]; then
  (
    cd "$ROOT_DIR"
    npm run build --workspace apps/web
  )
fi

STANDALONE_WEB_DIR="$ROOT_DIR/apps/web/.next/standalone/apps/web"
mkdir -p "$STANDALONE_WEB_DIR/.next/static" "$STANDALONE_WEB_DIR/public"
cp -R "$ROOT_DIR/apps/web/.next/static/." "$STANDALONE_WEB_DIR/.next/static/"
cp -R "$ROOT_DIR/apps/web/public/." "$STANDALONE_WEB_DIR/public/"

(
  cd "$STANDALONE_WEB_DIR"
  HOSTNAME="127.0.0.1" \
  PORT="$WEB_PORT" \
  API_URL="http://127.0.0.1:$API_PORT/api/v1" \
  NEXT_PUBLIC_API_URL="http://127.0.0.1:$API_PORT/api/v1" \
  node server.js
) &
WEB_PID=$!

echo "PQ-AI 已启动："
echo "管理端：http://localhost:$WEB_PORT"
echo "API 文档：http://localhost:$API_PORT/docs"
wait
