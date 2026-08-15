from aje.discovery import jobs as jobs_mod
from aje.models import SavedSearch


class _KeepsOpen:
    """execute_run owns and closes its session — correct in production, but it
    would detach the objects this test still needs to inspect afterwards."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def close(self) -> None:
        pass


def test_create_run_starts_in_running_with_the_query_recorded(session):
    run = jobs_mod.create_run(
        session, term="python madrid", filters={"remote": True}, kind="manual"
    )

    assert run.status == "running"
    assert run.term == "python madrid"
    assert run.filters == {"remote": True}
    assert run.kind == "manual"
    assert run.finished_at is None


def test_execute_run_marks_the_run_failed_when_the_job_raises(session, monkeypatch):
    """A permanently-running row would make the UI poll forever and history lie."""
    run = jobs_mod.create_run(session, term="x", filters={}, kind="manual")

    monkeypatch.setattr(jobs_mod, "get_session", lambda: _KeepsOpen(session))

    def _boom(sess, r, **kwargs):
        raise RuntimeError("adapters exploded")

    monkeypatch.setattr(jobs_mod, "discover_into_run", _boom)

    jobs_mod.execute_run(run.id)

    session.refresh(run)
    assert run.status == "failed"
    assert run.finished_at is not None
    assert "adapters exploded" in run.source_results[0]["error"]


def test_reconcile_marks_orphaned_running_runs_as_failed(session):
    """Nothing survives a process restart, so a running row at startup is orphaned."""
    stale = jobs_mod.create_run(session, term="x", filters={}, kind="scheduled")
    done = jobs_mod.create_run(session, term="y", filters={}, kind="manual")
    done.status = "ok"
    session.commit()

    count = jobs_mod.reconcile_orphaned_runs(session)

    session.refresh(stale)
    session.refresh(done)
    assert count == 1
    assert stale.status == "failed" and stale.finished_at is not None
    assert done.status == "ok"


def _saved(session, **kwargs):
    search = SavedSearch(
        name=kwargs.pop("name", "s"),
        query=kwargs.pop("query", "python"),
        filters=kwargs.pop("filters", {"location": "Madrid"}),
        **kwargs,
    )
    session.add(search)
    session.commit()
    return search


def test_start_run_for_search_enqueues_with_the_searchs_cap(session, monkeypatch):
    """The cap is the whole point: a scheduled search that reaches enqueue_run
    without one scores every new offer it finds."""
    search = _saved(session, max_offers=25)
    enqueued: list[tuple[int, int | None]] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append((rid, cap))
    )

    run = jobs_mod.start_run_for_search(session, search)

    assert run is not None
    assert run.saved_search_id == search.id
    assert run.kind == "scheduled"
    assert run.term == "python"
    assert run.filters == {"location": "Madrid"}
    assert enqueued == [(run.id, 25)]


def test_start_run_for_search_passes_none_for_an_uncapped_search(session, monkeypatch):
    """NULL means deliberately uncapped and must survive as None, not become a number."""
    search = _saved(session, max_offers=None)
    enqueued: list[tuple[int, int | None]] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append((rid, cap))
    )

    run = jobs_mod.start_run_for_search(session, search)

    assert enqueued == [(run.id, None)]


def test_start_run_for_search_refuses_when_one_is_already_running(session, monkeypatch):
    """Overlapping runs double-spend. The caller decides whether that is a 409
    or a logged skip; this function just declines."""
    search = _saved(session, max_offers=25)
    jobs_mod.create_run(
        session, term="python", filters={}, kind="scheduled", saved_search_id=search.id
    )
    enqueued: list[int] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append(rid)
    )

    assert jobs_mod.start_run_for_search(session, search) is None
    assert enqueued == []


def test_active_run_for_search_finds_only_running_ones(session):
    run = jobs_mod.create_run(
        session, term="x", filters={}, kind="scheduled", saved_search_id=7
    )

    assert jobs_mod.active_run_for_search(session, 7) is not None

    run.status = "ok"
    session.commit()

    assert jobs_mod.active_run_for_search(session, 7) is None
