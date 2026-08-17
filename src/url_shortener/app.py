from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.api import api_router
from url_shortener.core.config import settings
from url_shortener.db.session import async_engine, get_db

logger = logging.getLogger(settings.APPLICATION_NAME)

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

    app.include_router(api_router, prefix=settings.API_VERSION_PREFIX)

    @app.get("/health", tags=["health"])
    async def health(db: AsyncSession = Depends(get_db)):
        try:
            await db.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}
        except Exception as exc:
            logger.error("DATABASE HEALTH CHECK FAILED", exc_info=exc)
            return JSONResponse(
                status_code=503,
                content={"status": "error", "database": "unreachable"}
            )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("UNHANDLED EXCEPTION", extra={"path": request.url.path})
        detail = str(exc) if settings.IS_DEV_ENV else "INTERNAL SERVER ERROR"
        return JSONResponse(status_code=500, content={"error": detail})

    return app

app = create_app()