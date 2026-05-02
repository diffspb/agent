from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from simple_agent.agent import PrimitiveAgentRuntime
from simple_agent.storage import Repository, SqliteDatabase


@pytest.mark.anyio
async def test_primitive_runtime_completes_run_and_updates_task_tracker(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    runtime = PrimitiveAgentRuntime(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await runtime.start_run(run)

    assert result.run.status == "completed"
    assert result.run.finished_at is not None
    assert tracker.tasks["PROJECT-1"]["status"] == "Done"
    assert [comment["body"] for comment in tracker.comments["PROJECT-1"]] == [
        "Агент начал выполнение задачи.",
        "Примитивный runtime завершил stub-выполнение задачи без изменения кода.",
    ]
    events = repository.list_events_for_run(run.id)
    assert [event.type for event in events] == [
        "run.started",
        "task.loaded",
        "task.status_changed",
        "task.comment_added",
        "task.comment_added",
        "task.status_changed",
        "run.completed",
    ]


@pytest.mark.anyio
async def test_primitive_runtime_cancels_queued_run(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    runtime = PrimitiveAgentRuntime(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await runtime.cancel_run(run)

    assert result.run.status == "cancelled"
    assert result.run.finished_at is not None
    assert repository.list_events_for_run(run.id)[0].type == "run.cancelled"


@pytest.mark.anyio
async def test_primitive_runtime_marks_run_failed_on_tracker_error(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-404", status="queued")
    tracker = FakeTracker([])
    runtime = PrimitiveAgentRuntime(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await runtime.start_run(run)

    assert result.run.status == "failed"
    assert result.run.error == "Task not found: PROJECT-404"
    assert repository.list_events_for_run(run.id)[-1].type == "run.failed"


def _repository(tmp_path: Path) -> Repository:
    database = SqliteDatabase(tmp_path / "runtime.sqlite3")
    database.initialize()
    return Repository(database)


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
