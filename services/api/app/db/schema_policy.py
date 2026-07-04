from sqlalchemy.exc import OperationalError, ProgrammingError


def missing_table_name(exc: ProgrammingError) -> str | None:
    """Return the missing MySQL table name for a schema mismatch error."""
    orig_args = getattr(getattr(exc, "orig", None), "args", ())
    if not orig_args or orig_args[0] != 1146:
        return None
    message = str(orig_args[1]) if len(orig_args) > 1 else str(exc)
    marker = "Table '"
    if marker not in message:
        return None
    table_ref = message.split(marker, 1)[1].split("'", 1)[0]
    return table_ref.split(".", 1)[-1]


def missing_column_name(exc: OperationalError) -> str | None:
    """Return the missing MySQL column name for a schema mismatch error."""
    orig_args = getattr(getattr(exc, "orig", None), "args", ())
    if not orig_args or orig_args[0] != 1054:
        return None
    message = str(orig_args[1]) if len(orig_args) > 1 else str(exc)
    marker = "Unknown column '"
    if marker not in message:
        return None
    return message.split(marker, 1)[1].split("'", 1)[0]
