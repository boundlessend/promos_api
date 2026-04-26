from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import add_exception_handlers

settings = get_settings()

app = FastAPI(title=settings.app_name)
add_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    """возвращает статус сервиса"""

    return {"status": "ok"}
