# Архитектурные Решения

Эта папка хранит ADR — записи архитектурных решений.

ADR нужно использовать для решений, которые сложно откатить, которые влияют на границы компонентов или задают долгосрочное поведение проекта.

## Формат

Файлы именуются так:

```text
NNNN-short-title.md
```

Рекомендуемые разделы:

```text
# NNNN. Название

Дата: YYYY-MM-DD
Статус: Предложено | Принято | Заменено | Отклонено

## Контекст

## Решение

## Последствия

## Рассмотренные Альтернативы
```

## Записи

- [0001. Исполнительное ядро как Python-библиотека и FastAPI как управляющий сервис](0001-python-library-runtime-fastapi-service.md)
- [0002. Ограничения разработки и локального запуска](0002-development-workflow-and-local-runtime.md)
- [0003. MCP-эмулятор таск-трекера с JSON-состоянием](0003-mcp-task-tracker-emulator.md)
- [0004. SQLite-хранилище через Repository Layer](0004-sqlite-storage-with-repository-layer.md)
- [0005. LiteLLM как provider layer для LLM](0005-litellm-provider-layer.md)
- [0006. Stateless бизнес-поведение с локальной наблюдаемостью](0006-stateless-business-behavior-with-local-observability.md)
