from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from simple_agent.storage.models import RunRecord


@dataclass(frozen=True)
class Workspace:
    root: Path
    repo: Path
    artifacts: Path
    logs: Path
    scratch: Path

    def resolve_path(self, relative_path: str, *, base: str = "repo") -> Path:
        if not relative_path:
            relative_path = "."
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("Absolute paths are not allowed")

        base_path = self._base_path(base)
        resolved = (base_path / candidate).resolve()
        if resolved != base_path and base_path not in resolved.parents:
            raise ValueError("Path escapes workspace")
        return resolved

    def _base_path(self, base: str) -> Path:
        if base == "repo":
            return self.repo.resolve()
        if base == "artifacts":
            return self.artifacts.resolve()
        if base == "logs":
            return self.logs.resolve()
        if base == "scratch":
            return self.scratch.resolve()
        raise ValueError(f"Unsupported workspace base: {base}")


class WorkspaceManager:
    def __init__(self, *, root: Path) -> None:
        self.root = root

    def prepare_for_run(self, run: RunRecord) -> Workspace:
        workspace_root = self.root / _workspace_name(run)
        workspace = Workspace(
            root=workspace_root,
            repo=workspace_root / "repo",
            artifacts=workspace_root / "artifacts",
            logs=workspace_root / "logs",
            scratch=workspace_root / "scratch",
        )
        for path in (
            workspace.root,
            workspace.repo,
            workspace.artifacts,
            workspace.logs,
            workspace.scratch,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return workspace


def _workspace_name(run: RunRecord) -> str:
    task_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", run.external_task_id).strip("-")
    return f"run-{run.id}-{task_id or 'task'}"
