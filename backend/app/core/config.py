from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "Fintech Payouts API"
    debug: bool = False
    log_level: str = "INFO"
    
    database_url: str
    
    secret_key: str
    access_token_expire_minutes: int = 30
    
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    webhook_secret: str
    webhook_timeout_seconds: int = 300  
    
    rate_limit_per_minute: int = 10
    
    auth_login_rate_limit: int = 5
    auth_login_window_minutes: int = 15
    auth_callback_rate_limit: int = 10
    auth_callback_window_minutes: int = 5
    auth_refresh_rate_limit: int = 20
    auth_refresh_window_minutes: int = 5
    auth_general_rate_limit: int = 30
    auth_general_window_minutes: int = 5
    
    payment_provider_base_url: str = "http://localhost:8000/mock-provider"
    payment_provider_timeout: int = 30

    cors_allow_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    frontend_url: str = "http://localhost:5173"
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("SECRET_KEY is required")
        return v
    
    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, v: str) -> str:
        if not v:
            raise ValueError("WEBHOOK_SECRET is required")
        return v

    model_config = SettingsConfigDict(
        env_file="app/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    
    @field_validator("database_url")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        valid_prefixes = [
            "postgresql+asyncpg://",
            "postgresql://",
            "sqlite+aiosqlite://",
            "sqlite://"
        ]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError("database_url must start with postgresql://, postgresql+asyncpg://, sqlite://, or sqlite+aiosqlite://")
        return v

settings = Settings()