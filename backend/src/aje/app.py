from fastapi import FastAPI
from sqlalchemy import text

from aje.db import get_engine, vec_version
from aje.llm.providers import register_default_providers


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Job Engine")
    register_default_providers()

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
