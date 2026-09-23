"""Use only the explicitly bound project's CAPTCHA credentials."""
import httpx
import math
from fastapi import HTTPException
from lead_validator.config import settings


async def validate(project, token, client_ip):
    provider = project.captcha_provider or 'none'
    if provider == 'none':
        return True, ''  # Intake route is authenticated by the project webhook secret.
    urls = {'turnstile': 'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            'recaptcha': 'https://www.google.com/recaptcha/api/siteverify',
            'smartcaptcha': 'https://smartcaptcha.cloud.yandex.ru/validate'}
    if provider not in urls or not project.captcha_secret_key:
        raise HTTPException(503, 'CAPTCHA проекта не настроена')
    if not token:
        return False, 'token_required'
    params = {'secret': project.captcha_secret_key,
              'token' if provider == 'smartcaptcha' else 'response': token}
    if client_ip:
        params['ip' if provider == 'smartcaptcha' else 'remoteip'] = client_ip
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.post(urls[provider], data=params)
            if response.status_code != 200:
                raise ValueError('Provider unavailable')
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError('Malformed CAPTCHA response')
            if provider == 'smartcaptcha':
                if data.get('status') not in ('ok', 'failed'):
                    raise ValueError('Unknown CAPTCHA status')
            elif type(data.get('success')) is not bool:
                raise ValueError('Missing CAPTCHA decision')
            if set(data.get('error-codes') or []) & {'missing-input-secret', 'invalid-input-secret', 'bad-request', 'internal-error'}:
                raise ValueError('CAPTCHA configuration or provider failure')
            valid = data.get('status') == 'ok' if provider == 'smartcaptcha' else data.get('success') is True
            if valid and provider == 'recaptcha' and 'score' in data:
                if type(data['score']) not in (float, int) or not math.isfinite(data['score']):
                    raise ValueError('Malformed CAPTCHA score')
                valid = float(data['score']) >= settings.RECAPTCHA_MIN_SCORE
            return valid, '' if valid else 'invalid_token'
    except Exception:
        # Unknown verification outcome is not a negative decision about the lead.
        raise HTTPException(503, 'Проверка CAPTCHA временно недоступна') from None
