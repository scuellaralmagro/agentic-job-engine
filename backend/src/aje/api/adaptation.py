from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.adaptation.cover_letter import write_cover_letter
from aje.adaptation.graph import adapt_match
from aje.adaptation.persist import render_cover_letter, render_projection
from aje.adaptation.render import PdfEngineError
from aje.adaptation.schema import TailoredCv
from aje.adaptation.validate import AnchorError
from aje.api.profile import get_db_session
from aje.models import CoverLetter, CvProjection, GeneratedDoc

router = APIRouter()


class AdaptIn(BaseModel):
    language: str | None = None
    notes: str | None = None


class ProjectionUpdate(BaseModel):
    # TailoredCv validates structure. Anchors are deliberately not re-checked:
    # past this point it is the user's CV, not the model's.
    content_json: TailoredCv | None = None
    name: str | None = None


def _projection_out(projection: CvProjection) -> dict:
    return {
        "id": projection.id,
        "name": projection.name,
        "offer_id": projection.offer_id,
        "match_id": projection.match_id,
        "language": projection.language,
        "content_json": projection.content_json,
        "suggestions": projection.suggestions,
        "created_at": projection.created_at.isoformat(),
    }


def _doc_out(doc: GeneratedDoc) -> dict:
    return {
        "id": doc.id,
        "kind": doc.kind,
        "offer_id": doc.offer_id,
        "cv_projection_id": doc.cv_projection_id,
        "pdf_ref": doc.pdf_ref,
        "created_at": doc.created_at.isoformat(),
    }


def _get_projection(session: Session, projection_id: int) -> CvProjection:
    projection = session.get(CvProjection, projection_id)
    if projection is None:
        raise HTTPException(status_code=404, detail="projection not found")
    return projection


@router.post("/matches/{match_id}/adapt")
def adapt(
    match_id: int, body: AdaptIn, session: Session = Depends(get_db_session)
) -> dict:
    try:
        projection = adapt_match(
            session, match_id, language=body.language, notes=body.notes
        )
    except AnchorError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Adaptation failed: {exc}")
    return _projection_out(projection)


@router.get("/projections")
def list_projections(
    offer_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> list[dict]:
    stmt = select(CvProjection).order_by(CvProjection.created_at.desc())
    if offer_id is not None:
        stmt = stmt.where(CvProjection.offer_id == offer_id)
    stmt = stmt.limit(limit).offset(offset)
    return [_projection_out(p) for p in session.execute(stmt).scalars()]


@router.get("/projections/{projection_id}")
def read_projection(
    projection_id: int, session: Session = Depends(get_db_session)
) -> dict:
    return _projection_out(_get_projection(session, projection_id))


@router.patch("/projections/{projection_id}")
def update_projection(
    projection_id: int,
    body: ProjectionUpdate,
    session: Session = Depends(get_db_session),
) -> dict:
    projection = _get_projection(session, projection_id)
    if body.content_json is not None:
        projection.content_json = body.content_json.model_dump()
        projection.language = body.content_json.language
    if body.name is not None:
        projection.name = body.name
    session.commit()
    return _projection_out(projection)


@router.delete("/projections/{projection_id}", status_code=204)
def delete_projection(
    projection_id: int, session: Session = Depends(get_db_session)
) -> Response:
    session.delete(_get_projection(session, projection_id))
    session.commit()
    return Response(status_code=204)


@router.post("/projections/{projection_id}/render")
def render(projection_id: int, session: Session = Depends(get_db_session)) -> dict:
    try:
        doc = render_projection(session, projection_id)
    except AnchorError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PdfEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return _doc_out(doc)


@router.get("/docs/{doc_id}/download")
def download(doc_id: int, session: Session = Depends(get_db_session)) -> FileResponse:
    doc = session.get(GeneratedDoc, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = Path(doc.pdf_ref)
    if not path.exists():
        raise HTTPException(status_code=404, detail="document file is missing")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


def _letter_out(letter: CoverLetter) -> dict:
    return {
        "id": letter.id,
        "match_id": letter.match_id,
        "offer_id": letter.offer_id,
        "language": letter.language,
        "content_json": letter.content_json,
        "created_at": letter.created_at.isoformat(),
    }


@router.post("/matches/{match_id}/cover-letter")
def create_cover_letter(
    match_id: int, body: AdaptIn, session: Session = Depends(get_db_session)
) -> dict:
    try:
        letter = write_cover_letter(
            session, match_id, language=body.language, notes=body.notes
        )
    except AnchorError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Cover letter failed: {exc}")
    return _letter_out(letter)


@router.get("/cover-letters/{letter_id}")
def read_cover_letter(letter_id: int, session: Session = Depends(get_db_session)) -> dict:
    letter = session.get(CoverLetter, letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="cover letter not found")
    return _letter_out(letter)


@router.post("/cover-letters/{letter_id}/render")
def render_letter(letter_id: int, session: Session = Depends(get_db_session)) -> dict:
    try:
        doc = render_cover_letter(session, letter_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PdfEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return _doc_out(doc)
