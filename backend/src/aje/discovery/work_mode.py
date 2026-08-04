"""Deterministic remote / hybrid / on-site detection. Pure: no LLM, no DB.

Runs on every offer at normalization time rather than during scoring, so a run
that hit its spend cap still has work modes for the offers it never scored.

The keyword sets are matched against accent-stripped, lowercased text, so
"híbrido" and "hibrido" are the same needle.
"""

from aje.textnorm import normalize_text

REMOTE = "remote"
HYBRID = "hybrid"
ONSITE = "onsite"

# Ordered most specific first only for readability; matching is order-independent.
_HYBRID_TERMS = (
    "hibrido",
    "hibrida",
    "hybrid",
    "semipresencial",
    "semi presencial",
    "teletrabajo parcial",
)

_REMOTE_TERMS = (
    "100% remoto",
    "totalmente remoto",
    "trabajo remoto",
    "en remoto",
    "remoto",
    "remota",
    "teletrabajo",
    "fully remote",
    "remote-first",
    "remote first",
    "work from home",
    "remote",
)

# Deliberately narrow. "oficina" is absent: remote postings routinely mention
# where the company's offices are, and matching it would call them on-site.
#
# Split by how reliably the term describes *this role's* arrangement. Measured
# against 248 real offers: "presencial" is a Spanish posting's statement about
# the job, while the English terms turn up in benefits copy ("compensated
# onsite retreats") and in boilerplate about other roles ("a limited number of
# roles remain office-based") inside postings that are themselves remote.
_ONSITE_STRONG = (
    "100% presencial",
    "presencial",
)

_ONSITE_WEAK = (
    "on-site",
    "on site",
    "onsite",
    "in office",
    "in-office",
)

_ONSITE_TERMS = _ONSITE_STRONG + _ONSITE_WEAK


def _contains(haystack: str, terms: tuple[str, ...]) -> bool:
    return any(term in haystack for term in terms)


def detect_work_mode(
    *,
    title: str | None = None,
    location: str | None = None,
    description: str | None = None,
    is_remote: bool | None = None,
) -> str | None:
    """Return "remote" | "hybrid" | "onsite", or None when the posting is silent.

    None is a real answer: many postings never state the arrangement, and
    guessing one would put a claim in front of the user that nothing supports.
    """
    haystack = normalize_text(" ".join(p for p in (title, location, description) if p))

    hybrid = _contains(haystack, _HYBRID_TERMS)
    remote = _contains(haystack, _REMOTE_TERMS)
    onsite = _contains(haystack, _ONSITE_TERMS)

    if hybrid:
        return HYBRID
    # A posting offering both is usually describing a split week — but only when
    # the on-site half is stated in the language postings use for it. A remote
    # job mentioning "onsite retreats" is still a remote job.
    if remote and _contains(haystack, _ONSITE_STRONG):
        return HYBRID
    if remote:
        return REMOTE
    if onsite:
        return ONSITE
    # The board's own flag is weaker evidence than the posting text, so it is
    # only consulted once the text has said nothing either way.
    if is_remote:
        return REMOTE
    return None
