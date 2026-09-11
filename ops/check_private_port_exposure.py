"""Run from outside the two servers: DB/Redis TCP ports must not be public."""
import json
import socket


def main():
    results = {}
    for host in ("91.221.68.90", "91.221.68.94"):
        for port in (5432, 6379, 6380):
            try:
                with socket.create_connection((host, port), timeout=2):
                    results[f"{host}:{port}"] = "OPEN"
            except (TimeoutError, ConnectionRefusedError, OSError):
                results[f"{host}:{port}"] = "not reachable from probe location"
    print(json.dumps(results))
    if "OPEN" in results.values():
        raise SystemExit(2)


if __name__ == "__main__":
    main()
