from __future__ import annotations

from simple_agent.tools.shell import RunCommandTool
from simple_agent.tools.types import JsonObject, ToolContext, ToolResult


class GitStatusTool:
    name = "git_status"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        cwd = input.get("cwd", ".")
        return RunCommandTool().run({"command": ["git", "status", "--short"], "cwd": cwd}, context)


class GitDiffTool:
    name = "git_diff"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        cwd = input.get("cwd", ".")
        return RunCommandTool().run({"command": ["git", "diff", "--"], "cwd": cwd}, context)
