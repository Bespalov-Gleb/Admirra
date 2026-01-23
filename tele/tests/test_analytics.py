"""
Unit тесты для сервиса аналитики (еженедельные отчёты).

Запуск:
    python -m pytest tests/test_analytics.py -v
"""

import pytest
from datetime import datetime, timedelta


class TestAnalyticsServiceUnit:
    """Unit тесты для AnalyticsService."""

    def test_analytics_service_init(self):
        """AnalyticsService должен инициализироваться."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        assert service is not None
        assert hasattr(service, 'record_lead')
        assert hasattr(service, 'generate_weekly_report')

    def test_record_lead_accepted(self):
        """Запись принятого лида."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        service.record_lead(
            utm_source="yandex",
            utm_campaign="test_campaign",
            utm_content="12345",
            rejected=False
        )
        
        stats = service.get_source_stats("yandex", "test_campaign", "12345")
        assert stats is not None
        assert stats.total_leads == 1
        assert stats.rejected_leads == 0

    def test_record_lead_rejected(self):
        """Запись отклонённого лида."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        service.record_lead(
            utm_source="google",
            utm_campaign="spam_campaign",
            utm_content="67890",
            rejected=True,
            rejection_reason="honeypot_filled"
        )
        
        stats = service.get_source_stats("google", "spam_campaign", "67890")
        assert stats is not None
        assert stats.total_leads == 1
        assert stats.rejected_leads == 1
        assert "honeypot_filled" in stats.rejection_reasons

    def test_multiple_leads_from_same_source(self):
        """Множество лидов с одного источника."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        
        # 10 принятых
        for i in range(10):
            service.record_lead(
                utm_source="yandex",
                utm_campaign="campaign1",
                rejected=False
            )
        
        # 5 отклонённых
        for i in range(5):
            service.record_lead(
                utm_source="yandex",
                utm_campaign="campaign1",
                rejected=True,
                rejection_reason="invalid_phone"
            )
        
        stats = service.get_source_stats("yandex", "campaign1")
        assert stats.total_leads == 15
        assert stats.rejected_leads == 5
        assert stats.rejection_rate == pytest.approx(33.33, rel=0.1)


class TestBadSourcesDetection:
    """Тесты обнаружения плохих источников."""

    def test_get_bad_sources_empty(self):
        """Нет плохих источников при пустой статистике."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        bad_sources = service.get_bad_sources()
        
        assert len(bad_sources) == 0

    def test_detect_bad_source(self):
        """Обнаружение источника с >50% мусора."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        
        # 10 заявок, 8 отклонённых = 80% мусора
        for i in range(2):
            service.record_lead(
                utm_source="bad_source",
                utm_campaign="spam_campaign",
                rejected=False
            )
        
        for i in range(8):
            service.record_lead(
                utm_source="bad_source",
                utm_campaign="spam_campaign",
                rejected=True,
                rejection_reason="bot"
            )
        
        bad_sources = service.get_bad_sources(min_leads=5, min_rejection_rate=50.0)
        
        assert len(bad_sources) == 1
        assert bad_sources[0].source == "bad_source"
        assert bad_sources[0].rejection_rate == 80.0

    def test_good_source_not_detected_as_bad(self):
        """Источник с <50% мусора не должен определяться как плохой."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        
        # 10 заявок, 2 отклонённых = 20% мусора
        for i in range(8):
            service.record_lead(
                utm_source="good_source",
                utm_campaign="campaign",
                rejected=False
            )
        
        for i in range(2):
            service.record_lead(
                utm_source="good_source",
                utm_campaign="campaign",
                rejected=True
            )
        
        bad_sources = service.get_bad_sources(min_leads=5, min_rejection_rate=50.0)
        
        assert len(bad_sources) == 0


class TestWeeklyReport:
    """Тесты еженедельного отчёта."""

    def test_generate_empty_report(self):
        """Генерация пустого отчёта."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        report = service.generate_weekly_report()
        
        assert report is not None
        assert report.total_leads == 0
        assert report.total_rejected == 0

    def test_generate_report_with_data(self):
        """Генерация отчёта с данными."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        
        # Добавляем тестовые данные
        for i in range(100):
            service.record_lead(
                utm_source="yandex",
                utm_campaign="campaign",
                rejected=(i % 5 == 0),  # 20% отклонённых
                rejection_reason="test" if i % 5 == 0 else None
            )
        
        report = service.generate_weekly_report()
        
        assert report.total_leads == 100
        assert report.total_rejected == 20
        assert report.overall_rejection_rate == 20.0

    def test_format_report_text(self):
        """Форматирование отчёта в текст."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        service.record_lead(utm_source="yandex", rejected=False)
        service.record_lead(utm_source="yandex", rejected=True, rejection_reason="bot")
        
        report = service.generate_weekly_report()
        text = service.format_report_text(report)
        
        assert "ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ" in text
        assert "Всего заявок" in text
        assert "Отклонено" in text


class TestClearStats:
    """Тесты очистки статистики."""

    def test_clear_stats(self):
        """Очистка статистики после отчёта."""
        from lead_validator.services.analytics import AnalyticsService
        
        service = AnalyticsService()
        service.record_lead(utm_source="test", rejected=False)
        
        assert len(service._stats) > 0
        
        service.clear_stats()
        
        assert len(service._stats) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
