#!/usr/bin/env python3
"""Verify the dedicated Redis monitor ACL without exposing its password."""

from __future__ import annotations

import json
import socket
from pathlib import Path


def command(*parts: str) -> bytes:
    encoded = [part.encode("utf-8") for part in parts]
    chunks = [f"*{len(encoded)}\r\n".encode()]
    for part in encoded:
        chunks.extend((f"${len(part)}\r\n".encode(), part, b"\r\n"))
    return b"".join(chunks)


def read_line(stream) -> bytes:
    value = stream.readline()
    if not value.endswith(b"\r\n"):
        raise RuntimeError("truncated Redis response")
    return value[:-2]


def reply(stream):
    prefix = stream.read(1)
    if prefix == b"+":
        return read_line(stream).decode("utf-8", errors="replace")
    if prefix == b"-":
        return RuntimeError(read_line(stream).decode("utf-8", errors="replace"))
    if prefix == b":":
        return int(read_line(stream))
    if prefix == b"$":
        length = int(read_line(stream))
        if length < 0:
            return None
        value = stream.read(length)
        if stream.read(2) != b"\r\n":
            raise RuntimeError("invalid Redis bulk response")
        return value
    raise RuntimeError("unexpected Redis response type")


def execute(stream, *parts: str):
    stream.write(command(*parts))
    stream.flush()
    return reply(stream)


def check(address: str, port: int, password: str) -> None:
    with socket.create_connection((address, port), timeout=3) as connection:
        connection.settimeout(3)
        with connection.makefile("rwb", buffering=0) as stream:
            if execute(stream, "AUTH", "monitor", password) != "OK":
                raise RuntimeError("Redis monitor authentication failed")
            if execute(stream, "PING") != "PONG":
                raise RuntimeError("Redis monitor ping failed")
            info = execute(stream, "INFO", "server")
            if not isinstance(info, bytes) or b"redis_version:" not in info:
                raise RuntimeError("Redis monitor INFO failed")
            denied = execute(stream, "SET", "admirra:monitor:forbidden", "value")
            if not isinstance(denied, RuntimeError) or "NOPERM" not in str(denied):
                raise RuntimeError("Redis monitor unexpectedly has write access")


def main() -> None:
    credentials = json.loads(Path("/etc/admirra/redis-credentials.json").read_text(encoding="utf-8"))
    password = credentials.get("monitor")
    if not isinstance(password, str) or len(password) < 40:
        raise RuntimeError("Redis monitor credential is missing")
    for port in (6379, 6380):
        check("10.77.0.2", port, password)
    print("Redis monitor ACL: authentication/read metrics allowed, writes denied")


if __name__ == "__main__":
    main()
