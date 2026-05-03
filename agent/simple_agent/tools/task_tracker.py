from __future__ import annotations

from simple_agent.tools.types import JsonObject, ToolContext, ToolError, ToolResult


class WorkflowGetTool:
    name = "workflow_get"

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        tracker = _require_tracker(context)
        _reject_extra_args(input)
        return ToolResult(output=await tracker.workflow_get())


class TasksGetTool:
    name = "tasks_get"

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        tracker = _require_tracker(context)
        task_id = _require_string(input, "task_id")
        return ToolResult(output=await tracker.tasks_get(task_id))


class TasksListTool:
    name = "tasks_list"

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        tracker = _require_tracker(context)
        status = _optional_string(input, "status")
        assignee_email = _optional_string(input, "assignee_email")
        return ToolResult(
            output={
                "tasks": await tracker.tasks_list(
                    status=status,
                    assignee_email=assignee_email,
                )
            }
        )


class TasksUpdateTool:
    name = "tasks_update"

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        tracker = _require_tracker(context)
        task_id = _require_string(input, "task_id")
        patch = input.get("patch")
        if not isinstance(patch, dict):
            raise ToolError("patch must be an object")
        return ToolResult(output=await tracker.tasks_update(task_id, patch))


class CommentsAddTool:
    name = "comments_add"

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        tracker = _require_tracker(context)
        if not context.agent_email:
            raise ToolError("agent_email is not configured")
        task_id = _require_string(input, "task_id")
        body = _require_string(input, "body")
        return ToolResult(
            output=await tracker.comments_add(
                task_id=task_id,
                author_email=context.agent_email,
                body=body,
            )
        )


class CommentsListTool:
    name = "comments_list"

    async def arun(self, input: JsonObject, context: ToolContext) -> ToolResult:
        tracker = _require_tracker(context)
        task_id = _require_string(input, "task_id")
        return ToolResult(output={"comments": await tracker.comments_list(task_id)})


def _require_tracker(context: ToolContext):
    if context.tracker is None:
        raise ToolError("task tracker is not configured in tool context")
    return context.tracker


def _require_string(input: JsonObject, field: str) -> str:
    value = input.get(field)
    if not isinstance(value, str) or not value:
        raise ToolError(f"{field} must be a non-empty string")
    return value


def _optional_string(input: JsonObject, field: str) -> str | None:
    value = input.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ToolError(f"{field} must be a non-empty string")
    return value


def _reject_extra_args(input: JsonObject) -> None:
    if input:
        raise ToolError("workflow_get does not accept arguments")
