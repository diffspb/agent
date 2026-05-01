from pathlib import Path

from simple_agent.storage import Repository, SqliteDatabase


def test_database_initializes_expected_tables(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "storage.sqlite3")
    database.initialize()

    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    assert [row["name"] for row in rows] == [
        "agent_notes",
        "events",
        "runs",
        "tasks",
        "tool_calls",
    ]


def test_repository_creates_task_run_event_and_stats(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "repository.sqlite3")
    database.initialize()
    repository = Repository(database)

    task = repository.create_task(
        external_id="PROJECT-1",
        title="Проверить хранилище",
        status="Open",
        assignee_email="agent@example.com",
        metadata={"source": "test"},
    )
    run = repository.create_run(task_id=task.id, status="running")
    event = repository.add_event(
        run_id=run.id,
        type="run.started",
        message="Запуск начат",
        payload={"step": 1},
    )

    assert repository.get_task(task.id) == task
    assert repository.get_run(run.id) == run
    assert repository.list_events_for_run(run.id) == [event]

    stats = repository.get_stats()
    assert stats.tasks_total == 1
    assert stats.runs_total == 1
    assert stats.runs_by_status == {"running": 1}
    assert stats.events_total == 1
    assert stats.tool_calls_total == 0
    assert stats.agent_notes_total == 0
