from dataclasses import dataclass
from datetime import datetime
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class AgentTickRecord:
    id: int
    source: str
    status: str
    trigger_task_id: str | None
    payload: JsonObject
    started_at: datetime
    finished_at: datetime | None
    error: str | None


@dataclass(frozen=True)
class TaskCandidateRecord:
    id: int
    tick_id: int
    external_task_id: str
    status: str
    assignee_email: str | None
    priority: int | None
    dependencies_state: str
    decision: str
    reason: str | None
    metadata: JsonObject
    created_at: datetime


@dataclass(frozen=True)
class RunRecord:
    id: int
    tick_id: int | None
    external_task_id: str
    branch_name: str | None
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
    tick_id: int | None
    run_id: int | None
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
class StatsRecord:
    ticks_total: int
    task_candidates_total: int
    runs_total: int
    runs_by_status: dict[str, int]
    events_total: int
    tool_calls_total: int
