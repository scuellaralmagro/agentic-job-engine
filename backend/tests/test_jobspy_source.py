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


def _adapter(site="linkedin", **overrides):
    fields = {
        "enabled": True,
        "country": "Spain",
        "max_results": 10,
        "sites": ["linkedin", "indeed"],
    }
    fields.update(overrides)
    return jobspy_source.JobSpyAdapter(SourceSettings(**fields), site=site)


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

    assert seen["site_name"] == ["linkedin"]
    assert seen["search_term"] == "python"
    assert seen["location"] == "Madrid"
    assert seen["country_indeed"] == "Spain"
    assert seen["results_wanted"] == 10
    assert seen["is_remote"] is True


def test_one_adapter_scrapes_exactly_one_site(monkeypatch):
    """Sites used to share a single scrape and a single max_results truncation.

    JobSpy sorts its combined frame alphabetically by site, so 'indeed' filled the
    budget and every 'linkedin' row was discarded by offers[:max_results] — silently,
    on every run, for the project's whole history.
    """
    seen = []
    monkeypatch.setattr(
        jobspy_source,
        "scrape_jobs",
        lambda **kw: seen.append(kw["site_name"]) or pd.DataFrame([]),
    )

    _adapter(site="indeed").search(SearchQuery(terms=["python"]))

    assert seen == [["indeed"]], "one adapter must never scrape a sibling's site"


def test_the_adapter_is_named_for_its_site(monkeypatch):
    """_fan_out_node builds one SourceResult per adapter.name, so this is what makes
    a dead site visible in run history instead of hiding inside an aggregate row."""
    assert _adapter(site="linkedin").name == "jobspy:linkedin"
    assert _adapter(site="indeed").name == "jobspy:indeed"


def test_linkedin_fetches_descriptions_but_other_sites_do_not(monkeypatch):
    """LinkedIn returns no description at all unless asked, and the rubric reads the
    description — an offer without one scores on its title alone. Costs ~0.75s/job,
    so it is only turned on for the site that needs it."""
    seen = {}

    def fake(**kwargs):
        seen[kwargs["site_name"][0]] = kwargs.get("linkedin_fetch_description")
        return pd.DataFrame([])

    monkeypatch.setattr(jobspy_source, "scrape_jobs", fake)

    _adapter(site="linkedin").search(SearchQuery(terms=["python"]))
    _adapter(site="indeed").search(SearchQuery(terms=["python"]))

    assert seen["linkedin"] is True
    assert not seen["indeed"]


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
