import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = "Умный кредитный кабинет предпринимателя"
    api_prefix: str = "/api"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/credit_cabinet.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "alfa-hack-2026-dev-secret-change-in-prod")
    jwt_algorithm: str = "HS256"
    access_token_ttl_hours: int = int(os.getenv("ACCESS_TOKEN_TTL_HOURS", "12"))
    # Масштаб искусственных задержек конвейера для наглядной демонстрации (0 — без задержек).
    demo_delay_scale: float = float(os.getenv("DEMO_DELAY_SCALE", "1.0"))
    offer_ttl_hours: int = int(os.getenv("OFFER_TTL_HOURS", "168"))
    static_dir: str = os.getenv("STATIC_DIR", "")
    seed_on_start: bool = _bool("SEED_ON_START", True)
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")


settings = Settings()
