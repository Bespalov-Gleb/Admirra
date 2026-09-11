"""The only supported file-service entrypoint: mutual TLS is mandatory."""
import os
from pathlib import Path
import ssl


def config():
    import uvicorn
    from backend_api.artifact_store import from_environment
    files = {key: os.environ[key] for key in ("ARTIFACT_CERT_FILE", "ARTIFACT_KEY_FILE", "ARTIFACT_CA_FILE")}
    if not all(Path(value).is_file() for value in files.values()):
        raise ValueError("Artifact TLS material is missing")
    result = uvicorn.Config(from_environment(), host=os.getenv("ARTIFACT_BIND", "0.0.0.0"),
        port=int(os.getenv("ARTIFACT_PORT", "9443")), workers=1, access_log=False,
        ssl_certfile=files["ARTIFACT_CERT_FILE"], ssl_keyfile=files["ARTIFACT_KEY_FILE"],
        ssl_ca_certs=files["ARTIFACT_CA_FILE"], ssl_cert_reqs=ssl.CERT_REQUIRED,
        limit_concurrency=12, timeout_keep_alive=5, timeout_graceful_shutdown=70)
    result.load()
    result.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    return result


def main():
    import uvicorn
    uvicorn.Server(config()).run()


if __name__ == "__main__":
    main()
