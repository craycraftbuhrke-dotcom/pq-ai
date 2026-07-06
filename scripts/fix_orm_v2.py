# -*- coding: utf-8 -*-
"""
后端 ORM (domain.py) 适配脚本 v2

背景：SQL 层已将以下关键字列改名，但为了避免影响 API 契约和前端，
     Python 属性名保持不变，只改 SQLAlchemy 层的 DB 列名。

策略：把
    status: Mapped[str] = mapped_column(String(24), ...)
改为
    status: Mapped[str] = mapped_column("row_status", String(24), ...)

改名映射（DB 列名 <- Python 属性名）：
- status  -> row_status
- method  -> method_code
- action  -> action_type
- role    -> role_code

注意：
- audit_log 已有 status_code 列，Python 属性也是 status_code，不动
- 只修改属性名精确匹配的行（前导缩进 + 关键字 + ": Mapped"）
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


def rewrite_line(line: str, py_attr: str, db_col: str) -> str:
    """
    把 `    status: Mapped[...] = mapped_column(String(24), ...)`
    改为 `    status: Mapped[...] = mapped_column("row_status", String(24), ...)`
    如果 mapped_column 内首个参数是字符串（说明已经显式指定列名），跳过。
    """
    # 匹配：<indent><attr>: Mapped[...] = mapped_column(<first_arg>...
    pattern = re.compile(
        r"^(\s+)" + re.escape(py_attr) + r"(\s*:\s*Mapped\[[^\]]+\]\s*=\s*mapped_column\()"
    )
    m = pattern.match(line)
    if not m:
        return line
    indent = m.group(1)
    prefix_group = m.group(2)  # ": Mapped[...] = mapped_column("
    rest = line[m.end():]
    # 检查 rest 是否已经以字符串字面量开头（表示已指定列名）
    stripped_rest = rest.lstrip()
    if stripped_rest.startswith('"') or stripped_rest.startswith("'"):
        return line
    # 插入 db 列名作为首个位置参数
    return f"{indent}{py_attr}{prefix_group}\"{db_col}\", {rest}"


def process_file(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    changed = 0
    for i, line in enumerate(lines):
        for py_attr, db_col in RENAMES.items():
            new_line = rewrite_line(line, py_attr, db_col)
            if new_line != line:
                lines[i] = new_line
                changed += 1
                break  # 一行只可能匹配一个属性

    new_text = "\n".join(lines)
    path.write_text(new_text, encoding="utf-8")
    print(f"OK: {path.name} rewrote {changed} lines")


if __name__ == "__main__":
    process_file(DOMAIN_PATH)
