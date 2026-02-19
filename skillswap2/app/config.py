from typing import Optional
import os

try:
    # Pydantic v2 preferred path.
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _USE_V2_SETTINGS = True
except ImportError:  # pragma: no cover - compatibility fallback
    # Fallback for environments missing pydantic-settings.
    # This lightweight settings loader reads from environment variables.
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        pass

    def _to_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    class BaseSettings:  # type: ignore
        def __init__(self, **kwargs):
            annotations = getattr(self.__class__, "__annotations__", {})
            for field, annotation in annotations.items():
                if field.startswith("_"):
                    continue
                if field in kwargs:
                    raw = kwargs[field]
                elif field in os.environ:
                    raw = os.environ[field]
                elif hasattr(self.__class__, field):
                    raw = getattr(self.__class__, field)
                else:
                    raise ValueError(f"Missing required setting: {field}")

                if annotation is bool:
                    value = _to_bool(raw)
                elif annotation is int:
                    value = int(raw)
                else:
                    value = raw
                setattr(self, field, value)

    SettingsConfigDict = dict  # type: ignore
    _USE_V2_SETTINGS = False

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Email Configuration
    EMAIL_NOTIFICATIONS_ENABLED: bool = True
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 8

    if _USE_V2_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

settings = Settings()
