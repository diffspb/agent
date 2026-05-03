from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from simple_agent.agent.artifacts import (
    build_workspace_diff,
    capture_repo_snapshot,
    write_artifact,
)
from simple_agent.agent.policies import decide_run_start
from simple_agent.agent.prompts import SYSTEM_PROMPT, build_task_prompt
from simple_agent.llm import LLMClient, LLMToolCall
from simple_agent.storage.models import RunRecord
from simple_agent.storage import ObservabilitySink
from simple_agent.tools import ToolContext, ToolError, ToolRegistry
from simple_agent.tracker.client import TaskTrackerClient
from simple_agent.workspace import Workspace, WorkspaceManager


RUN_STARTABLE_STATUSES = {"queued"}
RUN_CANCELABLE_STATUSES = {"queued", "running"}


@dataclass(frozen=True)
class RuntimeResult:
    run: RunRecord


@dataclass(frozen=True)
class RuntimeExecutionContext:
    run: RunRecord
    task: dict[str, Any]
    workspace: Workspace
    tool_context: ToolContext


@dataclass(frozen=True)
class CompletionReport:
    outcome: str
    final_comment: str
    run_summary: str
    task_status: str = "Done"
    artifacts: list[str] | None = None
    checks_summary: str | None = None


class TaskLifecycleRuntime:
    start_summary = "Runtime начал выполнение"
    start_message = "Runtime начал выполнение задачи"
    start_comment = "Агент начал выполнение задачи."
    failed_summary = "Runtime завершился с ошибкой"

    def __init__(
        self,
        *,
        observability: ObservabilitySink,
        tracker: TaskTrackerClient,
        agent_email: str,
        workspace_manager: WorkspaceManager,
        tool_registry: ToolRegistry,
        command_timeout_seconds: float,
        output_max_bytes: int,
        file_read_max_bytes: int,
    ) -> None:
        self.observability = observability
        self.tracker = tracker
        self.agent_email = agent_email
        self.workspace_manager = workspace_manager
        self.tool_registry = tool_registry
        self.command_timeout_seconds = command_timeout_seconds
        self.output_max_bytes = output_max_bytes
        self.file_read_max_bytes = file_read_max_bytes

    async def start_run(self, run: RunRecord) -> RuntimeResult:
        if run.status not in RUN_STARTABLE_STATUSES:
            raise ValueError(f"Run cannot be started from status: {run.status}")

        try:
            task = await self.tracker.tasks_get(run.external_task_id)
        except Exception as exc:
            await self._try_add_failure_comment(run, str(exc))
            failed = self.observability.update_run(
                run.id,
                status="failed",
                summary=self.failed_summary,
                error=str(exc),
                finished=True,
            )
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="run.failed",
                message="Run завершился с ошибкой",
                payload={"error": str(exc)},
            )
            return RuntimeResult(run=failed)

        decision = decide_run_start(task=task, agent_email=self.agent_email)
        if decision.event_type is not None and decision.event_message is not None:
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type=decision.event_type,
                message=decision.event_message,
                payload=decision.payload,
            )
        if not decision.allowed:
            raise ValueError(decision.message)

        running = self.observability.update_run(
            run.id,
            status="running",
            summary=self.start_summary,
        )
        self.observability.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="run.started",
            message=self.start_message,
            payload={"external_task_id": run.external_task_id},
        )

        try:
            context = await self._prepare_context(running, task=task)
            report = await self.execute(context)
            await self._complete_task(context, report)
            completed = self.observability.update_run(
                run.id,
                status="completed",
                summary=report.run_summary,
                error=None,
                finished=True,
            )
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="run.completed",
                message="Run завершен успешно",
                payload={"outcome": report.outcome},
            )
            return RuntimeResult(run=completed)
        except Exception as exc:
            await self._try_add_failure_comment(run, str(exc))
            failed = self.observability.update_run(
                run.id,
                status="failed",
                summary=self.failed_summary,
                error=str(exc),
                finished=True,
            )
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="run.failed",
                message="Run завершился с ошибкой",
                payload={"error": str(exc)},
            )
            return RuntimeResult(run=failed)

    async def cancel_run(self, run: RunRecord) -> RuntimeResult:
        if run.status not in RUN_CANCELABLE_STATUSES:
            raise ValueError(f"Run cannot be cancelled from status: {run.status}")

        cancelled = self.observability.update_run(
            run.id,
            status="cancelled",
            summary="Run отменен пользователем",
            error=None,
            finished=True,
        )
        self.observability.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="run.cancelled",
            message="Run отменен пользователем",
            payload={"external_task_id": run.external_task_id},
        )
        return RuntimeResult(run=cancelled)

    async def execute(self, context: RuntimeExecutionContext) -> CompletionReport:
        raise NotImplementedError

    async def _prepare_context(
        self,
        run: RunRecord,
        *,
        task: dict[str, Any],
    ) -> RuntimeExecutionContext:
        self.observability.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="task.loaded",
            message="Задача загружена из таск-трекера",
            payload={"external_task_id": task.get("id")},
        )

        workspace = self.workspace_manager.prepare_for_run(run)
        current_run = run
        branch_name = self.workspace_manager.branch_name_for_run(run)
        if run.branch_name != branch_name:
            current_run = self.observability.update_run(
                run.id,
                status=run.status,
                branch_name=branch_name,
            )
        self.observability.add_event(
            run_id=current_run.id,
            tick_id=current_run.tick_id,
            type="workspace.prepared",
            message="Рабочее пространство подготовлено",
            payload={"workspace_root": str(workspace.root), "branch_name": branch_name},
        )

        if str(task.get("status")) != "InProgress":
            await self.tracker.tasks_update(run.external_task_id, {"status": "InProgress"})
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.status_changed",
                message="Задача переведена в InProgress",
                payload={"status": "InProgress"},
            )

        await self.tracker.comments_add(
            task_id=run.external_task_id,
            author_email=self.agent_email,
            body=self.start_comment,
        )
        self.observability.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="task.comment_added",
            message="Добавлен комментарий о начале работы",
        )

        tool_context = ToolContext(
            workspace=workspace,
            command_timeout_seconds=self.command_timeout_seconds,
            output_max_bytes=self.output_max_bytes,
            file_read_max_bytes=self.file_read_max_bytes,
        )
        return RuntimeExecutionContext(
            run=current_run,
            task=task,
            workspace=workspace,
            tool_context=tool_context,
        )

    async def _complete_task(
        self,
        context: RuntimeExecutionContext,
        report: CompletionReport,
    ) -> None:
        await self.tracker.comments_add(
            task_id=context.run.external_task_id,
            author_email=self.agent_email,
            body=report.final_comment,
        )
        self.observability.add_event(
            run_id=context.run.id,
            tick_id=context.run.tick_id,
            type="task.comment_added",
            message="Добавлен итоговый комментарий runtime",
        )
        self.observability.add_event(
            run_id=context.run.id,
            tick_id=context.run.tick_id,
            type="run.outcome",
            message="Runtime сформировал результат выполнения",
            payload={
                "outcome": report.outcome,
                "artifacts": report.artifacts or [],
                "checks_summary": report.checks_summary,
            },
        )

        await self.tracker.tasks_update(
            context.run.external_task_id,
            {"status": report.task_status},
        )
        self.observability.add_event(
            run_id=context.run.id,
            tick_id=context.run.tick_id,
            type="task.status_changed",
            message=f"Задача переведена в {report.task_status}",
            payload={"status": report.task_status},
        )

    def _run_tool(
        self,
        *,
        run: RunRecord,
        name: str,
        input: dict[str, Any],
        context: ToolContext,
        raise_on_error: bool = True,
    ) -> dict[str, Any]:
        tool_call = self.observability.create_tool_call(
            run_id=run.id,
            tool_name=name,
            input=input,
        )
        try:
            result = self.tool_registry.run(name, input, context)
        except (ToolError, ValueError) as exc:
            self.observability.complete_tool_call(
                tool_call.id,
                status="failed",
                error=str(exc),
            )
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="tool.failed",
                message=f"Tool `{name}` завершился с ошибкой",
                payload={"tool_call_id": tool_call.id, "tool_name": name},
            )
            if raise_on_error:
                raise
            return {"error": str(exc)}

        self.observability.complete_tool_call(
            tool_call.id,
            status="completed",
            output=result.output,
        )
        self.observability.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="tool.completed",
            message=f"Tool `{name}` выполнен",
            payload={"tool_call_id": tool_call.id, "tool_name": name},
        )
        return result.output

    async def _try_add_failure_comment(self, run: RunRecord, error: str) -> None:
        try:
            await self.tracker.comments_add(
                task_id=run.external_task_id,
                author_email=self.agent_email,
                body=f"Агент завершился с ошибкой: {error}",
            )
        except Exception:
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.comment_failed",
                message="Не удалось добавить диагностический комментарий",
                payload={"error": error},
            )


class PrimitiveAgentRuntime(TaskLifecycleRuntime):
    start_summary = "Примитивный runtime начал выполнение"
    start_message = "Примитивный runtime начал выполнение задачи"
    start_comment = "Агент начал выполнение задачи."
    failed_summary = "Примитивный runtime завершился с ошибкой"

    async def execute(self, context: RuntimeExecutionContext) -> CompletionReport:
        self._run_tool(
            run=context.run,
            name="write_file",
            input={
                "path": "agent-run-summary.txt",
                "content": f"Stub workspace for {context.run.external_task_id}\n",
            },
            context=context.tool_context,
        )
        self._run_tool(
            run=context.run,
            name="list_files",
            input={"path": "."},
            context=context.tool_context,
        )
        self._run_tool(
            run=context.run,
            name="read_file",
            input={"path": "agent-run-summary.txt"},
            context=context.tool_context,
        )
        self._run_tool(
            run=context.run,
            name="search_text",
            input={"path": ".", "query": context.run.external_task_id},
            context=context.tool_context,
        )
        return CompletionReport(
            outcome="workspace_artifact",
            final_comment=(
                "Примитивный runtime завершил stub-выполнение задачи без изменения кода."
            ),
            run_summary="Примитивный runtime завершил задачу",
            task_status="Done",
        )


class LLMAgentRuntime(TaskLifecycleRuntime):
    start_summary = "LLM runtime начал выполнение"
    start_message = "LLM runtime начал выполнение задачи"
    start_comment = "Агент начал выполнение задачи в LLM-режиме."
    failed_summary = "LLM runtime завершился с ошибкой"

    def __init__(
        self,
        *,
        observability: ObservabilitySink,
        tracker: TaskTrackerClient,
        agent_email: str,
        workspace_manager: WorkspaceManager,
        tool_registry: ToolRegistry,
        llm_client: LLMClient,
        max_steps: int,
        command_timeout_seconds: float,
        output_max_bytes: int,
        file_read_max_bytes: int,
    ) -> None:
        super().__init__(
            observability=observability,
            tracker=tracker,
            agent_email=agent_email,
            workspace_manager=workspace_manager,
            tool_registry=tool_registry,
            command_timeout_seconds=command_timeout_seconds,
            output_max_bytes=output_max_bytes,
            file_read_max_bytes=file_read_max_bytes,
        )
        self.llm_client = llm_client
        self.max_steps = max_steps

    async def execute(self, context: RuntimeExecutionContext) -> CompletionReport:
        before = capture_repo_snapshot(
            context.workspace,
            max_file_bytes=self.file_read_max_bytes,
        )
        final_message = await self._run_llm_loop(
            run=context.run,
            task=context.task,
            tool_context=context.tool_context,
        )
        after = capture_repo_snapshot(
            context.workspace,
            max_file_bytes=self.file_read_max_bytes,
        )
        return self._build_completion_report(
            context=context,
            final_message=final_message,
            before=before,
            after=after,
        )

    async def _run_llm_loop(
        self,
        *,
        run: RunRecord,
        task: dict[str, Any],
        tool_context: ToolContext,
    ) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_task_prompt(task)},
        ]
        tools = self.tool_registry.to_llm_tools()
        final_message: str | None = None

        for step in range(1, self.max_steps + 1):
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="llm.requested",
                message="LLM вызван для следующего шага",
                payload={"step": step, "tools": self.tool_registry.names},
            )
            response = await self.llm_client.complete(messages=messages, tools=tools)
            self.observability.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="llm.responded",
                message="LLM вернул ответ",
                payload={
                    "step": step,
                    "has_content": bool(response.content),
                    "tool_calls": [call.name for call in response.tool_calls],
                },
            )

            messages.append(_assistant_message(response.content, response.tool_calls))
            if not response.tool_calls:
                final_message = response.content or "LLM runtime завершил задачу."
                break

            for call in response.tool_calls:
                output = self._run_tool(
                    run=run,
                    name=call.name,
                    input=call.arguments,
                    context=tool_context,
                    raise_on_error=False,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(output, ensure_ascii=False),
                    }
                )

        if final_message is None:
            raise RuntimeError(f"LLM runtime exceeded max steps: {self.max_steps}")
        return final_message

    def _build_completion_report(
        self,
        *,
        context: RuntimeExecutionContext,
        final_message: str,
        before: dict[str, str],
        after: dict[str, str],
    ) -> CompletionReport:
        diff = build_workspace_diff(
            context.workspace,
            before=before,
            after=after,
            max_file_bytes=self.file_read_max_bytes,
        )
        if not diff:
            return CompletionReport(
                outcome="answer_only",
                final_comment=final_message,
                run_summary="LLM runtime завершил задачу без изменений файлов",
                task_status="Done",
                checks_summary="Проверки не требовались: файлы не изменялись.",
            )

        artifact = write_artifact(context.workspace, "final.diff", diff)
        self.observability.add_event(
            run_id=context.run.id,
            tick_id=context.run.tick_id,
            type="artifact.created",
            message="Создан diff-артефакт",
            payload={"path": artifact.path, "bytes": artifact.bytes},
        )
        checks_summary = _checks_summary(
            self.observability.list_tool_calls_for_run(context.run.id)
        )
        return CompletionReport(
            outcome="code_change",
            final_comment=_format_code_change_comment(
                final_message=final_message,
                diff_path=artifact.path,
                checks_summary=checks_summary,
            ),
            run_summary="LLM runtime завершил задачу с изменениями файлов",
            task_status="InReview",
            artifacts=[artifact.path],
            checks_summary=checks_summary,
        )


def _assistant_message(content: str | None, tool_calls: list[LLMToolCall]) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False),
                },
            }
            for call in tool_calls
        ]
    return message


def _checks_summary(tool_calls: list[Any]) -> str:
    run_tests_calls = [call for call in tool_calls if call.tool_name == "run_tests"]
    if not run_tests_calls:
        return "Проверки не запускались: LLM runtime не вызвал run_tests."
    failed = [call for call in run_tests_calls if call.status != "completed"]
    if failed:
        return "Проверки запускались, но часть вызовов run_tests завершилась ошибкой."
    return "Проверки запускались через run_tests."


def _format_code_change_comment(
    *,
    final_message: str,
    diff_path: str,
    checks_summary: str,
) -> str:
    return "\n".join(
        [
            final_message,
            "",
            "Итог выполнения:",
            "- Тип результата: code_change",
            f"- Diff-артефакт: {diff_path}",
            f"- Проверки: {checks_summary}",
        ]
    )
