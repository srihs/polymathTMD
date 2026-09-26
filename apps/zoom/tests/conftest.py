"""Shared fixtures for the zoom app's tests (brief 005).

- Time is frozen at the brief's "now", Mon 28 Sep 2026 10:00 Colombo, by patching
  ``django.utils.timezone.now`` (no ``time-machine`` dependency). Every date in these tests is
  relative to it.
- The page templates (``zoom/*.html``) are owned by ``tmd-frontend`` and are replaced here by
  tiny stubs, so these tests pin the view layer (status codes, redirects, context) whatever the
  markup looks like. The rendered pages are the verifier's to test. The plain-text email
  templates are the real ones.
- Brief 006: the in-process Zoom token cache and Django's cache (which holds the preview's
  Zoom answers) are emptied around every test (criterion 45), so no test sees another's
  token or busy times. The project conftest blocks real HTTP; ``zoommock.py`` has the helpers
  for registering Zoom's answers.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone

from apps.zoom import services, zoom_api
from apps.zoom.models import HostAccount, LinkRequest
from apps.zoom.providers import FakeProvider

COLOMBO = ZoneInfo("Asia/Colombo")
FROZEN_NOW = datetime(2026, 9, 28, 10, 0, tzinfo=COLOMBO)

STUB_TEMPLATES = {
    "zoom/request_form.html": "request form {{ form.errors }}{{ form.non_field_errors }}",
    "zoom/request_sent.html": "sent to {{ sent_to }}",
    "zoom/confirm.html": "state={{ state }} {{ link_request.class_name }}",
    "zoom/confirmed.html": "confirmed {{ link_request.reference }}",
    "zoom/queue.html": "queue {% for r in link_requests %}{{ r.reference }} {% endfor %}",
    "zoom/detail.html": "detail {{ link_request.reference }} {{ approve_error }}",
    # The accounts stubs render the host-key input through its widget and print its bound
    # value, so "a typed key is never echoed" is tested against real output (brief 008).
    "zoom/accounts.html": "accounts {% for a in accounts %}{{ a.label }} {% endfor %}",
    "zoom/account_form.html": (
        "account form {{ saved_label }} {{ form.host_key }} [{{ form.host_key.value|default:'' }}]"
        " {{ form.errors }}"
    ),
    # The timetable stubs follow every relation the contract allows an entry to use, so the
    # query-count tests would catch a missing select_related (brief 009, criterion 18).
    "zoom/timetable.html": (
        "timetable {{ month.label }} {% for week in weeks %}{% for box in week %}{% if box %}"
        "{% for e in box.entries %}[{{ e.link_request.reference }} {{ e.link_request.class_name }}"
        " {{ e.link_request.get_status_display }} {{ e.host_account.label }}]{% endfor %}"
        "{% endif %}{% endfor %}{% endfor %}"
    ),
    "zoom/timetable_day.html": (
        "timetable day {{ day_label }} {% for e in entries %}[{{ e.link_request.reference }}"
        " {{ e.link_request.class_name }} {{ e.link_request.get_status_display }}"
        " {{ e.host_account.label }}]{% endfor %}"
    ),
}


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: FROZEN_NOW.astimezone(ZoneInfo("UTC")))
    return FROZEN_NOW


@pytest.fixture(autouse=True)
def fresh_zoom_caches():
    zoom_api.reset_token_cache()
    cache.clear()
    yield
    zoom_api.reset_token_cache()
    cache.clear()


@pytest.fixture(autouse=True)
def fake_provider():
    FakeProvider.reset()
    yield FakeProvider
    FakeProvider.reset()


@pytest.fixture(autouse=True)
def stub_page_templates(settings):
    engine = dict(django_settings.TEMPLATES[0])
    options = dict(engine["OPTIONS"])
    options["loaders"] = [
        ("django.template.loaders.locmem.Loader", STUB_TEMPLATES),
        "django.template.loaders.filesystem.Loader",
        "django.template.loaders.app_directories.Loader",
    ]
    engine["OPTIONS"] = options
    engine["APP_DIRS"] = False
    settings.TEMPLATES = [engine]


# --------------------------------------------------------------------------- factories


def make_account(label="Zoom 01", *, sort_order=0, host_key="", is_paid=True, is_active=True):
    account = HostAccount(
        label=label,
        email=f"{label.lower().replace(' ', '')}@polymath.example",
        sort_order=sort_order,
        is_paid=is_paid,
        is_active=is_active,
    )
    account.set_host_key(host_key)
    account.save()
    return account


def make_request(
    *,
    status=LinkRequest.Status.WAITING,
    first_date=date(2026, 10, 5),
    start=time(8, 30),
    end=time(11, 30),
    weekdays="",
    last_date=None,
    email="nimali@example.com",
    **fields,
):
    values = {
        "class_name": "CCC Batch 3 - Mathematics",
        "requester_name": "Nimali Perera",
        "requester_phone": "+94771234567",
        "submitted_ip": "127.0.0.1",
    }
    values.update(fields)
    link_request = LinkRequest.objects.create(
        status=status,
        first_date=first_date,
        start_time=start,
        end_time=end,
        repeat=LinkRequest.Repeat.WEEKLY if weekdays else LinkRequest.Repeat.ONCE,
        weekdays=weekdays,
        last_date=last_date,
        requester_email=email,
        **values,
    )
    link_request.create_occurrences()
    return link_request


def book(link_request, account, by=None):
    """Approve ``link_request`` on ``account`` through the real service (fake provider)."""
    result = services.approve(link_request.pk, account_id=account.pk, by=by)
    assert result.outcome == services.Outcome.APPROVED, result.message
    link_request.refresh_from_db()
    return link_request


@pytest.fixture
def account(db):
    return make_account("Zoom 01", sort_order=1, host_key="8421973")


@pytest.fixture
def it_user(db):
    user = get_user_model().objects.create_user(
        username="kasun.it", password="pw", email="kasun@polymath.example"
    )
    user.groups.add(Group.objects.get(name="IT desk"))
    return user


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin", password="pw", email="admin@polymath.example"
    )


@pytest.fixture
def plain_user(db):
    return get_user_model().objects.create_user(
        username="teacher", password="pw", email="teacher@polymath.example"
    )


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username="staffer", password="pw", email="staff@polymath.example", is_staff=True
    )


@pytest.fixture
def it_client(client, it_user):
    client.force_login(it_user)
    return client
