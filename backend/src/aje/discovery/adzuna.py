from datetime import datetime

import httpx

from aje.discovery.config import SourceSettings
from aje.discovery.schema import RawOffer, SearchQuery

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def _parse_created(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


class AdzunaAdapter:
    name = "adzuna"

    def __init__(
        self,
        settings: SourceSettings,
        app_id: str,
        app_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self.app_id = app_id
        self.app_key = app_key
        self.client = client or httpx.Client(timeout=20.0)

    def search(self, query: SearchQuery) -> list[RawOffer]:
        offers: list[RawOffer] = []
        for term in query.terms[: self.settings.max_terms]:
            offers.extend(self._search_term(term, query))
            if len(offers) >= self.settings.max_results:
                break
        return offers[: self.settings.max_results]

    def _search_term(self, term: str, query: SearchQuery) -> list[RawOffer]:
        params: dict[str, str | int] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": term,
            "results_per_page": self.settings.max_results,
        }
        if query.location:
            params["where"] = query.location
        url = ADZUNA_URL.format(country=self.settings.country or "es", page=1)
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return [self._to_raw_offer(r) for r in response.json().get("results", [])]

    def _to_raw_offer(self, result: dict) -> RawOffer:
        return RawOffer(
            title=result.get("title") or "",
            company=(result.get("company") or {}).get("display_name"),
            location=(result.get("location") or {}).get("display_name"),
            description=result.get("description"),
            url=result.get("redirect_url"),
            source=self.name,
            posted_at=_parse_created(result.get("created")),
        )
