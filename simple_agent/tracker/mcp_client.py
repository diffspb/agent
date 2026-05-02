from __future__ import annotations

from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


JsonObject = dict[str, Any]


class McpTaskTrackerClient:
    def __init__(self, *, url: str, timeout_seconds: float = 30.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    async def workflow_get(self) -> JsonObject:
        payload = await self._call_tool("workflow_get", {})
        return _expect_object(payload)

    async def tasks_get(self, task_id: str) -> JsonObject:
        payload = await self._call_tool("tasks_get", {"id": task_id})
        return _expect_object(payload)

    async def tasks_list(
        self,
        *,
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[JsonObject]:
        arguments: JsonObject = {}
        if status is not None:
            arguments["status"] = status
        if assignee_email is not None:
            arguments["assignee_email"] = assignee_email

        payload = await self._call_tool("tasks_list", arguments)
        return _expect_object_list(payload)

    async def tasks_update(self, task_id: str, patch: JsonObject) -> JsonObject:
        payload = await self._call_tool("tasks_update", {"id": task_id, "patch": patch})
        return _expect_object(payload)

    async def comments_add(
        self,
        *,
        task_id: str,
        author_email: str,
        body: str,
    ) -> JsonObject:
        payload = await self._call_tool(
            "comments_add",
            {
                "task_id": task_id,
                "author_email": author_email,
                "body": body,
            },
        )
        return _expect_object(payload)

    async def comments_list(self, task_id: str) -> list[JsonObject]:
        payload = await self._call_tool("comments_list", {"task_id": task_id})
        return _expect_object_list(payload)

    async def _call_tool(self, name: str, arguments: JsonObject) -> Any:
        async with streamablehttp_client(
            self.url,
            timeout=self.timeout_seconds,
            httpx_client_factory=_create_no_proxy_http_client,
        ) as (read_stream, write_stream, _session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(f"MCP tool call failed: {name}")
        return result.structuredContent


def _create_no_proxy_http_client(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        auth=auth,
        trust_env=False,
    )


def _expect_object(payload: Any) -> JsonObject:
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"Expected MCP object result, got {type(payload).__name__}")


def _expect_object_list(payload: Any) -> list[JsonObject]:
    if isinstance(payload, dict) and isinstance(payload.get("result"), list):
        values = payload["result"]
    else:
        values = payload

    if not isinstance(values, list):
        raise TypeError(f"Expected MCP list result, got {type(values).__name__}")
    if not all(isinstance(item, dict) for item in values):
        raise TypeError("Expected MCP list result to contain objects")
    return values
