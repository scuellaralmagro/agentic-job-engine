from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from aje.api.adaptation import router as adaptation_router
from aje.api.discovery import router as discovery_router
from aje.api.profile import router as profile_router
from aje.api.scoring import router as scoring_router
from aje.db import get_engine, get_session, vec_version
from aje.discovery.scheduler import get_scheduler, sync_all_jobs
from aje.llm.providers import register_default_providers


@asynccontextmanager
async def _lifespan(app: FastAPI):
    scheduler = get_scheduler()
    session = get_session()
    try:
        sync_all_jobs(scheduler, session)
    finally:
        session.close()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Job Engine", lifespan=_lifespan)
    register_default_providers()
    app.include_router(profile_router)
    app.include_router(discovery_router)
    app.include_router(scoring_router)
    app.include_router(adaptation_router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/health/db")
    def health_db() -> dict:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "ok"}

    @app.get("/health/vec")
    def health_vec() -> dict:
        return {"sqlite_vec": vec_version(get_engine())}

    return app
