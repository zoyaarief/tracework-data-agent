.PHONY: install dev api web test lint build

install:
	python -m pip install -e ".[dev]"
	npm ci

dev:
	@echo "Run 'make api' and 'make web' in separate terminals."

api:
	uvicorn backend.app.main:app --reload --port 8000

web:
	npm run dev

test:
	pytest

lint:
	ruff check backend
	npm run lint

build:
	npm run build
