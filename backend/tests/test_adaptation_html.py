import os
from pathlib import Path

import pytest

from aje.adaptation.config import CvConfig
from aje.adaptation.render import render_html
from aje.adaptation.schema import CvView, ViewExperience
from aje.extraction.schema import Contact, Link

GOLDEN = Path(__file__).parent / "fixtures" / "cv_default_golden.html"


def _view(**overrides) -> CvView:
    base = dict(
        contact=Contact(
            full_name="Ada Lovelace",
            headline="Backend Engineer",
            email="ada@example.com",
            phone="+34 600 000 000",
            location="Madrid, Spain",
            links=[Link(label="GitHub", url="https://github.com/ada")],
        ),
        language="en",
        headline="Backend Engineer",
        summary="Builds Python APIs that stay up.",
        experiences=[
            ViewExperience(
                title="Backend Engineer",
                company="Acme",
                period="2021 - 2024",
                bullets=["Owned the billing API", "Cut p99 latency 40%"],
            )
        ],
        skills=["Python", "FastAPI"],
        achievements=["Speaker at PyConES"],
        education=["Ingenieria Software UC3M"],
        languages=["English (C1)"],
    )
    base.update(overrides)
    return CvView(**base)


def test_the_document_carries_the_tailored_content():
    html = render_html(_view(), CvConfig())

    assert "Ada Lovelace" in html
    assert "Builds Python APIs that stay up." in html
    assert "Cut p99 latency 40%" in html
    assert "English (C1)" in html
    assert 'href="https://github.com/ada"' in html


def test_the_page_setup_comes_from_config():
    html = render_html(_view(), CvConfig(page={"format": "Letter", "margin_mm": 20}))

    assert "size: Letter" in html
    assert "margin: 20mm" in html


def test_the_language_lands_on_the_html_element():
    assert '<html lang="es"' in render_html(_view(language="es"), CvConfig())


def test_an_empty_section_is_omitted_entirely():
    html = render_html(_view(achievements=[], languages=[]), CvConfig())

    assert "Achievements" not in html
    assert "Languages" not in html


def test_content_is_escaped():
    html = render_html(_view(summary="Loves <script>alert(1)</script> jokes"), CvConfig())

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_a_profile_without_contact_still_renders():
    """Adapting before the profile has contact data yields a headerless CV, not an error."""
    html = render_html(_view(contact=Contact()), CvConfig())

    assert "Cut p99 latency 40%" in html
    assert "None" not in html


@pytest.mark.skipif(not GOLDEN.exists(), reason="golden snapshot not yet generated")
def test_the_template_matches_the_golden_snapshot():
    html = render_html(_view(), CvConfig())

    if os.environ.get("AJE_UPDATE_GOLDEN"):
        GOLDEN.write_text(html, encoding="utf-8")

    assert html == GOLDEN.read_text(encoding="utf-8")
