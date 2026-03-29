from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import database


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data_dir = tmp_path / "data"
    db_path = data_dir / "test_editorial.db"
    monkeypatch.setattr(database, "DATA_DIR", data_dir)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_database()

    with database.get_connection() as connection:
        connection.execute("DELETE FROM presupuestos")

    from main import app

    with TestClient(app) as test_client:
        yield test_client
