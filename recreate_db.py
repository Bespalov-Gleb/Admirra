#!/usr/bin/env python3
"""
Скрипт для полного пересоздания базы данных.
Удаляет существующую БД и создает новую со схемой из моделей SQLAlchemy.

⚠️ ВНИМАНИЕ: Этот скрипт полностью удаляет все данные из базы данных!
Используйте только для разработки и тестирования.

Использование:
    python recreate_db.py

Или в Docker:
    docker compose exec backend python recreate_db.py

Требования:
    - PostgreSQL должен быть запущен и доступен
    - DATABASE_URL должен быть установлен в переменных окружения или .env файле

Примечание:
    Скрипт создает схему БД напрямую из моделей SQLAlchemy (Base.metadata.create_all),
    без использования миграций Alembic. Это быстрее и проще для полного пересоздания БД.
"""

import os
import sys
from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def get_db_url():
    """Получить DATABASE_URL из переменных окружения."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Ошибка: DATABASE_URL не установлен в переменных окружения")
        print("   Установите DATABASE_URL или создайте .env файл")
        sys.exit(1)
    return db_url

def get_postgres_url(db_url):
    """Преобразовать DATABASE_URL в URL для подключения к postgres БД."""
    parsed = urlparse(db_url)
    # Заменяем имя БД на 'postgres' для подключения к системной БД
    new_path = '/postgres'
    postgres_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        new_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    return postgres_url

def get_db_name(db_url):
    """Извлечь имя БД из DATABASE_URL."""
    parsed = urlparse(db_url)
    # Убираем ведущий слэш
    db_name = parsed.path.lstrip('/')
    return db_name

def drop_database(engine, db_name):
    """Удалить базу данных."""
    print(f"🗑️  Удаление базы данных '{db_name}'...")
    try:
        # Сначала подключаемся к целевой БД и удаляем все типы ENUM
        # (они могут остаться после предыдущего удаления)
        try:
            db_url = get_db_url()
            db_engine = create_engine(db_url)
            with db_engine.connect() as db_conn:
                # Удаляем все типы ENUM
                db_conn.execute(text("""
                    DO $$ 
                    DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (
                            SELECT typname 
                            FROM pg_type 
                            WHERE typname IN ('userrole', 'integrationplatform', 'leadstatus')
                        ) 
                        LOOP
                            EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                        END LOOP;
                    END $$;
                """))
                db_conn.commit()
            db_engine.dispose()
        except Exception:
            # Если не удалось подключиться к БД (она уже удалена), это нормально
            pass
        
        # Завершаем все активные подключения к БД
        with engine.connect() as conn:
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                  AND pid <> pg_backend_pid();
            """))
            conn.commit()
        
        # Удаляем БД с принудительным завершением подключений (PostgreSQL 13+)
        # Если версия ниже, используем обычный DROP
        with engine.connect() as conn:
            conn.execute(text("COMMIT"))  # Завершаем транзакцию
            
            # Пробуем удалить с FORCE (PostgreSQL 13+)
            try:
                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE);'))
            except Exception:
                # Если FORCE не поддерживается, используем обычный DROP
                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}";'))
            
            conn.commit()
        
        print(f"✅ База данных '{db_name}' успешно удалена")
        return True
    except ProgrammingError as e:
        if "does not exist" in str(e) or "не существует" in str(e):
            print(f"ℹ️  База данных '{db_name}' не существует, пропускаем удаление")
            return True
        print(f"⚠️  Предупреждение при удалении БД: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при удалении БД: {e}")
        return False

def create_database(engine, db_name):
    """Создать новую базу данных."""
    print(f"🆕 Создание базы данных '{db_name}'...")
    try:
        with engine.connect() as conn:
            conn.execute(text("COMMIT"))  # Завершаем транзакцию
            conn.execute(text(f'CREATE DATABASE "{db_name}";'))
            conn.commit()
        
        print(f"✅ База данных '{db_name}' успешно создана")
        return True
    except ProgrammingError as e:
        if "already exists" in str(e) or "уже существует" in str(e):
            print(f"ℹ️  База данных '{db_name}' уже существует")
            return True
        print(f"❌ Ошибка при создании БД: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при создании БД: {e}")
        return False

def create_schema():
    """Создать схему БД напрямую из моделей SQLAlchemy (без миграций Alembic)."""
    print("📦 Создание схемы БД из моделей SQLAlchemy...")
    try:
        # Импортируем модели и Base
        # Важно: импортируем после создания БД, чтобы подключиться к правильной БД
        from core.models import Base
        from core.database import engine
        
        # Создаем все таблицы напрямую из моделей
        # Это создаст все таблицы, индексы, внешние ключи и типы ENUM
        Base.metadata.create_all(bind=engine)
        
        print("✅ Схема БД успешно создана из моделей")
        print("   Все таблицы, индексы и типы ENUM созданы")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта моделей: {e}")
        print("   Убедитесь, что вы находитесь в правильной директории")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Ошибка при создании схемы: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция."""
    print("=" * 60)
    print("🔄 Пересоздание базы данных")
    print("=" * 60)
    print()
    
    # Получаем DATABASE_URL
    db_url = get_db_url()
    db_name = get_db_name(db_url)
    postgres_url = get_postgres_url(db_url)
    
    print(f"📊 База данных: {db_name}")
    print(f"🔗 URL подключения: {postgres_url.split('@')[0]}@***")
    print()
    
    # Подключаемся к postgres БД для управления
    try:
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        print("✅ Подключение к PostgreSQL установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        print(f"   Проверьте, что PostgreSQL запущен и доступен")
        sys.exit(1)
    
    print()
    
    # Удаляем БД
    if not drop_database(engine, db_name):
        print("⚠️  Не удалось удалить БД, но продолжаем...")
        print()
    
    # Создаем БД
    if not create_database(engine, db_name):
        print("❌ Не удалось создать БД. Прерываем выполнение.")
        sys.exit(1)
    
    print()
    
    # Очищаем возможные остатки типов ENUM в новой БД
    # (на случай, если они остались от предыдущей БД)
    print("🧹 Очистка остатков типов ENUM...")
    try:
        db_url = get_db_url()
        db_engine = create_engine(db_url)
        with db_engine.connect() as db_conn:
            # Удаляем типы ENUM, если они существуют
            db_conn.execute(text("""
                DO $$ 
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT typname 
                        FROM pg_type 
                        WHERE typname IN ('userrole', 'integrationplatform', 'leadstatus')
                    ) 
                    LOOP
                        EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                    END LOOP;
                END $$;
            """))
            db_conn.commit()
        db_engine.dispose()
        print("✅ Очистка завершена")
    except Exception as e:
        # Не критично, продолжаем
        print(f"⚠️  Не удалось очистить типы ENUM (не критично): {e}")
    
    print()
    
    # Создаем схему БД напрямую из моделей (без миграций)
    if not create_schema():
        print("❌ Не удалось создать схему БД. Прерываем выполнение.")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ База данных успешно пересоздана!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

