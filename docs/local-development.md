# Локальный Запуск

Этот документ описывает локальный запуск без Docker для разработки.

## Python Окружение

Создать виртуальное окружение:

```bash
python3 -m virtualenv .venv
```

Активировать окружение:

```bash
vactivate
```

Если алиас `vactivate` недоступен, можно использовать:

```bash
source .venv/bin/activate
```

Установить зависимости:

```bash
python -m pip install -e ".[dev]"
```

Python-код разнесен по двум пакетным корням:

- `agent/simple_agent` — библиотека и FastAPI-сервис агента;
- `emulator/task_tracker_emulator` — MCP-эмулятор таск-трекера.

`pyproject.toml` устанавливает оба пакета. Makefile дополнительно задает `PYTHONPATH=agent:emulator` для локального запуска без лишней настройки окружения.

## Backend

Запустить API:

```bash
make run-agent
```

Backend по умолчанию слушает `http://127.0.0.1:8010`.

По умолчанию backend использует SQLite-файл `.data/simple-agent.sqlite3`. Для отдельного файла можно задать:

```bash
make run-agent DB_PATH=.data/dev.sqlite3
```

Настройки агента для подключения к MCP-трекеру:

```bash
make run-agent \
  AGENT_EMAIL=agent@example.com \
  TASK_TRACKER_MCP_URL=http://127.0.0.1:8020/mcp \
  TASK_TRACKER_MCP_TIMEOUT_SECONDS=30 \
  WORKSPACE_ROOT=.data/workspaces \
  TOOL_COMMAND_TIMEOUT_SECONDS=10
```

Режим runtime выбирается через `AGENT_RUNTIME_MODE`:

- `primitive` — режим по умолчанию, детерминированный runtime без LLM;
- `llm_stub` — LLM-цикл со stub-клиентом без реального токена;
- `llm` — LLM-цикл через LiteLLM.

Пример запуска stub LLM-режима:

```bash
make run-agent AGENT_RUNTIME_MODE=llm_stub
```

Пример запуска через LiteLLM:

```bash
make run-agent \
  AGENT_RUNTIME_MODE=llm \
  LLM_MODEL=openai/gpt-5-mini \
  LLM_API_KEY=... \
  LLM_BASE_URL=...
```

Если провайдер LiteLLM не требует `LLM_BASE_URL`, переменную можно не задавать.

ASGI-приложение для прямого запуска uvicorn находится в `simple_agent.service.asgi:app`. При прямом запуске из корня репозитория задайте `PYTHONPATH=agent:emulator`.

Сбросить локальную базу:

```bash
make reset-db
```

Проверить healthcheck:

```bash
curl --noproxy "*" http://127.0.0.1:8010/health
```

Проверить endpoints хранилища и наблюдаемости:

```bash
curl --noproxy "*" http://127.0.0.1:8010/api/ticks
curl --noproxy "*" http://127.0.0.1:8010/api/runs
curl --noproxy "*" http://127.0.0.1:8010/api/stats
```

Запустить ручной tick выбора задачи:

```bash
curl --noproxy "*" \
  -X POST http://127.0.0.1:8010/api/agent/tick \
  -H 'Content-Type: application/json' \
  -d '{"source":"manual"}'
```

Webhook-вход таск-трекера:

```bash
curl --noproxy "*" \
  -X POST http://127.0.0.1:8010/api/webhooks/task-tracker \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"PROJECT-1","event":"task.updated"}'
```

Запустить выбранный run текущим runtime:

```bash
curl --noproxy "*" \
  -X POST http://127.0.0.1:8010/api/runs/1/start
```

Отменить queued или running run:

```bash
curl --noproxy "*" \
  -X POST http://127.0.0.1:8010/api/runs/1/cancel
```

Получить события run:

```bash
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/events
```

Получить вызовы tools для run:

```bash
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/tool-calls
```

Получить артефакты run:

```bash
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/artifacts
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/artifacts/final.diff
```

В WSL или окружениях с proxy важно обходить proxy для локальных адресов. Для `curl` используйте `--noproxy "*"`.
MCP-клиент агента в сервисе отключает использование proxy-переменных для своих HTTP-вызовов к MCP endpoint.

## MCP-Эмулятор Таск-Трекера

Запустить эмулятор с простым seed-сценарием:

```bash
make run-task-tracker
```

По умолчанию эмулятор использует:

```text
state: datasets/task_tracker/simple-task.json
snapshot: .data/task-tracker-snapshot.json
endpoint: http://127.0.0.1:8020/mcp
```

Запустить другой сценарий:

```bash
make run-task-tracker MCP_STATE_FILE=datasets/task_tracker/blocked-task.json
```

Сбросить snapshot:

```bash
make reset-task-tracker
```

## Тесты

Тесты запускаются только из активированного виртуального окружения:

```bash
make test
```

Frontend-тесты запускаются через Vitest:

```bash
make frontend-test
```

Ручной smoke-сценарий описан в [ручном smoke-тесте](manual-smoke.md).

## Frontend

Установить зависимости:

```bash
make frontend-install
```

Запустить Vite dev-server:

```bash
make frontend-dev
```

Собрать frontend:

```bash
make frontend-build
```

Frontend будет доступен на `http://127.0.0.1:5173`.

Backend по умолчанию разрешает CORS для локальных frontend-origin вида `http://127.0.0.1:<порт>` и `http://localhost:<порт>`. Если нужно переопределить правило, используйте:

```bash
export SIMPLE_AGENT_CORS_ALLOW_ORIGIN_REGEX='^http://127\.0\.0\.1:5173$'
```
