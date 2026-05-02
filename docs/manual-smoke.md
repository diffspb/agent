# Ручной Smoke-Тест MVP

Этот сценарий нужен для ручной проверки полного локального контура без реального LLM.

## Предусловия

- Python-зависимости установлены в виртуальное окружение.
- Frontend-зависимости установлены через `make frontend-install`.
- Локальные порты `8010`, `8020`, `5173` свободны или переопределены через Makefile-переменные.

## Шаги

1. Сбросить локальное состояние:

```bash
make reset-db
make reset-task-tracker
```

2. Запустить MCP-эмулятор:

```bash
make run-task-tracker
```

3. В другом терминале запустить backend в stub LLM-режиме:

```bash
make run-agent AGENT_RUNTIME_MODE=llm_stub
```

4. В третьем терминале запустить frontend:

```bash
make frontend-dev
```

5. Открыть UI на `http://127.0.0.1:5173`.

6. Нажать `Запустить tick`.

Ожидаемый результат:

- появился новый tick;
- появилась выбранная задача `PROJECT-1`;
- создан run в статусе `queued`;
- в кандидатах видна причина выбора.

7. Нажать `Старт` у выбранного run.

Ожидаемый результат:

- run перешел в `completed`;
- в событиях есть `llm.requested`, `llm.responded`, `artifact.created`, `run.outcome`, `run.completed`;
- в tools есть `write_file`;
- в артефактах есть `final.diff`;
- preview diff содержит `llm-agent-summary.txt`.

8. Проверить задачу в snapshot MCP-эмулятора.

Ожидаемый результат:

- задача переведена в `InReview`, потому что stub LLM изменил файл;
- комментарии содержат старт работы и итоговый отчет с `Diff-артефакт: final.diff`.

## Проверка Через REST

Для WSL и окружений с proxy используйте `--noproxy "*"`:

```bash
curl --noproxy "*" -X POST http://127.0.0.1:8010/api/agent/tick \
  -H 'Content-Type: application/json' \
  -d '{"source":"manual-smoke"}'

curl --noproxy "*" -X POST http://127.0.0.1:8010/api/runs/1/start
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/events
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/tool-calls
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/artifacts
curl --noproxy "*" http://127.0.0.1:8010/api/runs/1/artifacts/final.diff
```
