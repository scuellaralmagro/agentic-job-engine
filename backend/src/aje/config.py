from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AJE_", env_file=".env", extra="ignore"
    )

    data_dir: Path = Path("./data")
    database_url: str | None = None
    models_config_path: Path = Path("./config/models.yaml")

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    @model_validator(mode="after")
    def _derive_database_url(self) -> "Settings":
        if self.database_url is None:
            db_path = (self.data_dir / "aje.sqlite3").as_posix()
            self.database_url = f"sqlite:///{db_path}"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
