"""Encryption at rest for the secrets the database holds (brief 005, D17; brief 015, D3).

This is the only module that imports ``cryptography``. Two kinds of secret are stored, both
through here and under the same keys, so there is one key list, one rotation and one backup
rule: Zoom host keys (brief 005) and each Zoom connection's Client Secret and webhook Secret
Token (brief 015). The rules are kept small and in one place:

- The key list comes from ``settings.HOST_KEY_ENCRYPTION_KEYS`` (read from the environment in
  ``config/settings/base.py`` only). The first key encrypts; every key decrypts. That is what
  makes rotation possible (``manage.py rotate_encryption_keys``, which re-encrypts every
  stored secret in one go, so removing the old key can never strand one kind of secret).
- The ``MultiFernet`` is built on every call, not at import time. ``collectstatic`` runs at
  image build time without any keys, and tests swap the key list with ``override_settings``;
  a cached cipher would break both. Building it costs microseconds.
- Nothing here logs, and no error message ever includes a key or a plaintext value.
"""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.debug import sensitive_variables

KEYS_ERROR = "HOST_KEY_ENCRYPTION_KEYS is missing or not a list of valid Fernet keys."


class SecretUnreadable(Exception):
    """A stored secret can't be decrypted with any configured key.

    It wraps ``cryptography``'s ``InvalidToken`` so callers never import ``cryptography``. One
    name for every stored secret (a host key, a client secret or a webhook secret), so an
    ``except`` around any of them reads truthfully (brief 015, D13). The usual cause is a key
    removed from ``HOST_KEY_ENCRYPTION_KEYS`` before ``rotate_encryption_keys`` ran; the fix
    is to type the secret again on its page. Its arguments never carry a value or a key.
    """


@sensitive_variables("keys")
def _clean_keys(keys):
    return [str(key).strip() for key in keys or []]


@sensitive_variables("keys", "cleaned", "key")
def keys_are_valid(keys) -> bool:
    """True when ``keys`` is a non-empty list of valid Fernet keys (backs check zoom.E003)."""
    cleaned = _clean_keys(keys)
    if not cleaned:
        return False
    try:
        for key in cleaned:
            Fernet(key)
    except (ValueError, TypeError):
        return False
    return True


@sensitive_variables("keys")
def _cipher() -> MultiFernet:
    keys = settings.HOST_KEY_ENCRYPTION_KEYS
    if not keys_are_valid(keys):
        raise ImproperlyConfigured(KEYS_ERROR)
    return MultiFernet([Fernet(key) for key in _clean_keys(keys)])


@sensitive_variables("plain")
def encrypt(plain: str) -> str:
    """Encrypt with the first key. Fernet adds a random IV, so equal inputs differ."""
    return _cipher().encrypt(plain.encode()).decode()


@sensitive_variables("token")
def decrypt(token: str) -> str:
    """Decrypt with whichever configured key works, or raise ``SecretUnreadable``."""
    try:
        return _cipher().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretUnreadable("InvalidToken") from exc


@sensitive_variables("token")
def rotate(token: str) -> str:
    """Re-encrypt ``token`` with the first key (``MultiFernet.rotate``)."""
    try:
        return _cipher().rotate(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretUnreadable("InvalidToken") from exc
