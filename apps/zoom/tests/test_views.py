"""Views: status codes, redirects, permissions, emails and the context contract (brief 005,
criteria 4-6, 9-11, 13-18, 20, 22-25, 28-32, 35-43, 59, 61, 65)."""

import logging
import re
from datetime import UTC, date, datetime, time, timedelta
from unittest import mock

import pytest
from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.core import mail
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from apps.zoom import services
from apps.zoom.models import HostAccount, HostSlot, LinkRequest, Occurrence
from apps.zoom.providers import FakeProvider

from .conftest import FROZEN_NOW, book, make_account, make_request

pytestmark = pytest.mark.django_db
HOST_KEY = "8421973"


def _form_data(**overrides):
    data = {
        "class_name": "CCC Batch 3 - Mathematics",
        "first_date": "2026-10-05",
        "start_time": "08:30",
        "end_time": "11:30",
        "repeat": "once",
        "requester_name": "Nimali Perera",
        "requester_email": "  Nimali@Example.COM ",
        "requester_phone": "077 123 4567",
        "notes": "",
        "website": "",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def _messages(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# --------------------------------------------------------------------------- request form


def test_request_form_get_is_public_and_supplies_the_contract(client):
    response = client.get(reverse("zoom:request"))
    assert response.status_code == 200
    context = response.context
    assert context["max_occurrences"] == 60
    assert context["today"] == date(2026, 9, 28)
    assert context["latest_date"] == date(2027, 9, 28)
    fields = set(context["form"].fields)
    assert fields == {
        "class_name",
        "first_date",
        "start_time",
        "end_time",
        "repeat",
        "weekdays",
        "last_date",
        "wants_recording",
        "requester_name",
        "requester_email",
        "requester_phone",
        "notes",
        "website",
    }
    assert [c[0] for c in context["form"].fields["weekdays"].choices] == list("1234567")
    assert context["form"]["wants_recording"].value() is False


def test_one_off_request_is_stored_unverified_and_the_confirm_email_sent(client):
    response = client.post(reverse("zoom:request"), _form_data(), REMOTE_ADDR="10.1.2.3")
    assert response.status_code == 302
    assert response.url == reverse("zoom:request_sent")

    link_request = LinkRequest.objects.get()
    assert link_request.status == LinkRequest.Status.UNVERIFIED
    assert link_request.requester_email == "nimali@example.com"
    assert link_request.requester_phone == "+94771234567"
    assert link_request.submitted_ip == "10.1.2.3"
    assert link_request.wants_recording is False
    [occurrence] = link_request.occurrences.all()
    assert (occurrence.starts_at, occurrence.ends_at) == (
        datetime(2026, 10, 5, 3, 0, tzinfo=UTC),
        datetime(2026, 10, 5, 6, 0, tzinfo=UTC),
    )
    assert HostSlot.objects.count() == 0
    [message] = mail.outbox
    assert message.to == ["nimali@example.com"]
    assert message.subject == "Confirm your Zoom link request"
    # The token carries a timestamp, so read the URL from the email rather than rebuild it.
    [confirm_url] = re.findall(r"http://testserver/zoom/confirm/\S+/", message.body)
    token = resolve(confirm_url.removeprefix("http://testserver")).kwargs["token"]
    assert services.confirm_state(token) == ("ready", link_request)

    sent = client.get(response.url)
    assert sent.context["sent_to"] == "nimali@example.com"
    assert sent.context["link_hours"] == 24
    assert client.get(response.url).context["sent_to"] is None  # shown once


def test_weekly_request_makes_eight_classes_and_stores_sorted_days(client):
    client.post(
        reverse("zoom:request"),
        _form_data(
            repeat="weekly", weekdays=["3", "1"], last_date="2026-10-28", wants_recording="on"
        ),
    )
    link_request = LinkRequest.objects.get()
    assert link_request.weekdays == "1,3"
    assert link_request.wants_recording is True
    assert link_request.occurrences.count() == 8


def test_once_ignores_weekly_fields(client):
    client.post(reverse("zoom:request"), _form_data(weekdays=["1"], last_date="2026-10-28"))
    link_request = LinkRequest.objects.get()
    assert (link_request.weekdays, link_request.last_date) == ("", None)
    assert link_request.occurrences.count() == 1


# The exact error copy pinned by criterion 6.
E_CLASS = "Type the name of the class, like CCC Batch 3 - Mathematics."
E_END = "The class must end after it starts. Check the end time."
E_STEP = "Use a time on a 5-minute step, like 8:30 or 8:35."
E_PASSED = "Choose a date and time that haven't passed yet."
E_FAR = "Choose a date within the next year."
E_NO_DAYS = "Tick at least one day of the week."
E_LAST = "Choose the date of the last class, on or after the first class."
E_NONE_IN_RANGE = "None of the days you ticked fall between the first and last class dates."
E_TOO_MANY = (
    "That makes 128 classes. One request can cover up to 60. Choose an earlier last date, "
    "or send a second request for the rest."
)
E_NAME = "Type your full name."
E_EMAIL = (
    "Type an email address you can open now, like nimali@example.com. We'll send a link to it."
)
E_PHONE = "Type a phone number we can call, like 077 123 4567 or +94 77 123 4567."
WEEKLY = {"repeat": "weekly"}
MON_TO_FRI = ["1", "2", "3", "4", "5"]


@pytest.mark.parametrize(
    ("overrides", "field", "error"),
    [
        ({"class_name": ""}, "class_name", E_CLASS),
        ({"end_time": "08:30"}, "end_time", E_END),
        ({"start_time": "08:32"}, "start_time", E_STEP),
        ({"end_time": "11:32"}, "end_time", E_STEP),
        ({"first_date": "2026-09-27"}, "first_date", E_PASSED),
        ({"first_date": "2026-09-28", "start_time": "09:55"}, "first_date", E_PASSED),
        ({"first_date": "2027-09-29"}, "first_date", E_FAR),
        ({**WEEKLY, "last_date": "2026-10-28"}, "weekdays", E_NO_DAYS),
        ({**WEEKLY, "weekdays": ["1"]}, "last_date", E_LAST),
        ({**WEEKLY, "weekdays": ["1"], "last_date": "2026-10-04"}, "last_date", E_LAST),
        ({**WEEKLY, "weekdays": ["2"], "last_date": "2026-10-05"}, "weekdays", E_NONE_IN_RANGE),
        ({**WEEKLY, "weekdays": MON_TO_FRI, "last_date": "2027-03-31"}, "last_date", E_TOO_MANY),
        ({"requester_name": ""}, "requester_name", E_NAME),
        ({"requester_email": "nimali@"}, "requester_email", E_EMAIL),
        ({"requester_phone": "12345"}, "requester_phone", E_PHONE),
        ({"requester_phone": ""}, "requester_phone", E_PHONE),
        ({"class_name": "x" * 201}, "class_name", None),
        ({"notes": "x" * 1001}, "notes", None),
    ],
)
def test_invalid_request_rerenders_with_the_pinned_error_and_keeps_values(
    client, overrides, field, error
):
    response = client.post(reverse("zoom:request"), _form_data(**overrides))
    assert response.status_code == 200
    form = response.context["form"]
    assert field in form.errors
    if error:
        assert error in form.errors[field]
    assert form["requester_name"].value() == _form_data(**overrides).get("requester_name")
    assert LinkRequest.objects.count() == 0
    assert mail.outbox == []


def test_honeypot_looks_like_success_but_stores_and_sends_nothing(client):
    response = client.post(reverse("zoom:request"), _form_data(website="http://spam.example"))
    assert response.status_code == 302
    assert response.url == reverse("zoom:request_sent")
    assert LinkRequest.objects.count() == 0 and Occurrence.objects.count() == 0
    assert mail.outbox == []


THROTTLED = (
    "You've sent a lot of requests in the last hour. Wait an hour, then try again, "
    "or phone the IT desk."
)


def test_sixth_request_from_one_email_in_an_hour_gets_429(client):
    for _ in range(5):
        make_request(email="nimali@example.com", submitted_ip="10.9.9.9")
    response = client.post(reverse("zoom:request"), _form_data())
    assert response.status_code == 429
    assert response.context["form"].non_field_errors() == [THROTTLED]
    assert response.context["form"]["class_name"].value() == "CCC Batch 3 - Mathematics"
    assert LinkRequest.objects.count() == 5 and mail.outbox == []


def test_twenty_first_request_from_one_ip_gets_429_and_old_ones_do_not_count(client):
    for number in range(20):
        make_request(email=f"p{number}@example.com", submitted_ip="127.0.0.1")
    assert client.post(reverse("zoom:request"), _form_data()).status_code == 429
    LinkRequest.objects.filter(pk=LinkRequest.objects.first().pk).update(
        created_at=FROZEN_NOW - timedelta(minutes=61)
    )
    assert client.post(reverse("zoom:request"), _form_data()).status_code == 302


def test_throttle_is_not_applied_to_invalid_posts(client):
    for _ in range(5):
        make_request(email="nimali@example.com")
    assert client.post(reverse("zoom:request"), _form_data(class_name="")).status_code == 200


def test_forwarded_ip_is_used_only_with_a_trusted_proxy(client, settings):
    client.post(reverse("zoom:request"), _form_data(), HTTP_X_FORWARDED_FOR="203.0.113.9")
    settings.TRUSTED_PROXY_COUNT = 1
    client.post(
        reverse("zoom:request"),
        _form_data(requester_email="b@example.com"),
        HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.9",
    )
    assert list(LinkRequest.objects.order_by("pk").values_list("submitted_ip", flat=True)) == [
        "127.0.0.1",
        "203.0.113.9",
    ]


# --------------------------------------------------------------------------- confirm


def _confirm_url(link_request):
    return reverse("zoom:confirm", args=[services.confirm_token(link_request)])


def test_confirm_get_shows_ready_and_changes_nothing(client):
    link_request = make_request(
        status=LinkRequest.Status.UNVERIFIED, weekdays="1,3", last_date=date(2026, 10, 28)
    )
    token = services.confirm_token(link_request)
    response = client.get(reverse("zoom:confirm", args=[token]))
    assert response.status_code == 200
    assert response.context["state"] == "ready"
    assert response.context["link_request"] == link_request
    assert len(response.context["occurrences"]) == response.context["occurrence_count"] == 8
    assert response.context["token"] == token
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.UNVERIFIED


def test_confirm_post_moves_to_waiting_and_emails_every_reviewer(
    client, it_user, superuser, plain_user, staff_user
):
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    token = services.confirm_token(link_request)
    response = client.post(reverse("zoom:confirm", args=[token]))
    assert response.status_code == 302
    assert response.url == reverse("zoom:confirmed", args=[token])
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING
    assert link_request.verified_at == FROZEN_NOW
    assert sorted(m.to[0] for m in mail.outbox) == [
        "admin@polymath.example",
        "kasun@polymath.example",
    ]
    assert all(link_request.reference in m.subject for m in mail.outbox)

    confirmed = client.get(response.url)
    assert confirmed.status_code == 200
    assert confirmed.context["link_request"] == link_request


def test_confirm_twice_is_already_and_sends_no_second_it_email(client, it_user):
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    url = _confirm_url(link_request)
    client.post(url)
    mail.outbox.clear()
    for response in (client.get(url), client.post(url)):
        assert response.status_code == 200
        assert response.context["state"] == "already"
    assert mail.outbox == []


def test_expired_and_invalid_tokens(client, monkeypatch):
    from django.core import signing

    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    real_timestamp = signing.TimestampSigner.timestamp
    monkeypatch.setattr(
        signing.TimestampSigner,
        "timestamp",
        lambda self: signing.b62_encode(signing.b62_decode(real_timestamp(self)) - 25 * 3600),
    )
    old_url = _confirm_url(link_request)
    monkeypatch.setattr(signing.TimestampSigner, "timestamp", real_timestamp)

    for method in (client.get, client.post):
        assert method(old_url).context["state"] == "expired"
        bad = method(reverse("zoom:confirm", args=["nonsense:token"]))
        assert (bad.status_code, bad.context["state"]) == (200, "invalid")
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.UNVERIFIED
    assert mail.outbox == []


def test_confirmed_page_404s_for_bad_or_unconfirmed_tokens(client):
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    token = services.confirm_token(link_request)
    assert client.get(reverse("zoom:confirmed", args=[token])).status_code == 404
    assert client.get(reverse("zoom:confirmed", args=["nonsense"])).status_code == 404


# --------------------------------------------------------------------------- access (17, 18)

IT_URLS = ["zoom:queue", "zoom:detail", "zoom:approve", "zoom:reject"]


def _url(name, link_request):
    return reverse(name) if name == "zoom:queue" else reverse(name, args=[link_request.pk])


@pytest.mark.parametrize("name", IT_URLS)
def test_anonymous_visitors_are_sent_to_sign_in(client, name):
    url = _url(name, make_request())
    response = client.post(url) if name in ("zoom:approve", "zoom:reject") else client.get(url)
    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={url}"


@pytest.mark.parametrize("name", IT_URLS)
@pytest.mark.parametrize("who", ["plain_user", "staff_user"])
def test_users_without_the_permission_get_403(client, request, name, who):
    client.force_login(request.getfixturevalue(who))
    url = _url(name, make_request())
    response = client.post(url) if name in ("zoom:approve", "zoom:reject") else client.get(url)
    assert response.status_code == 403


@pytest.mark.parametrize("who", ["it_user", "superuser"])
def test_it_users_and_superusers_can_open_the_it_pages(client, request, who):
    client.force_login(request.getfixturevalue(who))
    link_request = make_request()
    assert client.get(reverse("zoom:queue")).status_code == 200
    assert client.get(reverse("zoom:detail", args=[link_request.pk])).status_code == 200
    assert client.get(reverse("zoom:approve", args=[link_request.pk])).status_code == 405
    assert client.get(reverse("zoom:reject", args=[link_request.pk])).status_code == 405


def test_it_desk_group_holds_exactly_the_review_and_host_account_permissions():
    """Brief 005's criterion 18 said one permission; brief 008 (criterion 1) adds three."""
    group = Group.objects.get(name="IT desk")
    assert sorted(f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()) == [
        "zoom.add_hostaccount",
        "zoom.change_hostaccount",
        "zoom.review_linkrequest",
        "zoom.view_hostaccount",
    ]
    assert group.permissions.get(codename="review_linkrequest").name == (
        "Can approve or reject Zoom link requests"
    )
    assert not Group.objects.filter(name="Zoom account managers").exists()


def test_it_desk_migration_is_idempotent_and_reversible():
    from importlib import import_module

    from django.apps import apps

    migration = import_module("apps.zoom.migrations.0002_it_desk_group")
    migration.create_it_desk_group(apps, None)
    assert Group.objects.filter(name="IT desk").count() == 1
    migration.remove_it_desk_group(apps, None)
    assert not Group.objects.filter(name="IT desk").exists()
    migration.create_it_desk_group(apps, None)
    assert Group.objects.get(name="IT desk").permissions.count() == 1


def test_host_account_permission_migration_is_idempotent_and_reversible():
    from importlib import import_module

    from django.apps import apps

    migration = import_module("apps.zoom.migrations.0004_it_desk_manages_host_accounts")
    group = Group.objects.get(name="IT desk")
    migration.grant_host_account_permissions(apps, None)
    migration.grant_host_account_permissions(apps, None)
    assert group.permissions.count() == 4
    migration.revoke_host_account_permissions(apps, None)
    assert [p.codename for p in group.permissions.all()] == ["review_linkrequest"]
    migration.grant_host_account_permissions(apps, None)
    assert group.permissions.count() == 4


def test_host_account_permission_migration_reverse_creates_nothing():
    """Review round 1, nit 2: undoing the grant only looks permissions up, never makes them."""
    from importlib import import_module

    from django.apps import apps
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    migration = import_module("apps.zoom.migrations.0004_it_desk_manages_host_accounts")
    ContentType.objects.filter(app_label="zoom", model="hostaccount").delete()
    before = (ContentType.objects.count(), Permission.objects.count())
    migration.revoke_host_account_permissions(apps, None)
    assert (ContentType.objects.count(), Permission.objects.count()) == before
    assert [p.codename for p in Group.objects.get(name="IT desk").permissions.all()] == [
        "review_linkrequest"
    ]


def test_unverified_requests_404_on_detail(it_client):
    hidden = make_request(status=LinkRequest.Status.UNVERIFIED)
    assert it_client.get(reverse("zoom:detail", args=[hidden.pk])).status_code == 404
    response = it_client.get(reverse("zoom:queue"), {"status": "all", "q": hidden.reference})
    assert list(response.context["link_requests"]) == []


# --------------------------------------------------------------------------- queue (20-25)


def test_queue_defaults_to_waiting_with_tabs_counts_and_share_link(it_client, account, it_user):
    waiting = make_request()
    book(make_request(first_date=date(2026, 10, 12)), account, it_user)
    make_request(status=LinkRequest.Status.UNVERIFIED)
    for status in (None, "nonsense"):
        response = it_client.get(reverse("zoom:queue"), {"status": status} if status else {})
        context = response.context
        assert context["status"] == "waiting"
        assert context["q"] == ""
        assert list(context["link_requests"]) == [waiting]
        assert context["tabs"] == [
            {"value": "waiting", "label": "Waiting", "count": 1, "current": True},
            {"value": "approved", "label": "Link sent", "count": 1, "current": False},
            {"value": "rejected", "label": "Not approved", "count": 0, "current": False},
            {"value": "all", "label": "All", "count": 2, "current": False},
        ]
        assert context["public_form_url"] == "http://testserver/zoom/request/"
    row = context["link_requests"][0]
    assert row.first_start == datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
    assert row.occurrence_count == 1


def test_queue_search_works_within_the_tab(it_client):
    target = make_request(class_name="Grade 10 Science")
    make_request()
    response = it_client.get(reverse("zoom:queue"), {"status": "waiting", "q": "  science "})
    assert response.context["q"] == "science"
    assert list(response.context["link_requests"]) == [target]
    response = it_client.get(reverse("zoom:queue"), {"status": "approved", "q": "science"})
    assert list(response.context["link_requests"]) == []


def test_queue_pages_at_25(it_client):
    for _ in range(26):
        make_request()
    first = it_client.get(reverse("zoom:queue"))
    assert first.context["is_paginated"]
    assert len(first.context["link_requests"]) == 25
    second = it_client.get(reverse("zoom:queue"), {"page": 2, "status": "waiting"})
    assert len(second.context["link_requests"]) == 1


def test_queue_query_count_does_not_grow_with_rows(it_client, account, it_user):
    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            assert it_client.get(reverse("zoom:queue")).status_code == 200
        return len(queries)

    for _ in range(3):
        make_request(weekdays="1,3", last_date=date(2026, 10, 28))
    few = count_queries()
    for _ in range(22):
        make_request()
    assert count_queries() == few


# --------------------------------------------------------------------------- detail (26-32)


def test_detail_shows_free_and_busy_accounts_with_busy_count_per_class(it_client, account, it_user):
    busy = make_account("Zoom 02", sort_order=2)
    no_key = make_account("Zoom 03", sort_order=3)
    make_account("Free plan", is_paid=False)
    # Two bookings on Zoom 02 that both clash with the same one class (D22, G4).
    first = book(
        make_request(start=time(8, 30), end=time(9, 30), class_name="Early"), busy, it_user
    )
    book(make_request(start=time(10, 0), end=time(11, 0), class_name="Late"), busy, it_user)
    link_request = make_request()

    context = it_client.get(reverse("zoom:detail", args=[link_request.pk])).context
    availability = context["availability"]
    assert [entry["account"] for entry in availability] == [account, busy, no_key]
    assert [entry["is_free"] for entry in availability] == [True, False, True]
    assert [entry["has_host_key"] for entry in availability] == [True, False, False]
    assert availability[1]["busy_count"] == 1
    assert len(availability[1]["clashes"]) == 2
    assert availability[1]["clashes"][0]["other"].link_request == first
    assert context["free_count"] == 2
    assert context["can_decide"] and not context["has_started"]
    assert context["occurrence_count"] == 1
    assert context["needs_manual_details"] is False
    assert context["approve_error"] is None

    form = context["approve_form"]
    assert [choice[0].value for choice in form.fields["host_account"].widget.choices] == [
        account.pk,
        no_key.pk,
    ]
    assert form["host_account"].value() == account.pk
    assert "join_url" not in form.fields
    assert context["reject_form"] is not None
    assert HOST_KEY not in str(form) and HOST_KEY not in str(context["reject_form"])


def test_detail_with_manual_provider_asks_for_the_meeting_details(it_client, account, settings):
    settings.ZOOM_PROVIDER = "manual"
    context = it_client.get(reverse("zoom:detail", args=[make_request().pk])).context
    assert context["needs_manual_details"] is True
    assert {"join_url", "meeting_id", "passcode"} <= set(context["approve_form"].fields)


def test_detail_without_free_account_or_after_start_has_no_approve_form(
    it_client, account, it_user
):
    book(make_request(class_name="Holder"), account, it_user)
    clash = make_request()
    context = it_client.get(reverse("zoom:detail", args=[clash.pk])).context
    assert (context["free_count"], context["approve_form"]) == (0, None)
    assert context["reject_form"] is not None

    started = make_request(first_date=date(2026, 9, 28), start=time(9, 0), end=time(9, 30))
    context = it_client.get(reverse("zoom:detail", args=[started.pk])).context
    assert context["has_started"] and context["approve_form"] is None
    assert context["reject_form"] is not None


def test_decided_request_has_no_forms_or_availability(it_client, account, it_user):
    link_request = book(make_request(), account, it_user)
    context = it_client.get(reverse("zoom:detail", args=[link_request.pk])).context
    assert not context["can_decide"]
    assert context["approve_form"] is None and context["reject_form"] is None
    assert context["availability"] == [] and context["overlapping_waiting"] == []
    assert context["link_request"].decided_by == it_user


def test_detail_lists_overlapping_waiting_and_earlier_requests(it_client):
    earlier = make_request(first_date=date(2026, 11, 2))
    other = make_request(email="someone@example.com", start=time(9, 0), end=time(10, 0))
    link_request = make_request()
    context = it_client.get(reverse("zoom:detail", args=[link_request.pk])).context
    assert context["overlapping_waiting"] == [other]
    assert context["overlapping_waiting"][0].first_overlap == datetime(
        2026, 10, 5, 3, 30, tzinfo=UTC
    )
    assert context["earlier_requests"] == [earlier]


# --------------------------------------------------------------------------- approve (35-41)


def test_approve_view_books_emails_and_redirects(it_client, account):
    link_request = make_request(weekdays="1,3", last_date=date(2026, 10, 28))
    response = it_client.post(
        reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk}
    )
    assert response.status_code == 302
    assert response.url == reverse("zoom:detail", args=[link_request.pk])
    assert _messages(response) == ["Approved. The link was emailed to nimali@example.com."]
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED
    assert HostSlot.objects.count() == 288
    [message] = mail.outbox
    assert message.to == ["nimali@example.com"]
    assert HOST_KEY in message.body


def test_approve_view_runs_outside_the_request_transaction():
    view = resolve(reverse("zoom:approve", args=[1])).func
    assert "default" in getattr(view, "_non_atomic_requests", set())


def test_manual_approve_stores_typed_details_and_rejects_bad_ones(it_client, account, settings):
    settings.ZOOM_PROVIDER = "manual"
    link_request = make_request()
    url = reverse("zoom:approve", args=[link_request.pk])
    bad = it_client.post(
        url,
        {
            "host_account": account.pk,
            "join_url": "https://evil.example/zoom.us/j/1",
            "meeting_id": "12",
            "passcode": "x" * 11,
        },
    )
    assert bad.status_code == 200
    errors = bad.context["approve_form"].errors
    assert set(errors) == {"join_url", "meeting_id", "passcode"}
    assert bad.context["approve_form"]["join_url"].value() == "https://evil.example/zoom.us/j/1"
    assert HostSlot.objects.count() == 0 and mail.outbox == []

    good = it_client.post(
        url,
        {
            "host_account": account.pk,
            "join_url": "https://us02web.zoom.us/j/12345678901",
            "meeting_id": "123 4567 8901",
            "passcode": "k3Y",
        },
    )
    assert good.status_code == 302
    link_request.refresh_from_db()
    assert (link_request.join_url, link_request.meeting_id, link_request.passcode) == (
        "https://us02web.zoom.us/j/12345678901",
        "12345678901",
        "k3Y",
    )


def test_stale_page_gets_409_and_refreshed_availability(it_client, account, it_user):
    link_request = make_request()
    book(make_request(start=time(9, 0), end=time(10, 0), class_name="Sneaky"), account, it_user)
    mail.outbox.clear()
    FakeProvider.calls.clear()
    response = it_client.post(
        reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk}
    )
    assert response.status_code == 409
    assert response.context["approve_error"] == (
        "Zoom 01 was booked for an overlapping class a moment ago. Choose another free account."
    )
    assert response.context["availability"][0]["is_free"] is False
    assert FakeProvider.calls == [] and mail.outbox == []


@pytest.mark.parametrize("choice", ["unpaid", "inactive", "unknown"])
def test_unbookable_choice_is_a_form_error_with_409(it_client, account, choice):
    target = {
        "unpaid": lambda: make_account("Free", is_paid=False).pk,
        "inactive": lambda: make_account("Old", is_active=False).pk,
        "unknown": lambda: 999999,
    }[choice]()
    response = it_client.post(
        reverse("zoom:approve", args=[make_request().pk]), {"host_account": target}
    )
    assert response.status_code == 409
    assert response.context["approve_form"].errors["host_account"] == [
        "Choose one of the free accounts listed."
    ]


def test_deciding_twice_says_already_decided(it_client, account, it_user):
    link_request = book(make_request(), account, it_user)
    for name, data in (
        ("zoom:approve", {"host_account": account.pk}),
        ("zoom:reject", {"reason": "x"}),
    ):
        response = it_client.post(reverse(name, args=[link_request.pk]), data)
        assert response.status_code == 302
        # Not following the redirect leaves earlier messages queued; the newest is ours.
        assert _messages(response)[-1] == "This request has already been decided."


def test_approving_a_started_request_rerenders_with_the_started_state(it_client, account):
    started = make_request(first_date=date(2026, 9, 28), start=time(9, 0), end=time(9, 30))
    response = it_client.post(
        reverse("zoom:approve", args=[started.pk]), {"host_account": account.pk}
    )
    assert response.status_code == 200
    assert response.context["has_started"] and response.context["approve_form"] is None
    started.refresh_from_db()
    assert started.status == LinkRequest.Status.WAITING


def test_provider_error_rerenders_with_the_message(it_client, account):
    FakeProvider.next_error = "Zoom is not responding"
    link_request = make_request()
    response = it_client.post(
        reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk}
    )
    assert response.status_code == 200
    # Brief 006, criterion 30 (D25), amends 005's criterion 40 on purpose.
    assert response.context["approve_error"] == (
        "We couldn't make the meeting in Zoom: Zoom is not responding. Nothing was booked. "
        "Try again in a few minutes."
    )
    assert mail.outbox == []


def test_email_failure_keeps_the_approval_and_warns(it_client, account, caplog):
    link_request = make_request()
    with (
        mock.patch(
            "django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError
        ),
        caplog.at_level(logging.ERROR),
    ):
        response = it_client.post(
            reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk}
        )
    assert response.status_code == 302
    assert _messages(response) == [
        "Approved, but the email to nimali@example.com didn't send. Copy the link below and send "
        "it to them yourself. The host key is in the Zoom account's profile in Zoom."
    ]
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED
    [record] = caplog.records
    assert link_request.reference in record.getMessage() and "OSError" in record.getMessage()
    for secret in (HOST_KEY, link_request.join_url, link_request.passcode):
        assert secret not in record.getMessage()


def test_unreadable_host_key_rerenders_with_the_message(it_client, account, settings):
    from cryptography.fernet import Fernet

    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    response = it_client.post(
        reverse("zoom:approve", args=[make_request().pk]), {"host_account": account.pk}
    )
    assert response.status_code == 200
    assert response.context["approve_error"].startswith(
        "The host key saved for Zoom 01 can't be read."
    )


# --------------------------------------------------------------------------- reject (42-43)


def test_reject_view_stores_reason_emails_and_redirects(it_client, it_user):
    link_request = make_request()
    response = it_client.post(
        reverse("zoom:reject", args=[link_request.pk]),
        {"reason": "Please use the Grade 10 batch link instead."},
    )
    assert response.status_code == 302
    assert _messages(response) == ["Not approved. We emailed the reason to nimali@example.com."]
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.REJECTED
    assert link_request.rejection_reason == "Please use the Grade 10 batch link instead."
    assert (link_request.decided_by, link_request.decided_at) == (it_user, FROZEN_NOW)
    [message] = mail.outbox
    assert message.subject == f"Your Zoom link request {link_request.reference} was not approved"


def test_blank_reason_rerenders_and_keeps_the_approve_values(it_client, account, settings):
    settings.ZOOM_PROVIDER = "manual"
    link_request = make_request()
    response = it_client.post(
        reverse("zoom:reject", args=[link_request.pk]),
        {"reason": "   ", "join_url": "https://us02web.zoom.us/j/1"},
    )
    assert response.status_code == 200
    assert response.context["reject_form"].errors["reason"] == [
        "Tell the requester why, so they can fix it and ask again."
    ]
    assert response.context["approve_form"]["join_url"].value() == "https://us02web.zoom.us/j/1"
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING


# --------------------------------------------------------------------------- never logged (65)


def test_full_flow_never_logs_the_host_key_or_encryption_keys(
    client, it_user, superuser, settings, caplog
):
    """Brief 005 criterion 65, re-proved in the app by brief 008 (criterion 24).

    Submit, confirm, approve and reject; add an account with a key; an invalid re-render with
    a typed key; change the key; remove a key; rotate. No log record and no flash message
    holds a host key or an encryption key.
    """
    make_account("Zoom 01", host_key=HOST_KEY)
    secrets = [HOST_KEY, *settings.HOST_KEY_ENCRYPTION_KEYS]
    added_key, typed_key, new_key = "1122334", "5566778", "7654321"
    flashes = []
    with (
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
        caplog.at_level(logging.DEBUG, logger="django"),
    ):
        client.post(reverse("zoom:request"), _form_data())
        client.post(
            reverse("zoom:request"),
            _form_data(class_name="Second", requester_email="b@example.com"),
        )
        first, second = LinkRequest.objects.order_by("pk")
        for link_request in (first, second):
            client.post(_confirm_url(link_request))
        client.force_login(it_user)
        zoom01 = HostAccount.objects.get(label="Zoom 01")
        client.post(reverse("zoom:approve", args=[first.pk]), {"host_account": zoom01.pk})
        client.post(reverse("zoom:reject", args=[second.pk]), {"reason": "Use Grade 10."})
        client.force_login(superuser)

        def account_data(**overrides):
            data = {"label": "Zoom 01", "email": zoom01.email, "is_paid": "on"}
            data.update(is_active="on", sort_order=0, notes="", host_key="")
            data.update(overrides)
            return data

        zoom02 = {"label": "Zoom 02", "email": "zoom02@polymath.example"}
        edit_url = reverse("zoom:account_edit", args=[zoom01.pk])
        added = client.post(reverse("zoom:account_add"), account_data(**zoom02, host_key=added_key))
        flashes += _messages(added)
        invalid = client.post(edit_url, account_data(label="", host_key=typed_key))
        assert invalid.status_code == 200
        assert typed_key not in invalid.content.decode()
        changed = client.post(edit_url, account_data(host_key=new_key))
        flashes += _messages(changed)
        removed = client.post(
            reverse("zoom:account_edit", args=[HostAccount.objects.get(label="Zoom 02").pk]),
            account_data(**zoom02, remove_host_key="on"),
        )
        flashes += _messages(removed)
        from django.core.management import call_command

        call_command("rotate_host_keys", stdout=mock.MagicMock())
    assert HostAccount.objects.get(label="Zoom 01").get_host_key() == new_key
    assert not HostAccount.objects.get(label="Zoom 02").has_host_key
    # Unread messages pile up in storage, so each response lists every one stored so far.
    assert {
        "Added Zoom 02.",
        "Saved Zoom 01. The new host key goes out with the next approved link.",
        "Saved Zoom 02. Its host key was removed.",
    } <= set(flashes)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for secret in [*secrets, added_key, typed_key, new_key]:
        assert secret not in logged
        assert not any(secret in flash for flash in flashes)
