from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from task_tracker_emulator.errors import (
    DuplicateTaskError,
    InvalidPatchError,
    TaskNotFoundError,
)
from task_tracker_emulator.models import Comment, Task, TrackerState, Workflow, utc_now


MUTABLE_TASK_FIELDS = {
    "type",
    "status",
    "title",
    "author_email",
    "assignee_email",
    "description",
    "links",
    "metadata",
}


class TaskTrackerStore:
    def __init__(self, state: TrackerState, snapshot_file: Path) -> None:
        self._state = state
        self.snapshot_file = snapshot_file
        self._tasks = {task.id: task for task in state.tasks}
        if len(self._tasks) != len(state.tasks):
            raise DuplicateTaskError("Task identifiers must be unique")

    @classmethod
    def load(cls, state_file: Path, snapshot_file: Path | None = None) -> "TaskTrackerStore":
        state = TrackerState.model_validate_json(state_file.read_text(encoding="utf-8"))
        resolved_snapshot_file = snapshot_file or Path(
            tempfile.mkstemp(prefix="simple-agent-task-tracker-", suffix=".json")[1]
        )
        return cls(state=state, snapshot_file=resolved_snapshot_file)

    @property
    def project_key(self) -> str:
        return self._state.project_key

    def workflow_get(self) -> dict[str, Any]:
        return Workflow().model_dump(mode="json")

    def tasks_get(self, id: str) -> dict[str, Any]:
        return self._get_task(id).model_dump(mode="json")

    def tasks_list(
        self,
        *,
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[dict[str, Any]]:
        tasks = sorted(self._tasks.values(), key=lambda task: task.id)
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        if assignee_email is not None:
            tasks = [task for task in tasks if task.assignee_email == assignee_email]
        return [task.model_dump(mode="json") for task in tasks]

    def tasks_update(self, *, id: str, patch: dict[str, Any]) -> dict[str, Any]:
        unknown_fields = set(patch) - MUTABLE_TASK_FIELDS
        if unknown_fields:
            fields = ", ".join(sorted(unknown_fields))
            raise InvalidPatchError(f"Unsupported task patch fields: {fields}")

        current = self._get_task(id)
        payload = current.model_dump(mode="python")
        payload.update(patch)

        try:
            updated = Task.model_validate(payload)
        except ValidationError as exc:
            raise InvalidPatchError(str(exc)) from exc

        self._tasks[id] = updated
        self._sync_state()
        self.write_snapshot()
        return updated.model_dump(mode="json")

    def comments_add(self, *, task_id: str, author_email: str, body: str) -> dict[str, Any]:
        task = self._get_task(task_id)
        comment = Comment(
            id=f"comment-{uuid4().hex}",
            author_email=author_email,
            body=body,
            created_at=utc_now(),
        )
        updated = task.model_copy(update={"comments": [*task.comments, comment]})
        self._tasks[task_id] = updated
        self._sync_state()
        self.write_snapshot()
        return comment.model_dump(mode="json")

    def comments_list(self, *, task_id: str) -> list[dict[str, Any]]:
        task = self._get_task(task_id)
        return [comment.model_dump(mode="json") for comment in task.comments]

    def write_snapshot(self) -> None:
        self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_file.write_text(
            self._state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _get_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return task

    def _sync_state(self) -> None:
        self._state = self._state.model_copy(
            update={"tasks": sorted(self._tasks.values(), key=lambda task: task.id)}
        )
