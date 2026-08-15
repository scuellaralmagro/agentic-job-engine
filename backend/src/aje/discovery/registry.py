import logging
from typing import Protocol

from aje.config import Settings
from aje.discovery.adzuna import AdzunaAdapter
from aje.discovery.config import SourcesConfig
from aje.discovery.jobspy_source import JobSpyAdapter
from aje.discovery.schema import RawOffer, SearchQuery
from aje.discovery.tecnoempleo import TecnoempleoAdapter

logger = logging.getLogger(__name__)


class SourceAdapter(Protocol):
    name: str

    def search(self, query: SearchQuery) -> list[RawOffer]: ...


def build_adapters(config: SourcesConfig, settings: Settings) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = []
    for name in config.enabled_names():
        source_settings = config.for_source(name)
        if name == "adzuna":
            if not (settings.adzuna_app_id and settings.adzuna_app_key):
                logger.warning("adzuna enabled but credentials missing; skipping")
                continue
            adapters.append(
                AdzunaAdapter(
                    source_settings,
                    app_id=settings.adzuna_app_id,
                    app_key=settings.adzuna_app_key,
                )
            )
        elif name == "jobspy":
            if not source_settings.sites:
                logger.warning("jobspy enabled but no sites configured; skipping")
                continue
            # One adapter per site, not one covering all of them. A single adapter
            # handed every site to one scrape_jobs call and truncated the combined
            # frame, which JobSpy sorts alphabetically by site — so "linkedin" was
            # discarded in full on every run. Splitting them also gives each site its
            # own SourceResult, so a dead board is visible in the run record instead
            # of hiding inside an aggregate count.
            adapters.extend(
                JobSpyAdapter(source_settings, site=site)
                for site in source_settings.sites
            )
        elif name == "tecnoempleo":
            adapters.append(TecnoempleoAdapter(source_settings))
        else:
            logger.warning("unknown source %r in sources.yaml; ignoring", name)
    return adapters
