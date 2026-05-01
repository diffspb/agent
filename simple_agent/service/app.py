from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from simple_agent.config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    app = FastAPI(title=app_settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": app_settings.app_name,
            "environment": app_settings.environment,
        }

    return app


app = create_app()
