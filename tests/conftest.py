from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import database
import settings


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("AUTH_DEV_PASSWORD", "Admin123!!")
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
    settings.get_settings.cache_clear()

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


@pytest.fixture()
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!!",
            "next": "/",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client
