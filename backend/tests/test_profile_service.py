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


def test_reset_profile_clears_everything_and_allows_reingest(session, tmp_path):
    """Source documents must go too: run_extraction dedups on content_hash, so
    leaving them would make re-uploading the same CV a silent no-op."""
    from aje.extraction.profile_service import reset_profile
    from aje.extraction.schema import Skill
    from aje.models import Embedding, SourceDocument

    upload = tmp_path / "cv.pdf"
    upload.write_bytes(b"%PDF-1.4 fake")

    save_profile(session, ProfileData(skills=[Skill(name="Python")]))
    session.add(
        SourceDocument(
            kind="cv", file_ref=str(upload), status="parsed", content_hash="abc"
        )
    )
    session.add(
        Embedding(
            owner_kind="profile_item",
            owner_id=1,
            item_key="skill:python",
            text_hash="h",
            dim=3,
            vector=b"\x00\x00\x00",
        )
    )
    session.commit()

    summary = reset_profile(session)

    assert get_profile(session) == ProfileData()
    assert list_source_documents(session) == []
    assert session.query(Embedding).count() == 0
    assert not upload.exists()
    assert summary.source_documents == 1 and summary.files == 1
    assert summary.embeddings == 1


def test_reset_profile_leaves_offer_embeddings_alone(session):
    """Offers are not profile data — a reset must not force a re-embed of them."""
    from aje.extraction.profile_service import reset_profile
    from aje.models import Embedding

    session.add(
        Embedding(
            owner_kind="offer",
            owner_id=7,
            item_key="offer:7",
            text_hash="h",
            dim=3,
            vector=b"\x00\x00\x00",
        )
    )
    session.commit()

    reset_profile(session)

    assert session.query(Embedding).count() == 1


def test_reset_profile_on_empty_state_is_a_noop(session):
    from aje.extraction.profile_service import reset_profile

    summary = reset_profile(session)

    assert summary.source_documents == 0 and summary.embeddings == 0
    assert get_profile(session) == ProfileData()
