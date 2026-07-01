from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_DIR = Path(__file__).resolve().parents[4]


class AccessControlSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_DIR / ".env", _REPO_DIR / ".env.local"),
        env_prefix="ACCESS_CONTROL_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str | None = None
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None
    jwt_issuer: str = "younilab-access-control"
    jwt_audience: str = "younilab-seo"
    access_token_minutes: int = Field(default=10, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    portal_url: str = "http://127.0.0.1:5173"
    resource_catalog_url: str = "http://127.0.0.1:8001"
    notification_encryption_key: str | None = None

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
