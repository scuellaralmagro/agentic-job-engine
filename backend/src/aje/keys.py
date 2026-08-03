"""The single definition of Profile item keys.

Adaptation anchors every element of a tailored CV to one of these keys, and
scoring writes the experience and achievement ones into `embeddings.item_key`.
Two independently-maintained definitions would drift silently, so there is
only this one.
"""
import hashlib

from aje.discovery.normalize import normalize_text
from aje.extraction.schema import ProfileData


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def experience_key(company: str | None, title: str | None) -> str:
    return f"experience:{normalize_text(company)}|{normalize_text(title)}"


def description_key(exp_key: str) -> str:
    return f"{exp_key}#description"


def bullet_key(exp_key: str, index: int) -> str:
    return f"{exp_key}#bullet:{index}"


def achievement_key(text: str) -> str:
    return f"achievement:{text_hash(text)[:12]}"


def skill_key(name: str) -> str:
    return f"skill:{normalize_text(name)}"


def education_key(institution: str | None, degree: str | None) -> str:
    return f"education:{normalize_text(institution)}|{normalize_text(degree)}"


def language_key(name: str) -> str:
    return f"language:{normalize_text(name)}"


def profile_keys(profile: ProfileData) -> set[str]:
    """Every key this profile can legitimately be anchored to."""
    keys: set[str] = set()
    for skill in profile.skills:
        keys.add(skill_key(skill.name))
    for exp in profile.experiences:
        exp_key = experience_key(exp.company, exp.title)
        keys.add(exp_key)
        if exp.description:
            keys.add(description_key(exp_key))
        for index in range(len(exp.bullets)):
            keys.add(bullet_key(exp_key, index))
    for edu in profile.education:
        keys.add(education_key(edu.institution, edu.degree))
    for achievement in profile.achievements:
        keys.add(achievement_key(achievement.text))
    for language in profile.languages:
        keys.add(language_key(language.name))
    return keys
