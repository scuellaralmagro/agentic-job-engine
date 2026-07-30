import logging

from aje.discovery.schema import ExpandedQuery
from aje.llm.registry import llm_for

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You expand a job-search term into a short list of equivalent search terms for "
    "job boards in Spain. Include common English and Spanish variants of the same "
    "role (e.g. 'Backend Engineer' -> 'Desarrollador Backend', 'Ingeniero de "
    "Software'). Return at most 5 terms. Do not broaden the seniority or change the "
    "specialisation."
)


def expand_query(term: str) -> list[str]:
    """Expand a search term. Always returns at least [term]; never raises."""
    try:
        model = llm_for("discovery").with_structured_output(ExpandedQuery)
        result = model.invoke([("system", _SYSTEM), ("human", term)])
        expanded = [t.strip() for t in result.terms if t and t.strip()]
    except Exception:  # noqa: BLE001 - expansion is best-effort by design
        logger.warning("query expansion failed for %r; using literal term", term)
        return [term]

    terms = [term]
    terms.extend(t for t in expanded if t != term)
    return terms
