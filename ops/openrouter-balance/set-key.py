"""Run interactively via ssh -t on API-1. Never pass a key as an argument."""
import getpass
import os
from pathlib import Path
import sys
import subprocess

from monitor import balance, fetch_credits


def main():
    if os.geteuid() != 0 or not sys.stdin.isatty():
        raise SystemExit('Run as root in an interactive terminal (ssh -t).')
    key = getpass.getpass('OpenRouter Management key (hidden): ').strip()
    try:
        balance(fetch_credits(key))
    except Exception:
        raise SystemExit('Key validation failed; existing key was NOT changed. Check Management key permissions/API access.')
    target = Path('/etc/admirra/openrouter-balance/management-key')
    temp = target.with_suffix('.new')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(key + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)
    subprocess.run(['systemctl', 'start', 'admirra-openrouter-balance.service'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'admirra-openrouter-balance.timer'], check=True)
    print('Key validated and stored privately; monitor started. Check Notifications group.')


if __name__ == '__main__':
    main()
