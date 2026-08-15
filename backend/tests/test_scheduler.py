import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from aje.discovery import scheduler as sched_mod
from aje.models import SavedSearch


class _KeepsOpen:
    """run_saved_search_job owns and closes its session — correct in production,
    but it would detach the objects this test still needs afterwards."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def close(self) -> None:
        pass


@pytest.fixture
def scheduler():
    # in-memory jobstore keeps the test independent of the app database
    s = BackgroundScheduler()
    yield s
    if s.running:
        s.shutdown(wait=False)


def test_job_id_is_stable():
    assert sched_mod.job_id_for(7) == sched_mod.job_id_for(7)
    assert sched_mod.job_id_for(7) != sched_mod.job_id_for(8)


def test_sync_registers_job_for_scheduled_search(scheduler, session):
    search = SavedSearch(name="s", query="python", filters={}, schedule="0 8 * * *")
    session.add(search)
    session.commit()

    sched_mod.sync_search_job(scheduler, search)

    job = scheduler.get_job(sched_mod.job_id_for(search.id))
    assert job is not None
    assert job.args == (search.id,)


def test_sync_removes_job_when_schedule_cleared(scheduler, session):
    search = SavedSearch(name="s", query="python", filters={}, schedule="0 8 * * *")
    session.add(search)
    session.commit()
    sched_mod.sync_search_job(scheduler, search)

    search.schedule = None
    sched_mod.sync_search_job(scheduler, search)

    assert scheduler.get_job(sched_mod.job_id_for(search.id)) is None


def test_sync_replaces_existing_job(scheduler, session):
    search = SavedSearch(name="s", query="python", filters={}, schedule="0 8 * * *")
    session.add(search)
    session.commit()

    sched_mod.sync_search_job(scheduler, search)
    search.schedule = "0 20 * * *"
    sched_mod.sync_search_job(scheduler, search)

    jobs = [j for j in scheduler.get_jobs() if j.id == sched_mod.job_id_for(search.id)]
    assert len(jobs) == 1


def test_remove_job_is_idempotent(scheduler):
    sched_mod.remove_search_job(scheduler, 123)
    sched_mod.remove_search_job(scheduler, 123)  # must not raise


def test_invalid_cron_is_ignored(scheduler, session):
    search = SavedSearch(name="s", query="python", filters={}, schedule="not-a-cron")
    session.add(search)
    session.commit()

    sched_mod.sync_search_job(scheduler, search)  # must not raise

    assert scheduler.get_job(sched_mod.job_id_for(search.id)) is None


def test_cron_starts_a_run_through_the_shared_entry_point(session, monkeypatch):
    """The cron path used to call run_saved_search -> run_discovery, which took no
    cap and no concurrency guard. It must now travel the same road as run-now."""
    from aje.discovery import jobs as jobs_mod

    search = SavedSearch(name="s", query="python", filters={}, max_offers=25)
    session.add(search)
    session.commit()

    monkeypatch.setattr("aje.db.get_session", lambda: _KeepsOpen(session))
    enqueued: list[tuple[int, int | None]] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append((rid, cap))
    )

    sched_mod.run_saved_search_job(search.id)

    assert len(enqueued) == 1
    assert enqueued[0][1] == 25


def test_cron_skips_when_a_run_is_already_in_flight(session, monkeypatch):
    """A nightly run slower than its own interval would otherwise overlap itself
    and double-spend."""
    from aje.discovery import jobs as jobs_mod

    search = SavedSearch(name="s", query="python", filters={}, max_offers=25)
    session.add(search)
    session.commit()
    jobs_mod.create_run(
        session, term="python", filters={}, kind="scheduled", saved_search_id=search.id
    )

    monkeypatch.setattr("aje.db.get_session", lambda: _KeepsOpen(session))
    enqueued: list[int] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append(rid)
    )

    sched_mod.run_saved_search_job(search.id)

    assert enqueued == []


def test_cron_handles_a_deleted_search_without_raising(session, monkeypatch):
    """An exception here kills the scheduler thread for every other search."""
    monkeypatch.setattr("aje.db.get_session", lambda: _KeepsOpen(session))

    sched_mod.run_saved_search_job(9999)  # must not raise


def test_sync_all_registers_only_scheduled_searches(scheduler, session):
    session.add(SavedSearch(name="a", query="a", filters={}, schedule="0 8 * * *"))
    session.add(SavedSearch(name="b", query="b", filters={}, schedule=None))
    session.commit()

    sched_mod.sync_all_jobs(scheduler, session)

    assert len(scheduler.get_jobs()) == 1
