"""Two synthetic calls through the shipped assistant adapter, no DB/UI changes.

Run inside backend via stdin. Config changes are local to this probe process.
The event hook caps output at 1024 tokens per request; no customer data/tools.
"""
import asyncio
import argparse
import json
import time
import httpx
from ai.assistant import llm
from ai.assistant.models_catalog import get_model


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-current', action='store_true')
    args = parser.parse_args()
    if args.use_current:
        assert llm.cfg.openrouter.provider == 'openrouter'
        assert llm.cfg.openrouter.base_url == 'http://10.78.0.3:8080/api/v1'
    else:
        llm.cfg.openrouter.provider = 'openrouter'
        llm.cfg.openrouter.base_url = 'http://10.78.0.3:8080/api/v1'
    original = httpx.AsyncClient

    async def cap(request):
        if request.url.path.endswith('/chat/completions'):
            body = json.loads(request.content)
            body['max_tokens'] = 1024
            # httpx public streaming API: replace the outbound byte stream.
            content = json.dumps(body).encode()
            request.stream = httpx.ByteStream(content)
            request.headers['Content-Length'] = str(len(content))

    class BoundedClient(original):
        def __init__(self, *args, **kwargs):
            kwargs['event_hooks'] = {'request': [cap]}
            super().__init__(*args, **kwargs)

    llm.httpx.AsyncClient = BoundedClient
    tool = {'type': 'function', 'function': {'name': 'gateway_test', 'description': 'Returns the required verification number. You must call it before answering.',
        'parameters': {'type': 'object', 'properties': {}}}}
    messages = [{'role': 'user', 'content': 'Call gateway_test with no arguments, then reply only with the verification number from its result. Do not guess the number.'}]

    async def one(tools):
        started = time.monotonic()
        final = None
        async for event in llm.stream_completion(model=get_model(None), effort='medium', messages=messages, tools=tools):
            if event['type'] == 'message':
                final = event
        if not final:
            raise RuntimeError('No final adapter event')
        msg = final['message']
        print(json.dumps({'finish': final.get('finish_reason'), 'chars': len(msg.get('content') or ''),
                          'tool_calls': len(msg.get('tool_calls') or []), 'usage': final.get('usage'),
                          'seconds': round(time.monotonic() - started, 3)}), flush=True)
        return msg

    async with asyncio.timeout(90):
        first = await one([tool])
        calls = first.get('tool_calls') or []
        if len(calls) != 1 or calls[0]['function']['name'] != 'gateway_test':
            raise RuntimeError('Unexpected tool contract')
        messages.extend([first, {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': '{"verification_number": 42}'}])
        second = await one([tool])
        if second.get('tool_calls') or '42' not in second.get('content', ''):
            raise RuntimeError('Adapter failed to use tool result')
    print('PASS: production adapter, medium reasoning, tool result to final answer')


if __name__ == '__main__':
    asyncio.run(main())
