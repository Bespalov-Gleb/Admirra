"""Untrusted marketing metadata; never used as identity or authorization."""
import json
import time
import unicodedata
from urllib.parse import unquote

FIELDS = ('source', 'medium', 'campaign')


def clean(value):
    if not isinstance(value, str):
        return None
    return ''.join(' ' if unicodedata.category(c)[0] == 'C' else c for c in value).strip()[:256] or None


def registration_attribution(request=None, explicit=None):
    # API callers may still supply the existing email registration fields.
    if explicit:
        values = {f'registration_utm_{f}': clean(explicit.get(f'registration_utm_{f}')) for f in FIELDS}
        if any(values.values()):
            return values
    try:
        raw = request.cookies.get('admirra_signup_utm', '') if request else ''
        if not raw or len(raw) > 12000:
            return {}
        data = json.loads(unquote(raw))
        expiry = data.get('expires')
        now = time.time() * 1000
        if isinstance(expiry, bool) or not isinstance(expiry, (float, int)) or not now < expiry <= now + 31 * 86400000:
            return {}
        return {f'registration_utm_{f}': clean(data.get(f'utm_{f}')) for f in FIELDS}
    except (ValueError, TypeError, AttributeError):
        return {}
