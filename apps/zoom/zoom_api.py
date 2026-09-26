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
  ``errors.py`` whose message is a fixed phrase. Zoom's response text never leaves this module.
- **The token cache** (D4) lives in this process's memory only: never the database, never
  Django's cache (which could later be the database or Redis) and never a log. One token per
  credential set, reused until 300 seconds before it expires. Threads (the preview's parallel
  lookups) share it under a lock; each set has its own fetch lock, so a slow token fetch for
  one account doesn't hold up the others.
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
from urllib.parse import quote

import requests
from django.views.decorators.debug import sensitive_variables
from urllib3.exceptions import ProtocolError

from .errors import (
    ZoomAuthFailed,
    ZoomBusy,
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

# The clock the token cache uses; a module name so tests can move time forward.
monotonic = time.monotonic

_token_cache: dict[tuple[str, str], tuple[str, float]] = {}
_fetch_locks: dict[tuple[str, str], threading.Lock] = {}
_cache_lock = threading.Lock()


def reset_token_cache() -> None:
    """Forget every cached token (tests, criterion 45)."""
    with _cache_lock:
        _token_cache.clear()
        _fetch_locks.clear()


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


def _api_error(response):
    """The error for a non-2xx API answer (criterion 10). A 401 here is after the retry."""
    status = response.status_code
    code = _zoom_code(response)
    if status == 429:
        return ZoomBusy()
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
    """Calls Zoom's API for one credential set. Cheap to make: one per lookup or thread.

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
        self._cache_key = (credentials.slug, credentials.client_id)
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
