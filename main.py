from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import Base, engine
from app.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables. Shutdown: dispose engine."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
