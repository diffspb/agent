from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from simple_agent.storage.models import (
    AgentTickRecord,
    EventRecord,
    RunRecord,
    TaskCandidateRecord,
    ToolCallRecord,
)
from simple_agent.storage.repository import Repository


class ObservabilitySink(Protocol):
    def create_tick(
        self,
        *,
        source: str,
        status: str = "started",
        trigger_task_id: str | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AgentTickRecord:
        raise NotImplementedError

    def complete_tick(
        self,
        tick_id: int,
        *,
        status: str,
        error: str | None = None,
    ) -> AgentTickRecord:
        raise NotImplementedError

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
        raise NotImplementedError

    def list_task_candidates_for_tick(self, tick_id: int) -> list[TaskCandidateRecord]:
        raise NotImplementedError

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
        raise NotImplementedError

    def update_run(
        self,
        run_id: int,
        *,
        status: str,
        summary: str | None = None,
        error: str | None = None,
        finished: bool = False,
    ) -> RunRecord:
        raise NotImplementedError

    def add_event(
        self,
        *,
        type: str,
        message: str,
        tick_id: int | None = None,
        run_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        raise NotImplementedError

    def create_tool_call(
        self,
        *,
        run_id: int,
        tool_name: str,
        input: dict[str, Any] | None = None,
        status: str = "running",
    ) -> ToolCallRecord:
        raise NotImplementedError

    def complete_tool_call(
        self,
        tool_call_id: int,
        *,
        status: str,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ToolCallRecord:
        raise NotImplementedError

    def list_tool_calls_for_run(
        self,
        run_id: int,
        *,
        limit: int = 100,
    ) -> list[ToolCallRecord]:
        raise NotImplementedError

    def get_active_run_for_task(self, external_task_id: str) -> RunRecord | None:
        raise NotImplementedError


@dataclass(frozen=True)
class SqliteObservabilitySink:
    repository: Repository

    def create_tick(
        self,
        *,
        source: str,
        status: str = "started",
        trigger_task_id: str | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AgentTickRecord:
        return self.repository.create_tick(
            source=source,
            status=status,
            trigger_task_id=trigger_task_id,
            payload=payload,
            error=error,
        )

    def complete_tick(
        self,
        tick_id: int,
        *,
        status: str,
        error: str | None = None,
    ) -> AgentTickRecord:
        return self.repository.complete_tick(
            tick_id,
            status=status,
            error=error,
        )

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
        return self.repository.add_task_candidate(
            tick_id=tick_id,
            external_task_id=external_task_id,
            status=status,
            dependencies_state=dependencies_state,
            decision=decision,
            assignee_email=assignee_email,
            priority=priority,
            reason=reason,
            metadata=metadata,
        )

    def list_task_candidates_for_tick(self, tick_id: int) -> list[TaskCandidateRecord]:
        return self.repository.list_task_candidates_for_tick(tick_id)

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
        return self.repository.create_run(
            external_task_id=external_task_id,
            tick_id=tick_id,
            branch_name=branch_name,
            status=status,
            summary=summary,
            error=error,
        )

    def update_run(
        self,
        run_id: int,
        *,
        status: str,
        summary: str | None = None,
        error: str | None = None,
        finished: bool = False,
    ) -> RunRecord:
        return self.repository.update_run(
            run_id,
            status=status,
            summary=summary,
            error=error,
            finished=finished,
        )

    def add_event(
        self,
        *,
        type: str,
        message: str,
        tick_id: int | None = None,
        run_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        return self.repository.add_event(
            type=type,
            message=message,
            tick_id=tick_id,
            run_id=run_id,
            payload=payload,
        )

    def create_tool_call(
        self,
        *,
        run_id: int,
        tool_name: str,
        input: dict[str, Any] | None = None,
        status: str = "running",
    ) -> ToolCallRecord:
        return self.repository.create_tool_call(
            run_id=run_id,
            tool_name=tool_name,
            input=input,
            status=status,
        )

    def complete_tool_call(
        self,
        tool_call_id: int,
        *,
        status: str,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ToolCallRecord:
        return self.repository.complete_tool_call(
            tool_call_id,
            status=status,
            output=output,
            error=error,
        )

    def list_tool_calls_for_run(
        self,
        run_id: int,
        *,
        limit: int = 100,
    ) -> list[ToolCallRecord]:
        return self.repository.list_tool_calls_for_run(run_id, limit=limit)

    def get_active_run_for_task(self, external_task_id: str) -> RunRecord | None:
        return self.repository.get_active_run_for_task(external_task_id)
