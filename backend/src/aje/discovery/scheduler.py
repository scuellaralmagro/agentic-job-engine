import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.config import get_settings
from aje.models import SavedSearch

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def job_id_for(saved_search_id: int) -> str:
    return f"saved-search-{saved_search_id}"


def run_saved_search_job(saved_search_id: int) -> None:
    """Module-level entry point so APScheduler can persist a reference to it."""
    from aje.db import get_session
    from aje.discovery.jobs import start_run_for_search

    session = get_session()
    try:
        saved = session.get(SavedSearch, saved_search_id)
        if saved is None:
            logger.warning("scheduled search %s no longer exists", saved_search_id)
            return
        if start_run_for_search(session, saved) is None:
            logger.info(
                "scheduled search %s skipped: a run is already in flight",
                saved_search_id,
            )
    except Exception:  # noqa: BLE001 - a failed run must not kill the scheduler
        logger.exception("scheduled discovery run failed for search %s", saved_search_id)
    finally:
        session.close()


def build_scheduler() -> BackgroundScheduler:
    jobstore = SQLAlchemyJobStore(url=get_settings().database_url)
    return BackgroundScheduler(jobstores={"default": jobstore})


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = build_scheduler()
    return _scheduler


def reset_scheduler() -> None:
    global _scheduler
    _scheduler = None


def remove_search_job(scheduler: BackgroundScheduler, saved_search_id: int) -> None:
    try:
        scheduler.remove_job(job_id_for(saved_search_id))
    except Exception:  # noqa: BLE001 - JobLookupError when it was never scheduled
        pass


def sync_search_job(scheduler: BackgroundScheduler, search: SavedSearch) -> None:
    if not search.schedule:
        remove_search_job(scheduler, search.id)
        return
    try:
        trigger = CronTrigger.from_crontab(search.schedule)
    except ValueError:
        logger.warning(
            "saved search %s has an invalid cron %r; not scheduling",
            search.id,
            search.schedule,
        )
        remove_search_job(scheduler, search.id)
        return
    # replace_existing only dedupes against the jobstore; before the scheduler is
    # started jobs queue in _pending_jobs, so drop any prior one explicitly to keep
    # sync idempotent whether or not the scheduler is running.
    remove_search_job(scheduler, search.id)
    scheduler.add_job(
        run_saved_search_job,
        trigger=trigger,
        args=(search.id,),
        id=job_id_for(search.id),
        replace_existing=True,
    )


def sync_all_jobs(scheduler: BackgroundScheduler, session: Session) -> None:
    for search in session.execute(select(SavedSearch)).scalars():
        sync_search_job(scheduler, search)
