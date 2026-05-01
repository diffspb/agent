from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from simple_agent.config import Settings
from simple_agent.service.app import create_app


@pytest.mark.anyio
async def test_observability_api_returns_ticks_runs_events_and_stats(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(database_path=tmp_path / "api.sqlite3"))
    repository = app.state.repository
    tick = repository.create_tick(
        source="webhook",
        status="completed",
        trigger_task_id="PROJECT-7",
        payload={"event": "task.updated"},
    )
    repository.add_task_candidate(
        tick_id=tick.id,
        external_task_id="PROJECT-7",
        status="Open",
        assignee_email="agent@example.com",
        priority=100,
        dependencies_state="clear",
        decision="selected",
        reason="Самый высокий приоритет среди разблокированных задач",
    )
    run = repository.create_run(
        tick_id=tick.id,
        external_task_id="PROJECT-7",
        branch_name="PROJECT-7-storage",
        status="running",
    )
    repository.add_event(
        run_id=run.id,
        type="run.started",
        message="Запуск создан",
        payload={"external_task_id": "PROJECT-7"},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ticks_response = await client.get("/api/ticks")
        tick_response = await client.get(f"/api/ticks/{tick.id}")
        candidates_response = await client.get(f"/api/ticks/{tick.id}/candidates")
        runs_response = await client.get("/api/runs")
        run_response = await client.get(f"/api/runs/{run.id}")
        events_response = await client.get(f"/api/runs/{run.id}/events")
        stats_response = await client.get("/api/stats")

    assert ticks_response.status_code == 200
    assert ticks_response.json()[0]["trigger_task_id"] == "PROJECT-7"

    assert tick_response.status_code == 200
    assert tick_response.json()["source"] == "webhook"

    assert candidates_response.status_code == 200
    assert candidates_response.json()[0]["decision"] == "selected"

    assert runs_response.status_code == 200
    assert runs_response.json()[0]["external_task_id"] == "PROJECT-7"

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "running"

    assert events_response.status_code == 200
    assert events_response.json()[0]["type"] == "run.started"

    assert stats_response.status_code == 200
    assert stats_response.json()["ticks_total"] == 1
    assert stats_response.json()["task_candidates_total"] == 1
    assert stats_response.json()["runs_by_status"] == {"running": 1}


@pytest.mark.anyio
async def test_observability_api_returns_404_for_missing_records(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=tmp_path / "missing.sqlite3"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        tick_response = await client.get("/api/ticks/999")
        candidates_response = await client.get("/api/ticks/999/candidates")
        run_response = await client.get("/api/runs/999")
        events_response = await client.get("/api/runs/999/events")

    assert tick_response.status_code == 404
    assert candidates_response.status_code == 404
    assert run_response.status_code == 404
    assert events_response.status_code == 404
