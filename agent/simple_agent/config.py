from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "simple-agent"
    environment: str = "local"
    database_path: Path = Path(".data/simple-agent.sqlite3")
    cors_allow_origin_regex: str = r"^http://(127\.0\.0\.1|localhost):[0-9]+$"
    agent_email: str = "agent@example.com"
    task_tracker_mcp_url: str = "http://127.0.0.1:8020/mcp"
    task_tracker_mcp_timeout_seconds: float = 30.0
    workspace_root: Path = Path(".data/workspaces")
    tool_command_timeout_seconds: float = 10.0
    tool_output_max_bytes: int = 32_000
    tool_file_read_max_bytes: int = 128_000


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "simple-agent"),
        environment=os.getenv("APP_ENV", "local"),
        database_path=Path(os.getenv("SIMPLE_AGENT_DB_PATH", ".data/simple-agent.sqlite3")),
        cors_allow_origin_regex=os.getenv(
            "SIMPLE_AGENT_CORS_ALLOW_ORIGIN_REGEX",
            r"^http://(127\.0\.0\.1|localhost):[0-9]+$",
        ),
        agent_email=os.getenv("AGENT_EMAIL", "agent@example.com"),
        task_tracker_mcp_url=os.getenv(
            "TASK_TRACKER_MCP_URL",
            "http://127.0.0.1:8020/mcp",
        ),
        task_tracker_mcp_timeout_seconds=float(
            os.getenv("TASK_TRACKER_MCP_TIMEOUT_SECONDS", "30.0")
        ),
        workspace_root=Path(os.getenv("WORKSPACE_ROOT", ".data/workspaces")),
        tool_command_timeout_seconds=float(
            os.getenv("TOOL_COMMAND_TIMEOUT_SECONDS", "10.0")
        ),
        tool_output_max_bytes=int(os.getenv("TOOL_OUTPUT_MAX_BYTES", "32000")),
        tool_file_read_max_bytes=int(os.getenv("TOOL_FILE_READ_MAX_BYTES", "128000")),
    )
