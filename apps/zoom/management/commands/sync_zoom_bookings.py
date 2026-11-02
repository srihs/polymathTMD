"""Check every booking with classes still to come against Zoom (brief 013, criterion 19, D6).

The nightly backstop for a webhook event that never arrived: the server was down past Zoom's
three retries, or a connection has no webhook secret yet. It runs the same
``services.reconcile()`` as the webhook and the ``Check against Zoom`` button, on every
approved booking with a remaining class on a connected account, so the rules and the emails
are the same whichever way a change is found.

It prints one line per booking that changed, needs a look or couldn't be checked (Design D.6),
then the summary, and exits 1 if any booking couldn't be checked, so a scheduled task can
alert. Lines carry references, account labels and counts only: never a class name, an email
address, a link or a token, because this output ends up in a scheduler's log.

Each booking is checked on its own (criterion 19, review round 1, N3): an unexpected error
in one is logged once at ``ERROR`` (reference and exception class), printed as that
booking's couldn't-be-checked line and counted, and the run goes on, so one bad booking can't
leave every later one unchecked for the night.

It also clears the "needs a look" flag of approved bookings that have no class left to come
(criterion 28), in one ``UPDATE``, silently: nothing could ever clear those flags otherwise.
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.zoom import services
from apps.zoom.models import LinkRequest, ZoomEvent
from apps.zoom.providers import get_provider

logger = logging.getLogger(__name__)

# Criterion 19 and Design D.6.
SUMMARY = "Checked {n} booking{n_s}: {c} changed, {a} need{a_s} a look, {f} couldn't be checked."
COULD_NOT_CHECK = "{reference} ({label}): couldn't be checked: {reason}"
# Criterion 19's extra lines (D15, D18): a lock race is no Zoom error, so it has a reason
# sentence of its own; an unexpected error is named by its exception class.
LOCK_RACE_REASON = "Someone else was changing this booking at the same moment."
ERROR_REASON = "{name}."
CANT_REACH_ZOOM = "This system can't reach Zoom, so no bookings were checked."


def _plural(n, many="s", one=""):
    return one if n == 1 else many


def booking_line(result) -> str | None:
    """Design D.6's line for one reconciled booking, or ``None`` when nothing happened.

    The copied part names the cancelled classes before the moved ones, and leaves either out
    when it's 0. Then what needs a look ("still needs a look" when the sentences were already
    known, so no new email went), then who was emailed, then which email didn't send.
    """
    link_request = result.link_request
    cancelled, moved = len(result.cancelled), len(result.moved)
    copied = cancelled + moved
    if not copied and not result.needs_a_look:
        return None

    parts = []
    if cancelled:
        parts.append(f"{cancelled} class{_plural(cancelled, 'es')} cancelled")
    if moved:
        noun = "" if cancelled else f" class{_plural(moved, 'es')}"
        parts.append(f"{moved}{noun} moved")
    head = ", ".join(parts)
    if result.needs_a_look:
        look = "needs a look" if result.attention_changed else "still needs a look"
        head = f"{head}, and {look}" if head else look

    told = []
    if copied and result.emailed:
        told.append("the requester")
    if result.attention_changed and result.it_emailed:
        told.append("the IT desk")
    tail = []
    if told:
        tail.append(f"Emailed {' and '.join(told)}.")
    if copied and not result.emailed:
        tail.append("The email to the requester didn't send.")
    if result.attention_changed and not result.it_emailed:
        tail.append("The email to the IT desk didn't send.")
    if not tail:
        tail.append("No new email.")
    label = link_request.host_account.label
    return f"{link_request.reference} ({label}): {head}. {' '.join(tail)}"


class Command(BaseCommand):
    help = "Check every booking with classes still to come against Zoom, and copy what changed."

    def handle(self, *args, **options):
        now = timezone.now()
        LinkRequest.objects.clear_stale_attention(now)  # criterion 28's sweep, silent
        provider = get_provider()
        if not provider.checks_zoom:
            self.stdout.write(CANT_REACH_ZOOM)
            return

        bookings = [
            link_request
            for link_request in LinkRequest.objects.with_remaining_classes(now)
            .select_related("host_account")
            .order_by("pk")
            if provider.is_connected(link_request.host_account)
        ]
        changed = look = failed = 0
        for link_request in bookings:
            reason = None
            try:
                result = services.reconcile(link_request, provider=provider)
            except Exception as exc:  # N3: one booking's failure never stops the run
                logger.error(
                    "Checking %s with Zoom failed: %s", link_request.reference, type(exc).__name__
                )
                reason = ERROR_REASON.format(name=type(exc).__name__)
            else:
                if result.outcome == services.PROVIDER_FAILED:
                    reason = result.error.reason_sentence
                elif result.outcome == services.LOCK_RACE:
                    reason = LOCK_RACE_REASON
            if reason is not None:
                failed += 1
                self.stdout.write(
                    COULD_NOT_CHECK.format(
                        reference=link_request.reference,
                        label=link_request.host_account.label,
                        reason=reason,
                    )
                )
                continue
            if result.outcome == services.NOT_ASKED:
                continue  # its last class began after the list was read: nothing to check
            changed += result.outcome == ZoomEvent.Outcome.CHANGED
            look += result.needs_a_look
            line = booking_line(result)
            if line:
                self.stdout.write(line)

        n = len(bookings)
        self.stdout.write(
            SUMMARY.format(
                n=n,
                n_s=_plural(n),
                c=changed,
                a=look,
                a_s=_plural(look, "", "s"),
                f=failed,
            )
        )
        if failed:
            raise CommandError(
                f"{failed} booking{_plural(failed)} couldn't be checked.", returncode=1
            )
