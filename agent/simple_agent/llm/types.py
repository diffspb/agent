from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


JsonObject = dict[str, Any]
LLMMessage = dict[str, Any]


@dataclass(frozen=True)
class LLMToolCall:
    id: str
    name: str
    arguments: JsonObject


@dataclass(frozen=True)
class LLMResponse:
    content: str | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    raw: JsonObject = field(default_factory=dict)


class LLMClient(Protocol):
    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[JsonObject] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError
