import pytest

from aje.adaptation import cover_letter as letter_mod
from aje.adaptation import render as render_mod
from aje.adaptation.config import CvConfig
from aje.adaptation.persist import render_cover_letter
from aje.adaptation.schema import CoverLetterContent
from aje.adaptation.validate import AnchorError
from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Contact, Experience, ProfileData, Skill
from aje.models import CoverLetter, GeneratedDoc, Match, Offer


class _CountingLLM:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        self.calls += 1
        return self._result.model_copy(deep=True)


def _content(**overrides) -> CoverLetterContent:
    base = dict(
        language="en",
        salutation="Dear hiring team,",
        paragraphs=["I have built billing APIs in Python for three years."],
        closing="Kind regards, Ada Lovelace",
    )
    base.update(overrides)
    return CoverLetterContent(**base)


@pytest.fixture
def profile(session):
    save_profile(
        session,
        ProfileData(
            contact=Contact(full_name="Ada Lovelace"),
            skills=[Skill(name="Python")],
            experiences=[
                Experience(company="Acme", title="Backend Engineer", bullets=["Billing API"])
            ],
        ),
    )


@pytest.fixture
def match(session):
    offer = Offer(
        title="Senior Backend Engineer",
        company="Globex",
        description="Python and API design.",
        source="test",
        content_hash="h1",
        skills=["Python", "Kubernetes"],
    )
    session.add(offer)
    session.commit()
    row = Match(offer_id=offer.id, profile_id=1, fitness=78.0, status="accepted")
    session.add(row)
    session.commit()
    return row


def test_a_letter_is_written_and_stored(session, profile, match, monkeypatch):
    llm = _CountingLLM(_content())
    monkeypatch.setattr(letter_mod, "llm_for", lambda task: llm)

    letter = letter_mod.write_cover_letter(session, match.id, config=CvConfig())

    assert llm.calls == 1
    assert letter.match_id == match.id
    assert letter.offer_id == match.offer_id
    assert letter.language == "en"
    assert letter.content_json["salutation"] == "Dear hiring team,"


def test_a_letter_claiming_an_absent_skill_is_rejected(session, profile, match, monkeypatch):
    bad = _content(paragraphs=["I run Kubernetes clusters at scale."])
    monkeypatch.setattr(letter_mod, "llm_for", lambda task: _CountingLLM(bad))

    with pytest.raises(AnchorError, match="Kubernetes"):
        letter_mod.write_cover_letter(session, match.id, config=CvConfig())

    assert session.query(CoverLetter).count() == 0


def test_the_language_override_wins(session, profile, match, monkeypatch):
    monkeypatch.setattr(letter_mod, "llm_for", lambda task: _CountingLLM(_content()))

    letter = letter_mod.write_cover_letter(
        session, match.id, language="es", config=CvConfig()
    )

    assert letter.language == "es"


def test_an_unknown_match_raises(session, profile, monkeypatch):
    monkeypatch.setattr(letter_mod, "llm_for", lambda task: _CountingLLM(_content()))

    with pytest.raises(ValueError, match="match 999 not found"):
        letter_mod.write_cover_letter(session, 999, config=CvConfig())


def test_rendering_a_letter_writes_a_pdf_row(session, profile, match, monkeypatch):
    monkeypatch.setattr(letter_mod, "llm_for", lambda task: _CountingLLM(_content()))
    captured = {}

    def _fake(html, page):
        captured["html"] = html
        return b"%PDF-1.4 fake"

    render_mod.register_pdf_engine("fake", _fake)
    monkeypatch.setattr(render_mod, "DEFAULT_ENGINE", "fake")
    letter = letter_mod.write_cover_letter(session, match.id, config=CvConfig())

    doc = render_cover_letter(session, letter.id, config=CvConfig())

    assert doc.kind == "cover_letter"
    assert doc.cv_projection_id is None
    assert "Dear hiring team," in captured["html"]
    assert "billing APIs in Python" in captured["html"]
    assert session.query(GeneratedDoc).count() == 1
