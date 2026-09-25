"""Re-encrypt every saved Zoom host key with the first key in HOST_KEY_ENCRYPTION_KEYS.

Step 3 of key rotation (brief 005, D17): put the new key first, restart, run this, then
remove the old key and restart. It prints counts and account labels only, never a key.
Re-encrypting isn't a change of key, so ``host_key_changed_at`` / ``_by`` stay as they were
(brief 008, criterion 21): only ``host_key_encrypted`` is saved.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.zoom.models import HostAccount, HostKeyUnreadable


class Command(BaseCommand):
    help = "Re-encrypt every saved Zoom host key with the first HOST_KEY_ENCRYPTION_KEYS key."

    def handle(self, *args, **options):
        rotated = 0
        unreadable = []
        with transaction.atomic():
            for account in HostAccount.objects.select_for_update().exclude(host_key_encrypted=""):
                try:
                    account.rotate_host_key()
                except HostKeyUnreadable:
                    unreadable.append(account.label)
                    continue
                account.save(update_fields=["host_key_encrypted"])
                rotated += 1
        self.stdout.write(f"Re-encrypted {rotated} host key{'' if rotated == 1 else 's'}.")
        if unreadable:
            self.stderr.write(
                "Couldn't read the host key of: "
                + ", ".join(unreadable)
                + ". Type those keys again on the Zoom accounts page."
            )
