# -*- coding: utf-8 -*-
"""
PQ-AI SQL Schema 优化脚本 v2

本次改动（一次性）：
1. 关键字列名改名（DB 层）
   - `status`  -> `row_status`   （避免与 audit_log.status_code 语义冲突）
   - `method`  -> `method_code`
   - `action`  -> `action_type`
   - `role`    -> `role_code`     （仅 quality_issue_comment 表）
   同步改索引/唯一键中的列名引用。

2. 主键 id 保持 VARCHAR(36) NOT NULL 无 DEFAULT（业务由应用层 uuid4 生成）
   主键 DEFAULT (UUID()) 表达式会被部分审核器认为 grammar failure，故不使用。

3. TEXT 字段保持无 DEFAULT（MySQL 语法本身不允许 TEXT 有默认值）。

配套：
- 后端 ORM (services/api/app/models/domain.py) 使用 name=/key= 分离列名与属性名
- 前端 & Pydantic Schema 完全不动
"""

import re
from pathlib import Path

SQL_PATH = Path(__file__).resolve().parent.parent / "docs" / "sql" / "pq_ai_mysql_schema.sql"

# 严格按需要改的关键字列，避免误伤（例如 audit_log 的 `status_code`、`http_method` 都不要碰）
KEYWORD_RENAMES = [
    ("status", "row_status"),
    ("method", "method_code"),
    ("action", "action_type"),
    ("role", "role_code"),
]


def replace_column_definitions(content: str) -> str:
    """替换列定义、索引引用、唯一键引用中的关键字列名。

    只匹配用反引号包裹的独立词。例如：
    - `status`         -> `row_status`
    - `status_code`    保持不变（因为 audit_log 已有 status_code 语义完全不同）
    - `http_method`    保持不变
    - `method`         -> `method_code`
    """
    for old, new in KEYWORD_RENAMES:
        # 精确匹配反引号包裹的完整列名 `old`
        pattern = re.compile(r"`" + re.escape(old) + r"`")
        content = pattern.sub(f"`{new}`", content)
    return content


def main():
    text = SQL_PATH.read_text(encoding="utf-8")
    original_len = len(text)

    text = replace_column_definitions(text)

    SQL_PATH.write_text(text, encoding="utf-8")

    print(f"OK: schema rewritten, length {original_len} -> {len(text)}")
    for old, new in KEYWORD_RENAMES:
        cnt_new = text.count(f"`{new}`")
        cnt_old = text.count(f"`{old}`")
        print(f"  `{old}` remaining: {cnt_old}, `{new}` count: {cnt_new}")


if __name__ == "__main__":
    main()
