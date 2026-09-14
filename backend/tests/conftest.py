from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.database import Database
from backend.app.seed import seed_demo_database


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        openai_api_key=None,
        max_query_rows=25,
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    db = Database(settings)
    seed_demo_database(db.engine)
    yield db
    db.engine.dispose()
