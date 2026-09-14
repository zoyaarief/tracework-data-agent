from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.engine import Connection

from .config import Settings
from .sql_guard import ValidatedQuery, validate_readonly_sql


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        connect_args: dict[str, Any] = {}
        if settings.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False, "timeout": settings.query_timeout_seconds}
        self.engine: Engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)

        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._configure_sqlite)

    @staticmethod
    def _configure_sqlite(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 8000")
        cursor.close()

    @property
    def dialect(self) -> str:
        return "postgres" if self.engine.dialect.name == "postgresql" else "sqlite"

    @contextmanager
    def readonly_connection(self) -> Iterator[Connection]:
        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                if self.engine.dialect.name == "sqlite":
                    connection.exec_driver_sql("PRAGMA query_only = ON")
                elif self.engine.dialect.name == "postgresql":
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                    connection.execute(
                        text("SET LOCAL statement_timeout = :timeout"),
                        {"timeout": self.settings.query_timeout_seconds * 1000},
                    )
                yield connection
            finally:
                transaction.rollback()

    def inspect_schema(self) -> dict[str, Any]:
        inspector = inspect(self.engine)
        tables: list[dict[str, Any]] = []
        for table_name in sorted(inspector.get_table_names()):
            columns = [
                {"name": column["name"], "type": str(column["type"]), "nullable": column["nullable"]}
                for column in inspector.get_columns(table_name)
            ]
            foreign_keys = [
                {
                    "columns": key.get("constrained_columns", []),
                    "references": f"{key.get('referred_table')}({', '.join(key.get('referred_columns', []))})",
                }
                for key in inspector.get_foreign_keys(table_name)
            ]
            tables.append({"name": table_name, "columns": columns, "foreign_keys": foreign_keys})
        return {"dialect": self.dialect, "tables": tables}

    def execute_readonly(self, sql: str) -> tuple[ValidatedQuery, list[str], list[dict[str, Any]]]:
        validated = validate_readonly_sql(sql, dialect=self.dialect, max_rows=self.settings.max_query_rows)
        with self.readonly_connection() as connection:
            result = connection.execute(text(validated.sql))
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result.fetchall()]
        return validated, columns, rows

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))


def ensure_sqlite_parent(settings: Settings) -> None:
    if not settings.database_url.startswith("sqlite:///"):
        return
    database_path = Path(settings.database_url.removeprefix("sqlite:///"))
    database_path.parent.mkdir(parents=True, exist_ok=True)
