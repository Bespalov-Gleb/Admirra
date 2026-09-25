"""Read-only authenticated status checks; never claim offers or create payments.

Run inside the API process environment. Token stays in memory; print only
contract checks and timings, not account data or credentials.
"""
from datetime import timedelta
import json
import logging
import sys
import time
from urllib.request import Request, urlopen
from sqlalchemy import text
from core import models, security
from core.database import SessionLocal


def main():
    logging.disable(logging.CRITICAL)
    with SessionLocal() as db:
        db.execute(text('SET TRANSACTION READ ONLY'))
        user = db.query(models.User).filter(models.User.email == 'burlakov.timof@yandex.ru', models.User.is_active.is_(True)).one()
        token = security.create_access_token({'sub': user.email}, expires_delta=timedelta(minutes=3))
        uid = user.id
        projects = db.query(models.Client).filter(models.Client.owner_id == uid).count()
    allowed = ('http://127.0.0.1:8001', 'http://10.77.0.2:8001', 'https://admirra.ru')
    bases = sys.argv[1:] or allowed
    assert set(bases) <= set(allowed)
    for base in bases:
        samples = []
        for _ in range(3):
            started = time.monotonic()
            request = Request(base + '/api/billing/signup-discount', headers={'Authorization':'Bearer ' + token})
            with urlopen(request, timeout=15) as response:
                data = json.load(response)
                assert response.status == 200
            assert data['projects_count'] == projects
            assert isinstance(data['cabinets_count'], int)
            assert data['discount_state'] in ('not_granted', 'granted', 'used', 'expired')
            assert isinstance(data['trial_visible'], bool)
            assert data['trial_days_left'] >= 0
            assert not {'access_token', 'email', 'phone'} & set(data)
            samples.append(round((time.monotonic() - started) * 1000, 1))
        print(json.dumps({'base':base, 'status':200, 'contract_verified':True, 'milliseconds':samples}))


if __name__ == '__main__': main()
