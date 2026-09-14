from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class UnsafeQueryError(ValueError):
    """Raised when generated SQL violates the read-only query policy."""


@dataclass(frozen=True)
class ValidatedQuery:
    sql: str
    row_limit: int


FORBIDDEN_NODES = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Grant,
    exp.Insert,
    exp.Into,
    exp.Merge,
    exp.Revoke,
    exp.Transaction,
    exp.Update,
)

FORBIDDEN_FUNCTIONS = {
    "dblink_connect",
    "dblink_exec",
    "load_extension",
    "pg_cancel_backend",
    "pg_ls_dir",
    "pg_read_file",
    "pg_sleep",
    "pg_terminate_backend",
    "readfile",
    "set_config",
    "writefile",
}


def validate_readonly_sql(sql: str, *, dialect: str, max_rows: int) -> ValidatedQuery:
    if not sql or not sql.strip():
        raise UnsafeQueryError("SQL cannot be empty")
    if max_rows < 1:
        raise ValueError("max_rows must be positive")

    try:
        statements = [statement for statement in parse(sql, read=dialect) if statement is not None]
    except ParseError as exc:
        raise UnsafeQueryError(f"SQL could not be parsed: {exc}") from exc

    if len(statements) != 1:
        raise UnsafeQueryError("Exactly one SQL statement is allowed")

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise UnsafeQueryError("Only SELECT queries are allowed")
    if any(statement.find(node_type) is not None for node_type in FORBIDDEN_NODES):
        raise UnsafeQueryError("The query contains a forbidden write or control operation")
    called_functions = {function.name.lower() for function in statement.find_all(exp.Anonymous)}
    blocked_functions = sorted(called_functions & FORBIDDEN_FUNCTIONS)
    if blocked_functions:
        raise UnsafeQueryError(f"The query calls a forbidden function: {blocked_functions[0]}")

    requested_limit = statement.args.get("limit")
    if requested_limit is None:
        statement = statement.limit(max_rows)
        effective_limit = max_rows
    else:
        limit_expression = requested_limit.expression
        if not isinstance(limit_expression, exp.Literal) or not limit_expression.is_int:
            raise UnsafeQueryError("LIMIT must be a positive integer literal")
        limit = int(limit_expression.this)
        if limit < 1:
            raise UnsafeQueryError("LIMIT must be a positive integer")
        if limit > max_rows:
            statement.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
        effective_limit = min(limit, max_rows)

    return ValidatedQuery(sql=statement.sql(dialect=dialect), row_limit=effective_limit)
