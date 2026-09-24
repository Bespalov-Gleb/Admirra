"""Prepare on API-1 without starting a timer or replacing existing secrets.

Deployment only installs this standalone monitor. No app/container restarts.
Gateway GET /credits route must have been reviewed and enabled separately.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root on API-1.')
    source = Path(__file__).resolve().parent
    config_dir = Path('/etc/admirra/openrouter-balance')
    app_dir = Path('/opt/admirra-openrouter-balance')
    if config_dir.exists() or app_dir.exists():
        raise SystemExit('Existing installation preserved. Review before upgrading.')
    config = json.loads(Path('/etc/admirra/registration-notifier/config.json').read_text())
    if type(config['chat_id']) is not int or config['chat_id'] >= 0:
        raise SystemExit('Expected existing Notifications group.')
    if config['api_base'] != 'http://10.78.0.3:8080/telegram':
        raise SystemExit('Unexpected Telegram gateway.')
    if not Path('/etc/admirra/registration-notifier/bot-token').is_file():
        raise SystemExit('Existing Notifications token missing.')
    config_dir.mkdir(mode=0o700)
    app_dir.mkdir(mode=0o755)
    with (config_dir / 'config.json').open('x') as out:
        os.fchmod(out.fileno(), 0o600)
        json.dump({'chat_id': config['chat_id'], 'warning_usd': 20, 'critical_usd': 5}, out)
    for name in ('monitor.py', 'set-key.py'):
        shutil.copyfile(source / name, app_dir / name)
        os.chmod(app_dir / name, 0o644)
    units = ('admirra-openrouter-balance.service', 'admirra-openrouter-balance.timer')
    for unit in units:
        target = Path('/etc/systemd/system') / unit
        if target.exists():
            raise SystemExit('Unit already exists; refusing overwrite.')
        shutil.copyfile(source / unit, target)
        os.chmod(target, 0o644)
    subprocess.run(['systemd-analyze', 'verify', *[str(Path('/etc/systemd/system') / unit) for unit in units]], check=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    print('Prepared; timer NOT enabled. Run set-key.py interactively to validate key and start.')


if __name__ == '__main__':
    main()
