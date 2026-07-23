from pathlib import Path

import pytest

from aje.llm import registry


def _write_config(tmp_path: Path) -> Path:
    p = tmp_path / "models.yaml"
    p.write_text(
        "default:\n"
        "  provider: fake\n"
        "  model: base\n"
        "tasks:\n"
        "  scoring:\n"
        "    provider: fake\n"
        "    model: strong\n"
    )
    return p


def test_spec_for_falls_back_to_default(tmp_path):
    cfg = registry.load_model_config(_write_config(tmp_path))
    assert cfg.spec_for("scoring").model == "strong"
    assert cfg.spec_for("unknown_task").model == "base"


def test_build_dispatches_to_registered_provider(tmp_path, monkeypatch):
    seen = {}
    registry.register_chat_provider("fake", lambda spec: seen.update(spec=spec) or "MODEL")
    monkeypatch.setattr(registry, "_config", registry.load_model_config(_write_config(tmp_path)))
    result = registry.llm_for("scoring")
    assert result == "MODEL"
    assert seen["spec"].model == "strong"


def test_unknown_provider_raises(tmp_path):
    spec = registry.ModelSpec(provider="nope", model="x")
    with pytest.raises(registry.UnknownProviderError):
        registry.build_chat_model(spec)
