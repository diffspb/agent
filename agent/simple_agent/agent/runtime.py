from __future__ import annotations

import json
from dataclasses import dataclass

from simple_agent.agent.prompts import SYSTEM_PROMPT, build_task_prompt
from simple_agent.llm import LLMClient, LLMToolCall
from simple_agent.storage.models import RunRecord
from simple_agent.storage.repository import Repository
from simple_agent.tools import ToolContext, ToolError, ToolRegistry
from simple_agent.tracker.client import TaskTrackerClient
from simple_agent.workspace import WorkspaceManager


RUN_STARTABLE_STATUSES = {"queued"}
RUN_CANCELABLE_STATUSES = {"queued", "running"}


@dataclass(frozen=True)
class RuntimeResult:
    run: RunRecord


class PrimitiveAgentRuntime:
    def __init__(
        self,
        *,
        repository: Repository,
        tracker: TaskTrackerClient,
        agent_email: str,
        workspace_manager: WorkspaceManager,
        tool_registry: ToolRegistry,
        command_timeout_seconds: float,
        output_max_bytes: int,
        file_read_max_bytes: int,
    ) -> None:
        self.repository = repository
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

        running = self.repository.update_run(
            run.id,
            status="running",
            summary="Примитивный runtime начал выполнение",
        )
        self.repository.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="run.started",
            message="Примитивный runtime начал выполнение задачи",
            payload={"external_task_id": run.external_task_id},
        )

        try:
            task = await self.tracker.tasks_get(run.external_task_id)
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.loaded",
                message="Задача загружена из таск-трекера",
                payload={"external_task_id": task.get("id")},
            )

            workspace = self.workspace_manager.prepare_for_run(running)
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="workspace.prepared",
                message="Рабочее пространство подготовлено",
                payload={"workspace_root": str(workspace.root)},
            )

            await self.tracker.tasks_update(run.external_task_id, {"status": "InProgress"})
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.status_changed",
                message="Задача переведена в InProgress",
                payload={"status": "InProgress"},
            )

            await self.tracker.comments_add(
                task_id=run.external_task_id,
                author_email=self.agent_email,
                body="Агент начал выполнение задачи.",
            )
            self.repository.add_event(
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
            self._run_tool(
                run=run,
                name="write_file",
                input={
                    "path": "agent-run-summary.txt",
                    "content": f"Stub workspace for {run.external_task_id}\n",
                },
                context=tool_context,
            )
            self._run_tool(
                run=run,
                name="list_files",
                input={"path": "."},
                context=tool_context,
            )
            self._run_tool(
                run=run,
                name="read_file",
                input={"path": "agent-run-summary.txt"},
                context=tool_context,
            )
            self._run_tool(
                run=run,
                name="search_text",
                input={"path": ".", "query": run.external_task_id},
                context=tool_context,
            )

            await self.tracker.comments_add(
                task_id=run.external_task_id,
                author_email=self.agent_email,
                body="Примитивный runtime завершил stub-выполнение задачи без изменения кода.",
            )
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.comment_added",
                message="Добавлен комментарий о завершении работы",
            )

            await self.tracker.tasks_update(run.external_task_id, {"status": "Done"})
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.status_changed",
                message="Задача переведена в Done",
                payload={"status": "Done"},
            )

            completed = self.repository.update_run(
                run.id,
                status="completed",
                summary="Примитивный runtime завершил задачу",
                error=None,
                finished=True,
            )
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="run.completed",
                message="Run завершен успешно",
            )
            return RuntimeResult(run=completed)
        except Exception as exc:
            failed = self.repository.update_run(
                run.id,
                status="failed",
                summary="Примитивный runtime завершился с ошибкой",
                error=str(exc),
                finished=True,
            )
            self.repository.add_event(
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

        cancelled = self.repository.update_run(
            run.id,
            status="cancelled",
            summary="Run отменен пользователем",
            error=None,
            finished=True,
        )
        self.repository.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="run.cancelled",
            message="Run отменен пользователем",
            payload={"external_task_id": run.external_task_id},
        )
        return RuntimeResult(run=cancelled)

    def _run_tool(
        self,
        *,
        run: RunRecord,
        name: str,
        input: dict,
        context: ToolContext,
    ) -> None:
        tool_call = self.repository.create_tool_call(
            run_id=run.id,
            tool_name=name,
            input=input,
        )
        try:
            result = self.tool_registry.run(name, input, context)
        except (ToolError, ValueError) as exc:
            self.repository.complete_tool_call(
                tool_call.id,
                status="failed",
                error=str(exc),
            )
            raise

        self.repository.complete_tool_call(
            tool_call.id,
            status="completed",
            output=result.output,
        )
        self.repository.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="tool.completed",
            message=f"Tool `{name}` выполнен",
            payload={"tool_call_id": tool_call.id, "tool_name": name},
        )


class LLMAgentRuntime:
    def __init__(
        self,
        *,
        repository: Repository,
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
        self.repository = repository
        self.tracker = tracker
        self.agent_email = agent_email
        self.workspace_manager = workspace_manager
        self.tool_registry = tool_registry
        self.llm_client = llm_client
        self.max_steps = max_steps
        self.command_timeout_seconds = command_timeout_seconds
        self.output_max_bytes = output_max_bytes
        self.file_read_max_bytes = file_read_max_bytes

    async def start_run(self, run: RunRecord) -> RuntimeResult:
        if run.status not in RUN_STARTABLE_STATUSES:
            raise ValueError(f"Run cannot be started from status: {run.status}")

        running = self.repository.update_run(
            run.id,
            status="running",
            summary="LLM runtime начал выполнение",
        )
        self.repository.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="run.started",
            message="LLM runtime начал выполнение задачи",
            payload={"external_task_id": run.external_task_id},
        )

        try:
            task = await self.tracker.tasks_get(run.external_task_id)
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.loaded",
                message="Задача загружена из таск-трекера",
                payload={"external_task_id": task.get("id")},
            )

            workspace = self.workspace_manager.prepare_for_run(running)
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="workspace.prepared",
                message="Рабочее пространство подготовлено",
                payload={"workspace_root": str(workspace.root)},
            )

            await self.tracker.tasks_update(run.external_task_id, {"status": "InProgress"})
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.status_changed",
                message="Задача переведена в InProgress",
                payload={"status": "InProgress"},
            )

            await self.tracker.comments_add(
                task_id=run.external_task_id,
                author_email=self.agent_email,
                body="Агент начал выполнение задачи в LLM-режиме.",
            )
            self.repository.add_event(
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
            final_message = await self._run_llm_loop(
                run=run,
                task=task,
                tool_context=tool_context,
            )

            await self.tracker.comments_add(
                task_id=run.external_task_id,
                author_email=self.agent_email,
                body=final_message,
            )
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.comment_added",
                message="Добавлен итоговый комментарий LLM runtime",
            )

            await self.tracker.tasks_update(run.external_task_id, {"status": "Done"})
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.status_changed",
                message="Задача переведена в Done",
                payload={"status": "Done"},
            )

            completed = self.repository.update_run(
                run.id,
                status="completed",
                summary="LLM runtime завершил задачу",
                error=None,
                finished=True,
            )
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="run.completed",
                message="Run завершен успешно",
            )
            return RuntimeResult(run=completed)
        except Exception as exc:
            await self._try_add_failure_comment(run, str(exc))
            failed = self.repository.update_run(
                run.id,
                status="failed",
                summary="LLM runtime завершился с ошибкой",
                error=str(exc),
                finished=True,
            )
            self.repository.add_event(
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

        cancelled = self.repository.update_run(
            run.id,
            status="cancelled",
            summary="Run отменен пользователем",
            error=None,
            finished=True,
        )
        self.repository.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="run.cancelled",
            message="Run отменен пользователем",
            payload={"external_task_id": run.external_task_id},
        )
        return RuntimeResult(run=cancelled)

    async def _run_llm_loop(
        self,
        *,
        run: RunRecord,
        task: dict,
        tool_context: ToolContext,
    ) -> str:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_task_prompt(task)},
        ]
        tools = self.tool_registry.to_llm_tools()
        final_message: str | None = None

        for step in range(1, self.max_steps + 1):
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="llm.requested",
                message="LLM вызван для следующего шага",
                payload={"step": step, "tools": self.tool_registry.names},
            )
            response = await self.llm_client.complete(messages=messages, tools=tools)
            self.repository.add_event(
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
                output = self._run_llm_tool(run=run, call=call, context=tool_context)
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

    def _run_llm_tool(
        self,
        *,
        run: RunRecord,
        call: LLMToolCall,
        context: ToolContext,
    ) -> dict:
        tool_call = self.repository.create_tool_call(
            run_id=run.id,
            tool_name=call.name,
            input=call.arguments,
        )
        try:
            result = self.tool_registry.run(call.name, call.arguments, context)
        except (ToolError, ValueError) as exc:
            self.repository.complete_tool_call(
                tool_call.id,
                status="failed",
                error=str(exc),
            )
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="tool.failed",
                message=f"Tool `{call.name}` завершился с ошибкой",
                payload={"tool_call_id": tool_call.id, "tool_name": call.name},
            )
            return {"error": str(exc)}

        self.repository.complete_tool_call(
            tool_call.id,
            status="completed",
            output=result.output,
        )
        self.repository.add_event(
            run_id=run.id,
            tick_id=run.tick_id,
            type="tool.completed",
            message=f"Tool `{call.name}` выполнен",
            payload={"tool_call_id": tool_call.id, "tool_name": call.name},
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
            self.repository.add_event(
                run_id=run.id,
                tick_id=run.tick_id,
                type="task.comment_failed",
                message="Не удалось добавить диагностический комментарий",
                payload={"error": error},
            )


def _assistant_message(content: str | None, tool_calls: list[LLMToolCall]) -> dict:
    message: dict = {"role": "assistant", "content": content}
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
