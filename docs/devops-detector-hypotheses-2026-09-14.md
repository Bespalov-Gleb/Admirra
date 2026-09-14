# T03/T07 — AI-обогащение детектора без удержания SQL-соединения

Дата работы: 14.09.2026. Подготовленная реализация для durable sync, не production rollout и не полное закрытие T03/T07/T10.

## Исследованный путь

`backend_api/sync_jobs.py:_run_job_sync` вызывает `automation/sync.py:sync_integration`. После статистики вызывается детерминированный детектор в SAVEPOINT, затем `refresh_hypothesis_texts_for_client(db, ...)`: запросы LLM выполнялись с открытой SQL-транзакцией/нефиксированными результатами детектора. Это общий участок разных рекламных каналов. Сами HTTP-запросы Direct/VK/Avito выше по функции также смешаны с DB IO и остаются отдельной работой.

## Что изменено

1. Новый `_sync_attempt` при наличии durable execution fence просит `sync_integration(..., defer_hypotheses=True)` не выполнять старый LLM-шаг. Без fence старый контракт сохранён.
2. Только после успешного завершения статистики и детектора сохраняется завершённая SQL-работа; соединение вызывающей Session возвращается в пул. Это граница завершённого этапа, не принудительный commit внутри незавершённого HTTP-цикла.
3. `automation/detector_hypothesis_work.py` читает снимки подходящих алертов короткой сессией, закрывает её и вызывает LLM без ORM-объектов/занятого соединения. HTTP-клиент закрывается через async context manager.
4. Для непустого ответа новая короткая транзакция блокирует Client → User → DetectorAlert, проверяет владельца, active/enabled/global enabled и полное совпадение исходной записи алерта. Обновившиеся цифры/meta, новый запуск детектора, смена владельца, закрытие/удаление, новый текст, пауза/отключение не перезаписываются. Commit дополнительно проверяет durable lease через существующий fence.
5. Сохраняются `hypothesis_text` и `llm_hypothesis_at`, остальные metadata не теряются. После commit вызывается прежняя локальная cache invalidation без SQL-соединения. Это не новая межрепличная revision-инвалидация — T06 остаётся открыт.

Промпт и `_build_prompt` переиспользуются, модель/base URL/ключ берутся из того же конфига; лимит 150 tokens, temperature 1.0 и 23-часовой кэш сохранены. `plan`, `critical_balance`, `critical_stopped`, `critical_tracking` по-прежнему не переформулируются. Тарифы и платёжная логика не менялись.

Для нового необязательного обогащения явно задано `max_retries=0`: SDK не должен автоматически повторять потенциально оплаченный запрос при неизвестном результате. По умолчанию SDK повторяет часть ошибок дважды; механизм отключения описан в [официальной документации](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python#retries). Ошибка/пустой ответ оставляют детерминированный текст. Ошибка необязательного enrichment не инициирует retry полной синхронизации; `LeaseLost` и отмена не скрываются. Общий timeout задачи сохранён.

## Проверки

Изолированный PostgreSQL, синтетические данные и fake LLM; платных запросов нет.

- `tests/test_detector_hypothesis_work.py`: **33 passed**, 16 warnings, 37,15 s.
- `pool.checkedout() == 0` при создании/вызове/закрытии HTTP-клиента и cache invalidation; отдельно проверен реальный вызывающий `_sync_attempt` с pending detector write перед commit.
- Кэш/replay без второго LLM-вызова, прежние prompt/model/параметры, пропуск детерминированных/неактивных/свежих алертов.
- Изменение state/ownership во время HTTP, lease expiry и rollback; отсутствие перезаписи fallback, очистка HTTP-ресурсов.
- Границы ошибок sync/detector/enrichment/lease, неизменный legacy вызов без нового аргумента.

Общий source-bind regression: **517 passed, 1 skipped, 1 deselected**, 47 warnings, 149,47 s. После него локально изменено только форматирование сигнатуры и docstring `sync_integration`; финальная версия проверяется в чистом образе. Image-only evidence записывается после завершения проверки артефакта.

## Что остаётся и как откатить

- Это устранение одной длинной SQL-транзакции в новом durable sync, а не перевод всего `sync_integration` на snapshot/collect/apply. Полные рекламные HTTP-стадии, refresh credentials, частичные результаты/coverage и отдельный report pipeline ещё требуют реализации.
- Остальные legacy вызовы `sync_integration` без durable fence сохраняют прежний путь. Нельзя включать одновременно legacy и durable исполнителей одного ресурса.
- Не добавлен durable paid-request ledger/reservation/usage/settlement. После process crash между платным ответом и SQL commit либо при двух интеграциях одного проекта повторная генерация по-прежнему возможна; cache/CAS не означает exactly-once оплаты. Это остаётся T10 и не считается закрытым отключением SDK retry.
- Полный batch API/межрепличный cache, capacity, backup/restore и rollout gates остаются обязательными.
- Миграций нет. Откат — предыдущий совместимый backend image; детерминированные данные и совместимые поля алерта остаются читаемыми. Production-переключение пока не выполнялось.
