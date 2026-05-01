from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from simple_agent.service.dependencies import get_repository
from simple_agent.service.schemas import event_to_response, run_to_response
from simple_agent.storage import Repository


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
