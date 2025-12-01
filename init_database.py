from app.core.database import engine, Base
from app.models.user import User 

def init_database():
    try:
        Base.metadata.create_all(bind=engine)
        print("Таблицы успешно созданы в базе данных 'english_learning'")
        print("Создана таблица: users")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")

if __name__ == "__main__":
    init_database()