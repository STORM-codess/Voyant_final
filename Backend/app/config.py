from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SECRET_KEY: str = "changethislater"

    # comma-separated list of allowed CORS origins; defaults to local Vite dev
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # require strict DB SSL verification (set true in production with proper certs)
    DB_SSL_VERIFY: bool = False

    # default rate limit applied to most endpoints
    RATE_LIMIT_DEFAULT: str = "120/minute"
    # tighter limit for expensive AI endpoints (protects against runaway cost)
    RATE_LIMIT_AI: str = "10/minute"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()