"""App config for Zoom link requests (brief 005).

The system checks are registered here, explicitly, rather than by importing a module for its
side effects: ``ready()`` is the one place Django guarantees runs once per process.
"""

from django.apps import AppConfig
from django.core import checks


class ZoomConfig(AppConfig):
    name = "apps.zoom"
    label = "zoom"
    verbose_name = "Zoom links"

    def ready(self):
        from . import checks as zoom_checks

        checks.register(zoom_checks.check_provider_setting)
        checks.register(zoom_checks.check_host_key_encryption_keys)
        checks.register(zoom_checks.check_credential_sets)
        checks.register(zoom_checks.check_it_desk_phone)
        checks.register(
            zoom_checks.check_fake_provider_not_deployed, checks.Tags.security, deploy=True
        )
        checks.register(
            zoom_checks.check_manual_provider_not_deployed, checks.Tags.security, deploy=True
        )
        checks.register(zoom_checks.check_accounts_connected, checks.Tags.database)
