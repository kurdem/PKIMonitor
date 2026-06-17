.PHONY: help backend-install backend-run backend-test seed frontend-install frontend-run up down logs

help:
	@echo "PKIMonitor make targets:"
	@echo "  make backend-install   Install backend deps into ./backend/.venv"
	@echo "  make backend-run       Run the API (uvicorn, reload) on :8000"
	@echo "  make backend-test      Run the backend test suite"
	@echo "  make seed              Insert sample certificates & monitors"
	@echo "  make frontend-install  npm install in ./frontend"
	@echo "  make frontend-run      Run the Vite dev server on :5173"
	@echo "  make up / make down    docker compose up -d / down"
	@echo "  make logs              Tail docker compose logs"

backend-install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest

backend-run:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && .venv/bin/python -m pytest

seed:
	cd backend && .venv/bin/python -m scripts.seed

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f
