.PHONY: help up down logs build test dev-backend dev-frontend seed clean

help:
	@echo "make up             — запустить всё в Docker (UI :8080, API :8000)"
	@echo "make down           — остановить контейнеры"
	@echo "make build          — пересобрать образы"
	@echo "make test           — прогнать автотесты backend"
	@echo "make dev-backend    — локальный backend с авто-перезагрузкой"
	@echo "make dev-frontend   — локальный frontend (Vite, прокси на :8000)"
	@echo "make seed           — наполнить работающий сервер демо-сценарием"
	@echo "make clean          — удалить данные и артефакты сборки"

up:
	docker compose up --build -d
	@echo "Приложение: http://localhost:8080 · API: http://localhost:8000/docs"

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f --tail=100

test:
	cd backend && DEMO_DELAY_SCALE=0 PYTHONPATH=. pytest -q

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

seed:
	python3 tools/seed_demo.py

clean:
	rm -rf backend/data data/*.db frontend/dist
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
