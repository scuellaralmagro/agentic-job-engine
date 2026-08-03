"""Deterministic truthfulness checks. Pure: no DB, no network, no LLM.

The anchoring rules exist to constrain the *model*. They are applied to LLM
output only — never to a projection the user has edited by hand.
"""
import re

from aje.adaptation.schema import TailoredCv
from aje.discovery.normalize import normalize_text
from aje.extraction.schema import ProfileData
from aje.keys import experience_key, profile_keys


class AnchorError(ValueError):
    """The draft claims something the Profile does not support."""


def _referenced_keys(cv: TailoredCv) -> list[str]:
    keys = [
        *cv.skill_keys,
        *cv.achievement_keys,
        *cv.education_keys,
        *cv.language_keys,
    ]
    for exp in cv.experiences:
        keys.append(exp.source_key)
        keys.extend(bullet.source_key for bullet in exp.bullets)
    return keys


def assert_no_unsupported_skills(
    text: str, profile: ProfileData, offer_skills: list[str]
) -> None:
    """Free prose must not name a technology the offer wants and the profile lacks.

    Used for the CV headline/summary and for cover-letter paragraphs — the only
    places where output is not anchored to a source key.
    """
    owned = {normalize_text(skill.name) for skill in profile.skills}
    haystack = normalize_text(text)
    invented = []
    for skill in offer_skills:
        needle = normalize_text(skill)
        if not needle or needle in owned:
            continue
        # \b is unreliable next to punctuation like "c++"; use \w lookarounds
        if re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack):
            invented.append(skill)
    if invented:
        raise AnchorError(
            "free prose claims skills the profile does not have: " + ", ".join(invented)
        )


def validate_projection(
    cv: TailoredCv, profile: ProfileData, offer_skills: list[str] | None = None
) -> None:
    """Raise AnchorError unless every claim traces back to the Profile."""
    known = profile_keys(profile)
    unknown = sorted({key for key in _referenced_keys(cv) if key not in known})
    if unknown:
        raise AnchorError("source keys not found in profile: " + ", ".join(unknown))

    required = {experience_key(e.company, e.title) for e in profile.experiences}
    present = {exp.source_key for exp in cv.experiences}
    missing = sorted(required - present)
    if missing:
        raise AnchorError(
            "profile experiences missing from the CV: " + ", ".join(missing)
        )

    assert_no_unsupported_skills(
        f"{cv.headline} {cv.summary}", profile, offer_skills or []
    )
