"""Builds the adaptation prompt payload. Pure: no LLM, no DB writes."""
from aje.extraction.schema import ProfileData
from aje.keys import (
    achievement_key,
    bullet_key,
    description_key,
    education_key,
    experience_key,
    language_key,
    skill_key,
)
from aje.models import Match, Offer


def render_profile(profile: ProfileData, *, with_keys: bool = True) -> str:
    """The profile as prompt text, optionally with each item's anchor key beside it.

    Anchoring only helps a consumer that resolves keys back to text. The cover
    letter does not — its paragraphs render verbatim — so it asks for the plain
    form rather than tempting the model to cite a key into the prose.
    """

    def tag(key: str) -> str:
        return f"[{key}] " if with_keys else ""

    lines: list[str] = ["SKILLS:"]
    for skill in profile.skills:
        lines.append(f"  {tag(skill_key(skill.name))}{skill.name}")

    lines.append("EXPERIENCES:")
    for exp in profile.experiences:
        exp_key = experience_key(exp.company, exp.title)
        period = " - ".join(p for p in (exp.start, exp.end) if p)
        header = f"  {tag(exp_key)}{exp.title} @ {exp.company}"
        lines.append(f"{header} ({period})" if period else header)
        if exp.description:
            lines.append(f"    {tag(description_key(exp_key))}{exp.description}")
        for index, bullet in enumerate(exp.bullets):
            lines.append(f"    {tag(bullet_key(exp_key, index))}{bullet}")

    lines.append("ACHIEVEMENTS:")
    for achievement in profile.achievements:
        lines.append(f"  {tag(achievement_key(achievement.text))}{achievement.text}")

    lines.append("EDUCATION:")
    for edu in profile.education:
        label = " ".join(p for p in (edu.degree, edu.field, edu.institution) if p)
        lines.append(f"  {tag(education_key(edu.institution, edu.degree))}{label}")

    lines.append("LANGUAGES:")
    for language in profile.languages:
        label = f"{language.name} ({language.level})" if language.level else language.name
        lines.append(f"  {tag(language_key(language.name))}{label}")

    return "\n".join(lines)


def render_profile_with_keys(profile: ProfileData) -> str:
    """The profile, with each item's anchor key in brackets beside it."""
    return render_profile(profile, with_keys=True)


def render_match(match: Match) -> str:
    gaps = "; ".join(
        f"{gap.get('requirement')} [{gap.get('severity')}]" for gap in (match.gaps or [])
    )
    return (
        f"FITNESS: {match.fitness:.0f}\n"
        f"ASSESSMENT: {match.explanation or ''}\n"
        f"GAPS: {gaps or 'none'}"
    )


def build_context(
    offer: Offer,
    match: Match,
    profile: ProfileData,
    *,
    notes: str | None = None,
    cite_keys: bool = True,
) -> str:
    header = " | ".join(p for p in (offer.title, offer.company, offer.location) if p)
    profile_heading = (
        "=== CANDIDATE PROFILE (cite these keys verbatim) ==="
        if cite_keys
        else "=== CANDIDATE PROFILE ==="
    )
    parts = [
        "=== JOB OFFER ===",
        header,
        offer.description or "",
        "",
        "=== SCORING ASSESSMENT ===",
        render_match(match),
        "",
        profile_heading,
        render_profile(profile, with_keys=cite_keys),
    ]
    if notes:
        parts += ["", "=== USER NOTES ===", notes]
    return "\n".join(parts)
