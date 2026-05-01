from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from simple_agent.config import Settings
from simple_agent.service.app import create_app


@pytest.mark.anyio
async def test_observability_api_returns_tasks_runs_events_and_stats(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(database_path=tmp_path / "api.sqlite3"))
    repository = app.state.repository
    task = repository.create_task(
        external_id="PROJECT-7",
        title="Подготовить наблюдаемость",
        status="InProgress",
        assignee_email="agent@example.com",
    )
    run = repository.create_run(task_id=task.id, status="running")
    repository.add_event(
        run_id=run.id,
        type="run.started",
        message="Запуск создан",
        payload={"task_id": task.id},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        tasks_response = await client.get("/api/tasks")
        task_response = await client.get(f"/api/tasks/{task.id}")
        runs_response = await client.get("/api/runs")
        run_response = await client.get(f"/api/runs/{run.id}")
        events_response = await client.get(f"/api/runs/{run.id}/events")
        stats_response = await client.get("/api/stats")

    assert tasks_response.status_code == 200
    assert tasks_response.json()[0]["external_id"] == "PROJECT-7"

    assert task_response.status_code == 200
    assert task_response.json()["title"] == "Подготовить наблюдаемость"

    assert runs_response.status_code == 200
    assert runs_response.json()[0]["task_id"] == task.id

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "running"

    assert events_response.status_code == 200
    assert events_response.json()[0]["type"] == "run.started"

    assert stats_response.status_code == 200
    assert stats_response.json()["runs_by_status"] == {"running": 1}


@pytest.mark.anyio
async def test_observability_api_returns_404_for_missing_records(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=tmp_path / "missing.sqlite3"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        task_response = await client.get("/api/tasks/999")
        run_response = await client.get("/api/runs/999")
        events_response = await client.get("/api/runs/999/events")

    assert task_response.status_code == 404
    assert run_response.status_code == 404
    assert events_response.status_code == 404
