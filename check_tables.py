from app.core.database import SessionLocal
from sqlalchemy import text

def check_tables():
    try:
        db = SessionLocal()
        
        # Проверяем существование таблицы users
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """))
        users_table_exists = result.fetchone()[0]
        
        print(f"Таблица 'users' существует: {users_table_exists}")
        
        if users_table_exists:
            # Проверяем структуру таблицы
            result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print("Структура таблицы 'users':")
            for column in columns:
                print(f"  - {column[0]}: {column[1]}")
        
        db.close()
        
    except Exception as e:
        print(f"Ошибка при проверке таблиц: {e}")

if __name__ == "__main__":
    check_tables()