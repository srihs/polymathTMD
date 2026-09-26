"""System checks for the Zoom settings (brief 005, criteria 48 and 63; brief 006, criteria 1, 4-6).

Registered explicitly in ``ZoomConfig.ready()``. Which check runs when:

- **Untagged** (``manage.py check`` and ``migrate``): ``zoom.E002`` (the provider name),
  ``zoom.E003`` (the host-key encryption keys) and ``zoom.E005`` (the Zoom credential sets,
  when ``ZOOM_PROVIDER=zoom``). They read settings only. ``collectstatic``, which runs at image
  build time with no keys, only runs the ``staticfiles`` checks, so it isn't blocked.
- **Deploy** (``check --deploy``): ``zoom.E001`` (the fake provider) and ``zoom.W001`` (the
  manual provider can't see meetings made directly in Zoom).
- **Database** (``check --database default``): ``zoom.E004``, every active paid account has a
  working connection name. It needs the database, and one unconnected account mustn't stop
  the site from starting (the public form would go down with it), so it isn't untagged (D11).

No message ever echoes a key or a credential value; E005 names variables, never values.
"""

import re
from collections import defaultdict

from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning
from django.db import DatabaseError

# A pure function, imported rather than read through ``settings``: E005's name-collision test
# must use the exact rule ``base.py`` used to turn each connection name into variable names,
# and settings only carry the values, not the rule. Every settings module (dev, test, prod)
# star-imports ``base`` first, so it's already loaded: this adds no second read of the
# environment, and env is still read only in ``base.py``.
from config.settings.base import zoom_credential_env_prefix

from . import crypto
from .models import HostAccount
from .providers import PROVIDERS
from .validators import CREDENTIAL_SET_ERROR, CREDENTIAL_SET_PATTERN


def check_provider_setting(app_configs=None, **kwargs):
    value = getattr(settings, "ZOOM_PROVIDER", None)
    if value in PROVIDERS:
        return []
    return [
        Error(
            f"ZOOM_PROVIDER is {value!r}; it must be one of: {', '.join(PROVIDERS)}.",
            hint="Set ZOOM_PROVIDER=zoom in production (manual is the fallback), or fake for "
            "local development.",
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
            "Set ZOOM_PROVIDER=zoom in production.",
            id="zoom.E001",
        )
    ]


def check_manual_provider_not_deployed(app_configs=None, **kwargs):
    """``zoom.W001``: ``manual`` is only a fallback, because it can't see Zoom (criterion 5)."""
    if getattr(settings, "ZOOM_PROVIDER", None) != "manual":
        return []
    return [
        CheckWarning(
            "ZOOM_PROVIDER=manual can't see meetings made directly in Zoom, so it can "
            "double-book them. Set ZOOM_PROVIDER=zoom before taking real requests.",
            id="zoom.W001",
        )
    ]


def check_credential_sets(app_configs=None, **kwargs):
    """``zoom.E005``: with ``zoom`` chosen, every listed credential set is usable (criterion 4).

    It reads what ``base.py`` parsed (``ZOOM_CREDENTIAL_SETS`` and the variable *names* in
    ``ZOOM_CREDENTIAL_MISSING``), so env is still read only in ``base.py``.
    """
    if getattr(settings, "ZOOM_PROVIDER", None) != "zoom":
        return []
    slugs = list(getattr(settings, "ZOOM_CREDENTIAL_SETS", []))
    if not slugs:
        return [
            Error(
                "ZOOM_PROVIDER is zoom, but ZOOM_CREDENTIAL_SETS is empty.",
                hint="List the Zoom connection names, like zoom-01,zoom-02, in "
                "zoom-credentials.env, with their three variables each.",
                id="zoom.E005",
            )
        ]
    errors = []
    missing = getattr(settings, "ZOOM_CREDENTIAL_MISSING", {})
    names = defaultdict(list)
    for slug in slugs:
        if not re.search(CREDENTIAL_SET_PATTERN, slug):
            errors.append(
                Error(
                    f"The Zoom connection name {slug!r} in ZOOM_CREDENTIAL_SETS isn't valid.",
                    hint=CREDENTIAL_SET_ERROR,
                    id="zoom.E005",
                )
            )
            continue
        names[zoom_credential_env_prefix(slug)].append(slug)
        if missing.get(slug):
            errors.append(
                Error(
                    f"The Zoom connection {slug} is missing {', '.join(missing[slug])}.",
                    hint="Set every one of them in zoom-credentials.env, then recreate web.",
                    id="zoom.E005",
                )
            )
    for prefix, clashing in names.items():
        if len(clashing) > 1:
            errors.append(
                Error(
                    f"The Zoom connections {', '.join(clashing)} all use the variables {prefix}_*.",
                    hint="List each connection once in ZOOM_CREDENTIAL_SETS.",
                    id="zoom.E005",
                )
            )
    return errors


def check_accounts_connected(app_configs=None, databases=None, **kwargs):
    """``zoom.E004``: every active paid account has a working connection name (criterion 6).

    Runs only with ``check --database default`` and ``ZOOM_PROVIDER=zoom``. Before
    ``migrate`` has made the table it reports nothing rather than crashing.
    """
    if getattr(settings, "ZOOM_PROVIDER", None) != "zoom" or "default" not in (databases or ()):
        return []
    try:
        accounts = list(HostAccount.objects.bookable())  # Meta.ordering: order, then name
    except DatabaseError:
        return []
    errors = []
    for account in accounts:
        state = account.zoom_connection_state
        if state == "ready":
            continue
        if state == "none":
            reason = "no Zoom connection name is set"
        else:
            reason = f"the server has no connection details called {account.credential_set}"
        errors.append(
            Error(
                f"{account.label} has no working Zoom connection: {reason}.",
                hint="Set it on the Zoom accounts page, or add the connection to "
                "zoom-credentials.env.",
                id="zoom.E004",
            )
        )
    return errors
