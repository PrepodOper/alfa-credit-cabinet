import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


# Длительности этапов автоматического конвейера в секундах (до умножения на DEMO_DELAY_SCALE).
# Профиль выбирается переменной окружения TIMING_PROFILE.
TIMING_PROFILES: dict[str, dict[str, float]] = {
    # Демонстрация: этапы сжаты, весь автоматический путь занимает ~2 секунды,
    # чтобы показ на защите не превращался в ожидание. Реальные SLA — в docs/08-timings.md.
    "demo": {"validation": 0.5, "enrichment": 0.4, "scoring": 0.6, "decision": 0.4},
    # Правдоподобные длительности цифрового конвейера: ~3 минуты на автоматическую ветку.
    "realistic": {"validation": 20.0, "enrichment": 90.0, "scoring": 45.0, "decision": 25.0},
}

STAGE_TITLES: dict[str, str] = {
    "validation": "Проверка полноты и корректности данных",
    "enrichment": "Обогащение данными из внешних источников",
    "scoring": "Скоринг и оценка кредитного риска",
    "decision": "Маршрутизация и формирование решения",
}



def _database_url() -> str:
    """URL базы с защитой от типичных ошибок в переменной окружения.

    Пустое значение → локальный файл. Голый путь (`/data/credit_cabinet.db`)
    без схемы SQLAlchemy не принимает и падает на импорте, поэтому схему
    достраиваем сами — приложение поднимается вместо crash-loop контейнера.
    """
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        return "sqlite:///./data/credit_cabinet.db"
    if "://" not in raw:
        path = raw if raw.startswith("/") else os.path.abspath(raw)
        return f"sqlite:///{path}"
    return raw


@dataclass
class Settings:
    app_name: str = "Умный кредитный кабинет предпринимателя"
    api_prefix: str = "/api"
    database_url: str = _database_url()
    jwt_secret: str = os.getenv("JWT_SECRET", "alfa-hack-2026-dev-secret-change-in-prod")
    jwt_algorithm: str = "HS256"
    access_token_ttl_hours: int = int(os.getenv("ACCESS_TOKEN_TTL_HOURS", "12"))
    # Масштаб искусственных задержек конвейера для наглядной демонстрации (0 — без задержек).
    demo_delay_scale: float = float(os.getenv("DEMO_DELAY_SCALE", "1.0"))
    # Профиль времени этапов: demo (ускоренный показ) или realistic (правдоподобные SLA).
    timing_profile: str = os.getenv("TIMING_PROFILE", "demo").strip().lower()
    offer_ttl_hours: int = int(os.getenv("OFFER_TTL_HOURS", "168"))
    static_dir: str = os.getenv("STATIC_DIR", "")
    seed_on_start: bool = _bool("SEED_ON_START", True)
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def stage_seconds(self) -> dict[str, float]:
        """Длительности этапов выбранного профиля (неизвестный профиль → demo)."""
        return TIMING_PROFILES.get(self.timing_profile, TIMING_PROFILES["demo"])

    @property
    def auto_branch_seconds(self) -> float:
        """Суммарная длительность автоматической ветки, секунды (без масштабирования)."""
        return round(sum(self.stage_seconds.values()), 1)


settings = Settings()
