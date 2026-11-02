"""Re-encrypt every stored secret with the first key in HOST_KEY_ENCRYPTION_KEYS (brief 015, D4).

Step 3 of key rotation: put the new key first, restart, run this, then remove the old key and
restart. It replaces brief 005's ``rotate_host_keys``, because the same keys now also protect
each Zoom connection's Client Secret and webhook secret. One command for all of them is the
point: rotation ends by removing the old key, and with two commands, forgetting the second
would leave every Zoom connection unreadable and stop every booking at once (risk R2).

So it re-encrypts every host key, every client secret and every webhook secret in **one
transaction**, with the rows locked. Re-encrypting isn't a change of secret, so no
``*_changed_at`` / ``*_changed_by`` and no ``credentials_version`` moves (the cached tokens
stay valid): only the encrypted columns are saved.

A value no configured key can read is named on stderr (an account label or a connection
name, never a value) and the command exits 1, so a rotation script stops before the old key
is removed. Everything readable is still re-encrypted: the unreadable values are lost either
way, and must be typed again on their pages.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.zoom.models import HostAccount, SecretUnreadable, ZoomConnection

DONE = "Re-encrypted {n} host key{n_s} and {m} Zoom connection secret{m_s}."
UNREADABLE = (
    "Couldn't read: {items}. Type those again on the Zoom accounts and Zoom connections pages."
)


def _plural(count) -> str:
    return "" if count == 1 else "s"


class Command(BaseCommand):
    help = (
        "Re-encrypt every saved Zoom host key and Zoom connection secret with the first "
        "HOST_KEY_ENCRYPTION_KEYS key."
    )

    def handle(self, *args, **options):
        host_keys = secrets = 0
        unreadable = []
        with transaction.atomic():
            for account in HostAccount.objects.select_for_update().exclude(host_key_encrypted=""):
                try:
                    account.rotate_host_key()
                except SecretUnreadable:
                    unreadable.append(f"the host key of {account.label}")
                    continue
                account.save(update_fields=["host_key_encrypted"])
                host_keys += 1
            for connection in ZoomConnection.objects.select_for_update():
                try:
                    secrets += connection.rotate_secrets()
                except SecretUnreadable as exc:
                    secrets += exc.rotated
                    # ``exc.args`` already names each secret ("client secret", ...).
                    unreadable += [f"the {name} of {connection.slug}" for name in exc.args]
                connection.save(
                    update_fields=["client_secret_encrypted", "webhook_secret_encrypted"]
                )
        self.stdout.write(
            DONE.format(n=host_keys, n_s=_plural(host_keys), m=secrets, m_s=_plural(secrets))
        )
        if unreadable:
            self.stderr.write(UNREADABLE.format(items="; ".join(unreadable)))
            raise CommandError("Some stored secrets couldn't be read.", returncode=1)
