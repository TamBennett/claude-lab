from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

BASE_DIR = Path(__file__).resolve().parent  # backend/
REPO_ROOT = BASE_DIR.parent  # claude-lab/


class AppEnv(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(
#         env_file=(
#             REPO_ROOT / ".env",
#             BASE_DIR / ".env",
#         ),  # root first, backend overrides
#         env_file_encoding="utf-8",
#         extra="ignore",
#     )
#     anthropic_api_key: str  # comes from root .env
#     app_env: str = "development"
#     model: str = "claude-haiku-4-5-20251001"
#     cors_origins: str = "http://localhost:5173"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # the following is declaring a default for each variable. Note; the anthropic_api_key
    # has no default defined so if the ANTHROPIC_API_KEY is not set in the environment
    # it will error out when used. Also, all of the snake_case attribute map to the
    # UPPER_SNAKE env variable
    anthropic_api_key: str
    app_env: AppEnv = AppEnv.development
    model: str = "claude-haiku-4-5-20251001"
    cors_origins: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.production


@lru_cache
def get_settings() -> Settings:
    return Settings()
