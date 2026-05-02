from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Request

from simple_agent.agent import TaskSelectionService
from simple_agent.config import Settings
from simple_agent.service.dependencies import get_repository, get_settings
from simple_agent.service.schemas import task_selection_result_to_response
from simple_agent.storage import Repository
from simple_agent.tracker import TaskTrackerClient


router = APIRouter(tags=["agent"])


@router.post("/api/agent/tick")
async def run_agent_tick(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
    repository: Repository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    trigger_task_id = _task_id_from_payload(payload)
    result = await _run_tick(
        request=request,
        repository=repository,
        settings=settings,
        source="manual",
        trigger_task_id=trigger_task_id,
        payload=payload,
    )
    return task_selection_result_to_response(result)


@router.post("/api/webhooks/task-tracker")
async def receive_task_tracker_webhook(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
    repository: Repository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    trigger_task_id = _task_id_from_payload(payload)
    result = await _run_tick(
        request=request,
        repository=repository,
        settings=settings,
        source="webhook",
        trigger_task_id=trigger_task_id,
        payload=payload,
    )
    return task_selection_result_to_response(result)


async def _run_tick(
    *,
    request: Request,
    repository: Repository,
    settings: Settings,
    source: str,
    trigger_task_id: str | None,
    payload: dict[str, Any],
) -> Any:
    tracker_factory = request.app.state.task_tracker_factory
    tracker: TaskTrackerClient = tracker_factory()
    service = TaskSelectionService(
        repository=repository,
        tracker=tracker,
        agent_email=settings.agent_email,
    )
    return await service.run_tick(
        source=source,
        trigger_task_id=trigger_task_id,
        payload=payload,
    )


def _task_id_from_payload(payload: dict[str, Any]) -> str | None:
    for key in ("task_id", "id", "external_task_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    task = payload.get("task")
    if isinstance(task, dict):
        value = task.get("id")
        if isinstance(value, str) and value:
            return value
    return None
