"""The Zoom timetable's calendar arithmetic: months, weeks, day boxes (brief 009).

Why this is a module of pure functions, apart from the models and the views:

- **No database access here.** Everything takes plain values (dates, already-fetched
  ``Occurrence`` objects, already-fetched ``HostAccount`` objects) and returns plain values.
  That keeps the grid logic unit-testable without MySQL, and it keeps the views thin: they
  parse the request, run the two queries (``HostAccount.objects.with_timetable_flag`` and
  ``Occurrence.objects.for_timetable``), call these functions and render (criterion 17).
- **Weeks run Monday to Sunday** (D8): Sri Lanka's calendars and ISO 8601 both start on Monday,
  as does brief 005's weekday numbering (1 = Monday).
- **A class's day is the local date of its start in ``TIME_ZONE``** (D3). Month and day bounds
  are local midnights; Django converts them to UTC for the query, so a class at 00:30 on
  1 Oct Colombo time (19:00Z on 30 Sep) is an October class.
- **Bad query values fall back quietly** (D4): a ``?month=`` that isn't a real month shows the
  current month, and an ``?account=`` that isn't a known account shows all accounts. Only the
  day view's path, which the app builds itself, gives 404 for an impossible date.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import TypedDict

from django.utils import dateformat, timezone

from .models import LinkRequest, class_date

# How many entries a month day box shows before "+N more". Defined once (criterion 9); the
# designer confirmed 3 (Design D.0): four would push a busy week past a laptop screen.
DAY_BOX_LIMIT = 3

# The months the timetable will show. Outside this range ``?month=`` falls back to the current
# month and a day-view path gives 404 (criteria 4 and 14).
FIRST_YEAR = 2000
LAST_YEAR = 2100

# ASCII digits only: ``\d`` would also match other scripts' digits (``２０２６-０９``), which
# ``int()`` happily converts, so a lookalike value would quietly pass as a real month.
_MONTH_VALUE = re.compile(r"([0-9]{4})-([0-9]{2})")

# Monday first (D8). ``calendar.Calendar`` defaults to Monday too; it's spelled out so the
# rule doesn't depend on a library default.
_WEEKS = calendar.Calendar(firstweekday=calendar.MONDAY)


def local_midnight(day: date) -> datetime:
    """The aware start of ``day`` in ``TIME_ZONE``, the bound every timetable query uses (D3)."""
    return datetime.combine(day, time(), tzinfo=timezone.get_default_timezone())


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """``[local midnight of day, local midnight of the next day)``, for the day view's query."""
    return local_midnight(day), local_midnight(day + timedelta(days=1))


@dataclass(frozen=True)
class Month:
    """One calendar month. Frozen, so it compares by value (``==``) and is safe to hand to
    templates. Not ordered: nothing sorts months, so ``<`` isn't offered.

    ``start`` and ``end`` are the half-open local bounds of the month; ``value`` is what goes
    in ``?month=`` and ``label`` is what people read.
    """

    year: int
    month: int

    @classmethod
    def for_date(cls, day: date) -> "Month":
        return cls(day.year, day.month)

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def start(self) -> datetime:
        """Local midnight on the 1st."""
        return local_midnight(self.first_day)

    @property
    def end(self) -> datetime:
        """Local midnight on the 1st of the next month: not part of this month."""
        return self.next.start

    @property
    def value(self) -> str:
        """``2026-09``, the ``?month=`` value."""
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def label(self) -> str:
        """``September 2026``."""
        return dateformat.format(self.first_day, "F Y")

    @property
    def previous(self) -> "Month":
        if self.month == 1:
            return Month(self.year - 1, 12)
        return Month(self.year, self.month - 1)

    @property
    def next(self) -> "Month":
        if self.month == 12:
            return Month(self.year + 1, 1)
        return Month(self.year, self.month + 1)

    def contains(self, day: date) -> bool:
        return (day.year, day.month) == (self.year, self.month)

    def weeks(self) -> list[list[date | None]]:
        """One 7-item list per week, Monday first; days outside the month are ``None`` (D2)."""
        return [
            [day if self.contains(day) else None for day in week]
            for week in _WEEKS.monthdatescalendar(self.year, self.month)
        ]


def parse_month(value, today: date) -> Month:
    """The month named by ``?month=YYYY-MM``, or ``today``'s month when it doesn't name one.

    Two-digit months only (``2026-1`` isn't accepted), years 2000 to 2100 (criterion 4). No
    error is raised or shown for a bad value: it comes from a link or the filter form (D4).
    """
    match = _MONTH_VALUE.fullmatch(value) if isinstance(value, str) else None
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if FIRST_YEAR <= year <= LAST_YEAR and 1 <= month <= 12:
            return Month(year, month)
    return Month.for_date(today)


def parse_day(year: int, month: int, day: int) -> date | None:
    """The day view's date from its path, or ``None`` for an impossible or out-of-range date.

    The caller turns ``None`` into 404: the path is one the app builds, so a bad one is a
    broken address rather than a choice to fall back from (D4, criterion 14).
    """
    if not FIRST_YEAR <= year <= LAST_YEAR:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_account_id(value) -> int | None:
    """The ``?account=`` pk as an int, or ``None`` when it isn't a positive whole number."""
    if isinstance(value, str) and value.isdigit() and value.isascii():
        number = int(value)
        return number or None
    return None


def account_filter(accounts, account_id):
    """``(filter_accounts, selected_account)`` for the account select (criteria 11 and 14).

    ``accounts`` is every account, each carrying the ``on_timetable`` flag from
    ``HostAccountQuerySet.with_timetable_flag`` and already in display order. The options are
    the flagged ones. The chosen account is looked up among *all* of them, so filtering to an
    account that's out of use and idle this month still works; it's then appended to the
    options, so the select shows it as chosen (OQ2, D9) and the template needs no membership
    test. An unknown or deleted pk falls back to all accounts (``None``).
    """
    accounts = list(accounts)
    options = [account for account in accounts if account.on_timetable]
    selected = next((account for account in accounts if account.pk == account_id), None)
    if selected is not None and not selected.on_timetable:
        options.append(selected)
    return options, selected


def _order(occurrences):
    """By start, then pk (criterion 8). Unsaved objects (pure tests) sort by start alone."""
    return sorted(occurrences, key=lambda o: (o.starts_at, o.pk or 0))


def local_day(occurrence) -> date:
    """The class's day: the local date of its start (D3)."""
    return timezone.localdate(occurrence.starts_at)


def day_entries(occurrences, day: date) -> list:
    """Every entry on ``day``, sorted. The day view's list, and what a month box counts."""
    return _order(o for o in occurrences if local_day(o) == day)


def entry_counts(occurrences) -> tuple[int, int]:
    """``(booked, waiting)`` for the summary line (criterion 12), counted from fetched entries.

    ``for_timetable`` returns only booked and waiting classes, so every entry that isn't
    waiting is booked; "booked" isn't restated here.
    """
    waiting = sum(1 for o in occurrences if o.link_request.status == LinkRequest.Status.WAITING)
    return len(occurrences) - waiting, waiting


class DayBox(TypedDict):
    """One in-month cell of the month grid (the context contract's ``DayBox``)."""

    date: date
    label: str  # "Tue 1 Sep": class_date without the year
    is_today: bool
    entries: list  # at most ``limit`` Occurrences, sorted
    more: int  # how many more classes the day view has; 0 when none


def build_month(month: Month, occurrences, today: date, limit: int = DAY_BOX_LIMIT):
    """The ``weeks`` grid: 7-item lists of ``DayBox`` or ``None`` (a day outside the month).

    ``occurrences`` is what ``for_timetable`` returned for the month; each is put in the box
    of its local start date, so a box's ``entries`` plus ``more`` are exactly what the day
    view lists for that date (criterion 15). Classes outside the month are ignored.
    """
    by_day: dict[date, list] = {}
    for occurrence in _order(occurrences):
        by_day.setdefault(local_day(occurrence), []).append(occurrence)
    return [
        [
            None
            if day is None
            else DayBox(
                date=day,
                label=class_date(day, year=False),
                is_today=day == today,
                entries=by_day.get(day, [])[:limit],
                more=max(len(by_day.get(day, [])) - limit, 0),
            )
            for day in week
        ]
        for week in month.weeks()
    ]
