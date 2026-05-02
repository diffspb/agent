from __future__ import annotations

from dataclasses import dataclass

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
