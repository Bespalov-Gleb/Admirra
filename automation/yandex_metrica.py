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
# Измерение ym:s:AdvEngine. Значения: ya_direct, ya_undefined (НЕ yandex_direct).
FILTER_YANDEX_DIRECT_VISITS = (
    "ym:s:AdvEngine=='ya_direct' OR ym:s:AdvEngine=='ya_undefined'"
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
        Uses /stat/v1/data/bytime for daily breakdown (Table endpoint returns 1 row).
        By default applies filter: only visits from Yandex.Direct (incl. Undefined).
        Returns list of {dimensions: [{name: date}], metrics: [...]} per day.
        """
        params = {
            "ids": counter_id,
            "metrics": metrics,
            "date1": date_from,
            "date2": date_to,
            "group": "day",
            # Явная атрибуция: сегмент «Источники • Автоматическая атрибуция»
            # dimensions с <attribution> + attribution=automatic (поддержка Метрики)
            "dimensions": "ym:s:<attribution>TrafficSource",
            "attribution": "automatic",
            "filters": filters if filters is not None else FILTER_YANDEX_DIRECT_VISITS,
            "accuracy": "1",
        }
        if goal_id:
            params["goal_id"] = goal_id
        logger.info(f"📊 Metrika bytime API: GET stat/v1/data/bytime counter={counter_id} date1={date_from} date2={date_to} filters=Yandex.Direct attribution=automatic")
        async with httpx.AsyncClient() as client:
            response = await client.get(self.bytime_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                rows_data = data.get('data', [])
                if not rows_data:
                    logger.warning(f"📊 Metrika bytime: 0 rows. Response keys: {list(data.keys())}")
                    return []

                # #region agent log
                _first = rows_data[0] if rows_data else {}
                _m = _first.get("metrics", [])
                logger.info(f"[DEBUG Metrika bytime] rows={len(rows_data)} metrics_len={len(_m)} first_metric_len={len(_m[0]) if _m else 0} query={params.get('metrics')} date1={date_from} date2={date_to}")
                # #endregion

                # bytime с dimensions: несколько строк (ya_direct, ya_undefined) — суммируем.
                # Без dimensions: одна строка. metrics[m][t] = метрика m для дня t.
                num_metrics = 0
                num_points = 0
                for row in rows_data:
                    metrics_2d = row.get('metrics', [])
                    if metrics_2d:
                        num_metrics = len(metrics_2d)
                        num_points = max(num_points, len(metrics_2d[0]) if metrics_2d[0] else 0)
                        break
                if not num_metrics or not num_points:
                    return []

                d_start = datetime.strptime(date_from, "%Y-%m-%d").date()
                result = []
                for day_idx in range(num_points):
                    date_str = (d_start + timedelta(days=day_idx)).strftime("%Y-%m-%d")
                    day_metrics = [0] * num_metrics
                    for row in rows_data:
                        metrics_2d = row.get('metrics', [])
                        if metrics_2d and day_idx < len(metrics_2d[0]):
                            for m_idx in range(min(num_metrics, len(metrics_2d))):
                                day_metrics[m_idx] += int(metrics_2d[m_idx][day_idx] or 0)
                    result.append({
                        'dimensions': [{'name': date_str}],
                        'metrics': day_metrics
                    })

                logger.info(f"📊 Metrika bytime: received {len(result)} days")
                # #region agent log
                if result:
                    logger.info(f"[DEBUG Metrika result] first_day={result[0]} total_days={len(result)} metrics={params.get('metrics')}")
                # #endregion
                return result
            elif response.status_code == 429:
                error = Exception(f"429 Too Many Requests")
                error.status_code = 429
                error.response = response
                raise error
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
