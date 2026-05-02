from __future__ import annotations

from pathlib import Path

from simple_agent.agent.artifacts import (
    build_snapshot_diff,
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
