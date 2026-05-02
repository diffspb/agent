from __future__ import annotations

from typing import Any, Protocol


JsonObject = dict[str, Any]


class TaskTrackerClient(Protocol):
    async def workflow_get(self) -> JsonObject:
        raise NotImplementedError

    async def tasks_get(self, task_id: str) -> JsonObject:
        raise NotImplementedError

    async def tasks_list(
        self,
        *,
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[JsonObject]:
        raise NotImplementedError

    async def tasks_update(self, task_id: str, patch: JsonObject) -> JsonObject:
        raise NotImplementedError

    async def comments_add(
        self,
        *,
        task_id: str,
        author_email: str,
        body: str,
    ) -> JsonObject:
        raise NotImplementedError

    async def comments_list(self, task_id: str) -> list[JsonObject]:
        raise NotImplementedError
