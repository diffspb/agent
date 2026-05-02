from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from simple_agent.agent import TaskSelectionService
from simple_agent.storage import Repository, SqliteDatabase


@pytest.mark.anyio
async def test_task_selection_picks_highest_priority_open_unblocked_task(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    tracker = FakeTracker(
        [
            _task("PROJECT-1", priority="normal"),
            _task("PROJECT-2", priority="high"),
        ]
    )
    service = TaskSelectionService(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await service.run_tick(source="manual")

    assert result.tick.status == "completed"
    assert result.selected_run is not None
    assert result.selected_run.external_task_id == "PROJECT-2"
    assert [candidate.reason for candidate in result.candidates] == [
        "lower_priority_than_selected",
        "selected_highest_priority",
    ]


@pytest.mark.anyio
async def test_task_selection_skips_task_blocked_by_active_dependency(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    tracker = FakeTracker(
        [
            _task(
                "PROJECT-1",
                priority="critical",
                links=[{"type": "blocked_by", "target": "PROJECT-9"}],
            ),
            _task("PROJECT-2", priority="normal"),
            _task("PROJECT-9", status="InProgress", assignee_email="other@example.com"),
        ]
    )
    service = TaskSelectionService(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await service.run_tick(source="manual")

    assert result.selected_run is not None
    assert result.selected_run.external_task_id == "PROJECT-2"
    blocked = next(
        candidate
        for candidate in result.candidates
        if candidate.external_task_id == "PROJECT-1"
    )
    assert blocked.reason == "blocked_by_dependency"
    assert blocked.dependencies_state == "blocked"
    assert blocked.metadata["blocking_task_ids"] == ["PROJECT-9"]


@pytest.mark.anyio
async def test_task_selection_ignores_cancelled_dependency(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    tracker = FakeTracker(
        [
            _task(
                "PROJECT-1",
                priority="critical",
                links=[{"type": "blocked_by", "target": "PROJECT-9"}],
            ),
            _task("PROJECT-9", status="Cancelled", assignee_email="other@example.com"),
        ]
    )
    service = TaskSelectionService(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await service.run_tick(source="manual")

    assert result.selected_run is not None
    assert result.selected_run.external_task_id == "PROJECT-1"


@pytest.mark.anyio
async def test_task_selection_skips_unknown_dependency(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    tracker = FakeTracker(
        [
            _task(
                "PROJECT-1",
                priority="critical",
                links=[{"type": "blocked_by", "target": "PROJECT-404"}],
            ),
        ]
    )
    service = TaskSelectionService(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await service.run_tick(source="manual")

    assert result.selected_run is None
    assert result.candidates[0].reason == "dependency_unknown"


@pytest.mark.anyio
async def test_task_selection_does_not_create_duplicate_run_for_active_task(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.create_run(external_task_id="PROJECT-1", status="running")
    tracker = FakeTracker([_task("PROJECT-1", priority="critical")])
    service = TaskSelectionService(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
    )

    result = await service.run_tick(source="manual")

    assert result.selected_run is None
    assert result.candidates[0].reason == "already_running"


def _repository(tmp_path: Path) -> Repository:
    database = SqliteDatabase(tmp_path / "agent.sqlite3")
    database.initialize()
    return Repository(database)


def _task(
    task_id: str,
    *,
    status: str = "Open",
    task_type: str = "task",
    assignee_email: str | None = "agent@example.com",
    priority: str | int = "normal",
    links: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "type": task_type,
        "status": status,
        "title": f"Задача {task_id}",
        "author_email": "author@example.com",
        "assignee_email": assignee_email,
        "description": "",
        "links": links or [],
        "comments": [],
        "metadata": {"priority": priority},
    }


class FakeTracker:
    def __init__(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = {task["id"]: task for task in tasks}

    async def workflow_get(self) -> dict[str, Any]:
        return {"statuses": ["Todo", "Open", "Done"], "transitions": "any"}

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
        tasks = list(self.tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task["status"] == status]
        if assignee_email is not None:
            tasks = [task for task in tasks if task["assignee_email"] == assignee_email]
        return sorted(tasks, key=lambda task: task["id"])
