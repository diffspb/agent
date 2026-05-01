from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "simple-agent"
    environment: str = "local"
    database_path: Path = Path(".data/simple-agent.sqlite3")
    cors_allow_origin_regex: str = r"^http://(127\.0\.0\.1|localhost):[0-9]+$"


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "simple-agent"),
        environment=os.getenv("APP_ENV", "local"),
        database_path=Path(os.getenv("SIMPLE_AGENT_DB_PATH", ".data/simple-agent.sqlite3")),
        cors_allow_origin_regex=os.getenv(
            "SIMPLE_AGENT_CORS_ALLOW_ORIGIN_REGEX",
            r"^http://(127\.0\.0\.1|localhost):[0-9]+$",
        ),
    )
