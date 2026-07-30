from datetime import date

import pandas as pd

from aje.discovery import jobspy_source
from aje.discovery.config import SourceSettings
from aje.discovery.schema import SearchQuery

_FRAME = pd.DataFrame(
    [
        {
            "site": "linkedin",
            "title": "Backend Engineer",
            "company": "Acme",
            "location": "Madrid, Spain",
            "description": "Python and FastAPI",
            "job_url": "https://linkedin.com/jobs/view/1",
            "date_posted": date(2026, 7, 28),
        },
        {
            "site": "indeed",
            "title": "Data Engineer",
            "company": None,
            "location": float("nan"),
            "description": float("nan"),
            "job_url": "https://es.indeed.com/viewjob?jk=2",
            "date_posted": None,
        },
    ]
)


def _adapter(**overrides):
    fields = {
        "enabled": True,
        "country": "Spain",
        "max_results": 10,
        "sites": ["linkedin", "indeed"],
    }
    fields.update(overrides)
    return jobspy_source.JobSpyAdapter(SourceSettings(**fields))


def test_search_maps_dataframe_to_raw_offers(monkeypatch):
    monkeypatch.setattr(jobspy_source, "scrape_jobs", lambda **kwargs: _FRAME)

    offers = _adapter().search(SearchQuery(terms=["python"], location="Madrid"))

    assert len(offers) == 2
    assert offers[0].title == "Backend Engineer"
    assert offers[0].company == "Acme"
    assert offers[0].source == "jobspy:linkedin"
    assert offers[0].posted_at is not None and offers[0].posted_at.day == 28
    # NaN and None both become None rather than blowing up validation
    assert offers[1].company is None
    assert offers[1].location is None
    assert offers[1].description is None
    assert offers[1].posted_at is None
    assert offers[1].source == "jobspy:indeed"


def test_search_passes_config_through_to_scrape_jobs(monkeypatch):
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return pd.DataFrame([])

    monkeypatch.setattr(jobspy_source, "scrape_jobs", fake)

    _adapter().search(SearchQuery(terms=["python"], location="Madrid", remote=True))

    assert seen["site_name"] == ["linkedin", "indeed"]
    assert seen["search_term"] == "python"
    assert seen["location"] == "Madrid"
    assert seen["country_indeed"] == "Spain"
    assert seen["results_wanted"] == 10
    assert seen["is_remote"] is True


def test_search_handles_empty_frame(monkeypatch):
    monkeypatch.setattr(jobspy_source, "scrape_jobs", lambda **kwargs: pd.DataFrame([]))
    assert _adapter().search(SearchQuery(terms=["python"])) == []


def test_search_skips_rows_without_a_title(monkeypatch):
    frame = pd.DataFrame(
        [
            {"site": "linkedin", "title": None, "job_url": "https://x/1"},
            {"site": "linkedin", "title": "Real Job", "job_url": "https://x/2"},
        ]
    )
    monkeypatch.setattr(jobspy_source, "scrape_jobs", lambda **kwargs: frame)

    offers = _adapter().search(SearchQuery(terms=["python"]))
    assert [o.title for o in offers] == ["Real Job"]


def test_search_queries_each_term_up_to_max_terms(monkeypatch):
    calls = []

    def fake(**kwargs):
        calls.append(kwargs["search_term"])
        return pd.DataFrame([])

    monkeypatch.setattr(jobspy_source, "scrape_jobs", fake)
    _adapter(max_terms=2).search(SearchQuery(terms=["python", "backend", "django"]))

    assert calls == ["python", "backend"]
