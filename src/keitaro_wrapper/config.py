from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://wrapper:wrapper@localhost/keitaro_wrapper"
    )
    app_secret_key: SecretStr
    keitaro_base_url: str = "https://tracker.example.invalid"
    keitaro_api_key: SecretStr = SecretStr("")
    keitaro_domain_id: int = 0
    keitaro_group_id: int = 0
    keitaro_traffic_source_id: int = 0
    campaign_name_prefix: str = "test_surname_"
    keitaro_creation_profile: Path | None = None
    http_connect_timeout: float = 5
    http_read_timeout: float = 15
    http_operation_timeout: float = 90
    allowed_hosts: str = "localhost,127.0.0.1,[::1],testserver"

    @field_validator("app_secret_key")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32 or value.get_secret_value().startswith("replace-"):
            raise ValueError("APP_SECRET_KEY must contain at least 32 random characters")
        return value

    @field_validator("keitaro_base_url")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("KEITARO_BASE_URL must be an HTTPS origin without credentials or path")
        return value.rstrip("/")

    @field_validator("keitaro_creation_profile", mode="before")
    @classmethod
    def empty_profile(cls, value: object) -> object:
        return None if value == "" else value
