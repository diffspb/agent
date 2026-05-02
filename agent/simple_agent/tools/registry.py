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
from simple_agent.tools.types import JsonObject, Tool, ToolContext, ToolResult


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

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
