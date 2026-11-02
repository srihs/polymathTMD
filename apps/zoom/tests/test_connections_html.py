"""HTML-level checks for brief 015's real templates (verifier-added).

``conftest.py`` stubs ``zoom/connections.html`` and ``zoom/connection_form.html`` (and the
accounts pages) for the view-layer tests in ``test_connections.py``, so those pin the
context contract but not the markup. This file renders the real templates and checks what a
person or screen reader sees: navigation (criterion 9), the list (10), the pasted inputs and
the "wasn't kept" notes (11, 14), the state blocks and address (15), the account pages'
connection section (18, 19, 21) and that no value or ciphertext leaks into any page (14, 41).
"""

import re

import pytest
from django.urls import reverse

from apps.zoom import crypto
from apps.zoom.models import ZoomConnection

from . import zoommock as zm
from .conftest import make_account
from .test_accounts import _user_with
from .test_connections import ADD_URL, add_data, edit_data, edit_url
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db

LIST_URL = reverse("zoom:connections")
ACCOUNTS_URL = reverse("zoom:accounts")


def page(client, url, settings, **kwargs):
    _real_templates(settings)
    response = client.get(url, **kwargs)
    assert response.status_code == 200
    return response.content.decode()


def tag_for(html, word):
    """The whole ``<span class="tag …">`` that holds ``word``, so tone and icon can be read."""
    found = re.findall(r'<span class="tag [^"]*">(?:(?!</span>).)*?' + re.escape(word), html, re.S)
    assert found, f"no tag with {word!r}"
    return found[0]


# ------------------------------------------------------------------------ 9 navigation


@pytest.mark.parametrize("name", ["connections", "connection_add", "connection_edit"])
def test_zoom_accounts_stays_current_on_every_connection_page(it_client, settings, name):
    conn = zm.connection()
    url = reverse(f"zoom:{name}", args=[conn.pk] if name == "connection_edit" else [])
    html = page(it_client, url, settings)
    assert re.search(r'href="' + re.escape(ACCOUNTS_URL) + r'" aria-current="page"', html)


def test_breadcrumbs_on_the_three_pages(it_client, settings):
    conn = zm.connection()
    for url, last in (
        (LIST_URL, "Zoom connections"),
        (ADD_URL, "Add a Zoom connection"),
        (edit_url(conn), conn.slug),
    ):
        html = page(it_client, url, settings)
        crumbs = html[html.index("crumbs") :]
        assert f'<span aria-current="page">{last}</span>' in crumbs
        assert f'href="{ACCOUNTS_URL}"' in crumbs
    assert f'href="{LIST_URL}"' in page(it_client, ADD_URL, settings)


def test_the_connections_link_shows_only_to_those_who_may_manage_them(it_client, settings, client):
    account = make_account("Zoom 01")
    assert f'href="{LIST_URL}"' in page(it_client, ACCOUNTS_URL, settings)
    edit = reverse("zoom:account_edit", args=[account.pk])
    assert f'href="{LIST_URL}"' in page(it_client, edit, settings)
    assert f'href="{LIST_URL}"' in page(it_client, reverse("zoom:account_add"), settings)

    viewer = _user_with("view_hostaccount", username="keyless")
    client.force_login(viewer)
    assert f'href="{LIST_URL}"' not in page(client, ACCOUNTS_URL, settings)


# ------------------------------------------------------------------------ 10 the list


def test_empty_list_has_one_add_button_in_the_head_and_none_in_the_empty_state(it_client, settings):
    html = page(it_client, LIST_URL, settings)
    assert "No Zoom connections yet." in html
    assert "Add one for each paid Zoom subscription." in html
    add_links = re.findall(r'<a [^>]*href="' + re.escape(ADD_URL) + r'"[^>]*>.*?</a>', html, re.S)
    assert len(add_links) == 1
    assert 'use href="#i-plus"' in add_links[0] and "Add a Zoom connection" in add_links[0]
    assert html.index(add_links[0]) < html.index("No Zoom connections yet.")


def test_the_list_rows_states_icons_and_accounts(it_client, settings):
    both = zm.connection("zoom-01", webhook_secret="test-webhook-secret-value")
    zm.make_unreadable(zm.connection("zoom-02"), client=True, webhook=True)
    zm.connection("zoom-03")
    make_account("Zoom 02", sort_order=2).zoom_connection = both
    for label, order in (("Zoom 02", 2), ("Zoom 01", 1)):
        account = make_account(label + " x", sort_order=order)
        account.zoom_connection = both
        account.save()
    html = page(it_client, LIST_URL, settings)
    assert html.index("zoom-01") < html.index("zoom-02") < html.index("zoom-03")
    assert html.index("Zoom 01 x") < html.index("Zoom 02 x")  # sort_order, then label
    assert "No account yet" in html
    saved = tag_for(html, "Saved")
    assert "tag--plain" in saved and "#i-lock" in saved
    warn = tag_for(html, "Not saved")
    assert "tag--warn" in warn and "#i-alert-triangle" in warn
    bad = tag_for(html, "Can't be read")
    assert "tag--bad" in bad and "#i-alert-octagon" in bad


# ------------------------------------------------------------------------ 11/14 the forms


@pytest.mark.parametrize("on_change", [False, True])
def test_pasted_inputs_render_as_plain_text_with_no_value_and_no_maxlength(
    it_client, settings, on_change
):
    url = edit_url(zm.connection()) if on_change else ADD_URL
    html = page(it_client, url, settings)
    for name in ("account_id", "client_id", "client_secret", "webhook_secret"):
        tag = re.search(r'<input [^>]*name="' + name + r'"[^>]*>', html).group(0)
        assert 'type="text"' in tag and "maxlength" not in tag
        for attr in ('autocomplete="off"', 'autocapitalize="none"', 'autocorrect="off"'):
            assert attr in tag
        assert 'spellcheck="false"' in tag
        if name.endswith("secret"):
            assert "value=" not in tag
    if not on_change:
        assert 'maxlength="40"' in html
    assert 'type="password"' not in html


def test_every_pasted_input_has_a_label_and_its_help_is_described(it_client, settings):
    html = page(it_client, ADD_URL, settings)
    for name in ("slug", "account_id", "client_id", "client_secret", "webhook_secret"):
        assert f'for="id_{name}"' in html
        assert f'id="{name}-help"' in html
        tag = re.search(r'<input [^>]*name="' + name + r'"[^>]*>', html).group(0)
        assert f"{name}-help" in tag


def test_an_invalid_add_keeps_names_drops_secrets_and_adds_the_notes(it_client, settings):
    _real_templates(settings)
    response = it_client.post(
        ADD_URL,
        add_data(
            account_id="has space",
            client_secret="typed-client-secret-xyz",
            webhook_secret="typed-webhook-secret-xyz",
        ),
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "We couldn't save this Zoom connection yet." in html
    assert "typed-client-secret-xyz" not in html and "typed-webhook-secret-xyz" not in html
    assert "has space" in html and zm.CLIENT_ID in html
    for kind in ("client", "webhook"):
        assert f"the {kind} secret you typed wasn" in html
        tag = re.search(r'<input [^>]*name="' + kind + r'_secret"[^>]*>', html).group(0)
        assert f"{kind}_secret-note" in tag and "value=" not in tag
    account_tag = re.search(r'<input [^>]*name="account_id"[^>]*>', html).group(0)
    assert 'aria-invalid="true"' in account_tag and "account_id-error" in account_tag


# ------------------------------------------------------------------------ 15 the change page


def test_change_page_states_and_address(it_client, settings, it_user):
    conn = zm.connection(by=it_user)
    html = page(it_client, edit_url(conn), settings)
    assert "No webhook secret saved" in html
    assert "Connection details saved on" in html
    assert f" by {it_user.get_full_name() or it_user.get_username()}." in html
    assert "/zoom/webhooks/zoom-test/" in html
    assert "copy-value" in html
    assert not re.search(r'<a [^>]*href="[^"]*/zoom/webhooks/', html)  # text, not a link
    # Plain http: Zoom can't use the address, and the page says so.
    assert "use this address" in html
    secure = page(it_client, edit_url(conn), settings, secure=True)
    assert "use this address" not in secure
    assert "https://testserver/zoom/webhooks/zoom-test/" in secure


def test_change_page_saved_and_unreadable_webhook_and_credentials(it_client, settings, it_user):
    conn = zm.connection(webhook_secret="test-webhook-secret-value", by=it_user)
    html = page(it_client, edit_url(conn), settings)
    assert "Webhook secret saved on" in html and "Nothing heard from Zoom yet." in html
    assert "Remove the saved webhook secret" in html
    zm.make_unreadable(conn, client=True, webhook=True)
    html = page(it_client, edit_url(conn), settings)
    assert "notice--bad" in html
    assert "can't be read with the server's current encryption keys" in html
    assert "Remove the saved webhook secret" in html


def test_no_secret_value_ciphertext_or_id_leaks_outside_the_change_page(it_client, settings):
    conn = zm.connection(webhook_secret="test-webhook-secret-value")
    account = make_account("Zoom 01")
    zm.connect(account)
    needles = [zm.CLIENT_SECRET, "test-webhook-secret-value", conn.client_secret_encrypted]
    needles += [conn.webhook_secret_encrypted, "gAAAAA"]
    id_needles = [zm.ACCOUNT_ID, zm.client_id_for(zm.SLUG)]
    pages = {
        "list": LIST_URL,
        "add": ADD_URL,
        "accounts": ACCOUNTS_URL,
        "account_add": reverse("zoom:account_add"),
        "account_edit": reverse("zoom:account_edit", args=[account.pk]),
    }
    for name, url in pages.items():
        html = page(it_client, url, settings)
        for needle in needles + id_needles:
            assert needle not in html, f"{needle!r} on {name}"
    change = page(it_client, edit_url(conn), settings)
    for needle in needles:
        assert needle not in change
    for needle in id_needles:  # the IDs are allowed here, inside their own inputs only
        assert change.count(needle) == 1
        assert re.search(r'<input [^>]*value="' + re.escape(needle) + '"', change)


# ------------------------------------------------------------------------ 18/19/21 accounts


def test_account_page_connection_select_and_three_states(it_client, settings):
    account = make_account("Zoom 01")
    url = reverse("zoom:account_edit", args=[account.pk])
    html = page(it_client, url, settings)
    assert re.search(r'<label [^>]*for="id_zoom_connection"', html)
    assert "No Zoom connection yet" in html
    assert 'id="zoom_connection-help"' in html and "zoom_connection-help" in re.search(
        r"<select [^>]*>", html
    ).group(0)
    assert "Not set up" in html

    conn = zm.connect(account)
    html = page(it_client, url, settings)
    assert "Set up" in html and "notice--ok" in html
    assert f'href="{edit_url(conn)}"' in html  # the name links for those who manage connections

    zm.make_unreadable(conn)
    html = page(it_client, url, settings)
    assert "notice--bad" in html and "Type its client secret again" in html


def test_a_posted_choice_stays_selected_after_an_invalid_account_post(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    conn = zm.connection()
    response = it_client.post(
        reverse("zoom:account_edit", args=[account.pk]),
        {"label": "", "email": "x@example.test", "sort_order": 1, "zoom_connection": conn.pk},
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert re.search(rf'<option value="{conn.pk}"[^>]*selected', html)


def test_accounts_list_tags_use_icon_and_word_for_each_state(it_client, settings):
    ready = make_account("Zoom 01", sort_order=1)
    zm.connect(ready)
    broken = make_account("Zoom 02", sort_order=2)
    zm.make_unreadable(zm.connect(broken, slug="zoom-02"))
    make_account("Zoom 03", sort_order=3)
    html = page(it_client, ACCOUNTS_URL, settings)
    unreadable = tag_for(html, "Can't be read")
    assert "#i-alert-octagon" in unreadable and "tag--bad" in unreadable
    assert "Missing on the server" not in html
    for word in ("Set up", "Not set up"):
        assert word in html


def test_the_secret_ciphertext_prefix_is_never_in_any_page_after_a_save(it_client, settings):
    _real_templates(settings)
    response = it_client.post(ADD_URL, add_data(webhook_secret="test-webhook-secret-value"))
    assert response.status_code == 302
    conn = ZoomConnection.objects.get(slug="zoom-01")
    assert crypto.decrypt(conn.client_secret_encrypted) == zm.CLIENT_SECRET
    for url in (LIST_URL, edit_url(conn)):
        html = page(it_client, url, settings)
        assert "gAAAAA" not in html
    edit = it_client.post(edit_url(conn), edit_data(conn, client_secret="test-client-secret-new"))
    assert edit.status_code == 302
    assert "test-client-secret-new" not in page(it_client, edit_url(conn), settings)
