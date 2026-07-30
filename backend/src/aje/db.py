from functools import lru_cache

import sqlite_vec
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from aje.config import get_settings


def _register_vec_loader(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _load_sqlite_vec(dbapi_conn, _record):  # noqa: ANN001
        dbapi_conn.enable_load_extension(True)
        sqlite_vec.load(dbapi_conn)
        dbapi_conn.enable_load_extension(False)


def make_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, future=True)
    _register_vec_loader(engine)
    return engine


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    # sqlite cannot create its file inside a directory that does not exist yet, and
    # startup touches the database before anything else has a reason to make it
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return make_engine(settings.database_url)


def get_session() -> Session:
    return sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)()


def vec_version(engine: Engine) -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT vec_version()")).scalar_one()
