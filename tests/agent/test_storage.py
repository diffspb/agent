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
        "agent_ticks",
        "events",
        "runs",
        "task_candidates",
        "tool_calls",
    ]


def test_repository_creates_tick_candidate_run_event_and_stats(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "repository.sqlite3")
    database.initialize()
    repository = Repository(database)

    tick = repository.create_tick(
        source="manual",
        status="completed",
        trigger_task_id="PROJECT-1",
        payload={"reason": "test"},
    )
    candidate = repository.add_task_candidate(
        tick_id=tick.id,
        external_task_id="PROJECT-1",
        status="Open",
        assignee_email="agent@example.com",
        priority=10,
        dependencies_state="clear",
        decision="selected",
        metadata={"source": "test"},
    )
    run = repository.create_run(
        tick_id=tick.id,
        external_task_id="PROJECT-1",
        branch_name="PROJECT-1-test",
        status="running",
    )
    event = repository.add_event(
        run_id=run.id,
        type="run.started",
        message="Запуск начат",
        payload={"step": 1},
    )

    assert repository.get_tick(tick.id) == tick
    assert repository.list_task_candidates_for_tick(tick.id) == [candidate]
    assert repository.get_run(run.id) == run
    assert repository.list_events_for_run(run.id) == [event]

    stats = repository.get_stats()
    assert stats.ticks_total == 1
    assert stats.task_candidates_total == 1
    assert stats.runs_total == 1
    assert stats.runs_by_status == {"running": 1}
    assert stats.events_total == 1
    assert stats.tool_calls_total == 0


def test_database_resets_incompatible_stage_1_schema(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "old-stage-1.sqlite3")
    database.path.parent.mkdir(parents=True, exist_ok=True)

    with database.connect() as connection:
        connection.executescript(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                status TEXT NOT NULL,
                title TEXT NOT NULL
            );
            CREATE TABLE runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                status TEXT NOT NULL
            );
            INSERT INTO tasks (external_id, status, title)
            VALUES ('PROJECT-1', 'Open', 'Старая задача');
            INSERT INTO runs (task_id, status)
            VALUES (1, 'running');
            """
        )

    database.initialize()

    with database.connect() as connection:
        runs_columns = {
            str(column["name"])
            for column in connection.execute("PRAGMA table_info(runs)").fetchall()
        }
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])

    assert "external_task_id" in runs_columns
    assert "task_id" not in runs_columns
    assert version == 2
