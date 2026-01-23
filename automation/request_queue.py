import asyncio
import time
from typing import Callable, Any, Optional
from collections import deque
import logging

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
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Ждет, пока можно будет сделать запрос"""
        async with self._lock:
            now = time.time()
            
            # Удаляем старые запросы вне временного окна
            while self.request_times and self.request_times[0] < now - self.time_window:
                self.request_times.popleft()
            
            # Если достигнут лимит, ждем
            if len(self.request_times) >= self.max_requests:
                wait_time = self.time_window - (now - self.request_times[0])
                if wait_time > 0:
                    logger.debug(f"Rate limit reached. Waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    # Обновляем время после ожидания
                    now = time.time()
                    # Снова очищаем старые запросы
                    while self.request_times and self.request_times[0] < now - self.time_window:
                        self.request_times.popleft()
            
            # Регистрируем новый запрос
            self.request_times.append(now)


class APIRequestQueue:
    """
    Очередь запросов к внешним API с rate limiting и обработкой 429 ошибок.
    """
    
    def __init__(self):
        # Разные лимитеры для разных API
        self.metrica_limiter = RateLimiter(max_requests=5, time_window=1.0)  # 5 запросов в секунду для Метрики
        self.direct_limiter = RateLimiter(max_requests=10, time_window=1.0)  # 10 запросов в секунду для Директа
        self.vk_limiter = RateLimiter(max_requests=10, time_window=1.0)  # 10 запросов в секунду для VK
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
                except Exception as e:
                    # Обработка 429 ошибки (может быть в httpx.HTTPStatusError или в response)
                    status_code = None
                    if hasattr(e, 'status_code'):
                        status_code = e.status_code
                    elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                    
                    if status_code == 429:
                        # Try to get Retry-After header
                        retry_after = 10
                        if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                            retry_after_header = e.response.headers.get('Retry-After', '10')
                            try:
                                retry_after = int(retry_after_header)
                            except:
                                retry_after = 10
                        
                        logger.warning(f"429 error for {api_type} API. Waiting {retry_after}s before retry")
                        await asyncio.sleep(retry_after)
                        # Повторно добавляем в очередь (с ограничением попыток)
                        task['retry_count'] = task.get('retry_count', 0) + 1
                        if task['retry_count'] < 3:  # Максимум 3 попытки
                            await self._queue.put(task)
                        else:
                            logger.error(f"Max retries reached for {api_type} API request")
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


# Глобальный экземпляр очереди
_request_queue: Optional[APIRequestQueue] = None


async def get_request_queue() -> APIRequestQueue:
    """Получить глобальный экземпляр очереди запросов"""
    global _request_queue
    if _request_queue is None:
        _request_queue = APIRequestQueue()
        await _request_queue.start()
    return _request_queue


async def shutdown_request_queue():
    """Остановить очередь запросов"""
    global _request_queue
    if _request_queue:
        await _request_queue.stop()
        _request_queue = None

