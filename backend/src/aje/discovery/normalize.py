import hashlib
import unicodedata

from aje.discovery.schema import RawOffer
from aje.models import Offer


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())


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
        content_hash=compute_offer_hash(raw.title, raw.company, raw.location),
    )
