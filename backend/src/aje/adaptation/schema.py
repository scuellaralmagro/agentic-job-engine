from pydantic import BaseModel, Field

from aje.extraction.schema import Contact


class TailoredBullet(BaseModel):
    source_key: str
    text: str


class TailoredExperience(BaseModel):
    source_key: str
    bullets: list[TailoredBullet] = Field(default_factory=list)


class TailoredCv(BaseModel):
    language: str
    headline: str
    summary: str
    experiences: list[TailoredExperience] = Field(default_factory=list)
    skill_keys: list[str] = Field(default_factory=list)
    achievement_keys: list[str] = Field(default_factory=list)
    education_keys: list[str] = Field(default_factory=list)
    language_keys: list[str] = Field(default_factory=list)


class Suggestion(BaseModel):
    kind: str  # rewrite | promote | demote | drop | emphasize
    source_key: str
    before: str | None = None
    after: str | None = None
    reason: str


class AdaptationResult(BaseModel):
    cv: TailoredCv
    suggestions: list[Suggestion] = Field(default_factory=list)


class CoverLetterContent(BaseModel):
    language: str
    salutation: str
    paragraphs: list[str] = Field(default_factory=list)
    closing: str


class ViewExperience(BaseModel):
    """A tailored experience with every key already resolved to text."""

    title: str
    company: str
    period: str
    bullets: list[str] = Field(default_factory=list)


class CvView(BaseModel):
    """What the template renders. Contains no keys — resolution happened upstream."""

    contact: Contact
    language: str
    headline: str
    summary: str
    experiences: list[ViewExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
