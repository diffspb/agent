from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from simple_agent.storage.models import RunRecord


JsonObject = dict[str, Any]

RUN_STARTABLE_TASK_STATUSES = {"Open", "InProgress"}


@dataclass(frozen=True)
class TaskSelectionPolicyDecision:
    reason: str | None
    dependencies_state: str | None
    event_type: str | None
    message: str | None
    payload: JsonObject


@dataclass(frozen=True)
class RunStartPolicyDecision:
    allowed: bool
    message: str
    task_status: str
    should_transition_to_in_progress: bool
    event_type: str | None = None
    event_message: str | None = None
    payload: JsonObject | None = None


def decide_task_selection(
    *,
    task: JsonObject,
    active_run: RunRecord | None,
    agent_email: str,
) -> TaskSelectionPolicyDecision:
    if active_run is None:
        return TaskSelectionPolicyDecision(
            reason=None,
            dependencies_state=None,
            event_type=None,
            message=None,
            payload={},
        )

    task_status = str(task.get("status"))
    task_assignee = str(task.get("assignee_email") or "")
    if task_status == "Open":
        return TaskSelectionPolicyDecision(
            reason=None,
            dependencies_state=None,
            event_type="task.reconciliation_detected",
            message="Найден локальный активный run для задачи в Open",
            payload={
                "external_task_id": task.get("id"),
                "active_run_id": active_run.id,
                "active_run_status": active_run.status,
                "task_status": task_status,
            },
        )

    if task_status == "InProgress" and task_assignee == agent_email:
        return TaskSelectionPolicyDecision(
            reason="task_already_in_progress",
            dependencies_state="live_task",
            event_type="task.reconciliation_detected",
            message="Задача уже находится в InProgress у агента",
            payload={
                "external_task_id": task.get("id"),
                "active_run_id": active_run.id,
                "active_run_status": active_run.status,
                "task_status": task_status,
            },
        )

    return TaskSelectionPolicyDecision(
        reason=None,
        dependencies_state=None,
        event_type="task.reconciliation_detected",
        message="Найден локальный активный run с отличающимся live-состоянием задачи",
        payload={
            "external_task_id": task.get("id"),
            "active_run_id": active_run.id,
            "active_run_status": active_run.status,
            "task_status": task_status,
            "task_assignee_email": task_assignee,
        },
    )


def decide_run_start(*, task: JsonObject, agent_email: str) -> RunStartPolicyDecision:
    task_id = str(task.get("id", ""))
    task_status = str(task.get("status", ""))
    task_assignee = str(task.get("assignee_email") or "")

    if task_assignee and task_assignee != agent_email:
        return RunStartPolicyDecision(
            allowed=False,
            message=f"Task is assigned to another user: {task_assignee}",
            task_status=task_status,
            should_transition_to_in_progress=False,
            event_type="task.start_rejected",
            event_message="Run не может быть запущен: задача назначена другому пользователю",
            payload={
                "external_task_id": task_id,
                "task_status": task_status,
                "task_assignee_email": task_assignee,
            },
        )

    if task_status not in RUN_STARTABLE_TASK_STATUSES:
        return RunStartPolicyDecision(
            allowed=False,
            message=f"Task cannot be started from status: {task_status}",
            task_status=task_status,
            should_transition_to_in_progress=False,
            event_type="task.start_rejected",
            event_message="Run не может быть запущен из текущего статуса задачи",
            payload={"external_task_id": task_id, "task_status": task_status},
        )

    if task_status == "InProgress":
        return RunStartPolicyDecision(
            allowed=True,
            message="Task can be resumed from InProgress",
            task_status=task_status,
            should_transition_to_in_progress=False,
            event_type="task.reconciliation_detected",
            event_message="Run продолжает задачу, уже находящуюся в InProgress",
            payload={"external_task_id": task_id, "task_status": task_status},
        )

    return RunStartPolicyDecision(
        allowed=True,
        message="Task can be started from Open",
        task_status=task_status,
        should_transition_to_in_progress=True,
    )
