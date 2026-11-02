"""Value rules for Zoom link requests that more than one layer needs.

Phone numbers are normalised to E.164 once, on the way in, so search, display and the
duplicate-requester lookup all compare like with like (criterion 8). The rule is deliberately
loose: no operator or area-code list, only the shape of a dialable number. The function moves
to ``apps/core`` when a second app needs it.
"""

import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.views.decorators.debug import sensitive_variables

PHONE_ERROR = "Type a phone number we can call, like 077 123 4567 or +94 77 123 4567."
HOST_KEY_ERROR = "A Zoom host key is 6 to 10 digits."
CREDENTIAL_SET_ERROR = "Use lower-case letters, numbers and hyphens only, like zoom-01."
# A Zoom connection name (brief 006, criteria 4 and 34; brief 015, criterion 1): lower-case
# words of letters and digits joined by single hyphens. \Z, not $, so a trailing newline can't
# slip through. The name is part of the connection's webhook address (/zoom/webhooks/zoom-01/),
# so it must be safe in a URL path, and it's never changed once saved (brief 015, D2).
CREDENTIAL_SET_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*\Z"
# Brief 015, criterion 13: what a pasted Zoom ID or secret may hold once trimmed. Zoom's IDs and
# secrets are printable ASCII with no spaces, so anything else is a paste of the wrong thing.
_ZOOM_VALUE = re.compile(r"[\x21-\x7e]+")

_PHONE_SEPARATORS = re.compile(r"[\s\-().]")
_E164 = re.compile(r"\+\d{8,15}")
_HOST_KEY = re.compile(r"\d{6,10}")


def normalise_phone(value) -> str:
    """Return ``value`` as E.164 (``+94771234567``) or raise ``ValidationError``.

    1. Strip spaces, ``-``, ``(``, ``)`` and ``.``.
    2. ``00…`` becomes ``+…``; ``0`` plus 9 digits and bare ``94`` plus 9 digits are
       Sri Lankan numbers and become ``+94`` plus the 9 digits.
    3. The result must be ``+`` followed by 8 to 15 digits.
    """
    compact = _PHONE_SEPARATORS.sub("", value or "")
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    elif re.fullmatch(r"0\d{9}", compact):
        compact = "+94" + compact[1:]
    elif re.fullmatch(r"94\d{9}", compact):
        compact = "+" + compact
    if not _E164.fullmatch(compact):
        raise ValidationError(PHONE_ERROR, code="invalid_phone")
    return compact


def format_phone(e164: str) -> str:
    """Group a stored Sri Lankan number for reading (``+94 77 123 4567``).

    Other countries group their numbers differently, and guessing wrong is worse than not
    grouping, so any number that isn't ``+94`` plus 9 digits is returned unchanged.
    """
    match = re.fullmatch(r"\+94(\d{2})(\d{3})(\d{4})", e164 or "")
    if not match:
        return e164 or ""
    return "+94 {} {} {}".format(*match.groups())


@sensitive_variables("value")
def is_zoom_https_url(value) -> bool:
    r"""True for a well-formed ``https`` URL on ``zoom.us`` or a subdomain of it.

    One rule for the two places a Zoom URL is trusted: a join link IT pastes (brief 005) and
    the ``start_url`` the start page redirects to (brief 011, criterion 18), so a strange answer
    can never become an open redirect. A backslash is refused outright, because browsers treat
    ``\`` like ``/``, so ``https://evil.example\.zoom.us/…`` would pass a host-suffix test yet
    open evil.example. ``value`` may be a start URL, so it's masked in error reports.
    """
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    try:
        URLValidator(schemes=["https"])(value)
        parts = urlsplit(value)
        host = (parts.hostname or "").lower()
    except (ValidationError, ValueError):
        return False
    return parts.scheme == "https" and (host == "zoom.us" or host.endswith(".zoom.us"))


validate_credential_set = RegexValidator(
    CREDENTIAL_SET_PATTERN, message=CREDENTIAL_SET_ERROR, code="invalid"
)


@sensitive_variables("value")
def validate_zoom_value(value, *, max_length: int, message: str) -> str:
    """Return a pasted Zoom Account ID, Client ID or secret, trimmed; or raise ``message``.

    Brief 015, criterion 13: after trimming, the value must be non-empty, have no whitespace,
    be printable ASCII, and be at most ``max_length`` characters (100 for IDs, 200 for
    secrets). The length is checked here, not by a ``maxlength`` attribute, so a paste that's
    too long is refused rather than silently cut short in the browser and then refused by Zoom
    (D20 G2). Each field passes its own pinned ``message``. ``value`` may be a secret, so it's
    masked in error reports, and the error never repeats it.
    """
    value = (value or "").strip()
    if len(value) > max_length or not _ZOOM_VALUE.fullmatch(value):
        raise ValidationError(message, code="invalid")
    return value


@sensitive_variables("value")
def validate_host_key(value: str) -> None:
    """Zoom host keys are 6 to 10 digits; anything else is a typing mistake.

    ``value`` is the typed key, so it's masked in error reports (brief 005 review, nit 2).
    """
    if not _HOST_KEY.fullmatch(value or ""):
        raise ValidationError(HOST_KEY_ERROR, code="invalid_host_key")
