from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from simple_agent.workspace import Workspace


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ToolContext:
    workspace: Workspace
    command_timeout_seconds: float
    output_max_bytes: int
    file_read_max_bytes: int


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


class ToolError(Exception):
    pass
