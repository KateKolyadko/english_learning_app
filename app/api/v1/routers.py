"""
Главный роутер API версии 1.
Собирает все роутеры из endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, analysis

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
