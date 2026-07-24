from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    category: str | None = None
    level: str | None = None
    source_refs: list[int] = Field(default_factory=list)


class Experience(BaseModel):
    company: str
    title: str
    description: str | None = None
    start: str | None = None
    end: str | None = None
    bullets: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    source_refs: list[int] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start: str | None = None
    end: str | None = None
    source_refs: list[int] = Field(default_factory=list)


class Achievement(BaseModel):
    text: str
    source_refs: list[int] = Field(default_factory=list)


class Language(BaseModel):
    name: str
    level: str | None = None
    source_refs: list[int] = Field(default_factory=list)


class ProfileData(BaseModel):
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class CandidateProfile(ProfileData):
    """Same shape as ProfileData; the intermediate emitted before merge."""
