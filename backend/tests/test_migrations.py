import subprocess

from sqlalchemy import create_engine, inspect


def test_upgrade_head_builds_schema(tmp_path, monkeypatch):
    db = tmp_path / "mig.sqlite3"
    monkeypatch.setenv("AJE_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"], check=True, cwd="."
    )
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert "offers" in tables and "profile" in tables
