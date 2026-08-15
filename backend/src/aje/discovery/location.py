"""Canonical city key for offer dedup. Pure: no LLM, no DB.

Exists because the boards disagree about how to write a place. Indeed sends
"Madrid, MD, ES" and Tecnoempleo sends "Madrid" for the same job, so hashing the
raw location stored it twice and could score it twice.

Normalizing rather than dropping is the point: five of the seven duplicate groups
in the live data are real openings in *different* cities under one title and
company, and only the location keeps them apart.
"""

import re

from aje.textnorm import normalize_text

REMOTE = "remote"

# Word-boundary matched so a city that merely contains the letters — Torremolinos —
# is not read as a remote posting.
_REMOTE_PATTERN = re.compile(r"\b(remoto|remota|remote|teletrabajo)\b")


def canonical_location(value: str | None) -> str:
    """City-level key for `compute_offer_hash`.

    Remote collapses first: a remote posting has no city, and the two boards spell
    it differently ("100% remoto" vs "En remoto, ES"), so without this the likeliest
    future duplicate — one remote role syndicated to both — would never merge.

    Everything else takes the first comma-separated segment, which turns Indeed's
    "City, REGION, COUNTRY" into Tecnoempleo's bare "City" without merging cities.
    """
    text = normalize_text(value)
    if not text:
        return ""
    if _REMOTE_PATTERN.search(text):
        return REMOTE
    return text.split(",")[0].strip()
