import zipfile
from pathlib import Path

import pytest

from aje.extraction import cv as cv_mod
from aje.extraction import graph as graph_mod
from aje.extraction import merge as merge_mod
from aje.extraction.profile_service import get_profile, list_source_documents
from aje.extraction.schema import CandidateProfile, ProfileData, Skill
from aje.extraction.text import UnsupportedFileType


class _FakeStructured:
    def __init__(self, result):
        self._result = result

    def invoke(self, messages):
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self._result = result

    def with_structured_output(self, schema):
        return _FakeStructured(self._result)


def _make_linkedin_zip(path: Path) -> bytes:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Skills.csv", "Name\nPython\n")
    return path.read_bytes()


def test_run_extraction_linkedin_updates_profile(session, tmp_path, monkeypatch):
    # merge just returns the candidate as the merged profile
    monkeypatch.setattr(
        merge_mod,
        "llm_for",
        lambda task: _FakeLLM(ProfileData(skills=[Skill(name="Python", source_refs=[1])])),
    )
    content = _make_linkedin_zip(tmp_path / "in.zip")

    result = graph_mod.run_extraction(session, content, "linkedin.zip")

    assert result.skills[0].name == "Python"
    assert get_profile(session).skills[0].name == "Python"
    docs = list_source_documents(session)
    assert len(docs) == 1 and docs[0].status == "parsed"
    assert docs[0].parsed_json["skills"][0]["name"] == "Python"


def test_run_extraction_dedups_duplicate_upload(session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        merge_mod, "llm_for", lambda task: _FakeLLM(ProfileData(skills=[Skill(name="Go")]))
    )
    content = _make_linkedin_zip(tmp_path / "in.zip")
    graph_mod.run_extraction(session, content, "linkedin.zip")
    graph_mod.run_extraction(session, content, "linkedin.zip")
    assert len(list_source_documents(session)) == 1


def test_run_extraction_unsupported_type_raises(session):
    with pytest.raises(UnsupportedFileType):
        graph_mod.run_extraction(session, b"hi", "notes.txt")
    assert list_source_documents(session) == []


def test_run_extraction_failure_marks_failed_and_preserves_profile(
    session, tmp_path, monkeypatch
):
    def _boom(task):
        raise RuntimeError("llm down")

    monkeypatch.setattr(cv_mod, "llm_for", _boom)

    from docx import Document

    docx_path = tmp_path / "cv.docx"
    doc = Document()
    doc.add_paragraph("Backend engineer")
    doc.save(str(docx_path))

    with pytest.raises(RuntimeError):
        graph_mod.run_extraction(session, docx_path.read_bytes(), "cv.docx")

    assert get_profile(session) == ProfileData()
    docs = list_source_documents(session)
    assert len(docs) == 1 and docs[0].status == "failed"
    assert "llm down" in docs[0].parsed_json["error"]
