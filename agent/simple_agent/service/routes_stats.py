from typing import Annotated

from fastapi import APIRouter, Depends

from simple_agent.service.dependencies import get_repository
from simple_agent.service.schemas import stats_to_response
from simple_agent.storage import Repository


router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict:
    return stats_to_response(repository.get_stats())
