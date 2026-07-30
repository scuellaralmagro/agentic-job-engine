import httpx

from aje.discovery.adzuna import AdzunaAdapter
from aje.discovery.config import SourceSettings
from aje.discovery.schema import SearchQuery

_PAYLOAD = {
    "results": [
        {
            "id": "1",
            "title": "Backend Developer",
            "company": {"display_name": "Acme"},
            "location": {"display_name": "Madrid, Madrid"},
            "description": "Build APIs with Python",
            "redirect_url": "https://www.adzuna.es/details/1",
            "created": "2026-07-29T10:15:00Z",
        },
        {
            "id": "2",
            "title": "Data Engineer",
            "company": {},
            "location": {},
            "description": "ETL",
            "redirect_url": "https://www.adzuna.es/details/2",
        },
    ]
}


def _adapter(handler, **overrides):
    fields = {"enabled": True, "country": "es", "max_results": 10}
    fields.update(overrides)
    settings = SourceSettings(**fields)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AdzunaAdapter(settings, app_id="id", app_key="key", client=client)


def test_search_maps_results_to_raw_offers():
    def handler(request):
        return httpx.Response(200, json=_PAYLOAD)

    offers = _adapter(handler).search(SearchQuery(terms=["python"], location="Madrid"))

    assert len(offers) == 2
    first = offers[0]
    assert first.title == "Backend Developer"
    assert first.company == "Acme"
    assert first.location == "Madrid, Madrid"
    assert first.url == "https://www.adzuna.es/details/1"
    assert first.source == "adzuna"
    assert first.posted_at is not None and first.posted_at.year == 2026
    # missing company/location/created degrade to None rather than raising
    assert offers[1].company is None
    assert offers[1].location is None
    assert offers[1].posted_at is None


def test_search_sends_credentials_and_query_params():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"results": []})

    _adapter(handler).search(SearchQuery(terms=["python"], location="Madrid"))

    assert "/jobs/es/search/1" in seen["url"]
    assert "app_id=id" in seen["url"] and "app_key=key" in seen["url"]
    assert "what=python" in seen["url"]
    assert "where=Madrid" in seen["url"]


def test_search_queries_each_term_up_to_max_terms():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"results": []})

    _adapter(handler, max_terms=2).search(
        SearchQuery(terms=["python", "backend", "django"])
    )

    assert len(calls) == 2
    assert "what=python" in calls[0] and "what=backend" in calls[1]


def test_search_truncates_to_max_results():
    def handler(request):
        return httpx.Response(200, json=_PAYLOAD)

    offers = _adapter(handler, max_results=1).search(SearchQuery(terms=["python"]))
    assert len(offers) == 1


def test_http_error_propagates_to_caller():
    def handler(request):
        return httpx.Response(500, text="boom")

    try:
        _adapter(handler).search(SearchQuery(terms=["python"]))
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("expected HTTPStatusError to propagate")
