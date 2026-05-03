from __future__ import annotations

import os
from pathlib import Path
import subprocess


def test_reset_sandbox_script_creates_fresh_git_repo(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / "scripts" / "reset_sandbox.sh"
    sandbox_root = tmp_path / "sandbox"
    seed_repo_dir = project_root / "datasets" / "sandbox_repos" / "demo_python_app"

    environment = os.environ.copy()
    environment["SANDBOX_ROOT"] = str(sandbox_root)
    environment["SANDBOX_SEED_REPO_DIR"] = str(seed_repo_dir)
    environment["AGENT_EMAIL"] = "agent@example.com"

    completed = subprocess.run(
        [str(script_path)],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (sandbox_root / "repo" / ".git").exists()
    assert (sandbox_root / "repo" / ".gitignore").exists()
    assert (sandbox_root / "repo" / "demo_app" / "calculator.py").exists()
    assert not (sandbox_root / "repo" / "README.md").exists()
    assert (sandbox_root / "workspaces").is_dir()
    assert "Sandbox reset complete" in completed.stdout

    branch = subprocess.run(
        ["git", "-C", str(sandbox_root / "repo"), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert branch.returncode == 0
    assert branch.stdout.strip() == "main"

    commit_count = subprocess.run(
        ["git", "-C", str(sandbox_root / "repo"), "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert commit_count.returncode == 0
    assert commit_count.stdout.strip() == "1"
