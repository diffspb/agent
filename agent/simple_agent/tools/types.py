from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from simple_agent.workspace import Workspace

if TYPE_CHECKING:
    from simple_agent.tracker.client import TaskTrackerClient


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ToolContext:
    workspace: Workspace
    command_timeout_seconds: float
    output_max_bytes: int
    file_read_max_bytes: int
    tracker: "TaskTrackerClient | None" = None
    agent_email: str | None = None


@dataclass(frozen=True)
class ToolResult:
    output: JsonObject


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: JsonObject


class Tool(Protocol):
    name: str

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        raise NotImplementedError


class AsyncTool(Protocol):
    name: str

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        raise NotImplementedError


class ToolError(Exception):
    pass
