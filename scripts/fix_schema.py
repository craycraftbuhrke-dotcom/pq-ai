"""
一次性修复 pq_ai_mysql_schema.sql 中的审批扣分项：
  1) VARCHAR(1000+) -> TEXT（长文本字段）
  2) 除主键 `id` 之外的 NOT NULL 字段补齐 DEFAULT

保留：
  - 主键仍为 VARCHAR(36)（UUID，业务需要）
  - 关键字列名（status/method/type 等）保持原名
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "docs" / "sql" / "pq_ai_mysql_schema.sql"

# ---------- Step 1: VARCHAR(>=1000) -> TEXT ----------
# 规则：VARCHAR(数字>=1000) 全部转成 TEXT
# 注意 TEXT 不能有 DEFAULT，且 NOT NULL 的 TEXT 审核允许
def _replace_varchar_to_text(line: str) -> str:
    def repl(m: re.Match[str]) -> str:
        n = int(m.group(1))
        if n >= 1000:
            return "TEXT"
        return m.group(0)
    return re.sub(r"VARCHAR\((\d+)\)", repl, line)


# ---------- Step 2: 补齐 NOT NULL DEFAULT ----------
# 规则：
#   `<col>` <TYPE> NOT NULL COMMENT ...  →  `<col>` <TYPE> NOT NULL DEFAULT <值> COMMENT ...
# 例外：
#   - 主键 `id` 保持原样（不加默认值）
#   - 已经带 DEFAULT 的不改
#   - TEXT/BLOB/JSON 不加默认值（MySQL 不允许 TEXT/BLOB/JSON 有默认字面量）
COL_PATTERN = re.compile(
    r"^(\s*`([a-zA-Z0-9_]+)`\s+)"        # 1: 前缀含 `col_name`; 2: col_name
    r"([A-Z]+(?:\s+UNSIGNED)?(?:\([\d,\s]+\))?)"  # 3: 类型（可能有 UNSIGNED 和括号）
    r"(\s+NOT NULL)"                     # 4: NOT NULL
    r"(?!\s+DEFAULT)"                    # 后瞻：确保还没 DEFAULT
    r"(\s+COMMENT\s+'.*')?"              # 5: 可选 COMMENT
    r"(,?)\s*$"                          # 6: 可选逗号
)


def _default_for_type(type_str: str) -> str | None:
    """根据 SQL 类型返回默认值字面量；返回 None 表示不加。"""
    t = type_str.upper()
    # TEXT/BLOB/JSON 不允许默认字面量
    if "TEXT" in t or "BLOB" in t or t.startswith("JSON"):
        return None
    if t.startswith("TIMESTAMP") or t.startswith("DATETIME"):
        return "CURRENT_TIMESTAMP"
    if t.startswith("DATE"):
        return "'1970-01-01'"
    if t.startswith("TIME"):
        return "'00:00:00'"
    # 数值型
    if any(t.startswith(x) for x in (
        "TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER", "BIGINT",
        "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL",
    )):
        return "0"
    # 字符串型
    if t.startswith("VARCHAR") or t.startswith("CHAR"):
        return "''"
    return None


def _add_default(line: str) -> str:
    m = COL_PATTERN.match(line)
    if not m:
        return line
    prefix, col_name, type_str, not_null, comment, trailing = (
        m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or "", m.group(6)
    )
    # 主键 id 不补默认值
    if col_name == "id":
        return line
    default_lit = _default_for_type(type_str)
    if default_lit is None:
        return line
    return f"{prefix}{type_str}{not_null} DEFAULT {default_lit}{comment}{trailing}\n"


def transform(content: str) -> str:
    out_lines: list[str] = []
    for raw in content.splitlines(keepends=True):
        line = _replace_varchar_to_text(raw)
        line = _add_default(line)
        out_lines.append(line)
    return "".join(out_lines)


def main() -> None:
    original = SRC.read_text(encoding="utf-8")
    updated = transform(original)
    if updated == original:
        print("No changes.")
        return
    SRC.write_text(updated, encoding="utf-8")
    # 打印统计
    before_varchar = len(re.findall(r"VARCHAR\((?:1[0-9]{3}|[2-9][0-9]{3})\)", original))
    after_varchar = len(re.findall(r"VARCHAR\((?:1[0-9]{3}|[2-9][0-9]{3})\)", updated))
    before_notnull_no_default = 0
    after_notnull_no_default = 0
    for raw in original.splitlines():
        if re.search(r"NOT NULL(?!\s+DEFAULT)\s+COMMENT", raw):
            before_notnull_no_default += 1
    for raw in updated.splitlines():
        if re.search(r"NOT NULL(?!\s+DEFAULT)\s+COMMENT", raw):
            after_notnull_no_default += 1
    print(f"VARCHAR(>=1000): before={before_varchar}  after={after_varchar}")
    print(f"NOT NULL 无 DEFAULT 的列（不含 TEXT/JSON/主键 id）: before={before_notnull_no_default}  after={after_notnull_no_default}")


if __name__ == "__main__":
    main()
