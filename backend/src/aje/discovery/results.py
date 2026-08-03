"""Per-offer bookkeeping for a discovery run.

Status transitions commit individually: the UI polls this table, so a batched
commit would show nothing and then everything, and a crashed run would leave a
lie about what completed.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.models import DiscoveryResult, Match

DISCOVERED = "discovered"
SCORING = "scoring"
PREFILTERED = "prefiltered"
SCORED = "scored"
FAILED = "failed"

TERMINAL = frozenset({PREFILTERED, SCORED, FAILED})


def _existing(session: Session, run_id: int, offer_id: int) -> DiscoveryResult | None:
    stmt = select(DiscoveryResult).where(
        DiscoveryResult.run_id == run_id, DiscoveryResult.offer_id == offer_id
    )
    return session.execute(stmt).scalars().first()


def record_result(
    session: Session, *, run_id: int, offer_id: int, is_new: bool, status: str
) -> DiscoveryResult:
    """Idempotent: two adapters returning the same posting is one result row."""
    row = _existing(session, run_id, offer_id)
    if row is None:
        row = DiscoveryResult(run_id=run_id, offer_id=offer_id)
        session.add(row)
    row.is_new = is_new
    row.status = status
    session.commit()
    return row


def set_result_status(
    session: Session,
    *,
    run_id: int,
    offer_id: int,
    status: str,
    error: str | None = None,
) -> None:
    row = _existing(session, run_id, offer_id)
    if row is None:
        return
    row.status = status
    row.error = error
    session.commit()


def status_for_known_offer(session: Session, offer_id: int) -> str:
    """What a re-found offer already is. No Match means nothing has processed it."""
    stmt = select(Match).where(Match.offer_id == offer_id)
    match = session.execute(stmt).scalars().first()
    if match is None:
        return DISCOVERED
    return PREFILTERED if match.scored_by == "vector" else SCORED


def results_for_run(session: Session, run_id: int) -> list[DiscoveryResult]:
    stmt = (
        select(DiscoveryResult)
        .where(DiscoveryResult.run_id == run_id)
        .order_by(DiscoveryResult.id)
    )
    return list(session.execute(stmt).scalars())
