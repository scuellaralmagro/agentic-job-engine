from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from aje.config import get_settings


class SourceSettings(BaseModel):
    enabled: bool = False
    max_results: int = 50
    max_terms: int = 3
    country: str | None = None
    sites: list[str] = Field(default_factory=list)
    delay_seconds: float = 0.0


class SourcesConfig(BaseModel):
    sources: dict[str, SourceSettings] = Field(default_factory=dict)

    def for_source(self, name: str) -> SourceSettings:
        return self.sources.get(name, SourceSettings())

    def enabled_names(self) -> list[str]:
        return [n for n, s in self.sources.items() if s.enabled]


def load_sources_config(path: Path) -> SourcesConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SourcesConfig.model_validate(data)


@lru_cache
def get_sources_config() -> SourcesConfig:
    return load_sources_config(get_settings().sources_config_path)
