from fastapi import Request

from simple_agent.storage import Repository


async def get_repository(request: Request) -> Repository:
    return request.app.state.repository
