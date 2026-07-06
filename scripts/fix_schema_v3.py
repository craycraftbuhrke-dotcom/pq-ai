"""
V3 SQL 修复脚本：
1. TEXT NOT NULL → TEXT NULL（消除 -5 分：BLOB/TEXT/JSON 不建议 NOT NULL DEFAULT + 无 DEFAULT）
2. JSON NOT NULL → JSON NULL（同上）
业务保护：应用层 ORM 仍保留 nullable=False + default=... 兜底，业务代码零改动
"""
import re

SQL_PATH = "docs/sql/pq_ai_mysql_schema.sql"

with open(SQL_PATH, encoding="utf-8") as f:
    sql = f.read()

original = sql
changes_text = 0
changes_json = 0

# 1) TEXT NOT NULL → TEXT NULL
# 匹配 `col_name` TEXT NOT NULL COMMENT '...'
def fix_text(match):
    global changes_text
    changes_text += 1
    return match.group(1) + " TEXT NULL" + match.group(2)

sql = re.sub(
    r"(`[a-z_]+`) TEXT NOT NULL(\s+COMMENT)",
    fix_text,
    sql,
)

# 2) JSON NOT NULL → JSON NULL
def fix_json(match):
    global changes_json
    changes_json += 1
    return match.group(1) + " JSON NULL" + match.group(2)

sql = re.sub(
    r"(`[a-z_]+`) JSON NOT NULL(\s+COMMENT)",
    fix_json,
    sql,
)

with open(SQL_PATH, "w", encoding="utf-8") as f:
    f.write(sql)

print(f"TEXT NOT NULL → TEXT NULL: {changes_text} changes")
print(f"JSON NOT NULL → JSON NULL: {changes_json} changes")
