"""Private mTLS service application. No SQL, JWT, providers or schedulers.

Run only with ops.artifact_server (mandatory client certificates), not public
backend_api.main. Role bearer credentials are defense in depth and never URLs.
"""
import asyncio
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import re

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from core.artifact_storage import (CHUNK_BYTES, LocalObjects, ObjectInfo, ObjectMissing,
    ObjectConflict, ObjectCorrupt, StorageUnavailable, object_key)

PERMISSIONS = {"read": {"read"}, "writer": {"read", "write"}, "maintenance": {"read", "delete"}}
PRIVATE = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def create_app(store, principals):
    if not principals or len(principals) > 16:
        raise ValueError("Artifact principals required")
    for name, spec in principals.items():
        if not re.fullmatch(r"[a-z0-9_-]{1,40}", name) or spec.get("role") not in PERMISSIONS:
            raise ValueError("Invalid artifact principal")
        if not re.fullmatch(r"[0-9a-f]{64}", spec.get("sha256", "")):
            raise ValueError("Invalid artifact credential digest")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    uploads = asyncio.Semaphore(4)

    def authorize(request, permission):
        header = request.headers.get("authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
            raise HTTPException(401, "Authentication required", headers=PRIVATE)
        digest = hashlib.sha256(token.encode()).hexdigest()
        matched = None
        for spec in principals.values():
            if hmac.compare_digest(digest, spec["sha256"]):
                matched = spec["role"]
        if matched is None:
            raise HTTPException(401, "Authentication required", headers=PRIVATE)
        if permission not in PERMISSIONS[matched]:
            raise HTTPException(403, "Operation forbidden", headers=PRIVATE)

    def key_of(key):
        try:
            return object_key(key)
        except ValueError:
            raise HTTPException(400, "Invalid object key", headers=PRIVATE) from None

    @app.exception_handler(ObjectMissing)
    async def missing(request, exc):
        return JSONResponse({"detail": "Object unavailable"}, status_code=404, headers=PRIVATE)

    @app.exception_handler(ObjectConflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": "Immutable object conflict"}, status_code=409, headers=PRIVATE)

    async def unavailable(request, exc):
        # No paths, credentials, SQL parameters or stack trace in responses/logs.
        return JSONResponse({"detail": "Storage unavailable"}, status_code=503, headers=PRIVATE)
    for cls in (OSError, ObjectCorrupt, StorageUnavailable):
        app.add_exception_handler(cls, unavailable)

    @app.get("/health")
    def health(request: Request):
        authorize(request, "read")
        os.fstat(store.fd)
        return JSONResponse({"status": "ok"}, headers=PRIVATE)

    @app.put("/objects/{key}")
    async def put(key: str, request: Request):
        authorize(request, "write")
        key = key_of(key)
        try:
            expected = ObjectInfo(key, int(request.headers.get("content-length", "-1")),
                                  request.headers.get("x-content-sha256", ""))
        except ValueError:
            raise HTTPException(400, "Size and digest required", headers=PRIVATE) from None
        try:
            async with asyncio.timeout(0.05):
                await uploads.acquire()
        except TimeoutError:
            raise HTTPException(503, "Upload capacity reached", headers={**PRIVATE, "Retry-After": "1"}) from None
        upload = None
        try:
            async with asyncio.timeout(60):
                upload = await run_in_threadpool(store.begin, expected)
                async for chunk in request.stream():
                    await run_in_threadpool(upload.write, chunk)
                info = await run_in_threadpool(upload.finish)
            return JSONResponse(asdict(info), status_code=201, headers=PRIVATE)
        except ValueError:
            raise HTTPException(400, "Object size or digest mismatch", headers=PRIVATE) from None
        except TimeoutError:
            raise HTTPException(408, "Upload timed out", headers=PRIVATE) from None
        finally:
            if upload is not None:
                await run_in_threadpool(upload.__exit__, None, None, None)
            uploads.release()

    @app.get("/objects/{key}/stat")
    def info(key: str, request: Request):
        authorize(request, "read")
        return JSONResponse(asdict(store.stat(key_of(key))), headers=PRIVATE)

    @app.get("/objects/{key}")
    def get(key: str, request: Request):
        authorize(request, "read")
        key = key_of(key)
        info = store.stat(key)
        async def chunks():
            opened = store.open(key, expected=info)
            with anyio.CancelScope(shield=True):
                stream, _ = await run_in_threadpool(opened.__enter__)
            try:
                while chunk := await run_in_threadpool(stream.read, CHUNK_BYTES):
                    yield chunk
            finally:
                with anyio.CancelScope(shield=True):
                    await run_in_threadpool(opened.__exit__, None, None, None)
        return StreamingResponse(chunks(), media_type="application/octet-stream", headers={**PRIVATE,
            "Content-Length": str(info.size), "X-Content-SHA256": info.sha256})

    @app.delete("/objects/{key}")
    def delete(key: str, request: Request):
        authorize(request, "delete")
        store.delete(key_of(key))
        return Response(status_code=204, headers=PRIVATE)

    return app


def from_environment():
    principals = json.loads(Path(os.environ["ARTIFACT_PRINCIPALS_FILE"]).read_text())
    min_free = int(os.getenv("ARTIFACT_MIN_FREE_BYTES", str(512 * 1024 * 1024)))
    if not 64 * 1024 * 1024 <= min_free <= 100 * 1024 ** 3:
        raise ValueError("Artifact disk reserve must be 64 MiB..100 GiB")
    store = LocalObjects(os.environ["ARTIFACT_ROOT"], min_free_bytes=min_free)
    return create_app(store, principals)
