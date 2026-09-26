"""What can go wrong when the app asks a meeting provider for something (briefs 005 and 006).

These live in their own module, not in ``providers.py``, because both ``providers.py`` and
``zoom_api.py`` raise them and ``providers.py`` imports ``zoom_api.py``: one import direction,
no cycle. ``providers.py`` re-exports them, so callers keep importing from there.

``user_message`` is always a fixed, lower-case phrase from brief 006's criterion 10 table. It
never carries Zoom's own response text, a URL or a credential, so any error here is safe to put
in front of IT, in a log, or in ``str()``.

Two class attributes steer the wording of the messages built from these errors:

- ``lasting`` (D23): ``False`` when waiting a few minutes can fix it (Zoom unreachable or busy),
  ``True`` when it can't (bad credentials, a missing permission, an unknown user, any other
  refusal). The message builders offer "try again in a few minutes" only when it's honest.
- ``maybe_done`` (D25): set only on ``ZoomUnavailable`` raised by an API call whose request
  reached Zoom (a read timeout, a dropped connection mid-request or an HTTP 5xx). For a create
  call it means Zoom may have made the meeting anyway, so the app looks for it before saying so.
"""


class ProviderError(Exception):
    """The provider couldn't do what was asked. ``user_message`` is safe to show IT.

    Plain ``ProviderError`` (the fake provider's) is temporary and certain: ``lasting`` and
    ``maybe_done`` are both false.
    """

    lasting = False
    maybe_done = False

    def __init__(self, user_message):
        super().__init__(user_message)
        self.user_message = user_message

    @property
    def reason_sentence(self) -> str:
        """``Zoom is busy right now.``: the phrase as a sentence (criteria 15, G6, and 28)."""
        phrase = self.user_message
        return f"{phrase[:1].upper()}{phrase[1:]}." if phrase else ""


class ZoomUnavailable(ProviderError):
    """No usable answer: a connection error, a timeout, an HTTP 5xx, or too many pages."""

    def __init__(self, *, maybe_done=False):
        super().__init__("no answer from Zoom")
        self.maybe_done = maybe_done


class ZoomBusy(ProviderError):
    """HTTP 429: Zoom's rate limit. Temporary."""

    def __init__(self):
        super().__init__("Zoom is busy right now")


class ZoomAuthFailed(ProviderError):
    """The token request was refused, or the API said 401 again after one fresh token."""

    lasting = True

    def __init__(self):
        super().__init__("Zoom didn't accept this account's connection details")


class ZoomMissingScope(ProviderError):
    """Zoom codes 4700 / 4711: the Server-to-Server app lacks a scope this call needs."""

    lasting = True

    def __init__(self):
        super().__init__("the Zoom app for this account is missing a permission")


class ZoomUserNotFound(ProviderError):
    """HTTP 404 with Zoom code 1001: the subscription has no user with the account's email."""

    lasting = True

    def __init__(self):
        super().__init__("Zoom has no user with this account's sign-in email")


class ZoomRejected(ProviderError):
    """Any other 4xx: Zoom refused the request itself, so repeating it later won't help (D23).

    ``code`` is Zoom's numeric error code, or the HTTP status when the body has none. It's the
    one detail passed on, because it's what the person who looks after the server needs.
    """

    lasting = True

    def __init__(self, code):
        super().__init__(f"Zoom error {code}")
        self.code = code


class ZoomNotConnected(ProviderError):
    """The account has no working connection on this server, so nothing was sent to Zoom.

    Callers check ``is_connected()`` first and use criterion 29's own message; this is the
    backstop if a lookup is asked for anyway.
    """

    lasting = True

    def __init__(self):
        super().__init__("this account isn't connected to Zoom")
