# Сборка Prompt

Этот документ фиксирует, как должен собираться prompt для агентского цикла. Он описывает целевую модель, которую нужно реализовать поэтапно. Документ используется как рабочий черновик для ревью prompt architecture.

## Цель

Prompt не должен быть одной большой строкой с жестко зашитыми правилами проекта. Он должен собираться из независимых слоев, чтобы:

- менять правила проекта без правки runtime;
- подключать разные таск-трекеры и workflow;
- задавать разные типы работ без переписывания Python-кода;
- передавать дополнительные знания о проекте и конкретной задаче;
- ревьюить агентское поведение отдельно от реализации tools и lifecycle.

## Базовая Модель

Сборка prompt состоит из пяти слоев.

### 1. Платформенные Инварианты

Это системный слой, одинаковый для всех проектов.

Содержит:

- границы workspace;
- правила использования tools;
- лимиты и ожидания по проверкам;
- требования по observability;
- правила публикации ошибок и итоговых отчетов;
- запрет на скрытые предположения о состоянии задачи;
- требование сверяться с live-данными через tools.

Этот слой должен быть компактным и максимально стабильным.

### 2. Project Profile

Это главный проектный слой.

Содержит:

- краткое описание проекта и репозитория;
- правила workflow task tracker;
- project-defined modes работы агента;
- git policy;
- testing policy;
- definition of done;
- стиль комментариев в задачах;
- правила эскалации вопросов;
- список обязательных документов и источников контекста.

Project profile должен храниться как конфигурация или документ проекта, который можно отдельно версионировать и ревьюить.

### 3. Task Context

Это слой конкретной задачи.

Содержит:

- карточку задачи;
- тип и статус задачи;
- исполнителя;
- описание;
- связанные задачи;
- комментарии;
- task-specific metadata;
- дополнительные инструкции по текущей задаче.

Task context должен собираться из task tracker и доступных metadata/attachments.

### 4. Knowledge Attachments

Это дополнительный контекст, который не всегда нужен, но может радикально влиять на качество.

Примеры:

- ADR;
- CONTRIBUTING;
- архитектурные заметки;
- project glossary;
- style guides;
- локальные runbooks;
- task-specific reference documents.

Этот слой должен подключаться выборочно. Нельзя без нужды заливать весь репозиторий в prompt.

### 5. Runtime Context

Это краткое состояние конкретного run.

Содержит:

- `external_task_id`;
- текущий workspace root;
- путь к `repo/`;
- branch name;
- доступные tools и их краткие правила;
- ограничения текущего запуска;
- предыдущие важные события текущего run, если они нужны модели.

## Разделение Ответственности

### Что Должно Быть В Runtime

- lifecycle;
- workspace;
- observability;
- лимиты;
- безопасный вызов tools;
- cancellation;
- platform-level error handling.

### Что Должно Быть В Project Profile И Prompt

- правила workflow;
- правила статусов и переводов;
- политика вопросов и комментариев;
- политика git;
- формат итогового отчета;
- expected behavior для разных типов задач;
- набор и смысл project-defined modes.

## Рабочие Режимы

Рабочие режимы не должны быть захардкожены как enum внутри runtime.

Нужна конфигурируемая модель:

- у проекта есть список mode definitions;
- mode может выбираться:
  - по metadata задачи;
  - по типу задачи;
  - по явному project rule;
  - по решению планировщика агента;
- mode меняет инструкции, ожидаемый результат и приоритетные tools.

Примеры mode definitions:

- реализация;
- ревью;
- документация;
- архитектурная проработка;
- исследование;
- операции с задачами.

Но это только примеры. Список должен задаваться проектом.

## Как Я Бы Собирал Prompt

Ниже целевая схема сборки.

### System Message

Один компактный system message с платформенными инвариантами:

- ты работаешь только в пределах workspace;
- состояние задачи проверяй через tools;
- не выдумывай статусы и workflow;
- перед изменением задачи или git-состояния опирайся на project rules;
- оставляй диагностический след через task comments и observability;
- если данных не хватает, сначала дочитывай контекст или задавай вопрос.

### Project Message

Отдельный блок с project profile:

- что это за проект;
- какие есть project modes;
- как понимать workflow;
- когда можно менять статусы;
- как работать с git;
- какие проверки обязательны;
- как оформлять итог.

Этот блок должен быть максимально декларативным. Не narrative, а набор правил и таблиц.

### Task Message

Отдельный блок с текущей задачей:

- id;
- summary;
- description;
- status;
- assignee;
- links;
- comments;
- metadata;
- явно вычисленный suggested mode, если он есть.

### Attachments Message

Краткий список подключенных документов:

- что подключено;
- почему это релевантно;
- ключевые выдержки или summary.

### Runtime Message

Короткий operational block:

- `repo/` — корень репозитория для работы;
- branch name;
- список доступных tools;
- ограничения по времени и шагам;
- что уже известно о текущем run.

## Предлагаемый Формат Конфигурации

На первом этапе я бы не делал сложную DSL. Достаточно структурированной JSON/YAML-модели.

Примерно так:

```yaml
project:
  name: Demo Project
  summary: Короткое описание проекта

workflow:
  statuses:
    - Todo
    - Open
    - InProgress
    - InReview
    - NeedsInfo
    - Done
  transitions: any
  policies:
    blocked_status: NeedsInfo
    review_status: InReview

modes:
  - name: implementation
    when:
      task_types: [task]
    expected_outcome: code_change
    preferred_tools: [read_file, patch_file, run_tests, git_diff]
  - name: documentation
    when:
      labels: [docs]
    expected_outcome: workspace_artifact
    preferred_tools: [read_file, write_file]

git:
  commit_enabled: false
  branch_pattern: "{task_id}-agent"
  require_tests_before_commit: true
  commit_message_template: "{task_id}: {summary}"

comments:
  ask_before_status_change: false
  final_report_sections:
    - summary
    - checks
    - risks
```

## Что Нельзя Делать

- не смешивать project profile с runtime code;
- не тащить весь repo в prompt;
- не хардкодить продуктовые modes в Python enum;
- не считать, что task tracker workflow одинаков для всех проектов;
- не считать git policy универсальной;
- не делать prompt assembly неявной.

## Вопросы Для Ревью

1. Достаточно ли четко разделены platform invariants и project rules?
2. Нужно ли хранить project profile в одном файле или допускать composition из нескольких документов?
3. Нужен ли отдельный mode resolver как кодовый компонент, или достаточно project rule evaluation внутри prompt assembly?
4. Какие части task context должны гарантированно идти в prompt, а какие лучше подгружать on demand?
