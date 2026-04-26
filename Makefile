.PHONY: install run test migrate up down logs format

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

test:
	pytest -q

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f app
