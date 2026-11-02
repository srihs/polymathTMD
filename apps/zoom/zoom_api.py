"""The only module that talks HTTP to Zoom, and the only one that imports ``requests`` (brief 006).

Why it is shaped like this:

- **Fixed HTTPS hosts** (criterion 8, D13). The token endpoint and the API base are module
  constants, not settings, so no configuration mistake can send a credential anywhere else.
  Certificate checks are ``requests``' default and are never switched off; redirects are not
  followed, so a 3xx can't carry the ``Authorization`` header to another host.
- **One request helper with timeouts** of ``(5, 15)`` seconds (connect, read) on every call.
- **No automatic retries** (D9), except one: an API ``401`` drops the cached token, fetches
  one new token and repeats the call once (criterion 9). A ``401`` means Zoom refused the
  request before acting on it, so even a create is safe to repeat then. Nothing else is ever
  repeated: a repeated create after a timeout could make a second meeting.
- **One error mapping** (criterion 10): every failure becomes a ``ProviderError`` subclass from
  ``errors.py`` whose message is a fixed phrase. Zoom's response text never leaves this module:
  it's never shown or logged (006 criterion 10, as amended by brief 012's D19). The one place
  it's read at all is a ``429``, to choose between two fixed errors (``_is_daily_limit``).
- **The token cache** (D4) lives in this process's memory only: never the database, never
  Django's cache (which could later be the database or Redis) and never a log. One token per
  Zoom connection, **credentials version and Client ID** (brief 015, criterion 24, D8, D21),
  reused until 300 seconds before it expires. Every operation reads its connection row,
  version included, so after IT saves new details every Gunicorn worker fetches a fresh token
  on its next call, with no restart, no signal and no message between processes. The Client
  ID is in the key because a connection deleted and re-added under the same name starts again
  at version 1: the version alone can't tell the old Zoom app from the new one, and the old
  app's token would book on the wrong Zoom account. Building a client drops that connection's
  tokens for every **lower** version, so a replaced secret's token isn't kept, but never a
  higher one: a client built from a stale read mustn't evict a newer version's token.
  Threads (the preview's parallel lookups) share the cache under a lock; each key has its
  own fetch lock, so a slow token fetch for one account doesn't hold up the others.
- **Credentials come from the database** (brief 015): ``ZoomConnection.credentials()`` builds
  a ``ZoomCredentials`` for one operation. Nothing here keeps them between operations.
- **Secrets stay out of error reports**: every function that holds a credential, a token or
  Zoom's answer (which carries join links, and on a create the ``start_url``) is
  ``@sensitive_variables``, and errors are raised ``from None``, so a traceback never shows
  ``requests``' own frames, whose locals include the prepared headers.

The token request sends ``grant_type=account_credentials`` and ``account_id`` as a
form-encoded body with HTTP Basic auth (Zoom's Server-to-Server OAuth docs accept the body or
the query). The body keeps the account ID out of the URL, which ``urllib3`` and exception
texts can repeat.
"""

import threading
import time
from dataclasses import dataclass, field
from urllib.parse import quote

import requests
from django.views.decorators.debug import sensitive_variables
from urllib3.exceptions import ProtocolError

from .errors import (
    ZoomAuthFailed,
    ZoomBusy,
    ZoomDailyLimit,
    ZoomMeetingNotFound,
    ZoomMissingScope,
    ZoomRejected,
    ZoomUnavailable,
    ZoomUserNotFound,
)

TOKEN_URL = "https://zoom.us/oauth/token"
API_BASE = "https://api.zoom.us/v2"
TIMEOUT = (5, 15)  # seconds: (connect, read)
TOKEN_REFRESH_MARGIN = 300  # seconds before expiry that a cached token stops being used
MAX_PAGES = 10

# Zoom's error codes that mean "this app lacks a scope for the call" (4700, 4711), "no such
# user" (1001) and "no such meeting" (3001).
MISSING_SCOPE_CODES = frozenset({4700, 4711})
USER_NOT_FOUND = 1001
MEETING_NOT_FOUND = 3001

# How Zoom marks a 429 as its daily limit rather than its per-second one (brief 012, criterion
# 14, D19). Zoom's rate-limits page (https://developers.zoom.us/docs/api/rate-limits/) words
# the two answers "You have reached the maximum per-second rate limit for this API. Try again
# later." and "You have reached the maximum daily rate limit for this API. Refer to the
# response header for details on when you can make another request." The page's earlier
# version (marketplace.zoom.us/docs/api-reference/rate-limits/, as archived in 2021-2022)
# also named that header: ``X-RateLimit-Type`` is ``QPS`` for the per-second limit and
# ``Daily-limit`` for the daily one. Today's page no longer lists it, so either signal is
# enough, and neither is required.
RATE_LIMIT_TYPE_HEADER = "X-RateLimit-Type"
DAILY_WORD = "daily"

# The clock the token cache uses; a module name so tests can move time forward.
monotonic = time.monotonic

# Keyed by (connection name, credentials version, Client ID); see the module docstring.
_token_cache: dict[tuple[str, int, str], tuple[str, float]] = {}
_fetch_locks: dict[tuple[str, int, str], threading.Lock] = {}
_cache_lock = threading.Lock()


@dataclass(frozen=True)
class ZoomCredentials:
    """One Zoom connection's token parts, as read for one operation (brief 015, criterion 2).

    Built only by ``ZoomConnection.credentials()``, from the row as read in that operation, and
    dropped when it ends. ``version`` is the row's ``credentials_version``, which keys the token
    cache. Every field but the connection name is ``repr=False``, so a traceback, a log line or
    an error report that shows one names the connection and nothing else. There's no webhook
    secret here: it isn't part of a token, and the webhook reads it on its own.
    """

    slug: str
    version: int = field(repr=False)
    account_id: str = field(repr=False)
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)


def reset_token_cache() -> None:
    """Forget every cached token (tests, criterion 45)."""
    with _cache_lock:
        _token_cache.clear()
        _fetch_locks.clear()


def _forget_lower_versions(cache_key) -> None:
    """Drop this connection's cached tokens for every version lower than ``cache_key``'s (c. 24).

    A token fetched with replaced details must not outlive them in this process, whatever its
    Client ID. Only *lower* versions go: a client built from an older, stale read of the row
    (another worker saved in between) must not evict the newer version's token, which the next
    fresh read will want again (review round 1, N4). A same-version key with another Client ID
    is a re-added connection's old app; it's simply never looked up again.
    """
    slug, version, _ = cache_key
    with _cache_lock:
        for cache in (_token_cache, _fetch_locks):
            for key in [key for key in cache if key[0] == slug and key[1] < version]:
                del cache[key]


def user_path(email: str, *rest: str) -> str:
    """``/users/{email}[/…]``, with the email quoted so it can't change the path."""
    return "/".join(["/users", quote(email, safe="@"), *rest])


def meeting_path(meeting_id) -> str:
    return f"/meetings/{quote(str(meeting_id), safe='')}"


def _zoom_code(response):
    """Zoom's numeric ``code`` from an error body, or ``None``. The message text is ignored."""
    try:
        code = response.json().get("code")
    except (ValueError, AttributeError):
        return None
    return code if isinstance(code, int) else None


@sensitive_variables("kind", "body", "message")
def _is_daily_limit(response) -> bool:
    """Whether a ``429`` is Zoom's daily limit: its header or its message says ``daily``.

    Zoom's header value and message are read only to choose between two fixed errors; neither
    is returned, kept or logged (D19). A body that isn't JSON, or has no text ``message``,
    reads as "not daily", so an odd answer is still ``ZoomBusy`` and never raises.
    """
    kind = response.headers.get(RATE_LIMIT_TYPE_HEADER) or ""
    if isinstance(kind, str) and DAILY_WORD in kind.lower():
        return True
    try:
        body = response.json()
    except ValueError:
        return False
    message = body.get("message") if isinstance(body, dict) else None
    return isinstance(message, str) and DAILY_WORD in message.lower()


def _api_error(response):
    """The error for a non-2xx API answer (criterion 10). A 401 here is after the retry.

    Only a ``429`` is told apart by Zoom's own answer (brief 012, criterion 14): the daily
    limit is lasting until Zoom's reset at 00:00 UTC, so "try again in a few minutes" would
    keep failing all day. Any other status with ``daily`` in its message is unaffected.
    """
    status = response.status_code
    code = _zoom_code(response)
    if status == 429:
        return ZoomDailyLimit() if _is_daily_limit(response) else ZoomBusy()
    if status >= 500:
        return ZoomUnavailable(maybe_done=True)
    if status in (400, 401) and code in MISSING_SCOPE_CODES:
        return ZoomMissingScope()
    if status == 401:
        return ZoomAuthFailed()
    if status == 404 and code == USER_NOT_FOUND:
        return ZoomUserNotFound()
    if status == 404 and code == MEETING_NOT_FOUND:
        return ZoomMeetingNotFound()
    return ZoomRejected(code if code is not None else status)


def _token_error(response):
    """The error for a non-2xx token answer: a 400 or 401 is always the credentials."""
    status = response.status_code
    if status in (400, 401):
        return ZoomAuthFailed()
    if status == 429:
        return ZoomBusy()
    if status >= 500:
        return ZoomUnavailable()
    return ZoomRejected(_zoom_code(response) or status)


def _is_missing_scope(response) -> bool:
    return response.status_code in (400, 401) and _zoom_code(response) in MISSING_SCOPE_CODES


class ZoomClient:
    """Calls Zoom's API for one Zoom connection. Cheap to make: one per lookup or thread.

    Each client has its own ``requests.Session`` (connection reuse within a lookup's pages);
    sessions aren't shared across threads. Tokens are shared through the module cache.

    Use it as a context manager (``with ZoomClient(credentials) as client:``), or call
    ``close()``, so the session's pooled connections are released when the work is done. The
    preview makes a client per account per page load in a thread; left to the garbage
    collector, their sockets would linger in each Gunicorn worker (review round 1, nit).
    """

    @sensitive_variables("credentials")
    def __init__(self, credentials):
        self.slug = credentials.slug
        self._credentials = credentials
        self._cache_key = (credentials.slug, credentials.version, credentials.client_id)
        _forget_lower_versions(self._cache_key)
        self._session = requests.Session()

    def __repr__(self):
        return f"<ZoomClient: {self.slug}>"

    def close(self) -> None:
        """Release the session's connections. Safe to call more than once."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    # ------------------------------------------------------------------ public calls

    def get(self, path, params=None) -> dict:
        return self._json(self._call("GET", path, params=params))

    def post(self, path, json) -> dict:
        return self._json(self._call("POST", path, json=json))

    def patch(self, path, json, params=None) -> None:
        """Update (brief 012). Zoom answers ``204 No Content``; like a create, it's never repeated
        here after a timeout, so the caller decides what an unanswered update means."""
        self._call("PATCH", path, params=params, json=json)

    def delete(self, path, params=None) -> None:
        """Delete; a 404 "no such meeting" counts as done (it's already gone)."""
        self._call("DELETE", path, params=params, missing_ok=True)

    # Listed meetings carry their join links, which let anyone in: masked in reports.
    @sensitive_variables("items", "page")
    def paged(self, path, params, key, max_pages=MAX_PAGES) -> list:
        """Every item under ``key`` across ``next_page_token`` pages.

        More than ``max_pages`` pages raises ``ZoomUnavailable``: a partial list could miss a
        booking, so the caller fails closed (criterion 12, D7).
        """
        items, params, token = [], dict(params or {}), None
        for _ in range(max_pages):
            if token:
                params["next_page_token"] = token
            page = self.get(path, params)
            items.extend(page.get(key) or [])
            token = page.get("next_page_token")
            if not token:
                return items
        raise ZoomUnavailable()

    # ------------------------------------------------------------------ plumbing

    @staticmethod
    @sensitive_variables("response", "data")
    def _json(response) -> dict:
        if response.status_code == 204 or not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            raise ZoomUnavailable() from None
        if not isinstance(data, dict):
            raise ZoomUnavailable()
        return data

    @sensitive_variables("token", "headers", "response")
    def _call(self, method, path, *, params=None, json=None, missing_ok=False):
        """One API call, with the one allowed retry after a ``401``."""
        url = API_BASE + path
        for attempt in (1, 2):
            token = self._token()
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            response = self._send(method, url, headers=headers, params=params, json=json)
            if response.status_code == 401 and attempt == 1 and not _is_missing_scope(response):
                self._drop_token(token)
                continue
            if 200 <= response.status_code < 300:
                return response
            if missing_ok and response.status_code == 404:
                if _zoom_code(response) == MEETING_NOT_FOUND:
                    return response
            raise _api_error(response)
        raise AssertionError("unreachable: the second attempt returns or raises")

    @sensitive_variables("headers", "data", "auth")
    def _send(
        self,
        method,
        url,
        *,
        headers=None,
        params=None,
        json=None,
        data=None,
        auth=None,
        token_request=False,
    ):
        """Send one request; transport failures become ``ZoomUnavailable``.

        ``maybe_done`` is set when the request may have reached Zoom: a read timeout, or a
        connection dropped after sending (``ProtocolError``). A connect timeout or a refused
        connection means nothing reached Zoom. Token requests never set it: a failed token
        fetch means the API call itself was never made.
        """
        try:
            return self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json,
                data=data,
                auth=auth,
                timeout=TIMEOUT,
                allow_redirects=False,
            )
        except requests.exceptions.ConnectTimeout:
            raise ZoomUnavailable() from None
        except requests.exceptions.ReadTimeout:
            raise ZoomUnavailable(maybe_done=not token_request) from None
        except requests.exceptions.ConnectionError as exc:
            reached = bool(exc.args) and isinstance(exc.args[0], ProtocolError)
            raise ZoomUnavailable(maybe_done=reached and not token_request) from None
        except requests.exceptions.RequestException:
            raise ZoomUnavailable() from None

    # ------------------------------------------------------------------ token

    @sensitive_variables("cached", "token")
    def _token(self) -> str:
        with _cache_lock:
            cached = _token_cache.get(self._cache_key)
            if cached and cached[1] > monotonic():
                return cached[0]
            fetch_lock = _fetch_locks.setdefault(self._cache_key, threading.Lock())
        with fetch_lock:
            # Another thread may have fetched it while this one waited.
            with _cache_lock:
                cached = _token_cache.get(self._cache_key)
                if cached and cached[1] > monotonic():
                    return cached[0]
            token, expires_in = self._fetch_token()
            with _cache_lock:
                _token_cache[self._cache_key] = (
                    token,
                    monotonic() + max(expires_in - TOKEN_REFRESH_MARGIN, 0),
                )
            return token

    @sensitive_variables("token")
    def _drop_token(self, token) -> None:
        with _cache_lock:
            cached = _token_cache.get(self._cache_key)
            if cached and cached[0] == token:
                del _token_cache[self._cache_key]

    @sensitive_variables("credentials", "auth", "data", "response", "payload", "token")
    def _fetch_token(self) -> tuple[str, int]:
        """A new access token and its lifetime in seconds (criterion 9)."""
        credentials = self._credentials
        auth = (credentials.client_id, credentials.client_secret)
        data = {"grant_type": "account_credentials", "account_id": credentials.account_id}
        response = self._send("POST", TOKEN_URL, data=data, auth=auth, token_request=True)
        if not 200 <= response.status_code < 300:
            raise _token_error(response)
        try:
            payload = response.json()
            token = payload["access_token"]
            expires_in = int(payload.get("expires_in", 3600))
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ZoomUnavailable() from None
        if not isinstance(token, str) or not token:
            raise ZoomUnavailable()
        return token, expires_in
