from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from simple_agent.agent import LLMAgentRuntime
from simple_agent.llm import LLMResponse, LLMToolCall, StubLLMClient
from simple_agent.storage import Repository, SqliteDatabase
from simple_agent.tools import build_default_tool_registry
from simple_agent.workspace import WorkspaceManager


@pytest.mark.anyio
async def test_llm_runtime_runs_tool_loop_and_completes_task(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    llm = StubLLMClient(
        [
            LLMResponse(
                content="Создам файл результата.",
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="write_file",
                        arguments={"path": "result.txt", "content": "done\n"},
                    )
                ],
            ),
            LLMResponse(content="Готово. Создан result.txt."),
        ]
    )
    runtime = _runtime(
        repository=repository,
        tracker=tracker,
        tmp_path=tmp_path,
        llm=llm,
    )

    result = await runtime.start_run(run)

    assert result.run.status == "completed"
    assert tracker.tasks["PROJECT-1"]["status"] == "Done"
    assert [comment["body"] for comment in tracker.comments["PROJECT-1"]] == [
        "Агент начал выполнение задачи в LLM-режиме.",
        "Готово. Создан result.txt.",
    ]
    events = repository.list_events_for_run(run.id)
    assert "llm.requested" in [event.type for event in events]
    assert "llm.responded" in [event.type for event in events]
    tool_calls = repository.list_tool_calls_for_run(run.id)
    assert [(call.tool_name, call.status) for call in tool_calls] == [
        ("write_file", "completed")
    ]
    assert len(llm.requests) == 2
    assert llm.requests[0]["tools"]


@pytest.mark.anyio
async def test_llm_runtime_fails_after_step_limit(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    llm = StubLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="unknown_tool",
                        arguments={},
                    )
                ],
            )
        ]
    )
    runtime = _runtime(
        repository=repository,
        tracker=tracker,
        tmp_path=tmp_path,
        llm=llm,
        max_steps=1,
    )

    result = await runtime.start_run(run)

    assert result.run.status == "failed"
    assert result.run.error == "LLM runtime exceeded max steps: 1"
    assert tracker.comments["PROJECT-1"][-1]["body"] == (
        "Агент завершился с ошибкой: LLM runtime exceeded max steps: 1"
    )
    tool_calls = repository.list_tool_calls_for_run(run.id)
    assert [(call.tool_name, call.status) for call in tool_calls] == [
        ("unknown_tool", "failed")
    ]


def _repository(tmp_path: Path) -> Repository:
    database = SqliteDatabase(tmp_path / "llm-runtime.sqlite3")
    database.initialize()
    return Repository(database)


def _runtime(
    *,
    repository: Repository,
    tracker: "FakeTracker",
    tmp_path: Path,
    llm: StubLLMClient,
    max_steps: int = 4,
) -> LLMAgentRuntime:
    return LLMAgentRuntime(
        repository=repository,
        tracker=tracker,
        agent_email="agent@example.com",
        workspace_manager=WorkspaceManager(root=tmp_path / "workspaces"),
        tool_registry=build_default_tool_registry(),
        llm_client=llm,
        max_steps=max_steps,
        command_timeout_seconds=2,
        output_max_bytes=10_000,
        file_read_max_bytes=10_000,
    )


def _task(task_id: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "type": "task",
        "status": "Open",
        "title": f"Задача {task_id}",
        "author_email": "author@example.com",
        "assignee_email": "agent@example.com",
        "description": "Создай файл result.txt.",
        "links": [],
        "comments": [],
        "metadata": {},
    }


class FakeTracker:
    def __init__(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = {task["id"]: task for task in tasks}
        self.comments: dict[str, list[dict[str, Any]]] = {
            task["id"]: [] for task in tasks
        }

    async def tasks_get(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            raise RuntimeError(f"Task not found: {task_id}")
        return task

    async def tasks_update(self, task_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        task = await self.tasks_get(task_id)
        task.update(patch)
        return task

    async def comments_add(
        self,
        *,
        task_id: str,
        author_email: str,
        body: str,
    ) -> dict[str, Any]:
        await self.tasks_get(task_id)
        comment = {
            "id": f"comment-{len(self.comments[task_id]) + 1}",
            "author_email": author_email,
            "body": body,
            "created_at": "2026-05-02T00:00:00Z",
        }
        self.comments[task_id].append(comment)
        return comment
