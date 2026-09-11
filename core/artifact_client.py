"""Bounded mTLS storage adapter. Never return unverified downloaded bytes."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import ssl
import tempfile
import re
import time
from urllib.parse import urlsplit

import httpx

from core.artifact_storage import (CHUNK_BYTES, MAX_BYTES, ObjectInfo, ObjectMissing,
    ObjectConflict, ObjectCorrupt, StorageUnavailable, object_key)


class RemoteObjects:
    def __init__(self, base_url, token, *, ca_file, cert_file, key_file, transport=None):
        url = urlsplit(base_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("A fixed HTTPS artifact origin is required")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
            raise ValueError("Invalid artifact credential format")
        context = ssl.create_default_context(cafile=ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert_file, key_file)
        self.client = httpx.Client(base_url=base_url.rstrip("/"), verify=context, transport=transport,
            trust_env=False, follow_redirects=False, headers={"Authorization": "Bearer " + token, "Accept-Encoding": "identity"},
            timeout=httpx.Timeout(30, connect=3, pool=3), limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))

    def close(self):
        self.client.close()

    @staticmethod
    def _status(response):
        if response.status_code == 404:
            raise ObjectMissing()
        if response.status_code == 409:
            raise ObjectConflict()
        if response.status_code not in {200, 201, 204}:
            # Do not include origin, credential, remote body or upstream traceback.
            raise StorageUnavailable()

    def stat(self, key):
        try:
            info = ObjectInfo(**self._json("GET", "/objects/" + object_key(key) + "/stat"))
            if info.key != key:
                raise ObjectCorrupt()
            return info
        except (httpx.HTTPError, ValueError, TypeError):
            raise StorageUnavailable() from None

    def _json(self, method, path, **kwargs):
        with self.client.stream(method, path, **kwargs) as response:
            self._status(response)
            data = bytearray()
            for chunk in response.iter_bytes(1024):
                data.extend(chunk)
                if len(data) > 4096:
                    raise ObjectCorrupt()
            return json.loads(data)

    def put(self, expected, chunks):
        def bounded():
            total, digest = 0, hashlib.sha256()
            for chunk in chunks:
                total += len(chunk)
                if total > expected.size:
                    raise ValueError("Upload exceeds declared size")
                digest.update(chunk)
                yield chunk
            if total != expected.size or digest.hexdigest() != expected.sha256:
                raise ValueError("Upload does not match metadata")
        try:
            result = self._json("PUT", "/objects/" + expected.key, content=bounded(), headers={
                "Content-Length": str(expected.size), "Content-Type": "application/octet-stream", "X-Content-SHA256": expected.sha256})
            if result != asdict(expected):
                raise ObjectCorrupt()
            return expected
        except httpx.HTTPError:
            raise StorageUnavailable() from None

    @contextmanager
    def open(self, key, expected):
        if not isinstance(expected, ObjectInfo) or object_key(key) != expected.key:
            raise ValueError("Trusted database metadata required for download")
        try:
            with tempfile.TemporaryFile(mode="w+b") as target:
                deadline = time.monotonic() + 60
                with self.client.stream("GET", "/objects/" + key) as response:
                    self._status(response)
                    if response.headers.get("content-encoding", "identity") != "identity":
                        raise ObjectCorrupt()
                    if response.headers.get("content-length") != str(expected.size) or response.headers.get("x-content-sha256") != expected.sha256:
                        raise ObjectCorrupt()
                    length, digest = 0, hashlib.sha256()
                    for chunk in response.iter_bytes(CHUNK_BYTES):
                        length += len(chunk)
                        if length > expected.size or length > MAX_BYTES or time.monotonic() > deadline:
                            raise ObjectCorrupt()
                        target.write(chunk)
                        digest.update(chunk)
                    if length != expected.size or digest.hexdigest() != expected.sha256:
                        raise ObjectCorrupt()
                target.seek(0)
                yield target, expected
        except (httpx.HTTPError, OSError):
            raise StorageUnavailable() from None

    def delete(self, key):
        try:
            response = self.client.delete("/objects/" + object_key(key))
            self._status(response)
        except httpx.HTTPError:
            raise StorageUnavailable() from None


def from_environment():
    return RemoteObjects(os.environ["ARTIFACT_BASE_URL"], Path(os.environ["ARTIFACT_TOKEN_FILE"]).read_text().strip(),
        ca_file=os.environ["ARTIFACT_CA_FILE"], cert_file=os.environ["ARTIFACT_CERT_FILE"], key_file=os.environ["ARTIFACT_KEY_FILE"])
