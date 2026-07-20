from collections.abc import Generator
import re

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# MySQL 连接超时：过短会导致鉴权中间件偶发 503，前端误踢登录。
# 启动探针仍依赖 /health/live（不查库），不必为启动把超时压到 3s。
_connect_args: dict = {}
if settings.database_url.startswith(("mysql", "mariadb")):
    _connect_args["connect_timeout"] = 8

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

FORBIDDEN_MYSQL_RUNTIME_PREFIXES = (
    "call",
    "delete",
    "create",
    "drop",
    "alter",
    "truncate",
    "replace",
    "set",
    "rename",
)


class DatabaseOperationPolicyError(RuntimeError):
    pass


_SQL_OPERATIONS = {
    "alter",
    "call",
    "create",
    "delete",
    "drop",
    "insert",
    "prepare",
    "rename",
    "replace",
    "select",
    "set",
    "truncate",
    "update",
}


def _normalize_mysql_comments(statement: str) -> str:
    """Remove ordinary comments and expose MySQL/MariaDB executable comments."""
    output: list[str] = []
    index = 0
    length = len(statement)
    while index < length:
        char = statement[index]
        if char in {"'", '"', "`"}:
            quote = char
            start = index
            index += 1
            while index < length:
                if statement[index] == "\\":
                    index += 2
                    continue
                if statement[index] == quote:
                    if index + 1 < length and statement[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            output.append(statement[start:index])
            continue
        dash_comment = (
            statement.startswith("--", index)
            and (
                index + 2 >= length
                or statement[index + 2].isspace()
                or ord(statement[index + 2]) <= 32
            )
        )
        if dash_comment or char == "#":
            line_end = statement.find("\n", index)
            index = length if line_end < 0 else line_end + 1
            output.append(" ")
            continue
        if statement.startswith("/*", index):
            comment_end = statement.find("*/", index + 2)
            if comment_end < 0:
                return "".join(output)
            body = statement[index + 2 : comment_end]
            executable = body.startswith("!") or body.upper().startswith("M!")
            if executable:
                body = body[1:] if body.startswith("!") else body[2:]
                body = re.sub(r"^\s*\d{5,6}\s*", "", body)
                output.extend((" ", body, " "))
            else:
                output.append(" ")
            index = comment_end + 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _top_level_statements(statement: str) -> list[str]:
    statements: list[str] = []
    statement_start = 0
    depth = 0
    index = 0
    length = len(statement)
    while index < length:
        char = statement[index]
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            while index < length:
                if statement[index] == "\\":
                    index += 2
                    continue
                if statement[index] == quote:
                    if index + 1 < length and statement[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if char == ";" and depth == 0:
            segment = statement[statement_start:index].strip()
            if segment:
                statements.append(segment)
            statement_start = index + 1
            index += 1
            continue
        index += 1
    segment = statement[statement_start:].strip()
    if segment:
        statements.append(segment)
    return statements


def _top_level_word_tokens(statement: str) -> list[tuple[str, int, int]]:
    tokens: list[tuple[str, int, int]] = []
    depth = 0
    index = 0
    length = len(statement)
    while index < length:
        char = statement[index]
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            while index < length:
                if statement[index] == "\\":
                    index += 2
                    continue
                if statement[index] == quote:
                    if index + 1 < length and statement[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0 and (char.isalpha() or char == "_"):
            end = index + 1
            while end < length and (statement[end].isalnum() or statement[end] in {"_", "$"}):
                end += 1
            tokens.append((statement[index:end].lower(), index, end))
            index = end
            continue
        index += 1
    return tokens


def _decode_mysql_string_literal(statement: str, start: int) -> str | None:
    if start >= len(statement) or statement[start] != "'":
        return None
    output: list[str] = []
    index = start + 1
    while index < len(statement):
        char = statement[index]
        if char == "\\":
            # Dynamic SQL decoding must fail closed; MySQL escape semantics depend on
            # sql_mode and are unsafe to reinterpret in the runtime policy guard.
            return None
        if char == "'":
            if index + 1 < len(statement) and statement[index + 1] == "'":
                output.append("'")
                index += 2
                continue
            return "".join(output)
        output.append(char)
        index += 1
    return None


def _prepare_literal_sql(statement: str) -> str | None:
    tokens = _top_level_word_tokens(statement)
    from_token = next((token for token in tokens if token[0] == "from"), None)
    if from_token is None:
        return None
    index = from_token[2]
    while index < len(statement) and statement[index].isspace():
        index += 1
    return _decode_mysql_string_literal(statement, index)


def _statement_operation(words: list[str]) -> str | None:
    if not words:
        return None
    if words[0] != "with":
        return words[0]
    for word in words[1:]:
        if word in _SQL_OPERATIONS:
            return word
    return None


def forbidden_mysql_runtime_operation(statement: str) -> str | None:
    """Return the first forbidden operation, including CTE and executable-comment forms."""
    sql = _normalize_mysql_comments(statement)
    for segment in _top_level_statements(sql):
        words = [word for word, _start, _end in _top_level_word_tokens(segment)]
        operation = _statement_operation(words)
        if operation in FORBIDDEN_MYSQL_RUNTIME_PREFIXES:
            return operation
        if operation == "prepare":
            prepared_sql = _prepare_literal_sql(segment)
            if prepared_sql is None:
                return "prepare"
            nested_operation = forbidden_mysql_runtime_operation(prepared_sql)
            if nested_operation:
                return nested_operation
    return None


@event.listens_for(engine, "before_cursor_execute")
def enforce_mysql_operation_policy(conn, cursor, statement, parameters, context, executemany) -> None:
    if conn.dialect.name not in {"mysql", "mariadb"}:
        return
    operation = forbidden_mysql_runtime_operation(statement)
    if operation:
        raise DatabaseOperationPolicyError(
            f"MySQL runtime SQL '{operation.upper()}' is forbidden by company policy; "
            "schema changes require DBA approval and physical deletes must be replaced "
            "by status/version workflows."
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
