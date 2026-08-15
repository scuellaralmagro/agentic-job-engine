from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.api.profile import get_db_session
from aje.discovery import manual as manual_mod
from aje.discovery.estimate import estimate_run
from aje.discovery.jobs import create_run, enqueue_run, start_run_for_search
from aje.discovery.results import results_for_run
from aje.discovery.scheduler import get_scheduler, remove_search_job, sync_search_job
from aje.models import DiscoveryRun, Match, Offer, SavedSearch

router = APIRouter()


class SavedSearchIn(BaseModel):
    name: str
    query: str
    filters: dict = Field(default_factory=dict)
    schedule: str | None = None
    # The default lives here, not only on the column: create_search does
    # SavedSearch(**body.model_dump()), so a None default here would override the
    # column default. Omitted -> 25, explicit null -> uncapped.
    max_offers: Annotated[int, Field(ge=1)] | None = 25


class OfferImportIn(BaseModel):
    text: str | None = None
    url: str | None = None


class RunIn(BaseModel):
    term: str
    filters: dict = Field(default_factory=dict)
    max_offers: int | None = None
    saved_search_id: int | None = None


def _search_out(search: SavedSearch) -> dict:
    return {
        "id": search.id,
        "name": search.name,
        "query": search.query,
        "filters": search.filters,
        "schedule": search.schedule,
        "max_offers": search.max_offers,
        "created_at": search.created_at.isoformat(),
    }


def _run_out(run: DiscoveryRun) -> dict:
    return {
        "id": run.id,
        "saved_search_id": run.saved_search_id,
        "kind": run.kind,
        "term": run.term,
        "filters": run.filters or {},
        "status": run.status,
        "offers_found": run.offers_found,
        "offers_new": run.offers_new,
        "source_results": run.source_results,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def _offer_out(offer: Offer) -> dict:
    return {
        "id": offer.id,
        "title": offer.title,
        "company": offer.company,
        "location": offer.location,
        "seniority": offer.seniority,
        "work_mode": offer.work_mode,
        "skills": offer.skills,
        "description": offer.description,
        "source": offer.source,
        "url": offer.url,
        "posted_at": offer.posted_at.isoformat() if offer.posted_at else None,
        "created_at": offer.created_at.isoformat(),
    }


@router.get("/searches")
def list_searches(session: Session = Depends(get_db_session)) -> list[dict]:
    stmt = select(SavedSearch).order_by(SavedSearch.created_at.desc())
    return [_search_out(s) for s in session.execute(stmt).scalars()]


@router.post("/searches")
def create_search(
    body: SavedSearchIn, session: Session = Depends(get_db_session)
) -> dict:
    search = SavedSearch(**body.model_dump())
    session.add(search)
    session.commit()
    sync_search_job(get_scheduler(), search)
    return _search_out(search)


@router.put("/searches/{search_id}")
def update_search(
    search_id: int, body: SavedSearchIn, session: Session = Depends(get_db_session)
) -> dict:
    search = session.get(SavedSearch, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="saved search not found")
    for field, value in body.model_dump().items():
        setattr(search, field, value)
    session.commit()
    sync_search_job(get_scheduler(), search)
    return _search_out(search)


@router.delete("/searches/{search_id}")
def delete_search(search_id: int, session: Session = Depends(get_db_session)) -> dict:
    search = session.get(SavedSearch, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="saved search not found")
    session.delete(search)
    session.commit()
    remove_search_job(get_scheduler(), search_id)
    return {"deleted": search_id}


@router.post("/searches/{search_id}/run")
def run_search(search_id: int, session: Session = Depends(get_db_session)) -> dict:
    saved = session.get(SavedSearch, search_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="saved search not found")
    run = start_run_for_search(session, saved)
    if run is None:
        raise HTTPException(status_code=409, detail="this search is already running")
    return _run_out(run)


@router.post("/runs")
def create_manual_run(body: RunIn, session: Session = Depends(get_db_session)) -> dict:
    if not body.term.strip():
        raise HTTPException(status_code=400, detail="term is required")
    run = create_run(
        session,
        term=body.term.strip(),
        filters=body.filters,
        kind="scheduled" if body.saved_search_id else "manual",
        saved_search_id=body.saved_search_id,
    )
    enqueue_run(run.id, body.max_offers)
    return _run_out(run)


# Declared before /runs/{run_id}, or FastAPI matches "estimate" as a run id.
@router.get("/runs/estimate")
def run_estimate() -> dict:
    return estimate_run().model_dump()


@router.get("/runs/{run_id}/results")
def run_results(run_id: int, session: Session = Depends(get_db_session)) -> list[dict]:
    if session.get(DiscoveryRun, run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")

    rows = results_for_run(session, run_id)
    offer_ids = [r.offer_id for r in rows] or [0]
    offers = {
        o.id: o
        for o in session.execute(select(Offer).where(Offer.id.in_(offer_ids))).scalars()
    }
    matches = {
        m.offer_id: m
        for m in session.execute(
            select(Match).where(Match.offer_id.in_(offer_ids))
        ).scalars()
    }

    def _match_out(offer_id: int) -> dict | None:
        match = matches.get(offer_id)
        if match is None:
            return None
        return {
            "id": match.id,
            "fitness": match.fitness,
            "status": match.status,
            "above_threshold": match.above_threshold,
        }

    return [
        {
            "id": r.id,
            "offer_id": r.offer_id,
            "offer": _offer_out(offers[r.offer_id]) if r.offer_id in offers else None,
            "is_new": r.is_new,
            "status": r.status,
            "error": r.error,
            "created_at": r.created_at.isoformat(),
            "match": _match_out(r.offer_id),
        }
        for r in rows
    ]


@router.get("/runs")
def list_runs(limit: int = 50, session: Session = Depends(get_db_session)) -> list[dict]:
    stmt = select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(limit)
    return [_run_out(r) for r in session.execute(stmt).scalars()]


@router.get("/runs/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_db_session)) -> dict:
    run = session.get(DiscoveryRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_out(run)


@router.get("/offers")
def list_offers(
    limit: int = 50, offset: int = 0, session: Session = Depends(get_db_session)
) -> list[dict]:
    stmt = select(Offer).order_by(Offer.created_at.desc()).limit(limit).offset(offset)
    return [_offer_out(o) for o in session.execute(stmt).scalars()]


@router.post("/offers/import")
def import_offer_route(
    body: OfferImportIn, session: Session = Depends(get_db_session)
) -> dict:
    try:
        offer = manual_mod.import_offer(session, text=body.text, url=body.url)
    except manual_mod.ManualImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Import failed: {exc}")
    return _offer_out(offer)
