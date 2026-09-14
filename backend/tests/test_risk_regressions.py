from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.agent import OpenAIInvestigator
from backend.app.config import Settings
from backend.app.database import Database
from backend.app.seed import seed_demo_database
from backend.app.sql_guard import UnsafeQueryError, validate_readonly_sql


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            tool_call = SimpleNamespace(
                type="function_call",
                name="execute_sql",
                arguments=json.dumps({"sql": "SELECT 1 AS value"}),
                call_id="call_1",
            )
            return SimpleNamespace(id="resp_1", output=[tool_call], output_text="")
        return SimpleNamespace(id="resp_2", output=[], output_text="The evidence query returned one row with value 1.")


def test_stateless_responses_loop_carries_prior_output(database: Database, settings: Settings) -> None:
    fake_responses = FakeResponses()
    fake_client = SimpleNamespace(responses=fake_responses)

    OpenAIInvestigator(database, settings, client=fake_client).investigate("Return one evidence row")

    continuation = fake_responses.calls[1]
    assert "previous_response_id" not in continuation
    assert continuation["input"][0]["role"] == "user"
    assert continuation["input"][1].type == "function_call"
    assert continuation["input"][2]["type"] == "function_call_output"


@pytest.mark.parametrize(
    ("dialect", "sql"),
    [
        ("postgres", "SELECT pg_sleep(10)"),
        ("postgres", "SELECT pg_terminate_backend(123)"),
        ("sqlite", "SELECT load_extension('/tmp/unsafe')"),
    ],
)
def test_sql_guard_rejects_dangerous_select_functions(dialect: str, sql: str) -> None:
    with pytest.raises(UnsafeQueryError):
        validate_readonly_sql(sql, dialect=dialect, max_rows=20)


def test_concurrent_sqlite_seed_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "concurrent.db"
    database = Database(Settings(database_url=f"sqlite:///{database_path}"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(seed_demo_database, database.engine) for _ in range(2)]
        for future in futures:
            future.result(timeout=15)

    with database.engine.connect() as connection:
        count = connection.exec_driver_sql("SELECT COUNT(*) FROM customers").scalar_one()
    assert count == 400
