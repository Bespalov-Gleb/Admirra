import httpx
import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone

from automation.vk_goal_action_mapping import get_vk_goal_action_name_ru

logger = logging.getLogger(__name__)


def _log_vk_error_for_support(response: httpx.Response, endpoint_hint: str) -> None:
    """Заголовки ответа VK для обращения в поддержку (x-request-id и т.д.)."""
    trace = {}
    for k, v in response.headers.items():
        kl = k.lower()
        if any(x in kl for x in ("request-id", "trace", "cf-ray", "correlation")):
            trace[k] = v
    http_date = response.headers.get("date")
    our_utc = datetime.now(timezone.utc).isoformat()
    if trace:
        logger.error(
            "VK Ads %s — для поддержки: %s | HTTP Date (ответ VK): %r | зафиксировано на сервере (UTC): %s",
            endpoint_hint,
            trace,
            http_date,
            our_utc,
        )
    else:
        logger.error(
            "VK Ads %s — trace-заголовки не пришли; HTTP Date: %r | UTC на сервере: %s | заголовки ответа: %s",
            endpoint_hint,
            http_date,
            our_utc,
            dict(response.headers),
        )


VK_ADS_OAUTH2_TOKEN_URL = "https://ads.vk.com/api/v2/oauth2/token.json"


def vk_agency_exchange_hints(
    agency_client_login: Optional[str],
    account_id: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    (agency_client_name, agency_client_id, cabinet_id_only).

    Если в БД один и тот же числовой ID кабинета в account_id и agency_client_login —
    это не user id из AgencyClients; для OAuth нужен разбор через GET agency/clients.json.
    """
    login = (agency_client_login or "").strip()
    aid = (account_id or "").strip()
    if login.lower() in ("unknown", "none", ""):
        login = ""
    if aid.lower() in ("unknown", "none", ""):
        aid = ""
    if login == aid and login.isdigit():
        return None, None, login
    # Только числовой кабинет в account_id без отдельного логина клиента агентства
    if not login and aid.isdigit():
        return None, None, aid

    name: Optional[str] = None
    uid: Optional[str] = None
    if login:
        if "@" in login or not login.isdigit():
            name = login
        else:
            uid = login
    if aid and aid.isdigit():
        uid = uid or aid
    elif aid and not name:
        name = aid
    if name and uid and name == uid:
        uid = name if name.isdigit() else uid
        name = None if (name or "").isdigit() else name
    return name, uid, None  # cabinet_only всегда None здесь


def vk_campaigns_error_needs_agency_client_retry(exc: BaseException) -> bool:
    """
    403 на ad_plans с view_campaigns / access_denied — часто из‑за токена агентства вместо клиента.
    Тогда имеет смысл один раз запросить токен через agency_client_credentials.
    """
    msg = str(exc)
    if "403" not in msg:
        return False
    return "view_campaigns" in msg or "access_denied" in msg


async def _vk_agency_client_credentials_attempts(
    *,
    client_id: str,
    client_secret: str,
    agency_access_token: str,
    agency_client_name: Optional[str] = None,
    agency_client_id: Optional[str] = None,
    minimal: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    grant agency_client_credentials: пробуем с access_token агентства и без.
    minimal=True — только две попытки по id или по name (для перебора клиентов).
    """
    if not (client_id and client_secret and agency_access_token):
        return None
    name = (agency_client_name or "").strip()
    if name.lower() in ("unknown", "none", ""):
        name = ""
    cid = (agency_client_id or "").strip()
    if cid.lower() in ("unknown", "none", ""):
        cid = ""
    if not name and not cid:
        return None

    base: Dict[str, Any] = {
        "grant_type": "agency_client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    attempts: List[Dict[str, Any]] = []

    if minimal:
        if cid:
            attempts.append({**base, "access_token": agency_access_token, "agency_client_id": cid})
            attempts.append({**base, "agency_client_id": cid})
        elif name:
            attempts.append({**base, "access_token": agency_access_token, "agency_client_name": name})
            attempts.append({**base, "agency_client_name": name})
    else:
        if name:
            attempts.append({**base, "access_token": agency_access_token, "agency_client_name": name})
            attempts.append({**base, "agency_client_name": name})
        if cid:
            attempts.append({**base, "access_token": agency_access_token, "agency_client_id": cid})
            attempts.append({**base, "agency_client_id": cid})

    seen: List[tuple] = []
    uniq: List[Dict[str, Any]] = []
    for p in attempts:
        key = tuple(sorted((k, str(v)) for k, v in p.items()))
        if key in seen:
            continue
        seen.append(key)
        uniq.append(p)

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient() as client:
        for i, data in enumerate(uniq):
            try:
                r = await client.post(
                    VK_ADS_OAUTH2_TOKEN_URL, data=data, headers=headers, timeout=30.0
                )
                if r.status_code == 200:
                    body = r.json()
                    if body.get("access_token"):
                        logger.info(
                            "VK Ads: agency_client_credentials OK (попытка %s, ключи тела: %s)",
                            i + 1,
                            [k for k in sorted(data.keys()) if k != "client_secret"],
                        )
                        return body
                logger.warning(
                    "VK Ads: agency_client_credentials попытка %s → HTTP %s: %s",
                    i + 1,
                    r.status_code,
                    (r.text or "")[:400],
                )
            except Exception as ex:
                logger.warning("VK Ads: agency_client_credentials запрос: %s", ex)
    return None


async def exchange_vk_agency_client_credentials_for_integration(
    *,
    client_id: str,
    client_secret: str,
    agency_access_token: str,
    agency_client_login: Optional[str],
    account_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Обмен для интеграции: учитывает, что в UI часто сохраняют ID кабинета, а не user id AgencyClients.
    """
    name, uid, cabinet_only = vk_agency_exchange_hints(agency_client_login, account_id)
    if name or uid:
        td = await _vk_agency_client_credentials_attempts(
            client_id=client_id,
            client_secret=client_secret,
            agency_access_token=agency_access_token,
            agency_client_name=name,
            agency_client_id=uid,
            minimal=False,
        )
        if td:
            return td
    if not cabinet_only:
        return None

    logger.info(
        "VK Ads: в интеграции только ID кабинета %r (не user id AgencyClients); "
        "загружаем agency/clients.json и подбираем клиента",
        cabinet_only,
    )
    api = VKAdsAPI(agency_access_token, account_id=None)
    raw = await api.get_agency_clients_raw()
    if not raw:
        logger.warning(
            "VK Ads: agency/clients.json пуст или недоступен. Нужен scope read_clients и аккаунт агентства; "
            "либо вручную укажите клиента агентства (user id из AgencyClients), а не только ID кабинета."
        )
        return None

    def _score(it: Dict[str, Any]) -> tuple:
        blob = json.dumps(it, ensure_ascii=False)
        hit = cabinet_only in blob
        return (0 if hit else 1, str(it.get("id") or ""))

    raw_sorted = sorted(raw, key=_score)
    max_items = 40
    if len(raw_sorted) > max_items:
        logger.warning(
            "VK Ads: клиентов агентства %s, перебираем первые %s",
            len(raw_sorted),
            max_items,
        )
        raw_sorted = raw_sorted[:max_items]

    for item in raw_sorted:
        aid = item.get("id")
        if aid is None:
            continue
        sid = str(aid)
        td = await _vk_agency_client_credentials_attempts(
            client_id=client_id,
            client_secret=client_secret,
            agency_access_token=agency_access_token,
            agency_client_name=None,
            agency_client_id=sid,
            minimal=True,
        )
        if td:
            logger.info(
                "VK Ads: agency_client_credentials OK для agency client id=%s (кабинет %s)",
                sid,
                cabinet_only,
            )
            return td
        user = item.get("user")
        uname = item.get("username") or item.get("user_name")
        if not uname and isinstance(user, dict):
            uname = user.get("username")
        if uname:
            td = await _vk_agency_client_credentials_attempts(
                client_id=client_id,
                client_secret=client_secret,
                agency_access_token=agency_access_token,
                agency_client_name=str(uname),
                agency_client_id=None,
                minimal=True,
            )
            if td:
                logger.info(
                    "VK Ads: agency_client_credentials OK по username из agency/clients (кабинет %s)",
                    cabinet_only,
                )
                return td
    return None


class VKAdsAPI:
    def __init__(self, access_token: str, account_id: str = None, *, send_client_id: Optional[bool] = None):
        self.base_url = "https://ads.vk.com/api/v2" # Example base URL
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
        # cabinet_id — реальный id кабинета (для отображения и фолбэков профилей/аккаунтов).
        self.cabinet_id = account_id
        # client_id подставляем в запросы ТОЛЬКО для агентского токена. По документации
        # VK Ads параметр client_id — это id клиента агентства; для ЛИЧНОГО кабинета токен
        # сам себя скоупит, и передача client_id возвращает пустую статистику (это и есть
        # баг «личный кабинет подключается, но не вытягивает статистику»).
        # По умолчанию поведение прежнее (шлём client_id, если задан account_id) — личный
        # vs агентский кабинет различает вызывающий код через send_client_id.
        if send_client_id is None:
            send_client_id = bool(account_id)
        self.send_client_id = bool(send_client_id)
        # account_id используется в методах только для подстановки client_id в запросы.
        # Для личного кабинета держим его None, чтобы client_id нигде не подставился.
        self.account_id = account_id if self.send_client_id else None
        self.debug_events: List[str] = []
        # Лимиты приложения VK Ads: 1 запрос/сек, 30/мин ({"limits":{"1":1,"60":30}}).
        # Без троттлинга массовые запросы (initial sync, иерархия) ловят 429 подряд.
        self._throttle_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def _throttle(self, min_interval: float = 1.05) -> None:
        """Выдерживает паузу между запросами к API (лимит 1 rps)."""
        import time
        async with self._throttle_lock:
            now = time.monotonic()
            wait = self._next_request_at - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._next_request_at = now + min_interval

    async def detect_token_kind(self) -> str:
        """
        Определяет тип токена по агентскому endpoint: "agency" | "personal" | "unknown".

        GET /agency/clients.json: 200 (агентство, в т.ч. с items) → agency;
        403 → личный/рекламодатель (personal); прочее/ошибка → unknown.
        Нужен, чтобы решить, передавать ли client_id в запросах статистики.
        """
        url = f"{self.base_url}/agency/clients.json"
        try:
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, headers=self.headers, timeout=20.0)
                if response.status_code == 200:
                    return "agency"
                if response.status_code == 403:
                    return "personal"
                logger.info("VK Ads detect_token_kind: HTTP %s", response.status_code)
        except Exception as ex:
            logger.info("VK Ads detect_token_kind error: %s", ex)
        return "unknown"

    def _push_debug(self, message: str, limit: int = 60) -> None:
        self.debug_events.append(message)
        if len(self.debug_events) > limit:
            self.debug_events = self.debug_events[-limit:]
    
    @staticmethod
    def _get_human_readable_objective(objective_code: str) -> str:
        """
        Переводит код целевого действия VK на русский (traffic → Трафик, reach → Охват и т.д.).
        """
        return get_vk_goal_action_name_ru(objective_code)

    @staticmethod
    def _parse_goal_value(value: Any) -> tuple:
        if value is None:
            return None, None
        if isinstance(value, dict):
            goal_id = (
                value.get("id")
                or value.get("goal_id")
                or value.get("action_id")
                or value.get("code")
                or value.get("type")
            )
            goal_name = value.get("name") or value.get("title") or value.get("label")
            if goal_name is None and goal_id is not None:
                goal_name = str(goal_id)
            return (str(goal_id) if goal_id is not None else None, goal_name)
        return (str(value), str(value))

    def _extract_goal_action(self, item: Dict[str, Any]) -> tuple:
        """
        Извлекает информацию о целевом действии из объекта кампании.
        Проверяет различные возможные поля и форматы данных.
        """
        # Прямые поля (наиболее вероятные)
        direct_id = (
            item.get("goal_id")
            or item.get("goal_action_id")
            or item.get("target_action_id")
            or item.get("objective_id")
            or item.get("objective", {}).get("id") if isinstance(item.get("objective"), dict) else None
            or item.get("goal", {}).get("id") if isinstance(item.get("goal"), dict) else None
        )
        direct_name = (
            item.get("goal_name")
            or item.get("goal_action_name")
            or item.get("target_action_name")
            or item.get("objective_name")
            or item.get("objective", {}).get("name") if isinstance(item.get("objective"), dict) else None
            or item.get("goal", {}).get("name") if isinstance(item.get("goal"), dict) else None
        )
        if direct_id or direct_name:
            return (str(direct_id) if direct_id is not None else None, direct_name or str(direct_id))

        # Проверяем вложенные объекты
        for key in [
            "goal",
            "target_action",
            "objective",
            "goal_type",
            "conversion_goal",
            "optimization_event",
            "event_type",
            "action_type",
        ]:
            if key in item:
                goal_id, goal_name = self._parse_goal_value(item.get(key))
                if goal_id or goal_name:
                    return (goal_id, goal_name)

        return (None, None)

    def _extract_goal_action_from_package(self, package: Dict[str, Any]) -> tuple:
        """
        Извлекает более детальный ЦД из Package.
        Приоритет:
        1) priced_event_type (детализация по событию оптимизации, согласно доке VK)
        2) objective (верхнеуровневая цель кампании).
        """
        priced_event_type = package.get("priced_event_type")
        if priced_event_type is not None:
            code_map = {
                41: "evt_41_community_actions",
                43: "evt_43_miniapp_events",
                51: "evt_51_lead_forms",
            }
            try:
                pet = int(priced_event_type)
            except (TypeError, ValueError):
                pet = None
            if pet in code_map:
                code = code_map[pet]
                return code, self._get_human_readable_objective(code)

        objective = (
            package.get("objective")
            or package.get("objective_name")
            or package.get("target_action")
        )
        if objective:
            if isinstance(objective, list):
                objective_code = objective[0] if objective else None
            else:
                objective_code = str(objective) if objective else None
            if objective_code:
                objective_name = self._get_human_readable_objective(objective_code)
                return objective_code, objective_name
        return None, None

    async def get_campaigns(self) -> List[Dict[str, Any]]:
        """
        Получает список всех рекламных кампаний (AdPlans) с целевыми действиями.
        
        Согласно документации VK Ads API (https://ads.vk.com/doc/api/object/AdPlan):
        - Endpoint: GET /api/v2/ad_plans.json - список кампаний
        - Endpoint: GET /api/v2/ad_plans/{id}.json - детальная информация о кампании
        - Поле 'objective' (string, readable) - "Цель рекламной кампании"
        
        Returns:
            List[Dict] с полями:
            - id: str - ID кампании
            - name: str - название кампании
            - status: str - статус кампании
            - goal_action_id: str - ID целевого действия (из поля objective)
            - goal_action_name: str - название целевого действия (из поля objective)
        """
        url = f"{self.base_url}/ad_plans.json"
        params = {}
        
        if self.account_id:
            params["client_id"] = self.account_id
        
        self._push_debug(f"GET {url} params={params}")
        self._push_debug(f"account_id={self.account_id} cabinet_id={self.cabinet_id} send_client_id={self.send_client_id}")
            
        try:
            async with httpx.AsyncClient() as client:
                campaigns = []
                limit = 200
                offset = 0
                use_fields = True

                while True:
                    page_params = params.copy()
                    page_params["limit"] = limit
                    page_params["offset"] = offset
                    if use_fields:
                        page_params["fields"] = "id,name,status,objective"

                    await self._throttle()
                    response = await client.get(url, params=page_params, headers=self.headers, timeout=30.0)

                    # Если fields не поддерживается — переключаемся на режим без fields и повторяем текущую страницу
                    if response.status_code == 400 and use_fields:
                        logger.info("ℹ️ VK API не поддерживает fields=objective в ad_plans.json, продолжаем без fields")
                        use_fields = False
                        continue

                    if response.status_code != 200:
                        _log_vk_error_for_support(response, "GET ad_plans.json (кампании)")
                        error_text = response.text[:200] if response.text else "No error message"
                        logger.error(f"❌ VK Ads API error: {response.status_code} - {error_text}")
                        raise Exception(f"Failed to fetch VK campaigns: {response.status_code} - {error_text}")

                    data = response.json()
                    items = data.get("items", [])
                    self._push_debug(
                        f"ad_plans.json page -> 200, offset={offset}, limit={limit}, items={len(items)}"
                    )

                    if not items:
                        break

                    if offset == 0:
                        self._push_debug(f"ad_plans[0] keys -> {list(items[0].keys())}")
                        self._push_debug(f"ad_plans[0] FULL -> {str(items[0])[:300]}")

                    for item in items:
                        item_id = item.get("id")
                        if not item_id:
                            self._push_debug(f"item БЕЗ id -> keys={list(item.keys())}")
                            continue

                        goal_id, goal_name = self._extract_goal_action(item)
                        if goal_id and not goal_name:
                            goal_name = self._get_human_readable_objective(goal_id)
                        elif goal_name and not goal_id:
                            goal_id = goal_name

                        disp_name = (
                            item.get("title")
                            or item.get("campaign_name")
                            or item.get("name")
                            or f"Campaign {item_id}"
                        )
                        raw_status = (item.get("status") or "").lower()
                        if raw_status == "active":
                            normalized_state = "ON"
                        elif raw_status == "deleted":
                            normalized_state = "ARCHIVED"
                        elif raw_status == "blocked":
                            normalized_state = "SUSPENDED"
                        else:
                            normalized_state = "UNKNOWN"

                        campaigns.append({
                            "id": str(item_id),
                            "name": disp_name,
                            "status": item.get("status"),
                            "state": normalized_state,
                            "goal_action_id": goal_id,
                            "goal_action_name": goal_name
                        })

                    offset += len(items)
                    if len(items) < limit:
                        break

                if not campaigns:
                    logger.warning("⚠️ VK Ads: список кампаний пуст (items=0).")

                logger.info(f"✅ VK Ads: получено {len(campaigns)} кампаний (с пагинацией)")
                if campaigns:
                    for i, camp in enumerate(campaigns[:3]):
                        self._push_debug(f"campaign[{i}] -> id={camp.get('id')}, name={camp.get('name')}")
                return campaigns
        except Exception as e:
            logger.error(f"Error fetching VK campaigns: {e}")
            raise e
    
    async def get_goal_actions_from_statistics(
        self,
        campaign_ids: List[str],
        date_from: str,
        date_to: str,
        campaigns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, tuple]:
        """
        Возвращает тип результата кампании из официальных сущностей AdPlan/Package.

        Statistics API не поддерживает group_by=goal/objective. Раньше метод
        перебирал недокументированные параметры и создавал серию HTTP 400.
        Подневные значения целей приходят в base.vk.goals, а тип результата
        определяется настройками кампании и Package.objective.
        """
        goal_actions_map = {}
        
        if not campaign_ids:
            return goal_actions_map
        
        try:
            campaigns = campaigns if campaigns is not None else await self.get_campaigns()
            campaigns_map = {str(c["id"]): c for c in campaigns}
                
            for camp_id in campaign_ids:
                campaign = campaigns_map.get(str(camp_id))
                if campaign and campaign.get("goal_action_id"):
                    goal_actions_map[str(camp_id)] = (
                        campaign["goal_action_id"],
                        campaign.get("goal_action_name") or campaign["goal_action_id"],
                    )
                
            missing_goals = set(str(cid) for cid in campaign_ids) - set(goal_actions_map)
            if missing_goals:
                package_goals = await self.get_goal_actions_from_packages(sorted(missing_goals))
                goal_actions_map.update(package_goals)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить целевые действия: {e}")
        
        return goal_actions_map

    async def get_ad_groups(self, campaign_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Получает группы объявлений (AdGroup) для указанных кампаний.
        Используется для получения package_id, который далее связывается с objective.
        """
        if not campaign_ids:
            return []

        url = f"{self.base_url}/ad_groups.json"
        ad_groups: List[Dict[str, Any]] = []

        # Основной рабочий фильтр — _ad_plan_id__in (как _ad_group_id__in у banners).
        # ВАЖНО: параметры вида ad_plan_id VK молча ИГНОРИРУЕТ (не ошибка, а просто
        # первые 20 групп всего кабинета без фильтра) — поэтому они только в хвосте
        # как фолбэк, а результат дополнительно фильтруется по ad_plan_id вызывающим кодом.
        param_variants = ["_ad_plan_id__in", "ad_plan_id", "ad_plan_ids", "campaign_id", "campaign_ids"]

        async with httpx.AsyncClient() as client:
            for param_name in param_variants:
                try:
                    # Пагинация: без limit VK отдаёт только первые 20 групп
                    found_any = False
                    offset = 0
                    limit = 200
                    for _ in range(25):
                        params = {
                            param_name: ",".join(campaign_ids[:200]),
                            "fields": "id,name,package_id,ad_plan_id",  # Явно запрашиваем нужные поля
                            "limit": limit,
                            "offset": offset,
                        }
                        if self.account_id:
                            params["client_id"] = self.account_id

                        await self._throttle()
                        response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                        if response.status_code == 400:
                            self._push_debug(
                                f"ad_groups.json {param_name} -> 400: {response.text[:200] if response.text else 'empty response'}"
                            )
                            logger.info(
                                f"ℹ️ VK Ads ad_groups 400 for param {param_name}: "
                                f"{response.text[:200] if response.text else 'empty response'}"
                            )
                            break
                        if response.status_code != 200:
                            logger.warning(
                                f"⚠️ VK Ads ad_groups error {response.status_code} for param {param_name}: "
                                f"{response.text[:200] if response.text else 'empty response'}"
                            )
                            break

                        data = response.json()
                        items = data.get("items", [])
                        if not items:
                            break
                        ad_groups.extend(items)
                        found_any = True
                        offset += len(items)
                        if len(items) < limit:
                            break

                    if found_any:
                        logger.info(f"✅ VK Ads: получено {len(ad_groups)} AdGroup (param {param_name})")
                        self._push_debug(
                            f"ad_groups.json {param_name} -> 200, items={len(ad_groups)}"
                        )
                        break
                    else:
                        logger.info(f"ℹ️ VK Ads ad_groups: пустой список (param {param_name})")
                except Exception as e:
                    logger.warning(f"⚠️ VK Ads ad_groups error for param {param_name}: {e}")
                    continue

            # Если фильтры не сработали, пробуем получить все группы постранично и фильтруем локально
            if not ad_groups:
                limit = 200
                offset = 0
                max_pages = 20
                campaign_set = set(str(cid) for cid in campaign_ids)
                for _ in range(max_pages):
                    params = {"limit": limit, "offset": offset}
                    if self.account_id:
                        params["client_id"] = self.account_id
                    await self._throttle()
                    response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                    if response.status_code != 200:
                        logger.warning(
                            f"⚠️ VK Ads ad_groups page error {response.status_code}: "
                            f"{response.text[:200] if response.text else 'empty response'}"
                        )
                        break
                    data = response.json()
                    items = data.get("items", [])
                    if not items:
                        break
                    for item in items:
                        campaign_id = (
                            item.get("ad_plan_id")
                            or item.get("adplan_id")
                            or item.get("campaign_id")
                            or item.get("plan_id")
                        )
                        if campaign_id is not None and str(campaign_id) in campaign_set:
                            ad_groups.append(item)
                    offset += len(items)
                    if len(items) < limit:
                        break
                if ad_groups:
                    logger.info(f"✅ VK Ads: получено {len(ad_groups)} AdGroup (fallback без фильтра)")
                    self._push_debug(
                        f"ad_groups.json fallback -> items={len(ad_groups)}"
                    )

        return ad_groups

    async def get_banners(self, group_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Объявления (banners) для указанных ГРУПП — третий уровень иерархии
        VK Ads (ad_plans → ad_groups → banners). GET /api/v2/banners.json.
        Фильтра по кампании у banners.json нет (unknown_filter _ad_plan_id__in) —
        только по группам: _ad_group_id__in. Чанки по 200 групп + пагинация.
        """
        group_ids = [str(g) for g in group_ids if g]
        if not group_ids:
            return []

        url = f"{self.base_url}/banners.json"
        banners: List[Dict[str, Any]] = []
        limit = 200
        max_pages = 50

        async with httpx.AsyncClient() as client:
            for chunk_start in range(0, len(group_ids), 200):
                chunk = group_ids[chunk_start:chunk_start + 200]
                offset = 0
                for _ in range(max_pages):
                    params = {
                        "_ad_group_id__in": ",".join(chunk),
                        "fields": "id,name,ad_group_id",
                        "limit": limit,
                        "offset": offset,
                    }
                    if self.account_id and self.send_client_id:
                        params["client_id"] = self.account_id
                    try:
                        await self._throttle()
                        response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                    except Exception as e:
                        logger.warning(f"⚠️ VK Ads banners request error: {e}")
                        break
                    if response.status_code != 200:
                        logger.warning(
                            f"⚠️ VK Ads banners error {response.status_code}: "
                            f"{(response.text or '')[:200]}"
                        )
                        break
                    items = (response.json() or {}).get("items", [])
                    if not items:
                        break
                    banners.extend(items)
                    offset += len(items)
                    if len(items) < limit:
                        break

        if banners:
            logger.info(f"✅ VK Ads: получено {len(banners)} banners для {len(group_ids)} групп")
        return banners

    async def get_level_statistics(
        self,
        level: str,
        object_ids: List[str],
        date_from: str,
        date_to: str,
    ) -> List[Dict[str, Any]]:
        """
        Дневная статистика произвольного уровня иерархии VK Ads:
        GET /api/v2/statistics/{ad_plans|ad_groups|banners}/day.json.
        Возвращает строки: {date, object_id, impressions, clicks, cost, conversions}.
        Ограничения API: 200 объектов на запрос, чанки дат ~92 дня.
        """
        if level not in ("ad_plans", "ad_groups", "banners"):
            raise ValueError(f"Unknown VK statistics level: {level}")
        object_ids = [str(i) for i in object_ids if i]
        if not object_ids:
            return []

        url = f"{self.base_url}/statistics/{level}/day.json"
        date_chunks = self._split_date_range(date_from, date_to, 90)
        results: List[Dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            for d_from, d_to in date_chunks:
                for id_offset in range(0, len(object_ids), 200):
                    id_chunk = object_ids[id_offset:id_offset + 200]
                    params = {
                        "date_from": d_from,
                        "date_to": d_to,
                        "id": ",".join(id_chunk),
                        "metrics": "base",
                    }
                    try:
                        await self._throttle()
                        response = await client.get(url, params=params, headers=self.headers, timeout=120.0)
                    except Exception as e:
                        logger.warning(f"⚠️ VK Ads {level} statistics error: {e}")
                        continue
                    if response.status_code == 429:
                        await asyncio.sleep(3)
                        try:
                            await self._throttle()
                            response = await client.get(url, params=params, headers=self.headers, timeout=120.0)
                        except Exception:
                            continue
                    if response.status_code != 200:
                        logger.warning(
                            f"⚠️ VK Ads statistics/{level} HTTP {response.status_code}: "
                            f"{(response.text or '')[:200]}"
                        )
                        continue
                    # Переиспользуем общий парсер (campaign_id в нём = id объекта уровня)
                    for row in self._parse_response(response.json(), {}):
                        results.append({
                            "date": row["date"],
                            "object_id": row["campaign_id"],
                            "impressions": row["impressions"],
                            "clicks": row["clicks"],
                            "cost": row["cost"],
                            "conversions": row["conversions"],
                        })
                    if id_offset + len(id_chunk) < len(object_ids):
                        await asyncio.sleep(0.55)

        return results

    async def get_packages_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Получает список пакетов (Packages) и возвращает мапу по ID.
        """
        url = f"{self.base_url}/packages.json"
        packages: Dict[str, Dict[str, Any]] = {}
        limit = 50  # VK API max_value для limit = 50
        offset = 0
        max_pages = 50  # Увеличиваем кол-во страниц, так как limit меньше

        async with httpx.AsyncClient() as client:
            for _ in range(max_pages):
                params = {"limit": limit, "offset": offset}
                if self.account_id:
                    params["client_id"] = self.account_id
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code != 200:
                    logger.warning(
                        f"⚠️ VK Ads packages error {response.status_code}: "
                        f"{response.text[:200] if response.text else 'empty response'}"
                    )
                    break

                data = response.json()
                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    package_id = item.get("id")
                    if package_id is None:
                        continue
                    packages[str(package_id)] = item
                if offset == 0:
                    self._push_debug(
                        f"packages.json -> 200, items_page={len(items)}, keys={list(items[0].keys()) if items else []}"
                    )
                    # ДИАГНОСТИКА: Показываем первые 10 package ID
                    if items:
                        first_pkg_ids = [str(item.get("id")) for item in items[:10] if item.get("id")]
                        logger.info(f"🔍 Первые 10 package ID: {first_pkg_ids}")

                offset += len(items)
                if len(items) < limit:
                    break

        if packages:
            logger.info(f"✅ VK Ads: получено {len(packages)} пакетов из Packages")
            # ДИАГНОСТИКА: Показываем диапазон ID пакетов
            all_pkg_ids = sorted([int(pid) for pid in packages.keys() if pid.isdigit()])
            if all_pkg_ids:
                logger.info(
                    f"🔍 Package ID диапазон: min={all_pkg_ids[0]}, max={all_pkg_ids[-1]}, "
                    f"первые 10: {all_pkg_ids[:10]}, последние 10: {all_pkg_ids[-10:]}"
                )
        else:
            logger.warning("⚠️ VK Ads: не удалось получить список пакетов из Packages")

        return packages

    async def get_packages_by_ids(self, package_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Получает конкретные пакеты по их ID.
        Используется когда package_id из AdGroup не найден в общем списке.
        """
        packages = {}
        
        if not package_ids:
            return packages
        
        async with httpx.AsyncClient() as client:
            for package_id in package_ids:
                try:
                    url = f"{self.base_url}/packages/{package_id}.json"
                    params = {}
                    if self.account_id:
                        params["client_id"] = self.account_id
                    
                    await self._throttle()
                    response = await client.get(url, params=params, headers=self.headers, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        # Ответ может быть {"item": {...}} или просто {...}
                        package_data = data.get("item") or data
                        if package_data.get("id"):
                            packages[str(package_id)] = package_data
                            logger.info(f"✅ Получен пакет {package_id} индивидуальным запросом")
                    elif response.status_code == 404:
                        logger.warning(f"⚠️ Пакет {package_id} не найден (404)")
                    else:
                        logger.warning(f"⚠️ Ошибка получения пакета {package_id}: {response.status_code}")
                except Exception as e:
                    logger.debug(f"Ошибка запроса пакета {package_id}: {e}")
                    continue
                
                # Небольшая задержка между запросами
                await asyncio.sleep(0.1)
        
        return packages

    async def get_goal_actions_from_packages(self, campaign_ids: List[str]) -> Dict[str, tuple]:
        """
        Получает целевые действия через AdGroup -> package_id -> Packages.objective.
        """
        goal_actions_map: Dict[str, tuple] = {}
        
        self._push_debug(f"get_goal_actions_from_packages START -> campaigns={len(campaign_ids)}")
        
        if not campaign_ids:
            self._push_debug("campaign_ids пустой!")
            return goal_actions_map

        try:
            ad_groups = await self.get_ad_groups(campaign_ids)
            self._push_debug(f"ad_groups result -> items={len(ad_groups)}")
            
            if ad_groups and len(ad_groups) > 0:
                first_group_keys = list(ad_groups[0].keys())
                self._push_debug(f"ad_groups[0] keys -> {first_group_keys}")
                self._push_debug(f"ad_groups[0] FULL -> {str(ad_groups[0])[:300]}")
            
            if not ad_groups:
                self._push_debug("AdGroups пустой!")
                return goal_actions_map

            packages_map = await self.get_packages_map()
            self._push_debug(f"packages result -> items={len(packages_map)}")
            
            if packages_map:
                first_package = next(iter(packages_map.values()))
                first_package_keys = list(first_package.keys())
                self._push_debug(f"packages[0] keys -> {first_package_keys}")
                self._push_debug(f"packages[0] FULL -> {str(first_package)[:300]}")
            
            if not packages_map:
                self._push_debug("Packages пустой!")
                return goal_actions_map

            # Создаем Set из ID кампаний для проверки
            campaign_ids_set = set(str(cid) for cid in campaign_ids)
            campaigns_with_goals = set()
            
            # ДИАГНОСТИКА: Собираем все package_id из AdGroups и подсчитываем кампании с AdGroups
            ad_group_package_ids = set()
            campaigns_with_ad_groups = set()
            for group in ad_groups:
                campaign_id = (
                    group.get("ad_plan_id")
                    or group.get("adplan_id")
                    or group.get("campaign_id")
                    or group.get("plan_id")
                )
                if campaign_id:
                    campaigns_with_ad_groups.add(str(campaign_id))
                
                pkg_id = group.get("package_id") or (group.get("package", {}).get("id") if isinstance(group.get("package"), dict) else None)
                if pkg_id:
                    ad_group_package_ids.add(str(pkg_id))
            
            # ДИАГНОСТИКА: Находим кампании без AdGroups
            campaigns_without_ad_groups = campaign_ids_set - campaigns_with_ad_groups
            if campaigns_without_ad_groups:
                logger.warning(
                    f"⚠️ ДИАГНОСТИКА: {len(campaigns_without_ad_groups)} кампаний БЕЗ AdGroups: "
                    f"{sorted(list(campaigns_without_ad_groups)[:10])}"
                )
                self._push_debug(f"campaigns WITHOUT ad_groups: {sorted(list(campaigns_without_ad_groups)[:20])}")
            
            # ДИАГНОСТИКА: Собираем все ID из packages_map
            packages_map_ids = set(packages_map.keys())
            
            # ДИАГНОСТИКА: Находим несовпадения
            missing_packages = ad_group_package_ids - packages_map_ids
            if missing_packages:
                logger.warning(
                    f"🔍 ДИАГНОСТИКА: В AdGroups используются {len(missing_packages)} package_id, "
                    f"которых НЕТ в Packages: {sorted(list(missing_packages)[:10])}"
                )
                self._push_debug(f"MISSING packages: {sorted(list(missing_packages)[:20])}")
                
                # ИСПРАВЛЕНИЕ: Запрашиваем недостающие пакеты индивидуально
                logger.info(f"🔄 Запрашиваем {len(missing_packages)} недостающих пакетов индивидуально...")
                missing_packages_data = await self.get_packages_by_ids(list(missing_packages))
                if missing_packages_data:
                    logger.info(f"✅ Получено {len(missing_packages_data)} недостающих пакетов")
                    # Добавляем недостающие пакеты в общий словарь
                    packages_map.update(missing_packages_data)
                    packages_map_ids = set(packages_map.keys())  # Обновляем set ID
                else:
                    logger.warning(f"⚠️ Не удалось получить недостающие пакеты")
            
            logger.info(
                f"🔍 ДИАГНОСТИКА: AdGroups имеют {len(ad_group_package_ids)} уникальных package_id, "
                f"Packages содержит {len(packages_map_ids)} пакетов (после догрузки)"
            )
            
            for idx, group in enumerate(ad_groups):
                # Пытаемся определить связь группы с кампанией
                campaign_id = (
                    group.get("ad_plan_id")
                    or group.get("adplan_id")
                    or group.get("campaign_id")
                    or group.get("plan_id")
                )
                if campaign_id is None:
                    if idx < 5:
                        self._push_debug(f"group[{idx}] NO campaign_id -> keys={list(group.keys())}")
                        logger.warning(f"🔍 AdGroup[{idx}] БЕЗ campaign_id: keys={list(group.keys())}")
                    continue
                
                package_id = group.get("package_id") or (group.get("package", {}).get("id") if isinstance(group.get("package"), dict) else None)
                
                # ДИАГНОСТИКА: Логируем для всех групп без package_id
                if package_id is None:
                    if idx < 5:
                        self._push_debug(f"group[{idx}] NO package_id -> keys={list(group.keys())}")
                        logger.warning(f"🔍 AdGroup[{idx}] campaign={campaign_id} БЕЗ package_id: {group}")
                    continue
                
                # ДИАГНОСТИКА: Логируем для первых 5 групп
                if idx < 5:
                    logger.info(f"🔍 AdGroup[{idx}] campaign={campaign_id}, package_id={package_id} (type={type(package_id).__name__})")

                package = packages_map.get(str(package_id))
                if not package:
                    # ДИАГНОСТИКА: Логируем ВСЕ случаи, когда package не найден
                    logger.warning(
                        f"🔍 AdGroup campaign={campaign_id}, package_id={package_id} → "
                        f"НЕ НАЙДЕН в packages_map! Проверяем ближайшие ID..."
                    )
                    # Показываем несколько ближайших ID из packages_map для сравнения
                    sample_ids = sorted(list(packages_map.keys())[:10])
                    logger.warning(f"   Примеры ID в packages_map: {sample_ids}")
                    if idx < 3:
                        self._push_debug(f"package {package_id} NOT FOUND, sample_ids={sample_ids}")
                    continue

                objective_code, objective_name = self._extract_goal_action_from_package(package)
                if objective_code:
                    goal_actions_map[str(campaign_id)] = (objective_code, objective_name)
                    campaigns_with_goals.add(str(campaign_id))
                    if idx < 3:
                        self._push_debug(
                            f"group[{idx}] MATCH -> campaign={campaign_id}, pkg={package_id}, "
                            f"obj={objective_code} -> name={objective_name}"
                        )

            # Проверяем, для каких кампаний НЕ нашлись цели
            campaigns_without_goals = campaign_ids_set - campaigns_with_goals
            if campaigns_without_goals:
                logger.warning(
                    f"⚠️ VK Ads: для {len(campaigns_without_goals)} кампаний НЕ найдены целевые действия: "
                    f"{sorted(list(campaigns_without_goals)[:5])}{'...' if len(campaigns_without_goals) > 5 else ''}"
                )
                self._push_debug(f"campaigns WITHOUT goals -> {len(campaigns_without_goals)}/{len(campaign_ids)}")
                
                # FALLBACK: Для кампаний без целей (особенно без AdGroups) пробуем индивидуальные запросы
                if len(campaigns_without_goals) <= 15:  # Ограничиваем количество
                    logger.info(f"🔄 Пробуем fallback: запрашиваем objective для {len(campaigns_without_goals)} кампаний...")
                    async with httpx.AsyncClient() as client:
                        for idx, camp_id in enumerate(sorted(list(campaigns_without_goals))[:15]):
                            try:
                                ad_plan_url = f"{self.base_url}/ad_plans/{camp_id}.json"
                                ad_plan_params = {"fields": "id,name,objective,status"}
                                if self.account_id:
                                    ad_plan_params["client_id"] = self.account_id
                                
                                ad_plan_response = await client.get(ad_plan_url, params=ad_plan_params, headers=self.headers, timeout=10.0)
                                if ad_plan_response.status_code == 200:
                                    ad_plan_data = ad_plan_response.json()
                                    ad_plan_item = ad_plan_data.get("item") or ad_plan_data
                                    
                                    if idx < 3:
                                        logger.info(f"🔍 Fallback ad_plan[{camp_id}] -> {str(ad_plan_item)[:200]}")
                                    
                                    goal_id, goal_name = self._extract_goal_action(ad_plan_item)
                                    if goal_id or goal_name:
                                        goal_actions_map[camp_id] = (goal_id, goal_name)
                                        campaigns_with_goals.add(camp_id)
                                        logger.info(f"✅ Fallback: найдена цель для кампании {camp_id}: {goal_name}")
                                
                                await asyncio.sleep(0.2)  # Задержка между запросами
                            except Exception as e:
                                if idx < 3:
                                    logger.debug(f"Fallback ad_plan[{camp_id}] ERROR: {str(e)[:200]}")
                                continue
                    
                    # Обновляем статистику после fallback
                    campaigns_without_goals = campaign_ids_set - campaigns_with_goals
                    if len(campaigns_without_goals) < len(campaign_ids_set):
                        logger.info(f"✅ После fallback: найдено {len(goal_actions_map)} целей (осталось без целей: {len(campaigns_without_goals)})")
            
            self._push_debug(f"packages objective -> goals={len(goal_actions_map)}")
            if goal_actions_map:
                logger.info(f"✅ VK Ads: найдено {len(goal_actions_map)} целевых действий через Packages")
            else:
                logger.warning("⚠️ VK Ads: цели через Packages не найдены")

        except Exception as e:
            logger.error(f"❌ ОШИБКА в get_goal_actions_from_packages: {e}", exc_info=True)
            self._push_debug(f"ERROR -> {str(e)[:200]}")

        return goal_actions_map

    async def get_goals(self, campaign_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Получает список целей (Goals) для кампаний.
        
        Согласно документации VK Ads API (https://ads.vk.com/doc/api):
        Endpoint: GET /api/v2/goals.json
        Параметры:
        - client_id (опционально) - ID кабинета
        - ids (опционально) - список ID целей
        
        Returns:
            Dict[str, Dict] - словарь {goal_id: {id, name, ...}}
        """
        url = f"{self.base_url}/goals.json"
        params = {}
        
        if self.account_id:
            params["client_id"] = self.account_id
        
        if campaign_ids:
            # Пока не используем campaign_ids, так как Goals API может не поддерживать фильтрацию по кампаниям
            pass
        
        try:
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 Retrieved {len(items)} goal(s) from VK Ads API")
                    
                    goals_map = {}
                    for item in items:
                        goal_id = str(item.get("id", ""))
                        goal_name = item.get("name") or item.get("title") or f"Goal {goal_id}"
                        goals_map[goal_id] = {
                            "id": goal_id,
                            "name": goal_name,
                            "type": item.get("type"),
                            "category": item.get("category")
                        }
                    
                    return goals_map
                else:
                    logger.warning(f"⚠️ Failed to fetch VK goals: {response.status_code} - {response.text[:200]}")
                    return {}
        except Exception as e:
            logger.warning(f"⚠️ Error fetching VK goals: {e}")
            return {}

    async def get_statistics(
        self,
        date_from: str,
        date_to: str,
        campaigns: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получает статистику по рекламным кампаниям (AdPlans).
        
        Согласно документации VK Ads API (https://ads.vk.com/doc/api/info/Statistics):
        Endpoint: GET /api/v2/statistics/ad_plans/day.json
        Параметры:
        - date_from (обязательно) - начальная дата (YYYY-MM-DD)
        - date_to (обязательно) - конечная дата (YYYY-MM-DD)
        - metrics (по умолчанию "base") - набор метрик
        - id (обязательно) - список ID кампаний
        
        API ограничивает один запрос 200 объектами и последними 366 днями.
        Профиль определяется OAuth-токеном; client_id в Statistics не передаётся.
        """
        # Получаем названия кампаний для маппинга
        campaigns = campaigns if campaigns is not None else await self.get_campaigns()
        campaign_ids = [str(c.get("id")) for c in campaigns if c.get("id") is not None]
        if not campaign_ids:
            logger.info("VK Ads: статистика не запрашивается — список кампаний пуст")
            return []
        names_map = {str(c["id"]): c["name"] for c in campaigns}
        
        # Разбиваем диапазон дат на чанки (максимум 366 дней согласно документации)
        date_chunks = self._split_date_range(date_from, date_to, 90)
        all_results = []

        async with httpx.AsyncClient() as client:
            for d_from, d_to in date_chunks:
                for id_offset in range(0, len(campaign_ids), 200):
                    id_chunk = campaign_ids[id_offset:id_offset + 200]
                # Согласно документации: GET /api/v2/statistics/ad_plans/day.json
                    url = f"{self.base_url}/statistics/ad_plans/day.json"
                    params = {
                        "date_from": d_from,
                        "date_to": d_to,
                        "id": ",".join(id_chunk),
                        "metrics": "base",
                    }

                    max_retries = 3
                    retry_delay = 5
                    last_error: Optional[Exception] = None
                
                    for attempt in range(max_retries):
                        try:
                            await self._throttle()
                            response = await client.get(
                                url,
                                params=params,
                                headers=self.headers,
                                timeout=120.0,
                            )
                        
                            if response.status_code == 200:
                                all_results.extend(self._parse_response(response.json(), names_map))
                                last_error = None
                                break

                            message = (
                                f"VK Ads statistics HTTP {response.status_code} "
                                f"for {d_from}..{d_to}, ids {id_offset + 1}-"
                                f"{id_offset + len(id_chunk)}: {(response.text or '')[:300]}"
                            )
                            last_error = RuntimeError(message)
                            if response.status_code == 429 and attempt < max_retries - 1:
                                retry_after = response.headers.get("Retry-After")
                                try:
                                    wait_time = max(float(retry_after), 1.0)
                                except (TypeError, ValueError):
                                    wait_time = retry_delay * (attempt + 1)
                                logger.warning("%s; retry in %.1fs", message, wait_time)
                                await asyncio.sleep(wait_time)
                                continue
                            if response.status_code >= 500 and attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay * (attempt + 1))
                                continue
                            _log_vk_error_for_support(response, "GET statistics/ad_plans/day.json")
                            raise last_error
                        except (httpx.TimeoutException, httpx.NetworkError) as exc:
                            last_error = exc
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay * (attempt + 1))
                                continue
                            raise RuntimeError(
                                f"VK Ads statistics request failed for {d_from}..{d_to}"
                            ) from exc

                    if last_error is not None:
                        raise last_error

                    if id_offset + len(id_chunk) < len(campaign_ids):
                        await asyncio.sleep(0.55)
                if d_to != date_chunks[-1][1]:
                    await asyncio.sleep(0.55)
                    
        return all_results

    def _split_date_range(self, date_from: str, date_to: str, interval: int = 90) -> List[tuple]:
        """Splits a date range into smaller chunks."""
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        
        chunks = []
        curr = start
        while curr <= end:
            chunk_end = min(curr + timedelta(days=interval), end)
            chunks.append((curr.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
            curr = chunk_end + timedelta(days=1)
        return chunks

    def _parse_response(self, data: Dict[str, Any], names_map: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Парсит ответ VK Ads API Statistics.
        
        Согласно документации (https://ads.vk.com/doc/api/info/Statistics):
        Структура ответа:
        {
          "items": [
            {
              "id": <campaign_id>,
              "rows": [
                {
                  "date": "YYYY-MM-DD",
                  "base": {
                    "shows": <impressions>,
                    "clicks": <clicks>,
                    "spent": <cost>,
                    "vk.goals": <conversions>,
                    "vk.cpa": <cpa>,
                    "vk.cr": <conversion_rate>
                  }
                }
              ]
            }
          ]
        }
        """
        results = []
        items = data.get("items", [])
        for item in items:
            campaign_id = item.get("id")
            campaign_key = str(campaign_id) if campaign_id is not None else ""
            campaign_name = names_map.get(campaign_key, f"Campaign {campaign_id}")
            rows = item.get("rows", [])
            for row in rows:
                base = row.get("base", {})
                # Дата находится на уровне row
                row_date = row.get("date")
                if not row_date:
                    continue
                
                # Согласно документации, метрики в base:
                # - shows - количество показов
                # - clicks - количество кликов
                # - spent - списания
                # - cpc - средняя цена клика (eCPC)
                # - vk.goals - количество достижений целей (Результат/Лиды) [ВЛОЖЕННАЯ СТРУКТУРА: base["vk"]["goals"]]
                # - vk.cpa - среднее списание за достижение 1 цели (Средняя цена цели) [ВЛОЖЕННАЯ СТРУКТУРА: base["vk"]["cpa"]]
                # - vk.cr - процентное отношение количества достижений целей к количеству кликов [ВЛОЖЕННАЯ СТРУКТУРА: base["vk"]["cr"]]
                
                # CRITICAL: VK API возвращает метрики целей (Цена за результат = vk.cpa, Результат = vk.goals).
                # Документация: https://ads.vk.com/doc/api/info/Statistics — base содержит vk: { goals, cpa, cr }.
                # В части ответов API также дублирует их на уровне base: goals, cpa, cr — учитываем оба варианта.
                vk_section = base.get("vk") or {}
                
                # Получаем CPC из base (средняя цена клика)
                vk_cpc = base.get("cpc")
                # CPA (Цена за результат): приоритет base["vk"]["cpa"], fallback base["cpa"]
                vk_cpa = vk_section.get("cpa") if isinstance(vk_section, dict) else None
                if vk_cpa is None:
                    vk_cpa = base.get("cpa")
                # Результат (лиды): приоритет base["vk"]["goals"], fallback base["goals"]
                conversions_val = 0
                if isinstance(vk_section, dict):
                    conversions_val = int(vk_section.get("goals", 0) or 0)
                if conversions_val == 0:
                    conversions_val = int(base.get("goals", 0) or 0)
                
                # Если cpc не указан в API, рассчитываем как cost/clicks
                if vk_cpc is None or vk_cpc == 0 or (isinstance(vk_cpc, str) and float(vk_cpc) == 0):
                    clicks_val = int(base.get("clicks", 0))
                    cost_val = float(base.get("spent", 0))
                    vk_cpc = cost_val / clicks_val if clicks_val > 0 else 0.0
                else:
                    vk_cpc = float(vk_cpc)
                
                # Если vk.cpa (Цена за результат) не указан в API, рассчитываем как cost/conversions
                try:
                    cpa_num = float(vk_cpa) if vk_cpa is not None else 0.0
                except (TypeError, ValueError):
                    cpa_num = 0.0
                if cpa_num == 0.0 and conversions_val > 0:
                    cost_val = float(base.get("spent", 0))
                    vk_cpa = cost_val / conversions_val
                else:
                    vk_cpa = cpa_num
                
                results.append({
                    "date": row_date,
                    "campaign_id": str(campaign_id) if campaign_id else "",
                    "campaign_name": campaign_name,
                    "impressions": int(base.get("shows", 0)),
                    "clicks": int(base.get("clicks", 0)),
                    "cost": float(base.get("spent", 0)),
                    "conversions": conversions_val,  # vk.goals = Результат (лиды) - из base["vk"]["goals"]
                    "cpc": vk_cpc,  # Средняя цена клика (eCPC)
                    "cpa": vk_cpa   # vk.cpa = Средняя цена цели - из base["vk"]["cpa"]
                })
        return results
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных рекламных аккаунтов (кабинетов).
        
        Согласно документации VK Ads API (https://ads.vk.com/doc/api/info/Statistics):
        Используем endpoint /api/v2/statistics/users/summary.json без параметра id
        для получения списка всех доступных кабинетов (users).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта (нормализованный числовой ID)
            - name: str - название аккаунта
            - status: str - статус аккаунта
        """
        accounts = []
        
        # Метод 1: Используем Statistics API для получения списка кабинетов
        # Документация: https://ads.vk.com/doc/api/info/Statistics
        # GET /api/v2/statistics/users/summary.json (без параметра id возвращает все кабинеты)
        try:
            url = f"{self.base_url}/statistics/users/summary.json"
            params = {
                "metrics": "base"  # Базовые метрики для получения списка кабинетов
            }
            
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 VK Ads Statistics API returned {len(items)} account(s) from users/summary.json")
                    
                    for item in items:
                        raw_id = item.get("id")
                        if not raw_id:
                            continue
                            
                        raw_id_str = str(raw_id)
                        
                        # Нормализуем account_id (извлекаем числовой ID из формата "vkads_592676405@vk@8493881")
                        import re
                        account_id = None
                        
                        if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                            # Формат: "vkads_592676405@vk@8493881" -> извлекаем "592676405"
                            match = re.search(r'vkads_(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                            else:
                                # Fallback: извлекаем первую числовую последовательность
                                match = re.search(r'(\d+)', raw_id_str)
                                if match:
                                    account_id = match.group(1)
                        elif raw_id_str.isdigit():
                            account_id = raw_id_str
                        else:
                            # Пытаемся извлечь любую числовую последовательность
                            match = re.search(r'(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        
                        if account_id:
                            # Пытаемся получить название кабинета из статистики или используем ID
                            account_name = f"Кабинет {account_id}"  # По умолчанию
                            
                            # Если есть данные в статистике, можно попытаться извлечь название
                            # Но обычно название нужно получать из другого endpoint
                            
                            accounts.append({
                                "id": account_id,
                                "name": account_name,
                                "status": "active"
                            })
                            
                            logger.info(f"✅ Added VK account from statistics: id={account_id}")
                        else:
                            logger.warning(f"⚠️ Could not extract numeric ID from: '{raw_id_str}', skipping")
                    
                    if accounts:
                        logger.info(f"✅ Successfully retrieved {len(accounts)} VK account(s) via Statistics API")
                        # Пытаемся получить названия кабинетов из кампаний
                        await self._enrich_accounts_with_names(accounts)
                        return accounts
                else:
                    logger.warning(f"⚠️ VK Ads Statistics API returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching VK accounts from Statistics API: {e}")
        
        # Метод 2: Fallback - пытаемся использовать старый endpoint
        try:
            url = f"{self.base_url}/ad_accounts.json"
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 VK Ads API returned {len(items)} account(s) from ad_accounts.json (fallback)")
                    
                    for item in items:
                        raw_id = item.get("id")
                        raw_id_str = str(raw_id)
                        
                        import re
                        account_id = None
                        
                        if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                            match = re.search(r'vkads_(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        elif raw_id_str.isdigit():
                            account_id = raw_id_str
                        else:
                            match = re.search(r'(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        
                        if account_id:
                            account_name = item.get("name", f"Аккаунт {account_id}")
                            account_status = item.get("status", "active")
                            
                            accounts.append({
                                "id": account_id,
                                "name": account_name,
                                "status": account_status
                            })
                            
                            logger.info(f"✅ Added VK account: id={account_id}, name='{account_name}'")
                    
                    if accounts:
                        logger.info(f"✅ Successfully retrieved {len(accounts)} VK account(s) via fallback method")
                        return accounts
        except Exception as e:
            logger.debug(f"Fallback method failed: {e}")
        
        # Метод 3: Извлекаем из статистики кампаний
        try:
            accounts = await self._get_accounts_from_statistics()
            if accounts:
                logger.info(f"✅ Found {len(accounts)} account(s) via statistics extraction method")
                return accounts
        except Exception as e:
            logger.debug(f"Statistics extraction method failed: {e}")
        
        # Fallback: Если account_id задан в конструкторе, используем его
        if self.cabinet_id:
            account_id_str = str(self.cabinet_id)
            import re
            if '@vk@' in account_id_str or account_id_str.startswith('vkads_'):
                match = re.search(r'vkads_(\d+)', account_id_str)
                if match:
                    account_id_str = match.group(1)
            
            accounts.append({
                "id": account_id_str,
                "name": f"Аккаунт {account_id_str}",
                "status": "active"
            })
            logger.info(f"✅ Using account_id from constructor as fallback: {account_id_str}")
        
        return accounts
    
    async def _enrich_accounts_with_names(self, accounts: List[Dict[str, Any]]):
        """
        Обогащает список кабинетов названиями, получая их из кампаний.
        Для каждого кабинета запрашиваем первую кампанию и пытаемся извлечь название.
        """
        try:
            async with httpx.AsyncClient() as client:
                for account in accounts:
                    account_id = account.get("id")
                    if not account_id:
                        continue
                    
                    # Запрашиваем кампании для этого кабинета
                    # Согласно документации, можно использовать client_id для фильтрации
                    try:
                        campaigns_url = f"{self.base_url}/ad_plans.json"
                        campaigns_params = {"client_id": account_id, "limit": 1}
                        campaigns_response = await client.get(
                            campaigns_url,
                            params=campaigns_params,
                            headers=self.headers,
                            timeout=10.0
                        )
                        
                        if campaigns_response.status_code == 200:
                            campaigns_data = campaigns_response.json()
                            campaigns_items = campaigns_data.get("items", [])
                            # Если есть кампании, можно использовать их для определения названия кабинета
                            # Но обычно название кабинета не содержится в данных кампаний
                            pass
                    except Exception as e:
                        logger.debug(f"Could not enrich account {account_id} with name: {e}")
        except Exception as e:
            logger.debug(f"Error enriching accounts with names: {e}")
    
    async def _get_accounts_from_statistics(self) -> List[Dict[str, Any]]:
        """
        Альтернативный метод получения кабинетов: используем статистику по users.
        
        Согласно документации VK Ads API:
        GET /api/v2/statistics/users/day.json или summary.json
        Без параметра id возвращает статистику по всем доступным кабинетам.
        """
        accounts = []
        seen_ids = set()
        
        try:
            from datetime import datetime, timedelta
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Используем статистику по users (кабинетам) для получения списка
            # Согласно документации: GET /api/v2/statistics/users/day.json
            url = f"{self.base_url}/statistics/users/day.json"
            params = {
                "date_from": date_from,
                "date_to": date_to,
                "metrics": "base"  # Базовые метрики
            }
            
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📊 Statistics/users response contains {len(items)} account(s)")
                    
                    # Извлекаем уникальные ID кабинетов из статистики
                    for item in items:
                        raw_id = item.get("id")
                        if not raw_id:
                            continue
                            
                        raw_id_str = str(raw_id)
                        
                        # Нормализуем account_id
                        import re
                        account_id = None
                        
                        if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                            match = re.search(r'vkads_(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                            else:
                                match = re.search(r'(\d+)', raw_id_str)
                                if match:
                                    account_id = match.group(1)
                        elif raw_id_str.isdigit():
                            account_id = raw_id_str
                        else:
                            match = re.search(r'(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        
                        if account_id and account_id not in seen_ids:
                            seen_ids.add(account_id)
                            
                            accounts.append({
                                "id": account_id,
                                "name": f"Кабинет {account_id}",
                                "status": "active"
                            })
                            
                            logger.info(f"✅ Extracted account from users statistics: id={account_id}")
                    
                    if accounts:
                        logger.info(f"✅ Extracted {len(accounts)} unique account(s) from users statistics")
                else:
                    logger.warning(f"⚠️ Statistics/users request returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"❌ Error extracting accounts from users statistics: {e}")
        
        return accounts
    
    async def get_agency_clients(self) -> List[Dict[str, Any]]:
        """
        Получает список клиентов агентского аккаунта (если токен принадлежит агентству).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID клиента
            - name: str - название клиента
            - status: str - статус клиента
        """
        url = f"{self.base_url}/agency/clients.json"
        
        try:
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    return [
                        {
                            "id": str(item.get("id")),
                            "name": item.get("name", f"Клиент {item.get('id')}"),
                            "status": item.get("status", "unknown")
                        }
                        for item in items
                    ]
                elif response.status_code == 403:
                    # 403 означает, что это не агентский аккаунт - это нормально
                    logger.debug("VK account is not an agency account (403)")
                    return []
                else:
                    logger.warning(f"Failed to fetch VK agency clients: {response.status_code} - {response.text[:200]}")
                    return []
        except Exception as e:
            logger.debug(f"Error fetching VK agency clients (may not be agency): {e}")
            return []

    async def get_agency_clients_raw(self) -> List[Dict[str, Any]]:
        """Сырые элементы из GET /agency/clients.json (для сопоставления кабинета с user id клиента)."""
        url = f"{self.base_url}/agency/clients.json"
        try:
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    return list(data.get("items") or [])
                logger.warning(
                    "VK Ads get_agency_clients_raw: HTTP %s %s",
                    response.status_code,
                    (response.text or "")[:300],
                )
        except Exception as e:
            logger.warning("VK Ads get_agency_clients_raw: %s", e)
        return []
    
    async def get_profiles(self) -> List[Dict[str, Any]]:
        """
        Получает список всех доступных профилей (аккаунтов) для выбора.
        Включает личный аккаунт и agency клиентов (если есть).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта/клиента
            - name: str - название
            - type: str - "personal" или "agency_client"
        """
        profiles = []
        seen_ids = set()
        
        # 1. Получаем личные аккаунты (кабинеты)
        try:
            accounts = await self.get_accounts()
            for account in accounts:
                account_id = account.get("id")
                if account_id and account_id not in seen_ids:
                    # Используем оригинальное название кабинета из API
                    account_name = account.get("name", f"Аккаунт {account_id}")
                    profiles.append({
                        "id": account_id,
                        "name": account_name,  # Показываем оригинальное название кабинета
                        "type": "personal"
                    })
                    seen_ids.add(account_id)
                    logger.info(f"✅ Added VK account: id={account_id}, name='{account_name}'")
        except Exception as e:
            logger.warning(f"Failed to fetch personal VK accounts: {e}")
        
        # 2. Получаем agency клиентов (если есть)
        try:
            agency_clients = await self.get_agency_clients()
            for client in agency_clients:
                client_id = client.get("id")
                if client_id and client_id not in seen_ids:
                    profiles.append({
                        "id": client_id,
                        "name": f"Клиент агентства ({client.get('name', client_id)})",
                        "type": "agency_client"
                    })
                    seen_ids.add(client_id)
                    logger.info(f"✅ Added VK agency client: {client_id}")
        except Exception as e:
            logger.debug(f"No agency clients found or error: {e}")
        
        # 3. Fallback: Если ничего не найдено, используем account_id из интеграции
        if not profiles and self.cabinet_id:
            profiles.append({
                "id": str(self.cabinet_id),
                "name": f"Аккаунт ({self.cabinet_id})",
                "type": "personal"
            })
            logger.info(f"✅ Added fallback VK profile from account_id: {self.cabinet_id}")
        
        # 4. Fallback: Если account_id не определен, пытаемся получить его из первой кампании
        if not profiles:
            try:
                campaigns = await self.get_campaigns()
                if campaigns:
                    # Попробуем извлечь account_id из данных кампании
                    # Для VK Ads, account_id может быть в данных кампании или мы используем токен по умолчанию
                    logger.info(f"⚠️ No profiles found, but {len(campaigns)} campaigns available. Using default account.")
                    profiles.append({
                        "id": "default",
                        "name": "Аккаунт по умолчанию",
                        "type": "personal"
                    })
            except Exception as e:
                logger.warning(f"Failed to get campaigns for fallback profile: {e}")
        
        # 5. Final fallback: Создаем профиль "default" если ничего не найдено
        if not profiles:
            logger.warning("⚠️ No VK profiles found, creating default profile")
            profiles.append({
                "id": "default",
                "name": "Аккаунт по умолчанию",
                "type": "personal"
            })
        
        return profiles
        
        # Fallback: если ничего не найдено, возвращаем текущий account_id если он есть
        if not profiles and self.cabinet_id:
            profiles.append({
                "id": str(self.cabinet_id),
                "name": f"Аккаунт ({self.cabinet_id})",
                "type": "personal"
            })
            logger.info(f"✅ Added fallback VK account: {self.cabinet_id}")
        
        return profiles
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        Получает баланс рекламного кабинета VK Ads.
        
        Согласно документации VK Ads API:
        - Endpoint для баланса: /api/v2/billing/balance.json (если доступен)
        - Альтернатива: вычисление баланса из TransactionGroups
        - Fallback: /api/v2/ad_accounts.json
        
        Returns:
            Dict с полями:
            - balance: float - баланс в валюте кабинета
            - currency: str - код валюты (RUB, USD, EUR, etc.)
            Или None при ошибке
        """
        # Метод 1: Пытаемся получить баланс через billing/balance.json
        try:
            url = f"{self.base_url}/billing/balance.json"
            params = {}
            if self.account_id:
                params["client_id"] = self.account_id
            
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    # Структура ответа может быть разной
                    # Попробуем разные варианты структуры
                    balance = None
                    currency = "RUB"
                    
                    # Вариант 1: баланс в корне ответа
                    if "balance" in data:
                        balance = data.get("balance")
                        currency = data.get("currency", "RUB")
                    # Вариант 2: баланс в items[0]
                    elif "items" in data and len(data.get("items", [])) > 0:
                        item = data["items"][0]
                        balance = item.get("balance") or item.get("amount") or item.get("funds")
                        currency = item.get("currency", "RUB")
                    # Вариант 3: баланс в result
                    elif "result" in data:
                        result = data["result"]
                        balance = result.get("balance") or result.get("amount") or result.get("funds")
                        currency = result.get("currency", "RUB")
                    
                    if balance is not None:
                        try:
                            balance_float = float(balance) if isinstance(balance, str) else balance
                            logger.info(f"✅ VK Ads balance from billing/balance.json: {balance_float} {currency}")
                            return {
                                "balance": balance_float,
                                "currency": currency
                            }
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse VK balance value: {balance}, error: {e}")
                elif response.status_code == 404:
                    logger.debug(f"⚠️ billing/balance.json endpoint not found (404), trying alternative methods...")
                else:
                    logger.debug(f"⚠️ billing/balance.json returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.debug(f"Error fetching balance from billing/balance.json: {e}")
        
        # Метод 2: Вычисляем баланс из TransactionGroups
        # Согласно документации: https://ads.vk.com/doc/api/resource/TransactionGroups
        # Суммируем транзакции типа "deposit" (пополнения) и вычитаем "charge" (списания)
        try:
            url = f"{self.base_url}/billing/transaction_groups.json"
            params = {
                "limit": 1000,  # Получаем последние транзакции
                "sorting": "-date"  # Сортируем по дате (новые сначала)
            }
            if self.account_id:
                params["client_id"] = self.account_id
            
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    if items:
                        # Вычисляем баланс: суммируем все транзакции
                        # deposit (пополнения) - положительные, charge (списания) - отрицательные
                        total_balance = 0.0
                        currency = "RUB"
                        
                        for item in items:
                            trans_type = item.get("type", "")
                            amount_str = item.get("amount", "0")
                            item_currency = item.get("currency", "RUB")
                            
                            # Используем валюту из первой транзакции
                            if not currency or currency == "RUB":
                                currency = item_currency
                            
                            try:
                                amount = float(amount_str) if isinstance(amount_str, str) else amount_str
                                
                                if trans_type == "deposit":
                                    # Пополнение - добавляем к балансу
                                    total_balance += amount
                                elif trans_type == "charge":
                                    # Списание - вычитаем из баланса
                                    total_balance -= amount
                                # Другие типы транзакций игнорируем или обрабатываем по необходимости
                                
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Failed to parse transaction amount: {amount_str}, error: {e}")
                                continue
                        
                        if total_balance != 0.0 or len(items) > 0:  # Возвращаем баланс даже если он 0
                            logger.info(f"✅ VK Ads balance calculated from TransactionGroups: {total_balance} {currency} ({len(items)} transactions)")
                            return {
                                "balance": total_balance,
                                "currency": currency
                            }
                elif response.status_code == 404:
                    logger.debug(f"⚠️ billing/transaction_groups.json endpoint not found (404), trying fallback...")
                else:
                    logger.debug(f"⚠️ billing/transaction_groups.json returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.debug(f"Error calculating balance from TransactionGroups: {e}")
        
        # Метод 3: Fallback - используем ad_accounts.json (старый метод)
        try:
            url = f"{self.base_url}/ad_accounts.json"
            params = {}
            if self.account_id:
                params["client_id"] = self.account_id
            
            async with httpx.AsyncClient() as client:
                await self._throttle()
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items and len(items) > 0:
                        account = items[0]
                        # VK Ads API возвращает баланс в разных полях в зависимости от версии API
                        balance = account.get("balance") or account.get("amount") or account.get("funds")
                        currency = account.get("currency", "RUB")
                        
                        if balance is not None:
                            try:
                                balance_float = float(balance) if isinstance(balance, str) else balance
                                logger.info(f"✅ VK Ads balance from ad_accounts.json: {balance_float} {currency}")
                                return {
                                    "balance": balance_float,
                                    "currency": currency
                                }
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to parse VK balance value: {balance}, error: {e}")
                                return None
                else:
                    logger.warning(f"⚠️ Failed to fetch VK Ads balance from ad_accounts.json: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Error fetching VK Ads balance from ad_accounts.json: {e}")
        
        logger.warning(f"❌ Could not fetch VK Ads balance using any method")
        return None
