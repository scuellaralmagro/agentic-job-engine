from aje.db import make_engine, vec_version


def test_sqlite_vec_extension_loads(tmp_path):
    url = f"sqlite:///{(tmp_path / 't.sqlite3').as_posix()}"
    engine = make_engine(url)
    version = vec_version(engine)
    assert isinstance(version, str) and version


def test_get_engine_creates_missing_data_dir(tmp_path, monkeypatch):
    """A fresh checkout has no data/ dir; startup must not fail on that."""
    from sqlalchemy import text

    from aje.config import get_settings
    from aje.db import get_engine

    target = tmp_path / "brand-new" / "data"
    monkeypatch.setenv("AJE_DATA_DIR", target.as_posix())
    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        assert not target.exists()
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        assert target.exists()
    finally:
        get_engine.cache_clear()
        get_settings.cache_clear()
