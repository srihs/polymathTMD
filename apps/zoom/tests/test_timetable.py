"""The Zoom timetable (brief 009): ``timetable.py``, its QuerySet methods and both views.

- The pure functions of ``timetable.py`` are tested without the database, on unsaved objects
  (criterion 17).
- The views are tested against the context contract with the stub templates from
  ``conftest.py``; those stubs follow every relation an entry may use, so the query-count
  tests also prove the ``select_related`` (criterion 18).
- Criteria 2 (sidebar), 16 (no private data) and 18 on the real markup render the real
  templates. They never skip: a renamed template must fail them, not silence them.

Time is frozen at Mon 28 Sep 2026, 10:00 Colombo (``conftest.py``).
"""

from datetime import UTC, date, datetime, time
from html.parser import HTMLParser

import pytest
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.zoom import timetable
from apps.zoom.models import HostAccount, LinkRequest, Occurrence
from apps.zoom.timetable import DAY_BOX_LIMIT, Month

from .conftest import COLOMBO, make_account, make_request
from .test_sidebar_zoom_group import _item, _real_templates, _sidenav

TODAY = date(2026, 9, 28)
APPROVED = LinkRequest.Status.APPROVED
WAITING = LinkRequest.Status.WAITING
MONTH_URL = reverse("zoom:timetable")


def day_url(day, **query):
    url = reverse("zoom:timetable_day", args=[day.year, day.month, day.day])
    if query:
        url += "?" + "&".join(f"{key}={value}" for key, value in query.items())
    return url


def add_class(
    account=None,
    day=date(2026, 10, 7),
    start=time(8, 30),
    end=time(11, 30),
    *,
    status=None,
    name="CCC Batch 3 - Mathematics",
    **fields,
):
    """One class: booked on ``account`` (approved), or with the given status and no account.

    Stored directly rather than through ``services.approve()``: these tests are about what the
    timetable shows, not about booking, and some put classes in the past or side by side.
    """
    status = status or (APPROVED if account else WAITING)
    if status == APPROVED:
        fields.update(
            host_account=account,
            join_url="https://zoom.example/j/123456789",
            meeting_id="123456789",
            passcode="483920",
        )
    link_request = make_request(
        status=status, first_date=day, start=start, end=end, class_name=name, **fields
    )
    if status == APPROVED:
        link_request.occurrences.update(host_account=account)
    return link_request.occurrences.get()


def unsaved(start_utc, *, status=APPROVED, account=None, pk=None):
    """An unsaved ``Occurrence`` for the pure-function tests: no database needed."""
    link_request = LinkRequest(status=status, class_name="Class")
    occurrence = Occurrence(
        link_request=link_request,
        starts_at=start_utc,
        ends_at=start_utc.replace(hour=(start_utc.hour + 1) % 24),
        host_account=account,
    )
    occurrence.pk = pk
    return occurrence


def local(day, hour=8, minute=30):
    return datetime.combine(day, time(hour, minute), tzinfo=COLOMBO)


def box_for(weeks, day):
    return next(box for week in weeks for box in week if box and box["date"] == day)


# =========================================================================== pure functions


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, Month(2026, 9)),
        ("2026-10", Month(2026, 10)),
        ("2026-13", Month(2026, 9)),
        ("2026-1", Month(2026, 9)),
        ("abc", Month(2026, 9)),
        ("", Month(2026, 9)),
        ("1999-12", Month(2026, 9)),
        ("2101-01", Month(2026, 9)),
        ("2026-00", Month(2026, 9)),
        (" 2026-10", Month(2026, 9)),
        ("２０２６-０９", Month(2026, 9)),  # full-width digits: not ASCII, so not a month
        ("٢٠٢٦-١٠", Month(2026, 9)),  # Arabic-Indic digits
        ("2000-01", Month(2000, 1)),
        ("2100-12", Month(2100, 12)),
    ],
)
def test_parse_month(value, expected):
    """Criterion 4: exactly these values; anything bad is the current month."""
    assert timetable.parse_month(value, TODAY) == expected


def test_month_values_labels_bounds_and_neighbours():
    month = Month(2026, 9)
    assert month.value == "2026-09"
    assert month.label == "September 2026"
    assert month.start == datetime(2026, 9, 1, tzinfo=COLOMBO)
    assert month.end == datetime(2026, 10, 1, tzinfo=COLOMBO)
    assert month.start.utcoffset() is not None
    assert (month.previous, month.next) == (Month(2026, 8), Month(2026, 10))
    assert Month(2026, 12).next == Month(2027, 1)
    assert Month(2027, 1).previous == Month(2026, 12)
    assert Month.for_date(date(2026, 10, 7)) == Month(2026, 10)
    assert month.contains(date(2026, 9, 30)) and not month.contains(date(2026, 10, 1))


def test_weeks_of_september_2026_start_on_tuesday():
    weeks = Month(2026, 9).weeks()
    assert len(weeks) == 5
    assert all(len(week) == 7 for week in weeks)
    assert weeks[0][:2] == [None, date(2026, 9, 1)]
    assert weeks[4] == [date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)] + [None] * 4


def test_weeks_of_february_2027_fill_four_rows_exactly():
    weeks = Month(2027, 2).weeks()
    assert len(weeks) == 4
    assert weeks[0][0] == date(2027, 2, 1)
    assert weeks[3][6] == date(2027, 2, 28)
    assert None not in [day for week in weeks for day in week]


def test_weeks_of_november_2026_take_six_rows():
    weeks = Month(2026, 11).weeks()
    assert len(weeks) == 6
    assert weeks[0] == [None] * 6 + [date(2026, 11, 1)]
    assert weeks[5] == [date(2026, 11, 30)] + [None] * 6


def test_every_day_of_the_month_appears_once_and_in_its_weekday_column():
    weeks = Month(2026, 9).weeks()
    days = [day for week in weeks for day in week if day]
    assert days == [date(2026, 9, n) for n in range(1, 31)]
    for week in weeks:
        for column, day in enumerate(week):
            if day:
                assert day.isoweekday() == column + 1  # Monday first (D8)


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        ((2026, 10, 7), date(2026, 10, 7)),
        ((2026, 2, 30), None),
        ((2026, 13, 1), None),
        ((1999, 12, 31), None),
        ((2101, 1, 1), None),
        ((2000, 1, 1), date(2000, 1, 1)),
        ((2100, 12, 31), date(2100, 12, 31)),
    ],
)
def test_parse_day(parts, expected):
    assert timetable.parse_day(*parts) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3", 3), ("", None), (None, None), ("abc", None), ("-3", None), ("0", None), ("٣", None)],
)
def test_parse_account_id(value, expected):
    assert timetable.parse_account_id(value) == expected


def test_build_month_caps_each_box_and_counts_the_rest():
    """Criterion 9: 5 classes on Wed 7 Oct show 3, with 2 more."""
    day = date(2026, 10, 7)
    occurrences = [unsaved(local(day, 8 + n).astimezone(UTC), pk=n + 1) for n in range(5)]
    box = box_for(timetable.build_month(Month(2026, 10), occurrences, TODAY), day)
    assert box["entries"] == occurrences[:DAY_BOX_LIMIT]
    assert box["more"] == 2
    assert box["label"] == "Wed 7 Oct"
    assert box["is_today"] is False


def test_build_month_boxes_with_room_have_no_more():
    day = date(2026, 10, 7)
    occurrences = [unsaved(local(day, 8 + n).astimezone(UTC), pk=n + 1) for n in range(3)]
    box = box_for(timetable.build_month(Month(2026, 10), occurrences, TODAY), day)
    assert len(box["entries"]) == 3 and box["more"] == 0


def test_build_month_orders_by_start_then_pk():
    day = date(2026, 10, 7)
    late = unsaved(local(day, 10).astimezone(UTC), pk=1)
    early_b = unsaved(local(day, 8).astimezone(UTC), pk=3)
    early_a = unsaved(local(day, 8).astimezone(UTC), pk=2)
    box = box_for(timetable.build_month(Month(2026, 10), [late, early_b, early_a], TODAY), day)
    assert box["entries"] == [early_a, early_b, late]


def test_build_month_marks_today_and_leaves_days_outside_empty():
    weeks = timetable.build_month(Month(2026, 9), [], TODAY)
    assert weeks[0][0] is None
    assert [box["date"] for box in weeks[4] if box and box["is_today"]] == [TODAY]
    assert box_for(weeks, date(2026, 9, 1)) == {
        "date": date(2026, 9, 1),
        "label": "Tue 1 Sep",
        "is_today": False,
        "entries": [],
        "more": 0,
    }


def test_build_month_puts_classes_on_their_local_start_date():
    """Criterion 10: the three time-zone edges, placed by local date."""
    after_midnight = unsaved(datetime(2026, 9, 30, 19, 0, tzinfo=UTC), pk=1)  # 1 Oct 00:30
    at_midnight = unsaved(datetime(2026, 8, 31, 18, 30, tzinfo=UTC), pk=2)  # 1 Sep 00:00
    before_midnight = unsaved(datetime(2026, 9, 30, 18, 25, tzinfo=UTC), pk=3)  # 30 Sep 23:55
    everything = [after_midnight, at_midnight, before_midnight]

    september = timetable.build_month(Month(2026, 9), everything, TODAY)
    assert box_for(september, date(2026, 9, 1))["entries"] == [at_midnight]
    assert box_for(september, date(2026, 9, 30))["entries"] == [before_midnight]
    october = timetable.build_month(Month(2026, 10), everything, TODAY)
    assert box_for(october, date(2026, 10, 1))["entries"] == [after_midnight]


def test_day_entries_lists_every_class_of_the_day_sorted():
    day = date(2026, 10, 7)
    occurrences = [unsaved(local(day, 18 - n).astimezone(UTC), pk=n + 1) for n in range(6)]
    other_day = unsaved(local(date(2026, 10, 8)).astimezone(UTC), pk=99)
    entries = timetable.day_entries(occurrences + [other_day], day)
    assert entries == list(reversed(occurrences))


def test_day_bounds_are_local_midnights():
    assert timetable.day_bounds(date(2026, 10, 7)) == (
        datetime(2026, 10, 7, tzinfo=COLOMBO),
        datetime(2026, 10, 8, tzinfo=COLOMBO),
    )


def test_entry_counts_splits_booked_and_waiting():
    now = datetime(2026, 10, 7, 3, 0, tzinfo=UTC)
    entries = [unsaved(now), unsaved(now), unsaved(now, status=WAITING)]
    assert timetable.entry_counts(entries) == (2, 1)
    assert timetable.entry_counts([]) == (0, 0)


def _flagged(pk, label, on_timetable):
    account = HostAccount(pk=pk, label=label)
    account.on_timetable = on_timetable
    return account


def test_account_filter_offers_the_flagged_accounts_and_resolves_the_choice():
    one, two = _flagged(1, "Zoom 01", True), _flagged(2, "Zoom 02", True)
    idle = _flagged(3, "Old Zoom", False)
    assert timetable.account_filter([one, two, idle], None) == ([one, two], None)
    assert timetable.account_filter([one, two, idle], 2) == ([one, two], two)
    assert timetable.account_filter([one, two, idle], 42) == ([one, two], None)


def test_account_filter_appends_a_chosen_account_that_isnt_an_option():
    """OQ2, D9: the select must list the chosen account exactly once."""
    one, idle = _flagged(1, "Zoom 01", True), _flagged(3, "Old Zoom", False)
    options, selected = timetable.account_filter([idle, one], 3)
    assert options == [one, idle]
    assert selected is idle


# =========================================================================== QuerySets


@pytest.mark.django_db
def test_in_period_is_half_open_on_starts():
    account = make_account("Zoom 01")
    inside = add_class(account, date(2026, 10, 1), time(0, 0), time(1, 0))
    add_class(account, date(2026, 11, 1), time(0, 0), time(1, 0))
    add_class(account, date(2026, 9, 30), time(23, 0), time(23, 55))
    month = Month(2026, 10)
    assert list(Occurrence.objects.in_period(month.start, month.end)) == [inside]


@pytest.mark.django_db
def test_for_timetable_keeps_booked_and_waiting_only():
    """Criterion 8: unverified and rejected requests never appear."""
    account = make_account("Zoom 01")
    booked = add_class(account, date(2026, 10, 5))
    waiting = add_class(day=date(2026, 10, 6))
    add_class(day=date(2026, 10, 7), status=LinkRequest.Status.UNVERIFIED)
    add_class(day=date(2026, 10, 8), status=LinkRequest.Status.REJECTED, rejection_reason="No")
    month = Month(2026, 10)
    assert list(Occurrence.objects.for_timetable(month.start, month.end)) == [booked, waiting]


@pytest.mark.django_db
def test_for_timetable_with_an_account_drops_waiting_and_other_accounts():
    """D1: a waiting class holds no account, so an account filter can't include it."""
    one, two = make_account("Zoom 01"), make_account("Zoom 02")
    mine = add_class(one, date(2026, 10, 5))
    add_class(two, date(2026, 10, 5), time(12, 0), time(13, 0))
    add_class(day=date(2026, 10, 6))
    month = Month(2026, 10)
    assert list(Occurrence.objects.for_timetable(month.start, month.end, account=one)) == [mine]


@pytest.mark.django_db
def test_for_timetable_orders_by_start_then_pk_and_joins_request_and_account():
    account = make_account("Zoom 01")
    later = add_class(account, date(2026, 10, 5), time(12, 0), time(13, 0))
    first = add_class(account, date(2026, 10, 5), time(8, 0), time(9, 0))
    second = add_class(day=date(2026, 10, 5), start=time(8, 0), end=time(9, 0))
    month = Month(2026, 10)
    qs = Occurrence.objects.for_timetable(month.start, month.end)
    assert list(qs) == [first, second, later]
    with CaptureQueriesContext(connection) as queries:
        rows = list(qs.all())
        [(o.link_request.reference, o.host_account and o.host_account.label) for o in rows]
    assert len(queries) == 1


@pytest.mark.django_db
def test_timetable_accounts_are_bookable_or_booked_in_the_month_in_order():
    """Criterion 11: every bookable account, plus any other with a booked class that month."""
    month = Month(2026, 10)
    second = make_account("Zoom 02", sort_order=2)
    first = make_account("Zoom 09", sort_order=1)
    retired = make_account("Old Zoom", sort_order=5, is_active=False)
    free = make_account("Free Zoom", sort_order=0, is_paid=False)
    make_account("Idle old Zoom", sort_order=0, is_active=False)
    booked_elsewhere = make_account("Retired in Sep", sort_order=0, is_active=False)
    add_class(retired, date(2026, 10, 20))
    add_class(free, date(2026, 10, 2))
    add_class(booked_elsewhere, date(2026, 9, 2))

    with CaptureQueriesContext(connection) as queries:
        accounts = list(HostAccount.objects.timetable_accounts(month.start, month.end))
    assert len(queries) == 1
    assert accounts == [free, first, second, retired]


@pytest.mark.django_db
def test_timetable_accounts_load_only_what_the_timetable_reads():
    """Review round 1, nit 3: the encrypted host key and the other private fields are
    deferred, never fetched; pk, label and sort_order are loaded."""
    make_account("Zoom 01", host_key="8421973")
    month = Month(2026, 10)
    with CaptureQueriesContext(connection) as queries:
        (account,) = HostAccount.objects.with_timetable_flag(month.start, month.end)
        assert (account.label, account.sort_order, account.on_timetable) == ("Zoom 01", 0, True)
    assert len(queries) == 1
    assert "host_key_encrypted" not in queries[0]["sql"]
    assert {"host_key_encrypted", "email", "notes", "credential_set"} <= (
        account.get_deferred_fields()
    )


@pytest.mark.django_db
def test_waiting_classes_do_not_put_an_account_on_the_timetable():
    retired = make_account("Old Zoom", is_active=False)
    link_request = make_request(status=WAITING, first_date=date(2026, 10, 5))
    link_request.occurrences.update(host_account=retired)  # never happens; still not booked
    month = Month(2026, 10)
    assert list(HostAccount.objects.timetable_accounts(month.start, month.end)) == []


# =========================================================================== access (criterion 1)


@pytest.fixture
def october_7():
    return date(2026, 10, 7)


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["month", "day"])
def test_anonymous_visitors_are_sent_to_sign_in(client, name, october_7):
    url = MONTH_URL if name == "month" else day_url(october_7)
    response = client.get(url)
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login") + "?next=")


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["month", "day"])
@pytest.mark.parametrize("who", ["plain_user", "staff_user"])
def test_signed_in_users_without_the_permission_get_403(client, request, who, name, october_7):
    client.force_login(request.getfixturevalue(who))
    url = MONTH_URL if name == "month" else day_url(october_7)
    assert client.get(url).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["month", "day"])
@pytest.mark.parametrize("who", ["it_user", "superuser"])
def test_it_users_and_superusers_get_the_pages(client, request, who, name, october_7):
    client.force_login(request.getfixturevalue(who))
    url = MONTH_URL if name == "month" else day_url(october_7)
    assert client.get(url).status_code == 200


# =========================================================================== month page


@pytest.mark.django_db
def test_month_page_supplies_the_context_contract(it_client):
    account = make_account("Zoom 01")
    booked = add_class(account, date(2026, 9, 29))
    waiting = add_class(day=date(2026, 9, 30))
    context = it_client.get(MONTH_URL).context

    assert context["month"] == Month(2026, 9)
    assert context["previous_month"] == Month(2026, 8)
    assert context["next_month"] == Month(2026, 10)
    assert context["is_current_month"] is True
    assert context["weekdays"] == [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    assert context["weeks"] == timetable.build_month(Month(2026, 9), [booked, waiting], TODAY)
    assert box_for(context["weeks"], TODAY)["is_today"] is True
    assert context["filter_accounts"] == [account]
    assert context["selected_account"] is None
    assert context["show_waiting"] is True
    assert (context["booked_count"], context["waiting_count"]) == (1, 1)
    assert context["has_accounts"] is True
    assert context["can_add_account"] is True


@pytest.mark.django_db
def test_month_parameter_chooses_the_month_and_bad_values_fall_back(it_client):
    context = it_client.get(MONTH_URL, {"month": "2026-10"}).context
    assert context["month"] == Month(2026, 10)
    assert context["is_current_month"] is False
    for bad in ("2026-13", "2026-1", "abc", "", "1999-12"):
        response = it_client.get(MONTH_URL, {"month": bad})
        assert response.status_code == 200
        assert response.context["month"] == Month(2026, 9), bad


@pytest.mark.django_db
def test_non_ascii_digits_in_the_month_fall_back(it_client):
    """Review round 1, nit 4: ``?month=２０２６-１０`` (full-width) is not October; it's
    the current month, exactly like any other bad value."""
    for value in ("２０２６-０９", "２０２６-１０"):
        response = it_client.get(MONTH_URL, {"month": value})
        assert response.status_code == 200
        assert response.context["month"] == Month(2026, 9), value
        assert response.context["is_current_month"] is True, value


@pytest.mark.django_db
def test_month_page_shows_classes_on_their_local_day(it_client):
    """Criterion 10, through the database: bounds are local midnights, stored in UTC."""
    account = make_account("Zoom 01")

    def stored_at(utc):
        occurrence = add_class(account, date(2026, 10, 20))
        Occurrence.objects.filter(pk=occurrence.pk).update(
            starts_at=utc, ends_at=utc.replace(minute=(utc.minute + 5) % 60)
        )
        return Occurrence.objects.get(pk=occurrence.pk)

    oct_1 = stored_at(datetime(2026, 9, 30, 19, 0, tzinfo=UTC))
    sep_1 = stored_at(datetime(2026, 8, 31, 18, 30, tzinfo=UTC))
    sep_30 = stored_at(datetime(2026, 9, 30, 18, 25, tzinfo=UTC))

    september = it_client.get(MONTH_URL, {"month": "2026-09"}).context["weeks"]
    assert box_for(september, date(2026, 9, 1))["entries"] == [sep_1]
    assert box_for(september, date(2026, 9, 30))["entries"] == [sep_30]
    assert oct_1 not in [e for week in september for box in week if box for e in box["entries"]]
    october = it_client.get(MONTH_URL, {"month": "2026-10"}).context["weeks"]
    assert box_for(october, date(2026, 10, 1))["entries"] == [oct_1]


@pytest.mark.django_db
def test_a_busy_day_shows_three_and_counts_the_rest(it_client, october_7):
    """Criterion 9: 5 entries on Wed 7 Oct 2026 → 3 entries plus ``+2 more``."""
    account = make_account("Zoom 01")
    classes = [add_class(account, october_7, time(8 + n, 0), time(8 + n, 55)) for n in range(5)]
    weeks = it_client.get(MONTH_URL, {"month": "2026-10"}).context["weeks"]
    box = box_for(weeks, october_7)
    assert box["entries"] == classes[:3]
    assert box["more"] == 2


@pytest.mark.django_db
def test_account_filter_shows_one_accounts_booked_classes_only(it_client):
    """Criterion 11: waiting classes are left out while filtered (D1)."""
    one, two = make_account("Zoom 01", sort_order=1), make_account("Zoom 02", sort_order=2)
    mine = add_class(one, date(2026, 10, 5))
    add_class(two, date(2026, 10, 5), time(12, 0), time(13, 0))
    add_class(day=date(2026, 10, 6))

    context = it_client.get(MONTH_URL, {"month": "2026-10", "account": one.pk}).context
    shown = [e for week in context["weeks"] for box in week if box for e in box["entries"]]
    assert shown == [mine]
    assert context["selected_account"] == one
    assert context["filter_accounts"] == [one, two]
    assert context["show_waiting"] is False
    assert (context["booked_count"], context["waiting_count"]) == (1, 0)


@pytest.mark.django_db
@pytest.mark.parametrize("bad", ["9999", "abc", "", "-1", "1.5"])
def test_bad_account_values_fall_back_to_all_accounts(it_client, bad):
    account = make_account("Zoom 01")
    add_class(account, date(2026, 10, 5))
    add_class(day=date(2026, 10, 6))
    response = it_client.get(MONTH_URL, {"month": "2026-10", "account": bad})
    assert response.status_code == 200
    assert response.context["selected_account"] is None
    assert response.context["show_waiting"] is True
    assert (response.context["booked_count"], response.context["waiting_count"]) == (1, 1)


@pytest.mark.django_db
def test_filtering_to_an_account_outside_the_options_lists_it_once_at_the_same_cost(it_client):
    """Criterion 11 / OQ2: the chosen idle account is appended, with no extra query."""
    in_use = make_account("Zoom 01", sort_order=1)
    retired = make_account("Old Zoom", sort_order=0, is_active=False)
    add_class(in_use, date(2026, 10, 5))
    query = {"month": "2026-10"}
    it_client.get(MONTH_URL, query)  # warm per-process caches

    with CaptureQueriesContext(connection) as in_list:
        context = it_client.get(MONTH_URL, {**query, "account": in_use.pk}).context
    assert context["filter_accounts"] == [in_use]

    with CaptureQueriesContext(connection) as outside:
        context = it_client.get(MONTH_URL, {**query, "account": retired.pk}).context
    assert context["selected_account"] == retired
    assert context["filter_accounts"] == [in_use, retired]
    assert [a.pk for a in context["filter_accounts"]].count(retired.pk) == 1
    assert context["booked_count"] == 0
    assert len(outside) == len(in_list)


@pytest.mark.django_db
def test_summary_counts(it_client):
    """Criterion 12: the numbers behind the summary line, filtered and not."""
    account = make_account("Zoom 01")
    for n in range(3):
        add_class(account, date(2026, 9, 1 + n))
    add_class(day=date(2026, 9, 29))
    add_class(account, date(2026, 10, 1))  # next month: not counted
    context = it_client.get(MONTH_URL).context
    assert (context["booked_count"], context["waiting_count"]) == (3, 1)
    context = it_client.get(MONTH_URL, {"account": account.pk}).context
    assert (context["booked_count"], context["waiting_count"]) == (3, 0)


@pytest.mark.django_db
def test_no_accounts_at_all(it_client):
    """Criterion 13: no accounts → ``has_accounts`` False; the grid is still built."""
    add_class(day=date(2026, 9, 29))
    context = it_client.get(MONTH_URL).context
    assert context["has_accounts"] is False
    assert context["filter_accounts"] == []
    assert len(context["weeks"]) == 5
    assert context["waiting_count"] == 1


@pytest.mark.django_db
def test_has_accounts_counts_accounts_that_are_not_options(it_client):
    make_account("Old Zoom", is_active=False)
    context = it_client.get(MONTH_URL).context
    assert context["filter_accounts"] == []
    assert context["has_accounts"] is True


@pytest.mark.django_db
def test_can_add_account_follows_the_add_permission(client, django_user_model):
    reviewer = django_user_model.objects.create_user(username="reviewer", password="pw")
    reviewer.user_permissions.add(Permission.objects.get(codename="review_linkrequest"))
    client.force_login(reviewer)
    assert client.get(MONTH_URL).context["can_add_account"] is False


# =========================================================================== day view


@pytest.mark.django_db
@pytest.mark.parametrize("parts", [(2026, 2, 30), (2026, 13, 1), (1999, 12, 31), (2101, 1, 1)])
def test_impossible_or_out_of_range_days_are_404(it_client, parts):
    assert it_client.get(reverse("zoom:timetable_day", args=parts)).status_code == 404


@pytest.mark.django_db
def test_day_view_supplies_the_context_contract(it_client, october_7):
    """Criterion 14: every entry, no cap, sorted; the date labels; ``month_url``."""
    account = make_account("Zoom 01")
    classes = [add_class(account, october_7, time(18 - n, 0), time(18 - n, 55)) for n in range(5)]
    waiting = add_class(day=october_7, start=time(7, 0), end=time(7, 55))
    add_class(account, date(2026, 10, 8))
    context = it_client.get(day_url(october_7)).context

    assert context["day"] == october_7
    assert context["day_label"] == "Wed 7 Oct 2026"
    assert context["previous_day"] == date(2026, 10, 6)
    assert context["next_day"] == date(2026, 10, 8)
    assert context["month"] == Month(2026, 10)
    assert context["month_url"] == f"{MONTH_URL}?month=2026-10"
    assert context["entries"] == [waiting] + list(reversed(classes))
    assert context["filter_accounts"] == [account]
    assert context["selected_account"] is None
    assert context["show_waiting"] is True


@pytest.mark.django_db
def test_day_view_filtered_keeps_the_account_in_month_url(it_client, october_7):
    one, two = make_account("Zoom 01"), make_account("Zoom 02")
    mine = add_class(one, october_7)
    add_class(two, october_7, time(12, 0), time(13, 0))
    add_class(day=october_7, start=time(14, 0), end=time(15, 0))
    context = it_client.get(day_url(october_7, account=one.pk)).context
    assert context["entries"] == [mine]
    assert context["selected_account"] == one
    assert context["show_waiting"] is False
    assert context["month_url"] == f"{MONTH_URL}?month=2026-10&account={one.pk}"


@pytest.mark.django_db
def test_day_view_filter_offers_that_months_accounts_and_appends_an_outside_one(
    it_client, october_7
):
    in_use = make_account("Zoom 01", sort_order=1)
    retired_with_class = make_account("Old A", sort_order=0, is_active=False)
    retired_idle = make_account("Old B", sort_order=0, is_active=False)
    add_class(retired_with_class, date(2026, 10, 30))  # same month, another day
    context = it_client.get(day_url(october_7, account=retired_idle.pk)).context
    assert context["filter_accounts"] == [retired_with_class, in_use, retired_idle]
    assert context["selected_account"] == retired_idle
    assert context["entries"] == []


@pytest.mark.django_db
def test_day_view_edges_of_the_local_day(it_client):
    account = make_account("Zoom 01")
    at_midnight = add_class(account, date(2026, 10, 1), time(0, 0), time(1, 0))
    before_midnight = add_class(account, date(2026, 9, 30), time(23, 0), time(23, 55))
    assert it_client.get(day_url(date(2026, 10, 1))).context["entries"] == [at_midnight]
    assert it_client.get(day_url(date(2026, 9, 30))).context["entries"] == [before_midnight]


@pytest.mark.django_db
def test_the_two_pages_agree(it_client):
    """Criterion 15: each day view lists exactly what its month box shows plus ``more``."""
    accounts = [make_account(f"Zoom {n:02d}", sort_order=n) for n in range(1, 4)]
    days = [date(2026, 10, 1), date(2026, 10, 7), date(2026, 10, 31)]
    for index, day in enumerate(days):
        for n in range(index * 3 + 1):
            add_class(accounts[n % 3], day, time(6 + n, 0), time(6 + n, 55))
        add_class(day=day, start=time(20, 0), end=time(21, 0))

    for query in ({}, {"account": accounts[0].pk}):
        weeks = it_client.get(MONTH_URL, {"month": "2026-10", **query}).context["weeks"]
        for day in days:
            box = box_for(weeks, day)
            entries = it_client.get(day_url(day, **query)).context["entries"]
            assert entries[: len(box["entries"])] == box["entries"], (day, query)
            assert len(entries) == len(box["entries"]) + box["more"], (day, query)


# =========================================================================== query budget


def _busy_october():
    """Criterion 18's large case: 150 classes over 8 accounts, 10 waiting, 12 on one day."""
    accounts = [make_account(f"Zoom {n:02d}", sort_order=n) for n in range(3, 9)]
    accounts += list(HostAccount.objects.filter(label__in=["Zoom 01", "Zoom 02"]))
    busy = date(2026, 10, 7)
    for n in range(12):
        add_class(accounts[n % 8], busy, time(6 + n, 0), time(6 + n, 55))
    for n in range(150 - 3 - 12):
        add_class(accounts[n % 8], date(2026, 10, 1 + n % 31), time(8, 0), time(8, 55))
    for n in range(10):
        add_class(day=date(2026, 10, 1 + n), start=time(19, 0), end=time(20, 0))


@pytest.mark.django_db
def test_both_pages_run_a_fixed_number_of_queries(it_client):
    """Criterion 18: 3 classes on 2 accounts, then 150 on 8 plus 10 waiting; with and
    without ``?account=``. Every case costs the same: the shell's fixed queries, one for the
    filter's accounts and one for the classes."""
    _assert_fixed_query_count(it_client)


def _assert_fixed_query_count(it_client):
    one, two = make_account("Zoom 01", sort_order=1), make_account("Zoom 02", sort_order=2)
    add_class(one, date(2026, 10, 5))
    add_class(two, date(2026, 10, 7))
    add_class(one, date(2026, 10, 7), time(12, 0), time(13, 0))
    busy = date(2026, 10, 7)
    urls = {
        "month": (MONTH_URL, {"month": "2026-10"}),
        "month filtered": (MONTH_URL, {"month": "2026-10", "account": one.pk}),
        "day": (day_url(busy), {}),
        "day filtered": (day_url(busy), {"account": one.pk}),
    }
    it_client.get(MONTH_URL)  # warm per-process caches (content types, permissions)

    def counts():
        result = {}
        for name, (url, query) in urls.items():
            with CaptureQueriesContext(connection) as queries:
                assert it_client.get(url, query).status_code == 200
            result[name] = len(queries)
        return result

    small = counts()
    _busy_october()
    large = counts()
    assert Occurrence.objects.count() == 3 + 147 + 10
    assert large == small
    assert len(set(small.values())) == 1, small
    assert len(it_client.get(day_url(busy)).context["entries"]) >= 12


# =========================================================================== detail link (20)


@pytest.mark.django_db
def test_approved_request_detail_links_to_its_month_and_account(it_client):
    account = make_account("Zoom 03")
    occurrence = add_class(account, date(2026, 11, 3))
    response = it_client.get(reverse("zoom:detail", args=[occurrence.link_request_id]))
    assert response.context["timetable_url"] == f"{MONTH_URL}?month=2026-11&account={account.pk}"


@pytest.mark.django_db
def test_weekly_request_links_to_the_month_of_its_first_class(it_client):
    account = make_account("Zoom 03")
    link_request = make_request(
        status=APPROVED,
        first_date=date(2026, 10, 26),
        weekdays="1",
        last_date=date(2026, 11, 30),
        host_account=account,
        join_url="https://zoom.example/j/1",
    )
    link_request.occurrences.update(host_account=account)
    context = it_client.get(reverse("zoom:detail", args=[link_request.pk])).context
    assert context["timetable_url"] == f"{MONTH_URL}?month=2026-10&account={account.pk}"


@pytest.mark.django_db
@pytest.mark.parametrize("status", [WAITING, LinkRequest.Status.REJECTED])
def test_waiting_and_rejected_requests_have_no_timetable_link(it_client, status):
    extra = {"rejection_reason": "Clash"} if status == LinkRequest.Status.REJECTED else {}
    link_request = make_request(status=status, **extra)
    response = it_client.get(reverse("zoom:detail", args=[link_request.pk]))
    assert response.context["timetable_url"] is None


# =========================================================================== real templates


@pytest.mark.django_db
def test_neither_page_shows_private_data(client, settings, it_user, october_7):
    """Criterion 16: no host key or its state, no requester details, no meeting details."""
    _real_templates(settings)
    client.force_login(it_user)
    host_key = "8421973"
    accounts = [make_account(f"Zoom {n:02d}", sort_order=n, host_key=host_key) for n in (1, 2)]
    make_account("Zoom 03", sort_order=3)  # no key: "Not saved" on the accounts page
    for n in range(6):
        add_class(accounts[n % 2], october_7, time(8 + n, 0), time(8 + n, 55), wants_recording=True)
    add_class(day=october_7, start=time(19, 0), end=time(20, 0))

    pages = {
        "month": client.get(MONTH_URL, {"month": "2026-10"}),
        "month filtered": client.get(MONTH_URL, {"month": "2026-10", "account": accounts[0].pk}),
        "day": client.get(day_url(october_7)),
    }
    forbidden = [
        host_key,
        "gAAAAA",
        ">Saved<",
        "Not saved",
        "Nimali Perera",
        "nimali@example.com",
        "+94771234567",
        "+94 77 123 4567",
        "zoom.example/j/",
        "123456789",
        "483920",
    ]
    for name, response in pages.items():
        assert response.status_code == 200, name
        html = response.content.decode()
        assert "CCC Batch 3 - Mathematics" in html, name
        for text in forbidden:
            assert text not in html, (name, text)


@pytest.mark.django_db
def test_real_pages_run_a_fixed_number_of_queries(client, settings, it_user):
    """Criterion 18 on the real markup: no template follows a relation that isn't joined in."""
    _real_templates(settings)
    client.force_login(it_user)
    _assert_fixed_query_count(client)


@pytest.mark.django_db
def test_timetable_is_the_current_sidebar_item_between_requests_and_accounts(
    client, settings, it_user, october_7
):
    """Criterion 2, extending brief 008's sidebar tests on purpose."""
    _real_templates(settings)
    client.force_login(it_user)
    for url in (MONTH_URL, day_url(october_7)):
        nav = _sidenav(client.get(url).content.decode())
        assert nav.index("Link requests") < nav.index("Timetable") < nav.index("Zoom accounts")
        assert 'aria-current="page"' in _item(nav, "zoom:timetable"), url
        assert nav.count('aria-current="page"') == 1, url

    nav = _sidenav(client.get(reverse("zoom:queue")).content.decode())
    assert 'aria-current="page"' not in _item(nav, "zoom:timetable")


@pytest.mark.django_db
def test_timetable_sidebar_item_needs_the_review_permission(client, settings, django_user_model):
    _real_templates(settings)
    viewer = django_user_model.objects.create_user(username="viewer", password="pw")
    viewer.user_permissions.add(Permission.objects.get(codename="view_hostaccount"))
    client.force_login(viewer)
    nav = _sidenav(client.get(reverse("zoom:accounts")).content.decode())
    assert _item(nav, "zoom:timetable") is None


class _TableCells(HTMLParser):
    """Collects the calendar table's attributes and, per row, each ``th`` / ``td``'s."""

    def __init__(self):
        super().__init__()
        self.table = None
        self.inside = False
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and "cal" in (attrs.get("class") or "").split():
            self.table, self.inside = attrs, True
        elif self.inside and tag == "tr":
            self.rows.append([])
        elif self.inside and tag in ("th", "td"):
            self.rows[-1].append((tag, attrs))

    def handle_endtag(self, tag):
        if tag == "table":
            self.inside = False


@pytest.mark.django_db
@pytest.mark.parametrize("month", ["2026-09", "2026-11", "2027-02"])
def test_month_table_carries_column_count_and_index_on_every_cell(client, settings, it_user, month):
    """Review round 1, SF1: below 768px CSS hides out-of-month and empty days, so each cell
    states its own weekday column. ``aria-colcount="7"`` on the table, and ``aria-colindex``
    1 to 7, in order, on every ``th`` and every ``td``, empty and out-of-month cells too."""
    _real_templates(settings)
    client.force_login(it_user)
    add_class(make_account("Zoom 01"), date(2026, 9, 29))
    parser = _TableCells()
    parser.feed(client.get(MONTH_URL, {"month": month}).content.decode())

    assert parser.table is not None, "no calendar table"
    assert parser.table.get("aria-colcount") == "7"
    header, *weeks = parser.rows
    assert [tag for tag, _ in header] == ["th"] * 7
    assert weeks, "no week rows"
    for row in parser.rows:
        assert len(row) == 7, row
        assert [attrs.get("aria-colindex") for _, attrs in row] == [str(n) for n in range(1, 8)]
    assert all(tag == "td" for week in weeks for tag, _ in week)
