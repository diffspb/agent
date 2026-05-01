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


@pytest.mark.anyio
async def test_cors_allows_local_vite_ports(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=tmp_path / "cors.sqlite3"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/tasks",
            headers={
                "Origin": "http://127.0.0.1:5174",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
