import os
from pathlib import Path

import pytest

from aje.adaptation import render as render_mod
from aje.adaptation.config import CvConfig
from aje.adaptation.persist import render_projection
from aje.adaptation.render import PdfEngineError, html_to_pdf, register_pdf_engine
from aje.adaptation.schema import TailoredBullet, TailoredCv, TailoredExperience
from aje.adaptation.validate import AnchorError
from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Contact, Experience, ProfileData, Skill
from aje.models import CvProjection, GeneratedDoc, Offer

EXP_KEY = "experience:acme|backend engineer"


class _FakeEngine:
    def __init__(self):
        self.html = None
        self.page = None

    def __call__(self, html, page):
        self.html = html
        self.page = page
        return b"%PDF-1.4 fake"


@pytest.fixture
def fake_engine():
    engine = _FakeEngine()
    register_pdf_engine("fake", engine)
    return engine


@pytest.fixture
def profile(session):
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


@pytest.fixture
def projection(session, profile):
    offer = Offer(
        title="Senior Backend Engineer", source="test", content_hash="h1", skills=[]
    )
    session.add(offer)
    session.commit()
    cv = TailoredCv(
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
    row = CvProjection(
        profile_id=1,
        offer_id=offer.id,
        name="Senior Backend Engineer",
        content_json=cv.model_dump(),
        suggestions=[],
        language="en",
    )
    session.add(row)
    session.commit()
    return row


def test_an_unknown_engine_raises():
    with pytest.raises(PdfEngineError, match="unknown pdf engine"):
        html_to_pdf("<html></html>", CvConfig().page, engine="nope")


def test_the_engine_receives_the_rendered_html(fake_engine):
    html_to_pdf("<html>hello</html>", CvConfig().page, engine="fake")

    assert fake_engine.html == "<html>hello</html>"


def test_rendering_a_projection_writes_a_pdf_and_a_row(
    session, projection, fake_engine, monkeypatch
):
    monkeypatch.setattr(render_mod, "DEFAULT_ENGINE", "fake")

    doc = render_projection(session, projection.id, config=CvConfig())

    assert "Owned the billing API" in fake_engine.html
    assert doc.kind == "cv"
    assert doc.cv_projection_id == projection.id
    assert doc.offer_id == projection.offer_id
    assert Path(doc.pdf_ref).read_bytes() == b"%PDF-1.4 fake"
    assert session.query(GeneratedDoc).count() == 1


def test_rendering_twice_produces_two_documents(
    session, projection, fake_engine, monkeypatch
):
    monkeypatch.setattr(render_mod, "DEFAULT_ENGINE", "fake")

    first = render_projection(session, projection.id, config=CvConfig())
    second = render_projection(session, projection.id, config=CvConfig())

    assert first.pdf_ref != second.pdf_ref


def test_a_projection_referencing_a_deleted_profile_item_raises(
    session, projection, fake_engine, monkeypatch
):
    monkeypatch.setattr(render_mod, "DEFAULT_ENGINE", "fake")
    save_profile(session, ProfileData(contact=Contact(full_name="Ada Lovelace")))

    with pytest.raises(AnchorError):
        render_projection(session, projection.id, config=CvConfig())


def test_an_unknown_projection_raises_value_error(session):
    with pytest.raises(ValueError, match="projection 999 not found"):
        render_projection(session, 999, config=CvConfig())


@pytest.mark.skipif(
    os.environ.get("AJE_PDF_E2E") != "1", reason="set AJE_PDF_E2E=1 to run Chromium"
)
def test_chromium_really_produces_a_pdf():
    pdf = html_to_pdf("<html><body><h1>Ada</h1></body></html>", CvConfig().page)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
