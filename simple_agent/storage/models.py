from dataclasses import dataclass
from datetime import datetime
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class TaskRecord:
    id: int
    external_id: str | None
    type: str
    status: str
    title: str
    author_email: str | None
    assignee_email: str | None
    description: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RunRecord:
    id: int
    task_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    summary: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EventRecord:
    id: int
    run_id: int
    type: str
    message: str
    payload: JsonObject
    created_at: datetime


@dataclass(frozen=True)
class ToolCallRecord:
    id: int
    run_id: int
    tool_name: str
    status: str
    input: JsonObject
    output: JsonObject | None
    error: str | None
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True)
class AgentNoteRecord:
    id: int
    task_id: int | None
    run_id: int | None
    key: str
    value: str
    created_at: datetime


@dataclass(frozen=True)
class StatsRecord:
    tasks_total: int
    runs_total: int
    runs_by_status: dict[str, int]
    events_total: int
    tool_calls_total: int
    agent_notes_total: int
