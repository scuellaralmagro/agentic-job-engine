from datetime import datetime

from aje.models import DiscoveryRun, Offer


def test_offer_accepts_posted_at(session):
    session.add(
        Offer(
            title="Dev",
            source="adzuna",
            content_hash="h1",
            posted_at=datetime(2026, 7, 30, 12, 0),
        )
    )
    session.commit()
    got = session.query(Offer).one()
    assert got.posted_at == datetime(2026, 7, 30, 12, 0)


def test_offer_posted_at_is_optional(session):
    session.add(Offer(title="Dev", source="adzuna", content_hash="h2"))
    session.commit()
    assert session.query(Offer).one().posted_at is None


def test_discovery_run_defaults(session):
    run = DiscoveryRun(status="ok")
    session.add(run)
    session.commit()
    got = session.query(DiscoveryRun).one()
    assert got.offers_found == 0
    assert got.offers_new == 0
    assert got.source_results == []
    assert got.saved_search_id is None
    assert got.finished_at is None
    assert got.started_at is not None


def test_discovery_run_stores_source_results(session):
    session.add(
        DiscoveryRun(
            status="partial",
            offers_found=5,
            offers_new=2,
            source_results=[{"source": "adzuna", "count": 5, "error": None}],
        )
    )
    session.commit()
    got = session.query(DiscoveryRun).one()
    assert got.source_results[0]["source"] == "adzuna"
    assert got.status == "partial"


def test_discovery_result_links_a_run_to_an_offer(session):
    from aje.models import DiscoveryResult

    offer = Offer(title="Backend Engineer", source="test", content_hash="dr1", skills=[])
    run = DiscoveryRun(status="running", kind="manual", term="python", filters={})
    session.add_all([offer, run])
    session.commit()

    session.add(
        DiscoveryResult(
            run_id=run.id, offer_id=offer.id, is_new=True, status="discovered"
        )
    )
    session.commit()

    row = session.query(DiscoveryResult).one()
    assert row.run_id == run.id and row.offer_id == offer.id
    assert row.is_new is True and row.status == "discovered"
    assert row.error is None


def test_a_run_reports_an_offer_only_once(session):
    import pytest
    from sqlalchemy.exc import IntegrityError

    from aje.models import DiscoveryResult

    offer = Offer(title="A", source="test", content_hash="dr2", skills=[])
    run = DiscoveryRun(status="running", kind="manual", term="go", filters={})
    session.add_all([offer, run])
    session.commit()

    session.add(
        DiscoveryResult(run_id=run.id, offer_id=offer.id, is_new=True, status="discovered")
    )
    session.commit()
    session.add(
        DiscoveryResult(run_id=run.id, offer_id=offer.id, is_new=False, status="scored")
    )

    with pytest.raises(IntegrityError):
        session.commit()
