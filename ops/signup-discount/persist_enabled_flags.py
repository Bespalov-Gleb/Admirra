"""Persist only feature flags for future compose runs; never print secrets."""
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile

from release import env, inspect, private_json

with open('/var/lock/admirra-summary-release.lock','w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    backend=inspect('backend')
    for row in (backend,inspect('automation')):
        values=env(row)
        assert values['SIGNUP_DISCOUNT_ENABLED']=='true' and not values['SIGNUP_DISCOUNT_PILOT_USER_IDS']
    directory=Path(backend['Config']['Labels']['com.docker.compose.project.config_files']).parent
    assert json.loads((directory/'metadata.json').read_text())['all_eligible'] is True
    path=Path('/root/Admirra/.env')
    original=path.read_bytes()
    text=original.decode()
    for key,value in (('SIGNUP_DISCOUNT_ENABLED','true'),('SIGNUP_DISCOUNT_PILOT_USER_IDS','')):
        pattern=r'(?m)^'+key+r'=[^\r\n]*'
        assert len(re.findall(pattern,text))<=1
        if re.search(pattern,text):
            text=re.sub(pattern,key+'='+value,text)
        else:
            text=text.rstrip('\r\n')+'\n'+key+'='+value+'\n'
    backup=directory/'env-before-flags'
    with os.fdopen(os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as handle:
        handle.write(original)
    fd,tmp=tempfile.mkstemp(prefix='.env.signup-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(text.encode()); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print('Only signup feature flags persisted; root-only backup retained')
