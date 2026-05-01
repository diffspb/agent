from __future__ import annotations

from datetime import datetime
import json
import sqlite3
from typing import Any

from simple_agent.storage.models import EventRecord, RunRecord, StatsRecord, TaskRecord
from simple_agent.storage.sqlite import SqliteDatabase


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.removesuffix("Z") + "+00:00"
    return datetime.fromisoformat(normalized)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object")
    return payload


def _json_dumps(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


class Repository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def create_task(
        self,
        *,
        title: str,
        status: str = "Todo",
        type: str = "task",
        external_id: str | None = None,
        author_email: str | None = None,
        assignee_email: str | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> TaskRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (
                    external_id, type, status, title, author_email,
                    assignee_email, description, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    external_id,
                    type,
                    status,
                    title,
                    author_email,
                    assignee_email,
                    description,
                    _json_dumps(metadata),
                ),
            )
            task_id = int(cursor.lastrowid)

        task = self.get_task(task_id)
        if task is None:
            raise RuntimeError("Created task was not found")
        return task

    def list_tasks(self) -> list[TaskRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_task_from_row(row) for row in rows]

    def get_task(self, task_id: int) -> TaskRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return _task_from_row(row) if row else None

    def create_run(
        self,
        *,
        task_id: int,
        status: str = "queued",
        summary: str | None = None,
        error: str | None = None,
    ) -> RunRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO runs (task_id, status, summary, error)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, status, summary, error),
            )
            run_id = int(cursor.lastrowid)

        run = self.get_run(run_id)
        if run is None:
            raise RuntimeError("Created run was not found")
        return run

    def list_runs(self) -> list[RunRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY started_at DESC, id DESC"
            ).fetchall()
        return [_run_from_row(row) for row in rows]

    def get_run(self, run_id: int) -> RunRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _run_from_row(row) if row else None

    def add_event(
        self,
        *,
        run_id: int,
        type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (run_id, type, message, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, type, message, _json_dumps(payload)),
            )
            event_id = int(cursor.lastrowid)

        event = self.get_event(event_id)
        if event is None:
            raise RuntimeError("Created event was not found")
        return event

    def get_event(self, event_id: int) -> EventRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return _event_from_row(row) if row else None

    def list_events_for_run(self, run_id: int) -> list[EventRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY created_at ASC, id ASC",
                (run_id,),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def get_stats(self) -> StatsRecord:
        with self.database.connect() as connection:
            tasks_total = _count(connection, "tasks")
            runs_total = _count(connection, "runs")
            events_total = _count(connection, "events")
            tool_calls_total = _count(connection, "tool_calls")
            agent_notes_total = _count(connection, "agent_notes")
            status_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM runs GROUP BY status ORDER BY status"
            ).fetchall()

        return StatsRecord(
            tasks_total=tasks_total,
            runs_total=runs_total,
            runs_by_status={str(row["status"]): int(row["count"]) for row in status_rows},
            events_total=events_total,
            tool_calls_total=tool_calls_total,
            agent_notes_total=agent_notes_total,
        )


def _count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])


def _task_from_row(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(
        id=int(row["id"]),
        external_id=row["external_id"],
        type=str(row["type"]),
        status=str(row["status"]),
        title=str(row["title"]),
        author_email=row["author_email"],
        assignee_email=row["assignee_email"],
        description=str(row["description"]),
        metadata=_json_loads(row["metadata_json"]),
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
    )


def _run_from_row(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        id=int(row["id"]),
        task_id=int(row["task_id"]),
        status=str(row["status"]),
        started_at=_parse_datetime(row["started_at"]),
        finished_at=_parse_datetime(row["finished_at"]),
        summary=row["summary"],
        error=row["error"],
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
    )


def _event_from_row(row: sqlite3.Row) -> EventRecord:
    return EventRecord(
        id=int(row["id"]),
        run_id=int(row["run_id"]),
        type=str(row["type"]),
        message=str(row["message"]),
        payload=_json_loads(row["payload_json"]),
        created_at=_parse_datetime(row["created_at"]),
    )
