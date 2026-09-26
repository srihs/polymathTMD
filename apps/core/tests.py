"""Tests for the core app: home page, site-wide context and template guards.

Brief 004 ported the f-desk shell into base.html and the new partials under
templates/partials/. Three tests that pinned the old markup are rewritten
here (sign-out button, the two admin-link tests, which brief 010 turned into
Staff and access tests) to match text content with
tags stripped, because those controls now carry an icon. The header-comment
test is widened from three hard-coded paths to every template under
templates/ (criterion 21). The rest of this module adds the shell/CSS/
placeholder guard tests the brief assigns to the verifier.
"""

import re

import pytest
from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.staticfiles import finders
from django.test import Client, RequestFactory, override_settings
from django.urls import resolve, reverse
from django.utils.html import escape

from apps.core.context_processors import site
from apps.core.views import home as home_view

STATIC_TAG = re.compile(r"""{%\s*static\s+['"]([^'"]+)['"]\s*%}""")
TEMPLATES_DIR = settings.BASE_DIR / "templates"


def _templates():
    return sorted(TEMPLATES_DIR.rglob("*.html"))


def test_every_static_reference_in_templates_exists():
    """In production a missing static file is a 500, so catch it here."""
    missing = []
    for template in (settings.BASE_DIR / "templates").rglob("*.html"):
        for ref in STATIC_TAG.findall(template.read_text(encoding="utf-8")):
            if not finders.find(ref):
                missing.append(f"{template.name}: {ref}")
    assert not missing, missing


def test_dockerignore_keeps_private_data_out_of_the_image():
    """The runtime stages `COPY . .`, so an unlisted root file ships in the image.

    Brief 006 criterion 44: the host-key spreadsheet was baked into local images.
    """
    lines = (settings.BASE_DIR / ".dockerignore").read_text(encoding="utf-8").splitlines()
    required = {
        "/Dashboard 2A.xlsx",
        "/*.xlsx",
        "/*.xlsm",
        "/*.xls",
        "/*.ods",
        "/*.csv",
        "/data/private/",
        "zoom-credentials.env",
        ".env",
        ".cache",
    }
    assert required <= {line.strip() for line in lines}


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
    """Sign out now lives in the user menu; the button carries an icon before the word (D7)."""
    user = get_user_model().objects.create_user(username="staff", password="x")
    client.force_login(user)
    content = client.get(reverse("core:home")).content.decode()
    logout_url = re.escape(reverse("accounts:logout"))
    form = re.search(rf'<form[^>]*method="post"[^>]*action="{logout_url}".*?</form>', content, re.S)
    assert form, "no POST form to the logout URL on the home page"
    assert 'name="csrfmiddlewaretoken"' in form.group(0)
    button = re.search(r'<button[^>]*type="submit"[^>]*>(.*?)</button>', form.group(0), re.S)
    assert button, "no submit button inside the sign-out form"
    assert re.sub(r"<[^>]+>", "", button.group(1)).strip() == "Sign out"


@pytest.mark.django_db
def test_no_anchor_link_points_at_logout(client):
    """D7/criterion 9: sign-out is a POST form only, never a GET <a> link, anywhere on the page."""
    user = get_user_model().objects.create_user(username="staff", password="x")
    client.force_login(user)
    content = client.get(reverse("core:home")).content.decode()
    logout_url = reverse("accounts:logout")
    assert logout_url not in re.findall(r'<a[^>]*href="([^"]*)"', content)


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


# --- Staff and access link (brief 001 issue 3 as an Admin link; brief 004 moved it to the
# sidebar; brief 010 criterion 21 replaces the Django admin with Staff and access, gated by
# perms.accounts.view_user, never by is_staff) -------------------------------------------


def _staff_links(content):
    """Every <a href="{staff}"> on the page whose text, tags stripped, is "Staff and access".

    The link sits beside an icon inside a <span>, so this strips inner markup first.
    """
    staff_url = re.escape(reverse("accounts:staff"))
    inners = re.findall(rf'<a[^>]*href="{staff_url}"[^>]*>(.*?)</a>', content, re.S)
    return [
        inner for inner in inners if re.sub(r"<[^>]+>", "", inner).strip() == "Staff and access"
    ]


def _has_logout_form(content):
    logout_url = re.escape(reverse("accounts:logout"))
    return re.search(rf'<form[^>]*method="post"[^>]*action="{logout_url}"', content)


def _staff_manager(client):
    user = _signed_in(client)
    user.groups.add(Group.objects.get(name="Staff managers"))
    return user


@pytest.mark.django_db
def test_home_hides_staff_and_access_from_an_is_staff_user_without_permissions(client):
    _signed_in(client, is_staff=True)
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    content = response.content.decode()
    assert _staff_links(content) == []
    assert "Administration" not in content
    assert _has_logout_form(content)


@pytest.mark.django_db
def test_home_shows_staff_and_access_to_a_staff_manager(client):
    _staff_manager(client)
    content = client.get(reverse("core:home")).content.decode()
    assert len(_staff_links(content)) == 1
    assert _has_logout_form(content)


@pytest.mark.django_db
def test_home_shows_staff_and_access_to_a_superuser(client):
    user = get_user_model().objects.create_superuser(username="head", password="x")
    client.force_login(user)
    content = client.get(reverse("core:home")).content.decode()
    assert len(_staff_links(content)) == 1


def test_no_template_links_the_admin_or_reads_is_staff():
    """Criterion 3: the Django admin is gone and is_staff no longer means anything (D5)."""
    offenders = [
        str(template.relative_to(TEMPLATES_DIR))
        for template in _templates()
        if re.search(r"admin:index|\bis_staff\b", template.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


# --- Template header comments (brief 001 criterion 15; brief 004 widens to every template) --


@pytest.mark.parametrize(
    "relative_path",
    [str(p.relative_to(TEMPLATES_DIR)) for p in _templates()],
)
def test_template_starts_with_purpose_comment(relative_path):
    """Each template under templates/ must open with a ``{# ... #}`` header naming its purpose."""
    template = TEMPLATES_DIR / relative_path
    first_line = template.read_text(encoding="utf-8").split("\n", 1)[0]
    assert first_line.startswith("{#"), f"{relative_path} must start with a {{# ... #}} comment"
    assert re.match(r"{#.*?#}", first_line), f"{relative_path}: the comment on line 1 isn't closed"


# --- Document head and first paint (brief 004 criteria 1, 2) -------------------------


APPROVED_HTML_TAG = (
    '<html lang="en-LK" data-theme="light" data-width="full" '
    'data-nav-size="standard" data-nav-tone="purple">'
)


@pytest.mark.django_db
def test_home_html_tag_carries_approved_defaults(client):
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    assert APPROVED_HTML_TAG in content


@pytest.mark.django_db
def test_login_html_tag_carries_approved_defaults(client):
    content = client.get(reverse("accounts:login")).content.decode()
    assert APPROVED_HTML_TAG in content


def _head_checks(content):
    """Assert head order: theme-init.js (blocking), the Plex link, style.css; app.js deferred."""
    theme_init = re.search(r'<script[^>]*src="[^"]*theme-init\.js"[^>]*>', content)
    assert theme_init, "theme-init.js is not loaded"
    assert "defer" not in theme_init.group(0)
    assert "async" not in theme_init.group(0)

    font_link = re.search(
        r'<link[^>]*href="https://fonts\.googleapis\.com/css2\?family=IBM\+Plex\+Sans:'
        r'wght@300;400;500;600[^"]*display=swap[^"]*"[^>]*>',
        content,
    )
    assert font_link, (
        "IBM Plex Sans stylesheet link is missing, or its weights/display=swap are wrong"
    )

    style_link = re.search(r'<link[^>]*href="[^"]*css/style\.css"[^>]*>', content)
    assert style_link, "style.css is not loaded"

    app_js_tags = re.findall(r'<script[^>]*src="[^"]*js/app\.js"[^>]*>', content)
    assert len(app_js_tags) == 1, "app.js must be loaded exactly once"
    assert "defer" in app_js_tags[0]

    assert theme_init.start() < font_link.start() < style_link.start()
    assert style_link.end() <= content.find(app_js_tags[0])

    for banned in ("Cinzel", "Nunito", "Nunito+Sans"):
        assert banned not in content, (
            f"{banned!r} must not appear; the fonts changed to IBM Plex Sans"
        )


@pytest.mark.django_db
def test_home_head_loads_theme_init_before_fonts_before_style(client):
    _signed_in(client)
    _head_checks(client.get(reverse("core:home")).content.decode())


@pytest.mark.django_db
def test_login_head_loads_theme_init_before_fonts_before_style(client):
    _head_checks(client.get(reverse("accounts:login")).content.decode())


def test_no_template_references_the_old_fonts():
    offenders = [
        str(template.relative_to(settings.BASE_DIR))
        for template in _templates()
        if re.search(r"Cinzel|Nunito", template.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


# --- The shell: sidebar (brief 004 criterion 6) --------------------------------------


@pytest.mark.django_db
def test_sidebar_home_link_has_aria_current_only_on_home(client):
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    nav = re.search(r'<nav class="sidenav__menu".*?</nav>', content, re.S).group(0)
    assert nav.count('aria-current="page"') == 1
    home_url = re.escape(reverse("core:home"))
    assert re.search(rf'<a class="sidenav__link" href="{home_url}"[^>]*aria-current="page"', nav)


@pytest.mark.django_db
def test_sidebar_links_resolve_to_named_urls_only(client):
    _staff_manager(client)
    content = client.get(reverse("core:home")).content.decode()
    nav = re.search(r'<nav class="sidenav__menu".*?</nav>', content, re.S).group(0)
    hrefs = re.findall(r'<a class="sidenav__link"[^>]*href="([^"]*)"', nav)
    assert hrefs == [reverse("core:home"), reverse("accounts:staff")]
    assert "#" not in "".join(hrefs), "no dead '#' links belong in the nav"


@pytest.mark.django_db
def test_sidebar_shows_administration_group_only_with_view_user(client):
    _signed_in(client, is_staff=True)
    content = client.get(reverse("core:home")).content.decode()
    assert "Administration" not in content
    assert reverse("accounts:staff") not in content


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ["staff", "staff_add", "staff_edit", "staff_password"])
def test_staff_and_access_is_current_on_every_staff_page_and_last(client, url_name):
    """Criterion 3: aria-current on the four staff pages; Administration stays last."""
    user = get_user_model().objects.create_superuser(username="head", password="x")
    # Someone else: your own pk on staff_password redirects to password_change (010, crit. 34).
    other = get_user_model().objects.create_user(username="teacher", password="x")
    client.force_login(user)
    args = [other.pk] if url_name in ("staff_edit", "staff_password") else []
    content = client.get(reverse(f"accounts:{url_name}", args=args)).content.decode()
    nav = re.search(r'<nav class="sidenav__menu".*?</nav>', content, re.S).group(0)
    staff_url = re.escape(reverse("accounts:staff"))
    assert re.search(rf'<a class="sidenav__link" href="{staff_url}"[^>]*aria-current="page"', nav)
    assert nav.count('aria-current="page"') == 1
    assert 'id="nav-admin"' in nav
    assert nav.index("Zoom links") < nav.index("Administration")
    groups = re.findall(r'<p class="sidenav__group-title" id="([^"]+)"', nav)
    assert groups[-1] == "nav-admin", groups


@pytest.mark.django_db
def test_change_your_password_sits_between_layout_settings_and_sign_out(client):
    """Criterion 4: in every signed-in user's menu, a plain link, so it works without JS."""
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    menus = re.findall(r"<details[^>]*data-pop[^>]*>.*?</details>", content, re.S)
    menu = next(m for m in menus if "Sign out" in m)
    link = re.search(
        rf'<a[^>]*href="{re.escape(reverse("accounts:password_change"))}"[^>]*>(.*?)</a>',
        menu,
        re.S,
    )
    assert link and re.sub(r"<[^>]+>", "", link.group(1)).strip() == "Change your password"
    assert menu.index("Layout settings") < link.start() < menu.index("Sign out")


# --- The shell: user menu / sign-out (brief 004 criterion 9) -------------------------


@pytest.mark.django_db
def test_user_menu_layout_settings_button_is_hidden_in_html(client):
    """Layout settings is JS-only, so it must ship `hidden` and be revealed by app.js."""
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    button = re.search(r"<button[^>]*data-settings-open[^>]*>", content)
    assert button and "hidden" in button.group(0)


# --- The shell: settings dialog (brief 004 criterion 12) -----------------------------


@pytest.mark.django_db
def test_settings_dialog_present_on_home(client):
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    assert re.search(r"<dialog[^>]*data-settings[^>]*>", content)
    assert "Layout settings" in content
    assert "Your choices are saved in this browser only." in content


@pytest.mark.django_db
def test_settings_dialog_absent_on_login(client):
    content = client.get(reverse("accounts:login")).content.decode()
    assert "data-settings" not in content
    assert "<dialog" not in content


# --- The shell: messages in the page flow (brief 004 criterion 15, D16) --------------


def _rendered_home_with_message(level_func, text):
    """Render core.views.home directly with one message queued, bypassing the client
    round trip since the default FallbackStorage needs a session/cookie dance that
    the brief allows working around ("through the message storage on the request").
    resolver_match is set explicitly so base.html's sidebar/breadcrumb reads behave
    exactly as they do for a real request."""
    user = get_user_model().objects.create_user(username="staff", password="x")
    request = RequestFactory().get(reverse("core:home"))
    request.resolver_match = resolve(reverse("core:home"))
    request.user = user
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    level_func(request, text)
    return home_view(request).content.decode()


@pytest.mark.django_db
def test_success_message_renders_once_in_flow_under_title_row_with_role_status():
    content = _rendered_home_with_message(django_messages.success, "Request <sent> & done")
    assert content.count("data-flash>") == 1, "exactly one flash message should render"
    flash = re.search(
        r'<div class="flash flash--ok" role="status" data-flash>.*?</div>\s*</div>', content, re.S
    )
    assert flash, "success message did not render as an in-flow flash with role=status"
    assert "Request &lt;sent&gt; &amp; done" in flash.group(0), "message text must be escaped"

    titlebar_end = content.index("</div>", content.index('class="titlebar"'))
    box_start = content.index('class="box"')
    flash_start = content.index('class="flashes"')
    assert titlebar_end < flash_start < box_start, (
        "the flash must sit under the title row, inside <main>"
    )

    close_button = re.search(r"<button[^>]*data-flash-close[^>]*>", flash.group(0))
    assert close_button and "hidden" in close_button.group(0)


@pytest.mark.django_db
def test_error_message_uses_role_alert():
    content = _rendered_home_with_message(django_messages.error, "Something went wrong.")
    assert re.search(r'<div class="flash flash--bad" role="alert" data-flash>', content)


@pytest.mark.django_db
def test_no_message_renders_no_flash_container():
    user = get_user_model().objects.create_user(username="staff", password="x")
    request = RequestFactory().get(reverse("core:home"))
    request.resolver_match = resolve(reverse("core:home"))
    request.user = user
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    content = home_view(request).content.decode()
    assert "flashes" not in content


# --- Sign-in page shell (brief 004 criterion 17) --------------------------------------


@pytest.mark.django_db
def test_login_page_has_exactly_one_h1_reading_welcome_back(client):
    content = client.get(reverse("accounts:login")).content.decode()
    assert content.count("<h1") == 1
    assert re.search(r"<h1[^>]*>\s*Welcome back\s*</h1>", content)


@pytest.mark.django_db
def test_login_page_has_no_shell_chrome(client):
    content = client.get(reverse("accounts:login")).content.decode()
    for hook in ("sidenav", 'class="topbar"', "data-settings", "page-foot"):
        assert hook not in content
    assert "data-theme-toggle" in content, "the colour-mode button is still expected on sign-in"


# --- Templates, partials, DRY (brief 004 criteria 22, 23, 25, 26) ---------------------


INCLUDE_RE = re.compile(r"{%-?\s*include\s+[^%]*?-?%}")


def test_every_include_ends_with_only():
    offenders = []
    for template in _templates():
        for include in INCLUDE_RE.findall(template.read_text(encoding="utf-8")):
            if not re.search(r"only\s*-?%}$", include):
                offenders.append(f"{template.name}: {include}")
    assert not offenders, offenders


def test_no_inline_style_attributes_in_templates():
    offenders = [
        template.name
        for template in _templates()
        if re.search(r'\bstyle="', template.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


def test_no_hardcoded_paths_in_href_or_action_attributes():
    """Criterion 22: every URL is {% url %}, so no template hard-codes an absolute path.

    In the *source* (before rendering), a {% url %} or {% static %} tag reads as
    literal template-tag text, not a leading "/", so this only catches an actual
    hard-coded path. In-page "#…" anchors (the sprite, popovers, the skip link,
    the no-JS drawer target) are allowed.
    """
    offenders = []
    for template in _templates():
        text = template.read_text(encoding="utf-8")
        for attr, value in re.findall(r'\b(href|action)="([^"]*)"', text):
            if value.startswith("/"):
                offenders.append(f'{template.name}: {attr}="{value}"')
    assert not offenders, offenders


def _icons_partial_symbols():
    icons_html = (TEMPLATES_DIR / "partials" / "icons.html").read_text(encoding="utf-8")
    return set(re.findall(r'<symbol id="i-([a-z0-9-]+)"', icons_html))


def test_icons_partial_holds_the_only_symbol_elements():
    offenders = [
        template.name
        for template in _templates()
        if template.name != "icons.html" and "<symbol" in template.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


def test_every_icon_use_references_a_defined_symbol_and_every_symbol_is_used():
    symbols = _icons_partial_symbols()
    assert symbols, "icons.html defines no symbols"
    used = set()
    for template in _templates():
        text = template.read_text(encoding="utf-8")
        for name in re.findall(r'<use href="#i-([a-z0-9-]+)"', text):
            assert name in symbols, f"{template.name} references undefined symbol i-{name}"
            used.add(name)
    assert used == symbols, f"symbols defined but never used: {symbols - used}"


@pytest.mark.django_db
def test_icon_sprite_appears_exactly_once_on_rendered_pages(client):
    _signed_in(client)
    home = client.get(reverse("core:home")).content.decode()
    # A signed-in client redirects away from login (redirect_authenticated_user=True),
    # so this needs its own anonymous client.
    login = Client().get(reverse("accounts:login")).content.decode()
    assert home.count('class="sprite"') == 1
    assert login.count('class="sprite"') == 1


def _css_text():
    return (settings.BASE_DIR / "static" / "css" / "style.css").read_text(encoding="utf-8")


def _first_root_block(css):
    """The first `:root { … }` rule (the 1a palette block), and everything else.

    CSS custom properties don't nest braces, so the first `}` after the first
    `:root {` closes it. This is deliberately narrower than "all of section 1":
    the dark-mode block (1d) and the three [data-nav-tone] blocks (1e) are also
    `:root[...]` rules that must contain *no* literals, only `var(--…)`.
    """
    match = re.search(r":root\s*\{[^}]*\}", css)
    assert match, "no :root block found in style.css"
    palette = match.group(0)
    rest = css[: match.start()] + css[match.end() :]
    return palette, rest


COLOUR_LITERAL_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(|hsla?\(")


def test_css_colour_literals_live_only_in_the_root_palette_block():
    """Criterion 25: every hex/rgb(a)/hsl(a) literal sits in the first :root block.

    The dark-mode block and the three [data-nav-tone] blocks (also :root[...]
    rules) must only map tokens to var(--…), never repeat a literal.
    """
    css = _css_text()
    palette, rest = _first_root_block(css)
    assert COLOUR_LITERAL_RE.search(palette), "expected colour literals inside the palette block"
    offenders = COLOUR_LITERAL_RE.findall(rest)
    assert not offenders, f"colour literals found outside the palette block: {offenders}"


# The only prefixes allowed to end in a bare "-<digits>" step: the colour scales
# (white/grey/crest/green/amber/red/blue, from the palette block) and the two
# ordinal, non-colour scales already in the CSS (--space-1..8, --c-surface-2).
# Anything else ending in digits (--fs-14, --icon-16, ...) is a value baked into
# the name, which criterion 25 forbids.
ALLOWED_DIGIT_SUFFIX_PREFIXES = {
    "white",
    "clear",
    "grey",
    "crest",
    "green",
    "amber",
    "red",
    "blue",
    "space",
    "c-surface",
}


def test_css_custom_property_names_do_not_encode_their_value():
    """Criterion 25: no token name matches px/rem, digits-dash-digits, or a bare value suffix.

    Numeric colour-scale steps (--crest-600) and the --space-N / --c-surface-2
    ordinal scales are allowed; any other "-<digits>" ending is rejected.
    """
    css = _css_text()
    names = set(re.findall(r"--([a-z0-9-]+)\s*:", css))
    bad = []
    for name in names:
        if re.search(r"(px|rem)$", name):
            bad.append(name)
        elif re.search(r"\d+-\d+", name):
            bad.append(name)
        else:
            suffix_match = re.match(r"^(.+)-\d+$", name)
            if suffix_match and suffix_match.group(1) not in ALLOWED_DIGIT_SUFFIX_PREFIXES:
                bad.append(name)
    assert not bad, bad


def test_css_font_sizes_are_rem_and_the_root_size_is_never_set():
    """Criterion 26: no px font-size in style.css, and html {font-size} is never declared."""
    css = _css_text()
    declarations = re.findall(r"font-size:\s*([^;]+);", css)
    assert declarations, "expected at least one font-size declaration"
    assert all("px" not in decl for decl in declarations), declarations
    assert not re.search(r"html\s*{[^}]*font-size", css, re.S)


# --- Top-bar placeholders (brief 004 criteria 37, 38; D12, D15, D17) ------------------


@pytest.mark.django_db
def test_home_page_has_no_form_other_than_sign_out(client):
    """Criterion 37: the search placeholder is deliberately not a form.

    Nothing else on the page should submit either.
    """
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    forms = re.findall(r"<form\b[^>]*>", content)
    assert len(forms) == 1
    assert reverse("accounts:logout") in forms[0]


@pytest.mark.django_db
def test_search_placeholder_field_is_readonly_and_described(client):
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    field = re.search(r'<input[^>]*id="top-search"[^>]*>', content)
    assert field, "the search placeholder input is missing"
    tag = field.group(0)
    assert 'type="search"' in tag
    assert "readonly" in tag
    assert 'aria-disabled="true"' in tag
    assert 'placeholder="Search is coming soon"' in tag
    assert 'aria-describedby="top-search-note"' in tag
    assert '<label class="visually-hidden" for="top-search">Search</label>' in content
    assert re.search(
        r'<span class="visually-hidden" id="top-search-note">Search is coming soon\.</span>',
        content,
    )


def test_old_search_copy_appears_nowhere_in_templates():
    """D17: the old wording is replaced by 'Search is coming soon' everywhere in templates/."""
    offenders = [
        template.name
        for template in _templates()
        if "Search arrives with the first section" in template.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


@pytest.mark.django_db
def test_notifications_bell_has_no_badge_and_says_none_yet(client):
    _signed_in(client)
    content = client.get(reverse("core:home")).content.decode()
    blocks = re.findall(r'<details class="pop" data-pop>.*?</details>', content, re.S)
    bell = next((block for block in blocks if "#i-bell" in block), None)
    assert bell, "no bell dropdown found"
    assert "Notifications, none yet" in bell
    assert "count" not in bell, "the bell must carry no count badge or dot"
    assert re.search(r"<p class=\"pop__head\">Notifications</p>", bell)
    assert "No notifications yet." in bell
    panel = re.search(r'<div class="pop__panel">.*?</div>\s*</details>', bell, re.S).group(0)
    assert "<a " not in panel
    assert "<li" not in panel


# --- Model (brief 004 criterion 33) is covered in apps/accounts/tests.py -------------
