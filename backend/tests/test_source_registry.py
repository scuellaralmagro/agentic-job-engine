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
    assert sorted(a.name for a in adapters) == ["adzuna", "jobspy:linkedin"]


def test_jobspy_yields_one_adapter_per_site():
    """Each site needs its own adapter to get its own max_results and SourceResult.
    Sharing one truncated every site after the alphabetically-first."""
    config = SourcesConfig(
        sources={"jobspy": SourceSettings(enabled=True, sites=["linkedin", "indeed"])}
    )
    adapters = build_adapters(config, _settings())

    assert [a.name for a in adapters] == ["jobspy:linkedin", "jobspy:indeed"]
    assert [a.site for a in adapters] == ["linkedin", "indeed"]


def test_jobspy_without_sites_is_skipped():
    config = SourcesConfig(sources={"jobspy": SourceSettings(enabled=True, sites=[])})
    assert build_adapters(config, _settings()) == []


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
