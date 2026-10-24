#!/bin/sh
# Точка входа единого контейнера.
#
# 1. Готовит каталог постоянного хранилища (на PaaS он может быть смонтирован
#    уже root-ом — тогда просто проверяем запись).
# 2. Запускает uvicorn на порту из переменной PORT (Amvera/PaaS передают её сами,
#    локально по умолчанию 8000).
set -e

DB_DIR="$(dirname "${DATABASE_URL#sqlite:///}" 2>/dev/null || echo /data)"
case "$DATABASE_URL" in
  sqlite:///*)
    # sqlite:////data/file.db → /data/file.db
    DB_PATH="${DATABASE_URL#sqlite:///}"
    DB_DIR="$(dirname "$DB_PATH")"
    mkdir -p "$DB_DIR" 2>/dev/null || true
    if [ ! -w "$DB_DIR" ]; then
      echo "[warn] Каталог $DB_DIR недоступен для записи — SQLite не сможет сохранить данные." >&2
      echo "[warn] На Amvera проверьте run.persistenceMount в amvera.yaml." >&2
    fi
    ;;
esac

echo "[start] Порт: ${PORT:-8000}"
echo "[start] Статичный фронтенд: ${STATIC_DIR:-<не задан, API-only>}"
echo "[start] База данных: ${DATABASE_URL}"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
