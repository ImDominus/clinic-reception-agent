PY := .venv/Scripts/python.exe

.PHONY: db db-down test run fmt

db:        ## 개발 DB 올리고 schema/001_init.sql 자동 적용
	docker compose up -d db

db-down:
	docker compose down -v

test:
	$(PY) -m pytest -q

run:
	$(PY) -m uvicorn app.main:app --reload

fmt:
	$(PY) -m ruff format app tests seeds && $(PY) -m ruff check --fix app tests seeds
