"""Criterion 19: the sidebar's `Zoom links` group, shown only to permission holders, with
`aria-current` tracking the current page (brief 005).

``apps/zoom/tests/conftest.py`` stubs the ``zoom/*.html`` page templates for the view-layer
tests, so this is the one place that renders the real templates to prove the sidebar wiring.
"""

import re

import pytest
from django.conf import settings as django_settings
from django.urls import reverse

from .conftest import make_request

pytestmark = pytest.mark.django_db


def _real_templates(settings):
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


def _sidenav(html):
    match = re.search(r'<nav class="sidenav__menu".*?</nav>', html, re.S)
    assert match, "no sidebar nav found in the response"
    return match.group(0)


def test_it_user_sees_the_zoom_links_group(client, settings, it_user, account):
    _real_templates(settings)
    client.force_login(it_user)
    response = client.get(reverse("zoom:queue"))
    assert response.status_code == 200
    nav = _sidenav(response.content.decode())
    assert 'id="nav-zoom"' in nav
    assert "Zoom links" in nav
    assert "Link requests" in nav
    assert reverse("zoom:queue") in nav


def test_zoom_links_group_sits_between_menu_and_administration_for_superusers(
    client, settings, superuser
):
    """A superuser holds both the Zoom permission and is_staff, so both groups render."""
    _real_templates(settings)
    client.force_login(superuser)
    nav = _sidenav(client.get(reverse("zoom:queue")).content.decode())
    assert "Administration" in nav, "superuser should see the Administration group too"
    assert nav.index("Zoom links") < nav.index("Administration")


def test_plain_user_never_sees_the_zoom_links_group(client, settings, plain_user):
    _real_templates(settings)
    client.force_login(plain_user)
    response = client.get(reverse("core:home"))
    html = response.content.decode()
    nav = _sidenav(html)
    assert "Zoom links" not in nav
    assert 'id="nav-zoom"' not in nav


def test_link_requests_item_is_current_on_queue_and_detail_but_not_home(client, settings, it_user):
    _real_templates(settings)
    client.force_login(it_user)
    link_request = make_request()

    queue_nav = _sidenav(client.get(reverse("zoom:queue")).content.decode())
    detail_nav = _sidenav(
        client.get(reverse("zoom:detail", args=[link_request.pk])).content.decode()
    )
    home_nav = _sidenav(client.get(reverse("core:home")).content.decode())

    for nav, label in [(queue_nav, "queue"), (detail_nav, "detail")]:
        link_requests_item = re.search(r"<a[^>]*>\s*Link requests\s*</a>", nav) or re.search(
            r'<a[^>]*href="{}"[^>]*>'.format(re.escape(reverse("zoom:queue"))), nav
        )
        assert link_requests_item, f"Link requests link missing on {label}"
        tag = link_requests_item.group(0)
        assert 'aria-current="page"' in tag, f"Link requests should be current on {label}"

    home_link = re.search(
        r'<a[^>]*href="{}"[^>]*>'.format(re.escape(reverse("core:home"))), home_nav
    )
    assert home_link and 'aria-current="page"' in home_link.group(0)

    # On the zoom pages, Home must NOT be marked current.
    home_link_on_queue = re.search(
        r'<a[^>]*href="{}"[^>]*>'.format(re.escape(reverse("core:home"))), queue_nav
    )
    assert home_link_on_queue and 'aria-current="page"' not in home_link_on_queue.group(0)


# --------------------------------------------------------------------------- brief 008


def _item(nav, url_name, *args):
    """The sidebar ``<a>`` tag linking to ``url_name``, or None."""
    match = re.search(rf'<a[^>]*href="{re.escape(reverse(url_name, args=args))}"[^>]*>', nav)
    return match.group(0) if match else None


def test_it_user_sees_link_requests_then_zoom_accounts(client, settings, it_user):
    """Brief 005's criterion 19 ("holds one item") is amended by brief 008's criterion 3."""
    _real_templates(settings)
    client.force_login(it_user)
    nav = _sidenav(client.get(reverse("zoom:accounts")).content.decode())
    assert nav.index("Link requests") < nav.index("Zoom accounts")
    assert _item(nav, "zoom:queue") and _item(nav, "zoom:accounts")


def test_account_viewer_sees_the_group_with_only_zoom_accounts(client, settings):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission

    _real_templates(settings)
    viewer = get_user_model().objects.create_user(username="viewer", password="pw")
    viewer.user_permissions.add(Permission.objects.get(codename="view_hostaccount"))
    client.force_login(viewer)
    nav = _sidenav(client.get(reverse("zoom:accounts")).content.decode())
    assert 'id="nav-zoom"' in nav
    assert _item(nav, "zoom:accounts")
    assert _item(nav, "zoom:queue") is None


def test_zoom_accounts_is_current_on_the_accounts_pages_only(client, settings, it_user, account):
    _real_templates(settings)
    client.force_login(it_user)
    for url in (
        reverse("zoom:accounts"),
        reverse("zoom:account_add"),
        reverse("zoom:account_edit", args=[account.pk]),
    ):
        nav = _sidenav(client.get(url).content.decode())
        assert 'aria-current="page"' in _item(nav, "zoom:accounts"), url
        assert 'aria-current="page"' not in _item(nav, "zoom:queue"), url
        assert 'aria-current="page"' not in _item(nav, "core:home"), url

    nav = _sidenav(client.get(reverse("zoom:queue")).content.decode())
    assert 'aria-current="page"' in _item(nav, "zoom:queue")
    assert 'aria-current="page"' not in _item(nav, "zoom:accounts")
