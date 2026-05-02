PYTHON ?= .venv/bin/python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
UVICORN ?= .venv/bin/uvicorn
PYTHONPATH ?= agent:emulator

DB_PATH ?= .data/simple-agent.sqlite3
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8010
FRONTEND_PORT ?= 5173
MCP_HOST ?= 127.0.0.1
MCP_PORT ?= 8020
MCP_STATE_FILE ?= datasets/task_tracker/simple-task.json
MCP_SNAPSHOT_FILE ?= .data/task-tracker-snapshot.json
AGENT_EMAIL ?= agent@example.com
TASK_TRACKER_MCP_URL ?= http://$(MCP_HOST):$(MCP_PORT)/mcp
TASK_TRACKER_MCP_TIMEOUT_SECONDS ?= 30
WORKSPACE_ROOT ?= .data/workspaces
TOOL_COMMAND_TIMEOUT_SECONDS ?= 10
TOOL_OUTPUT_MAX_BYTES ?= 32000
TOOL_FILE_READ_MAX_BYTES ?= 128000
AGENT_RUNTIME_MODE ?= primitive
LLM_BASE_URL ?=
LLM_API_KEY ?=
LLM_MODEL ?= openai/gpt-5-mini
LLM_MAX_STEPS ?= 6
LLM_TIMEOUT_SECONDS ?= 60
NPM_CONFIG_CACHE ?= .data/npm-cache

.PHONY: help install run-agent reset-db test check generate-mcp-docs \
	frontend-install frontend-dev frontend-build frontend-preview frontend-test \
	run-task-tracker reset-task-tracker

help:
	@echo "Основные команды:"
	@echo "  make install           Установить backend-зависимости в .venv"
	@echo "  make run-agent        Запустить FastAPI-сервис агента"
	@echo "  make reset-db         Удалить локальную SQLite-базу"
	@echo "  make run-task-tracker Запустить MCP-эмулятор таск-трекера"
	@echo "  make reset-task-tracker Удалить snapshot MCP-эмулятора"
	@echo "  make generate-mcp-docs Сгенерировать документацию MCP tools"
	@echo "  make test             Запустить backend-тесты"
	@echo "  make check            Запустить backend-тесты и сборку frontend"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install Установить npm-зависимости"
	@echo "  make frontend-dev     Запустить Vite dev-server"
	@echo "  make frontend-build   Собрать frontend"
	@echo "  make frontend-preview Запустить preview сборки"
	@echo "  make frontend-test    Запустить frontend-тесты"
	@echo ""
	@echo "Переменные:"
	@echo "  DB_PATH=$(DB_PATH)"
	@echo "  BACKEND_HOST=$(BACKEND_HOST)"
	@echo "  BACKEND_PORT=$(BACKEND_PORT)"
	@echo "  FRONTEND_PORT=$(FRONTEND_PORT)"
	@echo "  MCP_PORT=$(MCP_PORT)"
	@echo "  MCP_STATE_FILE=$(MCP_STATE_FILE)"
	@echo "  MCP_SNAPSHOT_FILE=$(MCP_SNAPSHOT_FILE)"
	@echo "  AGENT_EMAIL=$(AGENT_EMAIL)"
	@echo "  TASK_TRACKER_MCP_URL=$(TASK_TRACKER_MCP_URL)"
	@echo "  WORKSPACE_ROOT=$(WORKSPACE_ROOT)"
	@echo "  AGENT_RUNTIME_MODE=$(AGENT_RUNTIME_MODE)"
	@echo "  LLM_MODEL=$(LLM_MODEL)"
	@echo "  NPM_CONFIG_CACHE=$(NPM_CONFIG_CACHE)"
	@echo "  PYTHONPATH=$(PYTHONPATH)"

install:
	$(PIP) install -e ".[dev]"

run-agent:
	PYTHONPATH="$(PYTHONPATH)" SIMPLE_AGENT_DB_PATH="$(DB_PATH)" AGENT_EMAIL="$(AGENT_EMAIL)" TASK_TRACKER_MCP_URL="$(TASK_TRACKER_MCP_URL)" TASK_TRACKER_MCP_TIMEOUT_SECONDS="$(TASK_TRACKER_MCP_TIMEOUT_SECONDS)" WORKSPACE_ROOT="$(WORKSPACE_ROOT)" TOOL_COMMAND_TIMEOUT_SECONDS="$(TOOL_COMMAND_TIMEOUT_SECONDS)" TOOL_OUTPUT_MAX_BYTES="$(TOOL_OUTPUT_MAX_BYTES)" TOOL_FILE_READ_MAX_BYTES="$(TOOL_FILE_READ_MAX_BYTES)" AGENT_RUNTIME_MODE="$(AGENT_RUNTIME_MODE)" LLM_BASE_URL="$(LLM_BASE_URL)" LLM_API_KEY="$(LLM_API_KEY)" LLM_MODEL="$(LLM_MODEL)" LLM_MAX_STEPS="$(LLM_MAX_STEPS)" LLM_TIMEOUT_SECONDS="$(LLM_TIMEOUT_SECONDS)" $(UVICORN) simple_agent.service.asgi:app --reload --host "$(BACKEND_HOST)" --port "$(BACKEND_PORT)"

reset-db:
	rm -f "$(DB_PATH)" "$(DB_PATH)-shm" "$(DB_PATH)-wal"

run-task-tracker:
	PYTHONPATH="emulator" $(PYTHON) -m task_tracker_emulator.main --state-file "$(MCP_STATE_FILE)" --snapshot-file "$(MCP_SNAPSHOT_FILE)" --host "$(MCP_HOST)" --port "$(MCP_PORT)"

reset-task-tracker:
	rm -f "$(MCP_SNAPSHOT_FILE)"

generate-mcp-docs:
	PYTHONPATH="emulator" $(PYTHON) -m task_tracker_emulator.tool_docs --state-file "$(MCP_STATE_FILE)" --output docs/mcp-task-tracker-tools.md

test:
	PYTHONPATH="$(PYTHONPATH)" $(PYTEST) -vv

check: test frontend-build

frontend-install:
	NPM_CONFIG_CACHE="$(NPM_CONFIG_CACHE)" npm --prefix frontend install

frontend-dev:
	NPM_CONFIG_CACHE="$(NPM_CONFIG_CACHE)" npm --prefix frontend run dev -- --host "$(BACKEND_HOST)" --port "$(FRONTEND_PORT)"

frontend-build:
	NPM_CONFIG_CACHE="$(NPM_CONFIG_CACHE)" npm --prefix frontend run build

frontend-preview:
	NPM_CONFIG_CACHE="$(NPM_CONFIG_CACHE)" npm --prefix frontend run preview -- --host "$(BACKEND_HOST)" --port "$(FRONTEND_PORT)"

frontend-test:
	NPM_CONFIG_CACHE="$(NPM_CONFIG_CACHE)" npm --prefix frontend test
