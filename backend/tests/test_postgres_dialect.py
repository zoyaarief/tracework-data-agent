"""Postgres-dialect regressions.

The app advertises Postgres support but nothing in compose or .env.example ever
points at one, so these paths had never been executed. Set
TRACEWORK_TEST_POSTGRES_URL to run them, e.g.

    docker run -d --name tracework-pg -e POSTGRES_PASSWORD=tracework \\
      -e POSTGRES_USER=tracework -e POSTGRES_DB=tracework -p 55432:5432 postgres:16
    export TRACEWORK_TEST_POSTGRES_URL=postgresql+psycopg://tracework:tracework@localhost:55432/tracework
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from backend.app.agent import DeterministicInvestigator
from backend.app.config import Settings
from backend.app.database import Database
from backend.app.seed import SCHEMA

POSTGRES_URL = os.environ.get("TRACEWORK_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="TRACEWORK_TEST_POSTGRES_URL is not set; skipping Postgres-dialect tests"
)


@pytest.fixture
def postgres_database() -> Database:
    database = Database(Settings(database_url=POSTGRES_URL, openai_api_key=None, max_query_rows=25))
    with database.engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        connection.commit()
    yield database
    database.engine.dispose()


def test_readonly_connection_works_on_postgres(postgres_database: Database) -> None:
    """SET LOCAL takes a literal, not a bind parameter, so every query used to fail."""
    _, columns, rows = postgres_database.execute_readonly("SELECT 1 AS n")

    assert columns == ["n"]
    assert rows == [{"n": 1}]


def test_readonly_connection_still_applies_a_statement_timeout(postgres_database: Database) -> None:
    """The timeout is the reason the SET exists; interpolating it must not drop it."""
    with postgres_database.readonly_connection() as connection:
        timeout = connection.execute(text("SHOW statement_timeout")).scalar_one()

    assert timeout == "8s"


def test_churn_investigation_works_on_postgres(postgres_database: Database) -> None:
    """strftime is SQLite-only; the churn branch has to use a portable month expression."""
    with postgres_database.engine.connect() as connection:
        connection.execute(
            text("INSERT INTO customers VALUES (1,'A','West','SMB','2025-01-01','2025-06-15')")
        )
        connection.execute(
            text("INSERT INTO customers VALUES (2,'B','West','SMB','2025-01-01','2025-06-20')")
        )
        connection.execute(text("INSERT INTO customers VALUES (3,'C','West','SMB','2025-01-01',NULL)"))
        connection.commit()

    response = DeterministicInvestigator(postgres_database).investigate("how has churn trended")

    assert "2 churned customers" in response.answer
    assert response.evidence == [{"month": "2025-06", "churned_customers": 2}]
