"""Project-wide template context.

Only values that genuinely belong on every page live here (CLAUDE.md: no context
processors for page-specific data).
"""

from django.conf import settings


def site(request):
    """Expose ``settings.SITE_NAME`` to every template as ``tmd_site_name``.

    The key carries a project prefix on purpose. A view's own context overrides a
    context processor's keys, and Django's auth views (``LoginView`` today, the
    password-reset views and their emails later) put ``site_name`` into their
    context from ``get_current_site()``. Without ``django.contrib.sites`` that is a
    ``RequestSite`` named after the request host, so a plain ``site_name`` key made
    the login page title read "Sign in · 127.0.0.1:8010". A prefixed key can't
    collide with Django's names (``site``, ``site_name``, admin's ``site_title`` /
    ``site_header``), which keeps ``settings.SITE_NAME`` the single source without
    patching each view.
    """
    return {"tmd_site_name": settings.SITE_NAME}
