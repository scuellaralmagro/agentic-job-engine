"""Comparison-normalized text. Pure: no deps beyond the stdlib.

Lives at the package root because keys, adaptation and discovery all compare
text this way. It sat in aje.discovery.normalize, which made every consumer
import from a feature package and left discovery.normalize unable to depend on
anything that also needed it.
"""

import unicodedata


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())
