import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aje.api.profile import get_db_session
from aje.app import create_app
from aje.extraction import merge as merge_mod
from aje.extraction.schema import ProfileData, Skill


class _FakeStructured:
    def __init__(self, result):
        self._result = result

    def invoke(self, messages):
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self._result = result

    def with_structured_output(self, schema):
        return _FakeStructured(self._result)


def _client(session):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    return TestClient(app)


def _linkedin_bytes(tmp_path: Path) -> bytes:
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("Skills.csv", "Name\nPython\n")
    return z.read_bytes()


def test_ingest_then_get_profile(session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        merge_mod,
        "llm_for",
        lambda task: _FakeLLM(ProfileData(skills=[Skill(name="Python", source_refs=[1])])),
    )
    client = _client(session)

    resp = client.post(
        "/profile/ingest",
        files={"file": ("linkedin.zip", _linkedin_bytes(tmp_path), "application/zip")},
    )
    assert resp.status_code == 200
    assert resp.json()["skills"][0]["name"] == "Python"

    got = client.get("/profile")
    assert got.json()["skills"][0]["name"] == "Python"


def test_ingest_unsupported_type_returns_400(session):
    client = _client(session)
    resp = client.post(
        "/profile/ingest",
        files={"file": ("notes.txt", b"hi", "text/plain")},
    )
    assert resp.status_code == 400


def test_put_profile_edits(session):
    client = _client(session)
    body = {"skills": [{"name": "Edited", "source_refs": []}]}
    resp = client.put("/profile", json=body)
    assert resp.status_code == 200
    assert client.get("/profile").json()["skills"][0]["name"] == "Edited"


def test_source_documents_listed(session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        merge_mod, "llm_for", lambda task: _FakeLLM(ProfileData(skills=[Skill(name="Go")]))
    )
    client = _client(session)
    client.post(
        "/profile/ingest",
        files={"file": ("linkedin.zip", _linkedin_bytes(tmp_path), "application/zip")},
    )
    docs = client.get("/source-documents").json()
    assert len(docs) == 1 and docs[0]["status"] == "parsed"
