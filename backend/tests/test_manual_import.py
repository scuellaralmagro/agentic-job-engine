import httpx
import pytest

from aje.discovery import manual
from aje.discovery.schema import RawOffer
from aje.models import Offer


class _FakeStructured:
    def __init__(self, result):
        self._result = result
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self.structured = _FakeStructured(result)

    def with_structured_output(self, schema):
        return self.structured


def _canned(**overrides):
    fields = {
        "title": "Backend Dev",
        "company": "Acme",
        "location": "Madrid",
        "description": "Python",
        "url": None,
        "source": "manual",
    }
    fields.update(overrides)
    return RawOffer(**fields)


def test_import_text_persists_offer(session, monkeypatch):
    monkeypatch.setattr(manual, "llm_for", lambda task: _FakeLLM(_canned()))

    offer = manual.import_offer(session, text="Backend Dev at Acme in Madrid")

    assert offer.id is not None
    assert offer.title == "Backend Dev"
    assert offer.source == "manual"
    assert session.query(Offer).count() == 1


def test_import_forces_manual_source_and_keeps_url(session, monkeypatch):
    monkeypatch.setattr(
        manual, "llm_for", lambda task: _FakeLLM(_canned(source="linkedin"))
    )

    offer = manual.import_offer(
        session, text="whatever", url="https://example.com/job/1"
    )

    assert offer.source == "manual"
    assert offer.url == "https://example.com/job/1"


def test_import_url_fetches_then_structures(session, monkeypatch):
    monkeypatch.setattr(manual, "llm_for", lambda task: _FakeLLM(_canned()))
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, text="<html><body>Backend Dev at Acme</body></html>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    offer = manual.import_offer(session, url="https://example.com/job/1", client=client)

    assert seen["url"] == "https://example.com/job/1"
    assert offer.title == "Backend Dev"


def test_duplicate_import_returns_existing_row(session, monkeypatch):
    monkeypatch.setattr(manual, "llm_for", lambda task: _FakeLLM(_canned()))

    first = manual.import_offer(session, text="a")
    second = manual.import_offer(session, text="a")

    assert first.id == second.id
    assert session.query(Offer).count() == 1


def test_requires_text_or_url(session):
    with pytest.raises(manual.ManualImportError):
        manual.import_offer(session)
