from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.extraction.cv import extract_cv
from aje.extraction.linkedin import parse_linkedin_zip
from aje.extraction.merge import merge_into_profile
from aje.extraction.profile_service import get_profile, save_profile
from aje.extraction.schema import CandidateProfile, ProfileData
from aje.extraction.storage import compute_hash, save_upload
from aje.extraction.text import UnsupportedFileType, extract_text
from aje.models import SourceDocument

_CV_EXTS = {".pdf", ".docx"}


class ExtractionState(TypedDict, total=False):
    filename: str
    file_path: str
    existing: ProfileData
    source_id: int
    kind: str
    candidate: CandidateProfile
    profile: ProfileData


def _kind_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in _CV_EXTS:
        return "cv"
    if ext == ".zip":
        return "linkedin_export"
    raise UnsupportedFileType(ext)


def _detect_type(state: ExtractionState) -> dict:
    return {"kind": _kind_for(state["filename"])}


def _route(state: ExtractionState) -> str:
    return state["kind"]


def _extract_cv_node(state: ExtractionState) -> dict:
    text = extract_text(Path(state["file_path"]))
    return {"candidate": extract_cv(text)}


def _parse_linkedin_node(state: ExtractionState) -> dict:
    return {"candidate": parse_linkedin_zip(Path(state["file_path"]))}


def _merge_node(state: ExtractionState) -> dict:
    merged = merge_into_profile(
        state["existing"], state["candidate"], state["source_id"]
    )
    return {"profile": merged}


def build_graph():
    g = StateGraph(ExtractionState)
    g.add_node("detect_type", _detect_type)
    g.add_node("extract_cv", _extract_cv_node)
    g.add_node("parse_linkedin", _parse_linkedin_node)
    g.add_node("merge", _merge_node)
    g.set_entry_point("detect_type")
    g.add_conditional_edges(
        "detect_type",
        _route,
        {"cv": "extract_cv", "linkedin_export": "parse_linkedin"},
    )
    g.add_edge("extract_cv", "merge")
    g.add_edge("parse_linkedin", "merge")
    g.add_edge("merge", END)
    return g.compile()


def run_extraction(session: Session, content: bytes, filename: str) -> ProfileData:
    kind = _kind_for(filename)  # raises UnsupportedFileType before any row is created
    digest = compute_hash(content)

    stmt = select(SourceDocument).where(
        SourceDocument.content_hash == digest, SourceDocument.status == "parsed"
    )
    if session.execute(stmt).scalars().first() is not None:
        return get_profile(session)

    path, _ = save_upload(content, filename)
    doc = SourceDocument(
        kind=kind, file_ref=str(path), status="uploaded", content_hash=digest
    )
    session.add(doc)
    session.commit()

    try:
        result = build_graph().invoke(
            {
                "filename": filename,
                "file_path": str(path),
                "existing": get_profile(session),
                "source_id": doc.id,
            }
        )
    except Exception as exc:
        doc.status = "failed"
        doc.parsed_json = {"error": str(exc)}
        session.commit()
        raise

    save_profile(session, result["profile"])
    doc.status = "parsed"
    doc.parsed_json = result["candidate"].model_dump()
    session.commit()
    return result["profile"]
