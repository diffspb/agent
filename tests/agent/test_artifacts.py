from __future__ import annotations

from pathlib import Path
import subprocess

from simple_agent.agent.artifacts import (
    build_git_diff,
    build_snapshot_diff,
    build_workspace_diff,
    capture_repo_snapshot,
    list_artifacts,
    read_artifact,
    write_artifact,
)
from simple_agent.workspace import Workspace


def test_snapshot_diff_tracks_added_changed_and_deleted_files(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace.repo / "changed.txt").write_text("old\n", encoding="utf-8")
    (workspace.repo / "deleted.txt").write_text("remove\n", encoding="utf-8")
    before = capture_repo_snapshot(workspace, max_file_bytes=1000)

    (workspace.repo / "changed.txt").write_text("new\n", encoding="utf-8")
    (workspace.repo / "deleted.txt").unlink()
    (workspace.repo / "added.txt").write_text("add\n", encoding="utf-8")
    after = capture_repo_snapshot(workspace, max_file_bytes=1000)

    diff = build_snapshot_diff(before, after)

    assert "--- a/added.txt" in diff
    assert "+++ b/changed.txt" in diff
    assert "--- a/deleted.txt" in diff
    assert "+new" in diff
    assert "-remove" in diff


def test_capture_repo_snapshot_ignores_git_and_large_files(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace.repo / "visible.txt").write_text("ok\n", encoding="utf-8")
    (workspace.repo / "large.txt").write_text("too large\n", encoding="utf-8")
    (workspace.repo / ".git").mkdir()
    (workspace.repo / ".git" / "config").write_text("secret\n", encoding="utf-8")

    snapshot = capture_repo_snapshot(workspace, max_file_bytes=4)

    assert snapshot == {"visible.txt": "ok\n"}


def test_artifact_write_list_and_read_stay_inside_artifacts(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    artifact = write_artifact(workspace, "reports/final.diff", "diff\n")

    assert artifact.path == "reports/final.diff"
    assert [item.path for item in list_artifacts(workspace)] == ["reports/final.diff"]
    assert read_artifact(workspace, "reports/final.diff") == "diff\n"


def test_build_git_diff_uses_gitignore_and_includes_untracked_text_files(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _init_git_repo(workspace.repo)
    (workspace.repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    (workspace.repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(workspace.repo, "add", ".")
    _git(workspace.repo, "commit", "-m", "initial")

    (workspace.repo / "tracked.txt").write_text("after\n", encoding="utf-8")
    (workspace.repo / "added.txt").write_text("new\n", encoding="utf-8")
    (workspace.repo / "__pycache__").mkdir()
    (workspace.repo / "__pycache__" / "module.cpython-312.pyc").write_bytes(b"binary")

    diff = build_git_diff(workspace, max_file_bytes=1_000)

    assert "tracked.txt" in diff
    assert "added.txt" in diff
    assert "__pycache__" not in diff
    assert "module.cpython-312.pyc" not in diff


def test_build_workspace_diff_prefers_git_when_repo_is_available(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _init_git_repo(workspace.repo)
    (workspace.repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(workspace.repo, "add", "tracked.txt")
    _git(workspace.repo, "commit", "-m", "initial")

    before = capture_repo_snapshot(workspace, max_file_bytes=1_000)
    (workspace.repo / "tracked.txt").write_text("after\n", encoding="utf-8")
    (workspace.repo / "scratch.pyc").write_bytes(b"binary")
    after = capture_repo_snapshot(workspace, max_file_bytes=1_000)

    diff = build_workspace_diff(
        workspace,
        before=before,
        after=after,
        max_file_bytes=1_000,
    )

    assert "tracked.txt" in diff
    assert "scratch.pyc" in diff


def _workspace(tmp_path: Path) -> Workspace:
    workspace = Workspace(
        root=tmp_path,
        repo=tmp_path / "repo",
        artifacts=tmp_path / "artifacts",
        logs=tmp_path / "logs",
        scratch=tmp_path / "scratch",
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


def _init_git_repo(repo_root: Path) -> None:
    _git(repo_root, "init", "-b", "main")
    _git(repo_root, "config", "user.name", "Test User")
    _git(repo_root, "config", "user.email", "test@example.com")


def _git(repo_root: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout or "git command failed")
