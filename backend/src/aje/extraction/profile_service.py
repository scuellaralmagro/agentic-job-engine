import logging
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from aje.extraction.schema import ProfileData
from aje.models import Embedding, Profile, SourceDocument

logger = logging.getLogger(__name__)

PROFILE_ID = 1


class ResetSummary(BaseModel):
    source_documents: int = 0
    files: int = 0
    embeddings: int = 0


def get_profile(session: Session) -> ProfileData:
    row = session.get(Profile, PROFILE_ID)
    if row is None:
        return ProfileData()
    return ProfileData(
        contact=row.contact or {},
        skills=row.skills or [],
        experiences=row.experiences or [],
        education=row.education or [],
        achievements=row.achievements or [],
        languages=row.languages or [],
    )


def save_profile(session: Session, data: ProfileData) -> ProfileData:
    row = session.get(Profile, PROFILE_ID)
    if row is None:
        row = Profile(id=PROFILE_ID)
        session.add(row)
    row.contact = data.contact.model_dump()
    row.skills = [s.model_dump() for s in data.skills]
    row.experiences = [e.model_dump() for e in data.experiences]
    row.education = [e.model_dump() for e in data.education]
    row.achievements = [a.model_dump() for a in data.achievements]
    row.languages = [lang.model_dump() for lang in data.languages]
    session.commit()
    return data


def reset_profile(session: Session) -> ResetSummary:
    """Wipe the Profile back to empty, as if nothing had ever been ingested.

    Source documents go too, and not just for tidiness: run_extraction dedups on
    content_hash, so leaving them behind would make re-uploading the same CV a
    silent no-op against an empty profile. Their stored copies are deleted with
    them — a CV is personal data the user asked us to forget.

    Matches and CV projections are deliberately left alone. They are separate work
    products; their scores simply go stale until the profile is rebuilt and rescored.
    """
    # Imported here: aje.scoring.embed imports this module, so a module-level
    # import would be circular.
    from aje.scoring.embed import PROFILE_ITEM

    summary = ResetSummary()

    for doc in session.execute(select(SourceDocument)).scalars():
        summary.source_documents += 1
        try:
            if doc.file_ref and Path(doc.file_ref).is_file():
                Path(doc.file_ref).unlink()
                summary.files += 1
        except OSError as exc:  # a locked file must not abort the reset
            logger.warning("could not delete upload %s: %s", doc.file_ref, exc)
        session.delete(doc)

    summary.embeddings = int(
        session.execute(
            delete(Embedding).where(Embedding.owner_kind == PROFILE_ITEM)
        ).rowcount
        or 0
    )

    save_profile(session, ProfileData())
    session.commit()
    return summary


def list_source_documents(session: Session) -> list[SourceDocument]:
    stmt = select(SourceDocument).order_by(SourceDocument.created_at.desc())
    return list(session.execute(stmt).scalars())
