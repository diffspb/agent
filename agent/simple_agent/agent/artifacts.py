from __future__ import annotations

from dataclasses import dataclass
import difflib
from pathlib import Path
import subprocess

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


def build_workspace_diff(
    workspace: Workspace,
    *,
    before: FileSnapshot,
    after: FileSnapshot,
    max_file_bytes: int,
) -> str:
    if _is_git_repository(workspace.repo):
        return build_git_diff(workspace, max_file_bytes=max_file_bytes)
    return build_snapshot_diff(before, after)


def build_git_diff(workspace: Workspace, *, max_file_bytes: int) -> str:
    tracked_diff = _git_output(workspace.repo, "diff", "--", allow_empty=True)
    untracked_chunks: list[str] = []
    for relative_path in _git_output(
        workspace.repo,
        "ls-files",
        "--others",
        "--exclude-standard",
        allow_empty=True,
    ).splitlines():
        if not relative_path:
            continue
        path = workspace.repo / relative_path
        if not path.is_file():
            continue
        data = path.read_bytes()
        if len(data) > max_file_bytes:
            continue
        content = data.decode("utf-8", errors="replace")
        untracked_chunks.extend(
            difflib.unified_diff(
                [],
                content.splitlines(keepends=True),
                fromfile="/dev/null",
                tofile=f"b/{relative_path}",
                lineterm="",
            )
        )
        untracked_chunks.append("\n")

    parts = [part for part in (tracked_diff.strip(), "\n".join(untracked_chunks).strip()) if part]
    return "\n\n".join(parts).strip() + "\n" if parts else ""


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


def _is_git_repository(repo_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _git_output(repo_root: Path, *args: str, allow_empty: bool = False) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 and not allow_empty:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise RuntimeError(stderr or stdout or "git command failed")
    return completed.stdout
