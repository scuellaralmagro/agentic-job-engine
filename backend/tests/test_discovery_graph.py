import pytest

from aje.discovery import graph as graph_mod
from aje.discovery.schema import RawOffer, SearchQuery
from aje.models import DiscoveryRun, Offer


class _StubAdapter:
    def __init__(self, name, offers=None, error=None):
        self.name = name
        self._offers = offers or []
        self._error = error
        self.seen_query = None

    def search(self, query: SearchQuery):
        self.seen_query = query
        if self._error:
            raise self._error
        return self._offers


def _raw(
    title,
    company="Acme",
    location="Madrid",
    source="stub",
    url="https://x/1",
    description=None,
):
    return RawOffer(
        title=title,
        company=company,
        location=location,
        source=source,
        url=url,
        description=description,
    )


@pytest.fixture(autouse=True)
def _no_llm_expansion(monkeypatch):
    # expansion has its own tests; keep graph tests deterministic
    monkeypatch.setattr(graph_mod, "expand_query", lambda term: [term])


def test_run_persists_offers_and_records_run(session):
    adapter = _StubAdapter(
        "stub", [_raw("Backend Dev"), _raw("Data Eng", url="https://x/2")]
    )

    run = graph_mod.run_discovery(session, term="python", adapters=[adapter], score=False)

    assert run.status == "ok"
    assert run.offers_found == 2
    assert run.offers_new == 2
    assert run.finished_at is not None
    assert session.query(Offer).count() == 2
    assert run.source_results == [{"source": "stub", "count": 2, "error": None}]


def test_query_carries_location_to_adapters(session):
    adapter = _StubAdapter("stub", [])
    graph_mod.run_discovery(
        session, term="python", location="Madrid", adapters=[adapter], score=False
    )
    assert adapter.seen_query.location == "Madrid"
    assert adapter.seen_query.terms == ["python"]


def test_duplicate_offers_across_sources_collapse(session):
    a = _StubAdapter("a", [_raw("Backend Dev", source="a", url="https://a/1")])
    b = _StubAdapter("b", [_raw("Backend Dev", source="b", url="https://b/9")])

    run = graph_mod.run_discovery(session, term="python", adapters=[a, b], score=False)

    assert run.offers_found == 2
    assert run.offers_new == 1
    assert session.query(Offer).count() == 1


def test_rerunning_adds_no_new_offers(session):
    def fresh():
        return _StubAdapter("stub", [_raw("Backend Dev")])

    graph_mod.run_discovery(session, term="python", adapters=[fresh()], score=False)
    run = graph_mod.run_discovery(session, term="python", adapters=[fresh()], score=False)

    assert run.offers_new == 0
    assert session.query(Offer).count() == 1


def test_one_failing_adapter_yields_partial_run(session):
    good = _StubAdapter("good", [_raw("Backend Dev")])
    bad = _StubAdapter("bad", error=RuntimeError("linkedin blocked"))

    run = graph_mod.run_discovery(
        session, term="python", adapters=[good, bad], score=False
    )

    assert run.status == "partial"
    assert session.query(Offer).count() == 1
    errors = {r["source"]: r["error"] for r in run.source_results}
    assert errors["good"] is None
    assert "linkedin blocked" in errors["bad"]


def test_all_adapters_failing_yields_failed_run(session):
    bad = _StubAdapter("bad", error=RuntimeError("down"))
    run = graph_mod.run_discovery(session, term="python", adapters=[bad], score=False)

    assert run.status == "failed"
    assert run.offers_new == 0


def test_filter_drops_offers_without_title_or_url(session):
    adapter = _StubAdapter(
        "stub",
        [_raw("Backend Dev"), _raw("No Url", url=None)],
    )
    run = graph_mod.run_discovery(session, term="python", adapters=[adapter], score=False)

    assert run.offers_new == 1
    assert session.query(Offer).one().title == "Backend Dev"


def test_filter_applies_locations_and_exclude_keywords(session):
    adapter = _StubAdapter(
        "stub",
        [
            _raw("Backend Dev", location="Madrid", url="https://x/1"),
            _raw("Backend Dev", location="Lisboa", url="https://x/2"),
            _raw("Senior Java Dev", location="Madrid", url="https://x/3"),
        ],
    )
    run = graph_mod.run_discovery(
        session,
        term="python",
        adapters=[adapter],
        filters={"locations": ["Madrid"], "exclude_keywords": ["java"]},
        score=False,
    )

    titles = [o.title for o in session.query(Offer).all()]
    assert titles == ["Backend Dev"]
    assert run.offers_new == 1


def test_the_work_mode_filter_keeps_matching_and_unstated_offers(session):
    """An undetected mode is missing information, not a mismatch: most Spanish
    postings never state it, and dropping them would hide real matches."""
    adapter = _StubAdapter(
        "stub",
        [
            _raw("Remote Dev", url="https://x/1", description="100% remoto"),
            _raw("Office Dev", url="https://x/2", description="Puesto presencial"),
            _raw("Split Dev", url="https://x/3", description="Modelo hibrido"),
            _raw("Quiet Dev", url="https://x/4", description="Buscamos backend"),
        ],
    )
    run = graph_mod.run_discovery(
        session,
        term="python",
        adapters=[adapter],
        filters={"work_mode": ["remote", "hybrid"]},
        score=False,
    )

    stored = {o.title: o.work_mode for o in session.query(Offer).all()}
    assert stored == {
        "Remote Dev": "remote",
        "Split Dev": "hybrid",
        "Quiet Dev": None,
    }
    assert run.offers_new == 3


def test_no_work_mode_filter_keeps_everything(session):
    adapter = _StubAdapter(
        "stub",
        [
            _raw("Remote Dev", url="https://x/1", description="100% remoto"),
            _raw("Office Dev", url="https://x/2", description="Puesto presencial"),
        ],
    )
    graph_mod.run_discovery(session, term="python", adapters=[adapter], score=False)

    assert session.query(Offer).count() == 2




def test_run_records_a_result_for_every_offer_including_refinds(session):
    """A search that surfaces nothing new still returned something."""
    from aje.discovery.results import results_for_run

    adapter = _StubAdapter("stub", [_raw("Backend Engineer")])

    first = graph_mod.run_discovery(
        session, term="python", adapters=[adapter], score=False
    )
    second = graph_mod.run_discovery(
        session, term="python", adapters=[adapter], score=False
    )

    assert session.query(Offer).count() == 1  # still deduped

    first_results = results_for_run(session, first.id)
    second_results = results_for_run(session, second.id)
    assert len(first_results) == 1 and first_results[0].is_new is True
    assert len(second_results) == 1 and second_results[0].is_new is False


def test_the_run_records_what_was_searched(session):
    """A manual run with no saved search would otherwise be anonymous in history."""
    adapter = _StubAdapter("stub", [])

    run = graph_mod.run_discovery(
        session, term="golang remote", adapters=[adapter], score=False
    )

    assert run.term == "golang remote"
    assert run.kind == "manual"


def test_scoring_transitions_are_recorded_on_the_result(session, monkeypatch):
    from aje.discovery.results import results_for_run
    from aje.scoring.schema import ScoringSummary

    adapter = _StubAdapter("stub", [_raw("A")])

    def _fake_score(sess, offer_ids, *, rescore=False, config=None, progress=None):
        for oid in offer_ids:
            progress(oid, "scoring", None)
            progress(oid, "scored", None)
        return ScoringSummary(scored=len(offer_ids))

    monkeypatch.setattr(graph_mod, "score_offers", _fake_score)

    run = graph_mod.run_discovery(session, term="python", adapters=[adapter], score=True)

    assert results_for_run(session, run.id)[0].status == "scored"


def test_max_offers_caps_scoring_not_recording(session, monkeypatch):
    """The cap is a spend limit, so it caps the LLM calls — nothing is hidden."""
    from aje.discovery.results import results_for_run
    from aje.scoring.schema import ScoringSummary

    raws = [_raw(f"Job {i}", url=f"https://x/{i}") for i in range(5)]
    adapter = _StubAdapter("stub", raws)
    scored: list[int] = []

    def _fake_score(sess, offer_ids, *, rescore=False, config=None, progress=None):
        scored.extend(offer_ids)
        for oid in offer_ids:
            progress(oid, "scored", None)
        return ScoringSummary(scored=len(offer_ids))

    monkeypatch.setattr(graph_mod, "score_offers", _fake_score)

    run = graph_mod.run_discovery(
        session, term="python", adapters=[adapter], score=True, max_offers=2
    )

    assert len(scored) == 2
    results = results_for_run(session, run.id)
    assert len(results) == 5
    assert sum(1 for r in results if r.status == "discovered") == 3
