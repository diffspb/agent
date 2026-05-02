from pathlib import Path

from task_tracker_emulator.tool_docs import generate_tools_markdown


def test_tool_docs_generator_documents_registered_tools() -> None:
    markdown = generate_tools_markdown(
        state_file=Path("datasets/task_tracker/simple-task.json")
    )

    for tool_name in (
        "comments_add",
        "comments_list",
        "tasks_get",
        "tasks_list",
        "tasks_update",
        "workflow_get",
    ):
        assert f"## `{tool_name}`" in markdown

    assert "Получить задачи по статусу и исполнителю email." in markdown
    assert "### JSON Schema Входа" in markdown
    assert "### JSON Schema Ответа" in markdown


def test_generated_tool_docs_file_is_up_to_date() -> None:
    expected = generate_tools_markdown(
        state_file=Path("datasets/task_tracker/simple-task.json")
    )
    actual = Path("docs/mcp-task-tracker-tools.md").read_text(encoding="utf-8")

    assert actual == expected
