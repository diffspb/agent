from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from simple_agent.config import Settings, load_settings
from simple_agent.service.routes_runs import router as runs_router
from simple_agent.service.routes_stats import router as stats_router
from simple_agent.service.routes_tasks import router as tasks_router
from simple_agent.storage import Repository, SqliteDatabase


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    app = FastAPI(title=app_settings.app_name)
    database = SqliteDatabase(app_settings.database_path)
    database.initialize()
    app.state.repository = Repository(database)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=app_settings.cors_allow_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": app_settings.app_name,
            "environment": app_settings.environment,
        }

    app.include_router(tasks_router)
    app.include_router(runs_router)
    app.include_router(stats_router)

    return app


app = create_app()
