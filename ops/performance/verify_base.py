"""Read-only build gate for the production-compatible summary overlay."""
import hashlib
from pathlib import Path

EXPECTED = {
    "backend_api/stats_service.py": "bd2341682389a6380337dfa1c8fd3b8e77c8b122bcfe887fdfc752ab0e576fb0",
    "backend_api/stats.py": "0f42b357a045c2eb779350a883ec02aab7e5fd93dea3ccfba320074a884c4a23",
    "backend_api/folders.py": "8c9a81590e0b46aef1347202e20432afebed9adedc18daf7af0f17ce243f62d4",
    "backend_api/clients.py": "c6eeb7d118087b5d70ca30ce6ca7d814fa85cfd00b5f1613f695a41dacef0efe",
    "core/schemas.py": "3a78c6160c4414f9c94738b154a4ea222ff9ff99215b680a4ede7014eef9bfaa",
    "ai/report_generator.py": "ffffecdfac215e2bcc2aacf77d0e1ac2c74b9cc2f89ce6fcb334f0ad249b61aa",
}

if __name__ == "__main__":
    for name, expected in EXPECTED.items():
        if hashlib.sha256((Path("/app") / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Refusing changed production source: {name}")
    if not Path("/app/ai/assistant/runs.py").is_file():
        raise SystemExit("The deployed AI accounting hotfix must remain present")
