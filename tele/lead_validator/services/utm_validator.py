"""
Валидатор UTM-меток и источников трафика (Уровень 6).

Проверки:
1. Подозрительные UTM-метки (странные значения, отсутствие при рекламном трафике)
2. Соответствие источника и GeoIP (utm_source=yandex + IP не из России = подозрительно)
3. Чёрный список площадок (utm_content с ID мусорных площадок РСЯ)
"""

import logging
import re
from typing import Optional, Tuple, List
from dataclasses import dataclass

from lead_validator.config import settings

logger = logging.getLogger("lead_validator.utm_validator")


@dataclass
class UTMData:
    """UTM-метки из заявки."""
    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None
    content: Optional[str] = None
    term: Optional[str] = None


@dataclass  
class UTMValidationResult:
    """Результат проверки UTM."""
    is_valid: bool
    reason: Optional[str] = None
    warning: Optional[str] = None  # Не блокирует, но логируется
    risk_score: int = 0  # 0-100, где 100 = точно спам


class UTMValidator:
    """
    Валидатор UTM-меток для выявления фрода и накрутки.
    
    Уровни проверки:
    1. Формат UTM (странные символы, слишком длинные значения)
    2. Соответствие источника и географии
    3. Чёрный список площадок РСЯ
    """
    
    def __init__(self):
        # Известные рекламные источники, требующие российский IP
        self.russian_sources = {"yandex", "ya", "direct", "yandex-direct"}
        
        # Чёрный список площадок (ID или паттерны в utm_content)
        # Заполняется из конфигурации
        self.blacklisted_placements: List[str] = settings.UTM_BLACKLISTED_PLACEMENTS
        
        # Подозрительные паттерны в UTM
        self.suspicious_patterns = [
            r"^test",  # test, testing, etc.
            r"^debug",
            r"^\d+$",  # только цифры
            r"^[a-z]$",  # одна буква
            r"undefined",
            r"null",
            r"\{.*\}",  # шаблонные переменные {keyword}
        ]
        
        # Страны, откуда НЕ должен идти трафик yandex (упрощённый список)
        # В реальности нужен GeoIP сервис
        self.non_russian_countries = {"UA", "BY", "KZ", "UZ", "GE", "AM", "AZ"}
        
        logger.info(
            f"UTM Validator initialized with {len(self.blacklisted_placements)} "
            f"blacklisted placements"
        )
    
    def validate(
        self, 
        utm: UTMData, 
        client_ip: Optional[str] = None,
        geo_country: Optional[str] = None
    ) -> UTMValidationResult:
        """
        Проверить UTM-метки.
        
        Args:
            utm: UTM данные из заявки
            client_ip: IP клиента (для логирования)
            geo_country: Код страны (RU, UA, etc.) если известен
            
        Returns:
            UTMValidationResult с результатом проверки
        """
        risk_score = 0
        warnings = []
        
        # === Проверка 1: Формат UTM ===
        format_result = self._check_format(utm)
        if format_result:
            risk_score += 20
            warnings.append(format_result)
        
        # === Проверка 2: Чёрный список площадок ===
        blacklist_result = self._check_blacklist(utm)
        if blacklist_result:
            logger.info(f"UTM blacklisted: {blacklist_result} from IP {client_ip}")
            return UTMValidationResult(
                is_valid=False,
                reason=f"blacklisted_placement:{blacklist_result}",
                risk_score=100
            )
        
        # === Проверка 3: Соответствие источника и географии ===
        geo_result = self._check_geo_match(utm, geo_country)
        if geo_result:
            risk_score += 50
            warnings.append(geo_result)
        
        # === Проверка 4: Подозрительные паттерны ===
        pattern_result = self._check_suspicious_patterns(utm)
        if pattern_result:
            risk_score += 30
            warnings.append(pattern_result)
        
        # Итоговый результат
        if risk_score >= 80:
            return UTMValidationResult(
                is_valid=False,
                reason="high_spam_risk",
                risk_score=risk_score
            )
        elif risk_score >= 40:
            return UTMValidationResult(
                is_valid=True,
                warning="; ".join(warnings),
                risk_score=risk_score
            )
        else:
            return UTMValidationResult(
                is_valid=True,
                risk_score=risk_score
            )
    
    def _check_format(self, utm: UTMData) -> Optional[str]:
        """Проверить формат UTM-меток."""
        issues = []
        
        # Проверяем каждое поле
        for field_name, value in [
            ("source", utm.source),
            ("medium", utm.medium),
            ("campaign", utm.campaign),
            ("content", utm.content),
            ("term", utm.term)
        ]:
            if not value:
                continue
                
            # Слишком длинное значение
            if len(value) > 200:
                issues.append(f"{field_name}_too_long")
            
            # Странные символы (кроме стандартных)
            if re.search(r'[<>"\']', value):
                issues.append(f"{field_name}_invalid_chars")
        
        return "; ".join(issues) if issues else None
    
    def _check_blacklist(self, utm: UTMData) -> Optional[str]:
        """Проверить чёрный список площадок."""
        if not self.blacklisted_placements:
            return None
        
        # Проверяем utm_content (обычно содержит ID площадки)
        if utm.content:
            content_lower = utm.content.lower()
            for placement in self.blacklisted_placements:
                if placement.lower() in content_lower:
                    return placement
        
        # Проверяем utm_campaign (иногда ID площадки там)
        if utm.campaign:
            campaign_lower = utm.campaign.lower()
            for placement in self.blacklisted_placements:
                if placement.lower() in campaign_lower:
                    return placement
        
        return None
    
    def _check_geo_match(
        self, 
        utm: UTMData, 
        geo_country: Optional[str]
    ) -> Optional[str]:
        """
        Проверить соответствие источника и географии.
        
        utm_source=yandex но IP из Украины = подозрительно,
        т.к. Яндекс.Директ показывает рекламу преимущественно в России.
        """
        if not geo_country or not utm.source:
            return None
        
        source_lower = utm.source.lower()
        
        # Проверяем российские источники
        for russian_source in self.russian_sources:
            if russian_source in source_lower:
                # Источник российский, проверяем страну
                if geo_country.upper() in self.non_russian_countries:
                    return f"geo_mismatch:source={utm.source},country={geo_country}"
        
        return None
    
    def _check_suspicious_patterns(self, utm: UTMData) -> Optional[str]:
        """Проверить подозрительные паттерны в UTM."""
        issues = []
        
        for field_name, value in [
            ("source", utm.source),
            ("medium", utm.medium),
            ("campaign", utm.campaign)
        ]:
            if not value:
                continue
            
            value_lower = value.lower()
            for pattern in self.suspicious_patterns:
                if re.search(pattern, value_lower):
                    issues.append(f"{field_name}_suspicious")
                    break
        
        return "; ".join(issues) if issues else None
    
    def add_to_blacklist(self, placement: str) -> None:
        """Добавить площадку в чёрный список (runtime)."""
        if placement not in self.blacklisted_placements:
            self.blacklisted_placements.append(placement)
            logger.info(f"Added placement to blacklist: {placement}")


# Глобальный экземпляр
utm_validator = UTMValidator()
