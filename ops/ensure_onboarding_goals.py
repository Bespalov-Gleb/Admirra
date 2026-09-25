"""Create only the two requested onboarding goals in AdMirra's marketing tag.

Uses its existing configured OAuth credential in memory; no ad-account tokens.
No changes to existing goals. Read-only by default; explicit --apply to create.
"""
import json
import logging
import sys
from urllib.request import Request, urlopen
from backend_api.services.metrika_conversions import _counter_id, _token

GOALS = {'signup_offer_click':'Онбординг — переход по предложению',
         'support_chat_click':'Онбординг — помощь в Telegram'}


def main():
    logging.disable(logging.CRITICAL)
    counter, token = _counter_id(), _token()
    assert counter == '109911357' and token, 'Marketing counter/credential unavailable'
    base = 'https://api-metrika.yandex.net/management/v1/counter/' + counter + '/goals'
    def call(payload=None):
        request = Request(base, data=json.dumps(payload).encode() if payload else None,
                          headers={'Authorization':'OAuth '+token, 'Content-Type':'application/json'})
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    goals = call()['goals']
    for event, title in GOALS.items():
        found = [g for g in goals if g.get('type') == 'action' and
                 any(c.get('url') == event for c in g.get('conditions', []))]
        if not found and '--apply' in sys.argv:
            call({'goal':{'name':title, 'type':'action', 'conditions':[{'type':'exact','url':event}]}})
            goals = call()['goals']  # verify provider state; never retry POST blindly
            found = [g for g in goals if g.get('type') == 'action' and
                     any(c.get('url') == event for c in g.get('conditions', []))]
            assert len(found) == 1, 'Unexpected provider state'
        print(json.dumps({'event':event,'goal_ids':[g['id'] for g in found], 'configured':bool(found)}))


if __name__ == '__main__': main()
