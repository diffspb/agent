from __future__ import annotations

from datetime import datetime
import json
import sqlite3
from typing import Any

from simple_agent.storage.models import (
    AgentTickRecord,
    EventRecord,
    RunRecord,
    StatsRecord,
    TaskCandidateRecord,
)
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

    def create_tick(
        self,
        *,
        source: str,
        status: str = "started",
        trigger_task_id: str | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AgentTickRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_ticks (source, status, trigger_task_id, payload_json, error)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source, status, trigger_task_id, _json_dumps(payload), error),
            )
            tick_id = int(cursor.lastrowid)

        tick = self.get_tick(tick_id)
        if tick is None:
            raise RuntimeError("Created tick was not found")
        return tick

    def list_ticks(self, *, limit: int = 50, offset: int = 0) -> list[AgentTickRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM agent_ticks
                ORDER BY started_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [_tick_from_row(row) for row in rows]

    def get_tick(self, tick_id: int) -> AgentTickRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_ticks WHERE id = ?",
                (tick_id,),
            ).fetchone()
        return _tick_from_row(row) if row else None

    def complete_tick(
        self,
        tick_id: int,
        *,
        status: str,
        error: str | None = None,
    ) -> AgentTickRecord:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE agent_ticks
                SET status = ?,
                    finished_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                    error = ?
                WHERE id = ?
                """,
                (status, error, tick_id),
            )

        tick = self.get_tick(tick_id)
        if tick is None:
            raise RuntimeError("Updated tick was not found")
        return tick

    def add_task_candidate(
        self,
        *,
        tick_id: int,
        external_task_id: str,
        status: str,
        dependencies_state: str,
        decision: str,
        assignee_email: str | None = None,
        priority: int | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskCandidateRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO task_candidates (
                    tick_id, external_task_id, status, assignee_email, priority,
                    dependencies_state, decision, reason, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tick_id,
                    external_task_id,
                    status,
                    assignee_email,
                    priority,
                    dependencies_state,
                    decision,
                    reason,
                    _json_dumps(metadata),
                ),
            )
            candidate_id = int(cursor.lastrowid)

        candidate = self.get_task_candidate(candidate_id)
        if candidate is None:
            raise RuntimeError("Created task candidate was not found")
        return candidate

    def get_task_candidate(self, candidate_id: int) -> TaskCandidateRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM task_candidates WHERE id = ?",
                (candidate_id,),
            ).fetchone()
        return _task_candidate_from_row(row) if row else None

    def list_task_candidates_for_tick(self, tick_id: int) -> list[TaskCandidateRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM task_candidates
                WHERE tick_id = ?
                ORDER BY id ASC
                """,
                (tick_id,),
            ).fetchall()
        return [_task_candidate_from_row(row) for row in rows]

    def create_run(
        self,
        *,
        external_task_id: str,
        tick_id: int | None = None,
        branch_name: str | None = None,
        status: str = "queued",
        summary: str | None = None,
        error: str | None = None,
    ) -> RunRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO runs (
                    tick_id, external_task_id, branch_name, status, summary, error
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tick_id, external_task_id, branch_name, status, summary, error),
            )
            run_id = int(cursor.lastrowid)

        run = self.get_run(run_id)
        if run is None:
            raise RuntimeError("Created run was not found")
        return run

    def list_runs(self, *, limit: int = 50, offset: int = 0) -> list[RunRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM runs
                ORDER BY started_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [_run_from_row(row) for row in rows]

    def get_run(self, run_id: int) -> RunRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _run_from_row(row) if row else None

    def get_active_run_for_task(self, external_task_id: str) -> RunRecord | None:
        active_statuses = ("queued", "running")
        placeholders = ", ".join("?" for _ in active_statuses)
        with self.database.connect() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM runs
                WHERE external_task_id = ?
                  AND status IN ({placeholders})
                ORDER BY started_at DESC, id DESC
                LIMIT 1
                """,
                (external_task_id, *active_statuses),
            ).fetchone()
        return _run_from_row(row) if row else None

    def add_event(
        self,
        *,
        type: str,
        message: str,
        tick_id: int | None = None,
        run_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (tick_id, run_id, type, message, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tick_id, run_id, type, message, _json_dumps(payload)),
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

    def list_events_for_run(self, run_id: int, *, limit: int = 100) -> list[EventRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM events
                WHERE run_id = ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def get_stats(self) -> StatsRecord:
        with self.database.connect() as connection:
            ticks_total = _count(connection, "agent_ticks")
            task_candidates_total = _count(connection, "task_candidates")
            runs_total = _count(connection, "runs")
            events_total = _count(connection, "events")
            tool_calls_total = _count(connection, "tool_calls")
            status_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM runs GROUP BY status ORDER BY status"
            ).fetchall()

        return StatsRecord(
            ticks_total=ticks_total,
            task_candidates_total=task_candidates_total,
            runs_total=runs_total,
            runs_by_status={str(row["status"]): int(row["count"]) for row in status_rows},
            events_total=events_total,
            tool_calls_total=tool_calls_total,
        )


def _count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])


def _tick_from_row(row: sqlite3.Row) -> AgentTickRecord:
    return AgentTickRecord(
        id=int(row["id"]),
        source=str(row["source"]),
        status=str(row["status"]),
        trigger_task_id=row["trigger_task_id"],
        payload=_json_loads(row["payload_json"]),
        started_at=_parse_datetime(row["started_at"]),
        finished_at=_parse_datetime(row["finished_at"]),
        error=row["error"],
    )


def _task_candidate_from_row(row: sqlite3.Row) -> TaskCandidateRecord:
    return TaskCandidateRecord(
        id=int(row["id"]),
        tick_id=int(row["tick_id"]),
        external_task_id=str(row["external_task_id"]),
        status=str(row["status"]),
        assignee_email=row["assignee_email"],
        priority=int(row["priority"]) if row["priority"] is not None else None,
        dependencies_state=str(row["dependencies_state"]),
        decision=str(row["decision"]),
        reason=row["reason"],
        metadata=_json_loads(row["metadata_json"]),
        created_at=_parse_datetime(row["created_at"]),
    )


def _run_from_row(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        id=int(row["id"]),
        tick_id=int(row["tick_id"]) if row["tick_id"] is not None else None,
        external_task_id=str(row["external_task_id"]),
        branch_name=row["branch_name"],
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
        tick_id=int(row["tick_id"]) if row["tick_id"] is not None else None,
        run_id=int(row["run_id"]) if row["run_id"] is not None else None,
        type=str(row["type"]),
        message=str(row["message"]),
        payload=_json_loads(row["payload_json"]),
        created_at=_parse_datetime(row["created_at"]),
    )
