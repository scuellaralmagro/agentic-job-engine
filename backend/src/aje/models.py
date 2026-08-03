from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact: Mapped[dict] = mapped_column(JSON, default=dict)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    experiences: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    achievements: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceDocument(Base):
    __tablename__ = "source_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # "cv" | "linkedin_export"
    file_ref: Mapped[str] = mapped_column(String(1024))
    parsed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CvProjection(Base):
    __tablename__ = "cv_projections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profile.id"))
    offer_id: Mapped[int | None] = mapped_column(ForeignKey("offers.id"), nullable=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    company: Mapped[str | None] = mapped_column(String(512), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    query: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule: Mapped[str | None] = mapped_column(String(128), nullable=True)  # cron expr
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("offer_id", "profile_id", name="uq_matches_offer_profile"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"))
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profile.id"), nullable=True)
    cv_projection_id: Mapped[int | None] = mapped_column(
        ForeignKey("cv_projections.id"), nullable=True
    )
    fitness: Mapped[float] = mapped_column()
    rubric: Mapped[dict] = mapped_column(JSON, default=dict)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    above_threshold: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), default="new")  # new|accepted|dismissed
    scored_by: Mapped[str] = mapped_column(String(16), default="rubric")  # vector|rubric
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeneratedDoc(Base):
    __tablename__ = "generated_docs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # "cv" | "cover_letter"
    offer_id: Mapped[int | None] = mapped_column(ForeignKey("offers.id"), nullable=True)
    cv_projection_id: Mapped[int | None] = mapped_column(
        ForeignKey("cv_projections.id"), nullable=True
    )
    pdf_ref: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    saved_search_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_searches.id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16))  # "ok" | "partial" | "failed"
    offers_found: Mapped[int] = mapped_column(Integer, default=0)
    offers_new: Mapped[int] = mapped_column(Integer, default=0)
    source_results: Mapped[list] = mapped_column(JSON, default=list)


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint(
            "owner_kind", "owner_id", "item_key", name="uq_embeddings_owner_item"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_kind: Mapped[str] = mapped_column(String(32))  # "profile_item" | "offer"
    owner_id: Mapped[int] = mapped_column(Integer)
    item_key: Mapped[str] = mapped_column(String(255))
    text_hash: Mapped[str] = mapped_column(String(64))
    dim: Mapped[int] = mapped_column(Integer)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
