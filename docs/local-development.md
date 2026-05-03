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

## Песочница Для Ручных И Live Прогонов

Для ручной проверки агента не используйте репозиторий `simple_agent` как `PROJECT_REPO_ROOT`.
Вместо этого используйте отдельную песочницу, которая пересоздается из seed-проекта.

Подготовить чистую песочницу:

```bash
make sandbox-reset
```

Команда создает:

- `/tmp/simple-agent-sandbox/repo` — отдельный git-репозиторий для задач;
- `/tmp/simple-agent-sandbox/workspaces` — каталог worktree и run;
- initial commit на ветке `main`.

Запустить MCP-эмулятор для песочницы:

```bash
make sandbox-run-tracker
```

Запустить backend агента на песочнице:

```bash
make sandbox-run-agent
```

Запустить backend песочницы с локальным LM Studio:

```bash
make sandbox-run-agent-llm-local
```

Полностью удалить песочницу:

```bash
make sandbox-clean
```

По умолчанию песочница живет в `/tmp/simple-agent-sandbox`. При необходимости корень можно переопределить:

```bash
make sandbox-reset SANDBOX_ROOT=/tmp/simple-agent-sandbox-2
make sandbox-run-agent SANDBOX_ROOT=/tmp/simple-agent-sandbox-2
```

Seed-проект для песочницы хранится в `datasets/sandbox_repos/demo_python_app`.

Настройки агента для подключения к MCP-трекеру:

```bash
make run-agent \
  AGENT_EMAIL=agent@example.com \
  TASK_TRACKER_MCP_URL=http://127.0.0.1:8020/mcp \
  TASK_TRACKER_MCP_TIMEOUT_SECONDS=30 \
  PROJECT_REPO_ROOT=/tmp/simple-agent-sandbox/repo \
  WORKSPACE_ROOT=/tmp/simple-agent-sandbox/workspaces \
  TOOL_COMMAND_TIMEOUT_SECONDS=10
```

`PROJECT_REPO_ROOT` указывает на локальный git-репозиторий проекта. Если переменная задана, агент подготавливает каталог `repo/` внутри workspace как `git worktree` рабочей ветки задачи. Если переменная не задана, используется обычный локальный каталог `repo/`, что удобно для изолированных unit-тестов.

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

Для локального LM Studio есть отдельная цель:

```bash
make run-agent-llm-local
```

Эта цель запускает backend с локальной LLM-конфигурацией, но без обязательной привязки к sandbox-репозиторию. Для ручного smoke на отдельном тестовом репозитории используйте `make sandbox-run-agent-llm-local`.

Она запускает backend в `llm`-режиме с:

- `LLM_BASE_URL=http://127.0.0.1:1234/v1`
- `LLM_API_KEY=lm-studio`
- `LLM_MODEL=openai/qwen3.5-2b`
- `NO_PROXY=localhost,127.0.0.1`
- `PROJECT_REPO_ROOT=/tmp/simple-agent-sandbox/repo`

При необходимости можно переопределить модель:

```bash
make run-agent-llm-local LLM_MODEL=openai/gemma-4-e4b
```

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

Если `PROJECT_REPO_ROOT` задан, после старта run в observability будет заполнен `branch_name`, а workspace получит ветку вида `PROJECT-123-agent`.

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
Для запуска backend через LiteLLM и локальный LM Studio задавайте `NO_PROXY=localhost,127.0.0.1`. Цель `make run-agent-llm-local` делает это автоматически.

## MCP-Эмулятор Таск-Трекера

Запустить эмулятор с простым seed-сценарием:

```bash
make run-task-tracker
```

Для live-теста с локальным LM Studio можно использовать отдельную цель с выделенным snapshot:

```bash
make run-task-tracker-llm-local
```

Для ручных и live smoke-прогонов предпочтительнее использовать `make sandbox-run-tracker`, чтобы snapshot состояния задач лежал рядом с песочницей, а не в `.data` текущего репозитория.

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
