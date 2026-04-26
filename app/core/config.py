from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """настройки приложения"""

    app_name: str = "promo service"
    api_prefix: str = "/api"
    secret_key: str = Field(
        default="misha-privet", alias="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=120, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/promocodes",
        alias="DATABASE_URL",
    )
    moscow_timezone: str = Field(
        default="Europe/Moscow", alias="MOSCOW_TIMEZONE"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """возвращает кэшированные настройки"""

    return Settings()
