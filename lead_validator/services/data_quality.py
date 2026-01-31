"""
Чёрный список одноразовых email-доменов и стоп-лист имён.

Уровень 2 и 4 по ТЗ:
- Disposable email: mailinator, tempmail, guerrillamail и т.д.
- Мусорные имена: test, asdf, qwerty и т.д.
"""

import logging
import re
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("lead_validator.data_quality")


# === ЧЁРНЫЙ СПИСОК ОДНОРАЗОВЫХ EMAIL ДОМЕНОВ ===
# Топ-100+ самых популярных disposable email сервисов
DISPOSABLE_EMAIL_DOMAINS = {
    # Популярные одноразовые
    "mailinator.com", "mailinator.net", "mailinator.org",
    "guerrillamail.com", "guerrillamail.org", "guerrillamail.net",
    "guerrillamail.biz", "guerrillamailblock.com",
    "10minutemail.com", "10minutemail.net", "10minutemail.org",
    "tempmail.com", "tempmail.net", "temp-mail.org", "temp-mail.ru",
    "throwaway.email", "throwawaymail.com",
    "fakeinbox.com", "fakemailgenerator.com",
    "getnada.com", "nada.email",
    "sharklasers.com", "spam4.me", "grr.la", "guerrillamail.info",
    "yopmail.com", "yopmail.fr", "yopmail.net",
    "maildrop.cc", "mailsac.com",
    "dispostable.com", "disposablemail.com",
    "tempr.email", "discard.email",
    "emailondeck.com", "inboxkitten.com",
    "mohmal.com", "tempail.com",
    "mailcatch.com", "mailnesia.com",
    "trashmail.com", "trashmail.net", "trashmail.org",
    "spam.la", "spamgourmet.com",
    "mytemp.email", "mt2015.com",
    "tmpmail.org", "tmpmail.net",
    "getairmail.com", "33mail.com",
    "guerrillamail.de", "guerrillamailblock.com",
    "burnermail.io", "emailfake.com",
    "fakemail.net", "fakebox.org",
    "mintemail.com", "tempmailaddress.com",
    "dropmail.me", "emkei.cz",
    "mailtemp.net", "tempsky.com",
    "spamavert.com", "nomail.xl.cx",
    "bobmail.info", "mailexpire.com",
    "mailmoat.com", "incognitomail.com",
    "anonymbox.com", "notmailinator.com",
    "mailhazard.com", "mailhazard.us",
    "spambox.us", "spambox.xyz",
    "throwam.com", "getonemail.com",
    "emailtemporario.com.br", "tempinbox.com",
    "mailforspam.com", "trashemail.de",
    "mvrht.com", "filzmail.com",
    "crazymailing.com", "jetable.org",
    "mailnator.com", "bugmenot.com",
    "classesmail.com", "deadaddress.com",
    "despammed.com", "devnullmail.com",
    "dodgeit.com", "dodgit.com",
    "dotmsg.com", "e4ward.com",
    "emailias.com", "emailsensei.com",
    "emailthe.net", "emailtmp.com",
    "emailwarden.com", "enterto.com",
    "ephemail.net", "evopo.com",
    "explodemail.com", "express.net.ua",
    "eyepaste.com", "fastacura.com",
    "filzmail.com", "fizmail.com",
    # Русские одноразовые
    "crazymailing.com", "temp-mail.ru",
    "dropmail.me", "emailna.co",
    "mailbox.in.ua", "mail.tm",
    "mohmal.in", "tempmailo.com",
}

# === СТОП-ЛИСТ МУСОРНЫХ ИМЁН ===
GARBAGE_NAMES = {
    # Тестовые
    "test", "тест", "testing", "тестовый",
    "demo", "демо", "example", "пример",
    "sample", "dummy", "fake", "фейк",
    
    # Клавиатурные последовательности
    "asdf", "asdfg", "asdfgh", "asdfghjk",
    "qwerty", "qwert", "qwertyuiop",
    "йцукен", "йцукенг", "йцукенгш",
    "zxcvbn", "zxcvb",
    
    # Бессмысленные
    "xxx", "ххх", "aaa", "ааа",
    "bbb", "ббб", "ccc", "ссс",
    "123", "1234", "12345",
    "abc", "абв", "abcd",
    "none", "null", "undefined",
    "na", "n/a", "нет", "no",
    
    # Популярные фейки
    "john doe", "jane doe",
    "вася пупкин", "иван иванов", "петр петров",
    "vasia pupkin", "ivan ivanov",
    "user", "пользователь", "клиент", "client",
    "customer", "guest", "гость",
    "admin", "administrator", "root",
    "аноним", "anonymous", "anon",
}

# Паттерны подозрительных имён (регулярные выражения)
SUSPICIOUS_NAME_PATTERNS = [
    r'^(.)\1{3,}$',          # Повторяющиеся символы: аааа, бббб
    r'^[0-9]+$',              # Только цифры
    r'^\d',                   # Начинается с цифры
    r'[0-9]{4,}',             # 4+ цифр подряд
    r'[@#$%^&*()+=\[\]{}|\\]', # Спецсимволы (кроме дефиса и апострофа)
    r'[\U0001F600-\U0001F64F]', # Эмодзи
    r'[\U0001F300-\U0001F5FF]', # Символы и пиктограммы
    r'^[a-z]{1,2}$',          # Слишком короткие латинские
    r'^[а-яё]{1,2}$',         # Слишком короткие кириллические
]


@dataclass
class DataQualityResult:
    """Результат проверки качества данных."""
    is_valid: bool
    rejection_reason: Optional[str] = None
    warning: Optional[str] = None


class DataQualityValidator:
    """
    Проверка качества данных: email и имена.
    
    Проверяет:
    - Email на disposable домены
    - Имя на стоп-лист и подозрительные паттерны
    """
    
    def __init__(self):
        self.disposable_domains = DISPOSABLE_EMAIL_DOMAINS.copy()
        self.garbage_names = GARBAGE_NAMES.copy()
        self.name_patterns = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_NAME_PATTERNS]
    
    def validate_email_domain(self, email: Optional[str]) -> DataQualityResult:
        """
        Проверить email на одноразовый домен.
        
        Args:
            email: Email адрес
            
        Returns:
            DataQualityResult
        """
        if not email:
            return DataQualityResult(is_valid=True)  # Email необязателен
        
        # Извлекаем домен
        if "@" not in email:
            return DataQualityResult(
                is_valid=False,
                rejection_reason="email_invalid_format"
            )
        
        domain = email.split("@")[-1].lower().strip()
        
        # Проверяем в чёрном списке
        if domain in self.disposable_domains:
            logger.info(f"Disposable email domain detected: {domain}")
            return DataQualityResult(
                is_valid=False,
                rejection_reason=f"email_disposable:{domain}"
            )
        
        return DataQualityResult(is_valid=True)
    
    def validate_name(self, name: Optional[str]) -> DataQualityResult:
        """
        Проверить имя на мусорные значения.
        
        Args:
            name: Имя клиента
            
        Returns:
            DataQualityResult
        """
        if not name:
            return DataQualityResult(is_valid=True)  # Имя может быть пустым
        
        name_clean = name.strip().lower()
        
        # Проверка длины
        if len(name_clean) < 2:
            logger.info(f"Name too short: '{name}'")
            return DataQualityResult(
                is_valid=False,
                rejection_reason="name_too_short"
            )
        
        # Проверка в стоп-листе
        if name_clean in self.garbage_names:
            logger.info(f"Garbage name detected: '{name}'")
            return DataQualityResult(
                is_valid=False,
                rejection_reason=f"name_garbage:{name_clean}"
            )
        
        # Проверка по паттернам
        for pattern in self.name_patterns:
            if pattern.search(name_clean):
                logger.info(f"Suspicious name pattern in: '{name}'")
                return DataQualityResult(
                    is_valid=False,
                    rejection_reason="name_suspicious_pattern"
                )
        
        # Проверка на повторяющиеся символы (3+ подряд)
        if re.search(r'(.)\1{2,}', name_clean):
            # Но разрешаем нормальные имена с двойными буквами (Анна, Алла)
            if re.search(r'(.)\1{3,}', name_clean):
                logger.info(f"Repeating chars in name: '{name}'")
                return DataQualityResult(
                    is_valid=False,
                    rejection_reason="name_repeating_chars"
                )
        
        return DataQualityResult(is_valid=True)
    
    def add_disposable_domain(self, domain: str):
        """Добавить домен в чёрный список."""
        self.disposable_domains.add(domain.lower())
        logger.info(f"Added disposable domain: {domain}")
    
    def add_garbage_name(self, name: str):
        """Добавить имя в стоп-лист."""
        self.garbage_names.add(name.lower())
        logger.info(f"Added garbage name: {name}")
    
    @staticmethod
    def normalize_name(name: Optional[str]) -> Optional[str]:
        """
        Нормализация имени для корректного поиска дубликатов.
        
        Выполняет:
        - Приведение к единому регистру (title case)
        - Удаление лишних пробелов
        - Замена ё на е
        - Удаление спецсимволов (кроме дефиса и апострофа)
        
        Args:
            name: Исходное имя
            
        Returns:
            Нормализованное имя или None
        """
        if not name:
            return None
        
        # Удаляем лишние пробелы
        normalized = " ".join(name.split())
        
        # Заменяем ё на е
        normalized = normalized.replace("ё", "е").replace("Ё", "Е")
        
        # Приводим к title case (первая буква заглавная, остальные строчные)
        normalized = normalized.title()
        
        # Удаляем спецсимволы (кроме дефиса и апострофа)
        normalized = re.sub(r"[^\w\s\-']", "", normalized)
        
        return normalized.strip() if normalized.strip() else None


# Глобальный экземпляр
data_quality_validator = DataQualityValidator()

