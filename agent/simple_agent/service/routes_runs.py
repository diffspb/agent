from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from simple_agent.agent.artifacts import list_artifacts, read_artifact
from simple_agent.agent import (
    AgentController,
    LLMAgentRuntime,
    PrimitiveAgentRuntime,
    RunNotFoundError,
)
from simple_agent.config import Settings
from simple_agent.llm import LiteLLMClient, StubLLMClient
from simple_agent.service.dependencies import get_repository, get_settings
from simple_agent.service.schemas import (
    artifact_to_response,
    event_to_response,
    run_to_response,
    tool_call_to_response,
)
from simple_agent.storage import Repository
from simple_agent.tools import build_default_tool_registry
from simple_agent.tracker import TaskTrackerClient
from simple_agent.workspace import WorkspaceManager


router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    return [run_to_response(run) for run in repository.list_runs()]


@router.get("/{run_id}")
async def get_run(
    run_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_to_response(run)


@router.get("/{run_id}/events")
async def list_run_events(
    run_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return [event_to_response(event) for event in repository.list_events_for_run(run_id)]


@router.get("/{run_id}/tool-calls")
async def list_run_tool_calls(
    run_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[dict]:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return [
        tool_call_to_response(tool_call)
        for tool_call in repository.list_tool_calls_for_run(run_id)
    ]


@router.get("/{run_id}/artifacts")
async def list_run_artifacts(
    run_id: int,
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict]:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    workspace = WorkspaceManager(root=settings.workspace_root).workspace_for_run(run)
    return [artifact_to_response(artifact) for artifact in list_artifacts(workspace)]


@router.get("/{run_id}/artifacts/{artifact_path:path}")
async def get_run_artifact(
    run_id: int,
    artifact_path: str,
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    workspace = WorkspaceManager(root=settings.workspace_root).workspace_for_run(run)
    try:
        content = read_artifact(workspace, artifact_path)
    except (FileNotFoundError, IsADirectoryError):
        raise HTTPException(status_code=404, detail="Artifact not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"path": artifact_path, "content": content}


@router.post("/{run_id}/start")
async def start_run(
    run_id: int,
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    controller = _create_controller(
        request=request,
        repository=repository,
        settings=settings,
    )
    try:
        result = await controller.start_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return run_to_response(result.run)


@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: int,
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    controller = _create_controller(
        request=request,
        repository=repository,
        settings=settings,
    )
    try:
        result = await controller.cancel_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return run_to_response(result.run)


def _create_controller(
    *,
    request: Request,
    repository: Repository,
    settings: Settings,
) -> AgentController:
    tracker_factory = request.app.state.task_tracker_factory
    tracker: TaskTrackerClient = tracker_factory()
    tool_registry = build_default_tool_registry()
    workspace_manager = WorkspaceManager(root=settings.workspace_root)
    if settings.agent_runtime_mode == "llm":
        runtime = LLMAgentRuntime(
            repository=repository,
            tracker=tracker,
            agent_email=settings.agent_email,
            workspace_manager=workspace_manager,
            tool_registry=tool_registry,
            llm_client=LiteLLMClient(
                model=settings.llm_model,
                api_base=settings.llm_base_url,
                api_key=settings.llm_api_key,
                timeout_seconds=settings.llm_timeout_seconds,
            ),
            max_steps=settings.llm_max_steps,
            command_timeout_seconds=settings.tool_command_timeout_seconds,
            output_max_bytes=settings.tool_output_max_bytes,
            file_read_max_bytes=settings.tool_file_read_max_bytes,
        )
        return AgentController(repository=repository, runtime=runtime)
    if settings.agent_runtime_mode == "llm_stub":
        runtime = LLMAgentRuntime(
            repository=repository,
            tracker=tracker,
            agent_email=settings.agent_email,
            workspace_manager=workspace_manager,
            tool_registry=tool_registry,
            llm_client=StubLLMClient(),
            max_steps=settings.llm_max_steps,
            command_timeout_seconds=settings.tool_command_timeout_seconds,
            output_max_bytes=settings.tool_output_max_bytes,
            file_read_max_bytes=settings.tool_file_read_max_bytes,
        )
        return AgentController(repository=repository, runtime=runtime)
    if settings.agent_runtime_mode != "primitive":
        raise HTTPException(
            status_code=500,
            detail=f"Unknown AGENT_RUNTIME_MODE: {settings.agent_runtime_mode}",
        )
    runtime = PrimitiveAgentRuntime(
        repository=repository,
        tracker=tracker,
        agent_email=settings.agent_email,
        workspace_manager=workspace_manager,
        tool_registry=tool_registry,
        command_timeout_seconds=settings.tool_command_timeout_seconds,
        output_max_bytes=settings.tool_output_max_bytes,
        file_read_max_bytes=settings.tool_file_read_max_bytes,
    )
    return AgentController(repository=repository, runtime=runtime)
