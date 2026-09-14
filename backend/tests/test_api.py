from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_and_schema(settings) -> None:
    with TestClient(create_app(settings)) as client:
        health = client.get("/health")
        schema = client.get("/api/schema")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "sqlite", "agent_mode": "demo"}
    assert {table["name"] for table in schema.json()["tables"]} == {
        "customers",
        "order_items",
        "orders",
        "products",
        "refunds",
    }


def test_demo_investigation_returns_evidence_and_trace(settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/investigations",
            json={"question": "Which region has the highest average order value?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "demo"
    assert body["row_limit"] == settings.max_query_rows
    assert body["evidence"]
    assert body["columns"] == ["region", "avg_order_value", "order_count", "revenue"]
    assert [step["tool"] for step in body["trace"]] == [
        "inspect_schema",
        "execute_sql",
        "analyze_results",
        "generate_answer",
    ]


def test_blank_question_is_rejected(settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/investigations", json={"question": "   "})

    assert response.status_code == 422
