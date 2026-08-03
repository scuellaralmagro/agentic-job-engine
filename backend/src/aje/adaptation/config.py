from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from aje.config import get_settings


class PageSettings(BaseModel):
    format: str = "A4"
    margin_mm: int = 15


class CvConfig(BaseModel):
    template: str = "cv_default"
    default_language: str = "es"
    page: PageSettings = Field(default_factory=PageSettings)
    # Prompt guidance only — an overshoot is cosmetic and must not discard a draft.
    max_bullets_per_experience: int = 5


def load_cv_config(path: Path) -> CvConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return CvConfig.model_validate(data)


@lru_cache
def get_cv_config() -> CvConfig:
    return load_cv_config(get_settings().cv_config_path)
