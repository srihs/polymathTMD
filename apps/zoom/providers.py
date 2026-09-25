"""Who makes the Zoom meeting when IT approves a request (brief 005, D4).

The rest of the app talks to one small interface, so brief 006 can add the live Zoom API
provider without touching the approval logic:

- ``create_meeting(*, link_request, host_account, occurrences, manual=None) -> Meeting``;
- ``needs_manual_details``: whether IT must type the link, meeting ID and passcode;
- failures raise ``ProviderError(user_message)``; the service rolls the booking back.

``Meeting`` never carries Zoom's ``start_url``: it would let anyone start the meeting as host
without signing in, so it is never stored or passed on (criterion 46).

Providers:

- ``manual`` (production until 006): IT creates the meeting in Zoom on the account the system
  chose, then pastes its details; the provider returns what was typed.
- ``fake`` (dev and tests): deterministic links on the reserved ``.invalid`` TLD, so a fake
  link can never reach a real meeting. Check ``zoom.E001`` keeps it out of production.
"""

import threading
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class Meeting:
    meeting_id: str
    join_url: str
    passcode: str


class ProviderError(Exception):
    """The provider couldn't make the meeting. ``user_message`` is safe to show IT."""

    def __init__(self, user_message):
        super().__init__(user_message)
        self.user_message = user_message


class MeetingProvider:
    needs_manual_details = False

    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        raise NotImplementedError


class FakeProvider(MeetingProvider):
    """Deterministic stand-in for Zoom.

    Class-level state so a test can inspect and steer the instance a view created:
    ``calls`` records what each call received (including ``wants_recording``, criterion 59),
    and setting ``next_error`` makes the next call raise ``ProviderError`` with that message.
    Tests reset both with ``FakeProvider.reset()``.
    """

    calls: list = []
    next_error: str | None = None
    _lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls._lock:
            cls.calls = []
            cls.next_error = None

    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        with self._lock:
            error = type(self).next_error
            if error is not None:
                type(self).next_error = None
                raise ProviderError(error)
            type(self).calls.append(
                {
                    "link_request_id": link_request.pk,
                    "host_account_id": host_account.pk,
                    "occurrence_count": len(occurrences),
                    "wants_recording": link_request.wants_recording,
                }
            )
        meeting_id = str(90_000_000_000 + link_request.pk)
        return Meeting(
            meeting_id=meeting_id,
            join_url=f"https://zoom.example.invalid/j/{meeting_id}",
            passcode=f"fake{link_request.pk % 1_000_000:06d}",
        )


class ManualProvider(MeetingProvider):
    """IT made the meeting in Zoom by hand; return the details it pasted."""

    needs_manual_details = True

    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        if not manual:
            raise ProviderError("the Zoom link, meeting ID and passcode are missing")
        return Meeting(
            meeting_id=manual["meeting_id"],
            join_url=manual["join_url"],
            passcode=manual.get("passcode", ""),
        )


PROVIDERS = {"fake": FakeProvider, "manual": ManualProvider}


def get_provider() -> MeetingProvider:
    """The provider named by ``settings.ZOOM_PROVIDER`` (check ``zoom.E002`` validates it)."""
    try:
        return PROVIDERS[settings.ZOOM_PROVIDER]()
    except KeyError:
        raise ImproperlyConfigured(
            f"ZOOM_PROVIDER must be one of {', '.join(PROVIDERS)}."
        ) from None
