from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.app.agent import DeterministicInvestigator
from backend.app.config import Settings
from backend.app.database import Database
from backend.app.seed import SCHEMA
from backend.app.sql_guard import validate_readonly_sql
from backend.app.tools import AgentTools


@pytest.fixture
def empty_schema_database(tmp_path: Path) -> Database:
    database = Database(Settings(database_url=f"sqlite:///{tmp_path / 'review.db'}", openai_api_key=None))
    with database.engine.connect() as connection:
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        connection.commit()
    yield database
    database.engine.dispose()


def test_growth_answer_survives_a_category_with_no_prior_quarter(empty_schema_database: Database) -> None:
    """A category that only sold in Q3 makes NULLIF(q2_revenue, 0) return NULL for growth_pct."""
    with empty_schema_database.engine.connect() as connection:
        connection.exec_driver_sql("INSERT INTO customers VALUES (1,'A','West','SMB','2025-01-01',NULL)")
        connection.exec_driver_sql("INSERT INTO products VALUES (1,'NewThing','BrandNew',100)")
        connection.exec_driver_sql("INSERT INTO orders VALUES (1,1,'2025-08-01','completed',100)")
        connection.exec_driver_sql("INSERT INTO order_items VALUES (1,1,1,1,100)")
        connection.commit()

    response = DeterministicInvestigator(empty_schema_database).investigate("what drove revenue growth")

    assert "BrandNew" in response.answer


def test_readonly_query_does_not_poison_the_pooled_connection(empty_schema_database: Database) -> None:
    """PRAGMA query_only is connection state; it must not survive back into the pool."""
    empty_schema_database.execute_readonly("SELECT id FROM customers")

    with empty_schema_database.engine.connect() as connection:
        connection.execute(text("INSERT INTO customers VALUES (9,'B','West','SMB','2025-01-01',NULL)"))
        connection.commit()

    with empty_schema_database.engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM customers").scalar_one() == 1


def test_row_limit_reports_the_effective_limit_not_the_cap() -> None:
    """truncated_at tells the model where the result was cut; a smaller user LIMIT is the real cut."""
    validated = validate_readonly_sql("SELECT * FROM orders LIMIT 5", dialect="sqlite", max_rows=25)

    assert validated.row_limit == 5


def test_decimal_columns_are_profiled_numerically(empty_schema_database: Database) -> None:
    """Postgres NUMERIC arrives as Decimal; money columns must still get min/max/mean."""
    tools = AgentTools(empty_schema_database)
    tools.last_columns = ["amount"]
    tools.last_rows = [{"amount": Decimal("10.5")}, {"amount": Decimal("20.5")}]

    profile = tools.analyze_results()["columns"]["amount"]

    assert profile["min"] == 10.5
    assert profile["max"] == 20.5
    assert profile["mean"] == 15.5


def test_boolean_columns_are_not_profiled_as_numeric(empty_schema_database: Database) -> None:
    """bool is a subclass of int, so a flag column silently reports a meaningless mean."""
    tools = AgentTools(empty_schema_database)
    tools.last_columns = ["is_active"]
    tools.last_rows = [{"is_active": True}, {"is_active": False}, {"is_active": True}]

    profile = tools.analyze_results()["columns"]["is_active"]

    assert "mean" not in profile
    assert profile["non_null"] == 3
