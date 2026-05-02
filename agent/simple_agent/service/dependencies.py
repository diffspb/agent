from fastapi import Request

from simple_agent.config import Settings
from simple_agent.storage import Repository


async def get_repository(request: Request) -> Repository:
    return request.app.state.repository


async def get_settings(request: Request) -> Settings:
    return request.app.state.settings
