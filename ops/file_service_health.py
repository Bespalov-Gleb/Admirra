"""Read-only bounded file-service health. Never log tokens, paths or responses."""
import argparse
import json
import os
from pathlib import Path
import ssl
import subprocess
import time
import urllib.request


def check(node):
    root = Path("/etc/admirra")
    client = root / ("artifact-api1" if node == "1" else "artifact-api2")
    ok = False
    try:
        context = ssl.create_default_context(cafile=str(client / "ca.crt"))
        context.load_cert_chain(str(client / "client.crt"), str(client / "client.key"))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
        req = urllib.request.Request("https://10.77.0.1:9443/health", headers={"Authorization": "Bearer " + (client / "token").read_text().strip()})
        with opener.open(req, timeout=4) as response:
            ok = response.status == 200 and json.loads(response.read(512)) == {"status": "ok"}
    except Exception:
        pass
    expires = []
    for path in root.glob("artifact-*/*.crt"):
        try:
            expires.append(ssl.cert_time_to_seconds(ssl._ssl._test_decode_cert(str(path))["notAfter"]))
        except Exception:
            expires.append(0)
    units = (["nfs-server.service", "srv-admirra-shared-uploads.mount", "srv-admirra-shared-rejected\\x2dleads.mount"]
             if node == "1" else ["srv-admirra-shared.mount"])
    mounted = all(subprocess.run(["systemctl", "is-active", "--quiet", unit], timeout=3).returncode == 0 for unit in units)
    return {"up": int(ok and mounted), "last_check_timestamp_seconds": int(time.time()),
            "certificate_not_after_timestamp_seconds": int(min(expires, default=0))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", choices=("1", "2"), required=True)
    args = parser.parse_args()
    values = check(args.node)
    target = Path("/var/lib/admirra-api2-monitor/shared-files.prom")
    temporary = target.with_suffix(".next")
    temporary.write_text("".join(f'admirra_shared_files_{name}{{node="{args.node}"}} {value}\n' for name, value in values.items()))
    temporary.chmod(0o644)
    os.replace(temporary, target)
    print(json.dumps(values))


if __name__ == "__main__":
    main()
