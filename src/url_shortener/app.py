from contextlib import asynccontextmanager
from fastapi import FastAPI

from url_shortener.core.config import settings
from url_shortener.db.session import async_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await async_engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APPLICATION_NAME,
        version="0.1.0",
        lifespan=lifespan
    )

    return app

app = create_app()