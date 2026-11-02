"""Checking that a call to the Zoom webhook came from that connection's own Zoom app (brief 013).

Pure functions over the request's headers, its raw bytes and the settings: no database and no
HTTP, so the view stays a mapping from results to status codes, and every rule is testable on
its own. ``hmac`` and ``hashlib`` from the standard library are all it needs (no Zoom SDK).

Why it's shaped like this (D2):

- **One address per connection** (``/zoom/webhooks/zoom-01/``). The name picks the secret to
  check against; names aren't secrets. Trying every secret on every call would be slower, and
  would blur which account spoke.
- **Zoom's ``v0`` signature** is HMAC-SHA256 under the connection's webhook secret over
  ``v0:{x-zm-request-timestamp}:{raw body}``, compared in constant time. The body is the bytes
  as received, never re-encoded JSON, so a proxy that rewrites bodies breaks it (D6, 0c).
- **A 300-second window**, in either direction, so a captured call can't be replayed later.
  Repeats inside the window are caught by the ``ZoomEvent`` record (D3).
- **The account check** (``is_from_account``): an event must name the connection's own Zoom
  account, so a leaked secret can't forge events about another account's bookings.
- **URL validation isn't a signing oracle.** Its reply is ``HMAC(secret, plainToken)``. Were it
  answered for any token, anyone could ask for ``plainToken = "v0:{ts}:{body}"`` and get a
  valid signature for a forged event. So validation is signature-checked like every event,
  and ``plainToken`` is limited to URL-safe characters, which can never hold a ``:``.
- **A 256 KB cap**, read from ``Content-Length`` before the body: the largest events are a few
  KB.

Nothing here logs or returns the secret, a signature, a header value or the body: a refusal
is logged once at ``WARNING`` with the connection name and a reason word (``missing``,
``stale``, ``bad signature``, ``wrong account``). An unknown connection name is logged at
``INFO`` only (criterion 4), since anyone can type a URL.
"""

import hashlib
import hmac
import json
import logging
import re
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

logger = logging.getLogger(__name__)

MAX_AGE_SECONDS = 300
MAX_BODY_BYTES = 256 * 1024
URL_VALIDATION = "endpoint.url_validation"
SIGNATURE_VERSION = "v0"
# Request headers as Django's ``META`` names them.
TIMESTAMP_HEADER = "HTTP_X_ZM_REQUEST_TIMESTAMP"
SIGNATURE_HEADER = "HTTP_X_ZM_SIGNATURE"
# Digits only (criterion 5); far more than a seconds timestamp needs, never a huge integer.
TIMESTAMP_PATTERN = re.compile(r"[0-9]{1,15}")
# Criterion 6: URL-safe characters only, which rules out the ":" of a signed message.
PLAIN_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,256}")


@dataclass(frozen=True)
class Refusal:
    """Why a webhook call was turned away: the status to answer, and the reason word logged."""

    status: int
    reason: str


UNKNOWN = Refusal(404, "unknown")
TOO_LARGE = Refusal(413, "too large")
MISSING = Refusal(401, "missing")
STALE = Refusal(401, "stale")
BAD_SIGNATURE = Refusal(401, "bad signature")
WRONG_ACCOUNT = Refusal(401, "wrong account")
UNREADABLE = Refusal(400, "unreadable")
BAD_TOKEN = Refusal(400, "bad token")


@sensitive_variables("secret", "timestamp", "body", "message")
def signature_for(secret, timestamp, body) -> str:
    """``v0=`` and the hex HMAC-SHA256 of ``v0:{timestamp}:{body}`` under ``secret``."""
    message = f"{SIGNATURE_VERSION}:{timestamp}:".encode() + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_VERSION}={digest}"


def body_sha256(body) -> str:
    """The ``ZoomEvent`` key's fingerprint of a raw body (D3): only this is ever kept."""
    return hashlib.sha256(body).hexdigest()


def _refused(slug, refusal) -> Refusal:
    logger.warning("Zoom webhook call to %s refused: %s", slug, refusal.reason)
    return refusal


def _content_length(request):
    try:
        return int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return 0


@sensitive_variables("credentials", "secret", "timestamp", "signature", "expected", "body")
def verify(request, slug):
    """The connection's ``ZoomCredentials`` when the call is Zoom's own, else a ``Refusal``.

    In order (criteria 4 and 5): a connection name the server doesn't have, or one with no
    webhook secret, is ``404``; a ``Content-Length`` over 256 KB is ``413`` before the body is
    read; then both headers must be there, the timestamp within 300 seconds of now either way,
    and the signature right for the raw body. Settings only: no query, no HTTP.
    """
    credentials = settings.ZOOM_S2S_SECRETS.get(slug)
    if credentials is None or not credentials.webhook_secret:
        logger.info("Zoom webhook call to a connection name with no webhook secret: refused.")
        return UNKNOWN
    if _content_length(request) > MAX_BODY_BYTES:
        return _refused(slug, TOO_LARGE)
    body = request.body
    if len(body) > MAX_BODY_BYTES:
        return _refused(slug, TOO_LARGE)

    timestamp = request.META.get(TIMESTAMP_HEADER, "")
    signature = request.META.get(SIGNATURE_HEADER, "")
    if not signature or not TIMESTAMP_PATTERN.fullmatch(timestamp):
        return _refused(slug, MISSING)
    if abs(timezone.now().timestamp() - int(timestamp)) > MAX_AGE_SECONDS:
        return _refused(slug, STALE)
    expected = signature_for(credentials.webhook_secret, timestamp, body)
    # WSGI hands headers over as latin-1 text, so this round-trips whatever bytes were sent.
    if not hmac.compare_digest(expected.encode(), signature.encode("latin-1")):
        return _refused(slug, BAD_SIGNATURE)
    return credentials


@sensitive_variables("body", "event")
def read_event(body):
    """The verified body as a dict with an ``event`` name and a ``payload`` object, or
    ``UNREADABLE`` (400).

    The ``payload`` check is here, before the account check, so a signed body that isn't a
    Zoom event is a 400 and never a misleading ``wrong account`` 401 (criterion 10, review
    round 1, S2; D18).
    """
    try:
        event = json.loads(body)
    except (UnicodeDecodeError, ValueError):
        return UNREADABLE
    if (
        not isinstance(event, dict)
        or not isinstance(event.get("event"), str)
        or not isinstance(event.get("payload"), dict)
    ):
        return UNREADABLE
    return event


@sensitive_variables("credentials", "token", "secret")
def url_validation_reply(credentials, event):
    """Zoom's URL validation answer (criterion 6), or ``BAD_TOKEN`` (400).

    ``{"plainToken": p, "encryptedToken": hex(HMAC-SHA256(secret, p))}``, only for a
    ``plainToken`` of URL-safe characters (see the module docstring). Only call it for an
    event that ``verify`` accepted. No query, no HTTP.
    """
    payload = event.get("payload")
    token = payload.get("plainToken") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not PLAIN_TOKEN_PATTERN.fullmatch(token):
        return BAD_TOKEN
    secret = credentials.webhook_secret
    encrypted = hmac.new(secret.encode(), token.encode("ascii"), hashlib.sha256).hexdigest()
    return {"plainToken": token, "encryptedToken": encrypted}


@sensitive_variables("credentials")
def is_from_account(credentials, event, slug) -> bool:
    """True when ``payload.account_id`` is this connection's own Zoom account (criterion 7).

    Compared in constant time, like the signature. A mismatch is logged with the connection
    name and ``wrong account``, never either account ID.
    """
    payload = event.get("payload")
    named = payload.get("account_id") if isinstance(payload, dict) else None
    # ``surrogatepass``: JSON can carry a lone surrogate, which plain UTF-8 can't encode.
    if isinstance(named, str) and hmac.compare_digest(
        named.encode("utf-8", "surrogatepass"), credentials.account_id.encode()
    ):
        return True
    _refused(slug, WRONG_ACCOUNT)
    return False
