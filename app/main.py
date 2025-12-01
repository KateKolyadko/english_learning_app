from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.models.user import User

# Импортируем роутеры
from app.api.v1.endpoints.auth import router as auth_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Создаем таблицы при запуске
@app.on_event("startup")
async def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        print("Таблицы базы данных успешно созданы/проверены")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])

# Базовые эндпоинты
@app.get("/")
def read_root():
    return {"message": "English Learning API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)