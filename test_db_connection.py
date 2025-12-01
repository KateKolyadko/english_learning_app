from app.core.database import SessionLocal
from sqlalchemy import text

def test_connection():
    try:
        db = SessionLocal()
        
        # Простой запрос для проверки подключения
        result = db.execute(text("SELECT version()"))
        db_version = result.fetchone()[0]
        print(f"Подключение к PostgreSQL успешно")
        print(f"Версия PostgreSQL: {db_version.split(',')[0]}")
        
        # Проверяем текущую базу данных
        result = db.execute(text("SELECT current_database()"))
        current_db = result.fetchone()[0]
        print(f"Текущая база данных: {current_db}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return False

if __name__ == "__main__":
    test_connection()