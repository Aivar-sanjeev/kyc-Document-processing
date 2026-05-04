from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_api_key: str = ""
    vision_model: str = "meta/llama-3.2-90b-vision-instruct"
    request_timeout_s: float = 120.0
    max_upload_mb: int = 15
    use_mock_vision: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
