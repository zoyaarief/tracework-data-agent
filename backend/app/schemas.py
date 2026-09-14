from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question cannot be blank")
        return value


class TraceStep(BaseModel):
    id: int
    title: str
    detail: str
    tool: str
    duration_ms: int
    status: Literal["complete", "error"] = "complete"


class InvestigationResponse(BaseModel):
    question: str
    answer: str
    columns: list[str]
    evidence: list[dict[str, Any]]
    trace: list[TraceStep]
    mode: Literal["demo", "openai"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: str
    agent_mode: Literal["demo", "openai"]
