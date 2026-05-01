from pathlib import Path

import pytest

from simple_agent.tracker_emulator.server import create_mcp_server
from simple_agent.tracker_emulator.store import TaskTrackerStore


@pytest.mark.anyio
async def test_mcp_server_registers_required_tools(tmp_path: Path) -> None:
    store = TaskTrackerStore.load(
        state_file=Path("seeds/task_tracker/simple-task.json"),
        snapshot_file=tmp_path / "snapshot.json",
    )
    server = create_mcp_server(store, host="127.0.0.1", port=8020)

    tools = await server.list_tools()

    assert {tool.name for tool in tools} == {
        "workflow.get",
        "tasks.get",
        "tasks.list",
        "tasks.update",
        "comments.add",
        "comments.list",
    }


@pytest.mark.anyio
async def test_mcp_server_calls_registered_tool(tmp_path: Path) -> None:
    store = TaskTrackerStore.load(
        state_file=Path("seeds/task_tracker/simple-task.json"),
        snapshot_file=tmp_path / "snapshot.json",
    )
    server = create_mcp_server(store, host="127.0.0.1", port=8020)

    _, result = await server.call_tool("tasks.get", {"id": "PROJECT-1"})

    assert result["id"] == "PROJECT-1"
    assert result["status"] == "Open"
