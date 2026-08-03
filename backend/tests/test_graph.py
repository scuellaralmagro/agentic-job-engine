import zipfile
from pathlib import Path

import pytest

from aje.extraction import cv as cv_mod
from aje.extraction import graph as graph_mod
from aje.extraction import merge as merge_mod
from aje.extraction import normalize as normalize_mod
from aje.extraction.profile_service import get_profile, list_source_documents
from aje.extraction.schema import CandidateProfile, Experience, ProfileData, Skill
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


def _stub_linkedin_structuring(monkeypatch, result: CandidateProfile) -> None:
    """The LinkedIn path runs an LLM structuring pass before merge."""
    monkeypatch.setattr(normalize_mod, "llm_for", lambda task: _FakeLLM(result))


def test_run_extraction_linkedin_updates_profile(session, tmp_path, monkeypatch):
    _stub_linkedin_structuring(monkeypatch, CandidateProfile(skills=[Skill(name="Python")]))
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
    _stub_linkedin_structuring(monkeypatch, CandidateProfile(skills=[Skill(name="Go")]))
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


def test_linkedin_export_is_structured_by_an_llm_before_merge(
    session, tmp_path, monkeypatch
):
    """The CSV read is mechanical; the LLM pass is what makes it CV-shaped."""
    seen: dict = {}

    class _CapturingStructured:
        def invoke(self, messages):
            seen["human"] = messages[-1][1]
            seen["system"] = messages[0][1]
            return CandidateProfile(
                experiences=[
                    Experience(
                        company="Acme",
                        title="Backend Engineer",
                        bullets=["Built the billing API", "Led the migration"],
                        skills=["Python"],
                    )
                ]
            )

    class _CapturingLLM:
        def with_structured_output(self, schema):
            return _CapturingStructured()

    monkeypatch.setattr(normalize_mod, "llm_for", lambda task: _CapturingLLM())
    monkeypatch.setattr(
        merge_mod,
        "llm_for",
        lambda task: _FakeLLM(ProfileData(skills=[Skill(name="Python")])),
    )

    zip_path = tmp_path / "in.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Positions.csv",
            "Company Name,Title,Description,Started On,Finished On\n"
            "Acme,Ingeniero Backend,Construi la API de facturacion,2020,2023\n",
        )

    graph_mod.run_extraction(session, zip_path.read_bytes(), "linkedin.zip")

    # the raw CSV values reached the model
    assert "Ingeniero Backend" in seen["human"]
    assert "English" in seen["system"]
    # and its structured output is what gets persisted, not the raw parse
    docs = list_source_documents(session)
    assert docs[0].parsed_json["experiences"][0]["title"] == "Backend Engineer"
    assert len(docs[0].parsed_json["experiences"][0]["bullets"]) == 2


def test_cv_prompt_demands_english():
    assert "English" in cv_mod._SYSTEM
