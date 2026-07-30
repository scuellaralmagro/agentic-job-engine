import re
import time
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from aje.discovery.config import SourceSettings
from aje.discovery.schema import RawOffer, SearchQuery

SEARCH_URL = "https://www.tecnoempleo.com/ofertas-trabajo/"
_CARD_SELECTOR = "div.p-3.border.rounded.mb-3.bg-white"
_DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
_USER_AGENT = "Mozilla/5.0 (compatible; agentic-job-engine/0.1)"


def _parse_date(text: str) -> datetime | None:
    match = _DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y")
    except ValueError:
        return None


class TecnoempleoAdapter:
    name = "tecnoempleo"

    def __init__(
        self, settings: SourceSettings, client: httpx.Client | None = None
    ) -> None:
        self.settings = settings
        self.client = client or httpx.Client(
            timeout=20.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        )

    def search(self, query: SearchQuery) -> list[RawOffer]:
        offers: list[RawOffer] = []
        for index, term in enumerate(query.terms[: self.settings.max_terms]):
            if index and self.settings.delay_seconds:
                time.sleep(self.settings.delay_seconds)
            offers.extend(self._search_term(term))
            if len(offers) >= self.settings.max_results:
                break
        return offers[: self.settings.max_results]

    def _search_term(self, term: str) -> list[RawOffer]:
        response = self.client.get(SEARCH_URL, params={"te": term})
        response.raise_for_status()
        # bytes, not .text — the page is ISO-8859-1 and bs4 sniffs it correctly
        soup = BeautifulSoup(response.content, "lxml")
        parsed = (self._to_raw_offer(card) for card in soup.select(_CARD_SELECTOR))
        return [offer for offer in parsed if offer is not None]

    def _to_raw_offer(self, card) -> RawOffer | None:  # noqa: ANN001
        link = card.select_one("h3 a")
        if link is None:
            return None
        title = link.get_text(strip=True)
        if not title:
            return None

        company_el = card.select_one("a.text-primary.link-muted")
        meta_el = card.select_one("span.d-block.d-lg-none.text-gray-800")
        desc_el = card.select_one("span.hidden-md-down.text-gray-800")

        location = None
        posted_at = None
        if meta_el is not None:
            bold = meta_el.find("b")
            location = bold.get_text(strip=True) if bold else None
            posted_at = _parse_date(meta_el.get_text(" ", strip=True))

        return RawOffer(
            title=title,
            company=company_el.get_text(strip=True) if company_el else None,
            location=location,
            description=desc_el.get_text(" ", strip=True) if desc_el else None,
            url=link.get("href"),
            source=self.name,
            posted_at=posted_at,
        )
