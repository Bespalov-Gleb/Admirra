# Durable синхронизация рекламных кабинетов: fetch/apply

22.09.2026. Candidate, не production rollout. Продолжение [standalone Метрики](devops-metrika-sync-2026-09-21.md).

## Реализовано

- Manual/night dispatch Директа, VK и Авито использует fenced lifecycle standalone Метрики. История этих каналов больше не держит SQL-сессию во время внешнего HTTP.
- Prepare фиксирует owner/project, настройки, credentials, даты и известные кампании. Сбор всех обязательных уровней и выбранных целей Метрики — без SQL-соединения. Apply повторно проверяет binding/settings/lease.
- Каталог, campaign/group/keyword/creative статистика, выбранные цели и SUCCESS коммитятся атомарно. При ошибке обязательного этапа остаются прежние факты и watermark. Подтверждённый пустой ответ заменяет только свои integration/date facts.
- Баланс и стратегии — optional metadata. Недоступный баланс не подменяется нулём. History не меняет текущий баланс/last_sync_at, не запускает detector/LLM. Cache invalidation — после commit.
- OAuth renewal Директа/VK — вне SQL; сохранение credentials — короткая fenced-транзакция при неизменной конфигурации. Затем весь снимок собирается заново с прежним профилем/FinanceToken. Follow-up получает только собственное изменение digest без расширения дат. Авито использует существующий client-credentials adapter.
- Последовательные окна не более 90 дней; после разбора ограничение 100 000 строк на коллекцию и 32 MiB JSON снимка. Это **не streaming HTTP cap**: SDK сначала декодирует тело ответа.
- Проверяются явные collections, ID, числа, даты, дубликаты ключей, пагинация и объявленный total. При Direct 3228 discovery идёт из обязательного date-scoped report, без десяти лет fallback.
- VK сохраняет objective/состав лидов/lead-form autodefault и уведомления. Ненулевые конверсии без подтверждённого objective не коммитятся. Явное `vk.goals=0` не заменяется `base.goals`.
- Авито включает архивные и известные кампании в history, не пропускает ошибки отдельных кампаний. При смешанном ответе недостающие daily-группы/креативы догружаются отдельно; отсутствующая детализация не превращается в синтетические нули.
- Keyword rows Директа получают CampaignId. Старые строки без FK заменяются только при подтверждённой принадлежности имени этой интеграции, включая переименование. Совпадающее имя в другом кабинете блокирует запись с сохранением прежних фактов: перед rollout нужен аудит таких legacy rows на восстановленной копии.
- Legacy non-durable consumers не переключены. При cutover они должны быть выключены.

## Проверки

Промежуточный расширенный прогон: **231 passed**, 194 warnings, 186,15 с, изолированные PostgreSQL/Redis, без production credentials и внешних API. После него внесены небольшие исправления; окончательный artifact regression фиксируется отдельно.

Тесты покрывают manual/auto/replay, три канала, history watermark, required detail/Metrika failure, неполные/повторные/неверные строки, пустой период, settings/owner/lease race, token rotation/follow-up, legacy keyword binding. HTTP-моки проверяют `pool.checkedout() == 0`. Сохранены регрессии standalone Метрики, scope guard и SDK.

Read-only сверка реального Avito payload **не выполнена**: запуск остановлен на согласовании доступа. Контракты пока проверены тестовыми ответами, не реальными кабинетами. Прежний прямой URL OpenAPI вернул HTTP 404.

## Что этот пакет не закрывает

1. Сохраняемый per-stage coverage/outcome и freshness barrier для reports/AI/detector. Сейчас обязательный снимок атомарен целиком; ошибка — FAILED со старыми фактами, не partial commit.
2. Показ связи follow-up и приёмка UI. Бизнес-статусы/job IDs сохранены.
3. Размерность реальных vendor quotas, streaming response cap, освобождение слота на долгий Retry-After. Существующий общий limiter используется.
4. Live read-only проверка форматов, аудит неоднозначных keywords, контрольный sync, mixed-load и общий cutover gate. Моки/restore не подтверждают live provider поведение.

Production images/ingress не изменены. S3 и две ночи наблюдения остаются отложенными, а не выполненными. Весь SYNC/DevOps не объявляется завершённым.
