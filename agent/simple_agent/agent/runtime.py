from __future__ import annotations

from dataclasses import dataclass

from simple_agent.storage.models import RunRecord
from simple_agent.storage.repository import Repository
from simple_agent.tracker.client import TaskTrackerClient


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
    ) -> None:
        self.repository = repository
        self.tracker = tracker
        self.agent_email = agent_email

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
