from datetime import datetime
from typing import Any

from simple_agent.storage.models import (
    AgentTickRecord,
    EventRecord,
    RunRecord,
    StatsRecord,
    TaskCandidateRecord,
)


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def tick_to_response(tick: AgentTickRecord) -> dict[str, Any]:
    return {
        "id": tick.id,
        "source": tick.source,
        "status": tick.status,
        "trigger_task_id": tick.trigger_task_id,
        "payload": tick.payload,
        "started_at": _format_datetime(tick.started_at),
        "finished_at": _format_datetime(tick.finished_at),
        "error": tick.error,
    }


def task_candidate_to_response(candidate: TaskCandidateRecord) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "tick_id": candidate.tick_id,
        "external_task_id": candidate.external_task_id,
        "status": candidate.status,
        "assignee_email": candidate.assignee_email,
        "priority": candidate.priority,
        "dependencies_state": candidate.dependencies_state,
        "decision": candidate.decision,
        "reason": candidate.reason,
        "metadata": candidate.metadata,
        "created_at": _format_datetime(candidate.created_at),
    }


def run_to_response(run: RunRecord) -> dict[str, Any]:
    return {
        "id": run.id,
        "tick_id": run.tick_id,
        "external_task_id": run.external_task_id,
        "branch_name": run.branch_name,
        "status": run.status,
        "started_at": _format_datetime(run.started_at),
        "finished_at": _format_datetime(run.finished_at),
        "summary": run.summary,
        "error": run.error,
        "created_at": _format_datetime(run.created_at),
        "updated_at": _format_datetime(run.updated_at),
    }


def event_to_response(event: EventRecord) -> dict[str, Any]:
    return {
        "id": event.id,
        "tick_id": event.tick_id,
        "run_id": event.run_id,
        "type": event.type,
        "message": event.message,
        "payload": event.payload,
        "created_at": _format_datetime(event.created_at),
    }


def stats_to_response(stats: StatsRecord) -> dict[str, Any]:
    return {
        "ticks_total": stats.ticks_total,
        "task_candidates_total": stats.task_candidates_total,
        "runs_total": stats.runs_total,
        "runs_by_status": stats.runs_by_status,
        "events_total": stats.events_total,
        "tool_calls_total": stats.tool_calls_total,
    }
