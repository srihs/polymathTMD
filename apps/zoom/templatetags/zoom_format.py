"""Date and time filters for Zoom pages: ``{% load zoom_format %}``.

The formats (``Mon 5 Oct 2026``, ``8:30 am``) are defined once, in ``apps.zoom.models``
(``class_date`` / ``class_time``), and used by ``schedule_summary``, ``Occurrence.__str__`` and
the emails. These filters call the same functions, so a template can't drift from them.
Aware datetimes are shown in ``TIME_ZONE`` (Colombo).
"""

from django import template

from apps.zoom import models

register = template.Library()


@register.filter(expects_localtime=True)
def class_date(value):
    """``{{ occurrence.starts_at|class_date }}`` → ``Mon 5 Oct 2026``."""
    return models.class_date(value)


@register.filter(expects_localtime=True)
def class_time(value):
    """``{{ occurrence.starts_at|class_time }}`` → ``8:30 am``."""
    return models.class_time(value)
