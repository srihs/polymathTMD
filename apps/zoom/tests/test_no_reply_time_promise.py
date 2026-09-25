"""Criterion 67 (D23): none of the public pages or the confirm email may promise *when* IT
will reply, while the confirm link's own lifetime is allowed and required to be stated.

``apps/zoom/tests/conftest.py`` swaps the real ``zoom/*.html`` templates for tiny locmem
stubs so the view-layer tests in ``test_views.py`` don't depend on markup. This module needs
the *real* templates, so each test restores the project's normal template engine first.
"""

import re

import pytest
from django.conf import settings as django_settings
from django.core import mail
from django.test import RequestFactory
from django.urls import reverse

from apps.zoom import services

from .conftest import make_request

pytestmark = pytest.mark.django_db

# The literal banned patterns from criterion 67, checked only against sentences that talk
# about IT (a bare, context-free match would also flag unrelated copy, like the request
# form's "Ends at: on the same day as it starts" help text -- that's a schedule fact, not a
# promise about when IT will reply. The main-session ruling on this criterion narrows the ban
# to promises about IT's reply time specifically).
_BANNED_PATTERNS = [
    r"working day",
    r"business day",
    r"within a day",
    r"within one",
    r"within \d+ (hour|day)s?",
    r"by tomorrow",
    r"by the end of",
    r"as soon as",
    r"same day",
]
_BANNED_RE = re.compile("|".join(_BANNED_PATTERNS), re.IGNORECASE)


def _real_templates(settings):
    """Point the template engine back at ``templates/`` for one test (undoes the autouse stub)."""
    engine = dict(django_settings.TEMPLATES[0])
    engine["APP_DIRS"] = True
    engine["OPTIONS"] = {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "apps.core.context_processors.site",
        ]
    }
    settings.TEMPLATES = [engine]


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _reply_time_promise_sentences(text: str) -> list[str]:
    """Sentences that both mention the IT desk and match a banned reply-time pattern.

    "IT" is matched case-sensitively: it names the IT desk in this app's copy, and a
    case-insensitive match would also catch the ordinary pronoun "it" (e.g. "on the same
    day as it starts"), which has nothing to do with a reply-time promise.
    """
    hits = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if re.search(r"\bIT\b", sentence) and _BANNED_RE.search(sentence):
            hits.append(sentence.strip())
    return hits


def test_request_form_makes_no_reply_time_promise(client, settings):
    _real_templates(settings)
    response = client.get(reverse("zoom:request"))
    assert response.status_code == 200
    text = _text(response.content.decode())
    assert _reply_time_promise_sentences(text) == []


def test_request_sent_states_the_link_lifetime_not_a_reply_time(client, settings):
    _real_templates(settings)
    submit = client.post(
        reverse("zoom:request"),
        {
            "class_name": "CCC Batch 3 - Mathematics",
            "first_date": "2026-10-05",
            "start_time": "08:30",
            "end_time": "11:30",
            "repeat": "once",
            "requester_name": "Nimali Perera",
            "requester_email": "nimali@example.com",
            "requester_phone": "077 123 4567",
            "notes": "",
            "website": "",
        },
    )
    assert submit.status_code == 302
    response = client.get(reverse("zoom:request_sent"))
    assert response.status_code == 200
    text = _text(response.content.decode())
    assert "The link works for one day." in text
    assert _reply_time_promise_sentences(text) == []


def test_confirm_ready_page_makes_no_reply_time_promise(client, settings, account):
    _real_templates(settings)
    link_request = make_request(status="unverified")
    token = services.confirm_token(link_request)
    response = client.get(reverse("zoom:confirm", args=[token]))
    assert response.status_code == 200
    text = _text(response.content.decode())
    assert _reply_time_promise_sentences(text) == []


def test_confirmed_page_makes_no_reply_time_promise(client, settings):
    _real_templates(settings)
    link_request = make_request(status="unverified")
    token = services.confirm_token(link_request)
    client.post(reverse("zoom:confirm", args=[token]))
    response = client.get(reverse("zoom:confirmed", args=[token]))
    assert response.status_code == 200
    text = _text(response.content.decode())
    assert _reply_time_promise_sentences(text) == []


def test_confirm_email_states_the_link_lifetime_in_hours_and_makes_no_reply_promise(settings):
    _real_templates(settings)
    link_request = make_request(status="unverified")
    services.send_confirm_email(RequestFactory().get("/"), link_request)
    body = mail.outbox[-1].body
    assert "The link works for 24 hours" in body
    assert _reply_time_promise_sentences(body) == []
