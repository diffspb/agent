from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from simple_agent.agent import AgentController, PrimitiveAgentRuntime, RunNotFoundError
from simple_agent.config import Settings
from simple_agent.service.dependencies import get_repository, get_settings
from simple_agent.service.schemas import event_to_response, run_to_response
from simple_agent.storage import Repository
from simple_agent.tracker import TaskTrackerClient


router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    return [run_to_response(run) for run in repository.list_runs()]


@router.get("/{run_id}")
async def get_run(
    run_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_to_response(run)


@router.get("/{run_id}/events")
async def list_run_events(
    run_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return [event_to_response(event) for event in repository.list_events_for_run(run_id)]


@router.post("/{run_id}/start")
async def start_run(
    run_id: int,
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    controller = _create_controller(
        request=request,
        repository=repository,
        settings=settings,
    )
    try:
        result = await controller.start_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return run_to_response(result.run)


@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: int,
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    controller = _create_controller(
        request=request,
        repository=repository,
        settings=settings,
    )
    try:
        result = await controller.cancel_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return run_to_response(result.run)


def _create_controller(
    *,
    request: Request,
    repository: Repository,
    settings: Settings,
) -> AgentController:
    tracker_factory = request.app.state.task_tracker_factory
    tracker: TaskTrackerClient = tracker_factory()
    runtime = PrimitiveAgentRuntime(
        repository=repository,
        tracker=tracker,
        agent_email=settings.agent_email,
    )
    return AgentController(repository=repository, runtime=runtime)
