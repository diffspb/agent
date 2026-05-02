from datetime import datetime
from typing import Any

from simple_agent.agent import TaskSelectionResult
from simple_agent.agent.artifacts import Artifact
from simple_agent.storage.models import (
    AgentTickRecord,
    EventRecord,
    RunRecord,
    StatsRecord,
    TaskCandidateRecord,
    ToolCallRecord,
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


def tool_call_to_response(tool_call: ToolCallRecord) -> dict[str, Any]:
    return {
        "id": tool_call.id,
        "run_id": tool_call.run_id,
        "tool_name": tool_call.tool_name,
        "status": tool_call.status,
        "input": tool_call.input,
        "output": tool_call.output,
        "error": tool_call.error,
        "started_at": _format_datetime(tool_call.started_at),
        "finished_at": _format_datetime(tool_call.finished_at),
    }


def artifact_to_response(artifact: Artifact) -> dict[str, Any]:
    return {
        "path": artifact.path,
        "name": artifact.name,
        "bytes": artifact.bytes,
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


def task_selection_result_to_response(result: TaskSelectionResult) -> dict[str, Any]:
    return {
        "tick": tick_to_response(result.tick),
        "selected_run": (
            run_to_response(result.selected_run) if result.selected_run is not None else None
        ),
        "selected_task": result.selected_task,
        "candidates": [
            task_candidate_to_response(candidate) for candidate in result.candidates
        ],
    }
