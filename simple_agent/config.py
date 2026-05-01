from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "simple-agent"
    environment: str = "local"


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "simple-agent"),
        environment=os.getenv("APP_ENV", "local"),
    )

