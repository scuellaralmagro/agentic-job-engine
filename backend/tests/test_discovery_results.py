from aje.discovery import results as results_mod
from aje.models import DiscoveryResult, DiscoveryRun, Match, Offer


def _run(session) -> DiscoveryRun:
    run = DiscoveryRun(status="running", kind="manual", term="python", filters={})
    session.add(run)
    session.commit()
    return run


def _offer(session, h: str) -> Offer:
    offer = Offer(title="A", source="test", content_hash=h, skills=[])
    session.add(offer)
    session.commit()
    return offer


def test_record_result_is_idempotent_per_run_and_offer(session):
    """Two adapters returning the same posting is one result row."""
    run, offer = _run(session), _offer(session, "h1")

    results_mod.record_result(
        session,
        run_id=run.id,
        offer_id=offer.id,
        is_new=True,
        status=results_mod.DISCOVERED,
    )
    results_mod.record_result(
        session,
        run_id=run.id,
        offer_id=offer.id,
        is_new=True,
        status=results_mod.DISCOVERED,
    )

    assert session.query(DiscoveryResult).count() == 1


def test_set_result_status_commits_so_a_poller_sees_it(session):
    run, offer = _run(session), _offer(session, "h1")
    results_mod.record_result(
        session,
        run_id=run.id,
        offer_id=offer.id,
        is_new=True,
        status=results_mod.DISCOVERED,
    )

    results_mod.set_result_status(
        session,
        run_id=run.id,
        offer_id=offer.id,
        status=results_mod.FAILED,
        error="boom",
    )

    row = session.query(DiscoveryResult).one()
    assert row.status == "failed" and row.error == "boom"
    assert not session.dirty  # already flushed and committed


def test_status_for_known_offer_reads_its_existing_match(session):
    offer = _offer(session, "h1")
    session.add(Match(offer_id=offer.id, profile_id=1, fitness=80.0, scored_by="rubric"))
    session.commit()

    assert results_mod.status_for_known_offer(session, offer.id) == results_mod.SCORED


def test_a_vector_gated_offer_reads_as_prefiltered(session):
    offer = _offer(session, "h2")
    session.add(Match(offer_id=offer.id, profile_id=1, fitness=10.0, scored_by="vector"))
    session.commit()

    assert (
        results_mod.status_for_known_offer(session, offer.id) == results_mod.PREFILTERED
    )


def test_a_known_offer_that_was_never_scored_reads_as_discovered(session):
    """A manual import has no Match — it is in the system but unprocessed."""
    offer = _offer(session, "h3")

    assert results_mod.status_for_known_offer(session, offer.id) == results_mod.DISCOVERED
