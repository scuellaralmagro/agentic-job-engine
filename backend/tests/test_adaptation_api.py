import pytest
from fastapi.testclient import TestClient

from aje.adaptation import draft as draft_mod
from aje.adaptation import render as render_mod
from aje.adaptation.schema import (
    AdaptationResult,
    Suggestion,
    TailoredBullet,
    TailoredCv,
    TailoredExperience,
)
from aje.api.profile import get_db_session
from aje.app import create_app
from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Contact, Experience, ProfileData, Skill
from aje.models import CoverLetter, GeneratedDoc, Match, Offer

EXP_KEY = "experience:acme|backend engineer"


class _FakeLLM:
    def __init__(self, result):
        self._result = result

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return self._result.model_copy(deep=True)


def _result(**cv_overrides) -> AdaptationResult:
    cv = dict(
        language="en",
        headline="Backend Engineer",
        summary="Builds Python APIs.",
        experiences=[
            TailoredExperience(
                source_key=EXP_KEY,
                bullets=[
                    TailoredBullet(
                        source_key=f"{EXP_KEY}#bullet:0", text="Owned the billing API"
                    )
                ],
            )
        ],
        skill_keys=["skill:python"],
    )
    cv.update(cv_overrides)
    return AdaptationResult(
        cv=TailoredCv(**cv),
        suggestions=[
            Suggestion(
                kind="rewrite",
                source_key=f"{EXP_KEY}#bullet:0",
                before="Built the billing API",
                after="Owned the billing API",
                reason="Offer emphasises ownership",
            )
        ],
    )


def _client(session):
    # the convention in tests/test_scoring_api.py: override the session dependency
    # rather than letting the app open its own
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    return TestClient(app)


@pytest.fixture(autouse=True)
def rendered(monkeypatch):
    """Captures the HTML the PDF engine was handed. No browser is ever launched."""
    captured = {}

    def _engine(html, page):
        captured["html"] = html
        return b"%PDF-1.4 fake"

    render_mod.register_pdf_engine("fake", _engine)
    monkeypatch.setattr(render_mod, "DEFAULT_ENGINE", "fake")
    return captured


@pytest.fixture
def fake_llm(monkeypatch):
    def _install(result):
        monkeypatch.setattr(draft_mod, "llm_for", lambda task: _FakeLLM(result))

    return _install


@pytest.fixture
def match(session):
    save_profile(
        session,
        ProfileData(
            contact=Contact(full_name="Ada Lovelace"),
            skills=[Skill(name="Python")],
            experiences=[
                Experience(
                    company="Acme",
                    title="Backend Engineer",
                    bullets=["Built the billing API"],
                )
            ],
        ),
    )
    offer = Offer(
        title="Senior Backend Engineer",
        description="Python and API design.",
        source="test",
        content_hash="h1",
        skills=["Python"],
    )
    session.add(offer)
    session.commit()
    row = Match(offer_id=offer.id, profile_id=1, fitness=78.0, status="accepted")
    session.add(row)
    session.commit()
    return row


def test_adapt_returns_a_projection_with_suggestions(session, match, fake_llm):
    fake_llm(_result())

    response = _client(session).post(f"/matches/{match.id}/adapt", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["content_json"]["headline"] == "Backend Engineer"
    assert body["suggestions"][0]["kind"] == "rewrite"
    assert body["language"] == "en"


def test_adapting_an_unknown_match_is_404(session, fake_llm):
    fake_llm(_result())

    assert _client(session).post("/matches/999/adapt", json={}).status_code == 404


def test_a_hallucinating_draft_is_422(session, match, fake_llm):
    fake_llm(_result(experiences=[]))

    response = _client(session).post(f"/matches/{match.id}/adapt", json={})

    assert response.status_code == 422
    assert "missing from the CV" in response.json()["detail"]


def test_projections_are_listed_and_readable(session, match, fake_llm):
    fake_llm(_result())
    client = _client(session)
    created = client.post(f"/matches/{match.id}/adapt", json={}).json()

    listed = client.get("/projections").json()
    single = client.get(f"/projections/{created['id']}").json()

    assert [p["id"] for p in listed] == [created["id"]]
    assert single["content_json"]["summary"] == "Builds Python APIs."


def test_patch_accepts_a_hand_written_edit(session, match, fake_llm):
    """Anchoring constrains the model, not the user editing their own CV."""
    fake_llm(_result())
    client = _client(session)
    created = client.post(f"/matches/{match.id}/adapt", json={}).json()
    content = created["content_json"]
    content["summary"] = "Rewritten by hand."

    response = client.patch(
        f"/projections/{created['id']}", json={"content_json": content}
    )

    assert response.status_code == 200
    assert response.json()["content_json"]["summary"] == "Rewritten by hand."


def test_patch_rejects_structurally_invalid_content(session, match, fake_llm):
    fake_llm(_result())
    client = _client(session)
    created = client.post(f"/matches/{match.id}/adapt", json={}).json()

    response = client.patch(
        f"/projections/{created['id']}", json={"content_json": {"headline": "x"}}
    )

    assert response.status_code == 422


def test_render_produces_a_downloadable_pdf(session, match, fake_llm):
    fake_llm(_result())
    client = _client(session)
    created = client.post(f"/matches/{match.id}/adapt", json={}).json()

    doc = client.post(f"/projections/{created['id']}/render").json()
    download = client.get(f"/docs/{doc['id']}/download")

    assert doc["kind"] == "cv"
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")


def test_a_hand_edited_bullet_reaches_the_rendered_document(
    session, match, fake_llm, rendered
):
    """The round trip that matters: adapt -> edit -> render."""
    fake_llm(_result())
    client = _client(session)
    created = client.post(f"/matches/{match.id}/adapt", json={}).json()
    content = created["content_json"]
    content["experiences"][0]["bullets"][0]["text"] = "Hand-written bullet"
    client.patch(f"/projections/{created['id']}", json={"content_json": content})

    client.post(f"/projections/{created['id']}/render")

    assert "Hand-written bullet" in rendered["html"]
    assert "Owned the billing API" not in rendered["html"]


def test_delete_removes_the_projection(session, match, fake_llm):
    fake_llm(_result())
    client = _client(session)
    created = client.post(f"/matches/{match.id}/adapt", json={}).json()

    assert client.delete(f"/projections/{created['id']}").status_code == 204
    assert client.get(f"/projections/{created['id']}").status_code == 404


def test_generated_docs_lists_newest_first_and_filters_by_kind(session):
    session.add(GeneratedDoc(kind="cv", pdf_ref="a.pdf"))
    session.add(GeneratedDoc(kind="cover_letter", pdf_ref="b.pdf"))
    session.commit()

    client = _client(session)
    body = client.get("/generated-docs").json()
    assert {d["kind"] for d in body} == {"cv", "cover_letter"}

    only_cv = client.get("/generated-docs", params={"kind": "cv"}).json()
    assert [d["kind"] for d in only_cv] == ["cv"]
    assert only_cv[0]["pdf_ref"] == "a.pdf"
