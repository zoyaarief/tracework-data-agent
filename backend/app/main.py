from __future__ import annotations

from contextlib import asynccontextmanager

from anyio import to_thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .agent import build_investigator
from .config import Settings, get_settings
from .database import Database, ensure_sqlite_parent
from .schemas import HealthResponse, InvestigationRequest, InvestigationResponse
from .seed import seed_demo_database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    ensure_sqlite_parent(settings)
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        seed_demo_database(database.engine)
        yield
        database.engine.dispose()

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        await to_thread.run_sync(request.app.state.database.ping)
        active_settings: Settings = request.app.state.settings
        return HealthResponse(
            status="ok",
            database=request.app.state.database.dialect,
            agent_mode="openai" if active_settings.openai_api_key else "demo",
        )

    @app.get("/api/schema")
    async def schema(request: Request) -> dict:
        return await to_thread.run_sync(request.app.state.database.inspect_schema)

    @app.post("/api/investigations", response_model=InvestigationResponse)
    async def investigate(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
        investigator = build_investigator(request.app.state.database, request.app.state.settings)
        try:
            return await to_thread.run_sync(investigator.investigate, payload.question)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="The investigation could not be completed") from exc

    return app


app = create_app()
