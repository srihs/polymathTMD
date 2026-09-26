"""Work that spans several models, the meeting provider or the outside world (briefs 005, 006).

- ``approve()``: the conflict-free booking (brief 005, D5), reordered for the live Zoom
  provider (brief 006, D6). Zoom is asked first, with no lock and no transaction; then one
  transaction locks, re-checks, books and makes the meeting. Every failure leaves the database
  and Zoom consistent: nothing is booked, and a meeting Zoom made is removed again.
- ``availability()``: the detail page's preview. It combines the database clashes with what
  Zoom says, asking Zoom for every account in parallel under a deadline, with a 60-second
  cache (brief 006, D8). It's the one place the two sources are combined.
- ``check_connection()``: the Zoom accounts page's "Check connection", and the
  ``check_zoom_connections`` command (brief 006, D12).
- The confirmation token (D8): signed and expiring, carrying only the request's pk, so no
  token column is needed.
- ``client_ip()`` and ``is_throttled()``: the abuse limits, counted in the database.
- The four emails. They're sent after the model change, synchronously, and a send failure is
  logged and reported but never undoes a decision (D9).

Logging rule for this module (brief 005 criteria 41, 64, 65; brief 006 criterion 11): log
references, account labels, meeting IDs and exception class names only. Never a host key,
join link, passcode, token, credential or exception text.
"""

import hashlib
import ipaddress
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import constants as message_levels
from django.core import signing
from django.core.cache import cache
from django.core.mail import EmailMessage, get_connection
from django.db import IntegrityError, OperationalError, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import (
    HostAccount,
    HostKeyUnreadable,
    HostSlot,
    LinkRequest,
    Occurrence,
    class_date,
    class_time,
)
from .providers import (
    ProviderError,
    ZoomAuthFailed,
    ZoomMissingScope,
    ZoomProvider,
    ZoomUnavailable,
    ZoomUserNotFound,
    get_provider,
)

logger = logging.getLogger(__name__)

REVIEW_PERMISSION = "zoom.review_linkrequest"

CONFIRM_SALT = "apps.zoom.confirm-email"
# The "confirmed" page reuses the token so it can name the reference without a session.
CONFIRMED_PAGE_MAX_AGE = timedelta(days=7)

# MySQL error numbers that mean "another transaction got in the way": deadlock victim and
# lock-wait timeout. A deadlock is retried once; after that both become a friendly "try again"
# conflict, never a 500 (criterion 38). 1062 is the slot backstop (a real clash).
MYSQL_DEADLOCK = 1213
MYSQL_LOCK_WAIT_TIMEOUT = 1205
MYSQL_DUPLICATE_ENTRY = 1062
# A deadlock victim's whole transaction was rolled back, so running it again is safe and
# usually succeeds: the other transaction has finished by then.
APPROVE_ATTEMPTS = 2

# The preview's Zoom lookups (brief 006, criterion 19, D8).
PREVIEW_WORKERS = 6
PREVIEW_DEADLINE_SECONDS = 8
PREVIEW_CACHE_SECONDS = 60

# User-facing copy pinned by the briefs' criteria.
ALREADY_DECIDED = "This request has already been decided."
NOT_OFFERED = "Choose one of the free accounts listed."
BOOKED_A_MOMENT_AGO = (
    "{label} was booked for an overlapping class a moment ago. Choose another free account."
)
# A lock race says nothing about which account was involved, so it doesn't blame one.
APPROVING_AT_THE_SAME_MOMENT = (
    "Someone else was approving at the same moment. Nothing was booked. Try again."
)
HOST_KEY_UNREADABLE = (
    "The host key saved for {label} can't be read. Ask someone in the IT desk to type it again "
    "on the Zoom accounts page, then approve."
)
THROTTLED = (
    "You've sent a lot of requests in the last hour. Wait an hour, then try again, "
    "or phone the IT desk."
)

# Brief 006: approving against Zoom (criteria 24 and 26-31; D23, D25). The next step depends
# on whether waiting can fix the error (``ProviderError.lasting``).
NEXT_STEP_TEMPORARY = "Try again in a few minutes."
NEXT_STEP_LASTING = (
    "Choose another free account, and ask whoever manages the Zoom accounts to press Check "
    "connection for {label}."
)
ZOOM_CLASH = (
    "{label} has a meeting in Zoom at an overlapping time: {topic}, {date} at {time}. "
    "Choose another free account."
)
LOOKUP_FAILED = (
    "We couldn't check {label}'s meetings in Zoom, so nothing was booked. {reason} {next_step}"
)
NOT_CONNECTED = (
    "{label} isn't connected to Zoom yet, so it can't be booked. Choose another free account, "
    "or set up its Zoom connection on the Zoom accounts page."
)
CREATE_FAILED = "We couldn't make the meeting in Zoom: {phrase}. Nothing was booked. {next_step}"
CREATE_MAYBE_MADE = (
    "We couldn't make the meeting in Zoom: no answer from Zoom, so Zoom may have made it "
    "anyway. Nothing was booked here."
)
CLEANUP_REMOVED = (
    " We found it in {label}'s Zoom account and removed it. Try again in a few minutes."
)
CLEANUP_NOT_FOUND = (
    " We didn't find it in {label}'s Zoom account. Try again in a few minutes. If it turns up "
    "there later, the next try removes it before making a new one."
)
CLEANUP_FAILED = (
    " We couldn't check {label}'s Zoom account for it. Try again in a few minutes. If a "
    "meeting for {reference} is there, the next try removes it before making a new one."
)
DATES_DIFFER = (
    "Zoom scheduled different dates from this request, so the meeting was removed from Zoom "
    "and nothing was booked. Tell whoever looks after the system."
)
ORPHANED = (
    "Zoom made meeting {meeting_id} on {label}, but it couldn't be saved here or removed from "
    "Zoom. Delete that meeting in Zoom, then try again."
)

# Brief 006, criterion 36: "Check connection".
CHECK_WORKS = "The Zoom connection works for {label}."
CHECK_BASIC_USER = (
    "The Zoom connection works for {label}, but Zoom says {email} is a Basic (free) user. Free "
    "users' meetings end after 40 minutes. Untick Paid account, or ask the Zoom account owner "
    "to give this user a licence."
)
CHECK_NO_NAME = "{label} has no Zoom connection name yet. Type it in, save, then check again."
CHECK_NOT_ON_SERVER = (
    "The server has no Zoom connection called {slug}. Ask whoever looks after the server to add "
    "it, then check again."
)
CHECK_AUTH_FAILED = (
    "Zoom didn't accept the connection details called {slug}. Check the account ID, client ID "
    "and client secret on the server, and that the Zoom app is activated."
)
CHECK_MISSING_SCOPE = (
    "The Zoom app for {slug} is missing a permission. Add the scopes listed in the README, then "
    "check again."
)
CHECK_USER_NOT_FOUND = (
    "The connection works, but that Zoom account has no user {email}. Check the Zoom sign-in email."
)
CHECK_TEMPORARY = "Couldn't check {label} with Zoom: {phrase}. Try again in a few minutes."
CHECK_LASTING = (
    "Couldn't check {label} with Zoom: {phrase}. Waiting won't fix this. Tell whoever looks "
    "after the server, and give them the Zoom error number."
)
ZOOM_BASIC_USER = 1  # Zoom's user type for a Basic (free) user


def next_step(error, label) -> str:
    """ "Try again in a few minutes." only when waiting can help (D23)."""
    return NEXT_STEP_LASTING.format(label=label) if error.lasting else NEXT_STEP_TEMPORARY


def lookup_failed_message(error, label) -> str:
    """Criterion 28's message, also used when removing a leftover fails (criterion 27)."""
    return LOOKUP_FAILED.format(
        label=label, reason=error.reason_sentence, next_step=next_step(error, label)
    )


def create_failed_message(error, label) -> str:
    """Criterion 30(a): Zoom certainly made nothing (D25)."""
    return CREATE_FAILED.format(phrase=error.user_message, next_step=next_step(error, label))


class Outcome(StrEnum):
    APPROVED = "approved"
    CONFLICT = "conflict"
    ALREADY_DECIDED = "already_decided"
    STARTED = "started"
    HOST_KEY_UNREADABLE = "host_key_unreadable"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True)
class ApproveResult:
    """What ``approve()`` did. ``host_key`` is set only on success, in memory, for the email."""

    outcome: Outcome
    message: str = ""
    link_request: LinkRequest | None = None
    host_key: str = field(default="", repr=False)


# --------------------------------------------------------------------------- Zoom clashes


def class_window(occurrences):
    """``(first start, last end)`` of a request's classes: the span Zoom is asked about."""
    return (
        min(occurrence.starts_at for occurrence in occurrences),
        max(occurrence.ends_at for occurrence in occurrences),
    )


def known_meeting_ids(accounts, window) -> dict:
    """``{account pk: {meeting ID, …}}`` of approved requests with a class in ``window``.

    A Zoom meeting the app booked itself is already reported by the database check, so it's
    left out of the Zoom clashes rather than shown twice (criterion 13). One query, whatever
    the number of accounts or Zoom meetings (criterion 20).
    """
    start, end = window
    rows = (
        LinkRequest.objects.filter(
            status=LinkRequest.Status.APPROVED,
            host_account__in=accounts,
            occurrences__starts_at__lt=end,
            occurrences__ends_at__gt=start,
        )
        .exclude(meeting_id="")
        .values_list("host_account_id", "meeting_id")
        .distinct()
    )
    known = defaultdict(set)
    for account_id, meeting_id in rows:
        known[account_id].add(meeting_id)
    return known


def zoom_clashes(link_request, occurrences, busy_times, known_ids) -> list[dict]:
    """``[{occurrence, busy}, …]``: this request's classes that overlap a Zoom meeting.

    Left out (criterion 13): meetings the app booked (``known_ids``) and meetings carrying
    **this** request's marker (leftovers of a failed attempt, which ``approve()`` removes).
    Another request's marker is an ordinary clash. Sorted by the class, then the Zoom
    meeting's start (G2).
    """
    found = [
        {"occurrence": occurrence, "busy": busy}
        for busy in busy_times
        if busy.meeting_id not in known_ids and not link_request.agenda_has_marker(busy.agenda)
        for occurrence in occurrences
        if busy.overlaps(occurrence.starts_at, occurrence.ends_at)
    ]
    return sorted(found, key=lambda c: (c["occurrence"].starts_at, c["busy"].starts_at))


def _preview_key(account, window) -> str:
    """Keyed by the account, its Zoom user and connection name, and the request's window.

    The email and connection name are part of the key so that changing either on the accounts
    page makes the next load ask Zoom again. Hashed to keep the key short and cache-safe.
    """
    start, end = window
    raw = "|".join(
        [str(account.pk), account.email, account.credential_set, start.isoformat(), end.isoformat()]
    )
    return "zoom:preview:" + hashlib.sha256(raw.encode()).hexdigest()


def remember_preview(account, window, busy_times) -> None:
    """Keep a fresh Zoom answer for the preview: busy times and topics only, never a token.

    The cache is Django's default, LocMem: one per process, so each Gunicorn worker keeps its
    own 60-second answers. Two page loads served by different workers can each ask Zoom; that
    costs a few extra list calls, never a stale booking, because ``approve()`` never reads it.
    """
    cache.set(
        _preview_key(account, window),
        (timezone.now(), tuple(busy_times)),
        PREVIEW_CACHE_SECONDS,
    )


def forget_preview(account, window) -> None:
    cache.delete(_preview_key(account, window))


def _cached_preview(account, window):
    """``(checked_at, busy_times)`` if Zoom was asked less than 60 seconds ago, else ``None``.

    The age is also checked against the app's clock, not only the cache's own expiry, so the
    60 seconds are the same "now" the rest of the page uses.
    """
    value = cache.get(_preview_key(account, window))
    if value is None:
        return None
    checked_at, busy_times = value
    if timezone.now() - checked_at >= timedelta(seconds=PREVIEW_CACHE_SECONDS):
        return None
    return checked_at, list(busy_times)


def _ask_zoom(accounts, window, provider) -> dict:
    """``{pk: (checked_at, busy_times) or ProviderError}`` for each account (criterion 19, D8).

    Cached answers are used as they are; the rest are asked in parallel, at most
    ``PREVIEW_WORKERS`` at a time, with one overall deadline. An account with no answer by
    then is ``ZoomUnavailable`` (fail closed). The worker threads touch no database: they get
    loaded account objects and call only the provider. Errors are never cached, so a reload
    asks again. Leaving the ``with`` doesn't wait for a late thread: it finishes on its own,
    and its answer is dropped.
    """
    start, end = window
    results, pending = {}, []
    for account in accounts:
        cached = _cached_preview(account, window)
        if cached is None:
            pending.append(account)
        else:
            results[account.pk] = cached
    if not pending:
        return results

    executor = ThreadPoolExecutor(
        max_workers=min(PREVIEW_WORKERS, len(pending)), thread_name_prefix="zoom-preview"
    )
    try:
        futures = {
            executor.submit(provider.busy_times, host_account=account, start=start, end=end): (
                account
            )
            for account in pending
        }
        done, _ = wait(futures, timeout=PREVIEW_DEADLINE_SECONDS)
        for future, account in futures.items():
            if future not in done:
                results[account.pk] = ZoomUnavailable()
                continue
            try:
                busy_times = future.result()
            except ProviderError as exc:
                logger.warning("Couldn't check %s with Zoom: %s", account.label, type(exc).__name__)
                results[account.pk] = exc
                continue
            except Exception as exc:  # fail closed: an unreadable answer is "not checked"
                logger.error("Checking %s with Zoom failed: %s", account.label, type(exc).__name__)
                results[account.pk] = ZoomUnavailable()
                continue
            remember_preview(account, window, busy_times)
            results[account.pk] = (timezone.now(), list(busy_times))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return results


@dataclass(frozen=True)
class Availability:
    """The preview for one request: the context contract's ``availability`` and friends."""

    entries: list
    checks_zoom: bool
    zoom_checked_at: datetime | None
    all_unchecked: bool

    @property
    def free_accounts(self) -> list:
        return [entry["account"] for entry in self.entries if entry["is_free"]]


def availability(link_request, occurrences, *, provider=None, account_edit_allowed=False):
    """Each bookable account's state for this request's classes (criteria 15–19; D8).

    The database side is ``HostAccount.objects.availability_for()``, unchanged. With a
    provider that ``checks_zoom``, each account is also ``checked`` (Zoom answered),
    ``unavailable`` (it couldn't be asked) or ``not_connected`` (no HTTP made), and only a
    ``checked`` account with no clash of either kind is offered. With ``manual`` every entry is
    ``off`` and nothing is sent anywhere (criterion 18).

    ``account_edit_allowed`` is the viewer's ``zoom.change_hostaccount``; it's copied onto every
    entry for the fix links (G1). Call this outside a transaction: it waits on HTTP.
    """
    provider = provider or get_provider()
    occurrences = list(occurrences)
    database = HostAccount.objects.availability_for(occurrences)
    checks_zoom = bool(provider.checks_zoom)
    asking = checks_zoom and bool(database) and bool(occurrences)

    answers, known = {}, {}
    if asking:
        window = class_window(occurrences)
        connected = [account for account, _ in database if provider.is_connected(account)]
        answers = _ask_zoom(connected, window, provider)
        known = known_meeting_ids([account for account, _ in database], window)

    entries, checked_times = [], []
    for account, clashes in database:
        state, found, problem = "off", [], ""
        if asking:
            answer = answers.get(account.pk)
            if answer is None:
                state = "not_connected"
            elif isinstance(answer, ProviderError):
                state, problem = "unavailable", answer.reason_sentence
            else:
                checked_at, busy_times = answer
                state = "checked"
                checked_times.append(checked_at)
                found = zoom_clashes(
                    link_request, occurrences, busy_times, known.get(account.pk, set())
                )
        entries.append(
            {
                "account": account,
                "is_free": state in ("checked", "off") and not clashes and not found,
                "has_host_key": account.has_host_key,
                # Classes of this request that clash, not clash pairs (brief 005, D22, G4).
                "busy_count": len(
                    {occurrence.pk for occurrence, _ in clashes}
                    | {clash["occurrence"].pk for clash in found}
                ),
                "clashes": [
                    {"occurrence": occurrence, "other": other} for occurrence, other in clashes
                ],
                "zoom_clashes": found,
                "zoom_state": state,
                "zoom_problem": problem,
                "account_edit_allowed": bool(account_edit_allowed),
            }
        )
    return Availability(
        entries=entries,
        checks_zoom=checks_zoom,
        zoom_checked_at=min(checked_times) if checked_times else None,
        all_unchecked=asking
        and all(entry["zoom_state"] in ("unavailable", "not_connected") for entry in entries),
    )


# --------------------------------------------------------------------------- Approval


def approve(link_request_id, *, account_id, by, manual=None, provider=None) -> ApproveResult:
    """Book ``account_id`` for every class of the request and make the meeting (D5; 006 D6).

    Per attempt:

    1. **No locks, no transaction** (only when the provider ``checks_zoom``): read the
       request, its classes and the account; refuse an account that isn't connected; ask Zoom
       for the account's meetings across the request's window, fresh, never from the preview
       cache. A Zoom clash or a failed lookup stops here. This request's own leftovers from a
       failed attempt are deleted from Zoom. This is the slow part, so it runs before any lock.
    2. **One transaction**: lock the request, then the account; re-check the status, the
       start and the account; decrypt the host key; re-check database clashes with a locking
       read; book the classes and insert the 5-minute slots (the unique slot index is the
       backstop).
    3. **Still inside it, one create call.** Then check a weekly meeting's dates, store Zoom's
       occurrence IDs, save the request and commit.
    4. **After a failure**, outside the rolled-back transaction: a meeting Zoom made is
       deleted again; a create with no answer gets one best-effort clean-up by agenda marker.

    Why step 3 holds locks (D6): one ``POST`` with timeouts, on two rows plus this request's
    classes, is cheaper and has fewer ways to fail than a reservation state with a sweeper.

    Emails are the caller's job, after this returns, so a mail failure can never undo a
    booking. Call it outside any open transaction (the approve view is ``non_atomic_requests``):
    a MySQL deadlock rolls back the whole transaction, not just a savepoint, and step 1 makes
    HTTP calls that must not hold a transaction open.

    A deadlock (MySQL 1213) is retried once, because MySQL already rolled the attempt back and
    the other transaction has usually finished; a second deadlock or a lock-wait timeout (1205)
    returns ``conflict`` with ``APPROVING_AT_THE_SAME_MOMENT``. A retry after Zoom made a
    meeting is safe: that meeting was deleted before the retry (criterion 31).
    """
    provider = provider or get_provider()
    reference = LinkRequest(pk=link_request_id).reference
    for attempt in range(1, APPROVE_ATTEMPTS + 1):
        try:
            if provider.checks_zoom:
                stopped = _check_zoom_first(link_request_id, account_id, provider)
                if stopped is not None:
                    return stopped
            return _approve_once(
                link_request_id, account_id=account_id, by=by, manual=manual, provider=provider
            )
        except OperationalError as exc:
            code = _mysql_code(exc)
            if code not in (MYSQL_DEADLOCK, MYSQL_LOCK_WAIT_TIMEOUT):
                raise
            if code == MYSQL_DEADLOCK and attempt < APPROVE_ATTEMPTS:
                logger.warning("Approving %s hit a deadlock; trying once more.", reference)
                continue
            logger.warning("Approving %s lost a lock race (MySQL %s).", reference, code)
            return ApproveResult(Outcome.CONFLICT, APPROVING_AT_THE_SAME_MOMENT)
    raise AssertionError("unreachable: every attempt returns or raises")


def _wait_for_other_attempts(link_request_id):
    """``(status, meeting_id)`` read under the request's row lock, which is released at once.

    An attempt at approving this request holds that lock from before its create call until
    it commits or rolls back. Waiting for the lock therefore means any meeting Zoom listed
    before this call was made by an attempt that has *finished*: if the request is still
    waiting, that meeting is a true leftover and safe to delete; if it's approved, the stored
    meeting ID is the one to keep. No HTTP call is made while the lock is held.
    """
    with transaction.atomic():
        return (
            LinkRequest.objects.select_for_update()
            .filter(pk=link_request_id)
            .values_list("status", "meeting_id")
            .get()
        )


def _check_zoom_first(link_request_id, account_id, provider):
    """Step 1 of ``approve()``: an ``ApproveResult`` that ends the attempt, or ``None``."""
    link_request = LinkRequest.objects.get(pk=link_request_id)
    if not link_request.can_be_decided():
        return ApproveResult(Outcome.ALREADY_DECIDED, ALREADY_DECIDED, link_request)
    if link_request.has_started():
        return ApproveResult(Outcome.STARTED, link_request=link_request)
    account = HostAccount.objects.bookable().filter(pk=account_id).first()
    if account is None:
        return ApproveResult(Outcome.CONFLICT, NOT_OFFERED, link_request)
    label = account.label
    if not provider.is_connected(account):
        return ApproveResult(Outcome.CONFLICT, NOT_CONNECTED.format(label=label), link_request)

    occurrences = list(link_request.occurrences.all())
    window = class_window(occurrences)
    try:
        busy_times = provider.busy_times(host_account=account, start=window[0], end=window[1])
    except ProviderError as exc:
        forget_preview(account, window)
        logger.warning(
            "Couldn't check %s in Zoom for %s: %s",
            label,
            link_request.reference,
            type(exc).__name__,
        )
        return ApproveResult(
            Outcome.PROVIDER_ERROR, lookup_failed_message(exc, label), link_request
        )
    # A fresh answer is the best preview there is: the re-render after a clash shows it.
    remember_preview(account, window, busy_times)

    known = known_meeting_ids([account], window).get(account.pk, set())
    clashes = zoom_clashes(link_request, occurrences, busy_times, known)
    if clashes:
        busy = clashes[0]["busy"]
        return ApproveResult(
            Outcome.CONFLICT,
            ZOOM_CLASH.format(
                label=label,
                topic=busy.display_topic,
                date=class_date(busy.starts_at),
                time=class_time(busy.starts_at),
            ),
            link_request,
        )

    leftovers = sorted(
        {busy.meeting_id for busy in busy_times if link_request.agenda_has_marker(busy.agenda)}
    )
    if leftovers:
        status, _ = _wait_for_other_attempts(link_request.pk)
        if status != LinkRequest.Status.WAITING:
            return ApproveResult(Outcome.ALREADY_DECIDED, ALREADY_DECIDED, link_request)
        try:
            for meeting_id in leftovers:
                provider.delete_meeting(host_account=account, meeting_id=meeting_id)
        except ProviderError as exc:
            forget_preview(account, window)
            logger.warning(
                "Couldn't remove a leftover Zoom meeting for %s on %s: %s",
                link_request.reference,
                label,
                type(exc).__name__,
            )
            return ApproveResult(
                Outcome.PROVIDER_ERROR, lookup_failed_message(exc, label), link_request
            )
        forget_preview(account, window)
        logger.warning(
            "Removed %s leftover Zoom meeting(s) for %s on %s before approving.",
            len(leftovers),
            link_request.reference,
            label,
        )
    return None


class _DatesDiffer(Exception):
    """Zoom's series doesn't match the stored classes (criterion 24); rolls the booking back."""


def _store_occurrence_ids(occurrences, meeting) -> None:
    """Match Zoom's classes to ours by start time, or raise ``_DatesDiffer`` (criterion 23)."""
    ours = sorted(occurrence.starts_at for occurrence in occurrences)
    theirs = sorted(start for start, _ in meeting.occurrence_ids)
    if ours != theirs:
        raise _DatesDiffer()
    by_start = dict(meeting.occurrence_ids)
    for occurrence in occurrences:
        occurrence.zoom_occurrence_id = by_start[occurrence.starts_at]
    Occurrence.objects.bulk_update(occurrences, ["zoom_occurrence_id"])


# host_key is decrypted here: keep it out of error reports (tracebacks, ADMINS error emails).
@sensitive_variables("host_key")
def _approve_once(link_request_id, *, account_id, by, manual, provider) -> ApproveResult:
    """Steps 2–4 of one attempt; MySQL lock errors propagate so the caller can retry.

    Accepted trade-off (review round 1, nit): if the COMMIT itself fails ambiguously, say
    the connection drops mid-commit (MySQL 2013), the server may have committed after all.
    This code can't tell, treats it like any failure after the create and deletes the meeting,
    so the request can end up approved with no meeting behind it (and no link email, since
    IT sees an error, not an approval). The alternative, keeping the meeting, would leave an
    orphan in Zoom on every real rollback, which is the far commoner case. This outcome needs
    a lost connection at the exact moment of COMMIT, and it isn't silent: IT sees the error,
    the request's page shows it approved, and the log names the removed meeting's ID.
    """
    reference = LinkRequest(pk=link_request_id).reference
    label = ""
    account = None
    occurrences = []
    made = None  # the meeting Zoom made in this attempt, until it's saved
    try:
        with transaction.atomic():
            link_request = LinkRequest.objects.select_for_update().get(pk=link_request_id)
            if not link_request.can_be_decided():
                return ApproveResult(Outcome.ALREADY_DECIDED, ALREADY_DECIDED, link_request)
            if link_request.has_started():
                # No message: the detail page shows its own started notice (from has_started).
                return ApproveResult(Outcome.STARTED, link_request=link_request)

            account = (
                HostAccount.objects.select_for_update().bookable().filter(pk=account_id).first()
            )
            if account is None:
                return ApproveResult(Outcome.CONFLICT, NOT_OFFERED, link_request)
            label = account.label
            if not provider.is_connected(account):
                return ApproveResult(
                    Outcome.CONFLICT, NOT_CONNECTED.format(label=label), link_request
                )
            host_key = account.get_host_key()

            occurrences = list(link_request.occurrences.select_for_update())
            [(_, clashes)] = HostAccount.objects.filter(pk=account.pk).availability_for(
                occurrences, lock=True
            )
            if clashes:
                return ApproveResult(
                    Outcome.CONFLICT, BOOKED_A_MOMENT_AGO.format(label=label), link_request
                )

            Occurrence.objects.filter(link_request=link_request).update(host_account=account)
            for occurrence in occurrences:
                occurrence.host_account = account
            HostSlot.objects.bulk_create(
                slot
                for occurrence in occurrences
                for slot in HostSlot.covering(occurrence, account)
            )

            made = provider.create_meeting(
                link_request=link_request,
                host_account=account,
                occurrences=occurrences,
                manual=manual,
            )
            if made.recurring:
                _store_occurrence_ids(occurrences, made)
            link_request.status = LinkRequest.Status.APPROVED
            link_request.host_account = account
            link_request.decided_by = by
            link_request.decided_at = timezone.now()
            link_request.meeting_id = made.meeting_id
            link_request.join_url = made.join_url
            link_request.passcode = made.passcode
            link_request.save(
                update_fields=[
                    "status",
                    "host_account",
                    "decided_by",
                    "decided_at",
                    "meeting_id",
                    "join_url",
                    "passcode",
                ]
            )
    except HostKeyUnreadable:
        logger.error("Host key for %s can't be read: InvalidToken", label)
        return ApproveResult(Outcome.HOST_KEY_UNREADABLE, HOST_KEY_UNREADABLE.format(label=label))
    except ProviderError as exc:
        # The create call failed, so ``made`` is None: nothing to compensate.
        return _create_failed(exc, link_request_id, account, occurrences, provider)
    except _DatesDiffer as exc:
        orphaned = _remove_made_meeting(provider, account, made, reference, label, exc)
        if orphaned is not None:
            return orphaned
        logger.warning(
            "Zoom's dates for %s differed; meeting %s removed.", reference, made.meeting_id
        )
        return ApproveResult(Outcome.PROVIDER_ERROR, DATES_DIFFER)
    except Exception as exc:
        if made is not None:
            orphaned = _remove_made_meeting(provider, account, made, reference, label, exc)
            if orphaned is not None:
                return orphaned
        if isinstance(exc, IntegrityError) and _mysql_code(exc) == MYSQL_DUPLICATE_ENTRY:
            logger.warning("Approving %s hit the slot backstop; another booking won.", reference)
            return ApproveResult(Outcome.CONFLICT, BOOKED_A_MOMENT_AGO.format(label=label))
        raise
    return ApproveResult(
        Outcome.APPROVED,
        f"Approved. The link was emailed to {link_request.requester_email}.",
        link_request,
        host_key,
    )


def _remove_made_meeting(provider, account, meeting, reference, label, cause):
    """The compensating delete (criterion 31), run after the rollback.

    Returns ``None`` when the meeting is gone, so the caller reports the original failure as
    usual (and a deadlock can be retried). If the delete fails too, the meeting is orphaned in
    Zoom: one ERROR record names the reference, the account, the meeting ID and the class of
    the failure that stopped the save, and the result tells IT exactly what to delete. An
    orphan that stays only makes the account look busy; it can't cause a double booking.
    """
    try:
        provider.delete_meeting(host_account=account, meeting_id=meeting.meeting_id)
    except ProviderError:
        logger.error(
            "Zoom meeting %s on %s for %s couldn't be saved or removed: %s",
            meeting.meeting_id,
            label,
            reference,
            type(cause).__name__,
        )
        return ApproveResult(
            Outcome.PROVIDER_ERROR, ORPHANED.format(meeting_id=meeting.meeting_id, label=label)
        )
    logger.warning(
        "Removed Zoom meeting %s on %s: saving %s failed with %s.",
        meeting.meeting_id,
        label,
        reference,
        type(cause).__name__,
    )
    return None


def _create_failed(error, link_request_id, account, occurrences, provider) -> ApproveResult:
    """Criterion 30: the create call raised, and the booking was rolled back (D25).

    If the request may have reached Zoom (``maybe_done``: a read timeout, a dropped connection
    or a 5xx), Zoom may have made the meeting anyway. One best-effort clean-up follows: list
    the account's meetings, then delete every one carrying this request's marker, after
    waiting out any other attempt at this request (``_wait_for_other_attempts``). The message
    then says what that clean-up actually found. Otherwise Zoom certainly made nothing.
    """
    reference = LinkRequest(pk=link_request_id).reference
    label = account.label if account is not None else ""
    logger.warning(
        "The meeting provider failed for %s; nothing was booked: %s",
        reference,
        type(error).__name__,
    )
    if account is not None and occurrences:
        forget_preview(account, class_window(occurrences))
    if not error.maybe_done or account is None or not occurrences:
        return ApproveResult(Outcome.PROVIDER_ERROR, create_failed_message(error, label))

    link_request = LinkRequest(pk=link_request_id)
    window = class_window(occurrences)
    try:
        busy_times = provider.busy_times(host_account=account, start=window[0], end=window[1])
        marked = sorted(
            {busy.meeting_id for busy in busy_times if link_request.agenda_has_marker(busy.agenda)}
        )
        removed = 0
        if marked:
            status, kept = _wait_for_other_attempts(link_request_id)
            for meeting_id in marked:
                if status == LinkRequest.Status.APPROVED and meeting_id == kept:
                    continue
                provider.delete_meeting(host_account=account, meeting_id=meeting_id)
                removed += 1
    except ProviderError as exc:
        logger.warning(
            "Couldn't clean up Zoom for %s on %s: %s", reference, label, type(exc).__name__
        )
        ending = CLEANUP_FAILED.format(label=label, reference=reference)
    else:
        ending = (CLEANUP_REMOVED if removed else CLEANUP_NOT_FOUND).format(label=label)
    return ApproveResult(Outcome.PROVIDER_ERROR, CREATE_MAYBE_MADE + ending)


# --------------------------------------------------------------------------- Check connection


@dataclass(frozen=True)
class ConnectionResult:
    """A ``django.contrib.messages`` level and criterion 36's message. Nothing is stored."""

    level: int
    message: str

    @property
    def works(self) -> bool:
        return self.level == message_levels.SUCCESS


def check_connection(account, provider=None) -> ConnectionResult:
    """Does this account's Zoom connection work? (criterion 36, D12).

    Always the live ``ZoomProvider``, whatever ``ZOOM_PROVIDER`` says, so a connection can be
    proved before switching the site over. With no name, or a name the server doesn't have,
    nothing is sent anywhere. The messages name the account, its email and the connection
    name, never a credential or a token.
    """
    provider = provider or ZoomProvider()
    label, slug, email = account.label, account.credential_set, account.email
    error = message_levels.ERROR
    state = account.zoom_connection_state
    if state == "none":
        return ConnectionResult(error, CHECK_NO_NAME.format(label=label))
    if state == "missing":
        return ConnectionResult(error, CHECK_NOT_ON_SERVER.format(slug=slug))
    try:
        user_type = provider.check_connection(account)
    except ZoomAuthFailed:
        return ConnectionResult(error, CHECK_AUTH_FAILED.format(slug=slug))
    except ZoomMissingScope:
        return ConnectionResult(error, CHECK_MISSING_SCOPE.format(slug=slug))
    except ZoomUserNotFound:
        return ConnectionResult(error, CHECK_USER_NOT_FOUND.format(email=email))
    except ProviderError as exc:
        # ZoomUnavailable and ZoomBusy are temporary; ZoomRejected is the lasting one here.
        template = CHECK_LASTING if exc.lasting else CHECK_TEMPORARY
        return ConnectionResult(error, template.format(label=label, phrase=exc.user_message))
    if user_type == ZOOM_BASIC_USER and account.is_paid:
        return ConnectionResult(
            message_levels.WARNING, CHECK_BASIC_USER.format(label=label, email=email)
        )
    return ConnectionResult(message_levels.SUCCESS, CHECK_WORKS.format(label=label))


def _mysql_code(exc):
    return exc.args[0] if exc.args and isinstance(exc.args[0], int) else None


# --------------------------------------------------------------------------- Email confirmation


def confirm_token(link_request) -> str:
    """A signed token carrying only the pk, with a salt used for nothing else (criterion 13)."""
    return signing.dumps(link_request.pk, salt=CONFIRM_SALT)


def _link_request_from_token(token, max_age):
    """The request a token names; raises ``signing.BadSignature`` / ``SignatureExpired``."""
    pk = signing.loads(token, salt=CONFIRM_SALT, max_age=max_age)
    if not isinstance(pk, int):
        raise signing.BadSignature("Unexpected payload.")
    return LinkRequest.objects.filter(pk=pk).first()


def confirm_state(token):
    """``(state, link_request)`` for the confirm page: ready, already, expired or invalid.

    Reading a token never changes anything, so mail scanners that prefetch links confirm
    nothing (D8): only the page's POST calls ``mark_verified()``.
    """
    try:
        link_request = _link_request_from_token(
            token, timedelta(hours=settings.ZOOM_CONFIRM_LINK_HOURS)
        )
    except signing.SignatureExpired:
        return "expired", None
    except signing.BadSignature:
        return "invalid", None
    if link_request is None:
        return "invalid", None
    if link_request.status != LinkRequest.Status.UNVERIFIED:
        return "already", link_request
    return "ready", link_request


def confirmed_link_request(token):
    """The confirmed request a "confirmed" page token names, or ``None`` (then a 404)."""
    try:
        link_request = _link_request_from_token(token, CONFIRMED_PAGE_MAX_AGE)
    except signing.BadSignature:
        return None
    if link_request is None or link_request.status == LinkRequest.Status.UNVERIFIED:
        return None
    return link_request


# --------------------------------------------------------------------------- Abuse limits


def client_ip(request):
    """The visitor's IP, trusting ``X-Forwarded-For`` only as far as ``TRUSTED_PROXY_COUNT``.

    Each trusted proxy appends the address it received the request from, so with N proxies
    the client's address is the N-th entry from the right; anything further left was typed by
    the client and can be forged. With 0 proxies, or too few entries, ``REMOTE_ADDR`` is the
    only trustworthy value (criterion 11).
    """
    remote = request.META.get("REMOTE_ADDR") or None
    proxies = settings.TRUSTED_PROXY_COUNT
    if proxies <= 0:
        return remote
    entries = [part.strip() for part in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")]
    entries = [part for part in entries if part]
    if len(entries) < proxies:
        return remote
    candidate = entries[-proxies]
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return remote
    return candidate


def is_throttled(*, email, ip) -> bool:
    """True when this email or IP already sent the hourly maximum of requests (criterion 10).

    Known, accepted race: this counts, then the view inserts, with no lock in between, so a
    burst of simultaneous submits from one address can each see ``limit - 1`` and all get
    through (at most one extra per concurrent request). Closing it would need a lock or a
    counter table for a limit whose job is to slow down abuse, not to be exact. Honeypot hits
    store nothing, so they never count.
    """
    recent = LinkRequest.objects.recent_from
    if recent(email=email).count() >= settings.ZOOM_REQUEST_LIMIT_PER_EMAIL_PER_HOUR:
        return True
    return bool(ip) and recent(ip=ip).count() >= settings.ZOOM_REQUEST_LIMIT_PER_IP_PER_HOUR


# --------------------------------------------------------------------------- Emails


@sensitive_variables("context", "body")
def _send(kind, template, context, recipients, link_request) -> bool:
    """Render a plain-text email pair and send one message per recipient.

    One message each, so IT staff don't see each other's addresses and a requester's email
    never carries anyone else's. Plain text only: no ``html_message``, and the ``.txt``
    templates turn autoescaping off so a class name reads exactly as typed (criterion 12).
    Returns False, after logging the reference and the exception class only, on failure.
    """
    try:
        subject_lines = render_to_string(f"zoom/email/{template}_subject.txt", context)
        subject = " ".join(line.strip() for line in subject_lines.splitlines() if line.strip())
        body = render_to_string(f"zoom/email/{template}_body.txt", context).strip() + "\n"
        connection = get_connection()
        connection.send_messages(
            [
                EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
                for recipient in recipients
            ]
        )
    except Exception as exc:  # any backend or rendering failure; the decision stands
        logger.error(
            "The %s email for %s didn't send: %s", kind, link_request.reference, type(exc).__name__
        )
        return False
    return True


def send_confirm_email(request, link_request) -> bool:
    """Ask the requester to confirm their address (to the requester only)."""
    context = {
        "link_request": link_request,
        "occurrences": list(link_request.occurrences.all()),
        "confirm_url": request.build_absolute_uri(
            reverse("zoom:confirm", args=[confirm_token(link_request)])
        ),
        "link_hours": settings.ZOOM_CONFIRM_LINK_HOURS,
    }
    return _send("confirm", "confirm", context, [link_request.requester_email], link_request)


def it_recipients():
    """Every active holder of the review permission, superusers included (D9)."""
    users = get_user_model().objects.with_perm(
        REVIEW_PERMISSION, is_active=True, include_superusers=True
    )
    return sorted({user.email for user in users if user.email})


def send_it_new_request_email(request, link_request) -> bool:
    """Tell IT a confirmed request is waiting. No email when nobody holds the permission."""
    recipients = it_recipients()
    if not recipients:
        logger.warning(
            "Nobody can review %s: no active user has %s.",
            link_request.reference,
            REVIEW_PERMISSION,
        )
        return False
    context = {
        "link_request": link_request,
        "occurrences": list(link_request.occurrences.all()),
        "detail_url": request.build_absolute_uri(reverse("zoom:detail", args=[link_request.pk])),
    }
    return _send("new request", "it_new", context, recipients, link_request)


@sensitive_variables("host_key", "context")
def send_approved_email(request, link_request, host_key) -> bool:
    """The link and the host key, to the verified requester only: no cc, no bcc (D17).

    The only email that receives a host key. ``host_key`` comes from ``approve()`` and is
    never stored or logged on the way.
    """
    context = {
        "link_request": link_request,
        "occurrences": list(link_request.occurrences.all()),
        "host_key": host_key,
    }
    return _send("approval", "approved", context, [link_request.requester_email], link_request)


def send_rejected_email(request, link_request) -> bool:
    """The reason, and where to send a new request."""
    context = {
        "link_request": link_request,
        "request_url": request.build_absolute_uri(reverse("zoom:request")),
    }
    return _send("not approved", "rejected", context, [link_request.requester_email], link_request)
