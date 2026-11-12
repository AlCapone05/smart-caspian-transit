from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db_url import to_async_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Smart Caspian Transit API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./sct.db"
    api_key: str = "demo-key"
    data_quality: str = "synthetic_demo"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175,"
        "http://localhost:3000"
    )

    # Assistant LLM: local | auto | deepseek | openai
    assistant_provider: str = "deepseek"
    assistant_model: str = ""
    # DeepSeek (OpenAI-compatible)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    # GigaChat (Sber)
    gigachat_credentials: str = ""  # base64(client_id:client_secret) or raw "id:secret"
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"
    gigachat_auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_api_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    # OpenAI fallback
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        return to_async_url(str(v))


@lru_cache
def get_settings() -> Settings:
    return Settings()
