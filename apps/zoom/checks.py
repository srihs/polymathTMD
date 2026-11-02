"""System checks for the Zoom settings (brief 005, criteria 48 and 63; brief 006, criteria 1, 4-6;
brief 011, criterion 47; brief 015, criteria 30-33).

Registered explicitly in ``ZoomConfig.ready()``. Which check runs when:

- **Untagged** (``manage.py check`` and ``migrate``): ``zoom.E002`` (the provider name),
  ``zoom.E003`` (the encryption keys, which protect host keys and, from brief 015, Zoom
  connection secrets) and ``zoom.E006`` (``IT_DESK_PHONE`` is a number the app can read). They
  read settings only, none of them a credential. ``collectstatic``, which runs at image build
  time with no keys, only runs the ``staticfiles`` checks, so it isn't blocked.
- **Retired:** ``zoom.E005`` checked the env credential variables. Brief 015 moved credentials
  into the database, where required fields, constraints, the name rule and a unique name make
  each of its failures impossible (D10). Its id isn't reused.
- **Deploy** (``check --deploy``): ``zoom.E001`` (the fake provider) and ``zoom.W001`` (the
  manual provider can't see meetings made directly in Zoom).
- **Database** (``check --database default``): ``zoom.E004``, every active paid account has a
  working Zoom connection. It needs the database, and one unconnected account mustn't stop
  the site from starting (the public form would go down with it), so it isn't untagged (D11).
  ``zoom.W002`` (brief 013, criterion 2), every such connected account's connection has a
  readable webhook secret, for the same reasons; a warning, because bookings still work
  without it. Each is one query (``bookable()`` joins the connection), whatever the number of
  accounts, and silent before ``migrate`` has made the tables.

No message ever echoes a key, an ID or a secret: they name accounts and connections only.
"""

from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning
from django.core.exceptions import ValidationError
from django.db import DatabaseError

from . import crypto
from .models import HostAccount
from .providers import PROVIDERS
from .validators import normalise_phone

IT_DESK_PHONE_ERROR = (
    "IT_DESK_PHONE isn't a phone number the app can read. Use a form like 011 234 5678 or "
    "+94 11 234 5678."
)


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


def check_it_desk_phone(app_configs=None, **kwargs):
    """``zoom.E006``: a set ``IT_DESK_PHONE`` must be readable (brief 011, criterion 47).

    It's read by the same ``normalise_phone`` the start page uses, so a typo is caught by
    ``manage.py check`` rather than by a teacher tapping a dead number. Empty is allowed: the
    page then says "contact the IT desk" with no number. The message never repeats the value.
    """
    value = (getattr(settings, "IT_DESK_PHONE", "") or "").strip()
    if not value:
        return []
    try:
        normalise_phone(value)
    except ValidationError:
        return [Error(IT_DESK_PHONE_ERROR, id="zoom.E006")]
    return []


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


def check_accounts_connected(app_configs=None, databases=None, **kwargs):
    """``zoom.E004``: every active paid account has a working Zoom connection (c. 6, 015 c. 32).

    Runs only with ``check --database default`` and ``ZOOM_PROVIDER=zoom``. One query: the
    connection is joined. Before ``migrate`` has made the tables it reports nothing rather
    than crashing.
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
            reason = "no Zoom connection is chosen"
        else:
            reason = (
                f"the details of {account.zoom_connection.slug} can't be read with the current "
                "encryption keys"
            )
        errors.append(
            Error(
                f"{account.label} has no working Zoom connection: {reason}.",
                hint="Choose the connection on the Zoom accounts page, or type its client secret "
                "again on the Zoom connections page.",
                id="zoom.E004",
            )
        )
    return errors


WEBHOOK_SECRET_MISSING = (
    "{label}'s Zoom connection has no webhook secret, so changes made directly in Zoom to its "
    "meetings aren't seen here."
)
WEBHOOK_SECRET_UNREADABLE = (
    "{label}'s Zoom connection has a webhook secret that can't be read with the current "
    "encryption keys, so changes made directly in Zoom to its meetings aren't seen here."
)
WEBHOOK_SECRET_HINT = (
    "Add the webhook secret on the Zoom connection's page. The README says where Zoom shows it."
)


def check_webhook_secrets(app_configs=None, databases=None, **kwargs):
    """``zoom.W002``: each connected active paid account's connection has a readable webhook
    secret (brief 013, criterion 2; brief 015, criterion 33).

    Without one, Zoom can't tell this system about a class changed or deleted directly in
    Zoom, so it stays as it was here until its booking is checked. Only with
    ``ZOOM_PROVIDER=zoom`` and ``check --database default``; silent before ``migrate``. An
    account whose connection isn't working at all is ``zoom.E004``'s, so it isn't repeated
    here. One query; the message names the account, never a value.
    """
    if getattr(settings, "ZOOM_PROVIDER", None) != "zoom" or "default" not in (databases or ()):
        return []
    try:
        accounts = list(HostAccount.objects.bookable())  # Meta.ordering: order, then name
    except DatabaseError:
        return []
    messages = {"none": WEBHOOK_SECRET_MISSING, "unreadable": WEBHOOK_SECRET_UNREADABLE}
    warnings = []
    for account in accounts:
        if not account.is_zoom_connected():
            continue
        message = messages.get(account.zoom_connection.webhook_secret_state)
        if message:
            warnings.append(
                CheckWarning(
                    message.format(label=account.label), hint=WEBHOOK_SECRET_HINT, id="zoom.W002"
                )
            )
    return warnings
