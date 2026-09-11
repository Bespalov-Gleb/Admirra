"""Synthetic filesystem + real mutual TLS; no database/provider/production IO."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import time
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from fastapi.testclient import TestClient
import httpx
import pytest

from backend_api.artifact_store import create_app
from core.artifact_client import RemoteObjects
from core.artifact_storage import (MAX_BYTES, LocalObjects, ObjectInfo, ObjectConflict,
    ObjectCorrupt, ObjectMissing, StorageUnavailable, object_key)


def descriptor(data=b"synthetic PDF bytes", key=None):
    return ObjectInfo(key or str(uuid.uuid4()), len(data), hashlib.sha256(data).hexdigest())


@pytest.fixture
def store(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    store = LocalObjects(root)
    try:
        yield store, root
    finally:
        store.close()


@pytest.mark.parametrize("key", ["../outside", "/etc/passwd", "a" * 40, "", "..", str(uuid.uuid4()).upper(), "https://example.test/x"])
def test_only_canonical_server_object_keys(key):
    with pytest.raises(ValueError):
        object_key(key)


def test_metadata_bounds():
    for size, digest in ((True, "a" * 64), (-1, "a" * 64), (MAX_BYTES + 1, "a" * 64), (1, "bad")):
        with pytest.raises(ValueError):
            ObjectInfo(str(uuid.uuid4()), size, digest)


def test_atomic_idempotent_and_cross_instance_read(store):
    one, root = store
    data = b"frozen\x00snapshot" * 4000
    info = descriptor(data)
    with one.begin(info) as upload:
        upload.write(data[:10])
        with pytest.raises(ObjectMissing):
            one.stat(info.key)
        upload.write(data[10:])
        assert upload.finish() == info
    two = LocalObjects(root)
    try:
        assert two.stat(info.key) == info
        with two.open(info.key, expected=info) as (stream, actual):
            assert stream.read() == data and actual == info
        assert two.put(info, [data]) == info
        with pytest.raises(ObjectConflict):
            two.put(descriptor(b"other", info.key), [b"other"])
        assert one.stat(info.key) == info
        assert not list((root / ".uploads").glob(".part-*"))
    finally:
        two.close()


@pytest.mark.parametrize("chunks", [[b"short"], [b"way too much data for the expected file"], [b"bad bad bad bad bad"]])
def test_size_hash_failure_publishes_nothing(store, chunks):
    obj, root = store
    info = descriptor()
    with pytest.raises(ValueError):
        obj.put(info, chunks)
    with pytest.raises(ObjectMissing):
        obj.stat(info.key)
    assert not list((root / ".uploads").glob(".part-*"))


def test_disk_full_and_short_writes(store, monkeypatch):
    obj, root = store
    data, write = b"content", os.write
    info = descriptor(data)
    def short(fd, chunk):
        return write(fd, chunk[:2])
    monkeypatch.setattr(os, "write", short)
    assert obj.put(info, [data]) == info
    def full(fd, chunk):
        raise OSError(28, "synthetic full disk")
    monkeypatch.setattr(os, "write", full)
    other = descriptor(data)
    with pytest.raises(OSError):
        obj.put(other, [data])
    with pytest.raises(ObjectMissing):
        obj.stat(other.key)
    assert not list((root / ".uploads").glob(".part-*"))


def test_reserved_disk_space_stops_new_upload_before_tempfile(store, monkeypatch):
    obj, root = store
    from types import SimpleNamespace
    obj.min_free_bytes = 100
    monkeypatch.setattr(os, "fstatvfs", lambda fd: SimpleNamespace(f_bavail=1, f_frsize=10))
    with pytest.raises(StorageUnavailable):
        obj.put(descriptor(b"abc"), [b"abc"])
    assert not list((root / ".uploads").glob(".part-*"))


def test_symlinks_hardlinks_and_corrupt_bytes_are_rejected(store, tmp_path):
    obj, root = store
    info = descriptor(b"data")
    outside = tmp_path / "outside"
    outside.write_bytes(b"secret")
    (root / info.key).symlink_to(outside)
    with pytest.raises(ObjectCorrupt):
        obj.stat(info.key)
    with pytest.raises(ObjectCorrupt):
        obj.put(info, [b"data"])
    (root / info.key).unlink()
    os.link(outside, root / info.key)
    with pytest.raises(ObjectCorrupt):
        obj.stat(info.key)
    (root / info.key).unlink()
    obj.put(info, [b"data"])
    (root / info.key).write_bytes(b"edit")
    with pytest.raises(ObjectCorrupt), obj.open(info.key, expected=info):
        pass
    assert outside.read_bytes() == b"secret"
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(OSError):
        LocalObjects(alias)


def test_delete_is_idempotent_and_fences_inflight_upload(store):
    obj, root = store
    data = b"immutable"
    info = descriptor(data)
    obj.put(info, [data])
    for _ in range(2):
        obj.delete(info.key)
    assert (root / (info.key + ".deleted")).read_bytes() == data
    with pytest.raises(ObjectMissing):
        obj.stat(info.key)
    with pytest.raises(ObjectConflict):
        obj.put(info, [data])
    info = descriptor(data)
    with obj.begin(info) as upload:
        upload.write(data)
        obj.delete(info.key)
        with pytest.raises(ObjectConflict):
            upload.finish()


def test_concurrent_publish_has_one_immutable_winner(store):
    obj, _ = store
    key = str(uuid.uuid4())
    def put(i):
        data = str(i).encode()
        try:
            return obj.put(descriptor(data, key), [data])
        except ObjectConflict:
            return None
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(put, range(8)))
    winners = [info for info in results if info is not None]
    assert len(winners) == 1 and obj.stat(key) == winners[0]


def test_killed_upload_and_bounded_cleanup_preserve_live_files(store):
    obj, root = store
    info = descriptor(b"abc")
    script = """
import json, os, signal, sys
from core.artifact_storage import LocalObjects, ObjectInfo
args = json.load(sys.stdin)
store = LocalObjects(args['root'])
upload = store.begin(ObjectInfo(**args['info']))
upload.write(b'a')
os.kill(os.getpid(), signal.SIGKILL)
"""
    result = subprocess.run([sys.executable, "-c", script], input=json.dumps({"root": str(root), "info": asdict(info)}),
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == -9
    with pytest.raises(ObjectMissing):
        obj.stat(info.key)
    parts = list((root / ".uploads").glob(".part-*"))
    assert len(parts) == 1
    old = time.time() - 90000
    os.utime(parts[0], (old, old))
    live = descriptor(b"live")
    obj.put(live, [b"live"])
    with obj.begin(descriptor(b"pending")) as active:
        active.write(b"pen")
        os.utime(root / ".uploads" / active.name, (old, old))
        assert obj.cleanup_parts(limit=1) == 1
        assert obj.cleanup_parts() == 0  # live FD lock prevents cleanup
    assert obj.stat(live.key) == live
    assert not list((root / ".uploads").glob(".part-*"))


@pytest.fixture
def credentials():
    tokens = {role: secrets.token_urlsafe(32) for role in ("read", "writer", "maintenance")}
    principals = {role: {"role": role, "sha256": hashlib.sha256(token.encode()).hexdigest()} for role, token in tokens.items()}
    return tokens, principals


def test_private_http_roles_integrity_and_error_contract(store, credentials):
    obj, _ = store
    tokens, principals = credentials
    client = TestClient(create_app(obj, principals))
    data, info = b"synthetic PDF bytes", descriptor()
    path = "/objects/" + info.key
    def headers(role, **extra):
        return {"Authorization": "Bearer " + tokens[role], **extra}
    write = headers("writer", **{"X-Content-SHA256": info.sha256})
    assert client.get(path).status_code == 401
    assert client.put(path, content=data, headers=headers("read")).status_code == 403
    assert client.put(path, content=data, headers=write).status_code == 201
    assert client.put(path, content=data, headers=write).status_code == 201
    response = client.get(path, headers=headers("read"))
    assert response.content == data and response.headers["x-content-sha256"] == info.sha256
    assert response.headers["cache-control"] == "no-store"
    assert client.delete(path, headers=headers("writer")).status_code == 403
    assert client.delete(path, headers=headers("maintenance")).status_code == 204
    assert client.get(path, headers=headers("read")).status_code == 404
    assert client.put(path, content=data, headers=write).status_code == 409
    info = descriptor(b"data")
    assert client.put("/objects/" + info.key, content=b"edit", headers=write).status_code == 400
    assert client.get("/objects/bad/stat", headers=headers("read")).status_code == 400
    assert client.get("/openapi.json").status_code == 404


@pytest.fixture
def certificates(tmp_path):
    now = datetime.now(timezone.utc)
    def make(name, issuer=None, server=False, expired=False):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        issuer_name, issuer_key = (issuer[0].subject, issuer[1]) if issuer else (subject, key)
        cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer_name).public_key(key.public_key())\
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=2))\
            .not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=2))\
            .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=0 if issuer is None else None), True)\
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)\
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), False)\
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
                data_encipherment=False, key_agreement=False, key_cert_sign=issuer is None, crl_sign=issuer is None,
                encipher_only=False, decipher_only=False), True)
        if issuer:
            cert = cert.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]), False)
        if server:
            cert = cert.add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
        cert = cert.sign(issuer_key, hashes.SHA256())
        certpath, keypath = tmp_path / (name + ".crt"), tmp_path / (name + ".key")
        certpath.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        keypath.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        keypath.chmod(0o600)
        return cert, key, str(certpath), str(keypath)
    ca = make("ca")
    return {"ca": ca, "server": make("server", ca, server=True), "client": make("client", ca),
            "expired": make("expired", ca, expired=True), "rogue": make("rogue")}


@contextmanager
def tls_server(root, tmp_path, certs, credentials):
    tokens, principals = credentials
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    principal_file = tmp_path / "principals.json"
    principal_file.write_text(json.dumps(principals))
    principal_file.chmod(0o600)
    env = dict(os.environ, ARTIFACT_ROOT=str(root), ARTIFACT_PRINCIPALS_FILE=str(principal_file),
        ARTIFACT_CA_FILE=certs["ca"][2], ARTIFACT_CERT_FILE=certs["server"][2], ARTIFACT_KEY_FILE=certs["server"][3],
        ARTIFACT_BIND="127.0.0.1", ARTIFACT_PORT=str(port), ARTIFACT_MIN_FREE_BYTES=str(64 * 1024 * 1024),
        WW_TEST="1", WW_TEST_ID="artifact-mtls")
    proc = subprocess.Popen([sys.executable, "-m", "ops.artifact_server"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    origin = f"https://127.0.0.1:{port}"
    context = ssl.create_default_context(cafile=certs["ca"][2])
    context.load_cert_chain(certs["client"][2], certs["client"][3])
    try:
        for _ in range(60):
            if proc.poll() is not None:
                raise AssertionError(proc.stderr.read().decode())
            try:
                response = httpx.get(origin + "/health", verify=context, trust_env=False, timeout=0.3,
                    headers={"Authorization": "Bearer " + tokens["read"]})
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.05)
        else:
            raise AssertionError("Isolated mTLS service did not become ready")
        yield origin
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        proc.stderr.close()


def test_real_mtls_clients_server_restart_and_negative_credentials(store, tmp_path, certificates, credentials):
    obj, root = store
    certs, tokens = certificates, credentials[0]
    data = b"frozen report across replicas" * 1000
    info = descriptor(data)
    def adapter(origin, role="writer", token=None):
        return RemoteObjects(origin, token or tokens[role], ca_file=certs["ca"][2], cert_file=certs["client"][2], key_file=certs["client"][3])
    with tls_server(root, tmp_path, certs, credentials) as origin:
        one, two = adapter(origin), adapter(origin, "read")
        try:
            assert one.put(info, [data]) == info
            assert two.stat(info.key) == info
            with two.open(info.key, expected=info) as (stream, _):
                assert stream.read() == data
            with pytest.raises(StorageUnavailable):
                two.delete(info.key)
        finally:
            one.close()
            two.close()
        for identity in (None, "rogue", "expired"):
            context = ssl.create_default_context(cafile=certs["ca"][2])
            if identity:
                context.load_cert_chain(certs[identity][2], certs[identity][3])
            with pytest.raises(httpx.HTTPError):
                httpx.get(origin + "/health", verify=context, trust_env=False, timeout=2,
                          headers={"Authorization": "Bearer " + tokens["read"]})
        wrong = adapter(origin, token=secrets.token_urlsafe(32))
        try:
            with pytest.raises(StorageUnavailable):
                wrong.stat(info.key)
        finally:
            wrong.close()
    with tls_server(root, tmp_path, certs, credentials) as restarted:
        client = adapter(restarted, "read")
        try:
            with client.open(info.key, expected=info) as (stream, _):
                assert stream.read() == data
        finally:
            client.close()


@pytest.mark.parametrize("failure", ["hash", "length", "redirect", "missing", "outage", "encoding"])
def test_remote_download_never_exposes_unverified_or_redirected_data(certificates, credentials, failure):
    data = b"report"
    info = descriptor(data)
    certs, tokens = certificates, credentials[0]
    calls = []
    def reply(request):
        calls.append(request)
        status = {"redirect": 302, "missing": 404, "outage": 503}.get(failure, 200)
        headers = {"Content-Length": str(info.size), "X-Content-SHA256": info.sha256,
                   "Location": "https://untrusted.example.test/steal"}
        if failure == "length":
            headers["Content-Length"] = str(info.size + 1)
        if failure == "encoding":
            headers["Content-Encoding"] = "custom"
        return httpx.Response(status, headers=headers, content=b"broken" if failure == "hash" else data)
    client = RemoteObjects("https://fixed.example.test", tokens["read"], ca_file=certs["ca"][2],
        cert_file=certs["client"][2], key_file=certs["client"][3], transport=httpx.MockTransport(reply))
    expected_error = ObjectMissing if failure == "missing" else StorageUnavailable if failure in {"redirect", "outage"} else ObjectCorrupt
    try:
        with pytest.raises(expected_error), client.open(info.key, expected=info):
            pytest.fail("Unverified content exposed to caller")
        assert len(calls) == 1
    finally:
        client.close()
