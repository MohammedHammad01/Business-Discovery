from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Tests must never reach a real provider: no key + mock allowed => mock agent.
os.environ["GEMINI_API_KEY"] = ""
os.environ["ALLOW_MOCK_LLM"] = "true"
# The module-level engine stays in memory; each test gets its own file-backed one.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    """A TestClient backed by a throwaway SQLite file."""
    from app.db.session import Base, get_db
    from app.main import create_app

    import app.models  # noqa: F401  (registers mappers)

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()


@pytest.fixture()
def project(client):
    response = client.post("/api/projects", json={"name": "Approval automation", "client_name": "Acme"})
    assert response.status_code == 201
    return response.json()
