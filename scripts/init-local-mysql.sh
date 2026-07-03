#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT_DIR/.env.local"
set +a

export PYTHONPATH="$ROOT_DIR/services/api/.runtime/site-packages:$ROOT_DIR/services/api"

cd "$ROOT_DIR/services/api"
echo "数据库结构变更已禁用自动执行；建库、建表、改表、索引、约束、触发器等必须走审批工单并由人工执行 SQL。"
python3 -m app.db.seed_demo

echo "pq_ai 数据初始化完成。"
