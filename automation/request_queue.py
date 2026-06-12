import asyncio
import time
import threading
from typing import Callable, Any, Optional, Dict
from collections import deque
import logging
import httpx

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter для контроля частоты запросов к внешним API.
    Поддерживает разные лимиты для разных типов запросов.
    """
    
    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        """
        Args:
            max_requests: Максимальное количество запросов
            time_window: Временное окно в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()
        self._lock = threading.Lock()
    
    async def acquire(self):
        """Ждет, пока можно будет сделать запрос"""
        while True:
            wait_time = 0
            with self._lock:
                now = time.time()

                # Удаляем старые запросы вне временного окна
                while self.request_times and self.request_times[0] < now - self.time_window:
                    self.request_times.popleft()

                if len(self.request_times) < self.max_requests:
                    self.request_times.append(now)
                    return

                wait_time = self.time_window - (now - self.request_times[0])

            if wait_time > 0:
                logger.debug(f"Rate limit reached. Waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0)


_GLOBAL_METRICA_LIMITER = RateLimiter(max_requests=2, time_window=1.0)
_GLOBAL_DIRECT_LIMITER = RateLimiter(max_requests=10, time_window=1.0)
_GLOBAL_VK_LIMITER = RateLimiter(max_requests=10, time_window=1.0)


def get_api_limiter(api_type: str) -> RateLimiter:
    return {
        'metrica': _GLOBAL_METRICA_LIMITER,
        'direct': _GLOBAL_DIRECT_LIMITER,
        'vk': _GLOBAL_VK_LIMITER,
    }.get(api_type, _GLOBAL_DIRECT_LIMITER)


class APIRequestQueue:
    """
    Очередь запросов к внешним API с rate limiting и обработкой 429 ошибок.
    """
    
    def __init__(self):
        # Разные лимитеры для разных API
        # Лимитеры общие для всех event loop/thread в процессе, иначе параллельный sync
        # умножает фактическую частоту запросов на количество потоков.
        self.metrica_limiter = _GLOBAL_METRICA_LIMITER
        self.direct_limiter = _GLOBAL_DIRECT_LIMITER
        self.vk_limiter = _GLOBAL_VK_LIMITER
        self._queue = asyncio.Queue()
        self._workers = []
        self._running = False
    
    async def _worker(self, api_type: str):
        """Worker для обработки запросов из очереди"""
        limiter = {
            'metrica': self.metrica_limiter,
            'direct': self.direct_limiter,
            'vk': self.vk_limiter
        }.get(api_type, self.direct_limiter)
        
        while self._running:
            try:
                # Получаем задачу из очереди с таймаутом
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                
                # Применяем rate limiting
                await limiter.acquire()
                
                # Выполняем запрос
                try:
                    result = await task['func'](*task.get('args', []), **task.get('kwargs', {}))
                    if task.get('future'):
                        task['future'].set_result(result)
                except httpx.HTTPStatusError as e:
                    # httpx.HTTPStatusError имеет response с status_code
                    status_code = e.response.status_code if e.response else None
                    if status_code == 429:
                        # Try to get Retry-After header
                        retry_after = 60  # Увеличиваем базовую задержку до 60 секунд для Метрики
                        if e.response and e.response.headers:
                            retry_after_header = e.response.headers.get('Retry-After', '60')
                            try:
                                retry_after = max(int(retry_after_header), 60)  # Минимум 60 секунд
                            except:
                                retry_after = 60
                        
                        task['retry_count'] = task.get('retry_count', 0) + 1
                        if task['retry_count'] < 5:  # Увеличиваем до 5 попыток
                            # Exponential backoff: 60s, 120s, 180s, 240s, 300s
                            actual_wait = retry_after * task['retry_count']
                            logger.warning(f"429 error for {api_type} API (attempt {task['retry_count']}/5). Waiting {actual_wait}s before retry")
                            await asyncio.sleep(actual_wait)
                            # Повторно добавляем в очередь
                            await self._queue.put(task)
                        else:
                            logger.error(f"Max retries (5) reached for {api_type} API request after 429 errors")
                            if task.get('future'):
                                task['future'].set_exception(e)
                    else:
                        if task.get('future'):
                            task['future'].set_exception(e)
                        else:
                            logger.error(f"HTTP error in API request queue: {e}")
                except Exception as e:
                    # Обработка 429 ошибки (может быть в httpx.HTTPStatusError или в response)
                    status_code = None
                    if hasattr(e, 'status_code'):
                        status_code = e.status_code
                    elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                    elif isinstance(e, Exception) and '429' in str(e):
                        status_code = 429
                    
                    if status_code == 429:
                        # Try to get Retry-After header
                        retry_after = 60  # Увеличиваем базовую задержку до 60 секунд для Метрики
                        if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                            retry_after_header = e.response.headers.get('Retry-After', '60')
                            try:
                                retry_after = max(int(retry_after_header), 60)  # Минимум 60 секунд
                            except:
                                retry_after = 60
                        
                        task['retry_count'] = task.get('retry_count', 0) + 1
                        if task['retry_count'] < 5:  # Увеличиваем до 5 попыток
                            # Exponential backoff: 60s, 120s, 180s, 240s, 300s
                            actual_wait = retry_after * task['retry_count']
                            logger.warning(f"429 error for {api_type} API (attempt {task['retry_count']}/5). Waiting {actual_wait}s before retry")
                            await asyncio.sleep(actual_wait)
                            # Повторно добавляем в очередь
                            await self._queue.put(task)
                        else:
                            logger.error(f"Max retries (5) reached for {api_type} API request after 429 errors")
                            if task.get('future'):
                                task['future'].set_exception(e)
                    else:
                        if task.get('future'):
                            task['future'].set_exception(e)
                        else:
                            logger.error(f"Error in API request queue: {e}")
                finally:
                    self._queue.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in queue worker: {e}")
    
    async def start(self, num_workers: int = 3):
        """Запускает воркеры для обработки очереди"""
        self._running = True
        api_types = ['metrica', 'direct', 'vk']
        for i in range(num_workers):
            api_type = api_types[i % len(api_types)]
            worker = asyncio.create_task(self._worker(api_type))
            self._workers.append(worker)
        logger.info(f"API Request Queue started with {num_workers} workers")
    
    async def stop(self):
        """Останавливает воркеры"""
        self._running = False
        await self._queue.join()
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("API Request Queue stopped")
    
    async def enqueue(self, api_type: str, func: Callable, *args, **kwargs) -> Any:
        """
        Добавляет запрос в очередь
        
        Args:
            api_type: Тип API ('metrica', 'direct', 'vk')
            func: Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            Результат выполнения функции
        """
        future = asyncio.Future()
        task = {
            'api_type': api_type,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'future': future
        }
        await self._queue.put(task)
        return await future


# Очередь привязана к event loop: при фоновом синке (отдельный поток + свой loop)
# используется свой loop, иначе воркер в главном loop вызывает set_result() для Future
# из другого loop — await в фоне никогда не возвращается (cross-loop deadlock).
_request_queues: Dict[asyncio.AbstractEventLoop, APIRequestQueue] = {}
_request_queues_lock = threading.Lock()


async def get_request_queue() -> APIRequestQueue:
    """Получить очередь запросов для текущего event loop (каждый loop — своя очередь и воркеры)."""
    loop = asyncio.get_running_loop()
    with _request_queues_lock:
        queue = _request_queues.get(loop)
    if queue is None:
        queue = APIRequestQueue()
        await queue.start()
        with _request_queues_lock:
            _request_queues[loop] = queue
        logger.info(f"API Request Queue started for loop {id(loop)}")
    return queue


async def shutdown_request_queue():
    """Остановить очередь запросов для текущего loop (при shutdown приложения)."""
    loop = asyncio.get_running_loop()
    with _request_queues_lock:
        queue = _request_queues.pop(loop, None)
    if queue:
        await queue.stop()
        logger.info("API Request Queue stopped")
