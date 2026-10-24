import logging
import os
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import analytics, applications, auth, bank, company, news, products
from .seed import seed_database

logger = logging.getLogger("credit.pipeline")

app = FastAPI(
    title=settings.app_name,
    description=(
        "Прототип цифрового кредитного конвейера для малого и микробизнеса: "
        "клиентский кабинет, скоринг, ручное рассмотрение и моки внешних источников."
    ),
    version="1.2.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(auth.router, prefix=api)
app.include_router(products.router, prefix=api)
app.include_router(applications.router, prefix=api)
app.include_router(bank.router, prefix=api)
app.include_router(news.router, prefix=api)
app.include_router(analytics.router, prefix=api)
app.include_router(company.router, prefix=api)


@app.get("/api/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.2.0",
        # Видно, что показан ускоренный демо-профиль, а не «мгновенный кредит».
        "timing_profile": settings.timing_profile,
        "auto_branch_seconds": round(settings.auto_branch_seconds * settings.demo_delay_scale, 1),
    }


def recover_stuck_applications(older_than_minutes: int = 10) -> int:
    """Возврат в работу заявок, застрявших в промежуточных статусах.

    Причина застревания — перезапуск сервиса или падение воркера в момент прогона:
    фоновой задачи уже нет, и без этого шага заявка молча висела бы в «Скоринге».
    Такие заявки передаются андеррайтеру, а не теряются.
    """
    from .models import Application
    from .services.pipeline import AUTO_STATUSES, hand_over_to_manual_review

    db = SessionLocal()
    recovered = 0
    try:
        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        stuck = (db.query(Application)
                 .filter(Application.status.in_(tuple(AUTO_STATUSES)),
                         Application.updated_at < threshold)
                 .all())
        for app in stuck:
            hand_over_to_manual_review(
                db, app,
                "Обработка была прервана (перезапуск сервиса). Заявка возвращена в очередь, "
                "чтобы клиент не ждал повторного автоматического прогона.",
                title="Обработка прервана — заявка у андеррайтера",
            )
            recovered += 1
        if recovered:
            logger.warning("Восстановлено заявок после перезапуска: %s", recovered)
    except Exception:  # pragma: no cover
        db.rollback()
        logger.exception("Не удалось восстановить застрявшие заявки")
    finally:
        db.close()
    return recovered


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_start:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    recover_stuck_applications()


# --------------------------------------------------------------------- frontend
if settings.static_dir and os.path.isdir(settings.static_dir):
    assets_dir = os.path.join(settings.static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        index = os.path.join(settings.static_dir, "index.html")
        candidate = os.path.join(settings.static_dir, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(index)
