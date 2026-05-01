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
make run-agent
```

По умолчанию backend использует SQLite-файл `.data/simple-agent.sqlite3`. Для отдельного файла можно задать:

```bash
make run-agent DB_PATH=.data/dev.sqlite3
```

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

В WSL или окружениях с proxy важно обходить proxy для локальных адресов. Для `curl` используйте `--noproxy "*"`.

## Тесты

Тесты запускаются только из активированного виртуального окружения:

```bash
make test
```

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
