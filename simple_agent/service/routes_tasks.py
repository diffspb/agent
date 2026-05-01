from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from simple_agent.service.dependencies import get_repository
from simple_agent.service.schemas import task_to_response
from simple_agent.storage import Repository


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    return [task_to_response(task) for task in repository.list_tasks()]


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict:
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)
