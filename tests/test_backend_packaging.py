from ops.package_backend import allowed


def test_package_excludes_secrets_and_other_work():
    for path in [".env", "core/.env.prod", "core/secrets/key.json", "../.env",
                 "core/foo.pem", "core/google-service-account.json", ".git/config",
                 "uploads/avatar.png", "landing/index.html", "core/x_probe.py"]:
        assert not allowed(path), path


def test_runtime_sources_are_packaged():
    for path in ["Dockerfile", ".dockerignore", "requirements.lock", "core/runtime.py",
                 "backend_api/main.py", "certs/russian_trusted_root_ca.crt"]:
        assert allowed(path), path
