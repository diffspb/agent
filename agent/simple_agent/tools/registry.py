from __future__ import annotations

from simple_agent.tools.filesystem import (
    ListFilesTool,
    PatchFileTool,
    ReadFileTool,
    SearchTextTool,
    WriteFileTool,
)
from simple_agent.tools.git import GitDiffTool, GitStatusTool
from simple_agent.tools.shell import RunCommandTool, RunTestsTool
from simple_agent.tools.types import JsonObject, Tool, ToolContext, ToolResult, ToolSpec


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
        description="Запустить безопасную команду внутри рабочего пространства.",
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
        description="Запустить тестовую команду внутри рабочего пространства.",
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


def build_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
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
    )
