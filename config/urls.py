"""Project URLconf: one namespaced include per app.

There's no ``admin/`` route: django.contrib.admin was removed in task 010 (D10), so
``/admin/`` is a 404. Refusals render ``templates/403.html`` through Django's default
``handler403``, so no handler is set here.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("zoom/", include("apps.zoom.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
