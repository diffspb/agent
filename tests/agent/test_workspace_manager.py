from __future__ import annotations

from pathlib import Path
import subprocess

from simple_agent.storage.models import RunRecord
from simple_agent.workspace import WorkspaceManager


def test_workspace_manager_prepares_git_worktree_for_run(tmp_path: Path) -> None:
    source_repo = _init_git_repo(tmp_path / "source-repo")
    run = _run_record(external_task_id="PROJECT-123")
    manager = WorkspaceManager(
        root=tmp_path / "workspaces",
        source_repo_root=source_repo,
    )

    workspace = manager.prepare_for_run(run)

    assert (workspace.repo / ".git").exists()
    assert (workspace.repo / "README.md").read_text(encoding="utf-8") == "seed\n"
    branch = _git_output(workspace.repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert branch == "PROJECT-123-agent"


def test_workspace_manager_reuses_existing_worktree_for_same_branch(tmp_path: Path) -> None:
    source_repo = _init_git_repo(tmp_path / "source-repo")
    run = _run_record(external_task_id="PROJECT-123")
    manager = WorkspaceManager(
        root=tmp_path / "workspaces",
        source_repo_root=source_repo,
    )

    first = manager.prepare_for_run(run)
    (first.repo / "local.txt").write_text("draft\n", encoding="utf-8")
    second = manager.prepare_for_run(run)

    assert second.repo == first.repo
    assert (second.repo / "local.txt").read_text(encoding="utf-8") == "draft\n"


def _run_record(*, external_task_id: str) -> RunRecord:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return RunRecord(
        id=1,
        tick_id=1,
        external_task_id=external_task_id,
        branch_name=f"{external_task_id}-agent",
        status="queued",
        started_at=now,
        finished_at=None,
        summary=None,
        error=None,
        created_at=now,
        updated_at=now,
    )


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "master")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "Initial commit")
    return path


def _git(repo_root: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git failed")


def _git_output(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git failed")
    return completed.stdout.strip()
