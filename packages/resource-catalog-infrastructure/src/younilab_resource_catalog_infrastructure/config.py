from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_DIR = Path(__file__).resolve().parents[4]


class ResourceCatalogSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_DIR / ".env", _REPO_DIR / ".env.local"),
        env_prefix="RESOURCE_CATALOG_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str | None = None
    access_control_url: str = "http://127.0.0.1:8000"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
