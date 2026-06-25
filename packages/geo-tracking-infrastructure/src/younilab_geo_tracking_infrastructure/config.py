import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from younilab_geo_tracking_domain import ProviderCode, RegionCode


def _provider_from_env() -> ProviderCode:
    return ProviderCode(os.getenv("GEO_TRACKING_PROVIDER", ProviderCode.DUMMY))


def _float_from_env(name: str, default: str) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class SerpApiLocaleProfile:
    default_language: str
    hl: str
    gl: str
    location: str


SERPAPI_LOCALE_PROFILES: dict[RegionCode, SerpApiLocaleProfile] = {
    RegionCode.TAIWAN: SerpApiLocaleProfile(
        default_language="zh-TW",
        hl="zh-tw",
        gl="tw",
        location="Taiwan",
    ),
    RegionCode.UNITED_STATES: SerpApiLocaleProfile(
        default_language="en-US",
        hl="en",
        gl="us",
        location="United States",
    ),
}


@dataclass(frozen=True)
class GeoTrackingSettings:
    provider: ProviderCode = field(default_factory=_provider_from_env)
    vertex_project: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_PROJECT", "")
    )
    vertex_location: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_LOCATION", "global")
    )
    vertex_credentials_path: str = field(
        default_factory=lambda: os.getenv(
            "VERTEX_AI_CREDENTIALS_PATH",
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        )
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    )
    gemini_temperature: float = field(
        default_factory=lambda: _float_from_env("GEMINI_TEMPERATURE", "1.0")
    )
    gemini_thinking_level: str = field(
        default_factory=lambda: os.getenv("GEMINI_THINKING_LEVEL", "medium")
    )
    serpapi_api_key: str = field(
        default_factory=lambda: os.getenv("SERPAPI_API_KEY", "")
    )
    serpapi_timeout_seconds: float = field(
        default_factory=lambda: _float_from_env("SERPAPI_TIMEOUT_SECONDS", "30")
    )

    def resolve_vertex_project(self) -> str:
        if self.vertex_project:
            return self.vertex_project
        if not self.vertex_credentials_path:
            return ""
        credentials_path = Path(self.vertex_credentials_path)
        if not credentials_path.exists():
            return ""
        with credentials_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        project_id = payload.get("project_id")
        return project_id if isinstance(project_id, str) else ""
