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
PROJECT_REPO_ROOT ?=
WORKSPACE_ROOT ?= .data/workspaces
SANDBOX_ROOT ?= /tmp/simple-agent-sandbox
SANDBOX_REPO_ROOT ?= $(SANDBOX_ROOT)/repo
SANDBOX_WORKSPACE_ROOT ?= $(SANDBOX_ROOT)/workspaces
SANDBOX_DB_PATH ?= $(SANDBOX_ROOT)/agent.sqlite3
SANDBOX_SNAPSHOT_FILE ?= $(SANDBOX_ROOT)/task-tracker-snapshot.json
SANDBOX_SEED_REPO_DIR ?= datasets/sandbox_repos/demo_python_app
TOOL_COMMAND_TIMEOUT_SECONDS ?= 10
TOOL_OUTPUT_MAX_BYTES ?= 32000
TOOL_FILE_READ_MAX_BYTES ?= 128000
AGENT_RUNTIME_MODE ?= primitive
LLM_BASE_URL ?=
LLM_API_KEY ?=
LLM_MODEL ?= openai/gpt-5-mini
LLM_MAX_STEPS ?= 60
LLM_TIMEOUT_SECONDS ?= 300
NPM_CONFIG_CACHE ?= .data/npm-cache
NO_PROXY ?=

.PHONY: help install run-agent reset-db test check generate-mcp-docs \
	frontend-install frontend-dev frontend-build frontend-preview frontend-test \
	run-task-tracker reset-task-tracker run-agent-llm-local run-task-tracker-llm-local \
	sandbox-reset sandbox-run-tracker sandbox-run-agent sandbox-run-agent-llm-local sandbox-clean

help:
	@echo "Основные команды:"
	@echo "  make install           Установить backend-зависимости в .venv"
	@echo "  make run-agent        Запустить FastAPI-сервис агента"
	@echo "  make run-agent-llm-local Запустить backend с LiteLLM и локальным LM Studio"
	@echo "  make reset-db         Удалить локальную SQLite-базу"
	@echo "  make run-task-tracker Запустить MCP-эмулятор таск-трекера"
	@echo "  make run-task-tracker-llm-local Запустить MCP-эмулятор для live-теста с LM Studio"
	@echo "  make reset-task-tracker Удалить snapshot MCP-эмулятора"
	@echo "  make sandbox-reset    Пересоздать отдельную тестовую песочницу"
	@echo "  make sandbox-run-tracker Запустить MCP-эмулятор для песочницы"
	@echo "  make sandbox-run-agent Запустить backend агента на песочнице"
	@echo "  make sandbox-run-agent-llm-local Запустить backend песочницы с LM Studio"
	@echo "  make sandbox-clean    Полностью удалить песочницу"
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
	@echo "  PROJECT_REPO_ROOT=$(PROJECT_REPO_ROOT)"
	@echo "  WORKSPACE_ROOT=$(WORKSPACE_ROOT)"
	@echo "  SANDBOX_ROOT=$(SANDBOX_ROOT)"
	@echo "  SANDBOX_SEED_REPO_DIR=$(SANDBOX_SEED_REPO_DIR)"
	@echo "  AGENT_RUNTIME_MODE=$(AGENT_RUNTIME_MODE)"
	@echo "  LLM_MODEL=$(LLM_MODEL)"
	@echo "  NO_PROXY=$(NO_PROXY)"
	@echo "  NPM_CONFIG_CACHE=$(NPM_CONFIG_CACHE)"
	@echo "  PYTHONPATH=$(PYTHONPATH)"

install:
	$(PIP) install -e ".[dev]"

run-agent:
	PYTHONPATH_VALUE="$(PYTHONPATH)" UVICORN_BIN="$(UVICORN)" DB_PATH="$(DB_PATH)" AGENT_EMAIL_VALUE="$(AGENT_EMAIL)" TASK_TRACKER_MCP_URL_VALUE="$(TASK_TRACKER_MCP_URL)" TASK_TRACKER_MCP_TIMEOUT_SECONDS_VALUE="$(TASK_TRACKER_MCP_TIMEOUT_SECONDS)" PROJECT_REPO_ROOT_VALUE="$(PROJECT_REPO_ROOT)" WORKSPACE_ROOT_VALUE="$(WORKSPACE_ROOT)" TOOL_COMMAND_TIMEOUT_SECONDS_VALUE="$(TOOL_COMMAND_TIMEOUT_SECONDS)" TOOL_OUTPUT_MAX_BYTES_VALUE="$(TOOL_OUTPUT_MAX_BYTES)" TOOL_FILE_READ_MAX_BYTES_VALUE="$(TOOL_FILE_READ_MAX_BYTES)" AGENT_RUNTIME_MODE_VALUE="$(AGENT_RUNTIME_MODE)" LLM_BASE_URL_VALUE="$(LLM_BASE_URL)" LLM_API_KEY_VALUE="$(LLM_API_KEY)" LLM_MODEL_VALUE="$(LLM_MODEL)" LLM_MAX_STEPS_VALUE="$(LLM_MAX_STEPS)" LLM_TIMEOUT_SECONDS_VALUE="$(LLM_TIMEOUT_SECONDS)" BACKEND_HOST_VALUE="$(BACKEND_HOST)" BACKEND_PORT_VALUE="$(BACKEND_PORT)" NO_PROXY_VALUE="$(NO_PROXY)" ./scripts/run_agent.sh

run-agent-llm-local:
	$(MAKE) run-agent AGENT_RUNTIME_MODE=llm LLM_BASE_URL=http://127.0.0.1:1234/v1 LLM_API_KEY=lm-studio LLM_MODEL=openai/qwen/qwen3.5-9b NO_PROXY=localhost,127.0.0.1

reset-db:
	rm -f "$(DB_PATH)" "$(DB_PATH)-shm" "$(DB_PATH)-wal"

run-task-tracker:
	PYTHONPATH="emulator" $(PYTHON) -m task_tracker_emulator.main --state-file "$(MCP_STATE_FILE)" --snapshot-file "$(MCP_SNAPSHOT_FILE)" --host "$(MCP_HOST)" --port "$(MCP_PORT)"

run-task-tracker-llm-local:
	$(MAKE) run-task-tracker MCP_PORT=$(MCP_PORT) MCP_SNAPSHOT_FILE=.data/task-tracker-live-llm-noproxy.json

sandbox-reset:
	SANDBOX_ROOT="$(SANDBOX_ROOT)" SANDBOX_SEED_REPO_DIR="$(SANDBOX_SEED_REPO_DIR)" AGENT_EMAIL="$(AGENT_EMAIL)" ./scripts/reset_sandbox.sh

sandbox-run-tracker:
	$(MAKE) run-task-tracker MCP_PORT="$(MCP_PORT)" MCP_STATE_FILE="$(MCP_STATE_FILE)" MCP_SNAPSHOT_FILE="$(SANDBOX_SNAPSHOT_FILE)"

sandbox-run-agent:
	$(MAKE) run-agent DB_PATH="$(SANDBOX_DB_PATH)" PROJECT_REPO_ROOT="$(SANDBOX_REPO_ROOT)" WORKSPACE_ROOT="$(SANDBOX_WORKSPACE_ROOT)" TASK_TRACKER_MCP_URL="http://$(MCP_HOST):$(MCP_PORT)/mcp"

sandbox-run-agent-llm-local:
	$(MAKE) sandbox-run-agent AGENT_RUNTIME_MODE=llm LLM_BASE_URL=http://127.0.0.1:1234/v1 LLM_API_KEY=lm-studio LLM_MODEL=openai/qwen/qwen3.5-9b NO_PROXY=localhost,127.0.0.1

sandbox-clean:
	rm -rf "$(SANDBOX_ROOT)"

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
