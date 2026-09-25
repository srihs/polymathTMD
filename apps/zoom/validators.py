"""Value rules for Zoom link requests that more than one layer needs.

Phone numbers are normalised to E.164 once, on the way in, so search, display and the
duplicate-requester lookup all compare like with like (criterion 8). The rule is deliberately
loose: no operator or area-code list, only the shape of a dialable number. The function moves
to ``apps/core`` when a second app needs it.
"""

import re

from django.core.exceptions import ValidationError
from django.views.decorators.debug import sensitive_variables

PHONE_ERROR = "Type a phone number we can call, like 077 123 4567 or +94 77 123 4567."
HOST_KEY_ERROR = "A Zoom host key is 6 to 10 digits."

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
def validate_host_key(value: str) -> None:
    """Zoom host keys are 6 to 10 digits; anything else is a typing mistake.

    ``value`` is the typed key, so it's masked in error reports (brief 005 review, nit 2).
    """
    if not _HOST_KEY.fullmatch(value or ""):
        raise ValidationError(HOST_KEY_ERROR, code="invalid_host_key")
