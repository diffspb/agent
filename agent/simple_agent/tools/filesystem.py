from __future__ import annotations

from pathlib import Path

from simple_agent.tools.types import JsonObject, ToolContext, ToolError, ToolResult


class ListFilesTool:
    name = "list_files"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        root = _resolve_path(str(input.get("path", ".")), context)
        if not root.exists():
            raise ToolError(f"Path not found: {input.get('path', '.')}")
        if not root.is_dir():
            raise ToolError("Path is not a directory")

        files = []
        for path in sorted(root.iterdir(), key=lambda item: item.name):
            files.append(
                {
                    "name": path.name,
                    "path": _relative_to_repo(path, context),
                    "type": "directory" if path.is_dir() else "file",
                }
            )
        return ToolResult(output={"files": files})


class ReadFileTool:
    name = "read_file"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        path = _required_path(input, context)
        if not path.exists():
            raise ToolError(f"File not found: {input['path']}")
        if not path.is_file():
            raise ToolError("Path is not a file")
        data = path.read_bytes()
        truncated = len(data) > context.file_read_max_bytes
        content = data[: context.file_read_max_bytes].decode("utf-8", errors="replace")
        return ToolResult(
            output={
                "path": _relative_to_repo(path, context),
                "content": content,
                "truncated": truncated,
                "bytes": len(data),
            }
        )


class WriteFileTool:
    name = "write_file"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        path = _required_path(input, context)
        content = input.get("content")
        if not isinstance(content, str):
            raise ToolError("content must be a string")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            output={
                "path": _relative_to_repo(path, context),
                "bytes": len(content.encode("utf-8")),
            }
        )


class PatchFileTool:
    name = "patch_file"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        path = _required_path(input, context)
        old_text = input.get("old_text")
        new_text = input.get("new_text")
        if not isinstance(old_text, str) or not isinstance(new_text, str):
            raise ToolError("old_text and new_text must be strings")
        if not path.is_file():
            raise ToolError("Path is not a file")
        content = path.read_text(encoding="utf-8")
        if old_text not in content:
            raise ToolError("old_text was not found")
        updated = content.replace(old_text, new_text, 1)
        path.write_text(updated, encoding="utf-8")
        return ToolResult(output={"path": _relative_to_repo(path, context), "replacements": 1})


class SearchTextTool:
    name = "search_text"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        query = input.get("query")
        if not isinstance(query, str) or not query:
            raise ToolError("query must be a non-empty string")
        root = _resolve_path(str(input.get("path", ".")), context)
        if not root.exists():
            raise ToolError(f"Path not found: {input.get('path', '.')}")

        matches = []
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if query in line:
                    matches.append(
                        {
                            "path": _relative_to_repo(path, context),
                            "line": lineno,
                            "text": line[:240],
                        }
                    )
        return ToolResult(output={"matches": matches})


def _required_path(input: JsonObject, context: ToolContext) -> Path:
    value = input.get("path")
    if not isinstance(value, str) or not value:
        raise ToolError("path must be a non-empty string")
    return _resolve_path(value, context)


def _resolve_path(value: str, context: ToolContext) -> Path:
    try:
        return context.workspace.resolve_path(value)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def _relative_to_repo(path: Path, context: ToolContext) -> str:
    try:
        return str(path.resolve().relative_to(context.workspace.repo.resolve()))
    except ValueError:
        return str(path.resolve().relative_to(context.workspace.root.resolve()))
