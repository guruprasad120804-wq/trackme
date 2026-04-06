from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://trackme:changeme_db_password@localhost:5433/trackme"

    # Redis (optional — app works without it)
    redis_url: str = ""

    # Security
    secret_key: str = "changeme_secret_key_min_32_chars_long"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 30

    # URLs
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # WhatsApp
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_webhook_secret: str = ""

    # AI
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_primary_model: str = "qwen/qwen3.6-plus:free"
    openrouter_fallback_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_backup_model: str = "nvidia/nemotron-3-nano-30b-a3b:free"

    # MF Aggregator
    mf_api_key: str = ""
    mf_base_url: str = "https://api.example.com/mf"

    # AMFI
    amfi_nav_url: str = "https://www.amfiindia.com/spages/NAVAll.txt"

    # CORS — comma-separated string, split in code
    cors_origins_str: str = "http://localhost:3000,http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins_str.split(",") if o.strip()]
        # Always include frontend_url
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
