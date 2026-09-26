"""Who makes the Zoom meeting when IT approves a request, and who says whether Zoom is busy
(brief 005, D4; brief 006).

The rest of the app talks to one small interface, so the approval logic doesn't care which
provider is in use:

- ``needs_manual_details``: IT must type the link, meeting ID and passcode (``manual``).
- ``checks_zoom``: the provider can ask Zoom which meetings an account already has, so the
  preview and ``approve()`` check Zoom for clashes as well as the database.
- ``is_connected(account)``: whether this provider can reach Zoom for the account. It reads
  settings only, never the network.
- ``busy_times(*, host_account, start, end) -> list[BusyTime]``: the account's dated Zoom
  meetings overlapping ``[start, end)`` (criterion 12).
- ``create_meeting(*, link_request, host_account, occurrences, manual=None) -> Meeting``.
- ``delete_meeting(*, host_account, meeting_id, occurrence_id=None)``: for rollback, and for
  brief 011's cancelling. Zoom's "no such meeting" counts as done.
- ``can_start`` (brief 011): the provider can hand out a fresh host start link, so approval
  emails carry the app's start link. ``start_url(*, host_account, meeting_id) -> str`` asks
  for one; ``occurrence_id_for(*, host_account, meeting_id, starts_at)`` finds a class's Zoom
  occurrence ID when none was stored.
- failures raise a ``ProviderError`` subclass (``errors.py``, re-exported here).

``Meeting`` never carries Zoom's ``start_url``: it would let anyone start the meeting as host
without signing in, so it is dropped where Zoom's answer is read and never stored or passed on
(brief 005, criterion 46). ``start_url()`` is the one exception, by design (brief 011, D4): it
returns the URL to the start page's POST, which redirects to it at once, and nothing keeps it.

Providers:

- ``zoom``: the live Zoom API through ``zoom_api.py``, one Server-to-Server OAuth app per
  subscription, chosen by ``HostAccount.credential_set``.
- ``manual`` (the fallback): IT creates the meeting in Zoom on the account the system chose,
  then pastes its details. It can't see Zoom, which is why ``zoom.W001`` warns about it.
- ``fake`` (dev and tests): deterministic links on the reserved ``.invalid`` TLD, so a fake
  link can never reach a real meeting, and steerable Zoom answers for tests. ``zoom.E001``
  keeps it out of production.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.debug import sensitive_variables

from . import zoom_api
from .errors import (  # noqa: F401  (re-exported: callers import the error types from here)
    ProviderError,
    ZoomAuthFailed,
    ZoomBusy,
    ZoomMeetingNotFound,
    ZoomMissingScope,
    ZoomNotConnected,
    ZoomRejected,
    ZoomUnavailable,
    ZoomUserNotFound,
)
from .validators import is_zoom_https_url

# ISO weekday (1 = Monday) to Zoom's ``weekly_days`` (1 = Sunday), criterion 14.
ZOOM_WEEKDAYS = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 1}
# Zoom meeting types: 2 scheduled, 8 recurring with a fixed time. Types 1 (instant),
# 3 (recurring, no fixed time) and 4 (personal meeting ID) are ignored (D20).
SCHEDULED, RECURRING_FIXED = 2, 8
LIST_PAGE_SIZE = 300
# Design D.4: how a Zoom meeting with no topic is named, on the page and in criterion 26's
# message. Defined here, beside ``BusyTime``, which names a meeting with it.
UNNAMED_MEETING = "a meeting with no name"
# What reading a malformed Zoom answer can raise. Caught only around the reading, never around
# the HTTP calls, so a ``ProviderError`` keeps its own kind.
UNREADABLE_ANSWER = (AttributeError, KeyError, OverflowError, TypeError, ValueError)


@dataclass(frozen=True)
class Meeting:
    """What the app keeps of a meeting. The link and passcode stay out of ``repr``.

    ``occurrence_ids`` is ``((start, Zoom occurrence ID), …)`` for a recurring meeting, and
    ``recurring`` says Zoom made a series, so ``approve()`` checks its dates (criterion 24).
    """

    meeting_id: str
    join_url: str = field(repr=False)
    passcode: str = field(repr=False)
    occurrence_ids: tuple = ()
    recurring: bool = False


@dataclass(frozen=True)
class BusyTime:
    """One dated Zoom meeting (or one class of a series) on an account, in UTC.

    Holds only what the clash check and the page need: no link, no passcode, no token. It's
    what the preview cache stores (criterion 19).
    """

    starts_at: datetime
    ends_at: datetime
    topic: str
    meeting_id: str
    agenda: str = ""

    def overlaps(self, start, end) -> bool:
        """The overlap rule of brief 005's D6: touching end-to-start isn't a clash."""
        return self.starts_at < end and start < self.ends_at

    @property
    def display_topic(self) -> str:
        """The topic as people read it: Zoom allows an empty one, which gets a plain name.

        The one place that fallback is decided, so the detail page's clash line and criterion
        26's message always name an untitled meeting the same way (review round 1, SF3).
        """
        return self.topic or UNNAMED_MEETING


def zoom_weekly_days(weekdays: str) -> str:
    """``"1,3"`` (ISO, Monday and Wednesday) to ``"2,4"`` (Zoom's numbering)."""
    return ",".join(
        str(ZOOM_WEEKDAYS[int(day)]) for day in (weekdays or "").split(",") if day.strip()
    )


def parse_zoom_time(value) -> datetime:
    """Zoom's ``2026-10-05T03:00:00Z`` as an aware UTC datetime."""
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def meeting_payload(link_request, occurrences) -> dict:
    """The create body (criteria 22, 23, 25 and 49), and nothing else.

    ``settings`` carries only an explicit ``auto_recording``, so an account-wide default never
    records a class nobody asked to record, while every other meeting setting, join before
    host and the waiting room included, stays as the account has it (owner, Q1; D19).
    A weekly class is one series starting at the first stored class, which is always on a
    ticked day, so Zoom's series and the stored classes start together (D5).
    """
    first = min(occurrences, key=lambda occurrence: occurrence.starts_at)
    local_start = first.starts_at.astimezone(ZoneInfo(settings.TIME_ZONE))
    payload = {
        "topic": link_request.class_name,
        "type": SCHEDULED,
        "start_time": local_start.strftime("%Y-%m-%dT%H:%M:%S"),
        "timezone": settings.TIME_ZONE,
        "duration": int((first.ends_at - first.starts_at).total_seconds() // 60),
        "agenda": link_request.zoom_marker,
        "settings": {"auto_recording": "cloud" if link_request.wants_recording else "none"},
    }
    if link_request.repeat == link_request.Repeat.WEEKLY:
        payload["type"] = RECURRING_FIXED
        payload["recurrence"] = {
            "type": 2,  # weekly
            "repeat_interval": 1,
            "weekly_days": zoom_weekly_days(link_request.weekdays),
            "end_times": len(occurrences),
        }
    return payload


class MeetingProvider:
    needs_manual_details = False
    checks_zoom = False
    can_start = False

    def is_connected(self, host_account) -> bool:
        return True

    def busy_times(self, *, host_account, start, end) -> list[BusyTime]:
        raise NotImplementedError

    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        raise NotImplementedError

    def delete_meeting(self, *, host_account, meeting_id, occurrence_id=None) -> None:
        """Nothing to delete for a provider that made nothing."""

    def start_url(self, *, host_account, meeting_id) -> str:
        """Only providers with ``can_start`` hand out start links."""
        raise NotImplementedError

    def occurrence_id_for(self, *, host_account, meeting_id, starts_at) -> str | None:
        """A provider that can't see Zoom knows no occurrence IDs."""
        return None


class FakeProvider(MeetingProvider):
    """Deterministic stand-in for Zoom, steerable from tests (D17).

    Class-level state so a test can inspect and steer the instance a view created:

    - ``calls`` records each create (including ``wants_recording``, brief 005 criterion 59);
      ``next_error`` makes the next create raise ``ProviderError`` with that message, or raise
      the given ``ProviderError`` instance itself.
    - ``busy`` maps an account pk to the ``BusyTime`` items Zoom "has" for it (none by default);
      ``unavailable`` maps an account pk to the ``ProviderError`` its lookup raises;
      ``not_connected`` holds the pks of accounts treated as not connected; ``delay`` makes each
      lookup sleep, for the preview's deadline.
    - ``busy_calls`` and ``deleted`` record lookups and deletes; ``delete_error`` makes the
      next delete raise that ``ProviderError`` (brief 011's cancel tests).
    - ``start_calls`` records each start-link request, and ``start_error`` makes the next one
      raise that ``ProviderError`` (brief 011, criterion 36).

    ``reset()`` clears all of it. With nothing steered every account is connected and free, so
    brief 005's behaviour is unchanged (criterion 33).
    """

    checks_zoom = True
    can_start = True
    calls: list = []
    next_error = None
    busy: dict = {}
    unavailable: dict = {}
    not_connected: set = set()
    delay: float = 0
    busy_calls: list = []
    deleted: list = []
    delete_error = None
    start_calls: list = []
    start_error = None
    _lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls._lock:
            cls.calls = []
            cls.next_error = None
            cls.busy = {}
            cls.unavailable = {}
            cls.not_connected = set()
            cls.delay = 0
            cls.busy_calls = []
            cls.deleted = []
            cls.delete_error = None
            cls.start_calls = []
            cls.start_error = None

    def is_connected(self, host_account) -> bool:
        return host_account.pk not in type(self).not_connected

    def busy_times(self, *, host_account, start, end) -> list[BusyTime]:
        cls = type(self)
        with cls._lock:
            cls.busy_calls.append(host_account.pk)
            error = cls.unavailable.get(host_account.pk)
            items = list(cls.busy.get(host_account.pk, ()))
        if cls.delay:
            time.sleep(cls.delay)
        if error is not None:
            raise error
        return [item for item in items if item.overlaps(start, end)]

    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        with self._lock:
            error = type(self).next_error
            if error is not None:
                type(self).next_error = None
                raise error if isinstance(error, ProviderError) else ProviderError(error)
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

    def delete_meeting(self, *, host_account, meeting_id, occurrence_id=None) -> None:
        with self._lock:
            error = type(self).delete_error
            if error is not None:
                type(self).delete_error = None
                raise error
            type(self).deleted.append((host_account.pk, meeting_id, occurrence_id))

    def start_url(self, *, host_account, meeting_id) -> str:
        """A start link on the reserved ``.invalid`` TLD, so it can never start a real meeting."""
        with self._lock:
            error = type(self).start_error
            if error is not None:
                type(self).start_error = None
                raise error
            type(self).start_calls.append((host_account.pk, meeting_id))
        return f"https://zoom.example.invalid/s/{meeting_id}"


class ManualProvider(MeetingProvider):
    """IT made the meeting in Zoom by hand; return the details it pasted. Can't see Zoom."""

    needs_manual_details = True

    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        if not manual:
            raise ProviderError("the Zoom link, meeting ID and passcode are missing")
        return Meeting(
            meeting_id=manual["meeting_id"],
            join_url=manual["join_url"],
            passcode=manual.get("passcode", ""),
        )


class ZoomProvider(MeetingProvider):
    """The live Zoom API (brief 006). One ``ZoomClient`` per call, so threads never share one.

    Each call uses its client as a context manager, so the client's connection pool is closed
    when the call ends rather than whenever the garbage collector gets to it.

    The Zoom user is ``HostAccount.email``, used as the ``userId``, never ``me``, which is
    ambiguous for account-level apps (D10). The credential set is the account's
    ``credential_set``, looked up in ``settings.ZOOM_S2S_SECRETS``.
    """

    checks_zoom = True
    can_start = True

    def is_connected(self, host_account) -> bool:
        return host_account.is_zoom_connected()

    @sensitive_variables("credentials")
    def _client(self, host_account):
        credentials = None
        if host_account.credential_set:
            credentials = settings.ZOOM_S2S_SECRETS.get(host_account.credential_set)
        if credentials is None:
            raise ZoomNotConnected()
        return zoom_api.ZoomClient(credentials)

    # Zoom's list carries every meeting's join link: masked in error reports.
    @sensitive_variables("listed", "item", "detail")
    def busy_times(self, *, host_account, start, end) -> list[BusyTime]:
        """The account's dated meetings overlapping ``[start, end)`` (criterion 12, D7).

        The list is every scheduled meeting of the user, up to 10 pages of 300. Each recurring
        meeting (type 8) is read once more (``GET /meetings/{id}``) for its classes, because
        the list doesn't promise to carry every occurrence; deleted classes are skipped. Any
        failure raises, so the caller treats the account as unchecked (fail closed).

        An answer this code can't read (a ``start_time`` that isn't a time, a meeting that
        isn't an object) is ``ZoomUnavailable`` too, raised ``from None`` like every other Zoom
        failure: ``approve()`` and its clean-up catch only ``ProviderError``, so a bare
        ``ValueError`` would be a 500 instead of criterion 28's message (review round 1, SF1).
        """
        with self._client(host_account) as client:
            listed = client.paged(
                zoom_api.user_path(host_account.email, "meetings"),
                {"type": "scheduled", "page_size": LIST_PAGE_SIZE},
                "meetings",
            )
            found, series_ids = [], []
            try:
                for item in listed:
                    kind = item.get("type")
                    if kind == SCHEDULED:
                        found.extend(_single_busy(item))
                    elif kind == RECURRING_FIXED:
                        meeting_id = str(item.get("id", ""))
                        if meeting_id and meeting_id not in series_ids:
                            series_ids.append(meeting_id)
            except UNREADABLE_ANSWER:
                raise ZoomUnavailable() from None
            for meeting_id in series_ids:
                detail = client.get(zoom_api.meeting_path(meeting_id))
                try:
                    found.extend(_series_busy(detail))
                except UNREADABLE_ANSWER:
                    raise ZoomUnavailable() from None
        return [busy for busy in found if busy.overlaps(start, end)]

    # Zoom's answer holds the start_url and the passcode; the local is masked in reports.
    @sensitive_variables("created", "payload")
    def create_meeting(self, *, link_request, host_account, occurrences, manual=None) -> Meeting:
        """One ``POST`` (criteria 22–25). Never repeated by the client (criterion 10).

        An answer that lacks the ID or the link is treated like no answer
        (``ZoomUnavailable``, ``maybe_done``): Zoom may have made the meeting, so the caller
        looks for it by its agenda marker.
        """
        payload = meeting_payload(link_request, occurrences)
        with self._client(host_account) as client:
            created = client.post(zoom_api.user_path(host_account.email, "meetings"), payload)
        meeting_id = created.get("id")
        join_url = created.get("join_url")
        if not meeting_id or not isinstance(join_url, str) or not join_url:
            raise ZoomUnavailable(maybe_done=True)
        try:
            occurrence_ids = tuple(
                (parse_zoom_time(item["start_time"]), str(item["occurrence_id"]))
                for item in created.get("occurrences") or []
                if item.get("status") != "deleted"
            )
        except UNREADABLE_ANSWER:
            # Zoom has made the meeting by now, so this must not raise: no dates means
            # ``approve()`` removes it as DATES_DIFFER (criterion 24; review round 2, SF1).
            occurrence_ids = ()
        return Meeting(
            meeting_id=str(meeting_id),
            join_url=join_url,
            passcode=str(created.get("password") or ""),
            occurrence_ids=occurrence_ids,
            recurring=payload["type"] == RECURRING_FIXED,
        )

    def delete_meeting(self, *, host_account, meeting_id, occurrence_id=None) -> None:
        """``DELETE /meetings/{id}[?occurrence_id=…]``, with none of Zoom's own emails.

        Zoom's reminder and cancellation emails are both switched off (brief 006, D1; brief
        011, criterion 11, D6): the app sends the requester its own email. A ``404`` with code
        3001 (no such meeting) counts as done, so repeating a delete is always safe.
        """
        params = {"schedule_for_reminder": "false", "cancel_meeting_reminder": "false"}
        if occurrence_id:
            params["occurrence_id"] = occurrence_id
        with self._client(host_account) as client:
            client.delete(zoom_api.meeting_path(meeting_id), params)

    # Zoom's answer carries the start_url and the join link: both masked in error reports.
    @sensitive_variables("detail", "url")
    def start_url(self, *, host_account, meeting_id) -> str:
        """A fresh host start link from ``GET /meetings/{id}`` (brief 011, criterion 18).

        It must be ``https`` on ``zoom.us`` or a subdomain of it, or it's ``ZoomUnavailable``:
        the start page redirects to it, so a strange answer must never become an open redirect.
        The URL is returned to the caller only; it's never stored, logged or put in an error.
        """
        with self._client(host_account) as client:
            detail = client.get(zoom_api.meeting_path(meeting_id))
        url = detail.get("start_url")
        if not is_zoom_https_url(url):
            raise ZoomUnavailable()
        return url

    @sensitive_variables("detail")
    def occurrence_id_for(self, *, host_account, meeting_id, starts_at) -> str | None:
        """Zoom's occurrence ID of the class starting at ``starts_at``, or ``None`` (criterion 11).

        Only needed when none was stored (a booking made before the live connection). Deleted
        occurrences are skipped, so ``None`` means Zoom has no such class any more.
        """
        with self._client(host_account) as client:
            detail = client.get(zoom_api.meeting_path(meeting_id))
        try:
            for item in detail.get("occurrences") or []:
                if item.get("status") == "deleted" or not item.get("start_time"):
                    continue
                if parse_zoom_time(item["start_time"]) == starts_at:
                    return str(item["occurrence_id"])
        except UNREADABLE_ANSWER:
            raise ZoomUnavailable() from None
        return None

    def check_connection(self, host_account):
        """Prove the token, the user and the list scope (criterion 36, D12).

        Returns Zoom's user ``type`` (1 Basic, 2 Licensed, …). It can't prove the create and
        delete scopes without making a real meeting; the owner's live check covers those.
        """
        with self._client(host_account) as client:
            user = client.get(zoom_api.user_path(host_account.email))
            client.get(zoom_api.user_path(host_account.email, "meetings"), {"page_size": 1})
        return user.get("type")


@sensitive_variables("item")
def _single_busy(item) -> list[BusyTime]:
    if not item.get("start_time"):
        return []
    start = parse_zoom_time(item["start_time"])
    return [
        BusyTime(
            starts_at=start,
            ends_at=start + timedelta(minutes=_duration(item)),
            topic=str(item.get("topic") or ""),
            meeting_id=str(item.get("id", "")),
            agenda=str(item.get("agenda") or ""),
        )
    ]


@sensitive_variables("detail")
def _series_busy(detail) -> list[BusyTime]:
    topic = str(detail.get("topic") or "")
    agenda = str(detail.get("agenda") or "")
    meeting_id = str(detail.get("id", ""))
    busy = []
    for occurrence in detail.get("occurrences") or []:
        if occurrence.get("status") == "deleted" or not occurrence.get("start_time"):
            continue
        start = parse_zoom_time(occurrence["start_time"])
        minutes = _duration(occurrence, default=_duration(detail))
        busy.append(BusyTime(start, start + timedelta(minutes=minutes), topic, meeting_id, agenda))
    return busy


def _duration(item, default=60) -> int:
    """Minutes. Zoom always sends it; if it didn't, assume its 60-minute default (fail closed)."""
    try:
        minutes = int(item.get("duration") or 0)
    except (TypeError, ValueError):
        minutes = 0
    return minutes if minutes > 0 else default


PROVIDERS = {"fake": FakeProvider, "manual": ManualProvider, "zoom": ZoomProvider}


def get_provider() -> MeetingProvider:
    """The provider named by ``settings.ZOOM_PROVIDER`` (check ``zoom.E002`` validates it)."""
    try:
        return PROVIDERS[settings.ZOOM_PROVIDER]()
    except KeyError:
        raise ImproperlyConfigured(
            f"ZOOM_PROVIDER must be one of {', '.join(PROVIDERS)}."
        ) from None
