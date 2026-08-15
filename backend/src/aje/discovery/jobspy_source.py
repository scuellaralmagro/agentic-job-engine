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


def _to_bool(value: object) -> bool | None:
    """Missing cells arrive as NaN, which is truthy; only a real bool counts."""
    if isinstance(value, bool):
        return value
    if value is None or isinstance(value, float):  # NaN
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0"}:
            return False
    return None


def _to_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return None


class JobSpyAdapter:
    """One instance per board. `registry.build_adapters` creates one per configured
    site, which is load-bearing rather than cosmetic.

    A single adapter covering every site used to hand all of them to one
    `scrape_jobs` call and then truncate with `offers[:max_results]`. JobSpy sorts
    its combined frame alphabetically by site, so "indeed" filled the budget and
    every "linkedin" row was discarded — silently, on every run, after paying to
    scrape it.

    One adapter per site also means the discovery graph's existing per-adapter
    machinery does the rest for free: each site gets its own `max_results`, its own
    `SourceResult` in the run record, its own error isolation, and its own thread.
    """

    def __init__(self, settings: SourceSettings, *, site: str) -> None:
        self.settings = settings
        self.site = site
        self.name = f"jobspy:{site}"

    def search(self, query: SearchQuery) -> list[RawOffer]:
        offers: list[RawOffer] = []
        for term in query.terms[: self.settings.max_terms]:
            offers.extend(self._search_term(term, query))
            if len(offers) >= self.settings.max_results:
                break
        return offers[: self.settings.max_results]

    def _search_term(self, term: str, query: SearchQuery) -> list[RawOffer]:
        frame = scrape_jobs(
            site_name=[self.site],
            search_term=term,
            location=query.location,
            country_indeed=self.settings.country or "Spain",
            results_wanted=self.settings.max_results,
            is_remote=bool(query.remote),
            description_format="markdown",
            # LinkedIn returns no description at all without this, and the scoring
            # rubric reads the description — an offer without one would be scored on
            # its title alone. It costs roughly 0.75s per job (one extra request), so
            # it stays off for boards that already send descriptions.
            linkedin_fetch_description=self.site == "linkedin",
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
        # Taken from the row rather than self.site so the stored source reflects what
        # the board actually said. They agree in practice — an adapter requests one
        # site — but the row is the more truthful of the two.
        site = _clean(row.get("site")) or self.site
        return RawOffer(
            title=title,
            company=_clean(row.get("company")),
            location=_clean(row.get("location")),
            description=_clean(row.get("description")),
            url=_clean(row.get("job_url")),
            source=f"jobspy:{site}",
            posted_at=_to_datetime(row.get("date_posted")),
            is_remote=_to_bool(row.get("is_remote")),
        )
