import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.config import get_settings
from aje.discovery.config import get_sources_config
from aje.discovery.expand import expand_query
from aje.discovery.normalize import normalize_text, to_offer
from aje.discovery.registry import build_adapters
from aje.discovery.schema import RawOffer, SearchQuery, SourceResult
from aje.models import DiscoveryRun, Offer, SavedSearch
from aje.scoring.graph import score_offers

logger = logging.getLogger(__name__)

_MAX_WORKERS = 8


class DiscoveryState(TypedDict, total=False):
    term: str
    location: str | None
    remote: bool | None
    filters: dict
    adapters: list
    query: SearchQuery
    raw_offers: list[RawOffer]
    source_results: list[SourceResult]
    offers: list[Offer]
    kept: list[Offer]


def _expand_node(state: DiscoveryState) -> dict:
    terms = expand_query(state["term"])
    return {
        "query": SearchQuery(
            terms=terms,
            location=state.get("location"),
            remote=state.get("remote"),
        )
    }


def _fan_out_node(state: DiscoveryState) -> dict:
    adapters = state["adapters"]
    query = state["query"]

    def _run(adapter):
        try:
            return adapter, adapter.search(query), None
        except Exception as exc:  # noqa: BLE001 - isolation is the whole point
            logger.warning("source %r failed: %s", adapter.name, exc)
            return adapter, [], str(exc)

    raw_offers: list[RawOffer] = []
    results: list[SourceResult] = []
    if adapters:
        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(adapters))) as pool:
            for adapter, offers, error in pool.map(_run, adapters):
                raw_offers.extend(offers)
                results.append(
                    SourceResult(source=adapter.name, count=len(offers), error=error)
                )
    return {"raw_offers": raw_offers, "source_results": results}


def _normalize_node(state: DiscoveryState) -> dict:
    return {"offers": [to_offer(raw) for raw in state["raw_offers"]]}


def _dedup_node(state: DiscoveryState) -> dict:
    seen: set[str] = set()
    unique: list[Offer] = []
    for offer in state["offers"]:
        if offer.content_hash in seen:
            continue
        seen.add(offer.content_hash)
        unique.append(offer)
    return {"offers": unique}


def _coarse_filter_node(state: DiscoveryState) -> dict:
    filters = state.get("filters") or {}
    locations = [normalize_text(loc) for loc in filters.get("locations") or []]
    excluded = [normalize_text(kw) for kw in filters.get("exclude_keywords") or []]

    kept: list[Offer] = []
    for offer in state["offers"]:
        if not offer.title or not offer.url:
            continue
        if locations:
            offer_location = normalize_text(offer.location)
            if not any(loc in offer_location for loc in locations):
                continue
        if excluded:
            title = normalize_text(offer.title)
            if any(kw in title for kw in excluded):
                continue
        kept.append(offer)
    return {"kept": kept}


def build_graph():
    g = StateGraph(DiscoveryState)
    g.add_node("expand", _expand_node)
    g.add_node("fan_out", _fan_out_node)
    g.add_node("normalize", _normalize_node)
    g.add_node("dedup", _dedup_node)
    g.add_node("coarse_filter", _coarse_filter_node)
    g.set_entry_point("expand")
    g.add_edge("expand", "fan_out")
    g.add_edge("fan_out", "normalize")
    g.add_edge("normalize", "dedup")
    g.add_edge("dedup", "coarse_filter")
    g.add_edge("coarse_filter", END)
    return g.compile()


def _status_for(results: list[dict]) -> str:
    if not results:
        return "ok"
    failed = [r for r in results if r["error"]]
    if len(failed) == len(results):
        return "failed"
    return "partial" if failed else "ok"


def _persist_offers(session: Session, offers: list[Offer]) -> list[Offer]:
    if not offers:
        return []
    hashes = [o.content_hash for o in offers]
    existing = set(
        session.execute(
            select(Offer.content_hash).where(Offer.content_hash.in_(hashes))
        ).scalars()
    )
    new_offers = [o for o in offers if o.content_hash not in existing]
    session.add_all(new_offers)
    session.commit()
    return new_offers


def run_discovery(
    session: Session,
    *,
    term: str,
    location: str | None = None,
    remote: bool | None = None,
    filters: dict | None = None,
    saved_search_id: int | None = None,
    adapters: list | None = None,
    score: bool = True,
) -> DiscoveryRun:
    if adapters is None:
        adapters = build_adapters(get_sources_config(), get_settings())

    started_at = datetime.utcnow()
    result = build_graph().invoke(
        {
            "term": term,
            "location": location,
            "remote": remote,
            "filters": filters or {},
            "adapters": adapters,
        }
    )

    source_results = [r.model_dump() for r in result["source_results"]]
    kept = result["kept"]
    new_offers = _persist_offers(session, kept)

    run = DiscoveryRun(
        saved_search_id=saved_search_id,
        started_at=started_at,
        finished_at=datetime.utcnow(),
        status=_status_for(source_results),
        offers_found=len(result["raw_offers"]),
        offers_new=len(new_offers),
        source_results=source_results,
    )
    session.add(run)
    session.commit()

    if score and new_offers:
        try:
            summary = score_offers(session, [o.id for o in new_offers])
            logger.info("scored %s new offers: %s", len(new_offers), summary.model_dump())
        except Exception as exc:  # noqa: BLE001 - discovery must survive a scoring outage
            logger.warning("scoring after discovery failed: %s", exc)

    return run


def run_saved_search(
    session: Session, saved_search_id: int, *, score: bool = True
) -> DiscoveryRun:
    saved = session.get(SavedSearch, saved_search_id)
    if saved is None:
        raise ValueError(f"no saved search with id {saved_search_id}")
    filters = saved.filters or {}
    return run_discovery(
        session,
        term=saved.query,
        location=filters.get("location"),
        remote=filters.get("remote"),
        filters=filters,
        saved_search_id=saved.id,
        score=score,
    )
