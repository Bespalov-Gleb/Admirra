#!/usr/bin/env python3
"""
Скрипт для генерации финансового токена (FinanceToken) для Яндекс.Директа.

Согласно документации Яндекс.Директа:
Финансовый токен = SHA256(мастер-токен + operation_num + "AccountManagement" + operation_name)

Где:
- мастер-токен: ваш мастер-токен из Яндекс.Директа
- operation_num: порядковый номер операции (обычно 1 для первой операции)
- operation_name: название операции ("Get", "Deposit", "Invoice", "TransferMoney")
"""

import hashlib
import sys
from typing import Optional


def generate_finance_token(
    master_token: str,
    operation_num: int = 1,
    operation_name: str = "Get"
) -> str:
    """
    Генерирует финансовый токен для Яндекс.Директа.
    
    Args:
        master_token: Мастер-токен из Яндекс.Директа
        operation_num: Порядковый номер операции (по умолчанию 1)
        operation_name: Название операции ("Get", "Deposit", "Invoice", "TransferMoney")
    
    Returns:
        Финансовый токен (SHA256 хеш)
    """
    # Конкатенация строк согласно документации
    token_string = f"{master_token}{operation_num}AccountManagement{operation_name}"
    
    # SHA256 хеширование
    finance_token = hashlib.sha256(token_string.encode('utf-8')).hexdigest()
    
    return finance_token


def main():
    """Основная функция для интерактивной генерации токена."""
    print("=" * 60)
    print("Генератор финансового токена для Яндекс.Директа")
    print("=" * 60)
    print()
    
    # Получаем мастер-токен
    if len(sys.argv) > 1:
        master_token = sys.argv[1]
    else:
        master_token = input("Введите ваш мастер-токен: ").strip()
    
    if not master_token:
        print("Ошибка: Мастер-токен не может быть пустым")
        sys.exit(1)
    
    # Получаем номер операции
    if len(sys.argv) > 2:
        try:
            operation_num = int(sys.argv[2])
        except ValueError:
            print("Ошибка: Номер операции должен быть числом")
            sys.exit(1)
    else:
        operation_num_input = input("Введите номер операции (по умолчанию 1): ").strip()
        operation_num = int(operation_num_input) if operation_num_input else 1
    
    # Получаем название операции
    valid_operations = ["Get", "Deposit", "Invoice", "TransferMoney"]
    if len(sys.argv) > 3:
        operation_name = sys.argv[3]
        if operation_name not in valid_operations:
            print(f"Предупреждение: Операция '{operation_name}' не в списке стандартных: {valid_operations}")
    else:
        print(f"\nДоступные операции: {', '.join(valid_operations)}")
        operation_name_input = input("Введите название операции (по умолчанию Get): ").strip()
        operation_name = operation_name_input if operation_name_input else "Get"
        if operation_name not in valid_operations:
            print(f"Предупреждение: Операция '{operation_name}' не в списке стандартных")
    
    # Генерируем токен
    finance_token = generate_finance_token(master_token, operation_num, operation_name)
    
    # Выводим результат
    print()
    print("=" * 60)
    print("Результат:")
    print("=" * 60)
    print(f"Мастер-токен: {master_token}")
    print(f"Номер операции: {operation_num}")
    print(f"Название операции: {operation_name}")
    print(f"Строка для хеширования: {master_token}{operation_num}AccountManagement{operation_name}")
    print()
    print(f"Финансовый токен (FinanceToken):")
    print(f"   {finance_token}")
    print()
    print("=" * 60)
    print()
    print("Инструкция по использованию:")
    print("1. Скопируйте финансовый токен выше")
    print("2. Вставьте его в профиль пользователя (поле 'FinanceToken для Яндекс.Директа')")
    print("3. Или установите переменную окружения YANDEX_DIRECT_FINANCE_TOKEN")
    print()
    print("Важно:")
    print("- Для получения баланса обычно используется операция 'Get' с номером 1")
    print("- Если баланс не появляется, попробуйте другие номера операций (2, 3, и т.д.)")
    print("- Финансовый токен должен совпадать с тем, что ожидает API Яндекс.Директа")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

