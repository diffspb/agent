from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from simple_agent.service.dependencies import get_repository
from simple_agent.service.schemas import task_candidate_to_response, tick_to_response
from simple_agent.storage import Repository


router = APIRouter(prefix="/api/ticks", tags=["ticks"])


@router.get("")
async def list_ticks(
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    return [tick_to_response(tick) for tick in repository.list_ticks()]


@router.get("/{tick_id}")
async def get_tick(
    tick_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict:
    tick = repository.get_tick(tick_id)
    if tick is None:
        raise HTTPException(status_code=404, detail="Tick not found")
    return tick_to_response(tick)


@router.get("/{tick_id}/candidates")
async def list_tick_candidates(
    tick_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    tick = repository.get_tick(tick_id)
    if tick is None:
        raise HTTPException(status_code=404, detail="Tick not found")
    return [
        task_candidate_to_response(candidate)
        for candidate in repository.list_task_candidates_for_tick(tick_id)
    ]
