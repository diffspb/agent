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
            content="Проверю workflow и отмечу начало работы.",
            tool_calls=[
                LLMToolCall(
                    id="stub_workflow_get",
                    name="workflow_get",
                    arguments={},
                ),
                LLMToolCall(
                    id="stub_task_start",
                    name="tasks_update",
                    arguments={"task_id": "PROJECT-1", "patch": {"status": "InProgress"}},
                ),
                LLMToolCall(
                    id="stub_comment_start",
                    name="comments_add",
                    arguments={
                        "task_id": "PROJECT-1",
                        "body": "Агент начал выполнение задачи в LLM-режиме.",
                    },
                ),
                LLMToolCall(
                    id="stub_write_summary",
                    name="write_file",
                    arguments={
                        "path": "llm-agent-summary.txt",
                        "content": "Stub LLM runtime completed.\n",
                    },
                ),
            ],
        ),
        LLMResponse(
            content="Задача выполнена в stub-режиме LLM.",
            tool_calls=[
                LLMToolCall(
                    id="stub_comment_done",
                    name="comments_add",
                    arguments={
                        "task_id": "PROJECT-1",
                        "body": "Тип результата: code_change\nПроверки: Проверки не запускались: LLM runtime не вызвал run_tests.\nDiff-артефакт: final.diff\n\nЗадача выполнена в stub-режиме LLM.",
                    },
                ),
                LLMToolCall(
                    id="stub_task_done",
                    name="tasks_update",
                    arguments={"task_id": "PROJECT-1", "patch": {"status": "InReview"}},
                ),
            ],
        ),
        LLMResponse(content="Задача выполнена в stub-режиме LLM."),
    ]
