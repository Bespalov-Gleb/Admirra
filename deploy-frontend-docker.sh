#!/bin/bash
set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Сборка и деплой Frontend через Docker ===${NC}"

# Переменные
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/admin-panel-vue-main/admin-panel-vue-main"
DEPLOY_DIR="/var/www/admirra.ru"
BACKUP_DIR="/var/www/admirra.ru.backup.$(date +%Y%m%d_%H%M%S)"
TEMP_CONTAINER="temp-frontend-$(date +%s)"
TEMP_IMAGE="temp-frontend-build"

# Проверка что мы в правильной директории
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}ОШИБКА: Директория frontend не найдена: $FRONTEND_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}Шаг 1: Сборка Docker образа...${NC}"
cd "$FRONTEND_DIR"
docker build -t "$TEMP_IMAGE" .

echo -e "${YELLOW}Шаг 2: Извлечение файлов из образа...${NC}"
docker create --name "$TEMP_CONTAINER" "$TEMP_IMAGE"
docker cp "$TEMP_CONTAINER:/usr/share/nginx/html" /tmp/new-frontend-$(date +%s)
EXTRACT_DIR="/tmp/new-frontend-$(date +%s)"

# Найти последний созданный каталог
EXTRACT_DIR=$(ls -td /tmp/new-frontend-* | head -1)

if [ ! -d "$EXTRACT_DIR" ] || [ -z "$(ls -A $EXTRACT_DIR)" ]; then
    echo -e "${RED}ОШИБКА: Не удалось извлечь файлы из Docker образа!${NC}"
    docker rm "$TEMP_CONTAINER" 2>/dev/null || true
    docker rmi "$TEMP_IMAGE" 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Файлы извлечены в: $EXTRACT_DIR${NC}"

echo -e "${YELLOW}Шаг 3: Создание бэкапа старой версии...${NC}"
if [ -d "$DEPLOY_DIR" ] && [ "$(ls -A $DEPLOY_DIR)" ]; then
    sudo mv "$DEPLOY_DIR" "$BACKUP_DIR"
    echo -e "${GREEN}✓ Бэкап создан: $BACKUP_DIR${NC}"
else
    echo -e "${YELLOW}Старая версия не найдена, пропускаю бэкап${NC}"
fi

echo -e "${YELLOW}Шаг 4: Копирование новых файлов...${NC}"
sudo mkdir -p "$DEPLOY_DIR"
sudo cp -r "$EXTRACT_DIR"/* "$DEPLOY_DIR/"

echo -e "${YELLOW}Шаг 5: Установка прав доступа...${NC}"
sudo chown -R www-data:www-data "$DEPLOY_DIR"
sudo chmod -R 755 "$DEPLOY_DIR"

echo -e "${YELLOW}Шаг 6: Проверка файлов...${NC}"
if [ ! -f "$DEPLOY_DIR/index.html" ]; then
    echo -e "${RED}ОШИБКА: index.html не найден в $DEPLOY_DIR!${NC}"
    docker rm "$TEMP_CONTAINER" 2>/dev/null || true
    docker rmi "$TEMP_IMAGE" 2>/dev/null || true
    rm -rf "$EXTRACT_DIR"
    exit 1
fi

FILE_COUNT=$(find "$DEPLOY_DIR" -type f | wc -l)
echo -e "${GREEN}✓ Скопировано файлов: $FILE_COUNT${NC}"

echo -e "${YELLOW}Шаг 7: Очистка временных файлов...${NC}"
docker rm "$TEMP_CONTAINER" 2>/dev/null || true
docker rmi "$TEMP_IMAGE" 2>/dev/null || true
rm -rf "$EXTRACT_DIR"
echo -e "${GREEN}✓ Временные файлы удалены${NC}"

echo -e "${YELLOW}Шаг 8: Проверка конфига Nginx...${NC}"
if sudo nginx -t 2>/dev/null; then
    echo -e "${GREEN}✓ Конфиг Nginx валиден${NC}"
    echo -e "${YELLOW}Шаг 9: Перезагрузка Nginx...${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx перезагружен${NC}"
else
    echo -e "${RED}ОШИБКА: Конфиг Nginx невалиден!${NC}"
    sudo nginx -t
    exit 1
fi

echo -e "${GREEN}=== Деплой завершен успешно! ===${NC}"
echo -e "${GREEN}Frontend доступен по адресу: https://admirra.ru${NC}"
echo -e "${YELLOW}Бэкап сохранен в: $BACKUP_DIR${NC}"

