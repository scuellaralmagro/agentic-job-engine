"""recompute offer hashes with canonical location

Revision ID: cf460bdf407d
Revises: fac91cedf090
Create Date: 2026-08-15 16:53:55.950692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import hashlib
import re
import unicodedata


# revision identifiers, used by Alembic.
revision: str = 'cf460bdf407d'
down_revision: Union[str, Sequence[str], None] = 'fac91cedf090'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The hash logic is duplicated here rather than imported from aje.discovery. A
# migration has to keep reproducing what it did the day it ran; importing app code
# would let a later edit to canonical_location silently change what this migration
# does to a database being built from scratch.
_REMOTE_PATTERN = re.compile(r"\b(remoto|remota|remote|teletrabajo)\b")


def _normalize_text(value):
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())


def _canonical_location(value):
    text = _normalize_text(value)
    if not text:
        return ""
    if _REMOTE_PATTERN.search(text):
        return "remote"
    return text.split(",")[0].strip()


def _offer_hash(title, company, location):
    key = "|".join(
        (_normalize_text(title), _normalize_text(company), _canonical_location(location))
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def upgrade() -> None:
    """Recompute every offer's content_hash under the canonical-location rule.

    Forward-only in effect: downgrade restores the old hash function for future
    writes but cannot restore the previous hash *values*, because the raw location
    that produced them is not recoverable from the row once rewritten.

    Two rows of a collided pair cannot both hold the new hash — content_hash is
    unique and merging rows is out of scope — so one keeps the hash it already has
    and becomes an inert historical row, matched by nothing. Which one wins is
    load-bearing: if the unscored row took the canonical hash, every future re-find
    would match it and pay to score a job that was already scored.
    """
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT o.id, o.title, o.company, o.location, o.content_hash, "
            "       (SELECT COUNT(*) FROM matches m WHERE m.offer_id = o.id) AS n "
            "FROM offers o"
        )
    ).fetchall()

    planned = {r.id: _offer_hash(r.title, r.company, r.location) for r in rows}

    def rank(row):
        # 1. a scored row beats an unscored one — it carries the work.
        # 2. then a row already holding its own new hash, because its existing hash
        #    IS the contested value and it has nothing else it could fall back to.
        # 3. then lowest id, for determinism.
        return (
            0 if row.n else 1,
            0 if row.content_hash == planned[row.id] else 1,
            row.id,
        )

    final: dict[int, str] = {}
    taken: set[str] = set()
    for row in sorted(rows, key=rank):
        candidate = planned[row.id]
        if candidate in taken:
            candidate = row.content_hash  # loses; keeps what it had
        final[row.id] = candidate
        taken.add(candidate)

    # Park every row on a unique placeholder first. Assigning final values in place
    # would transiently collide whenever one row takes a hash another still holds.
    conn.execute(sa.text("UPDATE offers SET content_hash = 'migrating:' || id"))
    for offer_id, value in final.items():
        conn.execute(
            sa.text("UPDATE offers SET content_hash = :h WHERE id = :id"),
            {"h": value, "id": offer_id},
        )


def downgrade() -> None:
    """Restores nothing. See upgrade(): the pre-migration hash values are gone.

    Left deliberately empty rather than recomputing under the old rule, which would
    produce hashes that never existed for rows whose location had already been
    reconciled.
    """
    pass
