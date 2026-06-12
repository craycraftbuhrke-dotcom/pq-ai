#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT_DIR/.env.local"
set +a

export PYTHONPATH="$ROOT_DIR/services/api/.runtime/site-packages:$ROOT_DIR/services/api"

cd "$ROOT_DIR/services/api"
python3 -m alembic upgrade head
python3 -m app.db.seed_demo

echo "pq_ai 数据库迁移与初始化完成。"
