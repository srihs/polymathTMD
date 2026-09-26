"""Check the Zoom connection of every active paid account (brief 006, criterion 37, D12).

For scripted checks after setting up or rotating a credential, and for the go-live gate: it
runs the same check as the "Check connection" button (``services.check_connection``), always
against the live Zoom API whatever ``ZOOM_PROVIDER`` says, and prints one line per account.

Anything but a clean "works" counts as a failure, including a Basic (free) Zoom user on a
paid account, whose meetings would end after 40 minutes; the exit status is then 1. Lines
carry account labels, emails and connection names only, never a secret, a token or an
account ID.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.zoom import services
from apps.zoom.models import HostAccount


class Command(BaseCommand):
    help = "Check the Zoom connection of every active paid Zoom account."

    def handle(self, *args, **options):
        failed = 0
        for account in HostAccount.objects.bookable():  # Meta.ordering: order, then name
            result = services.check_connection(account)
            if result.works:
                self.stdout.write(f"{account.label}: works")
            else:
                failed += 1
                self.stdout.write(f"{account.label}: {result.message}")
        if failed:
            raise CommandError(
                f"{failed} Zoom account{'' if failed == 1 else 's'} failed the check.",
                returncode=1,
            )
