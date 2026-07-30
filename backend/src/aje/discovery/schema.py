from datetime import datetime

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """A saved search resolved into something adapters can execute."""

    terms: list[str]
    location: str | None = None
    remote: bool | None = None
    max_results: int = 50


class RawOffer(BaseModel):
    """What an adapter emits, before normalization."""

    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    url: str | None = None
    source: str
    posted_at: datetime | None = None


class SourceResult(BaseModel):
    """Per-adapter outcome of one run."""

    source: str
    count: int = 0
    error: str | None = None


class ExpandedQuery(BaseModel):
    terms: list[str] = Field(default_factory=list)
