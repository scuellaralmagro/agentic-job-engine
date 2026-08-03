import pytest
from sqlalchemy.orm import Session, sessionmaker

from aje.db import make_engine
from aje.models import Base


@pytest.fixture(autouse=True)
def _tmp_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AJE_DATA_DIR", (tmp_path / "data").as_posix())
    from aje.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_scheduler():
    from aje.discovery.scheduler import reset_scheduler

    reset_scheduler()
    yield
    reset_scheduler()


@pytest.fixture
def session(tmp_path):
    # make_engine (not create_engine) so every connection loads sqlite-vec —
    # the prefilter calls vec_distance_cosine() on this session
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)()
    yield sess
    sess.close()
