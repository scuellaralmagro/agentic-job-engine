from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.models import Match

STATUSES = ("new", "accepted", "dismissed")


def list_queue(
    session: Session,
    *,
    status: str = "new",
    min_fitness: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Match]:
    """Rubric-scored, above-threshold matches only.

    Vector-only matches carry a similarity-derived fitness on a different scale;
    ranking them alongside rubric scores would be meaningless.
    """
    stmt = (
        select(Match)
        .where(
            Match.scored_by == "rubric",
            Match.above_threshold.is_(True),
            Match.status == status,
        )
        .order_by(Match.fitness.desc())
        .limit(limit)
        .offset(offset)
    )
    if min_fitness is not None:
        stmt = stmt.where(Match.fitness >= min_fitness)
    return list(session.execute(stmt).scalars())


def get_match(session: Session, match_id: int) -> Match | None:
    return session.get(Match, match_id)


def set_status(session: Session, match_id: int, status: str) -> Match:
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    match = session.get(Match, match_id)
    if match is None:
        raise ValueError(f"no match with id {match_id}")
    match.status = status
    session.commit()
    return match
