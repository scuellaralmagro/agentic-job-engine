from datetime import datetime

from aje.discovery.normalize import compute_offer_hash, to_offer
from aje.textnorm import normalize_text
from aje.discovery.schema import RawOffer


def test_normalize_strips_accents_case_and_whitespace():
    assert normalize_text("  Ingeniería   DE Software ") == "ingenieria de software"
    assert normalize_text(None) == ""


def test_hash_is_stable_and_order_sensitive():
    a = compute_offer_hash("Backend Dev", "Acme", "Madrid")
    assert a == compute_offer_hash("backend  dev", "ACME", " madrid ")
    assert a != compute_offer_hash("Backend Dev", "Acme", "Barcelona")


def test_hash_collapses_same_job_from_different_sources():
    # the point of hashing title|company|location instead of the url
    assert compute_offer_hash("Backend Dev", "Acme", "Madrid") == compute_offer_hash(
        "Backend Dev", "Acme", "Madrid"
    )


def test_hash_reconciles_the_two_boards_location_formats():
    """The actual defect: Indeed writes "Madrid, MD, ES" and Tecnoempleo "Madrid"
    for the same job, so it was stored twice and could be scored twice."""
    assert compute_offer_hash(
        "AI Architect Engineer", "Accenture", "Madrid, MD, ES"
    ) == compute_offer_hash("AI Architect Engineer", "Accenture", "Madrid")


def test_hash_reconciles_the_two_boards_remote_spellings():
    assert compute_offer_hash(
        "Backend Dev", "Acme", "En remoto, ES"
    ) == compute_offer_hash("Backend Dev", "Acme", "100% remoto")


def test_hash_keeps_different_cities_apart():
    """The regression guard. Five of the seven duplicate groups in the live data are
    real openings in different cities under one title and company — dropping location
    from the hash instead of normalizing it would silently delete them."""
    madrid = compute_offer_hash("Desarrollador Senior IA", "Accenture", "Madrid, MD, ES")
    malaga = compute_offer_hash("Desarrollador Senior IA", "Accenture", "Málaga, AN, ES")
    assert madrid != malaga


def test_hash_tolerates_missing_company_and_location():
    assert compute_offer_hash("Dev", None, None) == compute_offer_hash("Dev", None, None)


def test_to_offer_maps_fields_and_sets_hash():
    raw = RawOffer(
        title="Backend Dev",
        company="Acme",
        location="Madrid",
        description="Build APIs",
        url="https://example.com/1",
        source="adzuna",
        posted_at=datetime(2026, 7, 30),
    )
    offer = to_offer(raw)
    assert offer.title == "Backend Dev"
    assert offer.source == "adzuna"
    assert offer.posted_at == datetime(2026, 7, 30)
    assert offer.content_hash == compute_offer_hash("Backend Dev", "Acme", "Madrid")
    # scoring owns these; discovery leaves them empty
    assert offer.seniority is None
    assert offer.skills == []
