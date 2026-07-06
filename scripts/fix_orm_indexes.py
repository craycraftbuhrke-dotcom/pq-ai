# -*- coding: utf-8 -*-
"""
后端 ORM Index/UniqueConstraint 中的 DB 列名同步改名

Index/UniqueConstraint 里的字符串参数是 DB 列名（不是 Python 属性名），
所以列名改动后必须同步改这些引用。

改名映射（DB 列名）：
- "status"  -> "row_status"
- "method"  -> "method_code"
- "action"  -> "action_type"
- "role"    -> "role_code"

只处理 Index(...) 和 UniqueConstraint(...) 内的字符串参数，不影响其他字符串。
"""

import re
from pathlib import Path

DOMAIN_PATH = Path(__file__).resolve().parent.parent / "services" / "api" / "app" / "models" / "domain.py"

RENAMES = {
    "status": "row_status",
    "method": "method_code",
    "action": "action_type",
    "role": "role_code",
}


def rewrite_index_line(line: str) -> str:
    """
    匹配诸如 Index("idx_xxx", "col_a", "status", "col_b") 或 UniqueConstraint(...)
    只替换其中的 "status"/"method"/"action"/"role" 三个字符串参数。
    """
    if "Index(" not in line and "UniqueConstraint(" not in line:
        return line

    for old, new in RENAMES.items():
        # 匹配双引号包裹的独立列名
        # 前面是 (  或 空格或逗号 或 引号后逗号 结尾，紧接 "old"
        line = re.sub(
            r'(?<=[,\s(])"' + re.escape(old) + r'"',
            f'"{new}"',
            line,
        )
    return line


def main():
    text = DOMAIN_PATH.read_text(encoding="utf-8")
    lines = text.split("\n")

    changed = 0
    for i, line in enumerate(lines):
        new_line = rewrite_index_line(line)
        if new_line != line:
            lines[i] = new_line
            changed += 1

    DOMAIN_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK: rewrote {changed} Index/UniqueConstraint lines")


if __name__ == "__main__":
    main()
