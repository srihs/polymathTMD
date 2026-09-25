"""System checks for the Zoom settings (brief 005, criteria 48 and 63).

Registered explicitly in ``ZoomConfig.ready()``. ``zoom.E002`` and ``zoom.E003`` are untagged,
so ``manage.py check`` and ``migrate`` report them, while ``collectstatic`` (which runs at image
build time with no encryption keys and only runs the ``staticfiles`` checks) is not blocked.
``zoom.E004`` (credential sets for the live provider) arrives with brief 006.

No message ever echoes a key.
"""

from django.conf import settings
from django.core.checks import Error

from . import crypto
from .providers import PROVIDERS


def check_provider_setting(app_configs=None, **kwargs):
    value = getattr(settings, "ZOOM_PROVIDER", None)
    if value in PROVIDERS:
        return []
    return [
        Error(
            f"ZOOM_PROVIDER is {value!r}; it must be one of: {', '.join(PROVIDERS)}.",
            hint="Set ZOOM_PROVIDER=manual in production, or fake for local development.",
            id="zoom.E002",
        )
    ]


def check_host_key_encryption_keys(app_configs=None, **kwargs):
    if crypto.keys_are_valid(getattr(settings, "HOST_KEY_ENCRYPTION_KEYS", None)):
        return []
    return [
        Error(
            crypto.KEYS_ERROR,
            hint='Generate one with python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())" and put it in .env.',
            id="zoom.E003",
        )
    ]


def check_fake_provider_not_deployed(app_configs=None, **kwargs):
    if getattr(settings, "ZOOM_PROVIDER", None) != "fake":
        return []
    return [
        Error(
            "The fake Zoom provider makes links that don't work. "
            "Set ZOOM_PROVIDER=manual in production.",
            id="zoom.E001",
        )
    ]
