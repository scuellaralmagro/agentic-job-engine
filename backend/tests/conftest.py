import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)()
    yield sess
    sess.close()
