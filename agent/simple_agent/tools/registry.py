from __future__ import annotations

from typing import cast

from simple_agent.tools.filesystem import (
    ListFilesTool,
    PatchFileTool,
    ReadFileTool,
    SearchTextTool,
    WriteFileTool,
)
from simple_agent.tools.git import GitDiffTool, GitStatusTool
from simple_agent.tools.shell import RunCommandTool, RunTestsTool
from simple_agent.tools.task_tracker import (
    CommentsAddTool,
    CommentsListTool,
    TasksGetTool,
    TasksListTool,
    TasksUpdateTool,
    WorkflowGetTool,
)
from simple_agent.tools.types import (
    AsyncTool,
    JsonObject,
    Tool,
    ToolContext,
    ToolResult,
    ToolSpec,
)


TOOL_SPECS = {
    "list_files": ToolSpec(
        name="list_files",
        description="Показать файлы и директории внутри каталога рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
            "additionalProperties": False,
        },
    ),
    "read_file": ToolSpec(
        name="read_file",
        description="Прочитать текстовый файл из рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
    "write_file": ToolSpec(
        name="write_file",
        description="Записать текстовый файл внутри рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    ),
    "patch_file": ToolSpec(
        name="patch_file",
        description="Заменить первое вхождение текста в файле рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
            "additionalProperties": False,
        },
    ),
    "search_text": ToolSpec(
        name="search_text",
        description="Найти строки с заданным текстом в файле или каталоге рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "."},
                "query": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    "run_command": ToolSpec(
        name="run_command",
        description="Запустить bash-команду внутри рабочего пространства. Для строковой команды поддерживаются cd, &&, | и другие shell-конструкции; рабочую директорию можно также задавать через cwd.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "oneOf": [
                        {"type": "string", "minLength": 1},
                        {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    ]
                },
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    ),
    "run_tests": ToolSpec(
        name="run_tests",
        description="Запустить тестовую bash-команду внутри рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "oneOf": [
                        {"type": "string", "minLength": 1},
                        {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    ]
                },
                "cwd": {"type": "string", "default": "."},
            },
            "additionalProperties": False,
        },
    ),
    "git_status": ToolSpec(
        name="git_status",
        description="Показать краткий git status внутри рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {"cwd": {"type": "string", "default": "."}},
            "additionalProperties": False,
        },
    ),
    "git_diff": ToolSpec(
        name="git_diff",
        description="Показать git diff внутри рабочего пространства.",
        input_schema={
            "type": "object",
            "properties": {"cwd": {"type": "string", "default": "."}},
            "additionalProperties": False,
        },
    ),
    "workflow_get": ToolSpec(
        name="workflow_get",
        description="Прочитать описание workflow таск-трекера через MCP.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    ),
    "tasks_get": ToolSpec(
        name="tasks_get",
        description="Получить задачу по идентификатору через MCP.",
        input_schema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
            "additionalProperties": False,
        },
    ),
    "tasks_list": ToolSpec(
        name="tasks_list",
        description="Получить список задач через MCP с необязательными фильтрами по статусу и исполнителю.",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "assignee_email": {"type": "string"},
            },
            "additionalProperties": False,
        },
    ),
    "tasks_update": ToolSpec(
        name="tasks_update",
        description="Обновить задачу через MCP, например изменить статус, исполнителя или metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "patch": {"type": "object"},
            },
            "required": ["task_id", "patch"],
            "additionalProperties": False,
        },
    ),
    "comments_add": ToolSpec(
        name="comments_add",
        description="Добавить комментарий к задаче через MCP от имени агента.",
        input_schema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["task_id", "body"],
            "additionalProperties": False,
        },
    ),
    "comments_list": ToolSpec(
        name="comments_list",
        description="Получить список комментариев задачи через MCP.",
        input_schema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    ),
}


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [TOOL_SPECS[name] for name in self.names if name in TOOL_SPECS]

    def to_llm_tools(self) -> list[JsonObject]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.input_schema,
                },
            }
            for spec in self.specs()
        ]

    def run(self, name: str, input: JsonObject, context: ToolContext) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        return tool.run(input, context)

    async def arun(self, name: str, input: JsonObject, context: ToolContext) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        if hasattr(tool, "arun"):
            return await cast(AsyncTool, tool).arun(input, context)
        return cast(Tool, tool).run(input, context)


def build_default_tool_registry(
    *,
    include_task_tracker_tools: bool = False,
) -> ToolRegistry:
    tools: list[Tool | AsyncTool] = [
        ListFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        PatchFileTool(),
        SearchTextTool(),
        RunCommandTool(),
        RunTestsTool(),
        GitStatusTool(),
        GitDiffTool(),
    ]
    if include_task_tracker_tools:
        tools.extend(
            [
                WorkflowGetTool(),
                TasksGetTool(),
                TasksListTool(),
                TasksUpdateTool(),
                CommentsAddTool(),
                CommentsListTool(),
            ]
        )
    return ToolRegistry(list(tools))
