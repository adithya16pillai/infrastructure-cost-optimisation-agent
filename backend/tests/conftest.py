from __future__ import annotations

import os
import tempfile

_TMP_DB = os.path.join(tempfile.gettempdir(), "cost_optimizer_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["MOCK_AWS"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""  # force heuristic validator

import pytest  # noqa: E402

from app.db import Base, engine, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
