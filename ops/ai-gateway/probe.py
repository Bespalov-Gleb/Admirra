"""Run inside the existing backend container; never prints/persists API keys.

Default: authenticated read-only check. --paid-smoke: at most two synthetic
generations, each max_tokens=1024. No customer/project data is accessed.
"""
import argparse
import json
import time
import httpx
from core.config import get_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--model', default='google/gemini-3.7-flash')
    parser.add_argument('--paid-smoke', action='store_true')
    a = parser.parse_args()
    key = get_config().openrouter.api_key
    if not key:
        raise SystemExit('OpenRouter key is absent; no changes made')
    with httpx.Client(base_url=a.base.rstrip('/') + '/', timeout=120,
                      headers={'Authorization': 'Bearer ' + key}) as client:
        r = client.get('key')
        print(json.dumps({'key_http': r.status_code}), flush=True)
        r.raise_for_status()
        data = r.json().get('data', {})
        print(json.dumps({'key_valid': True, 'limit_remaining': data.get('limit_remaining'),
                          'is_free_tier': data.get('is_free_tier')}), flush=True)
        r = client.get('models')
        r.raise_for_status()
        models = {m['id']: m for m in r.json()['data']}
        print(json.dumps({'model': a.model, 'in_catalog': a.model in models}), flush=True)
        if a.model not in models:
            raise SystemExit('Requested model missing; production remains unchanged')
        if not a.paid_smoke:
            return

        def generate(messages, tools=None):
            body = {'model': a.model, 'messages': messages, 'stream': True,
                    'max_tokens': 1024, 'reasoning': {'effort': 'low'},
                    'stream_options': {'include_usage': True}}
            if tools:
                body.update(tools=tools, tool_choice={'type': 'function', 'function': {'name': 'gateway_test'}})
            start = time.monotonic()
            text, calls, reasoning_details, usage, done, finish, first = '', {}, [], {}, False, None, None
            with client.stream('POST', 'chat/completions', json=body) as response:
                print(json.dumps({'generation_http': response.status_code}), flush=True)
                if response.status_code != 200:
                    try:
                        error = json.loads(response.read()).get('error', {})
                        print(json.dumps({'error_code': error.get('code'),
                                          'error_message': str(error.get('message', ''))[:250]}), flush=True)
                    except (ValueError, TypeError):
                        pass
                    raise SystemExit('Generation failed; production remains unchanged')
                for line in response.iter_lines():
                    if not line.startswith('data:'):
                        continue
                    raw = line[5:].strip()
                    if raw == '[DONE]':
                        done = True
                        break
                    chunk = json.loads(raw)
                    if chunk.get('error'):
                        raise SystemExit('Upstream SSE error; production remains unchanged')
                    if chunk.get('usage'):
                        usage = chunk['usage']
                    for choice in chunk.get('choices', []):
                        delta = choice.get('delta', {})
                        if first is None and (delta.get('content') or delta.get('tool_calls')):
                            first = round(time.monotonic() - start, 3)
                        text += delta.get('content') or ''
                        reasoning_details.extend(delta.get('reasoning_details') or [])
                        finish = choice.get('finish_reason') or finish
                        for d in delta.get('tool_calls', []):
                            call = calls.setdefault(d.get('index', 0), {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                            if d.get('id'):
                                call['id'] = d['id']
                            for field in ('name', 'arguments'):
                                call['function'][field] += d.get('function', {}).get(field) or ''
            print(json.dumps({'done': done, 'finish': finish, 'first_content_seconds': first,
                              'seconds': round(time.monotonic() - start, 3), 'text_chars': len(text),
                              'tool_calls': len(calls), 'usage': usage}), flush=True)
            if not done or finish not in ('stop', 'tool_calls'):
                raise SystemExit('Incomplete stream; production remains unchanged')
            message = {'role': 'assistant', 'content': text}
            if calls:
                message['tool_calls'] = list(calls.values())
            if reasoning_details:
                message['reasoning_details'] = reasoning_details
            return message

        messages = [{'role': 'user', 'content': 'Call gateway_test to obtain a verification number. Then return only the number provided by the tool.'}]
        tool = {'type': 'function', 'function': {'name': 'gateway_test', 'description': 'Returns a synthetic verification number.',
                                                'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}
        first = generate(messages, [tool])
        calls = first.get('tool_calls', [])
        if len(calls) != 1 or calls[0]['function']['name'] != 'gateway_test':
            raise SystemExit('Tool call contract failed')
        messages.extend([first, {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': '{"verification_number": 42}'}])
        second = generate(messages)
        if second.get('tool_calls') or '42' not in second['content']:
            raise SystemExit('Final tool result interpretation failed')
        print('PASS: authenticated API, SSE, two-turn tool response, usage')


if __name__ == '__main__':
    main()
