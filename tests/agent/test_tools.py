from pathlib import Path

import pytest

from simple_agent.tools import ToolContext, ToolError, build_default_tool_registry
from simple_agent.tools.registry import TOOL_SPECS
from simple_agent.workspace import Workspace


def test_filesystem_tools_stay_inside_workspace(tmp_path: Path) -> None:
    registry = build_default_tool_registry()
    context = _context(tmp_path)

    with pytest.raises(ToolError):
        registry.run("read_file", {"path": "../outside.txt"}, context)


def test_write_read_patch_and_search_tools(tmp_path: Path) -> None:
    registry = build_default_tool_registry()
    context = _context(tmp_path)

    registry.run("write_file", {"path": "notes.txt", "content": "hello PROJECT-1"}, context)
    registry.run(
        "patch_file",
        {"path": "notes.txt", "old_text": "hello", "new_text": "done"},
        context,
    )
    read_result = registry.run("read_file", {"path": "notes.txt"}, context)
    search_result = registry.run("search_text", {"path": ".", "query": "PROJECT-1"}, context)

    assert read_result.output["content"] == "done PROJECT-1"
    assert search_result.output["matches"][0]["path"] == "notes.txt"


def test_run_command_denies_destructive_commands(tmp_path: Path) -> None:
    registry = build_default_tool_registry()
    context = _context(tmp_path)

    with pytest.raises(ToolError):
        registry.run("run_command", {"command": ["rm", "-rf", "."], "cwd": "."}, context)


def test_run_command_times_out(tmp_path: Path) -> None:
    registry = build_default_tool_registry()
    context = _context(tmp_path, timeout=0.01)

    with pytest.raises(ToolError):
        registry.run(
            "run_command",
            {"command": ["python", "-c", "import time; time.sleep(1)"], "cwd": "."},
            context,
        )


def test_all_default_tools_have_llm_metadata() -> None:
    registry = build_default_tool_registry()
    tools = registry.to_llm_tools()

    assert set(registry.names) == set(TOOL_SPECS)
    assert [tool["function"]["name"] for tool in tools] == registry.names
    for tool in tools:
        function = tool["function"]
        assert function["description"]
        assert function["parameters"]["type"] == "object"


def _context(tmp_path: Path, *, timeout: float = 2) -> ToolContext:
    workspace = Workspace(
        root=tmp_path / "workspace",
        repo=tmp_path / "workspace" / "repo",
        artifacts=tmp_path / "workspace" / "artifacts",
        logs=tmp_path / "workspace" / "logs",
        scratch=tmp_path / "workspace" / "scratch",
    )
    for path in (
        workspace.root,
        workspace.repo,
        workspace.artifacts,
        workspace.logs,
        workspace.scratch,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        workspace=workspace,
        command_timeout_seconds=timeout,
        output_max_bytes=10_000,
        file_read_max_bytes=10_000,
    )
