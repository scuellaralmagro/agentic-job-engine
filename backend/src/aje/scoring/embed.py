import struct

from sqlalchemy import delete, select
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from aje.extraction.profile_service import PROFILE_ID, get_profile
from aje.llm.registry import embeddings_for
from aje.models import Embedding, Offer
from aje.scoring.texts import offer_item_texts, profile_item_texts, text_hash

PROFILE_ITEM = "profile_item"
OFFER = "offer"


def pack_vector(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def unpack_vector(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _existing(session: Session, owner_kind: str, owner_id: int) -> dict[str, Embedding]:
    stmt = select(Embedding).where(
        Embedding.owner_kind == owner_kind, Embedding.owner_id == owner_id
    )
    return {row.item_key: row for row in session.execute(stmt).scalars()}


def _sync(
    session: Session,
    owner_kind: str,
    owner_id: int,
    items: list[tuple[str, str]],
) -> tuple[int, dict[str, list[float]]]:
    """Embed only what changed. Returns (embedded_count, {item_key: vector})."""
    existing = _existing(session, owner_kind, owner_id)
    wanted = {key: text_hash(text) for key, text in items}

    stale = [key for key in existing if key not in wanted]
    if stale:
        session.execute(
            delete(Embedding).where(
                Embedding.owner_kind == owner_kind,
                Embedding.owner_id == owner_id,
                Embedding.item_key.in_(stale),
            )
        )

    todo = [
        (key, text)
        for key, text in items
        if key not in existing or existing[key].text_hash != wanted[key]
    ]

    vectors: dict[str, list[float]] = {
        key: unpack_vector(row.vector) for key, row in existing.items() if key in wanted
    }

    if todo:
        produced = embeddings_for("embeddings").embed_documents([text for _, text in todo])
        for (key, _), values in zip(todo, produced, strict=True):
            row = existing.get(key)
            if row is None:
                row = Embedding(owner_kind=owner_kind, owner_id=owner_id, item_key=key)
                session.add(row)
            row.text_hash = wanted[key]
            row.dim = len(values)
            row.vector = pack_vector(values)
            vectors[key] = values

    session.commit()
    return len(todo), vectors


def ensure_profile_embeddings(session: Session) -> int:
    items = profile_item_texts(get_profile(session))
    count, _ = _sync(session, PROFILE_ITEM, PROFILE_ID, items)
    return count


def ensure_offer_embeddings(
    session: Session, offer: Offer, chunk_chars: int
) -> list[list[float]]:
    items = offer_item_texts(offer, chunk_chars)
    _, vectors = _sync(session, OFFER, offer.id, items)
    return [vectors[key] for key, _ in items if key in vectors]


def similar_profile_items(
    session: Session, vector: list[float], limit: int
) -> list[tuple[str, float]]:
    """Profile items closest to `vector`, best first, as (item_key, similarity).

    Brute-force scan with sqlite-vec's distance function — at this scale that is
    faster than maintaining an index, and it keeps migrations free of vec0
    virtual tables. Rows whose dim differs (a provider or model change) are
    ignored rather than compared against.
    """
    rows = session.execute(
        sql_text(
            "SELECT item_key, vec_distance_cosine(vector, :q) AS dist "
            "FROM embeddings "
            "WHERE owner_kind = :kind AND dim = :dim "
            "ORDER BY dist LIMIT :limit"
        ),
        {
            "q": pack_vector(vector),
            "kind": PROFILE_ITEM,
            "dim": len(vector),
            "limit": limit,
        },
    ).all()
    return [(item_key, 1.0 - dist) for item_key, dist in rows]


def rebuild_all_embeddings(session: Session) -> int:
    """Force a full profile re-embed — used after a bulk edit or a model change."""
    session.execute(delete(Embedding).where(Embedding.owner_kind == PROFILE_ITEM))
    session.commit()
    return ensure_profile_embeddings(session)
