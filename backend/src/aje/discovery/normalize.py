import hashlib

from aje.discovery.schema import RawOffer
from aje.discovery.work_mode import detect_work_mode
from aje.models import Offer
from aje.textnorm import normalize_text


def compute_offer_hash(
    title: str | None, company: str | None, location: str | None
) -> str:
    key = "|".join(
        (normalize_text(title), normalize_text(company), normalize_text(location))
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def to_offer(raw: RawOffer) -> Offer:
    """Build an unsaved Offer. seniority/skills stay empty — that is scoring's job."""
    return Offer(
        title=raw.title,
        company=raw.company,
        location=raw.location,
        description=raw.description,
        source=raw.source,
        url=raw.url,
        posted_at=raw.posted_at,
        skills=[],
        work_mode=detect_work_mode(
            title=raw.title,
            location=raw.location,
            description=raw.description,
            is_remote=raw.is_remote,
        ),
        content_hash=compute_offer_hash(raw.title, raw.company, raw.location),
    )
