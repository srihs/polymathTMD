"""The Django admin is gone (criteria 19 and 22), and refusals get the friendly 403 page
(criterion 28, D11), plus the scans that keep the shared form partials in one place
(criteria 29 and 30).

The 403 page has no URL or view of its own: Django's default ``handler403`` renders
``templates/403.html`` for any ``PermissionDenied``. So these tests go through real views where
they can (an IT user opening Staff and access, a plain user opening Zoom accounts) and call
``django.views.defaults.permission_denied`` directly for the cases no current view can reach.
"""

import re
from html.parser import HTMLParser
from io import StringIO

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import RequestFactory
from django.urls import NoReverseMatch, reverse
from django.views.defaults import permission_denied

from .conftest import make_user

BASE_DIR = settings.BASE_DIR
TEMPLATES_DIR = BASE_DIR / "templates"

DENIED_H1 = "You can't open this page"
DENIED_BODY = (
    "Your roles don't include this page. Ask someone who manages Staff and access to give you "
    "the role you need."
)


# --------------------------------------------------------------------------- criterion 19


def test_admin_is_not_installed_but_auth_and_friends_are():
    assert "django.contrib.admin" not in settings.INSTALLED_APPS
    for app in (
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
    ):
        assert app in settings.INSTALLED_APPS


@pytest.mark.django_db
def test_admin_url_is_gone(client):
    assert client.get("/admin/").status_code == 404
    with pytest.raises(NoReverseMatch):
        reverse("admin:index")


def test_no_admin_module_or_import_remains():
    assert not (BASE_DIR / "apps" / "accounts" / "admin.py").exists()
    offenders = [
        str(path.relative_to(BASE_DIR))
        for folder in ("apps", "config")
        for path in (BASE_DIR / folder).rglob("*.py")
        if re.search(
            r"^\s*(from\s+django\.contrib\s+import\s+admin\b|from\s+django\.contrib\.admin\b"
            r"|import\s+django\.contrib\.admin\b)",
            path.read_text(encoding="utf-8"),
            re.M,
        )
    ]
    assert not offenders, offenders
    assert "admin.site" not in (BASE_DIR / "config" / "urls.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- criterion 22


@pytest.mark.django_db
def test_createsuperuser_still_makes_the_first_account(monkeypatch):
    from django.contrib.auth import get_user_model

    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Tr0ub4dor-3xyz-Q")
    call_command(
        "createsuperuser",
        "--noinput",
        "--username=first.head",
        "--email=first@polymath.example",
        stdout=StringIO(),
    )
    user = get_user_model().objects.get(username="first.head")
    assert user.is_superuser and user.is_active
    assert user.check_password("Tr0ub4dor-3xyz-Q")


# --------------------------------------------------------------------------- criterion 28


def _assert_friendly_shell_403(response):
    assert response.status_code == 403
    content = response.content.decode()
    assert "<h1" in content and DENIED_H1 in content
    assert DENIED_BODY in content
    assert re.search(
        rf'<a[^>]*href="{re.escape(reverse("core:home"))}"[^>]*>\s*Go to Home', content
    )
    assert '<nav class="sidenav__menu"' in content
    assert f"<title>{DENIED_H1} · " in content


@pytest.mark.django_db
def test_it_user_opening_staff_and_access_gets_the_friendly_403_in_the_shell(client):
    client.force_login(make_user("kasun.it", groups=["IT desk"]))
    _assert_friendly_shell_403(client.get(reverse("accounts:staff")))


@pytest.mark.django_db
def test_plain_user_opening_zoom_accounts_gets_the_friendly_403_in_the_shell(client):
    client.force_login(make_user("teacher"))
    _assert_friendly_shell_403(client.get(reverse("zoom:accounts")))


def _request(user, path="/accounts/staff/"):
    request = RequestFactory().get(path)
    SessionMiddleware(lambda r: None).process_request(request)
    request.user = user
    return request


@pytest.mark.django_db
def test_an_anonymous_refusal_uses_the_public_frame_with_a_sign_in_link():
    response = permission_denied(_request(AnonymousUser()), PermissionDenied())
    assert response.status_code == 403
    content = response.content.decode()
    assert DENIED_H1 in content
    assert "Sign in to see this page." in content
    assert f'href="{reverse("accounts:login")}?next=/accounts/staff/"' in content
    assert not re.search(r"\bdata-nav[\s>]", content), "no sidebar in the public frame"


@pytest.mark.django_db
def test_the_403_page_never_shows_the_exception_text():
    user = make_user("kasun.it", groups=["IT desk"])
    response = permission_denied(_request(user), PermissionDenied("accounts.change_user"))
    assert response.status_code == 403
    content = response.content.decode()
    assert "accounts.change_user" not in content
    assert "change_user" not in content
    anonymous = permission_denied(
        _request(AnonymousUser()), PermissionDenied("accounts.change_user")
    )
    assert "change_user" not in anonymous.content.decode()


# --------------------------------------------------------------------------- criteria 29–30

MOVED_PARTIALS = (
    "error_summary.html",
    "field.html",
    "field_error.html",
    "choice_group_head.html",
    # Moved too by the frontend (Implementation notes, 2b); review round 1, nit 7.
    "check_field.html",
)


def test_shared_form_partials_live_in_partials_and_nothing_uses_the_old_paths():
    for name in MOVED_PARTIALS:
        assert (TEMPLATES_DIR / "partials" / name).exists(), name
        assert not (TEMPLATES_DIR / "zoom" / "partials" / name).exists(), name
    for template in TEMPLATES_DIR.rglob("*.html"):
        text = template.read_text(encoding="utf-8")
        for name in MOVED_PARTIALS:
            assert f"zoom/partials/{name}" not in text, (str(template), name)


def test_accounts_registration_and_403_templates_never_reference_zoom():
    templates = [
        *(TEMPLATES_DIR / "accounts").rglob("*.html"),
        *(TEMPLATES_DIR / "registration").rglob("*.html"),
        TEMPLATES_DIR / "403.html",
    ]
    for template in templates:
        assert "zoom/" not in template.read_text(encoding="utf-8"), str(template)


class _ListInParagraph(HTMLParser):
    """Records every <ul> opened while a <p> is open (html.parser keeps the literal nesting)."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.offenders = 0

    def handle_starttag(self, tag, attrs):
        if tag == "ul" and "p" in self.stack:
            self.offenders += 1
        if tag not in ("input", "br", "img", "meta", "link", "hr", "use"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass


@pytest.mark.django_db
def test_no_page_in_this_brief_puts_a_list_inside_a_paragraph(client):
    superuser = make_user("head", is_superuser=True)
    other = make_user("teacher")
    client.force_login(superuser)
    urls = [
        reverse("accounts:staff"),
        reverse("accounts:staff_add"),
        reverse("accounts:staff_edit", args=[other.pk]),
        reverse("accounts:staff_password", args=[other.pk]),
        reverse("accounts:password_change"),
    ]
    for url in urls:
        parser = _ListInParagraph()
        parser.feed(client.get(url).content.decode())
        assert parser.offenders == 0, url
    content = client.get(reverse("accounts:staff_add")).content.decode()
    assert re.search(r'<div class="field__help" id="password1-help">\s*<ul>', content)


def test_field_help_list_css_rule_exists():
    css = (BASE_DIR / "static" / "css" / "style.css").read_text(encoding="utf-8")
    assert re.search(r"\.field__help ul\s*\{", css)
