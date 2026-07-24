from aje.extraction.profile_service import (
    get_profile,
    list_source_documents,
    save_profile,
)
from aje.extraction.schema import ProfileData, Skill
from aje.models import SourceDocument


def test_get_profile_empty_when_absent(session):
    p = get_profile(session)
    assert p == ProfileData()


def test_save_then_get_round_trips(session):
    save_profile(session, ProfileData(skills=[Skill(name="Rust", source_refs=[3])]))
    got = get_profile(session)
    assert got.skills[0].name == "Rust"
    assert got.skills[0].source_refs == [3]


def test_save_is_idempotent_singleton(session):
    save_profile(session, ProfileData(skills=[Skill(name="A")]))
    save_profile(session, ProfileData(skills=[Skill(name="B")]))
    got = get_profile(session)
    assert [s.name for s in got.skills] == ["B"]


def test_list_source_documents_newest_first(session):
    session.add(SourceDocument(kind="cv", file_ref="a", content_hash="h1"))
    session.add(SourceDocument(kind="cv", file_ref="b", content_hash="h2"))
    session.commit()
    docs = list_source_documents(session)
    assert len(docs) == 2
