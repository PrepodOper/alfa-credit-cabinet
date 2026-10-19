# Версия для проверки

- **Тег:** `v1.0.0`
- **Commit hash на момент сдачи:** `95dbff5`
- **Ветка:** `master`
- **Дата фиксации:** 19.10.2026

## Состав поставки

| Артефакт | Путь |
|---|---|
| Backend (FastAPI) | `backend/` |
| Frontend (React + Vite) | `frontend/` |
| Docker-конфигурация | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf` |
| Документация | `docs/` |
| OpenAPI | `docs/openapi.json` |
| Коллекция запросов | `docs/postman_collection.json` |
| Презентация | `docs/alfa-credit-cabinet-pitch.pptx` |
| Сторонние компоненты | `THIRD_PARTY_NOTICES.md` |
| Тестовые данные и демо-сценарий | `backend/app/seed.py`, `tools/seed_demo.py` |

## Проверка за 3 команды

```bash
cp .env.example .env
docker compose up --build
# UI: http://localhost:8080 · API/Swagger: http://localhost:8000/docs
```

Тесты: `make test` → `13 passed`.

## История коммитов

Репозиторий содержит осмысленную историю из 12 коммитов: каркас → модель данных → моки →
скоринг → конвейер → API → тесты → фронтенд клиента → фронтенд бэкофиса → документация →
Docker/CI → презентация.
