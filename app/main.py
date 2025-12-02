from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import api_router as api_router_v1
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Настройка CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Подключаем роутер API v1
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "English Learning API", 
        "version": settings.VERSION,
        "docs": "/docs" if settings.DEBUG else None,
        "openapi": f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}