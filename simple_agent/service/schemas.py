from datetime import datetime
from typing import Any

from simple_agent.storage.models import EventRecord, RunRecord, StatsRecord, TaskRecord


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def task_to_response(task: TaskRecord) -> dict[str, Any]:
    return {
        "id": task.id,
        "external_id": task.external_id,
        "type": task.type,
        "status": task.status,
        "title": task.title,
        "author_email": task.author_email,
        "assignee_email": task.assignee_email,
        "description": task.description,
        "metadata": task.metadata,
        "created_at": _format_datetime(task.created_at),
        "updated_at": _format_datetime(task.updated_at),
    }


def run_to_response(run: RunRecord) -> dict[str, Any]:
    return {
        "id": run.id,
        "task_id": run.task_id,
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
        "run_id": event.run_id,
        "type": event.type,
        "message": event.message,
        "payload": event.payload,
        "created_at": _format_datetime(event.created_at),
    }


def stats_to_response(stats: StatsRecord) -> dict[str, Any]:
    return {
        "tasks_total": stats.tasks_total,
        "runs_total": stats.runs_total,
        "runs_by_status": stats.runs_by_status,
        "events_total": stats.events_total,
        "tool_calls_total": stats.tool_calls_total,
        "agent_notes_total": stats.agent_notes_total,
    }
