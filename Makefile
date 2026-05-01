PYTHON ?= .venv/bin/python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
UVICORN ?= .venv/bin/uvicorn

DB_PATH ?= .data/simple-agent.sqlite3
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8010
FRONTEND_PORT ?= 5173

.PHONY: help install run-agent reset-db test check \
	frontend-install frontend-dev frontend-build frontend-preview frontend-test

help:
	@echo "Основные команды:"
	@echo "  make install           Установить backend-зависимости в .venv"
	@echo "  make run-agent        Запустить FastAPI-сервис агента"
	@echo "  make reset-db         Удалить локальную SQLite-базу"
	@echo "  make test             Запустить backend-тесты"
	@echo "  make check            Запустить backend-тесты и сборку frontend"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install Установить npm-зависимости"
	@echo "  make frontend-dev     Запустить Vite dev-server"
	@echo "  make frontend-build   Собрать frontend"
	@echo "  make frontend-preview Запустить preview сборки"
	@echo "  make frontend-test    Запустить frontend-тесты, когда они появятся"
	@echo ""
	@echo "Переменные:"
	@echo "  DB_PATH=$(DB_PATH)"
	@echo "  BACKEND_HOST=$(BACKEND_HOST)"
	@echo "  BACKEND_PORT=$(BACKEND_PORT)"
	@echo "  FRONTEND_PORT=$(FRONTEND_PORT)"

install:
	$(PIP) install -e ".[dev]"

run-agent:
	SIMPLE_AGENT_DB_PATH="$(DB_PATH)" $(UVICORN) simple_agent.service.asgi:app --reload --host "$(BACKEND_HOST)" --port "$(BACKEND_PORT)"

reset-db:
	rm -f "$(DB_PATH)" "$(DB_PATH)-shm" "$(DB_PATH)-wal"

test:
	$(PYTEST) -vv

check: test frontend-build

frontend-install:
	npm --prefix frontend install

frontend-dev:
	npm --prefix frontend run dev -- --host "$(BACKEND_HOST)" --port "$(FRONTEND_PORT)"

frontend-build:
	npm --prefix frontend run build

frontend-preview:
	npm --prefix frontend run preview -- --host "$(BACKEND_HOST)" --port "$(FRONTEND_PORT)"

frontend-test:
	@if npm --prefix frontend run | grep -q '^  test'; then \
		npm --prefix frontend test; \
	else \
		echo "Frontend-тесты пока не настроены (см. TD-009). Сейчас используйте make frontend-build."; \
	fi
