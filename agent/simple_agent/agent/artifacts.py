from __future__ import annotations

from dataclasses import dataclass
import difflib
from pathlib import Path

from simple_agent.workspace import Workspace


@dataclass(frozen=True)
class Artifact:
    path: str
    name: str
    bytes: int


FileSnapshot = dict[str, str]


def capture_repo_snapshot(workspace: Workspace, *, max_file_bytes: int) -> FileSnapshot:
    snapshot: FileSnapshot = {}
    if not workspace.repo.exists():
        return snapshot

    for path in sorted(workspace.repo.rglob("*")):
        if not path.is_file() or _is_ignored(path, workspace):
            continue
        data = path.read_bytes()
        if len(data) > max_file_bytes:
            continue
        relative_path = str(path.relative_to(workspace.repo))
        snapshot[relative_path] = data.decode("utf-8", errors="replace")
    return snapshot


def build_snapshot_diff(before: FileSnapshot, after: FileSnapshot) -> str:
    chunks: list[str] = []
    for path in sorted(set(before) | set(after)):
        old = before.get(path)
        new = after.get(path)
        if old == new:
            continue
        old_lines = [] if old is None else old.splitlines(keepends=True)
        new_lines = [] if new is None else new.splitlines(keepends=True)
        chunks.extend(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        chunks.append("\n")
    return "\n".join(chunks).strip() + "\n" if chunks else ""


def write_artifact(workspace: Workspace, relative_path: str, content: str) -> Artifact:
    path = workspace.resolve_path(relative_path, base="artifacts")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return _artifact_from_path(path, workspace)


def list_artifacts(workspace: Workspace) -> list[Artifact]:
    if not workspace.artifacts.exists():
        return []
    artifacts = [
        _artifact_from_path(path, workspace)
        for path in sorted(workspace.artifacts.rglob("*"))
        if path.is_file()
    ]
    return artifacts


def read_artifact(workspace: Workspace, relative_path: str) -> str:
    path = workspace.resolve_path(relative_path, base="artifacts")
    if not path.exists():
        raise FileNotFoundError(relative_path)
    if not path.is_file():
        raise IsADirectoryError(relative_path)
    return path.read_text(encoding="utf-8")


def _artifact_from_path(path: Path, workspace: Workspace) -> Artifact:
    relative_path = str(path.relative_to(workspace.artifacts))
    return Artifact(path=relative_path, name=path.name, bytes=path.stat().st_size)


def _is_ignored(path: Path, workspace: Workspace) -> bool:
    try:
        relative = path.relative_to(workspace.repo)
    except ValueError:
        return True
    return ".git" in relative.parts
