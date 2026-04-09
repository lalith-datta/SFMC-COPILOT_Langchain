"""
Application configuration using pydantic-settings.
Loads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Server ----
    server_port: int = 8080
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    # ---- Gemini ----
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # ---- SFMC ----
    sfmc_client_id: str = ""
    sfmc_client_secret: str = ""
    sfmc_auth_base_uri: str = ""
    sfmc_rest_base_uri: str = ""

    # ---- Figma ----
    figma_access_token: str = ""


settings = Settings()
