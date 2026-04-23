"""
Яндекс.Метрика API: статистика и цели.

Сегмент из интерфейса (скрин): «Визиты, в которых» → Источники →
Автоматическая атрибуция → Рекламная система: Яндекс.Директ или
Яндекс.Директ: Не определено.

Параметризация (https://yandex.ru/dev/metrika/ru/stat/param):
- Группировку AdvEngine нужно указывать с <attribution>, задавая через
  &attribution=automatic или вписывая атрибуцию в выражение.
- dimensions=ym:s:<attribution>TrafficSource + attribution=automatic
  соответствует отчёту «Источники, сводка» с автоматической атрибуцией.
- Фильтр: ya_direct, ya_undefined (НЕ yandex_direct).
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Фильтр: только визиты из Яндекс.Директа (включая «Не определено»).
# Поддержка: в фильтре нужна параметризация — ym:s:<attribution>AdvEngine (не ym:s:AdvEngine).
# Значения: ya_direct, ya_undefined (НЕ yandex_direct).
FILTER_YANDEX_DIRECT_VISITS = (
    "ym:s:<attribution>AdvEngine=='ya_direct' OR ym:s:<attribution>AdvEngine=='ya_undefined'"
)


class YandexMetricaAPI:
    def __init__(self, access_token: str, client_login: str = None):
        self.base_url = "https://api-metrica.yandex.net/stat/v1/data"
        self.bytime_url = "https://api-metrica.yandex.net/stat/v1/data/bytime"
        self.client_login = client_login
        self.headers = {
            "Authorization": f"OAuth {access_token}"
        }

    async def get_stats(self, counter_id: str, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Fetches statistics from Yandex Metrica API.
        """
        params = {
            "ids": counter_id,
            "metrics": "ym:s:visits,ym:s:users,ym:s:pageviews",
            "dimensions": "ym:s:date",
            "date1": date_from,
            "date2": date_to,
            "group": "day",
            "sort": "ym:s:date"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                results = []
                for row in data.get('data', []):
                    results.append({
                        "date": row['dimensions'][0]['name'],
                        "visits": row['metrics'][0],
                        "users": row['metrics'][1],
                        "pageviews": row['metrics'][2]
                    })
                return results
            else:
                logger.error(f"Yandex Metrica API Error: {response.status_code} - {response.text}")
                return []

    async def get_goals_stats(
        self,
        counter_id: str,
        date_from: str,
        date_to: str,
        metrics: str = "ym:s:anyGoalConversionRate,ym:s:sumGoalVisitsAny",
        goal_id: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches goal visits (целевые визиты) from Yandex Metrica.
        Использует /stat/v1/data как в примере поддержки (bytime возвращал нули).
        dimensions=ym:s:<attribution>TrafficSource + attribution=automatic — сегмент «Источники • Автоматическая атрибуция».
        dimensions=ym:s:date — разбивка по дням.
        Returns list of {dimensions: [{name: date}], metrics: [...]} per day.
        """
        params = {
            "ids": counter_id,
            "metrics": metrics,
            "date1": date_from,
            "date2": date_to,
            # Поддержка: /stat/v1/data + dimensions=ym:s:<attribution>TrafficSource + attribution=automatic.
            # Для разбивки по дням добавляем ym:s:date. Порядок: date первым (основная группировка).
            "dimensions": "ym:s:date,ym:s:<attribution>TrafficSource",
            "attribution": "AUTOMATIC",
            "filters": filters if filters is not None else FILTER_YANDEX_DIRECT_VISITS,
            "accuracy": "full",
            "limit": "1000",
        }
        if goal_id:
            params["goal_id"] = goal_id
        logger.info(f"📊 Metrika data API: GET stat/v1/data counter={counter_id} date1={date_from} date2={date_to} dimensions=TrafficSource+date attribution=AUTOMATIC")
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                rows_data = data.get('data', [])
                if not rows_data:
                    logger.warning(f"📊 Metrika data: 0 rows. Response keys: {list(data.keys())} totals={data.get('totals')}")
                    return []

                # #region agent log
                _first = rows_data[0] if rows_data else {}
                logger.info(f"[DEBUG Metrika data] rows={len(rows_data)} first={_first} totals={data.get('totals')}")
                # #endregion

                # /data: каждая строка = dimensions (date, TrafficSource) + metrics
                # Суммируем по датам (несколько строк на дату: ya_direct, ya_undefined)
                by_date: dict[str, list] = {}
                for row in rows_data:
                    dims = row.get('dimensions', [])
                    if len(dims) >= 1:
                        date_str = dims[0].get('name') if isinstance(dims[0], dict) else str(dims[0])
                    else:
                        continue
                    m = row.get('metrics', [])
                    if date_str not in by_date:
                        by_date[date_str] = [0] * len(m)
                    for i, v in enumerate(m):
                        if i < len(by_date[date_str]):
                            by_date[date_str][i] += int(v or 0)

                d_start = datetime.strptime(date_from, "%Y-%m-%d").date()
                d_end = datetime.strptime(date_to, "%Y-%m-%d").date()
                num_metrics = len(next(iter(by_date.values()), [])) if by_date else 0
                result = []
                for i in range((d_end - d_start).days + 1):
                    d = d_start + timedelta(days=i)
                    date_str = d.strftime("%Y-%m-%d")
                    day_metrics = by_date.get(date_str, [0] * num_metrics)
                    if len(day_metrics) < num_metrics:
                        day_metrics = day_metrics + [0] * (num_metrics - len(day_metrics))
                    result.append({
                        'dimensions': [{'name': date_str}],
                        'metrics': day_metrics[:num_metrics] if num_metrics else day_metrics
                    })

                logger.info(f"📊 Metrika data: received {len(result)} days, {len(by_date)} dates with data")
                if result:
                    logger.info(f"[DEBUG Metrika result] first_day={result[0]} total_days={len(result)}")
                return result
            elif response.status_code == 429:
                error = Exception(f"429 Too Many Requests")
                error.status_code = 429
                error.response = response
                raise error
            elif response.status_code == 400 and "Query is too complicated" in response.text:
                # Авто-деградация: дробим период на 2 части, чтобы упростить запрос.
                try:
                    d1 = datetime.strptime(date_from, "%Y-%m-%d").date()
                    d2 = datetime.strptime(date_to, "%Y-%m-%d").date()
                except Exception:
                    logger.warning(f"Yandex Metrica API error 400: {response.text[:200]}")
                    return []

                if d1 >= d2:
                    logger.warning(f"Yandex Metrica API error 400 on single-day range {date_from}: {response.text[:200]}")
                    return []

                mid = d1 + timedelta(days=(d2 - d1).days // 2)
                left_from = d1.strftime("%Y-%m-%d")
                left_to = mid.strftime("%Y-%m-%d")
                right_from = (mid + timedelta(days=1)).strftime("%Y-%m-%d")
                right_to = d2.strftime("%Y-%m-%d")

                logger.warning(
                    "Metrika query too complicated for %s..%s. Splitting into %s..%s and %s..%s",
                    date_from, date_to, left_from, left_to, right_from, right_to
                )

                left = await self.get_goals_stats(
                    counter_id=counter_id,
                    date_from=left_from,
                    date_to=left_to,
                    metrics=metrics,
                    goal_id=goal_id,
                    filters=filters,
                )
                right = await self.get_goals_stats(
                    counter_id=counter_id,
                    date_from=right_from,
                    date_to=right_to,
                    metrics=metrics,
                    goal_id=goal_id,
                    filters=filters,
                )
                return (left or []) + (right or [])
            else:
                logger.warning(f"Yandex Metrica API error {response.status_code}: {response.text[:200]}")
                return []

    async def get_counters(self) -> List[Dict[str, Any]]:
        """
        Lists all accessible counters.
        CRITICAL: If client_login is provided, API should filter counters by that profile.
        However, API may return all accessible counters regardless of ulogin parameter.
        We rely on backend filtering by owner_login after fetching.
        """
        url = "https://api-metrica.yandex.net/management/v1/counters"
        params = {}
        if self.client_login:
            params["ulogin"] = self.client_login
            logger.info(f"📊 YandexMetricaAPI.get_counters: Using ulogin={self.client_login} to filter counters")
        else:
            logger.info(f"📊 YandexMetricaAPI.get_counters: No client_login, fetching all accessible counters")
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                counters = data.get('counters', [])
                logger.info(f"📊 YandexMetricaAPI.get_counters: API returned {len(counters)} counters")
                if self.client_login:
                    # Log owner_login for each counter to verify filtering
                    for counter in counters:
                        owner_login = counter.get('owner_login', 'N/A')
                        logger.debug(f"   Counter '{counter.get('name')}' (ID: {counter.get('id')}): owner_login={owner_login}")
                return counters
            
            error_msg = f"Failed to fetch counters: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def get_counter_goals(self, counter_id: str) -> List[Dict[str, Any]]:
        """
        Lists all goals for a specific counter.
        """
        url = f"https://api-metrica.yandex.net/management/v1/counter/{counter_id}/goals"
        params = {}
        if self.client_login:
            params["ulogin"] = self.client_login
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('goals', [])
            
            error_msg = f"Failed to fetch goals for counter {counter_id}: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def get_activity_by_weekday(
        self,
        counter_id: str,
        date_from: str,
        date_to: str,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получает активность по дням недели (Пн–Вс).
        dimensions=ym:s:dayOfWeek, metrics=ym:s:visits
        dayOfWeek: 0=Вс, 1=Пн, ..., 6=Сб
        """
        params = {
            "ids": counter_id,
            "metrics": "ym:s:visits",
            "dimensions": "ym:s:dayOfWeek",
            "date1": date_from,
            "date2": date_to,
            "filters": filters if filters is not None else FILTER_YANDEX_DIRECT_VISITS,
            "attribution": "AUTOMATIC",
            "accuracy": "full",
            "limit": "100",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            logger.warning(f"Yandex Metrica dayOfWeek error {response.status_code}: {response.text[:200]}")
            return []

    async def get_activity_by_weekday(
        self,
        counter_id: str,
        date_from: str,
        date_to: str,
        filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Визиты по дням недели. dimensions=ym:s:dayOfWeek (0=Вс, 1=Пн, ..., 6=Сб).
        """
        params = {
            "ids": counter_id,
            "metrics": "ym:s:visits",
            "dimensions": "ym:s:dayOfWeek",
            "date1": date_from,
            "date2": date_to,
            "limit": "10",
        }
        if filters:
            params["filters"] = filters
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            logger.warning(f"Metrika dayOfWeek error {response.status_code}: {response.text[:200]}")
            return []

    async def get_audience_age(
        self,
        counter_id: str,
        date_from: str,
        date_to: str,
        filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Распределение аудитории по возрасту. dimensions=ym:s:ageInterval.
        Ограничение: данные при достаточном объёме выборки (>10 посетителей).
        """
        params = {
            "ids": counter_id,
            "metrics": "ym:s:visits",
            "dimensions": "ym:s:ageInterval",
            "date1": date_from,
            "date2": date_to,
            "limit": "20",
        }
        if filters:
            params["filters"] = filters
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            logger.warning(f"Metrika ageInterval error {response.status_code}: {response.text[:200]}")
            return []

    @staticmethod
    def normalize_domain(url: str) -> str:
        """
        Extract and normalize domain from Metrika counter site URL.
        Returns normalized domain (e.g., 'kxi-stroi.rf' from 'https://www.kxi-stroi.rf/').
        """
        if not url:
            return ""
        # Remove protocol
        url = url.replace("http://", "").replace("https://", "")
        # Remove www.
        if url.startswith("www."):
            url = url[4:]
        # Remove path and query
        url = url.split("/")[0].split("?")[0]
        # Remove port
        url = url.split(":")[0]
        # Lowercase
        return url.lower().strip()
