from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from simple_agent.agent import LLMAgentRuntime
from simple_agent.llm import LLMResponse, LLMToolCall, StubLLMClient
from simple_agent.storage import Repository, SqliteDatabase, SqliteObservabilitySink
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
                content="Переведу задачу в работу и создам файл результата.",
                tool_calls=[
                    LLMToolCall(
                        id="call-0",
                        name="tasks_update",
                        arguments={"task_id": "PROJECT-1", "patch": {"status": "InProgress"}},
                    ),
                    LLMToolCall(
                        id="call-0b",
                        name="comments_add",
                        arguments={
                            "task_id": "PROJECT-1",
                            "body": "Агент начал выполнение задачи в LLM-режиме.",
                        },
                    ),
                    LLMToolCall(
                        id="call-1",
                        name="write_file",
                        arguments={"path": "result.txt", "content": "done\n"},
                    ),
                ],
            ),
            LLMResponse(
                content="Оставлю итоговый комментарий и обновлю статус.",
                tool_calls=[
                    LLMToolCall(
                        id="call-2",
                        name="comments_add",
                        arguments={
                            "task_id": "PROJECT-1",
                            "body": "Готово. Создан result.txt.\nПроверки: Проверки не запускались: LLM runtime не вызвал run_tests.\nDiff-артефакт: final.diff",
                        },
                    ),
                    LLMToolCall(
                        id="call-3",
                        name="tasks_update",
                        arguments={"task_id": "PROJECT-1", "patch": {"status": "InReview"}},
                    ),
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
    assert tracker.tasks["PROJECT-1"]["status"] == "InReview"
    assert tracker.comments["PROJECT-1"][0]["body"] == "Агент начал выполнение задачи в LLM-режиме."
    assert "Готово. Создан result.txt." in tracker.comments["PROJECT-1"][1]["body"]
    assert "Diff-артефакт: final.diff" in tracker.comments["PROJECT-1"][1]["body"]
    events = repository.list_events_for_run(run.id)
    assert "llm.requested" in [event.type for event in events]
    assert "llm.responded" in [event.type for event in events]
    assert "artifact.created" in [event.type for event in events]
    tool_calls = repository.list_tool_calls_for_run(run.id)
    assert [(call.tool_name, call.status) for call in tool_calls] == [
        ("tasks_update", "completed"),
        ("comments_add", "completed"),
        ("write_file", "completed"),
        ("comments_add", "completed"),
        ("tasks_update", "completed"),
    ]
    assert len(llm.requests) == 3
    assert llm.requests[0]["tools"]
    diff_path = tmp_path / "workspaces" / "run-1-PROJECT-1" / "artifacts" / "final.diff"
    assert "result.txt" in diff_path.read_text(encoding="utf-8")


@pytest.mark.anyio
async def test_llm_runtime_can_complete_answer_only_task(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    llm = StubLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="comments_add",
                        arguments={"task_id": "PROJECT-1", "body": "Ответ без изменения файлов."},
                    ),
                    LLMToolCall(
                        id="call-2",
                        name="tasks_update",
                        arguments={"task_id": "PROJECT-1", "patch": {"status": "Done"}},
                    ),
                ]
            ),
            LLMResponse(content="Ответ без изменения файлов."),
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
    assert result.run.summary == "LLM runtime завершил задачу без изменений файлов"
    assert tracker.tasks["PROJECT-1"]["status"] == "Done"
    assert tracker.comments["PROJECT-1"][-1]["body"] == "Ответ без изменения файлов."
    events = repository.list_events_for_run(run.id)
    outcome_events = [event for event in events if event.type == "run.outcome"]
    assert outcome_events[0].payload["outcome"] == "answer_only"


@pytest.mark.anyio
async def test_llm_runtime_continues_after_tool_error(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    llm = StubLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="read_file",
                        arguments={"path": "missing.txt"},
                    )
                ],
            ),
            LLMResponse(content="Файл отсутствует, дополнительных действий не требуется."),
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
    assert tracker.tasks["PROJECT-1"]["status"] == "Open"
    tool_calls = repository.list_tool_calls_for_run(run.id)
    assert [(call.tool_name, call.status) for call in tool_calls] == [
        ("read_file", "failed")
    ]
    assert "File not found" in (tool_calls[0].error or "")


@pytest.mark.anyio
async def test_llm_runtime_runs_multiple_tool_calls_in_one_step(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    llm = StubLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="write_file",
                        arguments={"path": "one.txt", "content": "one\n"},
                    ),
                    LLMToolCall(
                        id="call-2",
                        name="write_file",
                        arguments={"path": "two.txt", "content": "two\n"},
                    ),
                ],
            ),
            LLMResponse(content="Созданы два файла."),
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
    tool_calls = repository.list_tool_calls_for_run(run.id)
    assert [(call.tool_name, call.status) for call in tool_calls] == [
        ("write_file", "completed"),
        ("write_file", "completed"),
    ]
    diff_path = tmp_path / "workspaces" / "run-1-PROJECT-1" / "artifacts" / "final.diff"
    diff = diff_path.read_text(encoding="utf-8")
    assert "one.txt" in diff
    assert "two.txt" in diff


@pytest.mark.anyio
async def test_llm_runtime_handles_empty_final_response(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_run(external_task_id="PROJECT-1", status="queued")
    tracker = FakeTracker([_task("PROJECT-1")])
    llm = StubLLMClient([LLMResponse()])
    runtime = _runtime(
        repository=repository,
        tracker=tracker,
        tmp_path=tmp_path,
        llm=llm,
    )

    result = await runtime.start_run(run)

    assert result.run.status == "completed"
    assert tracker.comments["PROJECT-1"] == []


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
        observability=SqliteObservabilitySink(repository),
        tracker=tracker,
        agent_email="agent@example.com",
        workspace_manager=WorkspaceManager(root=tmp_path / "workspaces"),
        tool_registry=build_default_tool_registry(include_task_tracker_tools=True),
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

    async def workflow_get(self) -> dict[str, Any]:
        return {"statuses": ["Open", "InProgress", "InReview", "Done"], "transitions": "any"}

    async def tasks_get(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            raise RuntimeError(f"Task not found: {task_id}")
        return task

    async def tasks_list(
        self,
        *,
        status: str | None = None,
        assignee_email: str | None = None,
    ) -> list[dict[str, Any]]:
        tasks = list(self.tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task.get("status") == status]
        if assignee_email is not None:
            tasks = [task for task in tasks if task.get("assignee_email") == assignee_email]
        return tasks

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

    async def comments_list(self, task_id: str) -> list[dict[str, Any]]:
        await self.tasks_get(task_id)
        return self.comments[task_id]
