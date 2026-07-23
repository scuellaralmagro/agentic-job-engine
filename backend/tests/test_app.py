from fastapi.testclient import TestClient

from aje.app import create_app


def test_health_ok():
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_health_db_and_vec(tmp_path, monkeypatch):
    monkeypatch.setenv("AJE_DATABASE_URL", f"sqlite:///{(tmp_path / 'h.sqlite3').as_posix()}")
    import aje.db as db

    db.get_engine.cache_clear()
    client = TestClient(create_app())
    assert client.get("/health/db").json() == {"database": "ok"}
    assert client.get("/health/vec").json()["sqlite_vec"]
