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
            adapters.append(JobSpyAdapter(source_settings))
        elif name == "tecnoempleo":
            adapters.append(TecnoempleoAdapter(source_settings))
        else:
            logger.warning("unknown source %r in sources.yaml; ignoring", name)
    return adapters
