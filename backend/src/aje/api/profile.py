from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from aje.db import get_session
from aje.extraction import profile_service
from aje.extraction.graph import run_extraction
from aje.extraction.schema import ProfileData
from aje.extraction.text import EmptyExtraction, UnsupportedFileType

router = APIRouter()


def get_db_session():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/profile/ingest", response_model=ProfileData)
async def ingest(
    file: UploadFile = File(...), session: Session = Depends(get_db_session)
) -> ProfileData:
    content = await file.read()
    try:
        return run_extraction(session, content, file.filename or "")
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {exc}")
    except EmptyExtraction as exc:
        raise HTTPException(status_code=422, detail=f"No text extracted: {exc}")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}")


@router.get("/profile", response_model=ProfileData)
def read_profile(session: Session = Depends(get_db_session)) -> ProfileData:
    return profile_service.get_profile(session)


@router.put("/profile", response_model=ProfileData)
def update_profile(
    data: ProfileData, session: Session = Depends(get_db_session)
) -> ProfileData:
    return profile_service.save_profile(session, data)


@router.delete("/profile")
def reset(session: Session = Depends(get_db_session)) -> dict:
    return profile_service.reset_profile(session).model_dump()


@router.get("/source-documents")
def source_documents(session: Session = Depends(get_db_session)) -> list[dict]:
    return [
        {
            "id": d.id,
            "kind": d.kind,
            "status": d.status,
            "file_ref": d.file_ref,
            "created_at": d.created_at.isoformat(),
        }
        for d in profile_service.list_source_documents(session)
    ]
