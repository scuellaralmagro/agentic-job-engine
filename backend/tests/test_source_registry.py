from aje.config import Settings
from aje.discovery.config import SourceSettings, SourcesConfig
from aje.discovery.registry import build_adapters


def _settings(**kwargs) -> Settings:
    return Settings(**kwargs)


def test_builds_only_enabled_adapters():
    config = SourcesConfig(
        sources={
            "adzuna": SourceSettings(enabled=True, country="es"),
            "tecnoempleo": SourceSettings(enabled=False),
            "jobspy": SourceSettings(enabled=True, sites=["linkedin"]),
        }
    )
    adapters = build_adapters(
        config, _settings(adzuna_app_id="id", adzuna_app_key="key")
    )
    assert sorted(a.name for a in adapters) == ["adzuna", "jobspy"]


def test_adzuna_skipped_without_credentials():
    config = SourcesConfig(
        sources={
            "adzuna": SourceSettings(enabled=True),
            "tecnoempleo": SourceSettings(enabled=True),
        }
    )
    adapters = build_adapters(config, _settings())
    assert [a.name for a in adapters] == ["tecnoempleo"]


def test_unknown_source_name_is_ignored():
    config = SourcesConfig(sources={"myspace": SourceSettings(enabled=True)})
    assert build_adapters(config, _settings()) == []


def test_empty_config_yields_no_adapters():
    assert build_adapters(SourcesConfig(), _settings()) == []
