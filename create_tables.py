from app.core.database import engine, Base
from app.models.user import User
from app.models.analysis import EssayAnalysis, TestSession, TestAnswer, UserProgress
from sqlalchemy import inspect

print("Проверка текущей структуры базы данных...")

inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Таблицы в БД: {tables}")

if 'users' in tables:
    columns = inspector.get_columns('users')
    print("\nСтолбцы в таблице users:")
    for col in columns:
        print(f"  - {col['name']} ({col['type']})")

print("\nУдаление существующих таблиц...")
Base.metadata.drop_all(bind=engine)

print("Создание новых таблиц...")
Base.metadata.create_all(bind=engine)

print("\nБаза данных обновлена успешно!")