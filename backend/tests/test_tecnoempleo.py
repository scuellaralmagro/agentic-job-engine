from pathlib import Path

import httpx

from aje.discovery.config import SourceSettings
from aje.discovery.schema import SearchQuery
from aje.discovery.tecnoempleo import TecnoempleoAdapter

_FIXTURE = Path(__file__).parent / "fixtures" / "tecnoempleo_search.html"


def _adapter(handler, **overrides):
    fields = {"enabled": True, "max_results": 10, "delay_seconds": 0.0}
    fields.update(overrides)
    settings = SourceSettings(**fields)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return TecnoempleoAdapter(settings, client=client)


def _fixture_handler(request):
    return httpx.Response(
        200,
        content=_FIXTURE.read_bytes(),
        headers={"content-type": "text/html; charset=iso-8859-1"},
    )


def test_parses_cards_from_fixture():
    offers = _adapter(_fixture_handler).search(SearchQuery(terms=["python"]))

    assert len(offers) == 2
    first = offers[0]
    assert first.title == "Analista de Datos - Python"
    assert first.company == "Arelance"
    assert first.location == "Madrid"
    assert first.url.endswith("rf-dcf916e3b296f32e7548")
    assert first.source == "tecnoempleo"
    assert first.posted_at is not None
    assert (first.posted_at.year, first.posted_at.month, first.posted_at.day) == (
        2026,
        7,
        30,
    )
    assert "Arelance" in first.description


def test_second_card_parsed_independently():
    offers = _adapter(_fixture_handler).search(SearchQuery(terms=["python"]))
    assert offers[1].title == "Backend Developer Python"
    assert offers[1].location == "Barcelona"
    assert offers[1].posted_at.day == 29


def test_sends_search_term_as_te_param():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, content=b"<html></html>")

    _adapter(handler).search(SearchQuery(terms=["python"]))
    assert "ofertas-trabajo" in seen["url"]
    assert "te=python" in seen["url"]


def test_empty_page_yields_no_offers():
    def handler(request):
        return httpx.Response(200, content=b"<html><body></body></html>")

    assert _adapter(handler).search(SearchQuery(terms=["python"])) == []


def test_truncates_to_max_results():
    offers = _adapter(_fixture_handler, max_results=1).search(
        SearchQuery(terms=["python"])
    )
    assert len(offers) == 1
