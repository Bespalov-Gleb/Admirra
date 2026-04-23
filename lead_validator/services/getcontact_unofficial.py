"""
Неофициальное API GetContact для получения имени по номеру телефона.

Основано на:
- https://github.com/SijyKijy/GetContactAPI (C#)
- https://github.com/kovinevmv/getcontact (Python)
- https://serj.ws/content/531 (PHP)

Возвращает displayName для последующего поиска в VK (по ФИО).
Токен и AES-ключ извлекаются из конфига приложения GetContact.
Работает с номерами RU, KZ, BY, KG, UA.
"""

import base64
import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger("lead_validator.getcontact_unofficial")

# HMAC-ключ (из декомпилированного приложения, может меняться с версией)
_HMAC_KEY = b'2Wq7)qkX~cp7)H|n_tc&o+:G_USN3/-uIi~>M+c ;Oq]E{t9)RC_5|lhAA_Qq%_4'

SEARCH_URL = "https://pbssrv-centralevents.com/v2.5/search"


def _encrypt_aes_ecb(key_bytes: bytes, plaintext: str) -> bytes:
    """Шифрование AES-256-ECB с PKCS7."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    block_size = 16
    raw = plaintext.encode("utf-8")
    padding = block_size - (len(raw) % block_size)
    padded = raw + bytes([padding] * padding)
    cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def _decrypt_aes_ecb(key_bytes: bytes, ciphertext: bytes) -> str:
    """Дешифрование AES-256-ECB."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(ciphertext) + decryptor.finalize()
    padding = decrypted[-1]
    if 1 <= padding <= 16:
        decrypted = decrypted[:-padding]
    return decrypted.decode("utf-8", errors="replace")


class GetContactUnofficial:
    """Клиент неофициального GetContact API."""

    def __init__(self, token: str, aes_key_hex: str):
        self.token = token.strip()
        try:
            self.aes_key = bytes.fromhex(aes_key_hex.replace(" ", "").strip())
        except ValueError:
            self.aes_key = b""
            logger.warning("Invalid GetContact AES key (expected hex)")

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.aes_key and len(self.aes_key) in (16, 24, 32))

    async def get_name_by_phone(self, phone: str, country_code: str = "RU") -> Optional[str]:
        """
        Получить displayName по номеру телефона.
        
        Returns:
            displayName или None при ошибке/не найден
        """
        if not self.enabled:
            return None

        import time
        timestamp = int(time.time())
        req_body = json.dumps({
            "countryCode": country_code,
            "source": "search",
            "token": self.token,
            "phoneNumber": phone.strip()
        })
        signature_input = f"{timestamp}-{req_body}"
        signature = base64.b64encode(
            hmac.new(_HMAC_KEY, signature_input.encode("utf-8"), hashlib.sha256).digest()
        ).decode("ascii")
        crypt_data = base64.b64encode(_encrypt_aes_ecb(self.aes_key, req_body)).decode("ascii")
        payload = json.dumps({"data": crypt_data})

        headers = {
            "X-App-Version": "4.9.7",
            "X-Token": self.token,
            "X-Os": "android 10",
            "X-Client-Device-Id": "14130e29cebe9c39",
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Encoding": "deflate",
            "X-Req-Timestamp": str(timestamp),
            "X-Req-Signature": signature,
            "X-Encrypted": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(SEARCH_URL, content=payload, headers=headers)
                if resp.status_code != 200:
                    logger.debug(f"GetContact unofficial: HTTP {resp.status_code}")
                    return None
                data = resp.json()
                enc_response = data.get("data")
                if not enc_response:
                    return None
                decrypted = _decrypt_aes_ecb(self.aes_key, base64.b64decode(enc_response))
                parsed = json.loads(decrypted)
                profile = None
                if isinstance(parsed, dict):
                    data = parsed.get("data")
                    if isinstance(data, dict):
                        profile = data.get("profile") or data
                    else:
                        profile = parsed.get("profile")
                display_name = None
                if isinstance(profile, dict):
                    display_name = profile.get("displayName") or profile.get("name")
                if display_name and str(display_name).strip().lower() not in ("not found", "null", ""):
                    return str(display_name).strip()
                return None
        except Exception as e:
            logger.debug(f"GetContact unofficial error: {e}")
            return None
