from aje.discovery.config import (
    SourceSettings,
    get_sources_config,
    load_sources_config,
)
from aje.discovery.schema import ExpandedQuery, RawOffer, SearchQuery, SourceResult


def test_search_query_defaults():
    q = SearchQuery(terms=["python"])
    assert q.terms == ["python"]
    assert q.location is None and q.max_results == 50


def test_raw_offer_requires_title_and_source():
    o = RawOffer(title="Backend Dev", source="adzuna")
    assert o.company is None and o.posted_at is None


def test_source_result_defaults():
    r = SourceResult(source="adzuna")
    assert r.count == 0 and r.error is None


def test_expanded_query_holds_terms():
    assert ExpandedQuery(terms=["a", "b"]).terms == ["a", "b"]


def test_load_sources_config(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(
        "sources:\n"
        "  adzuna: { enabled: true, country: es, max_results: 10 }\n"
        "  tecnoempleo: { enabled: false }\n",
        encoding="utf-8",
    )
    cfg = load_sources_config(p)
    assert cfg.enabled_names() == ["adzuna"]
    assert cfg.for_source("adzuna").country == "es"
    assert cfg.for_source("adzuna").max_results == 10
    # unknown source falls back to a disabled default
    assert cfg.for_source("nope") == SourceSettings()


def test_get_sources_config_reads_settings_path(tmp_path, monkeypatch):
    p = tmp_path / "s.yaml"
    p.write_text("sources:\n  jobspy: { enabled: true, sites: [linkedin] }\n", encoding="utf-8")
    monkeypatch.setenv("AJE_SOURCES_CONFIG_PATH", str(p))
    from aje.config import get_settings

    get_settings.cache_clear()
    get_sources_config.cache_clear()
    try:
        assert get_sources_config().for_source("jobspy").sites == ["linkedin"]
    finally:
        get_sources_config.cache_clear()
        get_settings.cache_clear()
