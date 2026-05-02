from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from task_tracker_emulator.server import load_mcp_server


DEFAULT_STATE_FILE = Path("datasets/task_tracker/simple-task.json")
DEFAULT_OUTPUT_FILE = Path("docs/mcp-task-tracker-tools.md")

TOOL_EXAMPLES: dict[str, dict[str, Any]] = {
    "workflow_get": {},
    "tasks_get": {"id": "PROJECT-123"},
    "tasks_list": {"status": "Open", "assignee_email": "agent@example.com"},
    "tasks_update": {
        "id": "PROJECT-123",
        "patch": {"status": "InProgress"},
    },
    "comments_add": {
        "task_id": "PROJECT-123",
        "author_email": "agent@example.com",
        "body": "Начинаю работу.",
    },
    "comments_list": {"task_id": "PROJECT-123"},
}

TOOL_NOTES: dict[str, list[str]] = {
    "workflow_get": [
        "Используется агентом перед выбором или выполнением задачи, чтобы узнать доступные статусы.",
    ],
    "tasks_get": [
        "Возвращает полную карточку задачи, включая описание, связи, комментарии и metadata.",
        "Если задача не найдена, tool возвращает ошибку MCP.",
    ],
    "tasks_list": [
        "Оба фильтра опциональны. Без фильтров возвращает задачи проекта.",
        "Для авто-выбора агент использует `status=Open` и `assignee_email=<email агента>`.",
    ],
    "tasks_update": [
        "Patch может изменять только поля задачи, разрешенные эмулятором.",
        "Для смены статуса передайте `patch.status`.",
    ],
    "comments_add": [
        "Комментарии являются основным каналом видимого прогресса, вопросов и итогов работы агента.",
    ],
    "comments_list": [
        "Используется для чтения обсуждения задачи перед продолжением работы.",
    ],
}


def generate_tools_markdown(*, state_file: Path = DEFAULT_STATE_FILE) -> str:
    mcp, _store = load_mcp_server(
        state_file=state_file,
        snapshot_file=None,
        host="127.0.0.1",
        port=8020,
    )
    tools_by_name = mcp._tool_manager._tools

    lines = [
        "# MCP Tools Таск-Трекера",
        "",
        "Этот документ сгенерирован из зарегистрированных tools MCP-эмулятора.",
        "",
        "Источник генерации: `emulator/task_tracker_emulator/server.py`.",
        "",
        "Команда обновления:",
        "",
        "```bash",
        "make generate-mcp-docs",
        "```",
        "",
        "## Сводка",
        "",
        "| Tool | Назначение |",
        "| --- | --- |",
    ]

    sorted_tools = [
        tools_by_name[name]
        for name in TOOL_EXAMPLES
        if name in tools_by_name
    ]
    for tool in sorted_tools:
        lines.append(f"| `{tool.name}` | {tool.description or '-'} |")

    lines.append("")

    for tool in sorted_tools:
        lines.extend(_tool_section(tool))

    return "\n".join(lines).rstrip() + "\n"


def write_tools_markdown(
    *,
    output_file: Path = DEFAULT_OUTPUT_FILE,
    state_file: Path = DEFAULT_STATE_FILE,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        generate_tools_markdown(state_file=state_file),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate human-readable documentation for MCP task tracker tools."
    )
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE)
    args = parser.parse_args()

    write_tools_markdown(output_file=args.output, state_file=args.state_file)
    print(f"Generated MCP tools documentation: {args.output}")


def _tool_section(tool: Any) -> list[str]:
    lines = [
        f"## `{tool.name}`",
        "",
        tool.description or "Описание отсутствует.",
        "",
    ]

    notes = TOOL_NOTES.get(tool.name, [])
    if notes:
        lines.extend(["### Примечания", ""])
        lines.extend(f"- {note}" for note in notes)
        lines.append("")

    lines.extend(["### Входные Параметры", ""])
    lines.extend(_parameter_table(tool.parameters))
    lines.append("")

    example_arguments = TOOL_EXAMPLES.get(tool.name, {})
    lines.extend(
        [
            "### Пример Вызова",
            "",
            "```json",
            _json_dump({"name": tool.name, "arguments": example_arguments}),
            "```",
            "",
            "### JSON Schema Входа",
            "",
            "```json",
            _json_dump(tool.parameters),
            "```",
            "",
            "### JSON Schema Ответа",
            "",
            "```json",
            _json_dump(tool.fn_metadata.output_schema),
            "```",
            "",
        ]
    )
    return lines


def _parameter_table(schema: dict[str, Any]) -> list[str]:
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    if not properties:
        return ["Параметры не требуются."]

    lines = [
        "| Параметр | Обязательный | Тип | Значение по умолчанию |",
        "| --- | --- | --- | --- |",
    ]
    for name, details in properties.items():
        default = details.get("default", "-")
        if default is None:
            default = "null"
        lines.append(
            f"| `{name}` | {_yes_no(name in required)} | `{_escape_table_cell(_schema_type(details))}` | `{_escape_table_cell(str(default))}` |"
        )
    return lines


def _schema_type(schema: dict[str, Any]) -> str:
    if "type" in schema:
        return str(schema["type"])
    if "anyOf" in schema:
        return " | ".join(str(item.get("type", "unknown")) for item in schema["anyOf"])
    return "object"


def _yes_no(value: bool) -> str:
    return "да" if value else "нет"


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
