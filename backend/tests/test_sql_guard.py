from __future__ import annotations

import pytest

from backend.app.sql_guard import UnsafeQueryError, validate_readonly_sql


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET status = 'cancelled'",
        "SELECT 1; DROP TABLE orders",
        "PRAGMA table_info(orders)",
        "SELECT * FROM orders LIMIT -1",
    ],
)
def test_guard_rejects_non_readonly_or_unbounded_shapes(sql: str) -> None:
    with pytest.raises(UnsafeQueryError):
        validate_readonly_sql(sql, dialect="sqlite", max_rows=20)


def test_guard_adds_and_caps_limit() -> None:
    missing = validate_readonly_sql("SELECT * FROM orders", dialect="sqlite", max_rows=20)
    excessive = validate_readonly_sql("SELECT * FROM orders LIMIT 500", dialect="sqlite", max_rows=20)

    assert missing.sql.endswith("LIMIT 20")
    assert excessive.sql.endswith("LIMIT 20")
