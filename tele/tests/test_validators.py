"""
Unit тесты для основного валидатора лидов.

Запуск:
    python -m pytest tests/test_validators.py -v
"""

import pytest
import time
from unittest.mock import patch, AsyncMock, MagicMock
import os


class TestLeadValidatorUnit:
    """Unit тесты для LeadValidator с моками всех сервисов."""

    def test_validator_init(self):
        """LeadValidator должен инициализироваться."""
        from lead_validator.validators import LeadValidator
        
        validator = LeadValidator()
        assert validator is not None
        assert hasattr(validator, 'validate')

    @pytest.mark.asyncio
    async def test_honeypot_rejection(self):
        """Лид с заполненным honeypot должен отклоняться."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        # Мокаем CAPTCHA валидатор чтобы он всегда пропускал
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            validator = LeadValidator()
            lead = LeadInput(
                phone="+79991234567",
                honeypot="bot_data",
                timestamp=int(time.time()) - 10
            )
            
            result = await validator.validate(lead)
            
            assert result.success == False
            assert "honeypot" in result.rejection_reason

    @pytest.mark.asyncio
    async def test_too_fast_form_fill_rejection(self):
        """Слишком быстрое заполнение формы должно отклоняться."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        # Мокаем CAPTCHA валидатор
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            validator = LeadValidator()
            lead = LeadInput(
                phone="+79991234567",
                timestamp=int(time.time())  # Прямо сейчас = 0 секунд на заполнение
            )
            
            result = await validator.validate(lead)
            
            assert result.success == False
            assert "too_fast" in result.rejection_reason

    @pytest.mark.asyncio
    async def test_empty_phone_rejection(self):
        """Пустой телефон должен отклоняться."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            validator = LeadValidator()
            lead = LeadInput(
                phone="",
                timestamp=int(time.time()) - 10
            )
            
            result = await validator.validate(lead)
            
            assert result.success == False

    @pytest.mark.asyncio
    async def test_short_phone_rejection(self):
        """Слишком короткий телефон должен отклоняться."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            validator = LeadValidator()
            lead = LeadInput(
                phone="123",
                timestamp=int(time.time()) - 30  # Нормальное время заполнения
            )
            
            result = await validator.validate(lead)
            
            assert result.success == False

    @pytest.mark.asyncio
    async def test_execution_time_tracked(self):
        """Время выполнения должно отслеживаться."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            validator = LeadValidator()
            lead = LeadInput(
                phone="+79991234567",
                timestamp=int(time.time()) - 10
            )
            
            result = await validator.validate(lead)
            
            # Время выполнения должно быть положительным
            assert result.execution_time_ms >= 0


class TestAntibotChecks:
    """Тесты антибот-проверок."""

    @pytest.mark.asyncio
    async def test_valid_timestamp_passes(self):
        """Валидный timestamp должен проходить."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            with patch('lead_validator.validators.dadata_service') as mock_dadata:
                mock_dadata.validate_phone = AsyncMock(return_value=None)
                
                validator = LeadValidator()
                lead = LeadInput(
                    phone="+79991234567",
                    timestamp=int(time.time()) - 15  # 15 секунд назад - нормально
                )
                
                result = await validator.validate(lead)
                
                # Не должно быть отклонено из-за timestamp
                if not result.success:
                    assert "too_fast" not in (result.rejection_reason or "")

    @pytest.mark.asyncio
    async def test_very_old_timestamp_rejected(self):
        """Очень старый timestamp должен отклоняться (stale)."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            validator = LeadValidator()
            lead = LeadInput(
                phone="+79991234567",
                timestamp=int(time.time()) - 86400 * 30  # 30 дней назад
            )
            
            result = await validator.validate(lead)
            # Должен быть отклонён как stale
            assert result.success == False
            assert "stale" in (result.rejection_reason or "")


class TestDataQualityChecks:
    """Тесты проверки качества данных."""

    @pytest.mark.asyncio
    async def test_valid_russian_phone_format(self):
        """Валидный российский номер должен приниматься."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput, DaDataPhoneResponse
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            # Мокаем успешный ответ DaData
            mock_dadata_response = DaDataPhoneResponse(
                source="+79991234567",
                qc=0,
                type="Мобильный",
                provider="МТС"
            )
            
            with patch('lead_validator.validators.dadata_service') as mock_dadata:
                mock_dadata.validate_phone = AsyncMock(return_value=mock_dadata_response)
                mock_dadata.is_phone_valid = MagicMock(return_value=True)
                
                # Мокаем redis и telegram
                with patch('lead_validator.validators.redis_service') as mock_redis:
                    mock_redis.check_rate_limit = AsyncMock(return_value=True)
                    mock_redis.is_duplicate = AsyncMock(return_value=False)
                    mock_redis.mark_phone = AsyncMock()
                    
                    with patch('lead_validator.validators.telegram_notifier') as mock_tg:
                        mock_tg.send_new_lead = AsyncMock()
                        
                        with patch('lead_validator.validators.metrica_service') as mock_metrica:
                            mock_metrica.send_quality_lead = AsyncMock()
                            
                            validator = LeadValidator()
                            lead = LeadInput(
                                phone="+79991234567",
                                timestamp=int(time.time()) - 10
                            )
                            
                            result = await validator.validate(lead)
                            
                            # Должен быть принят
                            assert result.success == True

    @pytest.mark.asyncio  
    async def test_trash_phone_rejected(self):
        """Мусорный телефон (qc=2) должен отклоняться."""
        from lead_validator.validators import LeadValidator
        from lead_validator.schemas import LeadInput, DaDataPhoneResponse
        
        with patch('lead_validator.services.captcha.validate_smartcaptcha') as mock_captcha:
            mock_captcha.return_value = (True, "")
            
            with patch('lead_validator.validators.redis_service') as mock_redis:
                mock_redis.check_rate_limit = AsyncMock(return_value=True)
                mock_redis.is_duplicate = AsyncMock(return_value=False)
                
                # Мокаем ответ DaData с qc=2 (мусор)
                mock_dadata_response = DaDataPhoneResponse(
                    source="9991234567",
                    qc=2,
                    type=None
                )
                
                with patch('lead_validator.validators.dadata_service') as mock_dadata:
                    mock_dadata.validate_phone = AsyncMock(return_value=mock_dadata_response)
                    mock_dadata.is_phone_valid = MagicMock(return_value=False)
                    
                    with patch('lead_validator.validators.trash_logger') as mock_logger:
                        mock_logger.log_rejected = AsyncMock()
                        
                        validator = LeadValidator()
                        lead = LeadInput(
                            phone="9991234567",  # 10 цифр
                            timestamp=int(time.time()) - 10
                        )
                        
                        result = await validator.validate(lead)
                        
                        # Должен быть отклонён
                        assert result.success == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
