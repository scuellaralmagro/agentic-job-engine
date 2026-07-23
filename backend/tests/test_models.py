from sqlalchemy import create_engine, inspect

from aje.models import Base, Offer


def test_metadata_creates_all_tables(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'm.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {
        "profile",
        "source_documents",
        "cv_projections",
        "offers",
        "saved_searches",
        "matches",
        "generated_docs",
    } <= tables


def test_offer_content_hash_unique():
    cols = {c.name: c for c in Offer.__table__.columns}
    assert cols["content_hash"].unique is True
