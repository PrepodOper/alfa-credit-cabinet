#!/usr/bin/env bash
# Запуск приложения одним процессом: FastAPI раздаёт собранный фронтенд из frontend/dist.
# Использование: ./start.sh [порт]
set -euo pipefail

cd "$(dirname "$0")"
PORT="${1:-8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "✗ Не найден $PYTHON_BIN. Установите Python 3.11+ (https://www.python.org/downloads/)."
  exit 1
fi

if [ ! -d backend/.venv ]; then
  echo "→ Создаю виртуальное окружение backend/.venv…"
  "$PYTHON_BIN" -m venv backend/.venv
fi

# shellcheck disable=SC1091
source backend/.venv/bin/activate

echo "→ Устанавливаю зависимости…"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r backend/requirements.txt

if [ ! -f frontend/dist/index.html ]; then
  echo "! Собранный фронтенд не найден (frontend/dist)."
  echo "  Соберите его: cd frontend && npm install && npm run build"
  echo "  Либо используйте Docker: docker compose up --build"
  exit 1
fi

mkdir -p backend/data

echo ""
echo "  ✔ Приложение:  http://localhost:${PORT}"
echo "  ✔ API/Swagger: http://localhost:${PORT}/docs"
echo "  ✔ Логин:       ivan@vesna.ru / demo1234"
echo "  (остановить — Ctrl+C)"
echo ""

cd backend
STATIC_DIR="../frontend/dist" exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
