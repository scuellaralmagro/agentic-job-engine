import pytest

from aje.discovery import graph as graph_mod
from aje.discovery.schema import RawOffer, SearchQuery
from aje.models import DiscoveryRun, Offer, SavedSearch


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


def _raw(title, company="Acme", location="Madrid", source="stub", url="https://x/1"):
    return RawOffer(
        title=title, company=company, location=location, source=source, url=url
    )


@pytest.fixture(autouse=True)
def _no_llm_expansion(monkeypatch):
    # expansion has its own tests; keep graph tests deterministic
    monkeypatch.setattr(graph_mod, "expand_query", lambda term: [term])


def test_run_persists_offers_and_records_run(session):
    adapter = _StubAdapter(
        "stub", [_raw("Backend Dev"), _raw("Data Eng", url="https://x/2")]
    )

    run = graph_mod.run_discovery(session, term="python", adapters=[adapter])

    assert run.status == "ok"
    assert run.offers_found == 2
    assert run.offers_new == 2
    assert run.finished_at is not None
    assert session.query(Offer).count() == 2
    assert run.source_results == [{"source": "stub", "count": 2, "error": None}]


def test_query_carries_location_to_adapters(session):
    adapter = _StubAdapter("stub", [])
    graph_mod.run_discovery(
        session, term="python", location="Madrid", adapters=[adapter]
    )
    assert adapter.seen_query.location == "Madrid"
    assert adapter.seen_query.terms == ["python"]


def test_duplicate_offers_across_sources_collapse(session):
    a = _StubAdapter("a", [_raw("Backend Dev", source="a", url="https://a/1")])
    b = _StubAdapter("b", [_raw("Backend Dev", source="b", url="https://b/9")])

    run = graph_mod.run_discovery(session, term="python", adapters=[a, b])

    assert run.offers_found == 2
    assert run.offers_new == 1
    assert session.query(Offer).count() == 1


def test_rerunning_adds_no_new_offers(session):
    def fresh():
        return _StubAdapter("stub", [_raw("Backend Dev")])

    graph_mod.run_discovery(session, term="python", adapters=[fresh()])
    run = graph_mod.run_discovery(session, term="python", adapters=[fresh()])

    assert run.offers_new == 0
    assert session.query(Offer).count() == 1


def test_one_failing_adapter_yields_partial_run(session):
    good = _StubAdapter("good", [_raw("Backend Dev")])
    bad = _StubAdapter("bad", error=RuntimeError("linkedin blocked"))

    run = graph_mod.run_discovery(session, term="python", adapters=[good, bad])

    assert run.status == "partial"
    assert session.query(Offer).count() == 1
    errors = {r["source"]: r["error"] for r in run.source_results}
    assert errors["good"] is None
    assert "linkedin blocked" in errors["bad"]


def test_all_adapters_failing_yields_failed_run(session):
    bad = _StubAdapter("bad", error=RuntimeError("down"))
    run = graph_mod.run_discovery(session, term="python", adapters=[bad])

    assert run.status == "failed"
    assert run.offers_new == 0


def test_filter_drops_offers_without_title_or_url(session):
    adapter = _StubAdapter(
        "stub",
        [_raw("Backend Dev"), _raw("No Url", url=None)],
    )
    run = graph_mod.run_discovery(session, term="python", adapters=[adapter])

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
    )

    titles = [o.title for o in session.query(Offer).all()]
    assert titles == ["Backend Dev"]
    assert run.offers_new == 1


def test_run_saved_search_uses_stored_query_and_links_run(session, monkeypatch):
    saved = SavedSearch(
        name="Python Madrid",
        query="python",
        filters={"locations": ["Madrid"]},
    )
    session.add(saved)
    session.commit()

    adapter = _StubAdapter("stub", [_raw("Backend Dev", location="Madrid")])
    monkeypatch.setattr(graph_mod, "build_adapters", lambda config, settings: [adapter])

    run = graph_mod.run_saved_search(session, saved.id)

    assert run.saved_search_id == saved.id
    assert run.offers_new == 1
    assert session.query(DiscoveryRun).count() == 1
