from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.promos import router as promos_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(campaigns_router)
api_router.include_router(promos_router)
