from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.api.profile import get_db_session
from aje.discovery import graph as graph_mod
from aje.discovery import manual as manual_mod
from aje.models import DiscoveryRun, Offer, SavedSearch

router = APIRouter()


class SavedSearchIn(BaseModel):
    name: str
    query: str
    filters: dict = Field(default_factory=dict)
    schedule: str | None = None


class OfferImportIn(BaseModel):
    text: str | None = None
    url: str | None = None


def _search_out(search: SavedSearch) -> dict:
    return {
        "id": search.id,
        "name": search.name,
        "query": search.query,
        "filters": search.filters,
        "schedule": search.schedule,
        "created_at": search.created_at.isoformat(),
    }


def _run_out(run: DiscoveryRun) -> dict:
    return {
        "id": run.id,
        "saved_search_id": run.saved_search_id,
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
    return _search_out(search)


@router.delete("/searches/{search_id}")
def delete_search(search_id: int, session: Session = Depends(get_db_session)) -> dict:
    search = session.get(SavedSearch, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="saved search not found")
    session.delete(search)
    session.commit()
    return {"deleted": search_id}


@router.post("/searches/{search_id}/run")
def run_search(search_id: int, session: Session = Depends(get_db_session)) -> dict:
    if session.get(SavedSearch, search_id) is None:
        raise HTTPException(status_code=404, detail="saved search not found")
    return _run_out(graph_mod.run_saved_search(session, search_id))


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
