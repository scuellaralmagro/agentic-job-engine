import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.discovery.normalize import to_offer
from aje.discovery.schema import RawOffer
from aje.llm.registry import llm_for
from aje.models import Offer

_SYSTEM = (
    "You extract a single job offer from the text of a job posting. Capture the "
    "title, company, location and a plain-text description. Do not invent details "
    "that are not present. Leave unknown fields empty."
)
_USER_AGENT = "Mozilla/5.0 (compatible; agentic-job-engine/0.1)"


class ManualImportError(Exception):
    pass


def structure_offer_text(text: str, url: str | None = None) -> RawOffer:
    model = llm_for("discovery").with_structured_output(RawOffer)
    raw = model.invoke([("system", _SYSTEM), ("human", text)])
    # the model does not get to decide provenance
    raw.source = "manual"
    if url:
        raw.url = url
    return raw


def import_offer(
    session: Session,
    *,
    text: str | None = None,
    url: str | None = None,
    client: httpx.Client | None = None,
) -> Offer:
    if not text and not url:
        raise ManualImportError("provide text or url")

    if not text:
        http = client or httpx.Client(
            timeout=20.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        )
        response = http.get(url)
        response.raise_for_status()
        text = response.text

    offer = to_offer(structure_offer_text(text, url))
    existing = (
        session.execute(select(Offer).where(Offer.content_hash == offer.content_hash))
        .scalars()
        .first()
    )
    if existing is not None:
        return existing

    session.add(offer)
    session.commit()
    return offer
