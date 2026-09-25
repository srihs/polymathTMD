"""Work that spans several models, the meeting provider or the outside world (brief 005).

- ``approve()``: the conflict-free booking (D5). It locks, re-checks, writes the booking and
  its slots, then asks the provider for the meeting, all in one transaction, so any failure
  leaves nothing booked.
- The confirmation token (D8): signed and expiring, carrying only the request's pk, so no
  token column is needed.
- ``client_ip()`` and ``is_throttled()``: the abuse limits, counted in the database.
- The four emails. They're sent after the model change, synchronously, and a send failure is
  logged and reported but never undoes a decision (D9).

Logging rule for this module (criteria 41, 64, 65): log references, account labels and
exception class names only. Never a host key, join link, passcode, token or exception text.
"""

import ipaddress
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMessage, get_connection
from django.db import IntegrityError, OperationalError, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import HostAccount, HostKeyUnreadable, HostSlot, LinkRequest, Occurrence
from .providers import ProviderError, get_provider

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

# User-facing copy pinned by the brief's criteria.
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
PROVIDER_FAILED = (
    "Zoom didn't create the meeting: {error}. Nothing was booked. Try again in a few minutes."
)
THROTTLED = (
    "You've sent a lot of requests in the last hour. Wait an hour, then try again, "
    "or phone the IT desk."
)


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


# --------------------------------------------------------------------------- Approval


def approve(link_request_id, *, account_id, by, manual=None, provider=None) -> ApproveResult:
    """Book ``account_id`` for every class of the request and make the meeting (D5).

    Order inside the transaction, always the same so concurrent approvals queue rather than
    deadlock where possible:

    1. lock the request row, then re-check it is still waiting and not started;
    2. lock the account row (it must still be active and paid);
    3. decrypt the host key now, so an unreadable key fails before anything is written;
    4. re-check clashes with a locking read (``availability_for(lock=True)``);
    5. set the account on every class and insert the 5-minute slots (the unique slot index
       is the backstop if anything slipped past step 4);
    6. call the provider; then save the meeting details and the decision.

    Any exception rolls all of it back. Emails are the caller's job, after this returns, so a
    mail failure can never undo a booking. Call it outside any open transaction (the approve
    view is ``non_atomic_requests``): a MySQL deadlock rolls back the whole transaction, not
    just a savepoint.

    A deadlock (MySQL 1213) is retried once, because MySQL already rolled the attempt back and
    the other transaction has usually finished; a second deadlock or a lock-wait timeout (1205)
    returns ``conflict`` with ``APPROVING_AT_THE_SAME_MOMENT``.
    """
    provider = provider or get_provider()
    reference = LinkRequest(pk=link_request_id).reference
    for attempt in range(1, APPROVE_ATTEMPTS + 1):
        try:
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


# host_key is decrypted here: keep it out of error reports (tracebacks, ADMINS error emails).
@sensitive_variables("host_key")
def _approve_once(link_request_id, *, account_id, by, manual, provider) -> ApproveResult:
    """One attempt of ``approve()``; MySQL lock errors propagate so the caller can retry."""
    reference = LinkRequest(pk=link_request_id).reference
    label = ""
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

            meeting = provider.create_meeting(
                link_request=link_request,
                host_account=account,
                occurrences=occurrences,
                manual=manual,
            )
            link_request.status = LinkRequest.Status.APPROVED
            link_request.host_account = account
            link_request.decided_by = by
            link_request.decided_at = timezone.now()
            link_request.meeting_id = meeting.meeting_id
            link_request.join_url = meeting.join_url
            link_request.passcode = meeting.passcode
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
        logger.warning("The meeting provider failed for %s; nothing was booked.", reference)
        return ApproveResult(Outcome.PROVIDER_ERROR, PROVIDER_FAILED.format(error=exc.user_message))
    except IntegrityError as exc:
        if _mysql_code(exc) != MYSQL_DUPLICATE_ENTRY:
            raise
        logger.warning("Approving %s hit the slot backstop; another booking won.", reference)
        return ApproveResult(Outcome.CONFLICT, BOOKED_A_MOMENT_AGO.format(label=label))
    return ApproveResult(
        Outcome.APPROVED,
        f"Approved. The link was emailed to {link_request.requester_email}.",
        link_request,
        host_key,
    )


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
