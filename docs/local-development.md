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

## Backend

Запустить API:

```bash
uvicorn simple_agent.service.app:app --reload --host 127.0.0.1 --port 8000
```

По умолчанию backend использует SQLite-файл `.data/simple-agent.sqlite3`. Для отдельного файла можно задать:

```bash
export SIMPLE_AGENT_DB_PATH=.data/dev.sqlite3
```

Проверить healthcheck:

```bash
curl --noproxy "*" http://127.0.0.1:8000/health
```

Проверить endpoints хранилища и наблюдаемости:

```bash
curl --noproxy "*" http://127.0.0.1:8000/api/tasks
curl --noproxy "*" http://127.0.0.1:8000/api/runs
curl --noproxy "*" http://127.0.0.1:8000/api/stats
```

В WSL или окружениях с proxy важно обходить proxy для локальных адресов. Для `curl` используйте `--noproxy "*"`.

## Тесты

Тесты запускаются только из активированного виртуального окружения:

```bash
pytest
```

## Frontend

Установить зависимости:

```bash
cd frontend
npm install
```

Запустить Vite dev-server:

```bash
npm run dev
```

Frontend будет доступен на `http://127.0.0.1:5173`.
