"""One-time private PKI enrollment. No service start; no credentials on stdout.

Run on API1 in the tested image with ONLY /etc/admirra bind-mounted. CA key
stays in artifact-pki, never in runtime mounts. Explicit rotation is separate.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from ops.private_redis import write_once

PRINCIPALS = {"api1": "writer", "api2": "writer", "worker": "writer", "maintenance": "maintenance"}


def enroll(root=Path("/etc/admirra")):
    state = root / "artifact-pki"
    state.mkdir(mode=0o700, exist_ok=True)
    if state.is_symlink() or state.stat().st_mode & 0o077:
        raise ValueError("PKI directory must be private")
    # Fail closed on partial/conflicting enrollment; never silently rotate keys.
    if any(state.iterdir()):
        raise ValueError("PKI already exists; inspect enrollment before rotating")
    now = datetime.now(timezone.utc)
    def issue(name, issuer=None, server=False):
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        parent, signer = (issuer[0].subject, issuer[1]) if issuer else (subject, key)
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(parent)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=365 if issuer else 1825))
                .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=0 if issuer is None else None), True)
                .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
                    data_encipherment=False, key_agreement=False, key_cert_sign=issuer is None, crl_sign=issuer is None,
                    encipher_only=False, decipher_only=False), True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(signer.public_key()), False))
        if issuer:
            cert = cert.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]), False)
        if server:
            cert = cert.add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("10.77.0.1"))]), False)
        return cert.sign(signer, hashes.SHA256()), key
    def pem(cert):
        return cert.public_bytes(serialization.Encoding.PEM).decode()
    def private(key):
        return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption()).decode()
    ca, ca_key = issue("admirra-artifacts-ca")
    write_once(state / "ca.key", private(ca_key), 0o600)
    write_once(state / "ca.crt", pem(ca), 0o600)
    server, server_key = issue("admirra-artifacts", (ca, ca_key), server=True)
    directory = root / "artifact-server"
    directory.mkdir(mode=0o750)
    write_once(directory / "server.key", private(server_key), 0o640)
    write_once(directory / "server.crt", pem(server), 0o640)
    write_once(directory / "client-ca.crt", pem(ca), 0o640)
    principals = {}
    for name, role in PRINCIPALS.items():
        cert, key = issue("admirra-artifacts-" + name, (ca, ca_key))
        client = root / ("artifact-" + name)
        client.mkdir(mode=0o750)
        token = secrets.token_urlsafe(48)
        for filename, content in (("client.crt", pem(cert)), ("client.key", private(key)),
                                  ("ca.crt", pem(ca)), ("token", token + "\n")):
            write_once(client / filename, content, 0o640)
        principals[name] = {"role": role, "sha256": hashlib.sha256(token.encode()).hexdigest()}
    write_once(directory / "principals.json", json.dumps(principals), 0o640)
    for name in ("server", *PRINCIPALS):
        folder = root / ("artifact-" + name)
        if os.geteuid() == 0:
            os.chown(folder, 0, 10001)
            for file in folder.iterdir():
                os.chown(file, 0, 10001)
    write_once(state / "enrolled.json", json.dumps({"created_at": now.isoformat(), "renew_before": (now + timedelta(days=300)).isoformat(), "principals": list(PRINCIPALS)}), 0o600)


if __name__ == "__main__":
    if os.geteuid() != 0:
        raise SystemExit("Root required")
    enroll()
    print("Private artifact PKI enrolled; runtime mounts exclude CA key")
