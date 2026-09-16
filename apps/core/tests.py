"""Tests for the core app: home page, site-wide context and template guards."""

import re

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils.html import escape

from apps.core.context_processors import site

STATIC_TAG = re.compile(r"""{%\s*static\s+['"]([^'"]+)['"]\s*%}""")


def test_every_static_reference_in_templates_exists():
    """In production a missing static file is a 500, so catch it here."""
    missing = []
    for template in (settings.BASE_DIR / "templates").rglob("*.html"):
        for ref in STATIC_TAG.findall(template.read_text(encoding="utf-8")):
            if not finders.find(ref):
                missing.append(f"{template.name}: {ref}")
    assert not missing, missing


def test_healthz_ignores_host_header(client):
    response = client.get("/healthz/", HTTP_HOST="unlisted-host.internal")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_home_requires_login(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


@pytest.mark.django_db
def test_home_renders_for_signed_in_user(client):
    user = get_user_model().objects.create_user(username="staff", password="x")
    client.force_login(user)
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b"css/style.css" in response.content


@pytest.mark.django_db
def test_home_shows_sign_out_button_that_posts_to_logout(client):
    user = get_user_model().objects.create_user(username="staff", password="x")
    client.force_login(user)
    content = client.get(reverse("core:home")).content.decode()
    logout_url = re.escape(reverse("accounts:logout"))
    form = re.search(rf'<form[^>]*method="post"[^>]*action="{logout_url}".*?</form>', content, re.S)
    assert form, "no POST form to the logout URL on the home page"
    assert re.search(r'<button[^>]*type="submit"[^>]*>\s*Sign out\s*</button>', form.group(0))


# --- Site name and page titles (brief 001, issue 1) ---------------------------------


def _title(content):
    """Return the text of the page's <title>, so failures show what was rendered."""
    match = re.search(r"<title>(.*?)</title>", content, re.S)
    assert match, "no <title> in the page"
    return match.group(1)


def _signed_in(client, **extra):
    user = get_user_model().objects.create_user(username="staff", password="x", **extra)
    client.force_login(user)
    return user


def test_site_context_processor_uses_prefixed_key():
    """``site_name`` is overwritten by Django's auth views, so it must not be our key."""
    context = site(RequestFactory().get("/"))
    assert context == {"tmd_site_name": settings.SITE_NAME}


@pytest.mark.django_db
def test_home_title_and_body_use_site_name(client):
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    name = escape(settings.SITE_NAME)
    assert _title(content) == f"Home · {name}"
    assert f"{name} is set up and running." in content


@pytest.mark.django_db
@override_settings(SITE_NAME="Example Desk")
def test_site_name_setting_is_the_only_source_of_page_titles(client):
    """Login and home both follow the setting, so nothing else feeds the title."""
    login = client.get(reverse("accounts:login")).content.decode()
    assert _title(login) == "Sign in · Example Desk"

    _signed_in(client)
    home = client.get(reverse("core:home")).content.decode()
    assert _title(home) == "Home · Example Desk"


def test_no_template_reads_the_colliding_site_name_variable():
    """Django auth views set ``site_name`` to the request host; templates must not use it.

    ``tmd_site_name`` doesn't match because ``_`` is a word character.
    """
    offenders = [
        str(template.relative_to(settings.BASE_DIR))
        for template in (settings.BASE_DIR / "templates").rglob("*")
        if template.is_file() and re.search(r"\bsite_name\b", template.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


# --- Admin link only for staff (brief 001, issue 3) ---------------------------------


def _admin_links(content):
    """Every <a> on the page that points at the admin or is labelled "Admin"."""
    admin_url = re.escape(reverse("admin:index"))
    return re.findall(
        rf'<a[^>]*href="{admin_url}"[^>]*>.*?</a>|<a[^>]*>\s*Admin\s*</a>', content, re.S
    )


def _has_logout_form(content):
    logout_url = re.escape(reverse("accounts:logout"))
    return re.search(rf'<form[^>]*method="post"[^>]*action="{logout_url}"', content)


@pytest.mark.django_db
def test_home_hides_admin_link_from_non_staff(client):
    _signed_in(client, is_staff=False)
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    content = response.content.decode()
    assert _admin_links(content) == []
    assert _has_logout_form(content)


@pytest.mark.django_db
def test_home_shows_admin_link_to_staff(client):
    _signed_in(client, is_staff=True)
    content = client.get(reverse("core:home")).content.decode()
    admin_url = re.escape(reverse("admin:index"))
    assert re.search(rf'<a[^>]*href="{admin_url}"[^>]*>\s*Admin\s*</a>', content)
    assert _has_logout_form(content)


# --- Template header comments (brief 001, criterion 15) -----------------------------


@pytest.mark.parametrize(
    "relative_path",
    ["base.html", "registration/login.html", "core/home.html"],
)
def test_template_starts_with_purpose_comment(relative_path):
    """Each template this task touches must open with a ``{# ... #}`` header naming its purpose."""
    template = settings.BASE_DIR / "templates" / relative_path
    first_line = template.read_text(encoding="utf-8").split("\n", 1)[0]
    assert first_line.startswith("{#"), f"{relative_path} must start with a {{# ... #}} comment"
    assert re.match(r"{#.*?#}", first_line), f"{relative_path}: the comment on line 1 isn't closed"


@pytest.mark.django_db
def test_home_shows_admin_link_to_superuser(client):
    user = get_user_model().objects.create_superuser(username="head", password="x")
    client.force_login(user)
    content = client.get(reverse("core:home")).content.decode()
    admin_url = re.escape(reverse("admin:index"))
    assert re.search(rf'<a[^>]*href="{admin_url}"[^>]*>\s*Admin\s*</a>', content)
