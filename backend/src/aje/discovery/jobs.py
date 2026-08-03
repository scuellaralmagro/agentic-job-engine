"""Run lifecycle for asynchronous discovery.

Runs execute on APScheduler's thread pool — the same scheduler that already fires
cron searches — so manual and scheduled runs travel one code path.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.db import get_session
from aje.discovery.graph import discover_into_run
from aje.discovery.scheduler import get_scheduler
from aje.models import DiscoveryRun

logger = logging.getLogger(__name__)


def create_run(
    session: Session,
    *,
    term: str,
    filters: dict,
    kind: str,
    saved_search_id: int | None = None,
) -> DiscoveryRun:
    run = DiscoveryRun(
        saved_search_id=saved_search_id,
        kind=kind,
        term=term,
        filters=filters or {},
        started_at=datetime.utcnow(),
        status="running",
        source_results=[],
    )
    session.add(run)
    session.commit()
    return run


def _fail(session: Session, run: DiscoveryRun, message: str) -> None:
    run.status = "failed"
    run.finished_at = datetime.utcnow()
    run.source_results = [{"source": "run", "count": 0, "error": message}]
    session.commit()


def execute_run(run_id: int, max_offers: int | None = None) -> None:
    """Module-level entry point so APScheduler can persist a reference to it."""
    session = get_session()
    try:
        run = session.get(DiscoveryRun, run_id)
        if run is None:
            logger.warning("discovery run %s vanished before it started", run_id)
            return
        try:
            discover_into_run(session, run, max_offers=max_offers)
        except Exception as exc:  # noqa: BLE001 - the run must never stay "running"
            logger.exception("discovery run %s failed", run_id)
            _fail(session, run, str(exc))
    finally:
        session.close()


def enqueue_run(run_id: int, max_offers: int | None = None) -> None:
    # No trigger: APScheduler runs a job with no trigger immediately.
    get_scheduler().add_job(
        execute_run,
        args=(run_id, max_offers),
        id=f"discovery-run-{run_id}",
        replace_existing=True,
    )


def reconcile_orphaned_runs(session: Session) -> int:
    """A run still `running` at startup was orphaned — no job survives the process."""
    stmt = select(DiscoveryRun).where(DiscoveryRun.status == "running")
    orphaned = list(session.execute(stmt).scalars())
    for run in orphaned:
        _fail(session, run, "interrupted: the process restarted mid-run")
    if orphaned:
        logger.warning("marked %s orphaned discovery run(s) as failed", len(orphaned))
    return len(orphaned)


def active_run_for_search(session: Session, saved_search_id: int) -> DiscoveryRun | None:
    stmt = select(DiscoveryRun).where(
        DiscoveryRun.saved_search_id == saved_search_id,
        DiscoveryRun.status == "running",
    )
    return session.execute(stmt).scalars().first()
