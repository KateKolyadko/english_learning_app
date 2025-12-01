import subprocess
import sys

def run_sql_command(command):
    """Выполняет SQL команду через docker exec"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'english_learning_postgres',
            'psql', '-U', 'postgres', '-d', 'english_learning', '-c', command
        ], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Ошибка: {e}")
        print(f"Stderr: {e.stderr}")
        return None

print("🔧 Создаем таблицы через subprocess...")

sql_commands = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR NOT NULL UNIQUE,
        hashed_password VARCHAR NOT NULL,
        full_name VARCHAR,
        is_active BOOLEAN DEFAULT TRUE,
        is_superuser BOOLEAN DEFAULT FALSE,
        current_level VARCHAR DEFAULT 'beginner',
        target_level VARCHAR DEFAULT 'intermediate',
        learning_goals TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_users_full_name ON users(full_name);"
]

for i, command in enumerate(sql_commands, 1):
    print(f"Выполняем команду {i}...")
    result = run_sql_command(command)
    if result:
        print(f"Команда {i} выполнена успешно")
    else:
        print(f"Ошибка выполнения команды {i}")

print("Все таблицы созданы!")