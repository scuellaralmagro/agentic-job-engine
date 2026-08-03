"""Pure text/keying helpers for embeddings. No DB, no network."""
from aje.extraction.schema import ProfileData
from aje.keys import achievement_key, experience_key, text_hash
from aje.models import Offer

# text_hash is re-exported: embed.py and test_scoring_texts.py import it from here
__all__ = ["text_hash", "chunk_text", "profile_item_texts", "offer_item_texts"]


def chunk_text(text: str, chunk_chars: int) -> list[str]:
    """Split on blank lines, greedily packing paragraphs up to chunk_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > chunk_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(paragraph[:chunk_chars])
            paragraph = paragraph[chunk_chars:]
        if not paragraph:
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > chunk_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _experience_text(exp: dict) -> str:
    parts = [
        exp.get("title") or "",
        exp.get("company") or "",
        exp.get("description") or "",
        *(exp.get("bullets") or []),
        ", ".join(exp.get("skills") or []),
    ]
    return "\n".join(p for p in parts if p)


def profile_item_texts(profile: ProfileData) -> list[tuple[str, str]]:
    """(item_key, text) for the substantial profile items only.

    Skills, languages and education are short and go into the rubric prompt
    verbatim, so they are deliberately not embedded.
    """
    items: list[tuple[str, str]] = []
    for experience in profile.experiences:
        exp = experience.model_dump()
        items.append(
            (experience_key(exp.get("company"), exp.get("title")), _experience_text(exp))
        )
    for achievement in profile.achievements:
        text = achievement.text
        items.append((achievement_key(text), text))
    return items


def offer_item_texts(offer: Offer, chunk_chars: int) -> list[tuple[str, str]]:
    headline = "\n".join(p for p in (offer.title, offer.company, offer.location) if p)
    items: list[tuple[str, str]] = [("title", headline)]
    for index, chunk in enumerate(chunk_text(offer.description or "", chunk_chars)):
        items.append((f"chunk:{index}", chunk))
    return items
