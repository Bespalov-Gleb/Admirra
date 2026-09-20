#!/usr/bin/env python3
"""Send a clearly labelled synthetic critical/recovery pair without changing live state."""
import datetime as dt
import json
import tempfile
from pathlib import Path

from external_heartbeat import notify_status


def main():
    config = json.loads(Path("/etc/admirra/monitoring/heartbeat-telegram.json").read_text())
    with tempfile.TemporaryDirectory(prefix="admirra-heartbeat-smoke-") as folder:
        for status in ("critical", "ok"):
            result = {"status": status, "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()}
            print(json.dumps(notify_status(result, config, Path(folder) / "state.json", test=True)))


if __name__ == "__main__":
    main()
