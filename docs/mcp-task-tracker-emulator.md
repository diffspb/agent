# MCP-Эмулятор Таск-Трекера

Этот документ фиксирует модель примитивного таск-трекера для MVP.

## Назначение

MCP-эмулятор нужен для локальной разработки, интеграционных тестов и демонстрации полного цикла работы агента без подключения к реальному таск-трекеру.

Эмулятор представляет собой таск-трекер одного проекта. Он хранит простые задачи, комментарии, связи между задачами, статусы и мета-информацию.

## Реализация

Эмулятор реализован на официальном Python SDK `mcp[cli]` версии `1.x` через `FastMCP`.
Зависимость подключена в `pyproject.toml` как `mcp[cli]>=1.27,<2.0`.

Локальный endpoint по умолчанию:

```text
http://127.0.0.1:8020/mcp
```

Команда запуска:

```bash
make run-task-tracker
```

Прямой запуск:

```bash
simple-agent-task-tracker \
  --state-file seeds/task_tracker/simple-task.json \
  --snapshot-file .data/task-tracker-snapshot.json \
  --host 127.0.0.1 \
  --port 8020
```

В WSL или окружениях с proxy MCP-клиентам для локального endpoint может понадобиться:

```bash
NO_PROXY="*" no_proxy="*"
```

## Хранение Состояния

- При запуске эмулятор считывает состояние из указанного JSON-файла.
- Во время работы состояние хранится в памяти.
- При изменении состояния эмулятор сбрасывает актуальную копию во временный JSON-файл.
- Эмулятор можно запускать с заранее подготовленных JSON-файлов для разных сценариев.
- Чтобы продолжить с прошлого места, можно передать на вход JSON-файл, созданный предыдущим запуском.

Ожидаемые параметры запуска:

```text
--state-file path/to/scenario.json
--snapshot-file path/to/current-state.json
```

Если `--snapshot-file` не указан, эмулятор создает временный файл самостоятельно и пишет его путь в лог запуска.

## Пользователи

Во всех местах MVP пользователь идентифицируется email-адресом.

Примеры:

```text
author@example.com
agent@example.com
reviewer@example.com
```

## Workflow

Workflow фиксированный:

```text
Todo
Open
InProgress
InReview
NeedsInfo
Done
Cancelled
```

На этапе MVP разрешены любые переходы между статусами.

## Типы Задач

Поддерживаются типы:

```text
epic
task
test
```

## Идентификаторы

Идентификатор задачи имеет формат:

```text
PROJECT-123
```

Где `PROJECT` — ключ проекта, а `123` — номер задачи.

## Модель Задачи

Минимальная задача:

```json
{
  "id": "PROJECT-123",
  "type": "task",
  "status": "Open",
  "title": "Добавить healthcheck",
  "author_email": "author@example.com",
  "assignee_email": "agent@example.com",
  "description": "Нужно добавить GET /health.",
  "links": [
    {
      "type": "part_of_epic",
      "target": "PROJECT-1"
    }
  ],
  "comments": [],
  "metadata": {
    "repository": "local-demo-repo",
    "priority": "normal"
  }
}
```

Поля:

- `id`: идентификатор задачи.
- `type`: тип задачи, один из `epic`, `task`, `test`.
- `status`: статус из фиксированного workflow.
- `title`: краткое название.
- `author_email`: автор задачи.
- `assignee_email`: исполнитель задачи.
- `description`: описание задачи.
- `links`: связи с другими задачами.
- `comments`: комментарии.
- `metadata`: произвольная мета-информация как набор пар ключ-значение.

## Связи Задач

Поддерживаемые типы связей:

```text
part_of_epic
blocks
blocked_by
```

Семантика:

- `part_of_epic`: задача входит в эпик.
- `blocks`: задача блокирует другую задачу.
- `blocked_by`: задача заблокирована другой задачей.

## Комментарии

Минимальная модель комментария:

```json
{
  "id": "comment-1",
  "author_email": "agent@example.com",
  "body": "Начинаю работу.",
  "created_at": "2026-05-01T12:00:00Z"
}
```

## MCP API

Эмулятор должен предоставлять MCP-инструменты.

### `workflow_get`

Возвращает описание workflow:

```json
{
  "statuses": ["Todo", "Open", "InProgress", "InReview", "NeedsInfo", "Done", "Cancelled"],
  "transitions": "any"
}
```

### `tasks_get`

Получает задачу по идентификатору.

Вход:

```json
{
  "id": "PROJECT-123"
}
```

### `tasks_list`

Возвращает список задач с заданным статусом для пользователя.

Вход:

```json
{
  "status": "Open",
  "assignee_email": "agent@example.com"
}
```

Для MVP фильтр по `assignee_email` использует email как единственный идентификатор пользователя.

### `tasks_update`

Изменяет задачу, включая статус.

Вход:

```json
{
  "id": "PROJECT-123",
  "patch": {
    "status": "InProgress",
    "assignee_email": "agent@example.com",
    "metadata": {
      "last_run_id": "run-123"
    }
  }
}
```

### `comments_add`

Добавляет комментарий к задаче.

Вход:

```json
{
  "task_id": "PROJECT-123",
  "author_email": "agent@example.com",
  "body": "Нужны уточнения по ожидаемому поведению."
}
```

### `comments_list`

Возвращает комментарии задачи.

Вход:

```json
{
  "task_id": "PROJECT-123"
}
```

## Минимальные Сценарии Для Seed-Файлов

Подготовленные JSON-файлы:

- `seeds/task_tracker/simple-task.json`: простая задача без связей.
- `seeds/task_tracker/epic-and-task.json`: задача внутри эпика.
- `seeds/task_tracker/blocked-task.json`: задача, заблокированная другой задачей.
- `seeds/task_tracker/test-task.json`: тестовая задача.
- `seeds/task_tracker/needs-info.json`: задача в статусе `NeedsInfo` с комментариями.
