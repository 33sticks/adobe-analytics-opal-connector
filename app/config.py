"""Environment configuration and settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    adobe_client_id: str
    adobe_client_secret: str
    adobe_org_id: str
    adobe_company_id: str = "exchane5"
    adobe_report_suite_id: str = "33sticksjennwebprops"
    opal_bearer_token: str
    port: int = 8000
    base_url: str = "http://localhost:8000"
    environment: str = "development"
    log_level: str = "info"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
