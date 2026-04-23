#!/bin/bash
# Скрипт для полного пересоздания базы данных
# Удаляет существующую БД и создает новую со схемой из моделей SQLAlchemy

set -e  # Прерывать выполнение при ошибке

echo "============================================================"
echo "🔄 Пересоздание базы данных"
echo "============================================================"
echo ""

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Ошибка: DATABASE_URL не установлен"
    echo "   Установите DATABASE_URL или создайте .env файл"
    exit 1
fi

# Извлекаем параметры подключения из DATABASE_URL
# Формат: postgresql://user:password@host:port/dbname
DB_URL_REGEX="postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)"
if [[ $DATABASE_URL =~ $DB_URL_REGEX ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
else
    echo "❌ Ошибка: неверный формат DATABASE_URL"
    echo "   Ожидается: postgresql://user:password@host:port/dbname"
    exit 1
fi

echo "📊 База данных: $DB_NAME"
echo "🔗 Хост: $DB_HOST:$DB_PORT"
echo "👤 Пользователь: $DB_USER"
echo ""

# Экспортируем пароль для psql
export PGPASSWORD="$DB_PASS"

# Подключаемся к postgres БД для управления
echo "🔌 Подключение к PostgreSQL..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Ошибка подключения к PostgreSQL"
    echo "   Проверьте, что PostgreSQL запущен и доступен"
    exit 1
fi
echo "✅ Подключение установлено"
echo ""

# Завершаем все активные подключения к БД
echo "🔒 Завершение активных подключений к БД '$DB_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
EOF
echo ""

# Удаляем БД
echo "🗑️  Удаление базы данных '$DB_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>&1
if [ $? -eq 0 ]; then
    echo "✅ База данных '$DB_NAME' успешно удалена"
else
    echo "⚠️  Предупреждение при удалении БД (возможно, БД не существовала)"
fi
echo ""

# Создаем БД
echo "🆕 Создание базы данных '$DB_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";" 2>&1
if [ $? -eq 0 ]; then
    echo "✅ База данных '$DB_NAME' успешно создана"
else
    echo "❌ Ошибка при создании БД"
    exit 1
fi
echo ""

# Создаем схему БД напрямую из моделей SQLAlchemy
echo "📦 Создание схемы БД из моделей SQLAlchemy..."
python -c "
from core.models import Base
from core.database import engine
Base.metadata.create_all(bind=engine)
print('✅ Схема БД успешно создана из моделей')
"

if [ $? -eq 0 ]; then
    echo "✅ Схема БД успешно создана"
else
    echo "❌ Ошибка при создании схемы БД"
    exit 1
fi
echo ""

echo "============================================================"
echo "✅ База данных успешно пересоздана!"
echo "============================================================"

