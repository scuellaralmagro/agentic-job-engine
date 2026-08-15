import subprocess

from sqlalchemy import create_engine, inspect, text


def test_upgrade_head_builds_schema(tmp_path, monkeypatch):
    db = tmp_path / "mig.sqlite3"
    monkeypatch.setenv("AJE_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"], check=True, cwd="."
    )
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert "offers" in tables and "profile" in tables
    assert "discovery_runs" in tables
    cols = {c["name"] for c in inspect(engine).get_columns("offers")}
    assert "posted_at" in cols
    assert "embeddings" in tables
    match_cols = {c["name"] for c in inspect(engine).get_columns("matches")}
    assert {"status", "scored_by", "similarity", "scored_at"} <= match_cols
    profile_cols = {c["name"] for c in inspect(engine).get_columns("profile")}
    assert "contact" in profile_cols
    projection_cols = {c["name"] for c in inspect(engine).get_columns("cv_projections")}
    assert {"match_id", "suggestions", "language"} <= projection_cols
    assert "cover_letters" in tables
    search_cols = {c["name"] for c in inspect(engine).get_columns("saved_searches")}
    assert "max_offers" in search_cols


def _insert_offer(conn, *, offer_id, title, company, location, content_hash, source):
    conn.execute(
        text(
            "INSERT INTO offers (id, title, company, location, skills, source, "
            "content_hash, created_at) VALUES (:i, :t, :c, :l, '[]', :s, :h, "
            "'2026-01-01 00:00:00')"
        ),
        {
            "i": offer_id,
            "t": title,
            "c": company,
            "l": location,
            "s": source,
            "h": content_hash,
        },
    )


def test_recomputed_hashes_keep_both_rows_and_favour_the_scored_one(
    tmp_path, monkeypatch
):
    """The two boards write one Madrid job two ways, so it was stored twice.

    Recomputing merges the key, but content_hash is unique and both rows survive, so
    one keeps its old hash. The scored row must be the one holding the canonical
    hash — otherwise every future re-find matches the unscored row and pays to score
    a job that was already scored.
    """
    db = tmp_path / "dedup.sqlite3"
    monkeypatch.setenv("AJE_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "fac91cedf090"], check=True, cwd="."
    )

    engine = create_engine(f"sqlite:///{db.as_posix()}")
    with engine.begin() as conn:
        # same job, two boards, two spellings — the defect being fixed
        _insert_offer(
            conn,
            offer_id=1,
            title="AI Architect Engineer",
            company="Accenture",
            location="Madrid, MD, ES",
            content_hash="old-indeed",
            source="jobspy:indeed",
        )
        _insert_offer(
            conn,
            offer_id=2,
            title="AI Architect Engineer",
            company="Accenture",
            location="Madrid",
            content_hash="old-tecnoempleo",
            source="tecnoempleo",
        )
        # a different city under the same title+company must NOT be merged
        _insert_offer(
            conn,
            offer_id=3,
            title="AI Architect Engineer",
            company="Accenture",
            location="Málaga, AN, ES",
            content_hash="old-malaga",
            source="jobspy:indeed",
        )
        # only the Tecnoempleo row has been scored
        conn.execute(
            text(
                "INSERT INTO matches (offer_id, fitness, rubric, gaps, "
                "above_threshold, created_at) VALUES (2, 70.0, '{}', '[]', 1, "
                "'2026-01-01 00:00:00')"
            )
        )

    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True, cwd=".")

    with engine.connect() as conn:
        hashes = dict(
            conn.execute(text("SELECT id, content_hash FROM offers")).fetchall()
        )

    assert len(hashes) == 3, "no row may be deleted"
    assert hashes[2] != "old-tecnoempleo", "the scored row takes the canonical hash"
    assert hashes[1] != hashes[2], "the loser keeps a distinct hash"
    assert hashes[3] not in (hashes[1], hashes[2]), "Málaga is a different opening"


def test_existing_saved_searches_are_backfilled_with_a_cap(tmp_path, monkeypatch):
    """A search created before the column existed must not stay uncapped.

    At migration time no NULL can be a deliberate "score everything" choice, so
    treating them all as "never set" is the safe reading. After the migration a
    NULL is only ever something the user chose.
    """
    db = tmp_path / "backfill.sqlite3"
    monkeypatch.setenv("AJE_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "dae74d08d7a4"], check=True, cwd="."
    )

    engine = create_engine(f"sqlite:///{db.as_posix()}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO saved_searches (name, query, filters, schedule, created_at) "
                "VALUES ('legacy', 'python', '{}', '0 8 * * *', '2026-01-01 00:00:00')"
            )
        )

    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True, cwd=".")

    with engine.connect() as conn:
        cap = conn.execute(text("SELECT max_offers FROM saved_searches")).scalar()
    assert cap == 25
