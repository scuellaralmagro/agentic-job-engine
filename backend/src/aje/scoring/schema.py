from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    score: int = Field(ge=0, le=100)
    evidence: str


class Gap(BaseModel):
    requirement: str
    severity: str  # "blocker" | "major" | "minor"
    profile_has: str | None = None


class OfferRequirements(BaseModel):
    """The offer's own stated requirements, extracted while scoring."""

    skills: list[str] = Field(default_factory=list)
    seniority: str | None = None
    languages: list[str] = Field(default_factory=list)


class RubricResult(BaseModel):
    skills: DimensionScore
    seniority: DimensionScore
    domain: DimensionScore
    language: DimensionScore
    dealbreaker: bool = False
    dealbreaker_reason: str | None = None
    gaps: list[Gap] = Field(default_factory=list)
    requirements: OfferRequirements = Field(default_factory=OfferRequirements)
    explanation: str = ""


class ScoringSummary(BaseModel):
    scored: int = 0  # rubric-scored
    gated: int = 0  # below the prefilter cutoff, no LLM call
    skipped: int = 0  # already had a match and rescore was not requested
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
