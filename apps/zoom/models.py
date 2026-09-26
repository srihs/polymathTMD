"""Zoom link requests: who asked, for which classes, and which host account is booked.

Why the data is shaped like this (brief 005):

- Every class is stored as its own ``Occurrence``. The spreadsheet IT used before had one
  row per date, and a clash is a question about single classes, not about patterns.
- ``HostSlot`` is the database-level guarantee against double booking (D5). MySQL has no
  exclusion constraints, so each booked class is cut into 5-minute slots and a unique
  ``(host_account, starts_at)`` makes a second booking of the same 5 minutes on one account
  impossible to store, whatever code path tries. That's why times must sit on 5-minute steps.
- The schedule and the status rules live here (``clean()``, the QuerySets and the transition
  methods) so views stay thin and every path (the forms, the shell, ``services.approve()``)
  gets the same answers.
- Host keys are the one secret stored (D17). They are encrypted through ``crypto.py`` and only
  reachable through ``set_host_key`` / ``get_host_key``, never as a plain field.
- Host accounts are managed on the in-app Zoom accounts page (brief 008); the project doesn't
  use the Django admin. Taking an account out of use while classes are still booked on it is
  refused here, on the model (``stop_booking_errors``), so no screen can skip the rule.
- The Zoom connection (brief 006) is named here (``credential_set``) but its credentials live
  only in the server's environment (``settings.ZOOM_S2S_SECRETS``). ``zoom_connection_state``
  and ``is_zoom_connected()`` are the one definition of "connected": they read settings only,
  never the network or the database. ``LinkRequest.zoom_marker`` is the one definition of the
  agenda marker that lets a retry find a meeting left in Zoom by a failed attempt.
- Cancelling (brief 011) never deletes a row. A cancelled class keeps who cancelled it, when
  and why, and its slots are removed so the account is free again. ``BOOKED`` leaves cancelled
  classes out, so every screen built on ``booked()`` (the clash check, the timetable, the
  accounts' upcoming counts) follows without a second rule. The cancel rules, the start-link
  window and the start page's state are methods here, so the views and ``services`` only ask.
- ``HostKeyReveal`` (brief 011, D11) records each time the IT desk was shown a host key, and
  never the key itself.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import dateformat, timezone
from django.views.decorators.debug import sensitive_variables

from . import crypto
from .crypto import HostKeyUnreadable  # noqa: F401  (re-exported: callers catch it from here)
from .validators import (
    format_phone,
    normalise_phone,
    validate_credential_set,
    validate_host_key,
)

SLOT_MINUTES = 5

WEEKDAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}
WEEKDAY_CHOICES = [(str(number), name) for number, name in WEEKDAY_NAMES.items()]

# The queue's tabs, in display order: (status value or "all", label). Criterion 20.
QUEUE_TABS = (
    ("waiting", "Waiting"),
    ("approved", "Link sent"),
    ("rejected", "Not approved"),
    ("cancelled", "Cancelled"),
    ("all", "All"),
)
DEFAULT_QUEUE_TAB = "waiting"

# Copy pinned by criterion 6. It lives with the rules that raise it.
CLASS_NAME_REQUIRED = "Type the name of the class, like CCC Batch 3 - Mathematics."
END_BEFORE_START = "The class must end after it starts. Check the end time."
TIME_STEP = "Use a time on a 5-minute step, like 8:30 or 8:35."
DATE_PASSED = "Choose a date and time that haven't passed yet."
DATE_TOO_FAR = "Choose a date within the next year."
NO_WEEKDAYS = "Tick at least one day of the week."
LAST_DATE_NEEDED = "Choose the date of the last class, on or after the first class."
NO_DAY_IN_RANGE = "None of the days you ticked fall between the first and last class dates."
TOO_MANY_CLASSES = (
    "That makes {n} classes. One request can cover up to {max}. Choose an earlier last date, "
    "or send a second request for the rest."
)
REASON_REQUIRED = "Tell the requester why, so they can fix it and ask again."

# Brief 008, criterion 17: why an account can't stop being bookable yet. ``{what}`` comes from
# STOP_BOOKING_WHAT, keyed by the field whose tick was removed. Brief 011, criterion 33 adds
# "or been cancelled", now that a class can stop holding the account that way too.
STOP_BOOKING_MANY = (
    "{label} still has {n} booked classes, from {first} to {last}. It can be {what} once the "
    "last one has finished or been cancelled."
)
STOP_BOOKING_MANY_SAME_DAY = (
    "{label} still has {n} booked classes, on {first}. It can be {what} once the last one has "
    "finished or been cancelled."
)
STOP_BOOKING_ONE = (
    "{label} still has 1 booked class, on {first}. It can be {what} once it has finished or "
    "been cancelled."
)
STOP_BOOKING_WHAT = {"is_active": "taken out of use", "is_paid": "marked as free"}

# Brief 011, criterion 6: why there's nothing to cancel. They live beside the rules that
# raise them (``cancel_booking_blocked_message`` and ``Occurrence.cancel_blocked_message``),
# and the detail page shows the whole-booking ones too (G2), so the text is written once.
CANCEL_IN_PROGRESS = (
    "{occurrence} is in progress. Cancel the rest of this booking after it ends at {end}."
)
NOTHING_LEFT_TO_CANCEL = "There are no classes left to cancel in this booking."
CLASS_STARTED = "That class has already started, so it can't be cancelled."
CLASS_ALREADY_CANCELLED = "That class was already cancelled."
CANCEL_REASON_REQUIRED = "Tell the requester why it's cancelled."


class InvalidTransition(Exception):
    """A status change was asked for from a status that doesn't allow it.

    Raised instead of silently doing nothing, so the caller can tell the user the request was
    already confirmed or decided (criteria 15 and 39).
    """


def queue_tab(value) -> str:
    """The queue tab to show for a ``?status=`` value; unknown values fall back to Waiting."""
    return value if value in dict(QUEUE_TABS) else DEFAULT_QUEUE_TAB


def class_time(value) -> str:
    """``8:30 am``, the one time format for pages and emails (the ``class_time`` filter).

    Django's ``a`` format gives ``a.m.``, which the design doesn't want. Aware datetimes are
    shown in ``TIME_ZONE`` (Colombo), so a UTC value from the database reads as local time.
    """
    if value in (None, ""):
        return ""
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return dateformat.time_format(value, "g:i A").lower()


def class_date(value, *, year=True) -> str:
    """``Mon 5 Oct 2026``, the one date format for pages and emails (the ``class_date`` filter)."""
    if value in (None, ""):
        return ""
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return dateformat.format(value, "D j M Y" if year else "D j M")


def _join_words(words) -> str:
    """``Monday``, ``Monday and Wednesday``, ``Monday, Wednesday and Friday``."""
    words = list(words)
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


# --------------------------------------------------------------------------- Host accounts

# What makes an account bookable, defined once (brief 008, criterion 16): ``BOOKABLE`` filters
# in the database, and ``is_bookable_with`` answers the same question for unsaved flag values.
BOOKABLE_FLAGS = {"is_active": True, "is_paid": True}
BOOKABLE = Q(**BOOKABLE_FLAGS)


def is_bookable_with(**flags) -> bool:
    """True when these flag values (``is_active=…, is_paid=…``) would make an account bookable."""
    return all(bool(flags[name]) == wanted for name, wanted in BOOKABLE_FLAGS.items())


def zoom_connection_state_for(credential_set) -> str:
    """``"none"``, ``"missing"`` or ``"ready"`` for a connection name (brief 006, criterion 35).

    A module function so the change page can ask about the *stored* name even after an
    invalid submit has put the typed one on the instance. Settings only: no query, no HTTP.
    """
    if not credential_set:
        return "none"
    if credential_set not in settings.ZOOM_S2S_SECRETS:
        return "missing"
    return "ready"


class HostAccountQuerySet(models.QuerySet):
    def bookable(self):
        """Accounts IT may book. Free accounts cut meetings at 40 minutes, so never those."""
        return self.filter(BOOKABLE)

    def with_upcoming(self, now=None):
        """Adds ``upcoming_count`` (int) and ``next_class_start`` (aware datetime or None).

        Both are correlated subqueries built from ``Occurrence.objects.booked().upcoming()``,
        so "upcoming class" keeps one definition, and the whole list stays one query however
        many accounts or classes there are (brief 008, criterion 6). A class in progress
        counts; one that has ended doesn't.
        """
        upcoming = (
            Occurrence.objects.booked()
            .upcoming(now)
            .filter(host_account=OuterRef("pk"))
            .order_by()
            .values("host_account")
        )
        return self.annotate(
            upcoming_count=Coalesce(
                Subquery(upcoming.annotate(n=Count("pk")).values("n")), Value(0)
            ),
            next_class_start=Subquery(upcoming.annotate(first=Min("starts_at")).values("first")),
        )

    def for_management(self):
        """The Zoom accounts list: in use first, then by order and name, with upcoming figures."""
        return self.with_upcoming().order_by("-is_active", "sort_order", "label")

    def with_timetable_flag(self, start, end):
        """Every account, with ``on_timetable``: True when it belongs in the timetable filter.

        That's an account IT may book (the shared ``BOOKABLE`` rule, brief 008), or one with a
        booked class starting in ``[start, end)``, so an account taken out of use still shows
        in the months it hosted classes (brief 009, criterion 11). The class test is an
        ``EXISTS`` subquery built from ``Occurrence.objects.booked()``, so "booked" keeps one
        definition, and the whole list is one query.

        The timetable views read *all* accounts through this, rather than only the flagged
        ones, so the same single query also resolves an ``?account=`` pk that isn't an option
        and tells whether any account exists at all ("No Zoom accounts are set up yet."). There
        are only a handful of accounts, so reading every one costs nothing.

        ``only()`` loads just what the timetable reads (``pk``, ``label``, and ``sort_order``
        for the order), so the encrypted host key and the notes never leave the database on a
        page that has no use for them (review round 1, nit 3). Reading any other field on these
        objects would cost a query per account, which the fixed query-count tests would catch.
        """
        booked_here = (
            Occurrence.objects.booked().in_period(start, end).filter(host_account=OuterRef("pk"))
        )
        return (
            self.only("pk", "label", "sort_order")
            .annotate(
                on_timetable=Case(
                    When(BOOKABLE | Q(Exists(booked_here)), then=Value(True)),
                    default=Value(False),
                    output_field=models.BooleanField(),
                )
            )
            .order_by("sort_order", "label")
        )

    def timetable_accounts(self, start, end):
        """The timetable filter's options: bookable accounts plus any with a booked class in
        ``[start, end)``, ordered by ``(sort_order, label)``. One query (criterion 17)."""
        return self.with_timetable_flag(start, end).filter(on_timetable=True)

    def availability_for(self, occurrences, *, lock=False):
        """For each bookable account: ``(account, clashes)``, clash = ``(occurrence, other)``.

        One function backs both the preview on the detail page and the re-check inside the
        approval transaction, so they can never disagree about what a clash is (D6: overlap,
        not touch, among approved bookings only).

        The query count is fixed (two queries, whatever the number of classes or accounts):
        the approved classes of every bookable account inside ``[first start, last end]`` are
        fetched once and matched in Python.

        ``lock=True`` is for the approval transaction. It makes both reads locking reads
        (``SELECT … FOR UPDATE``). Under MySQL's REPEATABLE READ a plain read can come from a
        snapshot taken before this transaction waited for the account lock, and would miss a
        booking committed a moment ago; a locking read always sees the latest committed rows.
        """
        accounts_qs = self.bookable()
        if lock:
            accounts_qs = accounts_qs.select_for_update()
        accounts = list(accounts_qs)
        occurrences = list(occurrences)
        if not accounts or not occurrences:
            return [(account, []) for account in accounts]

        booked = (
            Occurrence.objects.booked()
            .filter(host_account__in=accounts)
            .overlapping(min(o.starts_at for o in occurrences), max(o.ends_at for o in occurrences))
            .select_related("link_request")
            .order_by("starts_at", "pk")
        )
        if lock:
            booked = booked.select_for_update()
        by_account = defaultdict(list)
        for other in booked:
            by_account[other.host_account_id].append(other)

        return [
            (
                account,
                [
                    (occurrence, other)
                    for occurrence in occurrences
                    for other in by_account[account.pk]
                    if occurrence.overlaps(other)
                ],
            )
            for account in accounts
        ]


class HostAccount(models.Model):
    """A Zoom user that can host meetings. Managed on the Zoom accounts page by the IT desk
    (brief 008).

    Accounts are taken out of use, never deleted (``PROTECT``, and no screen deletes), so the
    history of who hosted what stays intact. The host key is stored encrypted, with a record of
    when and by whom it was last changed (brief 008, D3).

    A host key is never shown back on the account's pages or in any list or email. An IT desk
    member can show it on its own page as a fallback, and every time it's shown is recorded.
    (Brief 011, D11 and criterion 45: this amends brief 008's "write-only" rule. The one place
    a key is decrypted for showing is ``services.reveal_host_key()``, which writes a
    ``HostKeyReveal`` row each time.)
    """

    # Uniqueness of the name and the email ignores letter case because the columns use the
    # case-insensitive ``utf8mb4_0900_ai_ci`` collation, pinned for the server in compose.yaml
    # (``--collation-server``) and for the test database in ``DATABASES["default"]["TEST"]``
    # in config/settings/base.py. A case-sensitive collation would let "Zoom 01" and "zoom 01"
    # both be saved (brief 008, criterion 22).
    label = models.CharField(
        "name",
        max_length=60,
        unique=True,
        help_text="IT's short name for the account, like Zoom 01.",
    )
    email = models.EmailField(
        "Zoom sign-in email",
        unique=True,
        help_text="The email address this Zoom account signs in with.",
    )
    is_paid = models.BooleanField(
        "paid account",
        default=True,
        help_text="Untick for free accounts. Free accounts end meetings after 40 minutes, "
        "so they are never booked.",
    )
    is_active = models.BooleanField(
        "in use",
        default=True,
        help_text="Untick to stop booking this account. Accounts with bookings can't be "
        "deleted, only taken out of use.",
    )
    sort_order = models.PositiveSmallIntegerField(
        "order",
        default=0,
        help_text="Lower numbers are suggested first when several accounts are free.",
    )
    # Only the *name* of the connection. The credentials themselves are in the server's
    # environment and never in the database (brief 006, D2).
    credential_set = models.SlugField(
        "Zoom connection name",
        max_length=40,
        blank=True,
        validators=[validate_credential_set],
        help_text="The name of this account's Zoom connection on the server, like zoom-01. "
        "Whoever looks after the server tells you the name.",
    )
    # Fernet token, never the key itself (D17). Read and written only by the methods below.
    host_key_encrypted = models.TextField(
        "host key (encrypted)",
        blank=True,
        editable=False,
        help_text="Set it on the Zoom accounts page.",
    )
    # When and by whom the key was last stored or removed: the only history of a key change,
    # since no partial key is ever shown (brief 008, D3).
    host_key_changed_at = models.DateTimeField(
        "host key last changed",
        null=True,
        blank=True,
        editable=False,
        help_text="When a host key was last saved or removed. Empty for keys saved before this "
        "was recorded.",
    )
    host_key_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
        verbose_name="host key last changed by",
        help_text="Who last saved or removed the host key.",
    )
    notes = models.TextField("notes", blank=True, help_text="Anything IT should remember.")

    objects = HostAccountQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "label"]
        verbose_name = "Zoom host account"
        verbose_name_plural = "Zoom host accounts"

    def __str__(self):
        return f"{self.label} ({self.email})"

    def __repr__(self):
        # Spelled out so the key can never reach a traceback or log through repr().
        return f"<HostAccount: {self.label}>"

    def clean(self):
        """Trim and lower-case the sign-in email, so uniqueness compares like with like."""
        if self.email:
            self.email = self.email.strip().lower()

    # Applied directly, not via method_decorator: its wrapper frame would show the args.
    @sensitive_variables("plain")
    def set_host_key(self, plain, *, by=None) -> None:
        """Encrypt and store ``plain``; an empty value removes the saved key.

        Raises ``ValidationError`` unless the key is 6 to 10 digits (criterion 60). Storing a
        key, or removing a saved one, records when and by whom (brief 008, criterion 21), the
        only history a key has. Clearing when nothing is saved changes nothing. Rotation
        doesn't come through here, so re-encrypting never looks like a person changed the key.
        """
        plain = (plain or "").strip()
        if not plain:
            if self.host_key_encrypted:
                self.host_key_encrypted = ""
                self._record_host_key_change(by)
            return
        validate_host_key(plain)
        self.host_key_encrypted = crypto.encrypt(plain)
        self._record_host_key_change(by)

    def _record_host_key_change(self, by):
        self.host_key_changed_at = timezone.now()
        self.host_key_changed_by = by

    def get_host_key(self) -> str:
        """The plaintext key, ``""`` if none is saved; ``HostKeyUnreadable`` if undecryptable."""
        if not self.host_key_encrypted:
            return ""
        return crypto.decrypt(self.host_key_encrypted)

    @property
    def has_host_key(self) -> bool:
        return bool(self.host_key_encrypted)

    @property
    def host_key_state(self) -> str:
        """``"none"``, ``"unreadable"``, ``"saved"``, or ``"saved_legacy"`` (no change record).

        It decrypts only to tell a readable key from an unreadable one, and drops the plaintext
        at once: the result is never kept, returned or bound to a name an error report could
        show.
        """
        if not self.host_key_encrypted:
            return "none"
        try:
            self.get_host_key()
        except HostKeyUnreadable:
            return "unreadable"
        return "saved" if self.host_key_changed_at else "saved_legacy"

    @property
    def zoom_connection_state(self) -> str:
        """``"none"`` (no name), ``"missing"`` (not on the server) or ``"ready"``."""
        return zoom_connection_state_for(self.credential_set)

    def is_zoom_connected(self) -> bool:
        """The one definition used by the preview, ``approve()`` and check ``zoom.E004``."""
        return self.zoom_connection_state == "ready"

    @property
    def needs_zoom_connection(self) -> bool:
        """True when this account can be booked, so a missing Zoom connection matters.

        A free account or one out of use is never booked, so it never needs a connection; the
        accounts list shows its "Not set up" plainly rather than as a warning (brief 006,
        D.2.2). Built on ``is_bookable_with`` so the template never repeats the bookable rule
        (review round 1, SF2). It says nothing about whether a connection is set up: that's
        ``zoom_connection_state``.
        """
        return is_bookable_with(is_active=self.is_active, is_paid=self.is_paid)

    def rotate_host_key(self) -> bool:
        """Re-encrypt the saved key with the first configured key. False when none is saved."""
        if not self.host_key_encrypted:
            return False
        self.host_key_encrypted = crypto.rotate(self.host_key_encrypted)
        return True

    # ----------------------------------------------------------------------- key reveals

    def last_key_reveal(self):
        """The latest ``HostKeyReveal`` with its ``shown_by`` user, or ``None`` (criterion 44)."""
        return self.key_reveals.select_related("shown_by").order_by("-shown_at", "-pk").first()

    def key_reveal_count(self) -> int:
        """How many times this account's key has been shown, ever (criterion 44)."""
        return self.key_reveals.count()

    # ----------------------------------------------------------------------- booked classes

    def upcoming_classes(self, now=None):
        """This account's booked classes that haven't ended yet, soonest first."""
        return (
            Occurrence.objects.booked()
            .filter(host_account=self)
            .upcoming(now)
            .order_by("starts_at", "pk")
        )

    def stop_booking_errors(self, *, is_active, is_paid, now=None) -> dict[str, str]:
        """Field errors for removing the ``is_active`` / ``is_paid`` tick while classes are booked.

        An account can't stop being bookable while it still has upcoming classes, or they'd be
        left on an account IT no longer uses (owner, Q2; brief 008, D8). Only a change from
        bookable to not bookable is refused, and the error goes on each tick being *removed*.
        An account that was already out of use or free can still have its other details, or
        its other tick, saved (review round 1, nit 1).

        When the account is staying bookable, or wasn't bookable before, nothing is queried.
        Otherwise there's one locking read of the upcoming classes *and* their requests
        (``SELECT … FOR UPDATE OF zoom_occurrence, zoom_linkrequest``), and the count and dates
        are worked out in Python from the locked rows (criterion 19).

        Why both tables (review round 1, B1): "booked" is decided by the request's ``status``.
        A locking read reads the latest committed version of the rows it locks, but a table it
        doesn't lock is read from the transaction's snapshot. At REPEATABLE READ that snapshot
        can predate an approval that committed while this edit waited for the account lock:
        the class would be seen on the account, its request still ``waiting``, and the class
        dropped from the count. Django runs MySQL at READ COMMITTED, where a fresh snapshot is
        taken per statement, but locking both tables makes the check right at either level.

        The caller must already hold this account's row lock in the same transaction, as the
        edit view does. ``services.approve()`` takes that lock before it books, so no approval
        can slip in between this check and the save. Locking the requests here, after the
        account, can't deadlock with ``approve()``, which locks a request before the account:
        while this edit holds the account, the only requests it reaches are ones whose classes
        are already on it, and ``approve()`` only puts a request's classes on an account after
        it holds that account's lock.
        """
        if not self.pk or is_bookable_with(is_active=is_active, is_paid=is_paid):
            return {}
        if not is_bookable_with(is_active=self.is_active, is_paid=self.is_paid):
            return {}
        new_values = {"is_active": is_active, "is_paid": is_paid}
        unticked = [name for name, value in new_values.items() if getattr(self, name) and not value]
        starts = [
            occurrence.starts_at
            for occurrence in self.upcoming_classes(now)
            .select_related("link_request")
            .only("starts_at", "link_request__id")
            .select_for_update(of=("self", "link_request"))
        ]
        if not starts:
            return {}
        first, last = class_date(starts[0]), class_date(starts[-1])
        if len(starts) == 1:
            template = STOP_BOOKING_ONE
        elif first == last:
            template = STOP_BOOKING_MANY_SAME_DAY
        else:
            template = STOP_BOOKING_MANY
        return {
            name: template.format(
                label=self.label,
                n=len(starts),
                first=first,
                last=last,
                what=STOP_BOOKING_WHAT[name],
            )
            for name in unticked
        }


# --------------------------------------------------------------------------- Link requests


class LinkRequestQuerySet(models.QuerySet):
    def visible_to_it(self):
        """Requests whose email was never confirmed are invisible to IT (criterion 16)."""
        return self.exclude(status=LinkRequest.Status.UNVERIFIED)

    def waiting(self):
        return self.filter(status=LinkRequest.Status.WAITING)

    def with_schedule(self):
        """Adds ``first_start`` and ``occurrence_count`` so lists need no per-row queries."""
        return self.annotate(
            first_start=Min("occurrences__starts_at"),
            occurrence_count=Count("occurrences"),
        ).select_related("host_account", "decided_by")

    def for_tab(self, tab):
        """Filter and order for a queue tab (criterion 20). Unknown tabs mean Waiting."""
        tab = queue_tab(tab)
        qs = self if "first_start" in self.query.annotations else self.with_schedule()
        if tab == "all":
            return qs.order_by("-created_at", "-pk")
        qs = qs.filter(status=tab)
        if tab == LinkRequest.Status.WAITING:
            return qs.order_by("first_start", "pk")
        if tab == LinkRequest.Status.CANCELLED:
            return qs.order_by("-cancelled_at", "-pk")
        return qs.order_by("-decided_at", "-pk")

    def tab_counts(self) -> dict:
        """The count for every queue tab, in one aggregate query, never counting unverified."""
        status = LinkRequest.Status
        return self.visible_to_it().aggregate(
            waiting=Count("pk", filter=Q(status=status.WAITING)),
            approved=Count("pk", filter=Q(status=status.APPROVED)),
            rejected=Count("pk", filter=Q(status=status.REJECTED)),
            cancelled=Count("pk", filter=Q(status=status.CANCELLED)),
            all=Count("pk"),
        )

    def search(self, q):
        """Criterion 22: reference, class, name, email, or phone digits.

        ``ZL-0007``, ``zl-7`` and ``7`` all mean pk 7. A phone number is matched in its stored
        E.164 form (``0771234567`` finds ``+94771234567``), and six or more digits also match
        anywhere in the number, so a partial number works too.
        """
        q = (q or "").strip()
        if not q:
            return self
        condition = (
            Q(class_name__icontains=q)
            | Q(requester_name__icontains=q)
            | Q(requester_email__icontains=q)
        )
        reference = re.fullmatch(r"(?:zl-?)?(\d{1,18})", q, re.IGNORECASE)
        if reference:
            condition |= Q(pk=int(reference.group(1)))
        try:
            condition |= Q(requester_phone=normalise_phone(q))
        except ValidationError:
            pass
        digits = re.sub(r"\D", "", q).lstrip("0")
        if len(digits) >= 6:
            condition |= Q(requester_phone__contains=digits)
        return self.filter(condition)

    def recent_from(self, *, email=None, ip=None, minutes=60):
        """Requests created in the last ``minutes`` from this email and/or IP, any status.

        Counted in the database so the hourly limits hold across Gunicorn workers without a
        shared cache (D8).
        """
        qs = self.filter(created_at__gte=timezone.now() - timedelta(minutes=minutes))
        if email is not None:
            qs = qs.filter(requester_email__iexact=email.strip())
        if ip is not None:
            qs = qs.filter(submitted_ip=ip)
        return qs

    def overlapping_waiting(self, link_request, occurrences=None):
        """Other waiting requests with a class overlapping any class of ``link_request``.

        Waiting requests don't block each other (D6), but IT should see them before deciding
        (criterion 29). Each result carries ``first_overlap``: the earliest start among *its*
        classes that overlap this request, and the list is ordered by it. Fixed query count.
        """
        occurrences = list(link_request.occurrences.all() if occurrences is None else occurrences)
        if not occurrences:
            return []
        candidates = (
            Occurrence.objects.filter(link_request__status=LinkRequest.Status.WAITING)
            .exclude(link_request_id=link_request.pk)
            .overlapping(min(o.starts_at for o in occurrences), max(o.ends_at for o in occurrences))
            .order_by("starts_at", "pk")
        )
        first_overlap = {}
        for other in candidates:
            if other.link_request_id in first_overlap:
                continue
            if any(other.overlaps(mine) for mine in occurrences):
                first_overlap[other.link_request_id] = other.starts_at
        if not first_overlap:
            return []
        found = list(self.filter(pk__in=first_overlap).with_schedule())
        for item in found:
            item.first_overlap = first_overlap[item.pk]
        return sorted(found, key=lambda item: (item.first_overlap, item.pk))

    def earlier_from_same_requester(self, link_request, limit=5):
        """Up to ``limit`` other requests IT can see from the same email, newest first."""
        return (
            self.visible_to_it()
            .filter(requester_email__iexact=link_request.requester_email)
            .exclude(pk=link_request.pk)
            .order_by("-created_at", "-pk")[:limit]
        )


class LinkRequest(models.Model):
    """One request, from one person, for one class schedule (one-off or weekly).

    Status moves only forward: unverified → waiting → approved | rejected; approved →
    cancelled. ``unverified`` means the email isn't confirmed yet, ``waiting`` is IT's queue,
    and ``rejected`` and ``cancelled`` are terminal (a cancelled booking is never restored,
    brief 011 D9). Confirming and rejecting are methods here; approving and cancelling span
    several models and the meeting provider, so they live in ``services``. The rules they ask
    (can this booking be cancelled now, which classes, what status follows, what the start
    page shows) are methods here, so every caller gets the same answer.
    """

    MAX_OCCURRENCES = 60  # Zoom's cap for a recurring meeting; keeps one request reviewable
    MAX_DAYS_AHEAD = 365

    class Status(models.TextChoices):
        UNVERIFIED = "unverified", "Waiting for email check"
        WAITING = "waiting", "Waiting for IT"
        APPROVED = "approved", "Link sent"
        REJECTED = "rejected", "Not approved"
        CANCELLED = "cancelled", "Cancelled"

    class Repeat(models.TextChoices):
        ONCE = "once", "Just once"
        WEEKLY = "weekly", "Every week"

    class_name = models.CharField(
        "class name",
        max_length=200,  # Zoom's topic limit
        help_text="The name students and IT will see, like CCC Batch 3 - Mathematics.",
    )
    notes = models.TextField(
        "notes for IT", max_length=1000, blank=True, help_text="Anything IT should know."
    )
    wants_recording = models.BooleanField(
        "recording asked for",
        default=False,
        help_text="The requester asked for the class to be recorded to the Zoom cloud.",
    )
    first_date = models.DateField(
        "date of the class", help_text="For a weekly class, the date of the first class."
    )
    start_time = models.TimeField("starts at", help_text="Sri Lanka time, on a 5-minute step.")
    end_time = models.TimeField("ends at", help_text="On the same day as it starts.")
    repeat = models.CharField("how often", max_length=10, choices=Repeat, default=Repeat.ONCE)
    weekdays = models.CharField(
        "days of the week",
        max_length=13,
        blank=True,
        help_text="For weekly classes: ISO day numbers, 1 is Monday, like 1,3.",
    )
    last_date = models.DateField(
        "date of the last class",
        null=True,
        blank=True,
        help_text="For weekly classes: every ticked day is booked up to and including it.",
    )
    requester_name = models.CharField("requester's name", max_length=150)
    requester_email = models.EmailField(
        "requester's email", help_text="Confirmed by the requester before IT sees the request."
    )
    requester_phone = models.CharField(
        "requester's phone", max_length=16, help_text="Stored in international form."
    )
    submitted_ip = models.GenericIPAddressField(
        "sent from IP address",
        null=True,
        blank=True,
        help_text="Used only to limit how many requests one address can send in an hour.",
    )
    status = models.CharField(
        "status", max_length=12, choices=Status, default=Status.UNVERIFIED, db_index=True
    )
    created_at = models.DateTimeField("sent", auto_now_add=True, db_index=True)
    verified_at = models.DateTimeField("email confirmed", null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="decided by",
    )
    decided_at = models.DateTimeField("decided", null=True, blank=True)
    rejection_reason = models.TextField(
        "reason for not approving", blank=True, help_text="Emailed to the requester."
    )
    host_account = models.ForeignKey(
        HostAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="link_requests",
        verbose_name="booked on",
    )
    meeting_id = models.CharField("meeting ID", max_length=32, blank=True)
    join_url = models.URLField("Zoom link", max_length=1000, blank=True)
    # The meeting passcode is given to the requester; it isn't an account credential.
    passcode = models.CharField("passcode", max_length=10, blank=True)
    # Brief 011: who cancelled the whole booking, and when. Set only by ``services.cancel()``,
    # when no class of the booking is left to come.
    cancelled_at = models.DateTimeField(
        "cancelled", null=True, blank=True, help_text="When the IT desk cancelled the booking."
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="cancelled by",
        help_text="Who in the IT desk cancelled the booking.",
    )

    objects = LinkRequestQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Zoom link request"
        verbose_name_plural = "Zoom link requests"
        # Renamed in migration 0007 (brief 011, D8): migrate never renames a permission.
        permissions = [
            (
                "review_linkrequest",
                "Can approve, reject, reschedule or cancel Zoom link requests",
            )
        ]
        indexes = [
            models.Index(fields=["requester_email", "created_at"], name="zoom_lr_email_created"),
            models.Index(fields=["submitted_ip", "created_at"], name="zoom_lr_ip_created"),
        ]
        # MySQL 8.4 enforces CHECK constraints, so these hold for every write (criterion 45).
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="zoom_linkrequest_ends_after_start",
            ),
            models.CheckConstraint(
                condition=Q(repeat="once") | (Q(last_date__isnull=False) & ~Q(weekdays="")),
                name="zoom_linkrequest_weekly_has_days_and_end",
            ),
            models.CheckConstraint(
                condition=~Q(status="approved") | (Q(host_account__isnull=False) & ~Q(join_url="")),
                name="zoom_linkrequest_approved_has_link",
            ),
            models.CheckConstraint(
                condition=~Q(status="rejected") | ~Q(rejection_reason=""),
                name="zoom_linkrequest_rejected_has_reason",
            ),
            # Brief 011, criterion 1: only a booking that had a link can be cancelled, and it
            # always says when.
            models.CheckConstraint(
                condition=~Q(status="cancelled")
                | (Q(host_account__isnull=False) & ~Q(join_url="") & Q(cancelled_at__isnull=False)),
                name="zoom_linkrequest_cancelled_was_booked",
            ),
        ]

    def __str__(self):
        return f"{self.reference} {self.class_name}".strip()

    # ----------------------------------------------------------------------- derived values

    @property
    def reference(self) -> str:
        """``ZL-0042``. The only place the format is defined (D12); nothing is stored."""
        return f"ZL-{self.pk:04d}" if self.pk else ""

    @property
    def zoom_marker(self) -> str:
        """``Polymath TMD ZL-0042``: the agenda text of every Zoom meeting made for this request.

        Zoom has no idempotency key, so this is how a later attempt recognises (and removes) a
        meeting left in Zoom by an attempt that failed (brief 006, D6). The one place it's
        defined; match it with ``agenda_has_marker()``, never a bare substring test.
        """
        return f"Polymath TMD {self.reference}"

    def agenda_has_marker(self, agenda) -> bool:
        """True when ``agenda`` carries this request's marker, and not a longer reference.

        ``ZL-1234`` is a prefix of ``ZL-12345``, so the marker must not be followed by a digit.
        """
        if not self.pk or not agenda:
            return False
        return re.search(re.escape(self.zoom_marker) + r"(?!\d)", agenda) is not None

    @property
    def weekday_numbers(self) -> list[int]:
        return [int(day) for day in (self.weekdays or "").split(",") if day.strip().isdigit()]

    @property
    def weekday_names(self) -> list[str]:
        return [WEEKDAY_NAMES[day] for day in self.weekday_numbers if day in WEEKDAY_NAMES]

    @property
    def requester_phone_display(self) -> str:
        """``+94 77 123 4567`` for reading; ``tel:`` links keep the E.164 value (D22)."""
        return format_phone(self.requester_phone)

    def class_count(self) -> int:
        """How many classes the schedule makes, computed without listing them.

        Counted arithmetically so a mistyped last date years ahead is refused quickly with
        the right number, instead of building thousands of dates first.
        """
        if self.repeat != self.Repeat.WEEKLY:
            return 1 if self.first_date else 0
        if not (self.first_date and self.last_date) or self.last_date < self.first_date:
            return 0
        total = 0
        for day in set(self.weekday_numbers):
            offset = (day - self.first_date.isoweekday()) % 7
            first = self.first_date + timedelta(days=offset)
            if first <= self.last_date:
                total += (self.last_date - first).days // 7 + 1
        return total

    def occurrence_dates(self):
        """The class dates, sorted. Weekly: every ticked day from first to last date."""
        if self.repeat != self.Repeat.WEEKLY:
            return [self.first_date] if self.first_date else []
        if not (self.first_date and self.last_date):
            return []
        dates = []
        for day in set(self.weekday_numbers):
            current = self.first_date + timedelta(days=(day - self.first_date.isoweekday()) % 7)
            while current <= self.last_date:
                dates.append(current)
                current += timedelta(days=7)
        return sorted(dates)

    def occurrence_times(self) -> list[tuple[datetime, datetime]]:
        """Aware ``(start, end)`` for every class, in ``TIME_ZONE`` (Asia/Colombo).

        Pure: it reads only this request's fields, so ``clean()`` can use it before anything
        is saved, and ``create_occurrences()`` stores exactly what was validated.

        Caveat: ``datetime.combine`` doesn't check that a wall-clock time exists. In a zone with
        daylight saving, a time inside the spring-forward gap would be stored shifted by the
        gap. Asia/Colombo has no DST, so this can't happen here; if ``TIME_ZONE`` ever changes
        to such a zone, ``clean()`` must reject nonexistent times first.
        """
        if self.start_time is None or self.end_time is None:
            return []
        zone = timezone.get_default_timezone()
        return [
            (
                datetime.combine(day, self.start_time, tzinfo=zone),
                datetime.combine(day, self.end_time, tzinfo=zone),
            )
            for day in self.occurrence_dates()
        ]

    @property
    def schedule_summary(self) -> str:
        """The schedule in one plain-text sentence, the one source for pages and emails (D22).

        ``Every Monday and Wednesday, 8:30 am to 11:30 am, from Mon 5 Oct to Wed 28 Oct 2026
        (8 classes)`` or ``Once, on Mon 5 Oct 2026, 8:30 am to 11:30 am``. The first date
        drops its year when it's the same as the last date's.
        """
        dates = self.occurrence_dates()
        if not dates or self.start_time is None or self.end_time is None:
            return ""
        times = f"{class_time(self.start_time)} to {class_time(self.end_time)}"
        if self.repeat != self.Repeat.WEEKLY:
            return f"Once, on {class_date(dates[0])}, {times}"
        first, last = dates[0], dates[-1]
        count = len(dates)
        return (
            f"Every {_join_words(self.weekday_names)}, {times}, "
            f"from {class_date(first, year=first.year != last.year)} to {class_date(last)} "
            f"({count} class{'' if count == 1 else 'es'})"
        )

    def has_started(self, now=None) -> bool:
        """True once the first class has begun; such a request can no longer be approved."""
        times = self.occurrence_times()
        return bool(times) and times[0][0] <= (now or timezone.now())

    def can_be_decided(self) -> bool:
        return self.status == self.Status.WAITING

    # ----------------------------------------------------------------------- cancelling (011)
    #
    # Each rule takes ``now`` (default: the current time) and, optionally, the request's classes
    # already in memory. ``services.cancel()`` passes the rows it has just locked, so its checks
    # read exactly what it's about to change; pages pass the list they already show, so no rule
    # costs a query of its own.

    def _classes(self, occurrences):
        found = self.occurrences.all() if occurrences is None else occurrences
        return sorted(found, key=lambda occurrence: (occurrence.starts_at, occurrence.pk or 0))

    def class_in_progress(self, now=None, *, occurrences=None):
        """The booked class running at ``now`` (``starts_at <= now < ends_at``), or ``None``."""
        now = now or timezone.now()
        for occurrence in self._classes(occurrences):
            if occurrence.is_booked() and occurrence.starts_at <= now < occurrence.ends_at:
                return occurrence
        return None

    def cancellable_classes(self, now=None, *, occurrences=None) -> list["Occurrence"]:
        """Booked classes that haven't started, soonest first (criterion 3)."""
        now = now or timezone.now()
        return [o for o in self._classes(occurrences) if o.can_be_cancelled(now)]

    def kept_classes(self, now=None, *, occurrences=None) -> list["Occurrence"]:
        """Booked classes that have started (in progress or over), soonest first.

        The other half of ``cancellable_classes``: cancelling the whole booking leaves these as
        they were (criterion 4), and the confirm page lists them under "Classes that stay". Kept
        here, next to its complement, so the two can't drift apart (review round 1, SF2).
        """
        now = now or timezone.now()
        return [o for o in self._classes(occurrences) if o.is_booked() and o.starts_at <= now]

    def can_cancel_booking(self, now=None, *, occurrences=None) -> bool:
        """Approved, at least one class left to cancel, and no class running right now.

        A class in progress blocks the whole cancel (criterion 6): Zoom refuses to delete a
        meeting that's running, and the teacher would be cut off mid-class.
        """
        if self.status != self.Status.APPROVED:
            return False
        classes = self._classes(occurrences)
        return bool(self.cancellable_classes(now, occurrences=classes)) and (
            self.class_in_progress(now, occurrences=classes) is None
        )

    def cancel_booking_blocked_message(self, now=None, *, occurrences=None):
        """Criterion 6's whole-booking message when the booking can't be cancelled now, else None.

        Used both to refuse a cancel and, on the detail page, to say why there's no cancel
        link (G2), so the sentence is built in one place.
        """
        classes = self._classes(occurrences)
        if self.can_cancel_booking(now, occurrences=classes):
            return None
        running = self.class_in_progress(now, occurrences=classes)
        if running is not None:
            return CANCEL_IN_PROGRESS.format(
                occurrence=running, end=class_time(timezone.localtime(running.ends_at))
            )
        return NOTHING_LEFT_TO_CANCEL

    def status_after_cancel(self, now=None, *, occurrences=None) -> str:
        """``cancelled`` once no class is both not cancelled and not ended; else ``approved``.

        A class that has ended stays as it was (criterion 4), so a booking whose remaining
        classes are all cancelled is over, even though its held classes keep their history.
        """
        now = now or timezone.now()
        still_on = any(
            occurrence.cancelled_at is None and occurrence.ends_at > now
            for occurrence in self._classes(occurrences)
        )
        return self.Status.APPROVED if still_on else self.Status.CANCELLED

    def start_state(self, now=None, *, occurrences=None):
        """``(state, occurrence)`` for the public start page (criterion 21).

        - ``ready``: ``now`` is inside the start window of one of its booked classes (that one);
        - ``too_early``: a booked class is still to come, but no window is open (the next one);
        - ``ended``: no booked class is still to come (the last held class, or ``None``);
        - ``cancelled``: the whole booking was cancelled (``None``).

        Only a class whose 30 minutes before its start have come can be inside its window, so
        at most a couple of windows are worked out, each one query.
        """
        if self.status == self.Status.CANCELLED:
            return "cancelled", None
        now = now or timezone.now()
        booked = [o for o in self._classes(occurrences) if o.is_booked()]
        to_come = [o for o in booked if o.ends_at > now]
        lead = timedelta(minutes=Occurrence.START_WINDOW_MINUTES)
        for occurrence in to_come:
            if occurrence.starts_at - lead > now:
                break
            opens_at, closes_at = occurrence.start_window()
            if opens_at <= now < closes_at:
                return "ready", occurrence
        if to_come:
            return "too_early", to_come[0]
        return "ended", (booked[-1] if booked else None)

    # ----------------------------------------------------------------------- validation

    def clean(self):
        """Every schedule rule of criterion 6, so the form and the shell agree.

        It also normalises: the email is trimmed and lower-cased, weekdays are sorted and
        de-duplicated, and a one-off request drops any weekly fields that were sent.
        """
        errors = {}
        if self.requester_email:
            self.requester_email = self.requester_email.strip().lower()

        weekly = self.repeat == self.Repeat.WEEKLY
        if weekly:
            days = sorted({day for day in self.weekday_numbers if day in WEEKDAY_NAMES})
            self.weekdays = ",".join(str(day) for day in days)
        else:
            self.weekdays = ""
            self.last_date = None

        for name in ("start_time", "end_time"):
            value = getattr(self, name)
            if value is not None and (
                value.minute % SLOT_MINUTES or value.second or value.microsecond
            ):
                errors[name] = TIME_STEP
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
            and "end_time" not in errors
        ):
            errors["end_time"] = END_BEFORE_START

        now = timezone.localtime()
        today = now.date()
        if self.first_date:
            if self.first_date < today or (
                self.first_date == today
                and self.start_time is not None
                and self.start_time <= now.time()
            ):
                errors["first_date"] = DATE_PASSED
            elif self.first_date > today + timedelta(days=self.MAX_DAYS_AHEAD):
                errors["first_date"] = DATE_TOO_FAR

        if weekly:
            if not self.weekdays:
                errors["weekdays"] = NO_WEEKDAYS
            if not self.last_date or (self.first_date and self.last_date < self.first_date):
                errors["last_date"] = LAST_DATE_NEEDED
            if self.first_date and "weekdays" not in errors and "last_date" not in errors:
                count = self.class_count()
                if count == 0:
                    errors["weekdays"] = NO_DAY_IN_RANGE
                elif count > self.MAX_OCCURRENCES:
                    errors["last_date"] = TOO_MANY_CLASSES.format(n=count, max=self.MAX_OCCURRENCES)

        if errors:
            raise ValidationError(errors)

    # ----------------------------------------------------------------------- state changes

    def create_occurrences(self):
        """Store one ``Occurrence`` per class. Called once, right after the request is saved."""
        return Occurrence.objects.bulk_create(
            Occurrence(link_request=self, starts_at=start, ends_at=end)
            for start, end in self.occurrence_times()
        )

    def mark_verified(self):
        """``unverified`` → ``waiting``, once the requester confirms their email.

        A conditional UPDATE, not read-then-save, so two confirm clicks at the same moment
        can't both succeed and send IT two emails.
        """
        now = timezone.now()
        updated = (
            type(self)
            .objects.filter(pk=self.pk, status=self.Status.UNVERIFIED)
            .update(status=self.Status.WAITING, verified_at=now)
        )
        if not updated:
            raise InvalidTransition("Only an unconfirmed request can be confirmed.")
        self.status = self.Status.WAITING
        self.verified_at = now

    def reject(self, by, reason):
        """``waiting`` → ``rejected`` with a reason the requester will read.

        Conditional UPDATE for the same reason as ``mark_verified``: a request approved or
        rejected by someone else a moment ago is never overwritten.
        """
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError({"rejection_reason": REASON_REQUIRED})
        now = timezone.now()
        updated = (
            type(self)
            .objects.filter(pk=self.pk, status=self.Status.WAITING)
            .update(
                status=self.Status.REJECTED, rejection_reason=reason, decided_by=by, decided_at=now
            )
        )
        if not updated:
            raise InvalidTransition("Only a waiting request can be decided.")
        self.status = self.Status.REJECTED
        self.rejection_reason = reason
        self.decided_by = by
        self.decided_at = now


# --------------------------------------------------------------------------- Classes and slots


# What makes a class booked, defined once: ``booked()`` filters on it, and the timetable ORs
# it with "waiting" (brief 009, criterion 17), so the two can't drift apart. A cancelled class
# (brief 011, criterion 2) holds nothing, so everything built on ``booked()`` frees its time.
# ``Occurrence.is_booked()`` is the same rule for a class already in memory.
BOOKED = Q(
    link_request__status=LinkRequest.Status.APPROVED,
    host_account__isnull=False,
    cancelled_at__isnull=True,
)


class OccurrenceQuerySet(models.QuerySet):
    def booked(self):
        """Classes that hold an account: those of approved requests (D6)."""
        return self.filter(BOOKED)

    def overlapping(self, start, end):
        """Classes overlapping ``[start, end)``. Touching end-to-start is not an overlap."""
        return self.filter(starts_at__lt=end, ends_at__gt=start)

    def upcoming(self, now=None):
        """Classes that haven't ended by ``now``; one in progress still counts (brief 008)."""
        return self.filter(ends_at__gt=now or timezone.now())

    def in_period(self, start, end):
        """Classes *starting* in ``[start, end)``.

        By start, not by overlap, because the timetable puts a class in the box of its local
        start date (brief 009, D3); classes are same-day, so none is split across two boxes.
        """
        return self.filter(starts_at__gte=start, starts_at__lt=end)

    def for_timetable(self, start, end, account=None):
        """The timetable's entries starting in ``[start, end)``, in display order.

        Booked classes plus classes waiting for IT. With ``account``, only that account's
        booked classes: a waiting class holds no account yet, so it can't match an account
        filter (brief 009, D1). Unverified and rejected requests never appear (criterion 8).

        One query: the request and the account are joined in, because each entry shows the
        reference, the class name and the account label (criterion 18).
        """
        if account is None:
            qs = self.filter(BOOKED | Q(link_request__status=LinkRequest.Status.WAITING))
        else:
            qs = self.booked().filter(host_account=account)
        return (
            qs.in_period(start, end)
            .select_related("link_request", "host_account")
            .order_by("starts_at", "pk")
        )


class Occurrence(models.Model):
    """One class meeting of a request. Its ``host_account`` is set when the request is approved.

    A class is *booked* while its request is approved, it has an account and it isn't
    cancelled; *started* once ``starts_at <= now``; *in progress* while ``starts_at <= now <
    ends_at`` (brief 011). Cancelling sets ``cancelled_at``, ``cancelled_by`` and
    ``cancel_reason`` and deletes its slots; the account stays recorded, as history.
    """

    # Brief 011, D4: the start link opens this many minutes before the class.
    # The pinned copy types "30 minutes" out in three templates, which don't read this
    # constant: zoom/start.html, zoom/detail.html and zoom/email/approved_body.txt. Change
    # the number there too if it ever changes here (review round 1 nit).
    START_WINDOW_MINUTES = 30

    link_request = models.ForeignKey(
        LinkRequest,
        on_delete=models.CASCADE,
        related_name="occurrences",
        verbose_name="request",
    )
    starts_at = models.DateTimeField("starts")
    ends_at = models.DateTimeField("ends")
    host_account = models.ForeignKey(
        HostAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="occurrences",
        verbose_name="booked on",
    )
    # Set only by approve() for a weekly (recurring) meeting; read by brief 011 to cancel a
    # single class. Blank for one-off classes and for the manual and fake providers.
    zoom_occurrence_id = models.CharField(
        "Zoom occurrence ID",
        max_length=20,
        blank=True,
        help_text="Zoom's ID for this class within its weekly meeting, when Zoom made it.",
    )
    # Brief 011: set together by ``services.cancel()``. A class that has started is never
    # cancelled, so these always describe a class that didn't happen.
    cancelled_at = models.DateTimeField(
        "cancelled", null=True, blank=True, help_text="When the IT desk cancelled this class."
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="cancelled by",
        help_text="Who in the IT desk cancelled this class.",
    )
    cancel_reason = models.TextField(
        "reason for cancelling",
        blank=True,
        help_text="Why the class was cancelled. It's emailed to the requester.",
    )

    objects = OccurrenceQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at", "pk"]
        verbose_name = "class"
        verbose_name_plural = "classes"
        indexes = [
            models.Index(fields=["host_account", "starts_at"], name="zoom_occ_host_start"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="zoom_occurrence_ends_after_start"
            ),
            # Brief 011, criterion 1: a cancelled class always says why.
            models.CheckConstraint(
                condition=Q(cancelled_at__isnull=True) | ~Q(cancel_reason=""),
                name="zoom_occurrence_cancel_has_reason",
            ),
        ]

    def __str__(self):
        start = timezone.localtime(self.starts_at)
        end = timezone.localtime(self.ends_at)
        return f"{class_date(start)}, {class_time(start)} to {class_time(end)}"

    def overlaps(self, other) -> bool:
        """``a.start < b.end and b.start < a.end`` (D6): back-to-back classes don't clash."""
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at

    # ----------------------------------------------------------------------- brief 011

    def is_booked(self) -> bool:
        """``BOOKED`` for a class in memory.

        It reads ``link_request``, which a request's own ``occurrences`` already carry, so
        asking costs no query there.
        """
        return (
            self.cancelled_at is None
            and self.host_account_id is not None
            and self.link_request.status == LinkRequest.Status.APPROVED
        )

    def can_be_cancelled(self, now=None) -> bool:
        """Booked and not started (criterion 3): a class that has begun keeps its history."""
        return self.is_booked() and self.starts_at > (now or timezone.now())

    def cancel_blocked_message(self, now=None):
        """Criterion 6's one-class message when this class can't be cancelled, else ``None``."""
        if self.cancelled_at is not None:
            return CLASS_ALREADY_CANCELLED
        if self.can_be_cancelled(now):
            return None
        return CLASS_STARTED

    def start_window(self):
        """``(opens_at, closes_at)``: when the booking's start link works for this class (D4).

        It opens ``START_WINDOW_MINUTES`` before the class, or when the account's previous
        booked class ends if that's later, and closes when this class ends. The plan allows one
        meeting at a time per Zoom user, so starting early while the previous class still runs
        on the same account could end that class (R3). One query: the latest end of another
        booked class on this account inside ``(starts_at - 30 min, starts_at]``. Remembered on
        the instance, because the start page asks more than once.
        """
        if getattr(self, "_start_window", None) is None:
            earliest = self.starts_at - timedelta(minutes=self.START_WINDOW_MINUTES)
            previous_end = None
            if self.host_account_id is not None:
                previous_end = (
                    Occurrence.objects.booked()
                    .filter(
                        host_account_id=self.host_account_id,
                        ends_at__gt=earliest,
                        ends_at__lte=self.starts_at,
                    )
                    .exclude(pk=self.pk)
                    .aggregate(latest=Max("ends_at"))["latest"]
                )
            opens_at = max(earliest, previous_end) if previous_end else earliest
            self._start_window = (opens_at, self.ends_at)
        return self._start_window

    def opens_after_other_class(self) -> bool:
        """True when the window opens later than 30 minutes before, because of another class."""
        earliest = self.starts_at - timedelta(minutes=self.START_WINDOW_MINUTES)
        return self.start_window()[0] > earliest


class HostSlot(models.Model):
    """One booked 5-minute slot of one account: the database backstop against double booking.

    Written only by ``services.approve()``, and deleted by ``services.cancel()`` for each class
    it cancels (brief 011), which frees the account at those times. Deleting a request cascades
    to its occurrences and from them to these rows too.
    """

    host_account = models.ForeignKey(
        HostAccount, on_delete=models.PROTECT, related_name="slots", verbose_name="account"
    )
    starts_at = models.DateTimeField("slot starts")
    occurrence = models.ForeignKey(
        Occurrence, on_delete=models.CASCADE, related_name="slots", verbose_name="class"
    )

    class Meta:
        ordering = ["host_account", "starts_at"]
        verbose_name = "booked slot"
        verbose_name_plural = "booked slots"
        constraints = [
            models.UniqueConstraint(
                fields=["host_account", "starts_at"], name="zoom_one_booking_per_account_slot"
            ),
        ]

    def __str__(self):
        return f"{self.host_account.label} {timezone.localtime(self.starts_at):%Y-%m-%d %H:%M}"

    @classmethod
    def covering(cls, occurrence, account) -> list["HostSlot"]:
        """Unsaved slots covering every 5 minutes of ``occurrence`` on ``account``.

        Refuses unaligned times, because a class starting at 8:32 would only half-overlap the
        slot grid and the unique constraint could miss a clash.
        """
        start, end = occurrence.starts_at, occurrence.ends_at
        if start.minute % SLOT_MINUTES or start.second or start.microsecond:
            raise ValueError("Class times must sit on 5-minute steps.")
        step = timedelta(minutes=SLOT_MINUTES)
        slots = []
        while start < end:
            slots.append(cls(host_account=account, starts_at=start, occurrence=occurrence))
            start += step
        return slots


class HostKeyReveal(models.Model):
    """One time an IT desk member was shown an account's host key (brief 011, D11).

    The owner asked for every reveal to be recorded with who and when, and the IT desk can't
    read the server logs, so this table is the in-app record; the log line is the second copy.
    It stores no key, and no part or hash of one. Written only by ``services.reveal_host_key()``.
    """

    host_account = models.ForeignKey(
        HostAccount,
        on_delete=models.PROTECT,
        related_name="key_reveals",
        verbose_name="account",
        help_text="The Zoom account whose host key was shown.",
    )
    shown_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="shown to",
        help_text="The IT desk member who pressed Show host key.",
    )
    shown_at = models.DateTimeField("shown", auto_now_add=True)

    class Meta:
        ordering = ["-shown_at", "-pk"]
        verbose_name = "host key reveal"
        verbose_name_plural = "host key reveals"

    def __str__(self):
        return f"{self.host_account.label} shown to {self.shown_by}"
