from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from simple_agent.agent.policies import decide_task_selection
from simple_agent.storage.models import AgentTickRecord, RunRecord, TaskCandidateRecord
from simple_agent.storage import ObservabilitySink
from simple_agent.tracker.client import JsonObject, TaskTrackerClient


EXECUTABLE_TASK_TYPES = {"task", "test"}
BLOCKING_STATUSES = {"Todo", "Open", "InProgress", "InReview", "NeedsInfo"}
NON_BLOCKING_STATUSES = {"Done", "Cancelled"}
PRIORITY_BY_LABEL = {
    "critical": 400,
    "high": 300,
    "normal": 200,
    "low": 100,
}


@dataclass(frozen=True)
class TaskSelectionResult:
    tick: AgentTickRecord
    selected_run: RunRecord | None
    selected_task: JsonObject | None
    candidates: list[TaskCandidateRecord]


@dataclass(frozen=True)
class _EvaluatedTask:
    task: JsonObject
    priority: int
    dependencies_state: str
    decision: str
    reason: str
    blocking_task_ids: list[str]
    metadata: JsonObject


class TaskSelectionService:
    def __init__(
        self,
        *,
        observability: ObservabilitySink,
        tracker: TaskTrackerClient,
        agent_email: str,
    ) -> None:
        self.observability = observability
        self.tracker = tracker
        self.agent_email = agent_email

    async def run_tick(
        self,
        *,
        source: str,
        trigger_task_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TaskSelectionResult:
        tick = self.observability.create_tick(
            source=source,
            status="started",
            trigger_task_id=trigger_task_id,
            payload=payload,
        )

        try:
            await self.tracker.workflow_get()
            self.observability.add_event(
                tick_id=tick.id,
                type="tick.workflow_loaded",
                message="Workflow таск-трекера загружен",
            )

            tasks = await self.tracker.tasks_list(
                status="Open",
                assignee_email=self.agent_email,
            )
            all_tasks = await self.tracker.tasks_list()
            evaluated = await self._evaluate_tasks(
                tick_id=tick.id,
                tasks=tasks,
                all_tasks=all_tasks,
            )
            selected = self._select_task(evaluated)
            candidates = self._record_candidates(
                tick_id=tick.id,
                evaluated=evaluated,
                selected=selected,
            )

            selected_run = None
            selected_task = selected.task if selected else None
            if selected_task is not None:
                task_id = str(selected_task["id"])
                selected_run = self.observability.create_run(
                    tick_id=tick.id,
                    external_task_id=task_id,
                    status="queued",
                    summary="Задача выбрана для выполнения",
                )
                self.observability.add_event(
                    tick_id=tick.id,
                    run_id=selected_run.id,
                    type="task.selected",
                    message="Выбрана задача для выполнения",
                    payload={"external_task_id": task_id},
                )
            else:
                self.observability.add_event(
                    tick_id=tick.id,
                    type="task_selection.none",
                    message="Нет доступных задач для выполнения",
                    payload={"candidate_count": len(evaluated)},
                )

            tick = self.observability.complete_tick(tick.id, status="completed")
            return TaskSelectionResult(
                tick=tick,
                selected_run=selected_run,
                selected_task=selected_task,
                candidates=candidates,
            )
        except Exception as exc:
            self.observability.add_event(
                tick_id=tick.id,
                type="tick.failed",
                message="Tick завершился с ошибкой",
                payload={"error": str(exc)},
            )
            failed_tick = self.observability.complete_tick(
                tick.id,
                status="failed",
                error=str(exc),
            )
            return TaskSelectionResult(
                tick=failed_tick,
                selected_run=None,
                selected_task=None,
                candidates=self.observability.list_task_candidates_for_tick(tick.id),
            )

    async def _evaluate_tasks(
        self,
        *,
        tick_id: int,
        tasks: list[JsonObject],
        all_tasks: list[JsonObject],
    ) -> list[_EvaluatedTask]:
        tasks_by_id = {str(task.get("id")): task for task in all_tasks if task.get("id")}
        evaluated: list[_EvaluatedTask] = []
        for listed_task in tasks:
            task_id = str(listed_task.get("id"))
            task = await self._load_task(task_id, fallback=listed_task)
            evaluated.append(
                await self._evaluate_task(
                    tick_id=tick_id,
                    task=task,
                    tasks_by_id=tasks_by_id,
                )
            )
        return evaluated

    async def _load_task(self, task_id: str, *, fallback: JsonObject) -> JsonObject:
        try:
            return await self.tracker.tasks_get(task_id)
        except Exception:
            return fallback

    async def _evaluate_task(
        self,
        *,
        tick_id: int,
        task: JsonObject,
        tasks_by_id: dict[str, JsonObject],
    ) -> _EvaluatedTask:
        task_id = str(task.get("id", ""))
        priority = priority_score(task)
        blocking_task_ids = await self._find_blocking_tasks(
            task=task,
            tasks_by_id=tasks_by_id,
        )

        metadata: JsonObject = {}
        if str(task.get("status")) != "Open":
            reason = "status_not_open"
            dependencies_state = "not_checked"
        elif task.get("assignee_email") != self.agent_email:
            reason = "wrong_assignee"
            dependencies_state = "not_checked"
        elif str(task.get("type")) not in EXECUTABLE_TASK_TYPES:
            reason = "unsupported_task_type"
            dependencies_state = "not_checked"
        elif "dependency_unknown" in blocking_task_ids:
            reason = "dependency_unknown"
            dependencies_state = "unknown"
        elif blocking_task_ids:
            reason = "blocked_by_dependency"
            dependencies_state = "blocked"
        else:
            active_run = self.observability.get_active_run_for_task(task_id)
            decision = decide_task_selection(
                task=task,
                active_run=active_run,
                agent_email=self.agent_email,
            )
            if decision.event_type is not None and decision.message is not None:
                self.observability.add_event(
                    tick_id=tick_id,
                    run_id=active_run.id if active_run is not None else None,
                    type=decision.event_type,
                    message=decision.message,
                    payload=decision.payload,
                )
            if active_run is not None:
                metadata["local_active_run"] = {
                    "id": active_run.id,
                    "status": active_run.status,
                }
            if decision.reason is not None:
                reason = decision.reason
                dependencies_state = decision.dependencies_state or "not_checked"
            else:
                reason = "eligible"
                dependencies_state = "clear"
        if reason == "eligible":
            reason = "eligible"

        decision = "candidate" if reason == "eligible" else "skipped"
        return _EvaluatedTask(
            task=task,
            priority=priority,
            dependencies_state=dependencies_state,
            decision=decision,
            reason=reason,
            blocking_task_ids=blocking_task_ids,
            metadata=metadata,
        )

    async def _find_blocking_tasks(
        self,
        *,
        task: JsonObject,
        tasks_by_id: dict[str, JsonObject],
    ) -> list[str]:
        task_id = str(task.get("id"))
        blocking_task_ids: list[str] = []

        for link in _links(task):
            if link.get("type") != "blocked_by":
                continue
            target_id = str(link.get("target", ""))
            blocking = await self._is_blocking_task(target_id, tasks_by_id=tasks_by_id)
            if blocking is None:
                blocking_task_ids.append("dependency_unknown")
            elif blocking:
                blocking_task_ids.append(target_id)

        for other_task in tasks_by_id.values():
            other_id = str(other_task.get("id", ""))
            if other_id == task_id:
                continue
            for link in _links(other_task):
                if link.get("type") == "blocks" and str(link.get("target")) == task_id:
                    blocking = await self._is_blocking_task(other_id, tasks_by_id=tasks_by_id)
                    if blocking is None:
                        blocking_task_ids.append("dependency_unknown")
                    elif blocking:
                        blocking_task_ids.append(other_id)

        return sorted(set(blocking_task_ids), key=_task_sort_key)

    async def _is_blocking_task(
        self,
        task_id: str,
        *,
        tasks_by_id: dict[str, JsonObject],
    ) -> bool | None:
        task = tasks_by_id.get(task_id)
        if task is None:
            try:
                task = await self.tracker.tasks_get(task_id)
            except Exception:
                return None

        status = str(task.get("status"))
        if status in NON_BLOCKING_STATUSES:
            return False
        return True

    def _select_task(self, evaluated: list[_EvaluatedTask]) -> _EvaluatedTask | None:
        eligible = [item for item in evaluated if item.reason == "eligible"]
        if not eligible:
            return None
        return sorted(
            eligible,
            key=lambda item: (-item.priority, _task_sort_key(str(item.task.get("id")))),
        )[0]

    def _record_candidates(
        self,
        *,
        tick_id: int,
        evaluated: list[_EvaluatedTask],
        selected: _EvaluatedTask | None,
    ) -> list[TaskCandidateRecord]:
        selected_task_id = str(selected.task.get("id")) if selected else None
        records: list[TaskCandidateRecord] = []
        for item in sorted(
            evaluated,
            key=lambda value: _task_sort_key(str(value.task.get("id"))),
        ):
            task_id = str(item.task.get("id"))
            decision = item.decision
            reason = item.reason
            if task_id == selected_task_id:
                decision = "selected"
                reason = "selected_highest_priority"
            elif item.reason == "eligible":
                decision = "skipped"
                reason = "lower_priority_than_selected"

            records.append(
                self.observability.add_task_candidate(
                    tick_id=tick_id,
                    external_task_id=task_id,
                    status=str(item.task.get("status", "")),
                    assignee_email=_optional_string(item.task.get("assignee_email")),
                    priority=item.priority,
                    dependencies_state=item.dependencies_state,
                    decision=decision,
                    reason=reason,
                    metadata={
                        "title": item.task.get("title"),
                        "type": item.task.get("type"),
                        "priority": _metadata(item.task).get("priority"),
                        "blocking_task_ids": item.blocking_task_ids,
                        **item.metadata,
                    },
                )
            )
        return records


def priority_score(task: JsonObject) -> int:
    raw_priority = _metadata(task).get("priority")
    if raw_priority is None:
        return PRIORITY_BY_LABEL["normal"]
    if isinstance(raw_priority, int):
        return raw_priority
    if isinstance(raw_priority, float):
        return int(raw_priority)

    priority = str(raw_priority).strip().lower()
    if priority.lstrip("-").isdigit():
        return int(priority)
    return PRIORITY_BY_LABEL.get(priority, PRIORITY_BY_LABEL["normal"])


def _metadata(task: JsonObject) -> JsonObject:
    metadata = task.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _links(task: JsonObject) -> list[JsonObject]:
    links = task.get("links")
    if not isinstance(links, list):
        return []
    return [link for link in links if isinstance(link, dict)]


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _task_sort_key(task_id: str) -> tuple[str, int, str]:
    match = re.search(r"^(?P<project>[A-Z][A-Z0-9]*)-(?P<number>\d+)$", task_id)
    if match is None:
        return (task_id, 0, task_id)
    return (match.group("project"), int(match.group("number")), task_id)
