"""Tests for sign-in and sign-out, including the login page's title and error wiring."""

import re

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import escape


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="nimali.p", password="s3cret-pass")


def test_custom_user_model_is_active():
    assert get_user_model()._meta.label == "accounts.User"


@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    assert b'name="csrfmiddlewaretoken"' in response.content


def test_login_with_valid_details_goes_home(client, user):
    response = client.post(
        reverse("accounts:login"), {"username": "nimali.p", "password": "s3cret-pass"}
    )
    assert response.status_code == 302
    assert response.url == reverse("core:home")


def test_login_with_wrong_password_shows_error(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    assert response.status_code == 200
    assert b"We couldn&rsquo;t sign you in" in response.content


def test_logout_requires_post(client, user):
    client.force_login(user)
    assert client.get(reverse("accounts:logout")).status_code == 405
    response = client.post(reverse("accounts:logout"))
    assert response.url == reverse("accounts:login")


def _login_error_tag(content):
    """Return the opening tag of the login error alert, which is always in the HTML."""
    match = re.search(rb'<div[^>]*id="login-error"[^>]*>', content)
    assert match, "login error alert missing from the page"
    return match.group(0)


@pytest.mark.django_db
def test_login_error_is_hidden_before_any_attempt(client):
    """The alert markup is always rendered, so the error text alone proves nothing."""
    response = client.get(reverse("accounts:login"))
    assert b" hidden" in _login_error_tag(response.content)


def test_login_error_is_shown_after_wrong_password(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    assert b" hidden" not in _login_error_tag(response.content)


def test_login_with_wrong_password_keeps_typed_username(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    username_input = re.search(rb'<input[^>]*name="username"[^>]*>', response.content).group(0)
    assert b'value="nimali.p"' in username_input


# --- Page title (brief 001, issue 1) -------------------------------------------------


def _title(content):
    """Return the text of the page's <title>, so failures show what was rendered."""
    match = re.search(r"<title>(.*?)</title>", content, re.S)
    assert match, "no <title> in the page"
    return match.group(1)


@pytest.mark.django_db
def test_login_title_uses_site_name_not_request_host(client):
    """LoginView puts the request host into ``site_name``; the title must ignore it."""
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    title = _title(response.content.decode())
    assert title == f"Sign in · {escape(settings.SITE_NAME)}"
    assert "testserver" not in title


def test_login_title_unchanged_after_wrong_password(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    assert response.status_code == 200
    assert _title(response.content.decode()) == f"Sign in · {escape(settings.SITE_NAME)}"


# --- Error wiring for screen readers (brief 001, issue 2) ---------------------------


def _input_tag(content, input_id):
    match = re.search(rf'<input[^>]*\bid="{input_id}"[^>]*>', content)
    assert match, f"no input with id={input_id!r}"
    return match.group(0)


def _described_by(tag):
    """The ``aria-describedby`` tokens of a tag, in order ([] when the attribute is absent)."""
    match = re.search(r'\baria-describedby="([^"]*)"', tag)
    return match.group(1).split() if match else []


@pytest.mark.django_db
def test_login_inputs_describe_only_help_before_any_attempt(client):
    """A hidden alert must never be referenced, so ``login-error`` is absent here."""
    content = client.get(reverse("accounts:login")).content.decode()
    for input_id in ("username", "password"):
        tag = _input_tag(content, input_id)
        assert _described_by(tag) == [f"{input_id}-help"]
        assert "aria-invalid" not in tag


def test_login_inputs_point_at_error_after_wrong_password(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    content = response.content.decode()
    for input_id in ("username", "password"):
        tag = _input_tag(content, input_id)
        assert 'aria-invalid="true"' in tag
        tokens = _described_by(tag)
        assert "login-error" in tokens
        assert f"{input_id}-help" in tokens


def test_login_inputs_list_error_before_help_text(client, user):
    """Design section 2 fixes the token order (error first) so it's read before the general hint."""
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    content = response.content.decode()
    for input_id in ("username", "password"):
        tag = _input_tag(content, input_id)
        assert _described_by(tag) == ["login-error", f"{input_id}-help"]


def test_login_error_alert_and_described_ids_exist_after_wrong_password(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    content = response.content.decode()
    alert = _login_error_tag(response.content)
    assert b'role="alert"' in alert
    assert b" hidden" not in alert
    for input_id in ("username", "password"):
        for ref in _described_by(_input_tag(content, input_id)):
            assert f'id="{ref}"' in content, f"{input_id} describes missing id {ref!r}"
