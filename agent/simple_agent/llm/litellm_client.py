from __future__ import annotations

import json
from typing import Any

from litellm import acompletion

from simple_agent.llm.types import JsonObject, LLMMessage, LLMResponse, LLMToolCall


class LiteLLMClient:
    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def complete(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[JsonObject] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "timeout": self.timeout_seconds,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await acompletion(**kwargs)
        return _normalize_response(response)


def _normalize_response(response: Any) -> LLMResponse:
    raw = _to_plain_json(response)
    choices = raw.get("choices") or []
    if not choices:
        return LLMResponse(raw=raw)

    message = choices[0].get("message") or {}
    tool_calls = []
    for index, call in enumerate(message.get("tool_calls") or []):
        function = call.get("function") or {}
        tool_calls.append(
            LLMToolCall(
                id=str(call.get("id") or f"tool_call_{index}"),
                name=str(function.get("name") or ""),
                arguments=_parse_arguments(function.get("arguments")),
            )
        )

    return LLMResponse(
        content=message.get("content"),
        tool_calls=[call for call in tool_calls if call.name],
        raw=raw,
    )


def _parse_arguments(value: Any) -> JsonObject:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_plain_json(value: Any) -> JsonObject:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "dict"):
        dumped = value.dict()
        return dumped if isinstance(dumped, dict) else {}
    return {}
