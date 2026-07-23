from pathlib import Path
from typing import Callable

import yaml
from pydantic import BaseModel, Field

from aje.config import get_settings


class ModelSpec(BaseModel):
    provider: str
    model: str
    params: dict = Field(default_factory=dict)


class ModelConfig(BaseModel):
    default: ModelSpec
    tasks: dict[str, ModelSpec] = Field(default_factory=dict)

    def spec_for(self, task: str) -> ModelSpec:
        return self.tasks.get(task, self.default)


class UnknownProviderError(Exception):
    pass


_CHAT_BUILDERS: dict[str, Callable[[ModelSpec], object]] = {}
_EMBED_BUILDERS: dict[str, Callable[[ModelSpec], object]] = {}
_config: ModelConfig | None = None


def register_chat_provider(name: str, builder: Callable[[ModelSpec], object]) -> None:
    _CHAT_BUILDERS[name] = builder


def register_embeddings_provider(name: str, builder: Callable[[ModelSpec], object]) -> None:
    _EMBED_BUILDERS[name] = builder


def load_model_config(path: Path) -> ModelConfig:
    data = yaml.safe_load(Path(path).read_text())
    return ModelConfig.model_validate(data)


def get_config() -> ModelConfig:
    global _config
    if _config is None:
        _config = load_model_config(get_settings().models_config_path)
    return _config


def build_chat_model(spec: ModelSpec) -> object:
    try:
        builder = _CHAT_BUILDERS[spec.provider]
    except KeyError as exc:
        raise UnknownProviderError(spec.provider) from exc
    return builder(spec)


def build_embeddings(spec: ModelSpec) -> object:
    try:
        builder = _EMBED_BUILDERS[spec.provider]
    except KeyError as exc:
        raise UnknownProviderError(spec.provider) from exc
    return builder(spec)


def llm_for(task: str) -> object:
    return build_chat_model(get_config().spec_for(task))


def embeddings_for(task: str) -> object:
    return build_embeddings(get_config().spec_for(task))
