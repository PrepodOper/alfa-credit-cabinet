import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    if db_path not in {"", ":memory:"}:
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # Каталог постоянного хранилища может быть недоступен (например, на PaaS
            # смонтирован только для чтения или принадлежит другому пользователю).
            # Не падаем на старте: приложение поднимется, а причина будет видна в логах
            # и в ответах API, вместо бесконечного рестарта контейнера.
            print(f"[warn] Не удалось создать каталог для SQLite ({db_path}): {exc}", flush=True)
            print("[warn] Проверьте переменную DATABASE_URL и права на каталог постоянного хранилища.", flush=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
