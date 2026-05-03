from __future__ import annotations

from collections import deque

from simple_agent.llm.types import JsonObject, LLMMessage, LLMResponse, LLMToolCall


class StubLLMClient:
    def __init__(self, responses: list[LLMResponse] | None = None) -> None:
        self.responses = deque(responses or _default_responses())
        self.requests: list[dict[str, object]] = []

    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[JsonObject] | None = None,
    ) -> LLMResponse:
        self.requests.append({"messages": messages, "tools": tools or []})
        if not self.responses:
            return LLMResponse(content="Готово. Дополнительных действий не требуется.")
        return self.responses.popleft()


def _default_responses() -> list[LLMResponse]:
    return [
        LLMResponse(
            content="Подготовлю краткий файл-отчет в рабочем пространстве.",
            tool_calls=[
                LLMToolCall(
                    id="stub_write_summary",
                    name="write_file",
                    arguments={
                        "path": "llm-agent-summary.txt",
                        "content": "Stub LLM runtime completed.\n",
                    },
                )
            ],
        ),
        LLMResponse(content="Задача выполнена в stub-режиме LLM."),
    ]
