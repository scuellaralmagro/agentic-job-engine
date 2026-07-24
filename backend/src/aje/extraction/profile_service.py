from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.extraction.schema import ProfileData
from aje.models import Profile, SourceDocument

PROFILE_ID = 1


def get_profile(session: Session) -> ProfileData:
    row = session.get(Profile, PROFILE_ID)
    if row is None:
        return ProfileData()
    return ProfileData(
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
    row.skills = [s.model_dump() for s in data.skills]
    row.experiences = [e.model_dump() for e in data.experiences]
    row.education = [e.model_dump() for e in data.education]
    row.achievements = [a.model_dump() for a in data.achievements]
    row.languages = [lang.model_dump() for lang in data.languages]
    session.commit()
    return data


def list_source_documents(session: Session) -> list[SourceDocument]:
    stmt = select(SourceDocument).order_by(SourceDocument.created_at.desc())
    return list(session.execute(stmt).scalars())
