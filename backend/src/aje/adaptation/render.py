"""Projection -> CvView -> HTML -> PDF.

`build_view` is pure. The HTML and PDF layers arrive in the next two tasks.
"""
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from aje.adaptation.config import CvConfig
from aje.adaptation.schema import CvView, TailoredCv, ViewExperience
from aje.adaptation.validate import AnchorError
from aje.extraction.schema import ProfileData
from aje.keys import (
    achievement_key,
    education_key,
    experience_key,
    language_key,
    skill_key,
)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(view: CvView, config: CvConfig, template: str | None = None) -> str:
    name = template or config.template
    return _env().get_template(f"{name}.html.j2").render(cv=view, page=config.page)


def _resolve(keys: list[str], lookup: dict[str, str]) -> list[str]:
    resolved = []
    for key in keys:
        if key not in lookup:
            raise AnchorError(f"cannot resolve {key} against the current profile")
        resolved.append(lookup[key])
    return resolved


def build_view(cv: TailoredCv, profile: ProfileData) -> CvView:
    """Resolve every key to text. Raises AnchorError if the Profile has moved on."""
    skills = {skill_key(s.name): s.name for s in profile.skills}
    achievements = {achievement_key(a.text): a.text for a in profile.achievements}
    education = {
        education_key(e.institution, e.degree): " ".join(
            p for p in (e.degree, e.field, e.institution) if p
        )
        for e in profile.education
    }
    languages = {
        language_key(lang.name): (
            f"{lang.name} ({lang.level})" if lang.level else lang.name
        )
        for lang in profile.languages
    }
    experiences = {experience_key(e.company, e.title): e for e in profile.experiences}

    views: list[ViewExperience] = []
    for tailored in cv.experiences:
        source = experiences.get(tailored.source_key)
        if source is None:
            raise AnchorError(
                f"cannot resolve {tailored.source_key} against the current profile"
            )
        views.append(
            ViewExperience(
                title=source.title,
                company=source.company,
                period=" - ".join(p for p in (source.start, source.end) if p),
                bullets=[bullet.text for bullet in tailored.bullets],
            )
        )

    return CvView(
        contact=profile.contact,
        language=cv.language,
        headline=cv.headline,
        summary=cv.summary,
        experiences=views,
        skills=_resolve(cv.skill_keys, skills),
        achievements=_resolve(cv.achievement_keys, achievements),
        education=_resolve(cv.education_keys, education),
        languages=_resolve(cv.language_keys, languages),
    )
