import json
from pathlib import Path

import pytest

from ops.prepare_worker_runtime import select, env_text, install
from ops.shared_files_host import server_files, client_files, firewall_rules


def test_artifact_enrollment_keeps_ca_private_and_roles_separate(tmp_path):
    from ops.enroll_artifact_storage import enroll, PRINCIPALS
    from cryptography import x509
    from cryptography.x509.oid import ExtendedKeyUsageOID
    enroll(tmp_path)
    assert (tmp_path / "artifact-pki/ca.key").stat().st_mode & 0o777 == 0o600
    server = x509.load_pem_x509_certificate((tmp_path / "artifact-server/server.crt").read_bytes())
    assert ExtendedKeyUsageOID.SERVER_AUTH in server.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    specs = json.loads((tmp_path / "artifact-server/principals.json").read_text())
    for name, role in PRINCIPALS.items():
        assert specs[name]["role"] == role
        assert not (tmp_path / ("artifact-" + name) / "ca.key").exists()
    with pytest.raises(ValueError, match="already exists"):
        enroll(tmp_path)


def test_worker_secret_allowlist_and_literal_values():
    values = select({"SECRET_KEY": "a", "ENCRYPTION_KEY": "b", "OPENAI_API_KEY": "abc$def#ghi",
        "DATABASE_URL": "superuser", "POSTGRES_PASSWORD": "forbidden", "INTERNAL_ADMIN_JWT_SECRET": "forbidden",
        "SMTP_DIAGNOSE_SECRET": "forbidden", "YANDEX_CLIENT_SECRET": "refresh"})
    assert set(values) == {"SECRET_KEY", "ENCRYPTION_KEY", "OPENAI_API_KEY", "YANDEX_CLIENT_SECRET"}
    assert "OPENAI_API_KEY=abc$def#ghi\n" in env_text(values)
    with pytest.raises(ValueError):
        env_text({"SECRET_KEY": "a\nBAD=true"})


def test_runtime_install_separates_scheduler_and_preserves_existing(tmp_path):
    db = "DATABASE_URL=postgresql://admirra_worker:" + "x" * 43 + "@10.77.0.1:5432/saas_project\n"
    (tmp_path / "db-worker.env").write_text(db)
    payload = {"env": {"SECRET_KEY": "test", "ENCRYPTION_KEY": "test", "OPENAI_API_KEY": "test"},
               "google": json.dumps({"type": "service_account", "private_key": "synthetic"})}
    install(payload, tmp_path)
    install(payload, tmp_path)
    assert (tmp_path / "scheduler.env").read_text() == db
    assert (tmp_path / "worker.env").stat().st_mode & 0o777 == 0o600
    assert "postgresql://admirra_worker:" in (tmp_path / "worker.env").read_text()
    payload["env"]["SECRET_KEY"] = "changed"
    with pytest.raises(RuntimeError, match="differs"):
        install(payload, tmp_path)


def test_storage_export_is_private_and_cannot_grant_root():
    files = server_files()
    exports = files["/etc/exports.d/admirra.exports"]
    assert "no_root_squash" not in exports and "*" not in exports
    assert exports.count("all_squash,anonuid=10001,anongid=10001") == 3
    assert exports.count("10.77.0.2(") == 3
    assert "host=10.77.0.1" in files["/etc/nfs.conf.d/admirra.conf"]
    assert "vers3=n" in files["/etc/nfs.conf.d/admirra.conf"]
    mount = client_files()["/etc/systemd/system/srv-admirra-shared.mount"]
    assert "hard," in mount and "soft," not in mount
    assert "nosuid,nodev,noexec" in mount


def test_file_firewall_is_additive_ipv4_ipv6_and_docker_safe():
    for ipv6 in (True, False):
        chains, hooks = firewall_rules(ipv6)
        assert len(hooks) == 5
        assert "admrfiles0" in str(hooks[-1]) and "NEW" in str(hooks[-1])
        assert chains["ADMR-FILES-IN"][-1] == ["-j", "DROP"]
        flat = str((chains, hooks))
        assert "eth0" in flat
        assert ("10.77.0.2/32" in flat) != ipv6
        assert "5432" not in flat and "6379" not in flat


def test_compose_scheduler_has_no_files_or_provider_env():
    text = (Path(__file__).parents[1] / "ops/compose.workers.yml").read_text()
    scheduler = text.split("  scheduler:\n")[1].split("\nvolumes:")[0]
    assert "worker.env" not in scheduler.replace("redis-worker.env", "")
    assert "scheduler.env" in scheduler and "volumes: []" in scheduler
    assert "format: raw" in scheduler
    assert 'device: ":/uploads"' in text and "volume: {nocopy: true}" in text
    assert "read_only: true" in text
