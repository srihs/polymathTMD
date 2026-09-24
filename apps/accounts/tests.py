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


# --- User.initials for the avatar (brief 004, criterion 33) --------------------------


@pytest.mark.parametrize(
    ("first_name", "last_name", "username", "expected"),
    [
        ("Nimali", "Perera", "nimali.p", "NP"),
        ("nimali", "perera", "nimali.p", "NP"),
        ("Nimali", "", "nimali.p", "N"),
        ("", "Perera", "nimali.p", "P"),
        ("", "", "nimali.p", "N"),
        ("   ", "  ", "kasun", "K"),
    ],
)
def test_initials_follow_name_then_username_rule(first_name, last_name, username, expected):
    """Unsaved instances are enough: the property reads fields only, no query."""
    user = get_user_model()(first_name=first_name, last_name=last_name, username=username)
    assert user.initials == expected


def test_initials_never_empty_for_saved_user(user):
    """The fixture user has no first or last name, so this exercises the username fallback."""
    user.refresh_from_db()
    assert user.initials == "N"


# --- Owner correction: sign-in matches the concept exactly (brief 004) --------------
# "login page design is different than the concept" -> "Match the concept exactly".
# These pin the correction so the old app-authored copy/controls can't silently return.


@pytest.mark.django_db
def test_login_username_help_matches_the_concept_copy(client):
    content = client.get(reverse("accounts:login")).content.decode()
    help_text = re.search(r'<p class="field__help" id="username-help">([^<]*)</p>', content)
    assert help_text, "username-help paragraph missing"
    assert help_text.group(1) == "The name the school gave you, like nimali.p"


@pytest.mark.django_db
def test_login_password_help_matches_the_concept_copy(client):
    content = client.get(reverse("accounts:login")).content.decode()
    help_text = re.search(r'<p class="field__help" id="password-help">([^<]*)</p>', content)
    assert help_text, "password-help paragraph missing"
    assert help_text.group(1) == "Passwords are case sensitive."
    assert "Check that Caps Lock is off" not in content


@pytest.mark.django_db
def test_login_page_has_no_password_show_hide_control(client):
    """The concept has no Show/Hide button; the toggle-password hook must be gone."""
    content = client.get(reverse("accounts:login")).content.decode()
    assert "data-toggle-password" not in content
    assert re.search(r">\s*Show\s*<", content) is None
    assert re.search(r">\s*Hide\s*<", content) is None


@pytest.mark.django_db
def test_login_page_has_no_forgot_password_help_line(client):
    content = client.get(reverse("accounts:login")).content.decode()
    assert "Forgot your password" not in content
    assert "signin__help" not in content


@pytest.mark.django_db
def test_login_password_field_is_not_wrapped_in_a_toggle_row(client):
    """The password input sits directly in .field, full width, with no button beside it."""
    content = client.get(reverse("accounts:login")).content.decode()
    assert "field__row" not in content
    password_start = content.index('id="password"')
    end_of_field_div = content.index("</div>", password_start)
    field_tail = content[password_start:end_of_field_div]
    assert "<button" not in field_tail


@pytest.mark.django_db
def test_login_autofocus_on_username_before_any_attempt(client):
    """Kept from brief 001 across the concept-match restructure (D8's autofocus rule)."""
    content = client.get(reverse("accounts:login")).content.decode()
    assert "autofocus" in _input_tag(content, "username")
    assert "autofocus" not in _input_tag(content, "password")


def test_login_autofocus_moves_to_password_after_wrong_password(client, user):
    response = client.post(reverse("accounts:login"), {"username": "nimali.p", "password": "no"})
    content = response.content.decode()
    assert "autofocus" not in _input_tag(content, "username")
    assert "autofocus" in _input_tag(content, "password")
