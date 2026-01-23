"""
Unit тесты для Pydantic схем.

Запуск:
    python -m pytest tests/test_schemas.py -v
"""

import pytest
from datetime import datetime
from pydantic import ValidationError


class TestLeadInput:
    """Тесты для схемы LeadInput."""

    def test_minimal_lead_input(self):
        """Минимальный лид с только телефоном."""
        from lead_validator.schemas import LeadInput
        
        lead = LeadInput(phone="+79991234567")
        
        assert lead.phone == "+79991234567"
        assert lead.email is None
        assert lead.name is None

    def test_full_lead_input(self):
        """Полный лид со всеми полями."""
        from lead_validator.schemas import LeadInput
        
        lead = LeadInput(
            phone="+79991234567",
            email="test@example.com",
            name="Иван Иванов",
            timestamp=1700000000,
            utm_source="yandex",
            utm_medium="cpc",
            utm_campaign="test"
        )
        
        assert lead.phone == "+79991234567"
        assert lead.email == "test@example.com"
        assert lead.utm_source == "yandex"

    def test_phone_normalization(self):
        """Телефон должен нормализоваться."""
        from lead_validator.schemas import LeadInput
        
        # Телефон с пробелами и скобками
        lead = LeadInput(phone="+7 (999) 123-45-67")
        
        # Должен остаться только +79991234567
        assert lead.phone == "+79991234567"

    def test_phone_normalization_8_start(self):
        """Телефон начинающийся с 8 должен нормализоваться."""
        from lead_validator.schemas import LeadInput
        
        lead = LeadInput(phone="8 999 123 45 67")
        
        # Только цифры остаются
        assert lead.phone == "89991234567"

    def test_empty_phone_allowed(self):
        """Пустой телефон должен проходить (отсеивается валидатором)."""
        from lead_validator.schemas import LeadInput
        
        lead = LeadInput(phone="")
        assert lead.phone == ""

    def test_honeypot_field(self):
        """Honeypot поле должно сохраняться."""
        from lead_validator.schemas import LeadInput
        
        lead = LeadInput(
            phone="+79991234567",
            honeypot="bot_filled_this"
        )
        
        assert lead.honeypot == "bot_filled_this"

    def test_captcha_tokens(self):
        """CAPTCHA токены должны сохраняться."""
        from lead_validator.schemas import LeadInput
        
        lead = LeadInput(
            phone="+79991234567",
            cf_turnstile_response="turnstile_token_123",
            smart_token="smartcaptcha_token_456"
        )
        
        assert lead.cf_turnstile_response == "turnstile_token_123"
        assert lead.smart_token == "smartcaptcha_token_456"


class TestValidationResult:
    """Тесты для схемы ValidationResult."""

    def test_success_result(self):
        """Успешный результат валидации."""
        from lead_validator.schemas import ValidationResult
        
        result = ValidationResult(
            success=True,
            lead_id="lead_12345",
            execution_time_ms=45.5
        )
        
        assert result.success == True
        assert result.lead_id == "lead_12345"
        assert result.rejection_reason is None

    def test_failed_result(self):
        """Неуспешный результат с причиной отказа."""
        from lead_validator.schemas import ValidationResult
        
        result = ValidationResult(
            success=False,
            rejection_reason="honeypot_filled",
            execution_time_ms=5.2
        )
        
        assert result.success == False
        assert result.rejection_reason == "honeypot_filled"

    def test_result_with_phone_details(self):
        """Результат с деталями телефона."""
        from lead_validator.schemas import ValidationResult
        
        result = ValidationResult(
            success=True,
            execution_time_ms=120.0,
            phone_type="Мобильный",
            phone_provider="МТС",
            phone_region="Москва",
            dadata_qc=0
        )
        
        assert result.phone_type == "Мобильный"
        assert result.phone_provider == "МТС"
        assert result.dadata_qc == 0


class TestRejectedLead:
    """Тесты для схемы RejectedLead."""

    def test_minimal_rejected_lead(self):
        """Минимальный отклонённый лид."""
        from lead_validator.schemas import RejectedLead
        
        lead = RejectedLead(
            phone="+79991234567",
            rejection_reason="too_fast_form_fill"
        )
        
        assert lead.phone == "+79991234567"
        assert lead.rejection_reason == "too_fast_form_fill"
        assert isinstance(lead.created_at, datetime)

    def test_rejected_lead_with_utm(self):
        """Отклонённый лид с UTM метками."""
        from lead_validator.schemas import RejectedLead
        
        lead = RejectedLead(
            phone="+79991234567",
            rejection_reason="blacklisted_utm",
            utm_source="suspicious_source",
            utm_medium="cpc",
            utm_campaign="spam_campaign"
        )
        
        assert lead.utm_source == "suspicious_source"
        assert lead.utm_campaign == "spam_campaign"

    def test_rejected_lead_with_dadata(self):
        """Отклонённый лид с данными DaData."""
        from lead_validator.schemas import RejectedLead
        
        lead = RejectedLead(
            phone="абракадабра",
            rejection_reason="invalid_phone",
            dadata_qc=2,
            phone_type=None
        )
        
        assert lead.dadata_qc == 2
        assert lead.phone_type is None


class TestDaDataPhoneResponse:
    """Тесты для схемы DaDataPhoneResponse."""

    def test_qc_codes(self):
        """Проверка различных QC кодов."""
        from lead_validator.schemas import DaDataPhoneResponse
        
        # qc=0: распознан уверенно (Россия)
        response_0 = DaDataPhoneResponse(source="+79991234567", qc=0)
        assert response_0.qc == 0
        
        # qc=1: распознан с допущениями
        response_1 = DaDataPhoneResponse(source="+79991234567", qc=1)
        assert response_1.qc == 1
        
        # qc=2: мусор
        response_2 = DaDataPhoneResponse(source="trash", qc=2)
        assert response_2.qc == 2
        
        # qc=7: иностранный
        response_7 = DaDataPhoneResponse(source="+1234567890", qc=7)
        assert response_7.qc == 7

    def test_phone_types(self):
        """Проверка типов телефонов."""
        from lead_validator.schemas import DaDataPhoneResponse
        
        mobile = DaDataPhoneResponse(source="+79991234567", type="Мобильный")
        assert mobile.type == "Мобильный"
        
        landline = DaDataPhoneResponse(source="+74951234567", type="Стационарный")
        assert landline.type == "Стационарный"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
