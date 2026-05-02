from pathlib import Path

import pytest

from task_tracker_emulator.errors import InvalidPatchError, TaskNotFoundError
from task_tracker_emulator.store import TaskTrackerStore


def test_store_loads_workflow_and_lists_tasks(tmp_path: Path) -> None:
    store = TaskTrackerStore.load(
        state_file=Path("datasets/task_tracker/simple-task.json"),
        snapshot_file=tmp_path / "snapshot.json",
    )

    workflow = store.workflow_get()
    tasks = store.tasks_list(status="Open", assignee_email="agent@example.com")

    assert workflow["statuses"] == [
        "Todo",
        "Open",
        "InProgress",
        "InReview",
        "NeedsInfo",
        "Done",
        "Cancelled",
    ]
    assert workflow["transitions"] == "any"
    assert [task["id"] for task in tasks] == ["PROJECT-1"]


def test_store_updates_task_and_writes_snapshot(tmp_path: Path) -> None:
    snapshot_file = tmp_path / "snapshot.json"
    store = TaskTrackerStore.load(
        state_file=Path("datasets/task_tracker/simple-task.json"),
        snapshot_file=snapshot_file,
    )

    updated = store.tasks_update(
        id="PROJECT-1",
        patch={
            "status": "InProgress",
            "metadata": {"last_run_id": "run-1"},
        },
    )

    assert updated["status"] == "InProgress"
    assert updated["metadata"] == {"last_run_id": "run-1"}
    assert snapshot_file.exists()
    assert "InProgress" in snapshot_file.read_text(encoding="utf-8")


def test_store_adds_and_lists_comments(tmp_path: Path) -> None:
    store = TaskTrackerStore.load(
        state_file=Path("datasets/task_tracker/simple-task.json"),
        snapshot_file=tmp_path / "snapshot.json",
    )

    comment = store.comments_add(
        task_id="PROJECT-1",
        author_email="agent@example.com",
        body="Начинаю работу.",
    )

    comments = store.comments_list(task_id="PROJECT-1")
    assert comment["author_email"] == "agent@example.com"
    assert comment["body"] == "Начинаю работу."
    assert comments[-1]["id"] == comment["id"]


def test_store_reports_missing_tasks_and_invalid_patch(tmp_path: Path) -> None:
    store = TaskTrackerStore.load(
        state_file=Path("datasets/task_tracker/simple-task.json"),
        snapshot_file=tmp_path / "snapshot.json",
    )

    with pytest.raises(TaskNotFoundError):
        store.tasks_get("PROJECT-999")

    with pytest.raises(InvalidPatchError):
        store.tasks_update(id="PROJECT-1", patch={"unknown": True})
