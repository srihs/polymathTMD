"""Work that spans several models, the meeting provider or the outside world (briefs 005, 006,
011).

- ``approve()``: the conflict-free booking (brief 005, D5), reordered for the live Zoom
  provider (brief 006, D6). Zoom is asked first, with no lock and no transaction; then one
  transaction locks, re-checks, books and makes the meeting. Every failure leaves the database
  and Zoom consistent: nothing is booked, and a meeting Zoom made is removed again.
- ``availability()``: the detail page's preview. It combines the database clashes with what
  Zoom says, asking Zoom for every account in parallel under a deadline, with a 60-second
  cache (brief 006, D8). It's the one place the two sources are combined.
- ``check_connection()``: the Zoom accounts page's "Check connection", and the
  ``check_zoom_connections`` command (brief 006, D12). From brief 015 the credentials it
  proves are the account's ``ZoomConnection`` row, read as the check runs, so a detail saved
  on the Zoom connections page is checked at once, with no restart.
- ``connection_saved_message()``: the Zoom connections pages' success flash (brief 015).
- The confirmation token (D8): signed and expiring, carrying only the request's pk, so no
  token column is needed.
- ``client_ip()`` and ``is_throttled()``: the abuse limits, counted in the database.
- ``cancel()`` (brief 011, D2): cancel a whole booking or one class. It locks the request,
  then its account, then its classes, writes the cancellation, deletes in Zoom *inside* the
  transaction, then commits, so a Zoom refusal rolls everything back and a later
  ``meeting.deleted`` webhook (brief 013) finds the database already matching Zoom.
- The start link (brief 011, D4): a signed token per booking, the start page's state, and
  ``start_class()``, which asks Zoom for a fresh host ``start_url`` and hands it to the view
  only. The URL is never stored, logged or emailed; each use is logged.
- ``reveal_host_key()`` (brief 011, D11): the one place a host key is decrypted for showing,
  recorded every time. ``approve()`` no longer decrypts keys at all.
- ``it_desk_phone()`` (brief 011, criterion 47): the start page's tap-to-call number.
- ``move_class()`` / ``move_series()`` (brief 012, D2): move one class, or change the time of
  a booking's remaining classes, on the same account and the same Zoom meeting. The same
  safety as ``approve()``: a fresh Zoom lookup with no locks, then one transaction that locks
  request → account → classes, re-checks, rewrites the slots and updates Zoom, then commits.
  Whenever Zoom may have changed and the move didn't commit, ``_put_zoom_back`` puts Zoom
  back to the times the database holds, under the same locks: one ``PATCH`` for one class;
  for a series, the restoring ``PATCH``, the forward path's read-back-and-delete, a ``PATCH``
  per flattened class and a final check (brief 012, criterion 32).
- ``reconcile()`` (brief 013): the one place a booking is brought into line with a change made
  directly in Zoom, for the webhook (``handle_event``), the ``Check against Zoom`` button and
  the nightly ``sync_zoom_bookings``. It asks Zoom first, with no transaction open, then locks
  request → account → classes as ``cancel()`` and the moves do, compares (``sync.compare``),
  and writes through the same model operations they use, with nobody named and no Zoom call
  (Zoom already has the change). Because ``cancel()`` and the moves change Zoom while holding
  the request lock, a webhook about the app's own change waits for that commit and then finds
  nothing to do (D1).
- The emails. They're sent after the model change, synchronously, and a send failure is
  logged and reported but never undoes a decision (D9).

Logging rule for this module (brief 005 criteria 41, 64, 65; brief 006 criterion 11; brief 011
criteria 24, 25 and 43): log references, account labels, meeting IDs, user names, client IPs
and exception class names only. Never a host key, join link, passcode, token, start link,
Zoom ``start_url``, credential or exception text.
"""

import hashlib
import ipaddress
import logging
from collections import defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import constants as message_levels
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.db import DatabaseError, IntegrityError, OperationalError, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from . import sync
from .models import (
    CANCEL_REASON_REQUIRED,
    CANCELLED_IN_ZOOM_REASON,
    CLASS_ALREADY_CANCELLED,
    MOVE_CLASS_CANCELLED,
    MOVE_SHOWN_SALT,
    NOTHING_LEFT_TO_CANCEL,
    NOTHING_LEFT_TO_MOVE,
    ZOOM_CLASS_NOT_BOOKED,
    ZOOM_MOVE_CLASHES,
    ZOOM_MOVE_NOT_BOOKABLE,
    HostAccount,
    HostKeyReveal,
    HostSlot,
    LinkRequest,
    Occurrence,
    SecretUnreadable,
    ZoomEvent,
    class_date,
    class_moment,
    class_span,
    class_time,
    join_words,
)
from .providers import (
    ProviderError,
    ZoomAuthFailed,
    ZoomDailyLimit,
    ZoomMeetingNotFound,
    ZoomMissingScope,
    ZoomProvider,
    ZoomUnavailable,
    ZoomUserNotFound,
    get_provider,
)
from .validators import format_phone, normalise_phone

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
# Brief 012, criterion 34 (D22): Zoom's daily limit is lasting, but Check connection can't
# help with it. P5's reset sentence is built in one place (``daily_reset_sentence``); every
# daily message ends with it. Approve alone offers another account, which has its own quota.
DAILY_RESET = "Try again after {time} on {date}."
NEXT_STEP_DAILY = "Choose another free account, or wait for this one. {reset}"
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
# Brief 015, criterion 22: the three amended rows. 006's "not on the server" row is retired.
CHECK_NO_CONNECTION = "{label} has no Zoom connection yet. Choose one, save, then check again."
CHECK_UNREADABLE = (
    "The details of the Zoom connection {slug} can't be read with the server's current "
    "encryption keys. Type its client secret again on the Zoom connection's page, then check "
    "again."
)
CHECK_AUTH_FAILED = (
    "Zoom didn't accept the details of the Zoom connection {slug}. Check its Account ID, Client "
    "ID and Client Secret on the Zoom connection's page, and that the Zoom app is activated."
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
# Criterion 34, row 4: ``{reset}`` is ``daily_reset_sentence()``, so this renders exactly as
# pinned, "… {phrase}. Try again after {time} on {date}.", without a second copy of P5.
CHECK_DAILY_LIMIT = "Couldn't check {label} with Zoom: {phrase}. {reset}"
ZOOM_BASIC_USER = 1  # Zoom's user type for a Basic (free) user


def zoom_daily_reset(now=None) -> datetime:
    """When Zoom's daily limits reset next: the next 00:00 UTC (criterion 14, P5)."""
    today = (now or timezone.now()).astimezone(UTC).date()
    return datetime.combine(today + timedelta(days=1), time(0), tzinfo=UTC)


def daily_reset_sentence(now=None) -> str:
    """P5's ``Try again after 5:30 am on Tue 29 Sep 2026.`` (criterion 34, D22).

    The only place it's built, so every daily-limit message names the same reset in the same
    words: in Colombo time and as a day, never "UTC", "today" or "tomorrow".
    """
    reset = zoom_daily_reset(now)
    return DAILY_RESET.format(time=class_time(reset), date=class_date(reset))


def next_step(error, label) -> str:
    """ "Try again in a few minutes." only when waiting can help (D23).

    A daily limit is checked first (criterion 34): it's lasting, but Check connection can't
    help, so approve offers another account (its own quota) or the reset.
    """
    if isinstance(error, ZoomDailyLimit):
        return NEXT_STEP_DAILY.format(reset=daily_reset_sentence())
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
    PROVIDER_ERROR = "provider_error"
    # Brief 011: cancelling.
    CANCELLED = "cancelled"
    NOTHING_TO_DO = "nothing_to_do"
    # Brief 012: moving. ``INVALID``: the locked re-check found the typed time breaks a rule
    # (it's the time already booked, or it has passed while the form was open).
    MOVED = "moved"
    INVALID = "invalid"


@dataclass(frozen=True)
class ApproveResult:
    """What ``approve()`` did. Since brief 011 it carries no host key: approving never
    decrypts one (D3), so an unreadable key can't block an approval."""

    outcome: Outcome
    message: str = ""
    link_request: LinkRequest | None = None


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
    """Keyed by the account, its Zoom user, its connection and that connection's credentials
    version, and the request's window.

    The email, the chosen connection and its ``credentials_version`` are part of the key, so
    changing the email or the connection on the accounts page, or the connection's details on
    its own page, makes the next load ask Zoom again (brief 015, criterion 25). The connection
    was loaded with the account, so this runs no query. Hashed to keep the key short and
    cache-safe.
    """
    start, end = window
    connection = account.zoom_connection if account.zoom_connection_id else None
    raw = "|".join(
        [
            str(account.pk),
            account.email,
            str(account.zoom_connection_id or ""),
            str(connection.credentials_version if connection else ""),
            start.isoformat(),
            end.isoformat(),
        ]
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
       start and the account; re-check database clashes with a locking read; book the classes
       and insert the 5-minute slots (the unique slot index is the backstop). The host key is
       never decrypted here (brief 011, D3).
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

            account = HostAccount.objects.locked().bookable().filter(pk=account_id).first()
            if account is None:
                return ApproveResult(Outcome.CONFLICT, NOT_OFFERED, link_request)
            label = account.label
            if not provider.is_connected(account):
                return ApproveResult(
                    Outcome.CONFLICT, NOT_CONNECTED.format(label=label), link_request
                )

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


# --------------------------------------------------------------------------- Cancelling (011)

# Criteria 12-15: every cancel message says exactly what happened in Zoom and here.
CANCEL_FAILED = "We couldn't cancel it in Zoom: {phrase}. Nothing was cancelled. {next_step}"
CANCEL_NEXT_STEP_LASTING = (
    "Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again."
)
CANCEL_MAYBE_DONE = (
    "We couldn't tell whether Zoom removed it: no answer from Zoom. Nothing was cancelled here. "
    "Try again in a few minutes. Trying again is safe."
)
CANCEL_SAVE_FAILED = (
    "Zoom removed it, but saving the cancellation here failed. Press Cancel again to finish."
)
# Not pinned by the brief: a lock race before anything reached Zoom.
CANCELLING_AT_THE_SAME_MOMENT = (
    "Someone else was changing this booking at the same moment. Nothing was cancelled. Try again."
)
CANCELLED_BOOKING = "Cancelled the booking. We emailed {email}."
CANCELLED_CLASS = "Cancelled the class on {date}. We emailed {email}."
CANCELLED_EMAIL_FAILED = "Cancelled, but the email to {email} didn't send. Tell them yourself."
CANCELLED_NOT_IN_ZOOM = " This system can't reach Zoom: delete it in Zoom too."
CANCEL_ATTEMPTS = 2


def cancel_failed_message(error, label) -> str:
    """Criterion 12: Zoom certainly removed nothing. The next step depends on ``lasting``.

    A daily limit is checked first (brief 012, criterion 34): the reset sentence alone, since
    a cancel can't change account and Check connection can't help.
    """
    if isinstance(error, ZoomDailyLimit):
        step = daily_reset_sentence()
    elif error.lasting:
        step = CANCEL_NEXT_STEP_LASTING.format(label=label)
    else:
        step = NEXT_STEP_TEMPORARY
    return CANCEL_FAILED.format(phrase=error.user_message, next_step=step)


@dataclass(frozen=True)
class CancelResult:
    """What ``cancel()`` did.

    ``cancelled`` are the classes cancelled now; ``remaining`` are the classes still to come
    (not cancelled, not ended), for the requester's email (criterion 17). Both are empty unless
    the outcome is ``CANCELLED``.
    """

    outcome: Outcome
    message: str = ""
    link_request: LinkRequest | None = None
    cancelled: list = field(default_factory=list)
    remaining: list = field(default_factory=list)
    whole: bool = True


@dataclass
class _CancelProgress:
    """What has reached Zoom so far, across attempts, so every message stays honest.

    ``deleting``: the delete call itself was being made (a lookup before it can't have removed
    anything). ``deleted``: Zoom removed it, in this attempt or an earlier one.
    """

    deleting: bool = False
    deleted: bool = False
    meeting_id: str = ""


def cancel(link_request_id, *, occurrence_id=None, by, reason, provider=None) -> CancelResult:
    """Cancel a whole booking (``occurrence_id=None``) or one class of it (brief 011, D2).

    One transaction, in this order (criterion 10):

    1. lock the request, then its account, then its classes (``SELECT … FOR UPDATE``); the
       same order as ``approve()``, which locks a request before an account;
    2. re-check the rules on the locked rows (criterion 6); nothing to do returns
       ``NOTHING_TO_DO`` with the pinned message, and Zoom isn't called;
    3. mark the classes cancelled, delete their slots, and set the request ``cancelled`` when
       no class is left to come (``status_after_cancel``);
    4. one Zoom delete (criterion 11), still inside the transaction;
    5. commit.

    Why Zoom is called with the locks held: brief 013's ``meeting.deleted`` webhook locks the
    same request row, so it waits for this commit and then finds nothing left to do (D2). The
    lock is held for one ``DELETE`` with 006's timeouts, the bound 006 accepted for the create.

    Failures (criteria 12-14): any Zoom error rolls everything back. A MySQL deadlock is
    retried once, as ``approve()`` does; if Zoom had already removed it, the retry's delete is
    answered "no such meeting", which counts as done. Any other failure after Zoom removed it
    leaves the booking in place with ``CANCEL_SAVE_FAILED``, and pressing Cancel again
    finishes it. Call it outside an open transaction (the views are ``non_atomic_requests``).

    The email is the caller's, after this returns, so a mail failure never undoes a cancel.
    """
    provider = provider or get_provider()
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": CANCEL_REASON_REQUIRED})
    reference = LinkRequest(pk=link_request_id).reference
    progress = _CancelProgress()
    for attempt in range(1, CANCEL_ATTEMPTS + 1):
        progress.deleting = False
        try:
            return _cancel_once(
                link_request_id,
                occurrence_id,
                by=by,
                reason=reason,
                provider=provider,
                progress=progress,
            )
        except OperationalError as exc:
            code = _mysql_code(exc)
            if code == MYSQL_DEADLOCK and attempt < CANCEL_ATTEMPTS:
                logger.warning("Cancelling %s hit a deadlock; trying once more.", reference)
                continue
            if progress.deleted:
                return _cancel_save_failed(reference, progress.meeting_id, exc)
            if code in (MYSQL_DEADLOCK, MYSQL_LOCK_WAIT_TIMEOUT):
                logger.warning("Cancelling %s lost a lock race (MySQL %s).", reference, code)
                return CancelResult(Outcome.CONFLICT, CANCELLING_AT_THE_SAME_MOMENT)
            raise
        except Exception as exc:
            if progress.deleted:
                return _cancel_save_failed(reference, progress.meeting_id, exc)
            raise
    raise AssertionError("unreachable: every attempt returns or raises")


def _cancel_save_failed(reference, meeting_id, cause) -> CancelResult:
    """Criterion 14: Zoom removed it, but this database didn't record it. One ERROR line."""
    logger.error(
        "Cancelling %s: Zoom meeting %s was removed, but saving failed: %s",
        reference,
        meeting_id,
        type(cause).__name__,
    )
    return CancelResult(Outcome.PROVIDER_ERROR, CANCEL_SAVE_FAILED)


def _cancel_once(link_request_id, occurrence_id, *, by, reason, provider, progress):
    """One attempt of ``cancel()``; MySQL lock errors propagate so the caller can retry."""
    reference = LinkRequest(pk=link_request_id).reference
    label = ""
    try:
        with transaction.atomic():
            link_request = LinkRequest.objects.select_for_update().get(pk=link_request_id)
            if link_request.status not in (
                LinkRequest.Status.APPROVED,
                LinkRequest.Status.CANCELLED,
            ):
                return CancelResult(Outcome.NOTHING_TO_DO, NOTHING_LEFT_TO_CANCEL, link_request)
            account = HostAccount.objects.locked().get(pk=link_request.host_account_id)
            label = account.label
            occurrences = list(
                link_request.occurrences.select_for_update().order_by("starts_at", "pk")
            )
            now = timezone.now()

            whole = occurrence_id is None
            if whole:
                blocked = link_request.cancel_booking_blocked_message(now, occurrences=occurrences)
                targets = link_request.remaining_classes(now, occurrences=occurrences)
            else:
                target = next((o for o in occurrences if o.pk == occurrence_id), None)
                if target is None:
                    blocked = CLASS_ALREADY_CANCELLED
                else:
                    blocked = target.cancel_blocked_message(now)
                targets = [target]
            if blocked:
                return CancelResult(Outcome.NOTHING_TO_DO, blocked, link_request)

            # The writes are the model's, shared with brief 013's reconcile (criterion 28: the
            # booking's "needs a look" flag is cleared there when it becomes cancelled).
            link_request.record_cancel(
                targets, by=by, reason=reason, now=now, occurrences=occurrences
            )

            progress.meeting_id = link_request.meeting_id
            one_class = (
                None if whole or link_request.repeat != link_request.Repeat.WEEKLY else (targets[0])
            )
            _delete_in_zoom(provider, link_request, account, one_class, progress)
    except ProviderError as exc:
        logger.warning("Couldn't cancel %s in Zoom on %s: %s", reference, label, type(exc).__name__)
        if progress.deleted:
            # An earlier attempt's delete went through; only saving it here is missing.
            return CancelResult(Outcome.PROVIDER_ERROR, CANCEL_SAVE_FAILED)
        if progress.deleting and exc.maybe_done:
            return CancelResult(Outcome.PROVIDER_ERROR, CANCEL_MAYBE_DONE)
        return CancelResult(Outcome.PROVIDER_ERROR, cancel_failed_message(exc, label))

    remaining = link_request.classes_still_on(now, occurrences=occurrences)
    logger.info("Cancelled %s class(es) of %s on %s.", len(targets), link_request.reference, label)
    return CancelResult(Outcome.CANCELLED, "", link_request, list(targets), remaining, whole)


def _delete_in_zoom(provider, link_request, account, one_class, progress) -> None:
    """Criterion 11's one call: the whole meeting, or one class of a weekly one.

    A class with no stored Zoom occurrence ID is looked up by its start first; if Zoom has no
    such class (or no such meeting) it's already gone there, so nothing is deleted. A provider
    that can't reach Zoom (``manual``) deletes nothing, and ``progress.deleted`` stays false
    so no message claims Zoom removed anything.
    """
    meeting_id = link_request.meeting_id
    occurrence_id = None
    if one_class is not None:
        occurrence_id = one_class.zoom_occurrence_id
        if not occurrence_id and provider.checks_zoom:
            try:
                occurrence_id = provider.occurrence_id_for(
                    host_account=account, meeting_id=meeting_id, starts_at=one_class.starts_at
                )
            except ZoomMeetingNotFound:
                occurrence_id = None
        if not occurrence_id:
            logger.info(
                "%s: Zoom has no class at %s in meeting %s; nothing to delete there.",
                link_request.reference,
                timezone.localtime(one_class.starts_at).isoformat(),
                meeting_id,
            )
            return
    progress.deleting = True
    provider.delete_meeting(
        host_account=account, meeting_id=meeting_id, occurrence_id=occurrence_id
    )
    progress.deleted = bool(provider.checks_zoom)


def cancelled_message(result, *, emailed, checks_zoom) -> tuple[int, str]:
    """``(message level, text)`` for the detail page after a cancel (criterion 15)."""
    link_request = result.link_request
    email = link_request.requester_email
    if not emailed:
        level, text = message_levels.WARNING, CANCELLED_EMAIL_FAILED.format(email=email)
    elif result.whole:
        level, text = message_levels.SUCCESS, CANCELLED_BOOKING.format(email=email)
    else:
        date = class_date(result.cancelled[0].starts_at)
        level, text = message_levels.SUCCESS, CANCELLED_CLASS.format(date=date, email=email)
    if not checks_zoom:
        text += CANCELLED_NOT_IN_ZOOM
    return level, text


# --------------------------------------------------------------------------- Moving (012)

# Criterion 9: the new time clashes, or Zoom couldn't be asked. None of them offers another
# account: a move never changes account (D11).
MOVE_ZOOM_CLASH = (
    "{label} has a meeting in Zoom at that time: {topic}, {date} at {time}. Choose another time."
)
MOVE_BOOKED_CLASH = "{label} already has {booking} at that time. Choose another time."
MOVE_BOOKED_A_MOMENT_AGO = "{label} was booked at that time a moment ago. Choose another time."
MOVE_NOT_CONNECTED = (
    "{label} isn't connected to Zoom, so this class can't be moved here. Set up its Zoom "
    "connection on the Zoom accounts page."
)
MOVE_LOOKUP_FAILED = (
    "We couldn't check {label}'s meetings in Zoom, so nothing was changed. {reason} {next_step}"
)
MOVE_LOOKUP_NEXT_STEP_LASTING = (
    "Ask whoever manages the Zoom accounts to press Check connection for {label}."
)
# Criteria 11-15: what Zoom did, and what's true here. The lasting next step is 011's (P6).
MOVE_FAILED = "We couldn't move it in Zoom: {phrase}. Nothing was changed. {next_step}"
MOVE_MISSING_SCOPE = (
    "The Zoom app for {label} is missing the permission to change meetings. Nothing was "
    "changed. Ask whoever looks after the server to add the scopes listed in the README."
)
# ``{reset}`` is ``daily_reset_sentence()`` (criterion 34); the rendered text is criterion 14's.
MOVE_DAILY_LIMIT = (
    "Zoom's daily limit for changing {label}'s meetings is used up. Nothing was changed. {reset}"
)
MOVE_MAYBE_RESTORED = (
    "No answer from Zoom, so we put the class back to its old time there to be safe. Nothing "
    "was changed. Try again in a few minutes."
)
MOVE_MAYBE_NOT_RESTORED = (
    "No answer from Zoom, and we couldn't check what it did. Nothing was changed here. Try "
    "again in a few minutes. If the class shows the new time in Zoom, trying again finishes "
    "the move."
)
MOVE_DATES_DIFFER = (
    "Zoom scheduled different dates from these classes, so nothing was changed. Tell whoever "
    "looks after the system."
)
# Criterion 32 (D21, the designer's D.13): the move couldn't be saved and Zoom couldn't be
# made to match. Which one is chosen by ``_PutBack.landed``, because each claim must be true:
# with no restoring PATCH answered, Zoom *may* still be at the new time; once one was
# answered, Zoom has the saved times again, but the later steps (cancelled dates deleted,
# classes moved on their own put back) may not have happened.
MOVE_NOT_PUT_BACK = (
    "We couldn't save the new time here, or undo it in Zoom. {label}'s meeting {meeting_id} "
    "may still be at the new time in Zoom. Check that meeting in Zoom against this booking's "
    "Classes list, then tell whoever looks after the system."
)
MOVE_PARTLY_PUT_BACK = (
    "We couldn't save the new time here. We put {label}'s meeting {meeting_id} back to the "
    "times saved here, but some classes in Zoom may not match this booking. A cancelled class "
    "may have come back, or a class moved on its own may be at the usual time. Check that "
    "meeting in Zoom against this booking's Classes list, then tell whoever looks after the "
    "system."
)
# Criterion 29 (D.12): the "already moved" state of criteria 17a and 30. The page's signed
# ``shown`` no longer matches the locked rows, so the form showed a time that changed since.
# 1a names the class's time now (``str(occurrence)``); 1b the booking's times now.
MOVED_A_MOMENT_AGO = (
    "Someone else moved this class a moment ago. It's now {when}. We didn't make your change. "
    "If it still needs to move, check the time in the form and press the button again."
)
TIMES_CHANGED_A_MOMENT_AGO = (
    "Someone else changed the time of the remaining classes a moment ago. They're now {times}. "
    "We didn't make your change. If they still need a different time, check the times in the "
    "form and press the button again."
)
# Criterion 29, message 3 (approved as written): a lock-wait timeout or a second deadlock.
MOVING_AT_THE_SAME_MOMENT = (
    "Someone else was changing this booking at the same moment. Nothing was changed. Try again."
)
# Criterion 30 (main-session ruling): the form's ``shown`` is missing or doesn't read back (a
# page from before the fix, or an edited one), so there's no telling what the person saw.
MOVE_PAGE_OUT_OF_DATE = "This page is out of date. Reload it, check the times, then try again."
# Criterion 16: the flashes on the detail page.
MOVED_CLASS = "Moved the class to {when}. We emailed {email}."
MOVED_SERIES = "Changed the time of {n} {classes} to {times}. We emailed {email}."
MOVED_EMAIL_FAILED = (
    "Moved, but the email to {email} didn't send. Tell them the new times yourself."
)
MOVED_NOT_IN_ZOOM = " This system can't reach Zoom: change it in Zoom too."
MOVE_ATTEMPTS = 2

# Every message a move can show IT, for the scan that none offers another account (P6, D11).
MOVE_MESSAGES = (
    MOVE_ZOOM_CLASH,
    MOVE_BOOKED_CLASH,
    MOVE_BOOKED_A_MOMENT_AGO,
    MOVE_NOT_CONNECTED,
    MOVE_LOOKUP_FAILED,
    MOVE_LOOKUP_NEXT_STEP_LASTING,
    MOVE_FAILED,
    MOVE_MISSING_SCOPE,
    MOVE_DAILY_LIMIT,
    MOVE_MAYBE_RESTORED,
    MOVE_MAYBE_NOT_RESTORED,
    MOVE_DATES_DIFFER,
    MOVE_NOT_PUT_BACK,
    MOVE_PARTLY_PUT_BACK,
    MOVED_A_MOMENT_AGO,
    TIMES_CHANGED_A_MOMENT_AGO,
    MOVING_AT_THE_SAME_MOMENT,
    MOVE_PAGE_OUT_OF_DATE,
    MOVED_CLASS,
    MOVED_SERIES,
    MOVED_EMAIL_FAILED,
    MOVED_NOT_IN_ZOOM,
)

# A new time to check against Zoom's busy times (``zoom_clashes`` reads these two names).
_Span = namedtuple("_Span", "starts_at ends_at")


def move_next_step(error, label) -> str:
    """Criterion 12's next step (P6): wait, or ask for Check connection. Never "another account"."""
    return CANCEL_NEXT_STEP_LASTING.format(label=label) if error.lasting else NEXT_STEP_TEMPORARY


def move_failed_message(error, label, now=None) -> str:
    """Criteria 12 and 14: Zoom certainly changed nothing. Two kinds have their own text."""
    if isinstance(error, ZoomMissingScope):
        return MOVE_MISSING_SCOPE.format(label=label)
    if isinstance(error, ZoomDailyLimit):
        return MOVE_DAILY_LIMIT.format(label=label, reset=daily_reset_sentence(now))
    return MOVE_FAILED.format(phrase=error.user_message, next_step=move_next_step(error, label))


def move_lookup_failed_message(error, label) -> str:
    """Criterion 9's "couldn't be asked" row, with its own lasting next step.

    A daily limit is checked first (criterion 34): the reset sentence alone, since a move
    can't change account (D11) and Check connection can't help.
    """
    if isinstance(error, ZoomDailyLimit):
        step = daily_reset_sentence()
    elif error.lasting:
        step = MOVE_LOOKUP_NEXT_STEP_LASTING.format(label=label)
    else:
        step = NEXT_STEP_TEMPORARY
    return MOVE_LOOKUP_FAILED.format(label=label, reason=error.reason_sentence, next_step=step)


def read_move_shown(token) -> dict:
    """``{pk: (starts_at, ends_at)}`` in epoch seconds, from a move form's ``shown`` (c. 30).

    The other half of ``LinkRequest.move_fingerprint``. Raises ``signing.BadSignature`` for a
    missing, edited or malformed value (the view shows ``MOVE_PAGE_OUT_OF_DATE``). No
    ``max_age``: an old page is fine as long as nothing it shows has changed, which the locked
    re-check decides.
    """
    if not token:
        raise signing.BadSignature("No shown value.")
    rows = signing.loads(token, salt=MOVE_SHOWN_SALT)
    try:
        return {int(pk): (int(start), int(end)) for pk, start, end in rows}
    except (TypeError, ValueError) as exc:
        raise signing.BadSignature("Unexpected payload.") from exc


def _as_shown(occurrence) -> tuple:
    """A class's times in ``read_move_shown``'s form, to compare with what the page showed."""
    return int(occurrence.starts_at.timestamp()), int(occurrence.ends_at.timestamp())


@dataclass(frozen=True)
class MovedClass:
    """One class a move changed: its old times and the class, now at its new times.

    Named fields, because ``zoom/email/moved_body.txt`` reads ``old_start``, ``old_end`` and
    ``occurrence`` by name (the context contract's ``moves``).
    """

    old_start: datetime
    old_end: datetime
    occurrence: Occurrence


@dataclass(frozen=True)
class MoveResult:
    """What ``move_class()`` / ``move_series()`` did.

    ``moves`` is empty unless the outcome is ``MOVED``; ``series`` says which kind of move it
    was, for the flash. ``message`` is ``move_error`` in final form (criteria 9, 11-15), or a
    blocked rule's message for the redirect (``NOTHING_TO_DO``). ``stale`` marks criterion
    30's refusal (1a / 1b): the one ``CONFLICT`` whose re-render signs a fresh ``shown``,
    because its message names the current time (criterion 33).
    """

    outcome: Outcome
    message: str = ""
    link_request: LinkRequest | None = None
    moves: list = field(default_factory=list)
    series: bool = False
    stale: bool = False


@dataclass
class _MoveProgress:
    """What has reached Zoom so far, across attempts, so every message stays honest.

    ``changed``: an update was sent that may have gone through (answered, or unanswered with
    ``maybe_done``). ``certain``: one was answered, so Zoom certainly has a new time.
    """

    label: str = ""
    meeting_id: str = ""
    zoom_occurrence_id: str = ""
    changed: bool = False
    certain: bool = False


def move_class(
    link_request_id, occurrence_id, *, starts_at, ends_at, by, shown=None, provider=None
) -> MoveResult:
    """Move one class of an approved booking to ``[starts_at, ends_at)`` (brief 012).

    ``shown`` is ``read_move_shown()`` of the form the person pressed (criterion 30): if the
    class's times differ from what that page showed, this stops with ``MOVED_A_MOMENT_AGO``
    rather than undoing someone else's move (criteria 17a and 30). The move views always pass
    it; ``None`` skips the check, for a caller that acts on the stored rows by design. See
    ``_move`` for the order of work.
    """
    return _move(
        link_request_id,
        occurrence_id,
        (starts_at, ends_at),
        shown=shown,
        by=by,
        provider=provider,
    )


def move_series(
    link_request_id, *, start_time, end_time, by, shown=None, provider=None
) -> MoveResult:
    """Change the time of day of every remaining class of a weekly booking (brief 012, D10).

    ``shown`` as for ``move_class``, listing every remaining class the page showed; a change to
    any of them stops this with ``TIMES_CHANGED_A_MOMENT_AGO``. Also sets the request's
    ``start_time`` / ``end_time``, so ``schedule_summary`` stays true (D4).
    """
    return _move(
        link_request_id,
        None,
        (start_time, end_time),
        shown=shown,
        by=by,
        provider=provider,
    )


def _move(link_request_id, occurrence_id, times, *, shown, by, provider) -> MoveResult:
    """The one move procedure behind both services (D2), with 006's structure.

    Per attempt:

    1. **No locks, no transaction** (``_move_check_first``): the rules on the stored rows, the
       account's connection, a database clash preview, then a **fresh** Zoom lookup of the
       account's meetings across the new times. A clash or a failed lookup stops here, before
       anything is locked or sent to Zoom.
    2. **One transaction** (``_move_once``): lock the request, its account, its classes;
       re-check the rules and the database clashes with a locking read; replace the slots (the
       unique slot index is the backstop) and update the classes (and, for a series, the
       request's times); then, still inside it, update Zoom (``PATCH``; for a series also the
       read-back and the deletes of criterion 10); commit.

    Why Zoom is changed with the locks held: brief 013's ``meeting.updated`` webhook waits for
    this commit and then finds the database already matching (D2).

    After a failure: a deadlock is retried once (repeating the ``PATCH`` is harmless). If Zoom
    may hold the new time and the move didn't commit, ``_put_zoom_back`` sets Zoom to the
    times the database holds, and the message says what's true afterwards (criteria 11-15
    and 32): "nothing was changed" only once it's been checked; otherwise, whenever Zoom has
    certainly changed and couldn't be made to match, one neutral ``ERROR`` line and
    ``MOVE_NOT_PUT_BACK`` (no restoring ``PATCH`` answered) or ``MOVE_PARTLY_PUT_BACK`` (one
    answered, then a later step failed), D21.
    Call it outside an open transaction: the move views are ``non_atomic_requests``.
    """
    provider = provider or get_provider()
    reference = LinkRequest(pk=link_request_id).reference
    progress = _MoveProgress()
    result, cause = None, None
    for attempt in range(1, MOVE_ATTEMPTS + 1):
        try:
            stop, window = _move_check_first(
                link_request_id, occurrence_id, times, shown, provider, progress
            )
            result = stop or _move_once(
                link_request_id,
                occurrence_id,
                times,
                shown,
                window,
                by=by,
                provider=provider,
                progress=progress,
            )
            break
        except OperationalError as exc:
            code = _mysql_code(exc)
            if code == MYSQL_DEADLOCK and attempt < MOVE_ATTEMPTS:
                logger.warning("Moving %s hit a deadlock; trying once more.", reference)
                continue
            cause = exc
            if code in (MYSQL_DEADLOCK, MYSQL_LOCK_WAIT_TIMEOUT):
                logger.warning("Moving %s lost a lock race (MySQL %s).", reference, code)
                result = MoveResult(Outcome.CONFLICT, MOVING_AT_THE_SAME_MOMENT)
            break
        except IntegrityError as exc:
            cause = exc
            if _mysql_code(exc) == MYSQL_DUPLICATE_ENTRY:
                logger.warning("Moving %s hit the slot backstop; another booking won.", reference)
                result = MoveResult(
                    Outcome.CONFLICT, MOVE_BOOKED_A_MOMENT_AGO.format(label=progress.label)
                )
            break
        except _DatesDiffer as exc:
            cause = exc
            logger.warning("Zoom's dates for %s differed after changing its times.", reference)
            result = MoveResult(Outcome.PROVIDER_ERROR, MOVE_DATES_DIFFER)
            break
        except ProviderError as exc:
            cause = exc
            logger.warning(
                "Couldn't move %s in Zoom on %s: %s", reference, progress.label, type(exc).__name__
            )
            result = MoveResult(Outcome.PROVIDER_ERROR, move_failed_message(exc, progress.label))
            break
        except Exception as exc:  # re-raised below, once Zoom is put back if it needs to be
            cause = exc
            break

    if result is not None and result.outcome == Outcome.MOVED:
        return result
    if progress.changed:
        back = _put_zoom_back(provider, link_request_id, occurrence_id, progress, reference)
        if back.done:
            if not progress.certain:
                return MoveResult(Outcome.PROVIDER_ERROR, MOVE_MAYBE_RESTORED)
        elif not progress.certain and not back.landed:
            # Criterion 13: neither the move nor its undo was answered, so Zoom may never
            # have changed at all.
            return MoveResult(Outcome.PROVIDER_ERROR, MOVE_MAYBE_NOT_RESTORED)
        else:
            # Zoom has certainly changed (the move or the undo was answered) and doesn't match
            # this database: criteria 11, 15 and 32. The line is worded to be true whatever
            # Zoom now holds (D21), so it claims no time; class names only, never Zoom's text
            # or links. A one-class undo that was answered never gets here: it's done.
            logger.error(
                "Moving %s: Zoom meeting %s doesn't match this database: %s "
                "(putting it back: %s, restoring update answered: %s)",
                reference,
                progress.meeting_id,
                type(cause).__name__ if cause is not None else "unknown",
                back.failure,
                "yes" if back.landed else "no",
            )
            message = MOVE_PARTLY_PUT_BACK if back.landed else MOVE_NOT_PUT_BACK
            return MoveResult(
                Outcome.PROVIDER_ERROR,
                message.format(label=progress.label, meeting_id=progress.meeting_id),
            )
    if result is None:
        raise cause
    return result


def _plan_move(link_request, classes, occurrence_id, times, shown, now):
    """``(stop, moves)``: a ``MoveResult`` that ends the attempt, or the classes to move.

    ``moves`` is ``[(occurrence, new start, new end)]``. The rules are the models'
    (criterion 2); this only turns their answers into outcomes. Used by both steps, on the
    plain rows first and on the locked rows again, so a stale form (criterion 30) is refused
    before the Zoom lookup and, authoritatively, under the locks before any ``PATCH``.

    The stale check compares only classes that are still remaining: a class cancelled or
    started since the page was shown is left out by the rules, not refused. A remaining class
    the page didn't list (or a one-class page for another class) counts as changed.
    """
    if occurrence_id is not None:
        target = next((o for o in classes if o.pk == occurrence_id), None)
        blocked = target.move_blocked_message(now) if target else MOVE_CLASS_CANCELLED
        if blocked:
            return MoveResult(Outcome.NOTHING_TO_DO, blocked, link_request), []
        if shown is not None and shown.get(target.pk) != _as_shown(target):
            return MoveResult(
                Outcome.CONFLICT,
                MOVED_A_MOMENT_AGO.format(when=target),
                link_request,
                stale=True,
            ), []
        starts_at, ends_at = times
        errors = target.move_errors(starts_at=starts_at, ends_at=ends_at, now=now)
        if errors:
            return MoveResult(Outcome.INVALID, next(iter(errors.values())), link_request), []
        return None, [(target, starts_at, ends_at)]

    blocked = link_request.series_move_blocked_message(now, occurrences=classes)
    if blocked:
        return MoveResult(Outcome.NOTHING_TO_DO, blocked, link_request), []
    remaining = link_request.remaining_classes(now, occurrences=classes)
    if shown is not None and any(shown.get(o.pk) != _as_shown(o) for o in remaining):
        times_now = f"{class_time(link_request.start_time)} to {class_time(link_request.end_time)}"
        return MoveResult(
            Outcome.CONFLICT,
            TIMES_CHANGED_A_MOMENT_AGO.format(times=times_now),
            link_request,
            stale=True,
        ), []
    start_time, end_time = times
    errors = link_request.series_move_errors(
        start_time=start_time, end_time=end_time, now=now, occurrences=classes
    )
    if errors:
        return MoveResult(Outcome.INVALID, next(iter(errors.values())), link_request), []
    return None, link_request.series_new_times(start_time, end_time, now, occurrences=classes)


def _move_check_first(link_request_id, occurrence_id, times, shown, provider, progress):
    """Step 1 of a move, with no locks and no transaction: ``(stop or None, window)``.

    ``window`` is ``(first new start, last new end)``: the span Zoom was asked about. Step 2
    refuses to go on if the locked rows would move a class outside it (criterion 8: the
    lookup spans the new times). Nothing is sent to Zoom unless every check before it passed,
    so a class that can't be moved makes no Zoom call (criterion 4).
    """
    link_request = (
        LinkRequest.objects.select_related("host_account__zoom_connection")
        .filter(pk=link_request_id)
        .first()
    )
    if link_request is None or link_request.status != LinkRequest.Status.APPROVED:
        message = MOVE_CLASS_CANCELLED if occurrence_id is not None else NOTHING_LEFT_TO_MOVE
        return MoveResult(Outcome.NOTHING_TO_DO, message, link_request), None
    account = link_request.host_account
    label = progress.label = account.label
    progress.meeting_id = link_request.meeting_id
    classes = list(link_request.occurrences.all())
    stop, moves = _plan_move(link_request, classes, occurrence_id, times, shown, timezone.now())
    if stop is not None:
        return stop, None
    spans = [_Span(start, end) for _, start, end in moves]
    window = class_window(spans)

    if not provider.is_connected(account):
        return MoveResult(
            Outcome.CONFLICT, MOVE_NOT_CONNECTED.format(label=label), link_request
        ), None
    booked = Occurrence.objects.clashing(
        account, [tuple(span) for span in spans], exclude_ids=[o.pk for o, _, _ in moves]
    )
    if booked:
        return _booked_clash(label, booked[0], link_request), None
    if not provider.checks_zoom:
        return None, window

    try:
        busy_times = provider.busy_times(host_account=account, start=window[0], end=window[1])
    except ProviderError as exc:
        forget_preview(account, window)
        logger.warning(
            "Couldn't check %s in Zoom before moving %s: %s",
            label,
            link_request.reference,
            type(exc).__name__,
        )
        return MoveResult(
            Outcome.PROVIDER_ERROR, move_lookup_failed_message(exc, label), link_request
        ), None
    # The booking's own meeting is covered by the database check (criterion 7).
    known = known_meeting_ids([account], window).get(account.pk, set()) | {link_request.meeting_id}
    clashes = zoom_clashes(link_request, spans, busy_times, known)
    if clashes:
        busy = clashes[0]["busy"]
        return MoveResult(
            Outcome.CONFLICT,
            MOVE_ZOOM_CLASH.format(
                label=label,
                topic=busy.display_topic,
                date=class_date(busy.starts_at),
                time=class_time(busy.starts_at),
            ),
            link_request,
        ), None
    return None, window


def _booked_clash(label, other, link_request) -> MoveResult:
    """Criterion 9's "booked class at the new time", for the preview and the locked re-check."""
    return MoveResult(
        Outcome.CONFLICT,
        MOVE_BOOKED_CLASH.format(label=label, booking=other.link_request),
        link_request,
    )


def _move_once(
    link_request_id, occurrence_id, times, shown, window, *, by, provider, progress
) -> MoveResult:
    """Step 2 of a move: one transaction, Zoom updated inside it (criterion 8's order).

    MySQL lock errors, the slot backstop, ``_DatesDiffer`` and ``ProviderError`` propagate,
    after the rollback, so ``_move`` can retry, put Zoom back and pick the message.
    """
    series = occurrence_id is None
    with transaction.atomic():
        link_request = LinkRequest.objects.select_for_update().get(pk=link_request_id)
        if link_request.status != LinkRequest.Status.APPROVED:
            message = NOTHING_LEFT_TO_MOVE if series else MOVE_CLASS_CANCELLED
            return MoveResult(Outcome.NOTHING_TO_DO, message, link_request)
        account = HostAccount.objects.locked().get(pk=link_request.host_account_id)
        label = progress.label = account.label
        classes = list(link_request.occurrences.select_for_update().order_by("starts_at", "pk"))
        now = timezone.now()
        stop, moves = _plan_move(link_request, classes, occurrence_id, times, shown, now)
        if stop is not None:
            return stop
        spans = [(start, end) for _, start, end in moves]
        first, last = class_window([_Span(*span) for span in spans])
        if window is None or first < window[0] or last > window[1]:
            # The classes changed between the lookup and the lock (a race): Zoom wasn't asked
            # about these times, so nothing goes ahead.
            return MoveResult(Outcome.CONFLICT, MOVING_AT_THE_SAME_MOMENT, link_request)
        if not provider.is_connected(account):
            return MoveResult(
                Outcome.CONFLICT, MOVE_NOT_CONNECTED.format(label=label), link_request
            )
        moving = [occurrence for occurrence, _, _ in moves]
        booked = Occurrence.objects.clashing(
            account, spans, exclude_ids=[o.pk for o in moving], lock=True
        )
        if booked:
            return _booked_clash(label, booked[0], link_request)

        zoom_occurrence_id = None
        if not series and provider.checks_zoom:
            zoom_occurrence_id = _zoom_occurrence_id(provider, link_request, account, moving[0])
            progress.zoom_occurrence_id = zoom_occurrence_id or ""

        # The writes are the model's, shared with brief 013's reconcile. ``account`` is the row
        # locked above: never a change of account (D1), it only saves a query per class.
        done = [
            MovedClass(old_start, old_end, occurrence)
            for old_start, old_end, occurrence in link_request.record_moves(
                moves, by=by, now=now, account=account
            )
        ]
        if series:
            link_request.start_time, link_request.end_time = times
            link_request.save(update_fields=["start_time", "end_time"])

        if provider.checks_zoom:
            if series:
                _move_series_in_zoom(provider, link_request, account, moving, progress)
            else:
                _update_in_zoom(
                    progress,
                    provider.update_occurrence,
                    host_account=account,
                    meeting_id=link_request.meeting_id,
                    occurrence_id=zoom_occurrence_id,
                    starts_at=moving[0].starts_at,
                    ends_at=moving[0].ends_at,
                )
    logger.info("Moved %s class(es) of %s on %s.", len(done), link_request.reference, label)
    return MoveResult(Outcome.MOVED, "", link_request, done, series)


def _zoom_occurrence_id(provider, link_request, account, occurrence):
    """The Zoom occurrence ID to update one class of a weekly meeting by, or ``None`` (one-off).

    A blank stored ID is looked up with 011's ``occurrence_id_for`` and kept on the class, so
    the next cancel or move needn't ask again. If Zoom has no such class, there's nothing to
    move there: that's Zoom's "no such meeting", a lasting refusal.
    """
    if link_request.repeat != LinkRequest.Repeat.WEEKLY:
        return None
    found = occurrence.zoom_occurrence_id or provider.occurrence_id_for(
        host_account=account, meeting_id=link_request.meeting_id, starts_at=occurrence.starts_at
    )
    if not found:
        raise ZoomMeetingNotFound()
    occurrence.zoom_occurrence_id = found
    return found


def _update_in_zoom(progress, update, **kwargs) -> None:
    """One ``PATCH``, recording whether Zoom may, or certainly does, hold the new time now.

    A refusal Zoom answered changed nothing; an unanswered call (``maybe_done``) may have.
    """
    try:
        update(**kwargs)
    except ProviderError as exc:
        if exc.maybe_done:
            progress.changed = True
        raise
    progress.changed = progress.certain = True


def _move_series_in_zoom(provider, link_request, account, remaining, progress) -> None:
    """Criterion 10's series calls and criterion 11's check, inside the transaction.

    1. One ``PATCH`` re-anchoring the series at the first remaining class, at its new time,
       for as many weekly classes as the pattern has from there to the last remaining date.
    2. ``_tidy_series_in_zoom``: one ``GET``, then one ``DELETE ?occurrence_id=`` for each
       class Zoom made on a pattern date that has no remaining class (a class cancelled
       earlier, brief 011), so it doesn't come back.

    The ``GET`` comes before the deletes, not after as the brief's table lists them: Zoom
    doesn't document that occurrence IDs survive a series update, so the IDs to delete are
    read, not guessed; what Zoom holds afterwards is that answer minus the deletes it
    accepted. Every class from the first remaining one on must then be a remaining class at
    its new start and end, one to one, or ``_DatesDiffer`` rolls the move back. The new IDs
    are stored.
    """
    first = remaining[0]
    _update_in_zoom(
        progress,
        provider.update_series,
        host_account=account,
        meeting_id=link_request.meeting_id,
        starts_at=first.starts_at,
        ends_at=first.ends_at,
        weekdays=link_request.weekdays,
        count=len(link_request.series_span_dates(remaining)),
    )
    kept = _tidy_series_in_zoom(provider, link_request, account, remaining)
    _store_series_ids(remaining, kept)


def _tidy_series_in_zoom(provider, link_request, account, remaining) -> list:
    """Read a series back just after a series ``PATCH``, and delete what mustn't be there.

    The one helper behind both directions (criteria 10 and 32): the forward move, and putting
    a failed move back, which would otherwise bring back every class cancelled earlier
    (review round 1, SF1). One ``GET``; then one ``DELETE ?occurrence_id=`` per class Zoom
    made on a date of the series span that has no remaining class. Classes on dates before
    the first remaining class are history, in Zoom too, and are left alone. Returns the
    ``ZoomClass`` items Zoom keeps, soonest first.
    """
    first_day = timezone.localdate(remaining[0].starts_at)
    kept_days = {timezone.localdate(o.starts_at) for o in remaining}
    unwanted_days = set(link_request.series_span_dates(remaining)) - kept_days
    found = provider.meeting_snapshot(host_account=account, meeting_id=link_request.meeting_id)
    kept = []
    for item in sorted(found):
        day = timezone.localdate(item.starts_at)
        if day < first_day:
            continue
        if day in unwanted_days:
            provider.delete_meeting(
                host_account=account,
                meeting_id=link_request.meeting_id,
                occurrence_id=item.occurrence_id,
            )
            continue
        kept.append(item)
    return kept


def _store_series_ids(remaining, in_zoom) -> None:
    """Check Zoom's classes against the remaining ones, then store Zoom's occurrence IDs.

    One to one by start **and** end (criteria 11 and 32), or ``_DatesDiffer``. The IDs are
    stored because a series ``PATCH`` may renumber the occurrences, and a later cancel or
    move of one class addresses it by that ID (a stale one would "succeed" as Zoom's 3001).
    """
    if sorted((item.starts_at, item.ends_at) for item in in_zoom) != sorted(
        (o.starts_at, o.ends_at) for o in remaining
    ):
        raise _DatesDiffer()
    by_start = {item.starts_at: item.occurrence_id for item in in_zoom}
    for occurrence in remaining:
        occurrence.zoom_occurrence_id = by_start[occurrence.starts_at]
    Occurrence.objects.bulk_update(remaining, ["zoom_occurrence_id"])


@dataclass
class _PutBack:
    """What putting Zoom back did, so ``_move`` picks a true message (criteria 11, 13, 32).

    ``done``: Zoom matches the database again (for a series, the final check passed).
    ``landed``: a restoring ``PATCH`` was answered, so Zoom has certainly changed since the
    failed move, whatever happens after it; when not ``done``, it picks
    ``MOVE_PARTLY_PUT_BACK`` over ``MOVE_NOT_PUT_BACK`` and is the ``ERROR`` line's
    "restoring update answered" (D21). ``failure``: the error class name, or ``mismatch``,
    for that line; never Zoom's text.
    """

    done: bool = False
    landed: bool = False
    failure: str = ""


def _put_zoom_back(provider, link_request_id, occurrence_id, progress, reference) -> _PutBack:
    """The compensating work (criteria 11, 13, 15 and 32): Zoom back to what this database holds.

    It runs after the move's transaction has rolled back, in a transaction of its own that
    locks the request, then the account, then the classes: the order of ``approve()``,
    ``cancel()`` and the move itself (D2), so it can't deadlock against them by taking locks
    the other way round (review round 1, SF2). A MySQL deadlock or lock-wait timeout is
    retried once, as ``_move`` retries; repeating any of its Zoom calls is harmless.

    Zoom is set to the times the database holds *now*, read from the locked rows: the old
    time, or the winner's time if another move of the same class committed first (criterion
    17a). Setting times Zoom may already have is harmless, so it's right whatever the
    unanswered call did (D2). A class or booking that's been cancelled since has nothing to
    put back. ``_put_one_class_back`` and ``_put_series_back`` say what each sends.

    **The one-class edge counts as done** (criterion 32, D21). For one class the undo
    ``PATCH`` is the last thing the transaction does, and the transaction writes nothing.
    So if the ``PATCH`` was answered and the transaction then fails (its commit, a lock
    race), Zoom already has the time the locked row held, which nothing here changed: Zoom
    matches this database. That's ``done``, logged at ``WARNING``, with no retry, since a
    second ``PATCH`` would only send the same time again. A series is different: once its
    first ``PATCH`` lands, the later steps are what make Zoom match, so it isn't done
    until its final check passes.

    It never raises (review round 2, nit): any error, expected or not, becomes ``failure``
    (its class name only), so ``_move`` always writes its neutral ``ERROR`` line, picks the
    message from ``landed``, and keeps reporting the move's own error.
    """
    back = _PutBack()
    one_class = occurrence_id is not None
    for attempt in range(1, MOVE_ATTEMPTS + 1):
        try:
            with transaction.atomic():
                _put_zoom_back_once(provider, link_request_id, occurrence_id, progress, back)
        except DatabaseError as exc:
            if one_class and back.landed:
                return _one_class_put_back_anyway(back, reference, exc)
            code = _mysql_code(exc) if isinstance(exc, OperationalError) else None
            if code in (MYSQL_DEADLOCK, MYSQL_LOCK_WAIT_TIMEOUT) and attempt < MOVE_ATTEMPTS:
                logger.warning("Putting %s back hit MySQL %s; trying once more.", reference, code)
                continue
            back.failure = type(exc).__name__
        except _DatesDiffer:
            back.failure = "mismatch"
        except ProviderError as exc:
            back.failure = type(exc).__name__
        except Exception as exc:
            # Anything unexpected (review round 2, nit; criterion 32's catch-all) is still a
            # failed put-back, never a crash: escaping here would skip ``_move``'s neutral
            # ERROR line and replace the move's own exception. Only its class name is kept,
            # never its text. The one-class edge holds for it too: once that PATCH was
            # answered, Zoom matches this database whatever failed after it.
            if one_class and back.landed:
                return _one_class_put_back_anyway(back, reference, exc)
            back.failure = type(exc).__name__
        else:
            back.done = True
            logger.warning(
                "Put %s back to its stored times in Zoom after a failed move.", reference
            )
            return back
        logger.warning("Couldn't put %s back in Zoom: %s", reference, back.failure)
        return back
    raise AssertionError("unreachable: the last attempt returns")


def _one_class_put_back_anyway(back, reference, exc) -> _PutBack:
    """The one-class edge (criterion 32, D21): the undo PATCH was answered, so it's done."""
    back.done = True
    logger.warning(
        "Put %s back in Zoom, but its own transaction then failed: %s",
        reference,
        type(exc).__name__,
    )
    return back


def _put_zoom_back_once(provider, link_request_id, occurrence_id, progress, back) -> None:
    """One attempt of ``_put_zoom_back``, inside its transaction. Raises on any failure."""
    link_request = LinkRequest.objects.select_for_update().get(pk=link_request_id)
    if link_request.status != LinkRequest.Status.APPROVED:
        return
    account = HostAccount.objects.locked().get(pk=link_request.host_account_id)
    classes = list(link_request.occurrences.select_for_update().order_by("starts_at", "pk"))
    if occurrence_id is not None:
        target = next((o for o in classes if o.pk == occurrence_id), None)
        if target is not None and target.cancelled_at is None:
            _put_one_class_back(provider, link_request, account, target, progress, back)
        return
    remaining = link_request.remaining_classes(timezone.now(), occurrences=classes)
    if remaining:
        _put_series_back(provider, link_request, account, remaining, back)


def _restoring_update(back, update, **kwargs) -> None:
    """One restoring ``PATCH``; once Zoom has answered it, Zoom has certainly changed."""
    update(**kwargs)
    back.landed = True


def _put_one_class_back(provider, link_request, account, target, progress, back) -> None:
    """One ``PATCH`` back to the locked row's times (criteria 13, 15 and 32).

    The occurrence ID is the locked row's. Only when that's blank (a booking from before the
    live connection, whose ID the failed attempt looked up and then lost in the rollback) is
    the attempt's looked-up ID used (review round 1, nit): without an ID the ``PATCH`` would
    address the whole weekly meeting and move every class. With neither, nothing is sent and
    the class can't be put back.
    """
    zoom_id = None
    if link_request.repeat == LinkRequest.Repeat.WEEKLY:
        zoom_id = target.zoom_occurrence_id or progress.zoom_occurrence_id
        if not zoom_id:
            raise ZoomMeetingNotFound()
    _restoring_update(
        back,
        provider.update_occurrence,
        host_account=account,
        meeting_id=link_request.meeting_id,
        occurrence_id=zoom_id,
        starts_at=target.starts_at,
        ends_at=target.ends_at,
    )


def _put_series_back(provider, link_request, account, remaining, back) -> None:
    """Undo a failed series move fully (criterion 32; owner: "Undo fully", D18).

    One restoring ``PATCH`` alone rebuilds the series from its pattern, so it brings back
    every class cancelled earlier and flattens classes moved by themselves, while the page
    would say "nothing was changed" (review round 1, SF1). So, in order:

    1. the restoring series ``PATCH``, anchored at the first remaining class's date at the
       booking's own time of day (``start_time`` / ``end_time``, which a series move keeps
       true, D4), for the span from there to the last remaining class;
    2. ``_tidy_series_in_zoom``, the forward path's own helper: one ``GET``, then a
       ``DELETE`` for each date whose class was cancelled;
    3. one occurrence ``PATCH`` per remaining class that a one-class move left at another
       time on its usual day, back to its stored time, by the ID read in step 2 (a class
       moved to another day can't be here: the series move refuses then, criterion 31);
    4. a final ``GET``, which must match the remaining classes by start and end, one to
       one; its occurrence IDs are stored on them, under the same locks.
    """
    zone = timezone.get_default_timezone()

    def on_pattern(occurrence):
        day = timezone.localdate(occurrence.starts_at)
        return (
            datetime.combine(day, link_request.start_time, tzinfo=zone),
            datetime.combine(day, link_request.end_time, tzinfo=zone),
        )

    anchor_start, anchor_end = on_pattern(remaining[0])
    _restoring_update(
        back,
        provider.update_series,
        host_account=account,
        meeting_id=link_request.meeting_id,
        starts_at=anchor_start,
        ends_at=anchor_end,
        weekdays=link_request.weekdays,
        count=len(link_request.series_span_dates(remaining)),
    )
    kept = _tidy_series_in_zoom(provider, link_request, account, remaining)
    ids_by_day = {timezone.localdate(item.starts_at): item.occurrence_id for item in kept}
    for occurrence in remaining:
        if (occurrence.starts_at, occurrence.ends_at) == on_pattern(occurrence):
            continue
        zoom_id = ids_by_day.get(timezone.localdate(occurrence.starts_at))
        if not zoom_id:
            raise _DatesDiffer()  # Zoom made no class on its day to put back
        provider.update_occurrence(
            host_account=account,
            meeting_id=link_request.meeting_id,
            occurrence_id=zoom_id,
            starts_at=occurrence.starts_at,
            ends_at=occurrence.ends_at,
        )
    first_day = timezone.localdate(remaining[0].starts_at)
    found = provider.meeting_snapshot(host_account=account, meeting_id=link_request.meeting_id)
    _store_series_ids(
        remaining, [item for item in found if timezone.localdate(item.starts_at) >= first_day]
    )


def moved_message(result, *, emailed, checks_zoom) -> tuple[int, str]:
    """``(message level, text)`` for the detail page after a move (criterion 16, P2)."""
    email = result.link_request.requester_email
    if not emailed:
        level, text = message_levels.WARNING, MOVED_EMAIL_FAILED.format(email=email)
    elif result.series:
        n = len(result.moves)
        first = result.moves[0].occurrence
        times = f"{class_time(first.starts_at)} to {class_time(first.ends_at)}"
        text = MOVED_SERIES.format(
            n=n, classes="class" if n == 1 else "classes", times=times, email=email
        )
        level = message_levels.SUCCESS
    else:
        occurrence = result.moves[0].occurrence
        level, text = message_levels.SUCCESS, MOVED_CLASS.format(when=occurrence, email=email)
    if not checks_zoom:
        text += MOVED_NOT_IN_ZOOM
    return level, text


# --------------------------------------------------------------------------- Keeping in step (013)

# Criterion 18: what "Check against Zoom" says, exactly one message per press (P1-P5, P10, G4
# and G5). ``{s}`` is the plural ending of ``{n}`` (``1 change``, ``3 changes``).
SYNC_MATCHES = "Checked with Zoom: this booking matches Zoom."
SYNC_COPIED = "Checked with Zoom: {n} change{s} copied here. We emailed {email}."
SYNC_COPIED_EMAIL_FAILED = (
    "Checked with Zoom: {n} change{s} copied here, but the email to {email} didn't send. Tell "
    "them yourself."
)
SYNC_COPIED_AND_LOOK = (
    "Checked with Zoom: {n} change{s} copied here, and some changes need a look. We emailed "
    "{email}."
)
SYNC_COPIED_AND_LOOK_EMAIL_FAILED = (
    "Checked with Zoom: {n} change{s} copied here, and some changes need a look. The email to "
    "{email} didn't send, so tell them about the copied change{s} yourself."
)
SYNC_NEEDS_A_LOOK = "Checked with Zoom: some changes need a look."
SYNC_FAILED = "We couldn't check with Zoom: {phrase}. {next_step}"
# G4: nothing to check (a stale page or a hand-made POST). The provider is asked first.
SYNC_CANT_REACH_ZOOM = "This system can't reach Zoom, so it can't check this booking."
NOTHING_LEFT_TO_CHECK = "There are no classes left to check in this booking."
# Every message the button can show, for the scan that none offers another account (c. 18).
SYNC_MESSAGES = (
    SYNC_MATCHES,
    SYNC_COPIED,
    SYNC_COPIED_EMAIL_FAILED,
    SYNC_COPIED_AND_LOOK,
    SYNC_COPIED_AND_LOOK_EMAIL_FAILED,
    SYNC_NEEDS_A_LOOK,
    SYNC_FAILED,
    SYNC_CANT_REACH_ZOOM,
    NOTHING_LEFT_TO_CHECK,
    MOVING_AT_THE_SAME_MOMENT,
)
RECONCILE_ATTEMPTS = 2
# Criterion 30 (D16): how many times reconcile asks Zoom when the booking changes between the
# ``GET`` and the lock. A second change in a row is a lock race.
RECONCILE_LOOKS = 2
# Criterion 9: the events reconcile acts on. Anything else is recorded as ``ignored`` (014
# adds recordings).
HANDLED_EVENTS = ("meeting.deleted", "meeting.updated")
# ``ReconcileResult`` / ``EventResult`` outcomes beyond ``ZoomEvent.Outcome``'s.
DUPLICATE = "duplicate"
PROVIDER_FAILED = "provider_error"
LOCK_RACE = "conflict"
FAILED = "error"
# Criterion 18 (review round 1, N2; D18): the booking had nothing left to check by the time
# reconcile ran (no remaining class, not approved, or a provider that can't reach Zoom), so
# Zoom wasn't asked. The button says so, never "matches Zoom"; the webhook records it as
# ``no_change``.
NOT_ASKED = "not_asked"
# Inside reconcile: the state it compares with when Zoom wasn't asked.
_NOT_ASKED = object()


@dataclass(frozen=True)
class ReconcileResult:
    """What ``reconcile()`` did to one booking (criteria 14-18; G6).

    ``outcome`` is a ``ZoomEvent.Outcome`` value (``changed``, ``no_change``,
    ``needs_a_look``), or ``not_asked`` (nothing left to check, so Zoom wasn't asked, N2),
    ``provider_error`` (Zoom couldn't be asked, ``error`` says why), ``conflict`` (a lock race:
    a deadlock after its one retry, a lock-wait timeout, or the booking changing under two
    ``GET``s in a row, criterion 30; ``cause`` names which, for the log) or ``duplicate``
    (the webhook's event was already recorded). ``cancelled`` and ``moved`` are what was copied here
    (``Occurrence`` and ``MovedClass`` items); ``attention`` is the booking's needs-a-look
    sentences now, and ``attention_changed`` says they're new or different, so IT was
    emailed (``it_emailed``). ``emailed`` is G6's: true only when a requester email was due
    and every one sent.
    """

    outcome: str
    link_request: LinkRequest | None = None
    cancelled: list = field(default_factory=list)
    moved: list = field(default_factory=list)
    attention: list = field(default_factory=list)
    attention_changed: bool = False
    emailed: bool = False
    it_emailed: bool = False
    error: ProviderError | None = None
    cause: str = ""

    @property
    def copied(self) -> int:
        """Criterion 18's ``{n}``: the classes copied here, ``len(cancelled) + len(moved)``."""
        return len(self.cancelled) + len(self.moved)

    @property
    def needs_a_look(self) -> bool:
        return bool(self.attention)


@dataclass(frozen=True)
class EventRecord:
    """The ``ZoomEvent`` row a webhook delivery asks ``reconcile()`` to write with its changes."""

    slug: str
    event: str
    body_sha256: str
    event_ts: int | None = None


@dataclass(frozen=True)
class EventResult:
    """What ``handle_event()`` did, for the webhook view to map to a status code (c. 10).

    ``outcome`` is a ``ZoomEvent.Outcome`` value or ``duplicate`` (200), ``provider_error``
    (503: Zoom retries) or ``error`` (500, already logged once).
    """

    outcome: str


class _Duplicate(Exception):
    """This event's row already exists: another delivery of the same body got there first."""


class BookingChangedMeanwhile(Exception):
    """The booking changed between reconcile's Zoom ``GET`` and its lock (criterion 30, D16).

    Zoom's answer may then be older than the database, so it isn't compared: the transaction
    rolls back and reconcile asks Zoom again. Its class name is what the webhook's ``ERROR``
    line names when it happens twice in a row.
    """


def sync_blocked_message(link_request, *, provider, now=None, occurrences=None):
    """Why ``Check against Zoom`` has nothing to check (G4), else ``None``.

    The provider is asked first: with ``manual`` there's never anything to check, whatever
    the booking. Then the booking must be approved with at least one remaining class. The
    detail page's ``can_sync`` is this being ``None``, so the button and the refusal agree.
    """
    if not provider.checks_zoom:
        return SYNC_CANT_REACH_ZOOM
    if link_request.status != LinkRequest.Status.APPROVED or not link_request.remaining_classes(
        now, occurrences=occurrences
    ):
        return NOTHING_LEFT_TO_CHECK
    return None


def sync_failed_message(error, label) -> str:
    """Criterion 18's "Zoom couldn't be asked" row, with P4's next step.

    The daily limit is checked before ``lasting`` (012 criterion 34): the reset sentence
    alone. A lasting error gets 011's Check-connection step, because a check is about one
    booking on one account, so "choose another account" would mean nothing here.
    """
    if isinstance(error, ZoomDailyLimit):
        step = daily_reset_sentence()
    elif error.lasting:
        step = CANCEL_NEXT_STEP_LASTING.format(label=label)
    else:
        step = NEXT_STEP_TEMPORARY
    return SYNC_FAILED.format(phrase=error.user_message, next_step=step)


def sync_message(result) -> tuple[int, str]:
    """``(message level, text)`` for the detail page after ``Check against Zoom`` (c. 18)."""
    link_request = result.link_request
    if result.outcome == PROVIDER_FAILED:
        return message_levels.ERROR, sync_failed_message(
            result.error, link_request.host_account.label
        )
    if result.outcome == LOCK_RACE:
        return message_levels.ERROR, MOVING_AT_THE_SAME_MOMENT
    if result.outcome == NOT_ASKED:
        return message_levels.ERROR, NOTHING_LEFT_TO_CHECK
    n = result.copied
    if not n:
        if result.needs_a_look:
            return message_levels.WARNING, SYNC_NEEDS_A_LOOK
        return message_levels.SUCCESS, SYNC_MATCHES
    values = {"n": n, "s": "" if n == 1 else "s", "email": link_request.requester_email}
    if result.needs_a_look:
        template = SYNC_COPIED_AND_LOOK if result.emailed else SYNC_COPIED_AND_LOOK_EMAIL_FAILED
        return message_levels.WARNING, template.format(**values)
    if result.emailed:
        return message_levels.SUCCESS, SYNC_COPIED.format(**values)
    return message_levels.WARNING, SYNC_COPIED_EMAIL_FAILED.format(**values)


def reconcile(link_request, *, provider=None, request=None, zoom_event=None) -> ReconcileResult:
    """Bring one booking into line with its meeting as Zoom holds it now (criteria 12-17, 30).

    1. **No transaction, no lock** (criterion 13): read the booking and its **fingerprint**
       (``LinkRequest.sync_fingerprint``). If it's approved with a remaining class, ask Zoom
       for the meeting (``provider.meeting_state``). A fresh ``GET`` and never the webhook's
       payload, so events arriving out of order or with a partial payload can't mislead it
       (D4). If Zoom can't be asked, nothing changes. Otherwise Zoom isn't asked at all, and
       the outcome is ``not_asked`` (N2).
    2. **One transaction** (``_reconcile_once``): write the webhook's ``ZoomEvent`` row first,
       when there is one (criterion 10: the same transaction as the changes; a duplicate
       stops here). Then lock the request, the account and the classes, in 011's order, and
       check the fingerprint again from the locked rows, **before** comparing or writing.
       Then compare the locked rows with Zoom's answer (``sync.compare``). Cancels and moves
       go through ``LinkRequest.record_cancel`` / ``record_moves``, with nobody named (G1),
       and no Zoom call: Zoom already has them. A move is copied only if the account is free
       then; anything not copied becomes a needs-a-look sentence (criteria 14-15).
    3. **After the commit**, the emails (criterion 16): the requester's (011's or 012's, with
       ``in_zoom``), and IT's when the needs-a-look sentences are new or different.

    **Why the fingerprint** (criterion 30, D16): Zoom is asked before the lock, so no HTTP runs
    under one, which leaves a gap. A move or cancel made here can commit between the ``GET``
    and the lock, and comparing Zoom's older answer with it would copy the old time back as a
    change "made in Zoom", with a false email. If the fingerprint differs under the lock,
    nothing is written, and the whole round runs once more: a new fingerprint, a new ``GET``,
    the locks again. A second change in a row is ``conflict`` (a lock race), having changed
    nothing.

    Separately, a deadlock (MySQL 1213) is retried once, as ``approve()``, ``cancel()`` and
    the moves do, without asking Zoom again; a second one, or a lock-wait timeout, is
    ``conflict`` too (G5). Call it outside an open transaction: the views are
    ``non_atomic_requests``.
    """
    provider = provider or get_provider()
    for look in range(1, RECONCILE_LOOKS + 1):
        # The connection comes with the account, so asking Zoom costs no query of its own:
        # a webhook event costs only its one lookup more than in brief 013 (015 criterion 28).
        current = LinkRequest.objects.select_related("host_account__zoom_connection").get(
            pk=link_request.pk
        )
        classes = list(current.occurrences.all())
        expected = current.sync_fingerprint(classes)
        reference, label = current.reference, current.host_account.label
        state = _NOT_ASKED
        if (
            current.status == LinkRequest.Status.APPROVED
            and provider.checks_zoom
            and current.remaining_classes(occurrences=classes)
        ):
            try:
                state = provider.meeting_state(
                    host_account=current.host_account, meeting_id=current.meeting_id
                )
            except ProviderError as exc:
                logger.warning(
                    "Couldn't check %s with Zoom on %s: %s", reference, label, type(exc).__name__
                )
                return ReconcileResult(PROVIDER_FAILED, current, error=exc)
        try:
            done = _reconcile_locked(current.pk, state, zoom_event, expected)
        except BookingChangedMeanwhile as exc:
            if look < RECONCILE_LOOKS:
                logger.info("%s changed while Zoom was being asked; asking again.", reference)
                continue
            logger.warning(
                "Checking %s with Zoom lost a lock race: it changed twice while Zoom was asked.",
                reference,
            )
            return ReconcileResult(LOCK_RACE, current, cause=type(exc).__name__)
        if isinstance(done, ReconcileResult):
            return done
        return _reconcile_emails(done, request)
    raise AssertionError("unreachable: the last look returns")


def _reconcile_locked(link_request_id, state, zoom_event, expected):
    """``_reconcile_once`` with the one deadlock retry (G5).

    A ``_Reconciled``, or the final ``ReconcileResult`` for a duplicate or a lock race.
    ``BookingChangedMeanwhile`` propagates, for ``reconcile()`` to ask Zoom again.
    """
    reference = LinkRequest(pk=link_request_id).reference
    for attempt in range(1, RECONCILE_ATTEMPTS + 1):
        try:
            return _reconcile_once(link_request_id, state, zoom_event, expected)
        except _Duplicate:
            logger.info("A repeated Zoom event for %s was ignored.", reference)
            return ReconcileResult(DUPLICATE, _booking(link_request_id))
        except OperationalError as exc:
            code = _mysql_code(exc)
            if code == MYSQL_DEADLOCK and attempt < RECONCILE_ATTEMPTS:
                logger.warning("Checking %s with Zoom hit a deadlock; trying once more.", reference)
                continue
            if code in (MYSQL_DEADLOCK, MYSQL_LOCK_WAIT_TIMEOUT):
                logger.warning(
                    "Checking %s with Zoom lost a lock race (MySQL %s).", reference, code
                )
                return ReconcileResult(
                    LOCK_RACE, _booking(link_request_id), cause=type(exc).__name__
                )
            raise
    raise AssertionError("unreachable: the last attempt returns or raises")


def _booking(link_request_id) -> LinkRequest:
    return LinkRequest.objects.select_related("host_account").get(pk=link_request_id)


@dataclass
class _Reconciled:
    """What ``_reconcile_once`` committed, for the emails that follow it."""

    outcome: str
    link_request: LinkRequest
    cancelled: list
    remaining: list
    moved: list
    attention: list
    attention_changed: bool


def _reconcile_once(link_request_id, state, zoom_event, expected) -> _Reconciled:
    """Step 2 of ``reconcile()``; MySQL lock errors propagate so the caller can retry.

    ``expected`` is the fingerprint read before Zoom was asked. If the locked rows differ,
    ``BookingChangedMeanwhile`` rolls the transaction back (the ``ZoomEvent`` row with it)
    before anything is compared or written (criterion 30).
    """
    with transaction.atomic():
        event_row = None
        if zoom_event is not None:
            try:
                event_row = ZoomEvent.objects.create(
                    slug=zoom_event.slug,
                    event=zoom_event.event,
                    body_sha256=zoom_event.body_sha256,
                    event_ts=zoom_event.event_ts,
                    outcome=ZoomEvent.Outcome.NO_CHANGE,
                )
            except IntegrityError as exc:
                if _mysql_code(exc) == MYSQL_DUPLICATE_ENTRY:
                    raise _Duplicate() from None
                raise
        link_request = LinkRequest.objects.select_for_update().get(pk=link_request_id)
        approved = link_request.status == LinkRequest.Status.APPROVED
        if approved:
            account = HostAccount.objects.locked().get(pk=link_request.host_account_id)
            link_request.host_account = account
            classes = list(link_request.occurrences.select_for_update().order_by("starts_at", "pk"))
        else:
            # Nothing changes a booking that isn't approved, and every change takes the request
            # lock first, so here the classes are read only for the fingerprint.
            classes = list(link_request.occurrences.order_by("starts_at", "pk"))
        if link_request.sync_fingerprint(classes) != expected:
            raise BookingChangedMeanwhile()

        before = link_request.zoom_attention
        now = timezone.now()
        asked = state is not _NOT_ASKED
        # Unless Zoom was asked, the sentences stay as they are: not asking isn't "finding
        # nothing to flag" (criterion 15). Only G3 below may clear them without asking.
        cancelled, moved = [], []
        lines = link_request.zoom_attention_lines
        if approved and asked:
            found = sync.compare(link_request, classes, state, now)
            if found.cancel:
                link_request.record_cancel(
                    found.cancel,
                    by=None,
                    reason=CANCELLED_IN_ZOOM_REASON,
                    now=now,
                    occurrences=classes,
                )
                cancelled = found.cancel
            accepted, lines = _moves_to_copy(account, found.moves, now)
            if accepted:
                moved = [
                    MovedClass(old_start, old_end, occurrence)
                    for old_start, old_end, occurrence in link_request.record_moves(
                        accepted, by=None, now=now, account=account
                    )
                ]
            lines += [
                ZOOM_CLASS_NOT_BOOKED.format(when=class_span(item.starts_at, item.ends_at))
                for item in found.extra
            ]
        # G3 (criterion 28): a booking with nothing left to come keeps no flag.
        if link_request.status != LinkRequest.Status.APPROVED or not (
            link_request.remaining_classes(now, occurrences=classes)
        ):
            lines = []
        attention = "\n".join(lines)
        if attention != link_request.zoom_attention:
            LinkRequest.objects.filter(pk=link_request.pk).update(zoom_attention=attention)
            link_request.zoom_attention = attention

        if not asked:
            outcome = NOT_ASKED
        elif cancelled or moved:
            outcome = ZoomEvent.Outcome.CHANGED
        elif lines:
            outcome = ZoomEvent.Outcome.NEEDS_A_LOOK
        else:
            outcome = ZoomEvent.Outcome.NO_CHANGE
        if event_row is not None:
            ZoomEvent.objects.filter(pk=event_row.pk).update(
                outcome=ZoomEvent.Outcome.NO_CHANGE if outcome == NOT_ASKED else outcome,
                link_request=link_request,
            )
    if outcome in (ZoomEvent.Outcome.CHANGED, ZoomEvent.Outcome.NEEDS_A_LOOK):
        logger.info(
            "Copied from Zoom for %s on %s: %s class(es) cancelled, %s moved, %s to look at.",
            link_request.reference,
            link_request.host_account.label,
            len(cancelled),
            len(moved),
            len(lines),
        )
    return _Reconciled(
        outcome,
        link_request,
        list(cancelled),
        link_request.classes_still_on(now, occurrences=classes),
        moved,
        lines,
        attention_changed=bool(attention) and attention != before,
    )


def _moves_to_copy(account, candidates, now) -> tuple[list, list]:
    """``(moves to copy, needs-a-look sentences)`` for the classes Zoom has at another time.

    A move is copied only when 012's time rules allow the new time (``move_errors``: the
    5-minute step, the same day, not passed, within a year) and no other booked class on the
    account overlaps it (criterion 14), checked with a locking read, as a move made here is.
    The booking's own classes count, except those being moved; a class already accepted in
    this round counts at its new time. Otherwise it stays as it is and IT is told why.
    """
    accepted, lines = [], []
    for occurrence, found in candidates:
        start, end = found.starts_at, found.ends_at
        old, new = class_moment(occurrence.starts_at), class_span(start, end)
        if occurrence.move_errors(starts_at=start, ends_at=end, now=now):
            lines.append(ZOOM_MOVE_NOT_BOOKABLE.format(old=old, new=new))
            continue
        others = Occurrence.objects.clashing(
            account,
            [(start, end)],
            exclude_ids=[occurrence.pk, *(o.pk for o, _, _ in accepted)],
            lock=True,
        ) or [o for o, s, e in accepted if s < end and start < e]
        if others:
            lines.append(
                ZOOM_MOVE_CLASHES.format(
                    old=old, new=new, label=account.label, booking=others[0].link_request
                )
            )
            continue
        if found.occurrence_id and not occurrence.zoom_occurrence_id:
            occurrence.zoom_occurrence_id = found.occurrence_id
        accepted.append((occurrence, start, end))
    return accepted, lines


def _reconcile_emails(done, request) -> ReconcileResult:
    """Criterion 16's emails, after the commit, and the final ``ReconcileResult``.

    The requester hears about classes cancelled or moved (one email of each kind at most),
    in the ``in_zoom`` form, which never claims the IT desk made the change (P6). IT hears
    only when the needs-a-look sentences are new or different, never twice for the same ones.
    """
    link_request = done.link_request
    sent = []
    if done.cancelled:
        sent.append(
            send_cancelled_email(
                request,
                link_request,
                done.cancelled,
                done.remaining,
                CANCELLED_IN_ZOOM_REASON,
                in_zoom=True,
            )
        )
    if done.moved:
        sent.append(send_moved_email(request, link_request, done.moved, in_zoom=True))
    it_emailed = False
    if done.attention_changed:
        it_emailed = send_attention_email(request, link_request, done.attention)
    return ReconcileResult(
        done.outcome,
        link_request,
        cancelled=done.cancelled,
        moved=done.moved,
        attention=done.attention,
        attention_changed=done.attention_changed,
        emailed=bool(sent) and all(sent),
        it_emailed=it_emailed,
    )


# The parsed body holds join links (and, from 014, recording download tokens): masked in error
# reports (criterion 20, review round 1, N1).
@sensitive_variables("event")
def handle_event(connection, event, body_sha256, *, provider=None, request=None) -> EventResult:
    """Act on one verified webhook event from ``connection`` (criteria 8-12, D13).

    - The same body again (Zoom's retry): ``duplicate``, with no Zoom call (criterion 8).
    - An event this brief doesn't handle, or any meeting event with a provider that can't
      ask Zoom (``manual``, D13): recorded ``ignored``. A 503 would only make Zoom retry.
    - A meeting with no booking here, or one booked on another connection's account (which
      is never touched, and logged): recorded ``not_ours``, with no Zoom call (criterion 12).
    - Otherwise ``reconcile()``, which writes the row with the changes. If it raises, or
      loses a lock race (criterion 30's second change in a row included), one ``ERROR`` line
      names the booking and the exception class, nothing is kept, and the view answers 500,
      so Zoom's retry does the work. ``not_asked`` (a cancelled booking's echo) is recorded
      and answered as ``no_change``.

    ``connection`` is ``webhooks.verify``'s ``VerifiedConnection``: bookings are matched by its
    pk (brief 015, criterion 28), and its name keys the ``ZoomEvent`` record. ``event`` is the
    parsed body; only its event name, time and meeting ID are read here.
    """
    provider = provider or get_provider()
    slug = connection.slug
    name = str(event.get("event") or "")[:60]
    event_ts = event.get("event_ts")
    record = EventRecord(
        slug, name, body_sha256, event_ts if type(event_ts) is int and event_ts >= 0 else None
    )
    if ZoomEvent.objects.filter(slug=slug, body_sha256=body_sha256).exists():
        logger.info("A repeated Zoom event on %s was ignored.", slug)
        return EventResult(DUPLICATE)
    meeting_id = _event_meeting_id(event)
    if name not in HANDLED_EVENTS or not provider.checks_zoom or not meeting_id:
        return _record_only(record, ZoomEvent.Outcome.IGNORED)

    found = list(
        LinkRequest.objects.filter(
            meeting_id=meeting_id,
            status__in=[LinkRequest.Status.APPROVED, LinkRequest.Status.CANCELLED],
        )
        .select_related("host_account")
        .order_by("pk")
    )
    ours = [lr for lr in found if lr.host_account.zoom_connection_id == connection.pk]
    if not ours:
        if found:
            logger.warning(
                "A Zoom event on %s named meeting %s, which is booked on another connection's "
                "account; it wasn't touched.",
                slug,
                meeting_id,
            )
        return _record_only(record, ZoomEvent.Outcome.NOT_OURS)
    link_request = next((lr for lr in ours if lr.status == LinkRequest.Status.APPROVED), ours[0])
    reference = link_request.reference
    try:
        result = reconcile(link_request, provider=provider, request=request, zoom_event=record)
    except Exception as exc:  # criterion 10: one ERROR line, a 500, and Zoom retries
        logger.error("A Zoom event for %s on %s failed: %s", reference, slug, type(exc).__name__)
        return EventResult(FAILED)
    if result.outcome == LOCK_RACE:
        logger.error("A Zoom event for %s on %s failed: %s", reference, slug, result.cause)
        return EventResult(FAILED)
    if result.outcome == NOT_ASKED:
        return EventResult(ZoomEvent.Outcome.NO_CHANGE)
    return EventResult(result.outcome)


@sensitive_variables("event", "payload", "item")
def _event_meeting_id(event):
    """``payload.object.id`` as digits, or ``None`` when the event doesn't carry one."""
    payload = event.get("payload")
    item = payload.get("object") if isinstance(payload, dict) else None
    value = item.get("id") if isinstance(item, dict) else None
    if type(value) is int and value > 0:
        return str(value)
    if isinstance(value, str) and value.isdigit() and len(value) <= 32:
        return value
    return None


def _record_only(record, outcome) -> EventResult:
    """Write an event's row on its own, for an event that changes no booking."""
    try:
        with transaction.atomic():
            ZoomEvent.objects.create(
                slug=record.slug,
                event=record.event,
                body_sha256=record.body_sha256,
                event_ts=record.event_ts,
                outcome=outcome,
            )
    except IntegrityError as exc:
        if _mysql_code(exc) != MYSQL_DUPLICATE_ENTRY:
            raise
        return EventResult(DUPLICATE)
    return EventResult(outcome)


# --------------------------------------------------------------------------- Start link (011)

START_SALT = "apps.zoom.start-class"
START_ZOOM_FAILED = "We couldn't reach Zoom just now. Try again in a minute."
START_MEETING_GONE = "This class's meeting isn't in Zoom any more."


def start_token(link_request) -> str:
    """One token per booking (D4): the request's pk and its meeting ID, with its own salt.

    There's no expiry inside it: the class windows are the expiry. Carrying the meeting ID
    means a booking that ever gets a new meeting kills every older link. Rotating
    ``SECRET_KEY`` kills them too, unless the old key stays in ``SECRET_KEY_FALLBACKS``.
    """
    return signing.dumps({"r": link_request.pk, "m": link_request.meeting_id}, salt=START_SALT)


def start_link(request, link_request) -> str:
    """The absolute ``zoom:start`` URL for this booking, for the email and the detail page."""
    return request.build_absolute_uri(reverse("zoom:start", args=[start_token(link_request)]))


def link_request_from_start_token(token):
    """The booking a start token names, or ``None`` when the token is invalid (criterion 19).

    Invalid: a bad signature, an unreadable payload, no such request, a request that was never
    approved, or a stored meeting ID that isn't the one in the token. A cancelled booking is
    still valid, so its page can say it was cancelled.
    """
    try:
        payload = signing.loads(token, salt=START_SALT)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict):
        return None
    pk, meeting_id = payload.get("r"), payload.get("m")
    if type(pk) is not int or not isinstance(meeting_id, str) or not meeting_id:
        return None
    link_request = (
        LinkRequest.objects.select_related("host_account__zoom_connection")
        .filter(pk=pk, status__in=[LinkRequest.Status.APPROVED, LinkRequest.Status.CANCELLED])
        .first()
    )
    if link_request is None or link_request.meeting_id != meeting_id:
        return None
    return link_request


@dataclass(frozen=True)
class StartResult:
    """The start page's state (criteria 21-23, 26). ``url`` is Zoom's ``start_url``: set only
    after a successful POST, held in memory, handed to the view for the redirect, and kept
    out of ``repr``."""

    state: str
    occurrence: Occurrence | None = None
    url: str | None = field(default=None, repr=False)
    error: str | None = None
    error_still: bool = False

    @property
    def opens_at(self):
        """When the link opens for a ``too_early`` class, else ``None``."""
        if self.state != "too_early" or self.occurrence is None:
            return None
        return self.occurrence.start_window()[0]

    @property
    def opens_after_other_class(self) -> bool:
        return self.opens_at is not None and self.occurrence.opens_after_other_class()


def start_state(link_request, *, provider=None) -> StartResult:
    """What the start page shows, with no call to Zoom (criterion 22).

    A provider that can't start (``manual``) always shows ``not_set_up``, with the class the
    booking's state points to, so the teacher can still tell the IT desk which class (G6).
    """
    provider = provider or get_provider()
    state, occurrence = link_request.start_state()
    if not provider.can_start:
        return StartResult("not_set_up", occurrence)
    return StartResult(state, occurrence)


@sensitive_variables("url")
def start_class(link_request, *, ip, provider=None) -> StartResult:
    """The start page's POST (criteria 23 and 25): one ``GET /meetings/{id}`` when ``ready``.

    In any other state nothing is sent anywhere. Each use is logged at INFO with the
    reference, the class and the client IP; a failure at WARNING with the reference and the
    error class. Neither carries the token or any URL.
    """
    provider = provider or get_provider()
    result = start_state(link_request, provider=provider)
    if result.state != "ready":
        return result
    occurrence = result.occurrence
    try:
        url = provider.start_url(
            host_account=link_request.host_account, meeting_id=link_request.meeting_id
        )
    except ZoomMeetingNotFound as exc:
        logger.warning("Start link failed for %s: %s", link_request.reference, type(exc).__name__)
        return StartResult("ready", occurrence, error=START_MEETING_GONE, error_still=False)
    except ProviderError as exc:
        logger.warning("Start link failed for %s: %s", link_request.reference, type(exc).__name__)
        return StartResult("ready", occurrence, error=START_ZOOM_FAILED, error_still=True)
    starts = occurrence.starts_at
    logger.info(
        "Start link used for %s, class %s %s, from %s",
        link_request.reference,
        class_date(starts),
        class_time(starts),
        ip or "an unknown address",
    )
    return StartResult("ready", occurrence, url=url)


def it_desk_phone():
    """The IT desk's number for the start page (criterion 47), or ``None`` when not set.

    ``{"display": "+94 11 234 5678", "tel": "+94112345678"}``: read and shown by the same
    ``normalise_phone`` / ``format_phone`` as requesters' numbers, so there's one rule for
    both. A value those can't read is ``zoom.E006`` at start-up; if one slips through anyway,
    the page says "contact the IT desk" rather than offering a dead link.
    """
    value = (settings.IT_DESK_PHONE or "").strip()
    if not value:
        return None
    try:
        e164 = normalise_phone(value)
    except ValidationError:
        return None
    return {"display": format_phone(e164), "tel": e164}


# --------------------------------------------------------------------------- Host key reveal (011)


class NoHostKeySaved(Exception):
    """``Show host key`` was pressed for an account with no key saved (criterion 41)."""


@sensitive_variables("plain")
def reveal_host_key(account, *, by) -> str:
    """Decrypt an account's host key to show it once to ``by``, and record that (D11).

    The one place a key is decrypted for showing. Every reveal writes one ``HostKeyReveal``
    row and one INFO line with the label and the user name; neither holds the key. Raises
    ``NoHostKeySaved`` or ``SecretUnreadable`` (logged at WARNING with the label), and then
    records nothing. The key goes back to the view only, and ``plain`` is masked in error
    reports (criterion 43).
    """
    if not account.has_host_key:
        raise NoHostKeySaved()
    try:
        plain = account.get_host_key()
    except SecretUnreadable:
        logger.warning("Host key for %s can't be read: InvalidToken", account.label)
        raise
    HostKeyReveal.objects.create(host_account=account, shown_by=by)
    logger.info("Host key for %s shown to %s", account.label, by.get_username())
    return plain


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
    proved before switching the site over. With no connection chosen, or one whose client
    secret can't be read, nothing is sent anywhere (brief 015, criterion 22). The connection is
    the row as loaded for this check, so a secret saved a moment ago is the one proved. The
    messages name the account, its email and the connection name, never an ID, a secret or a
    token.
    """
    provider = provider or ZoomProvider()
    label, email = account.label, account.email
    error = message_levels.ERROR
    state = account.zoom_connection_state
    if state == "none":
        return ConnectionResult(error, CHECK_NO_CONNECTION.format(label=label))
    slug = account.zoom_connection.slug
    if state == "unreadable":
        return ConnectionResult(error, CHECK_UNREADABLE.format(slug=slug))
    try:
        user_type = provider.check_connection(account)
    except ZoomAuthFailed:
        return ConnectionResult(error, CHECK_AUTH_FAILED.format(slug=slug))
    except ZoomMissingScope:
        return ConnectionResult(error, CHECK_MISSING_SCOPE.format(slug=slug))
    except ZoomUserNotFound:
        return ConnectionResult(error, CHECK_USER_NOT_FOUND.format(email=email))
    except ZoomDailyLimit as exc:
        # Before the lasting test (criterion 34): waiting *does* fix it, after the reset, and
        # there's no Zoom error number to pass on.
        return ConnectionResult(
            error,
            CHECK_DAILY_LIMIT.format(
                label=label, phrase=exc.user_message, reset=daily_reset_sentence()
            ),
        )
    except ProviderError as exc:
        # ZoomUnavailable and ZoomBusy are temporary; ZoomRejected is the lasting one here.
        template = CHECK_LASTING if exc.lasting else CHECK_TEMPORARY
        return ConnectionResult(error, template.format(label=label, phrase=exc.user_message))
    if user_type == ZOOM_BASIC_USER and account.is_paid:
        return ConnectionResult(
            message_levels.WARNING, CHECK_BASIC_USER.format(label=label, email=email)
        )
    return ConnectionResult(message_levels.SUCCESS, CHECK_WORKS.format(label=label))


# Brief 015, criteria 11 and 12: the Zoom connections pages' success flashes.
CONNECTION_ADDED = (
    "Added the Zoom connection {slug}. Next, choose it on the Zoom account that uses it, then "
    "press Check connection there."
)
CONNECTION_SAVED_UNUSED = (
    "Saved the Zoom connection {slug}. Next, choose it on the Zoom account that uses it, then "
    "press Check connection there."
)
CONNECTION_SAVED_USED = (
    "Saved the Zoom connection {slug}. To make sure Zoom accepts it, press Check connection on "
    "{labels}."
)


def connection_saved_message(connection, accounts, *, added=False) -> str:
    """The flash after a connection is added or saved (criteria 11-12).

    It says what to do next: choose the connection on an account, or, when accounts already
    use it, press Check connection on each, named with the one word-joining rule
    (``Zoom 01, Zoom 02 and Zoom 03``). The same text whether or not anything changed, so a
    Save that changed nothing reads the same (criterion 12). Names only, never a value.
    """
    if added:
        return CONNECTION_ADDED.format(slug=connection.slug)
    labels = [account.label for account in accounts]
    if not labels:
        return CONNECTION_SAVED_UNUSED.format(slug=connection.slug)
    return CONNECTION_SAVED_USED.format(slug=connection.slug, labels=join_words(labels))


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


@sensitive_variables("context")
def send_approved_email(request, link_request) -> bool:
    """The link and the app's start link, to the verified requester only: no cc, no bcc.

    Since brief 011 no email carries a host key (D3). ``start_url`` is this booking's absolute
    ``zoom:start`` link when the provider ``can_start``, and ``""`` otherwise (the manual
    provider), so the email then doesn't mention a start link at all (G5, P3).
    """
    can_start = get_provider().can_start
    context = {
        "link_request": link_request,
        "occurrences": list(link_request.occurrences.all()),
        "start_url": start_link(request, link_request) if can_start else "",
    }
    return _send("approval", "approved", context, [link_request.requester_email], link_request)


def absolute_url(request, path) -> str:
    """``path`` as an absolute URL, for emails, with or without a request (brief 013).

    With a request it's ``build_absolute_uri``, as every email had until now: the webhook's
    request comes to the production domain, so its links do too. ``sync_zoom_bookings`` runs
    with no request, so it uses the first concrete name in ``ALLOWED_HOSTS`` (production
    refuses to start with none) and ``USE_HTTPS`` for the scheme. Settings only, no env read.
    """
    if request is not None:
        return request.build_absolute_uri(path)
    hosts = [h for h in settings.ALLOWED_HOSTS if h and not h.startswith(".") and "*" not in h]
    scheme = "https" if settings.USE_HTTPS else "http"
    return f"{scheme}://{hosts[0] if hosts else 'localhost'}{path}"


def send_cancelled_email(
    request, link_request, cancelled, remaining, reason, *, in_zoom=False
) -> bool:
    """Tell the requester what was cancelled and why (brief 011, criterion 17).

    To the requester only. It carries no join link, passcode, start link or host key: the
    cancelled classes don't need one, and the others keep what the approval email gave.
    ``can_start`` picks the "still on" sentence, so the manual provider's version doesn't
    mention a start link it never sent (G5, P3). ``in_zoom`` (brief 013, G2) is for a cancel
    copied from Zoom: the opening says it was cancelled directly in Zoom instead of naming the
    IT desk, which may not have made it (P6). ``request`` may be ``None`` (the nightly run).
    """
    context = {
        "link_request": link_request,
        "cancelled": list(cancelled),
        "remaining": list(remaining),
        "reason": reason,
        "request_url": absolute_url(request, reverse("zoom:request")),
        "can_start": get_provider().can_start,
        "in_zoom": in_zoom,
    }
    return _send("cancellation", "cancelled", context, [link_request.requester_email], link_request)


def send_moved_email(request, link_request, moves, *, in_zoom=False) -> bool:
    """Tell the requester the old and new times of every class a move changed (brief 012, 18).

    To the requester only, after the commit. ``moves`` is the ``MoveResult``'s list of
    ``MovedClass`` (``old_start``, ``old_end``, ``occurrence``), soonest first. It carries no
    join link, passcode, start link or host key: the links don't change (D1), so the email only
    says so, and ``can_start`` keeps the manual provider's version from mentioning a start
    link it never sent (G3, P3). ``in_zoom`` as for ``send_cancelled_email`` (brief 013, P6).
    ``request`` is unused, kept so every sender has one shape.
    """
    context = {
        "link_request": link_request,
        "moves": list(moves),
        "can_start": get_provider().can_start,
        "in_zoom": in_zoom,
    }
    return _send("classes moved", "moved", context, [link_request.requester_email], link_request)


def send_attention_email(request, link_request, lines) -> bool:
    """Tell IT what couldn't be copied from Zoom, and where to fix it (brief 013, c. 16).

    To every IT recipient (005 D9), one message each. Sent only when the sentences are new or
    different (``reconcile`` decides), so the same mismatch never mails IT twice. It names the
    booking and the account, never a link other than the booking's own page. ``request`` may
    be ``None`` (the nightly run): ``absolute_url`` then builds ``detail_url``.
    """
    recipients = it_recipients()
    if not recipients:
        logger.warning(
            "Nobody can be told %s needs a look: no active user has %s.",
            link_request.reference,
            REVIEW_PERMISSION,
        )
        return False
    context = {
        "link_request": link_request,
        "lines": list(lines),
        "detail_url": absolute_url(request, reverse("zoom:detail", args=[link_request.pk])),
    }
    return _send("needs a look", "attention", context, recipients, link_request)


def send_rejected_email(request, link_request) -> bool:
    """The reason, and where to send a new request."""
    context = {
        "link_request": link_request,
        "request_url": request.build_absolute_uri(reverse("zoom:request")),
    }
    return _send("not approved", "rejected", context, [link_request.requester_email], link_request)
