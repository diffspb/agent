from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from task_tracker_emulator.errors import InvalidPatchError, TaskNotFoundError
from task_tracker_emulator.store import TaskTrackerStore


def create_mcp_server(store: TaskTrackerStore, *, host: str, port: int) -> FastMCP:
    mcp = FastMCP(
        "Simple Agent Task Tracker Emulator",
        host=host,
        port=port,
        json_response=True,
        stateless_http=True,
    )

    @mcp.tool(name="workflow_get")
    def workflow_get() -> dict[str, Any]:
        """Получить фиксированный workflow таск-трекера."""
        return store.workflow_get()

    @mcp.tool(name="tasks_get")
    def tasks_get(id: str) -> dict[str, Any]:
        """Получить задачу по идентификатору вида PROJECT-123."""
        return _as_tool_error(store.tasks_get, id)

    @mcp.tool(name="tasks_list")
    def tasks_list(
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[dict[str, Any]]:
        """Получить задачи по статусу и исполнителю email."""
        return store.tasks_list(status=status, assignee_email=assignee_email)

    @mcp.tool(name="tasks_update")
    def tasks_update(id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Изменить задачу, включая статус."""
        return _as_tool_error(store.tasks_update, id=id, patch=patch)

    @mcp.tool(name="comments_add")
    def comments_add(task_id: str, author_email: str, body: str) -> dict[str, Any]:
        """Добавить комментарий к задаче."""
        return _as_tool_error(
            store.comments_add,
            task_id=task_id,
            author_email=author_email,
            body=body,
        )

    @mcp.tool(name="comments_list")
    def comments_list(task_id: str) -> list[dict[str, Any]]:
        """Получить комментарии задачи."""
        return _as_tool_error(store.comments_list, task_id=task_id)

    return mcp


def load_mcp_server(
    *,
    state_file: Path,
    snapshot_file: Path | None,
    host: str,
    port: int,
) -> tuple[FastMCP, TaskTrackerStore]:
    store = TaskTrackerStore.load(state_file=state_file, snapshot_file=snapshot_file)
    return create_mcp_server(store, host=host, port=port), store


def _as_tool_error(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except TaskNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    except InvalidPatchError as exc:
        raise ValueError(str(exc)) from exc
