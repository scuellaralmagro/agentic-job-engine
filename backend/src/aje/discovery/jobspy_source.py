from datetime import date, datetime

from jobspy import scrape_jobs

from aje.discovery.config import SourceSettings
from aje.discovery.schema import RawOffer, SearchQuery


def _clean(value: object) -> str | None:
    """pandas hands back NaN for missing cells; pydantic will not accept it."""
    if value is None:
        return None
    if isinstance(value, float):  # NaN is the only float we ever expect here
        return None
    text = str(value).strip()
    return text or None


def _to_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return None


class JobSpyAdapter:
    name = "jobspy"

    def __init__(self, settings: SourceSettings) -> None:
        self.settings = settings

    def search(self, query: SearchQuery) -> list[RawOffer]:
        offers: list[RawOffer] = []
        for term in query.terms[: self.settings.max_terms]:
            offers.extend(self._search_term(term, query))
            if len(offers) >= self.settings.max_results:
                break
        return offers[: self.settings.max_results]

    def _search_term(self, term: str, query: SearchQuery) -> list[RawOffer]:
        frame = scrape_jobs(
            site_name=list(self.settings.sites),
            search_term=term,
            location=query.location,
            country_indeed=self.settings.country or "Spain",
            results_wanted=self.settings.max_results,
            is_remote=bool(query.remote),
            description_format="markdown",
        )
        if frame is None or len(frame) == 0:
            return []
        return [
            offer
            for offer in (self._to_raw_offer(row) for row in frame.to_dict("records"))
            if offer is not None
        ]

    def _to_raw_offer(self, row: dict) -> RawOffer | None:
        title = _clean(row.get("title"))
        if not title:
            return None
        site = _clean(row.get("site")) or "unknown"
        return RawOffer(
            title=title,
            company=_clean(row.get("company")),
            location=_clean(row.get("location")),
            description=_clean(row.get("description")),
            url=_clean(row.get("job_url")),
            source=f"{self.name}:{site}",
            posted_at=_to_datetime(row.get("date_posted")),
        )
