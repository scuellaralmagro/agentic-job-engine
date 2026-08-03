from aje.discovery import graph as discovery_graph
from aje.discovery.schema import RawOffer
from aje.models import DiscoveryRun


class _FakeAdapter:
    name = "fake"

    def search(self, query):
        return [
            RawOffer(
                title="Backend Engineer",
                company="Acme",
                location="Madrid",
                description="python fastapi",
                url="https://example.test/1",
                source="fake",
            )
        ]


def _run(session, monkeypatch, *, score, spy):
    monkeypatch.setattr(discovery_graph, "expand_query", lambda term: [term])
    monkeypatch.setattr(discovery_graph, "score_offers", spy)
    return discovery_graph.run_discovery(
        session, term="python", adapters=[_FakeAdapter()], score=score
    )


def test_new_offers_are_scored_after_a_run(session, monkeypatch):
    seen = {}

    def _spy(sess, offer_ids, **kwargs):
        seen["ids"] = offer_ids
        seen["progress"] = kwargs.get("progress")
        from aje.scoring.schema import ScoringSummary

        return ScoringSummary(scored=len(offer_ids))

    run = _run(session, monkeypatch, score=True, spy=_spy)

    assert run.offers_new == 1
    assert len(seen["ids"]) == 1
    # discovery hands scoring a progress sink so result rows track the LLM call
    assert callable(seen["progress"])


def test_scoring_can_be_switched_off(session, monkeypatch):
    def _spy(sess, offer_ids, **kwargs):
        raise AssertionError("scoring should not have run")

    _run(session, monkeypatch, score=False, spy=_spy)


def test_a_scoring_failure_never_fails_the_discovery_run(session, monkeypatch):
    def _boom(sess, offer_ids, **kwargs):
        raise RuntimeError("embeddings down")

    run = _run(session, monkeypatch, score=True, spy=_boom)

    # discovery's job is finding offers; a scoring outage must not lose them
    assert isinstance(run, DiscoveryRun)
    assert run.offers_new == 1
    assert run.status == "ok"
