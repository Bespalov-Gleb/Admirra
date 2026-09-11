"""Immutable filesystem objects behind a private service, never a public path.

Only canonical UUID keys. Database metadata/tenant authorization belong to the
caller. A deleted key stays tombstoned: a delayed upload cannot resurrect it.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import time
import uuid

MAX_BYTES = 50 * 1024 * 1024
CHUNK_BYTES = 256 * 1024


class StorageUnavailable(Exception):
    pass


class ObjectMissing(Exception):
    pass


class ObjectConflict(Exception):
    pass


class ObjectCorrupt(Exception):
    pass


def object_key(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError("A canonical object UUID is required")
    return value


@dataclass(frozen=True)
class ObjectInfo:
    key: str
    size: int
    sha256: str

    def __post_init__(self):
        object_key(self.key)
        if isinstance(self.size, bool) or not isinstance(self.size, int) or not 0 <= self.size <= MAX_BYTES:
            raise ValueError("Invalid object size")
        if not isinstance(self.sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("Invalid object digest")


class LocalObjects:
    def __init__(self, root, min_free_bytes=0):
        root = Path(root)
        if not root.is_absolute():
            raise ValueError("Object root must be absolute")
        # Parent directory is an operator-controlled mount, not user input.
        self.fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.min_free_bytes = min_free_bytes
        try:
            try:
                os.mkdir(".uploads", mode=0o700, dir_fd=self.fd)
                os.fsync(self.fd)
            except FileExistsError:
                pass
            self.temp_fd = os.open(".uploads", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
        except BaseException:
            os.close(self.fd)
            raise

    def close(self):
        if self.fd is not None:
            os.close(self.temp_fd)
            os.close(self.fd)
            self.fd = None

    @contextmanager
    def _lock(self, key):
        # Fixed 256 lock stripes bound lock-file count; works across processes.
        name = ".lock-" + hashlib.sha256(key.encode()).hexdigest()[:2]
        fd = os.open(name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink != 1:
                raise ObjectCorrupt()
            deadline = time.monotonic() + 2
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StorageUnavailable()
                    time.sleep(0.01)
            yield
        finally:
            os.close(fd)

    def _deleted(self, key):
        try:
            os.stat(key + ".deleted", dir_fd=self.fd, follow_symlinks=False)
            return True
        except FileNotFoundError:
            return False

    def _open(self, key):
        try:
            fd = os.open(key, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        except FileNotFoundError:
            raise ObjectMissing() from None
        except OSError:
            raise ObjectCorrupt() from None
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
            os.close(fd)
            raise ObjectCorrupt()
        return os.fdopen(fd, "rb")

    @contextmanager
    def open(self, key, expected=None):
        key = object_key(key)
        with self._lock(key):
            if self._deleted(key):
                raise ObjectMissing()
            stream = self._open(key)
        try:
            digest, length = hashlib.sha256(), 0
            while chunk := stream.read(CHUNK_BYTES):
                length += len(chunk)
                if length > MAX_BYTES:
                    raise ObjectCorrupt()
                digest.update(chunk)
            info = ObjectInfo(key, length, digest.hexdigest())
            if expected is not None and info != expected:
                raise ObjectCorrupt()
            stream.seek(0)
            yield stream, info
        finally:
            stream.close()

    def stat(self, key):
        with self.open(key) as (_, info):
            return info

    def begin(self, expected):
        disk = os.fstatvfs(self.fd)
        if disk.f_bavail * disk.f_frsize < self.min_free_bytes + expected.size:
            raise StorageUnavailable()
        return _Upload(self, expected)

    def put(self, expected, chunks):
        with self.begin(expected) as upload:
            for chunk in chunks:
                upload.write(chunk)
            return upload.finish()

    def delete(self, key):
        """Logical delete, preserving bytes for backup/PITR until explicit GC.

        Maintenance callers must first fence/tombstone database metadata and
        prove no active reference. Never call from public HTTP directly.
        """
        key = object_key(key)
        with self._lock(key):
            if self._deleted(key):
                return
            try:
                with self._open(key):
                    pass
                os.rename(key, key + ".deleted", src_dir_fd=self.fd, dst_dir_fd=self.fd)
                os.utime(key + ".deleted", dir_fd=self.fd, follow_symlinks=False)
            except ObjectMissing:
                fd = os.open(key + ".deleted", os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                             0o600, dir_fd=self.fd)
                os.fsync(fd)
                os.close(fd)
            os.fsync(self.fd)

    def cleanup_parts(self, older_than_seconds=86400, limit=100):
        if older_than_seconds < 3600 or not 1 <= limit <= 1000:
            raise ValueError("Unsafe cleanup bounds")
        removed = 0
        # No traversal, symlink following or cleanup of published/deleted objects.
        with os.scandir(self.temp_fd) as entries:
            for entry in entries:
                if removed >= limit:
                    break
                if not re.fullmatch(r"\.part-[0-9a-f-]{36}", entry.name):
                    continue
                fd = None
                try:
                    fd = os.open(entry.name, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.temp_fd)
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    info = os.fstat(fd)
                    if stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_mtime < time.time() - older_than_seconds:
                        os.unlink(entry.name, dir_fd=self.temp_fd)
                        removed += 1
                except (FileNotFoundError, BlockingIOError):
                    pass
                finally:
                    if fd is not None:
                        os.close(fd)
        if removed:
            os.fsync(self.temp_fd)
        return removed


class _Upload:
    def __init__(self, store, expected):
        if not isinstance(expected, ObjectInfo):
            raise ValueError("Object metadata required")
        self.store, self.expected = store, expected
        self.name = ".part-" + str(uuid.uuid4())
        self.fd = os.open(self.name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                          0o600, dir_fd=store.temp_fd)
        fcntl.flock(self.fd, fcntl.LOCK_EX)  # cleanup skips live uploads, including other processes
        self.digest, self.size, self.finished = hashlib.sha256(), 0, False

    def __enter__(self):
        return self

    def write(self, chunk):
        if self.finished:
            raise ValueError("Upload already finished")
        self.size += len(chunk)
        if self.size > self.expected.size:
            raise ValueError("Upload exceeds declared size")
        view = memoryview(chunk)
        while view:
            count = os.write(self.fd, view)
            if count <= 0:
                raise StorageUnavailable()
            view = view[count:]
        self.digest.update(chunk)

    def finish(self):
        if self.finished:
            raise ValueError("Upload already finished")
        if self.size != self.expected.size or self.digest.hexdigest() != self.expected.sha256:
            raise ValueError("Object size or digest mismatch")
        os.fsync(self.fd)
        key = self.expected.key
        with self.store._lock(key):
            if self.store._deleted(key):
                raise ObjectConflict()
            try:
                stream = self.store._open(key)
            except ObjectMissing:
                # All service mutations take this cross-process stripe lock.
                # Rename publishes one fsynced inode, with no intermediate
                # hard-link state that a killed publisher would leave behind.
                os.rename(self.name, key, src_dir_fd=self.store.temp_fd, dst_dir_fd=self.store.fd)
            else:
                with stream:
                    digest, size = hashlib.sha256(), 0
                    while chunk := stream.read(CHUNK_BYTES):
                        size += len(chunk)
                        digest.update(chunk)
                if (size, digest.hexdigest()) != (self.expected.size, self.expected.sha256):
                    raise ObjectConflict()
                os.unlink(self.name, dir_fd=self.store.temp_fd)
            os.fsync(self.store.fd)
            os.fsync(self.store.temp_fd)
            self.finished = True
        return self.expected

    def __exit__(self, *args):
        os.close(self.fd)
        try:
            os.unlink(self.name, dir_fd=self.store.temp_fd)
        except FileNotFoundError:
            pass
