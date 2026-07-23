from aje.db import make_engine, vec_version


def test_sqlite_vec_extension_loads(tmp_path):
    url = f"sqlite:///{(tmp_path / 't.sqlite3').as_posix()}"
    engine = make_engine(url)
    version = vec_version(engine)
    assert isinstance(version, str) and version
