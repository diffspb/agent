from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from simple_agent.config import Settings
from simple_agent.service.app import create_app


@pytest.mark.anyio
async def test_healthcheck_returns_ok(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=tmp_path / "health.sqlite3"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "simple-agent",
        "environment": "local",
    }
