from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from aje.config import get_settings

_WEIGHT_TOLERANCE = 1e-6


class Weights(BaseModel):
    skills: float = 0.5
    seniority: float = 0.2
    domain: float = 0.2
    language: float = 0.1

    @model_validator(mode="after")
    def _must_sum_to_one(self) -> "Weights":
        total = self.skills + self.seniority + self.domain + self.language
        if abs(total - 1.0) > _WEIGHT_TOLERANCE:
            raise ValueError(f"scoring weights must sum to 1.0, got {total}")
        return self


class PrefilterSettings(BaseModel):
    min_similarity: float = 0.30
    top_k: int = 8
    chunk_chars: int = 800


class QueueSettings(BaseModel):
    threshold: float = 60.0


class ScoringConfig(BaseModel):
    weights: Weights = Field(default_factory=Weights)
    prefilter: PrefilterSettings = Field(default_factory=PrefilterSettings)
    queue: QueueSettings = Field(default_factory=QueueSettings)


def load_scoring_config(path: Path) -> ScoringConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return ScoringConfig.model_validate(data)


@lru_cache
def get_scoring_config() -> ScoringConfig:
    return load_scoring_config(get_settings().scoring_config_path)
