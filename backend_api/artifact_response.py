"""Verified, bounded artifact downloads with cleanup even on disconnect."""
from contextlib import ExitStack
import logging
import threading

import anyio
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response, JSONResponse, StreamingResponse

from core.artifact_client import from_environment
from core.artifact_storage import CHUNK_BYTES
from backend_api.reports.public_links import PRIVATE_HEADERS

logger = logging.getLogger(__name__)
_downloads = threading.BoundedSemaphore(2)


class ArtifactResponse(Response):
    def __init__(self, info, media_type, filename, *, inline=False, storage_factory=None):
        super().__init__(content=b"", media_type=media_type)
        if any(char in filename for char in ('"', "\r", "\n", "/", "\\")) or not filename.isascii():
            raise ValueError("Unsafe generated download filename")
        self.info, self.media_type, self.filename = info, media_type, filename
        self.inline = inline
        self.storage_factory = storage_factory or from_environment

    def _prepare(self):
        stack = ExitStack()
        try:
            storage = self.storage_factory()
            stack.callback(storage.close)
            stream, _ = stack.enter_context(storage.open(self.info.key, expected=self.info))
            return stack, stream
        except BaseException:
            stack.close()
            raise

    async def __call__(self, scope, receive, send):
        if not _downloads.acquire(blocking=False):
            return await JSONResponse({"detail": "Скачивание временно занято"}, status_code=503,
                headers={**PRIVATE_HEADERS, "Retry-After": "1"})(scope, receive, send)
        stack = None
        try:
            try:
                with anyio.CancelScope(shield=True):
                    stack, stream = await run_in_threadpool(self._prepare)
            except Exception:
                logger.error("Artifact download unavailable")
                return await JSONResponse({"detail": "Файл временно недоступен"}, status_code=503,
                    headers=PRIVATE_HEADERS)(scope, receive, send)
            async def chunks():
                while chunk := await run_in_threadpool(stream.read, CHUNK_BYTES):
                    yield chunk
            disposition = "inline" if self.inline else "attachment"
            response = StreamingResponse(chunks(), media_type=self.media_type, headers={**PRIVATE_HEADERS,
                "Content-Length": str(self.info.size), "Content-Disposition": f'{disposition}; filename="{self.filename}"'})
            await response(scope, receive, send)
        finally:
            try:
                if stack is not None:
                    with anyio.CancelScope(shield=True):
                        await run_in_threadpool(stack.close)
            finally:
                _downloads.release()
