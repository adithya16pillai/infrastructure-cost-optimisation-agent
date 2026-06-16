.PHONY: dev up down install backend frontend test

# Bring up the whole stack in Docker with mock AWS data.
up:
	docker compose up --build

down:
	docker compose down

# --- Local (non-Docker) development -----------------------------------------

install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
	cd frontend && npm install

# Run the backend API (mock mode).
backend:
	cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# Run the frontend dev server (proxies /api to :8000).
frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/Scripts/python -m pytest
