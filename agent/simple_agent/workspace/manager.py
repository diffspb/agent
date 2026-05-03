from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

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
    def __init__(self, *, root: Path, source_repo_root: Path | None = None) -> None:
        self.root = root
        self.source_repo_root = source_repo_root.resolve() if source_repo_root is not None else None

    def workspace_for_run(self, run: RunRecord) -> Workspace:
        workspace_root = self.root / _workspace_name(run)
        return Workspace(
            root=workspace_root,
            repo=workspace_root / "repo",
            artifacts=workspace_root / "artifacts",
            logs=workspace_root / "logs",
            scratch=workspace_root / "scratch",
        )

    def prepare_for_run(self, run: RunRecord) -> Workspace:
        workspace = self.workspace_for_run(run)
        workspace.root.mkdir(parents=True, exist_ok=True)
        if self.source_repo_root is None:
            workspace.repo.mkdir(parents=True, exist_ok=True)
        else:
            self._prepare_git_worktree(workspace, run)
        for path in (workspace.artifacts, workspace.logs, workspace.scratch):
            path.mkdir(parents=True, exist_ok=True)
        return workspace

    def branch_name_for_run(self, run: RunRecord) -> str:
        if run.branch_name:
            return run.branch_name
        task_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", run.external_task_id).strip("-")
        return f"{task_id or 'task'}-agent"

    def _prepare_git_worktree(self, workspace: Workspace, run: RunRecord) -> None:
        if self.source_repo_root is None:
            raise RuntimeError("source_repo_root is required for git worktree mode")
        if not _is_git_repository(self.source_repo_root):
            raise RuntimeError(f"PROJECT_REPO_ROOT is not a git repository: {self.source_repo_root}")

        branch_name = self.branch_name_for_run(run)
        if (workspace.repo / ".git").exists():
            current_branch = _git_output(workspace.repo, "rev-parse", "--abbrev-ref", "HEAD")
            if current_branch != branch_name:
                raise RuntimeError(
                    f"Workspace already exists with different branch: {current_branch}"
                )
            return

        workspace.repo.parent.mkdir(parents=True, exist_ok=True)
        if not workspace.repo.exists():
            workspace.repo.mkdir(parents=True, exist_ok=True)
        elif any(workspace.repo.iterdir()):
            raise RuntimeError(f"Workspace repo directory is not empty: {workspace.repo}")

        if _git_ref_exists(self.source_repo_root, branch_name):
            _git(self.source_repo_root, "worktree", "add", str(workspace.repo), branch_name)
        else:
            _git(
                self.source_repo_root,
                "worktree",
                "add",
                "-b",
                branch_name,
                str(workspace.repo),
                "HEAD",
            )


def _workspace_name(run: RunRecord) -> str:
    task_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", run.external_task_id).strip("-")
    return f"run-{run.id}-{task_id or 'task'}"


def _git(repo_root: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise RuntimeError(stderr or stdout or "git command failed")


def _git_output(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise RuntimeError(stderr or stdout or "git command failed")
    return completed.stdout.strip()


def _is_git_repository(repo_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _git_ref_exists(repo_root: Path, branch_name: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0
