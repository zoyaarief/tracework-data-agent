from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from .database import Database
from .schemas import TraceStep


class AgentTools:
    def __init__(self, database: Database):
        self.database = database
        self.trace: list[TraceStep] = []
        self.last_columns: list[str] = []
        self.last_rows: list[dict[str, Any]] = []

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "inspect_schema",
                "description": "Inspect available tables, columns, types, and foreign-key relationships before writing SQL.",
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                "strict": True,
            },
            {
                "type": "function",
                "name": "execute_sql",
                "description": "Execute one read-only SELECT query. Results are automatically capped. Never use writes, DDL, PRAGMAs, or control statements.",
                "parameters": {
                    "type": "object",
                    "properties": {"sql": {"type": "string", "description": "A single read-only SELECT statement."}},
                    "required": ["sql"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "analyze_results",
                "description": "Compute a compact profile of the most recent SQL result, including numeric ranges and null counts.",
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                "strict": True,
            },
        ]

    def _record(self, title: str, detail: str, tool: str, started_at: float, status: str = "complete") -> None:
        self.trace.append(
            TraceStep(
                id=len(self.trace) + 1,
                title=title,
                detail=detail,
                tool=tool,
                duration_ms=max(1, round((time.perf_counter() - started_at) * 1000)),
                status=status,
            )
        )

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "inspect_schema": self.inspect_schema,
            "execute_sql": self.execute_sql,
            "analyze_results": self.analyze_results,
        }
        if name not in handlers:
            raise ValueError(f"Unknown tool: {name}")
        return handlers[name](arguments)

    def inspect_schema(self, _: dict[str, Any] | None = None) -> dict[str, Any]:
        started_at = time.perf_counter()
        schema = self.database.inspect_schema()
        relationship_count = sum(len(table["foreign_keys"]) for table in schema["tables"])
        self._record(
            "Inspected database schema",
            f"Found {len(schema['tables'])} tables and {relationship_count} relationships",
            "inspect_schema",
            started_at,
        )
        return schema

    def execute_sql(self, arguments: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        sql = arguments.get("sql")
        if not isinstance(sql, str):
            raise ValueError("sql must be a string")
        try:
            validated, columns, rows = self.database.execute_readonly(sql)
        except Exception:
            self._record(
                "SQL query failed",
                "The generated query was rejected or could not execute",
                "execute_sql",
                started_at,
                "error",
            )
            raise
        self.last_columns = columns
        self.last_rows = rows
        self._record(
            "Executed read-only query",
            f"Returned {len(rows)} rows across {len(columns)} columns",
            "execute_sql",
            started_at,
        )
        return {
            "sql": validated.sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated_at": validated.row_limit,
        }

    def analyze_results(self, _: dict[str, Any] | None = None) -> dict[str, Any]:
        started_at = time.perf_counter()
        if not self.last_columns:
            raise ValueError("No query result is available to analyze")
        profile: dict[str, Any] = {"row_count": len(self.last_rows), "columns": {}}
        for column in self.last_columns:
            values = [row[column] for row in self.last_rows if row.get(column) is not None]
            numeric = [
                float(value)
                for value in values
                if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
            ]
            details: dict[str, Any] = {"non_null": len(values), "null": len(self.last_rows) - len(values)}
            if numeric:
                details.update({"min": min(numeric), "max": max(numeric), "mean": statistics.fmean(numeric)})
            profile["columns"][column] = details
        self._record(
            "Analyzed query result",
            f"Profiled {len(self.last_columns)} columns for completeness and numeric ranges",
            "analyze_results",
            started_at,
        )
        return profile

    @staticmethod
    def as_tool_output(value: dict[str, Any]) -> str:
        return json.dumps(value, default=str, separators=(",", ":"))
