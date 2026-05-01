from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from simple_agent.config import Settings
from simple_agent.service.app import create_app


@pytest.mark.anyio
async def test_agent_tick_endpoint_selects_task_and_returns_candidates(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            database_path=tmp_path / "api-agent.sqlite3",
            agent_email="agent@example.com",
        )
    )
    app.state.task_tracker_factory = lambda: FakeTracker(
        [
            _task("PROJECT-1", priority="low"),
            _task("PROJECT-2", priority="high"),
        ]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/agent/tick", json={"task_id": "PROJECT-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["tick"]["status"] == "completed"
    assert payload["tick"]["trigger_task_id"] == "PROJECT-1"
    assert payload["selected_run"]["external_task_id"] == "PROJECT-2"
    assert [candidate["external_task_id"] for candidate in payload["candidates"]] == [
        "PROJECT-1",
        "PROJECT-2",
    ]


def _task(
    task_id: str,
    *,
    priority: str | int = "normal",
) -> dict[str, Any]:
    return {
        "id": task_id,
        "type": "task",
        "status": "Open",
        "title": f"Задача {task_id}",
        "author_email": "author@example.com",
        "assignee_email": "agent@example.com",
        "description": "",
        "links": [],
        "comments": [],
        "metadata": {"priority": priority},
    }


class FakeTracker:
    def __init__(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = {task["id"]: task for task in tasks}

    async def workflow_get(self) -> dict[str, Any]:
        return {"statuses": ["Todo", "Open", "Done"], "transitions": "any"}

    async def tasks_get(self, task_id: str) -> dict[str, Any]:
        return self.tasks[task_id]

    async def tasks_list(
        self,
        *,
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[dict[str, Any]]:
        tasks = list(self.tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task["status"] == status]
        if assignee_email is not None:
            tasks = [task for task in tasks if task["assignee_email"] == assignee_email]
        return sorted(tasks, key=lambda task: task["id"])
