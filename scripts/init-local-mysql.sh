#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT_DIR/.env.local"
set +a

export PYTHONPATH="$ROOT_DIR/services/api/.runtime/site-packages:$ROOT_DIR/services/api"

echo "自动数据库 DDL 已禁用。" >&2
echo "请根据 services/api/alembic/versions 中的迁移内容整理审批 SQL，并通过公司工单流程手动执行。" >&2
echo "如已完成表结构审批并仅需写入演示数据，请显式运行：RUN_DEMO_SEED=true scripts/start-local.sh" >&2
exit 1
