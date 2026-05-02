from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from simple_agent.config import Settings
from simple_agent.service.app import create_app


@pytest.mark.anyio
async def test_run_start_endpoint_completes_queued_run(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            database_path=tmp_path / "run-start.sqlite3",
            agent_email="agent@example.com",
            workspace_root=tmp_path / "workspaces",
        )
    )
    repository = app.state.repository
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    app.state.task_tracker_factory = lambda: tracker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/runs/{run.id}/start")
        events_response = await client.get(f"/api/runs/{run.id}/events")
        tool_calls_response = await client.get(f"/api/runs/{run.id}/tool-calls")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert tracker.tasks["PROJECT-1"]["status"] == "Done"
    assert events_response.status_code == 200
    assert events_response.json()[-1]["type"] == "run.completed"
    assert tool_calls_response.status_code == 200
    assert tool_calls_response.json()[0]["tool_name"] == "write_file"


@pytest.mark.anyio
async def test_run_cancel_endpoint_cancels_queued_run(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            database_path=tmp_path / "run-cancel.sqlite3",
            workspace_root=tmp_path / "workspaces",
        )
    )
    repository = app.state.repository
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    app.state.task_tracker_factory = lambda: FakeTracker([_task("PROJECT-1")])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/runs/{run.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.anyio
async def test_run_start_endpoint_rejects_completed_run(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            database_path=tmp_path / "run-conflict.sqlite3",
            workspace_root=tmp_path / "workspaces",
        )
    )
    repository = app.state.repository
    run = repository.create_run(external_task_id="PROJECT-1", status="completed")
    app.state.task_tracker_factory = lambda: FakeTracker([_task("PROJECT-1")])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/runs/{run.id}/start")

    assert response.status_code == 409


def _task(task_id: str) -> dict[str, Any]:
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
        "metadata": {},
    }


class FakeTracker:
    def __init__(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = {task["id"]: task for task in tasks}
        self.comments: dict[str, list[dict[str, Any]]] = {
            task["id"]: [] for task in tasks
        }

    async def workflow_get(self) -> dict[str, Any]:
        return {"statuses": ["Open", "InProgress", "Done"], "transitions": "any"}

    async def tasks_get(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            raise RuntimeError(f"Task not found: {task_id}")
        return task

    async def tasks_list(
        self,
        *,
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[dict[str, Any]]:
        return list(self.tasks.values())

    async def tasks_update(self, task_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        task = await self.tasks_get(task_id)
        task.update(patch)
        return task

    async def comments_add(
        self,
        *,
        task_id: str,
        author_email: str,
        body: str,
    ) -> dict[str, Any]:
        await self.tasks_get(task_id)
        comment = {
            "id": f"comment-{len(self.comments[task_id]) + 1}",
            "author_email": author_email,
            "body": body,
            "created_at": "2026-05-02T00:00:00Z",
        }
        self.comments[task_id].append(comment)
        return comment

    async def comments_list(self, task_id: str) -> list[dict[str, Any]]:
        await self.tasks_get(task_id)
        return self.comments[task_id]
