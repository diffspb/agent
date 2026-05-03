from __future__ import annotations

import shlex
import subprocess

from simple_agent.tools.types import JsonObject, ToolContext, ToolError, ToolResult


DENIED_COMMANDS = {
    "chmod",
    "chown",
    "dd",
    "mkfs",
    "mount",
    "reboot",
    "rm",
    "shutdown",
    "sudo",
    "umount",
}


class RunCommandTool:
    name = "run_command"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        command = input.get("command")
        executable = _command_executable(command)
        if executable in DENIED_COMMANDS:
            raise ToolError(f"Command is denied: {executable}")

        try:
            cwd = context.workspace.resolve_path(str(input.get("cwd", ".")))
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        if not cwd.exists() or not cwd.is_dir():
            raise ToolError("cwd must be an existing directory inside workspace")

        try:
            completed = subprocess.run(
                _subprocess_args(command),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=context.command_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"Command timed out after {context.command_timeout_seconds}s") from exc
        except OSError as exc:
            raise ToolError(str(exc)) from exc

        stdout, stdout_truncated = _truncate(completed.stdout, context.output_max_bytes)
        stderr, stderr_truncated = _truncate(completed.stderr, context.output_max_bytes)
        return ToolResult(
            output={
                "returncode": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            }
        )


class RunTestsTool:
    name = "run_tests"

    def run(self, input: JsonObject, context: ToolContext) -> ToolResult:
        command = input.get("command", "python -m pytest")
        return RunCommandTool().run({"command": command, "cwd": input.get("cwd", ".")}, context)


def _command_executable(value: object) -> str:
    if isinstance(value, str):
        command = value.strip()
        if not command:
            raise ToolError("command must be a non-empty list of strings or a shell command string")
        parts = shlex.split(command)
        if not parts:
            raise ToolError("command must be a non-empty list of strings or a shell command string")
        return parts[0]
    if _is_string_list(value):
        return value[0]
    raise ToolError("command must be a non-empty list of strings or a shell command string")


def _subprocess_args(value: object) -> list[str]:
    if isinstance(value, str):
        command = value.strip()
        if not command:
            raise ToolError("command must be a non-empty list of strings or a shell command string")
        return ["bash", "-lc", command]
    if _is_string_list(value):
        return value
    raise ToolError("command must be a non-empty list of strings or a shell command string")


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) for item in value)


def _truncate(value: str, max_bytes: int) -> tuple[str, bool]:
    data = value.encode("utf-8")
    if len(data) <= max_bytes:
        return value, False
    truncated = data[:max_bytes].decode("utf-8", errors="replace")
    return truncated, True
