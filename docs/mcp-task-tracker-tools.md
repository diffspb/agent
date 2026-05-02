# MCP Tools Таск-Трекера

Этот документ сгенерирован из зарегистрированных tools MCP-эмулятора.

Источник генерации: `emulator/task_tracker_emulator/server.py`.

Команда обновления:

```bash
make generate-mcp-docs
```

## Сводка

| Tool | Назначение |
| --- | --- |
| `workflow_get` | Получить фиксированный workflow таск-трекера. |
| `tasks_get` | Получить задачу по идентификатору вида PROJECT-123. |
| `tasks_list` | Получить задачи по статусу и исполнителю email. |
| `tasks_update` | Изменить задачу, включая статус. |
| `comments_add` | Добавить комментарий к задаче. |
| `comments_list` | Получить комментарии задачи. |

## `workflow_get`

Получить фиксированный workflow таск-трекера.

### Примечания

- Используется агентом перед выбором или выполнением задачи, чтобы узнать доступные статусы.

### Входные Параметры

Параметры не требуются.

### Пример Вызова

```json
{
  "arguments": {},
  "name": "workflow_get"
}
```

### JSON Schema Входа

```json
{
  "properties": {},
  "title": "workflow_getArguments",
  "type": "object"
}
```

### JSON Schema Ответа

```json
{
  "additionalProperties": true,
  "title": "workflow_getDictOutput",
  "type": "object"
}
```

## `tasks_get`

Получить задачу по идентификатору вида PROJECT-123.

### Примечания

- Возвращает полную карточку задачи, включая описание, связи, комментарии и metadata.
- Если задача не найдена, tool возвращает ошибку MCP.

### Входные Параметры

| Параметр | Обязательный | Тип | Значение по умолчанию |
| --- | --- | --- | --- |
| `id` | да | `string` | `-` |

### Пример Вызова

```json
{
  "arguments": {
    "id": "PROJECT-123"
  },
  "name": "tasks_get"
}
```

### JSON Schema Входа

```json
{
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "title": "tasks_getArguments",
  "type": "object"
}
```

### JSON Schema Ответа

```json
{
  "additionalProperties": true,
  "title": "tasks_getDictOutput",
  "type": "object"
}
```

## `tasks_list`

Получить задачи по статусу и исполнителю email.

### Примечания

- Оба фильтра опциональны. Без фильтров возвращает задачи проекта.
- Для авто-выбора агент использует `status=Open` и `assignee_email=<email агента>`.

### Входные Параметры

| Параметр | Обязательный | Тип | Значение по умолчанию |
| --- | --- | --- | --- |
| `status` | нет | `string \| null` | `null` |
| `assignee_email` | нет | `string \| null` | `null` |

### Пример Вызова

```json
{
  "arguments": {
    "assignee_email": "agent@example.com",
    "status": "Open"
  },
  "name": "tasks_list"
}
```

### JSON Schema Входа

```json
{
  "properties": {
    "assignee_email": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Assignee Email"
    },
    "status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Status"
    }
  },
  "title": "tasks_listArguments",
  "type": "object"
}
```

### JSON Schema Ответа

```json
{
  "properties": {
    "result": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "title": "Result",
      "type": "array"
    }
  },
  "required": [
    "result"
  ],
  "title": "tasks_listOutput",
  "type": "object"
}
```

## `tasks_update`

Изменить задачу, включая статус.

### Примечания

- Patch может изменять только поля задачи, разрешенные эмулятором.
- Для смены статуса передайте `patch.status`.

### Входные Параметры

| Параметр | Обязательный | Тип | Значение по умолчанию |
| --- | --- | --- | --- |
| `id` | да | `string` | `-` |
| `patch` | да | `object` | `-` |

### Пример Вызова

```json
{
  "arguments": {
    "id": "PROJECT-123",
    "patch": {
      "status": "InProgress"
    }
  },
  "name": "tasks_update"
}
```

### JSON Schema Входа

```json
{
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "patch": {
      "additionalProperties": true,
      "title": "Patch",
      "type": "object"
    }
  },
  "required": [
    "id",
    "patch"
  ],
  "title": "tasks_updateArguments",
  "type": "object"
}
```

### JSON Schema Ответа

```json
{
  "additionalProperties": true,
  "title": "tasks_updateDictOutput",
  "type": "object"
}
```

## `comments_add`

Добавить комментарий к задаче.

### Примечания

- Комментарии являются основным каналом видимого прогресса, вопросов и итогов работы агента.

### Входные Параметры

| Параметр | Обязательный | Тип | Значение по умолчанию |
| --- | --- | --- | --- |
| `task_id` | да | `string` | `-` |
| `author_email` | да | `string` | `-` |
| `body` | да | `string` | `-` |

### Пример Вызова

```json
{
  "arguments": {
    "author_email": "agent@example.com",
    "body": "Начинаю работу.",
    "task_id": "PROJECT-123"
  },
  "name": "comments_add"
}
```

### JSON Schema Входа

```json
{
  "properties": {
    "author_email": {
      "title": "Author Email",
      "type": "string"
    },
    "body": {
      "title": "Body",
      "type": "string"
    },
    "task_id": {
      "title": "Task Id",
      "type": "string"
    }
  },
  "required": [
    "task_id",
    "author_email",
    "body"
  ],
  "title": "comments_addArguments",
  "type": "object"
}
```

### JSON Schema Ответа

```json
{
  "additionalProperties": true,
  "title": "comments_addDictOutput",
  "type": "object"
}
```

## `comments_list`

Получить комментарии задачи.

### Примечания

- Используется для чтения обсуждения задачи перед продолжением работы.

### Входные Параметры

| Параметр | Обязательный | Тип | Значение по умолчанию |
| --- | --- | --- | --- |
| `task_id` | да | `string` | `-` |

### Пример Вызова

```json
{
  "arguments": {
    "task_id": "PROJECT-123"
  },
  "name": "comments_list"
}
```

### JSON Schema Входа

```json
{
  "properties": {
    "task_id": {
      "title": "Task Id",
      "type": "string"
    }
  },
  "required": [
    "task_id"
  ],
  "title": "comments_listArguments",
  "type": "object"
}
```

### JSON Schema Ответа

```json
{
  "properties": {
    "result": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "title": "Result",
      "type": "array"
    }
  },
  "required": [
    "result"
  ],
  "title": "comments_listOutput",
  "type": "object"
}
```
