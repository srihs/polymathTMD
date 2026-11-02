"""How a booking differs from its meeting as Zoom holds it now (brief 013, criterion 14).

Pure: these functions read the classes and the ``MeetingState`` they're given, and never the
database or the network, so ``services.reconcile()`` can run them on the rows it has just
locked and each rule can be tested on its own. The same split as ``timetable.py``.

Matching a stored class to one of Zoom's classes:

1. **A one-off booking whose Zoom meeting is still one meeting** is paired with it whatever
   its time: "the single meeting for a one-off".
2. Otherwise **by Zoom occurrence ID**. Zoom keeps a class's ID when that class alone is
   moved, so a class moved in Zoom is still found.
3. A class whose ID Zoom doesn't have (or that has none stored: a booking made before the live
   connection) is then **matched by its start**, unless Zoom lists that ID as deleted.

What each unmatched or changed class means:

- the meeting is gone (``state is None``): every remaining class is cancelled;
- a remaining class Zoom lists as deleted is cancelled;
- a remaining class Zoom doesn't have at all is cancelled too ("missing"), **unless** Zoom has
  classes from now on that match nothing here. Then the series was probably rebuilt in Zoom
  (new IDs at new times), so cancelling would throw away classes that still exist under
  another ID: nothing is cancelled, and Zoom's unmatched classes are named for IT instead.
  That's the table's "nothing is changed; a needs-a-look sentence is added" row;
- a remaining class Zoom has at another start or length is a move, which the caller copies
  only if the account is free then.

Only **remaining** classes (booked, not started) are ever changed. Held classes still claim
their Zoom class, so they're never reported as extra, and cancelled classes claim nothing.
"""

from dataclasses import dataclass, field

from .models import LinkRequest


@dataclass
class Comparison:
    """What a reconcile should do, before the account is checked for the moves.

    ``cancel``: remaining classes Zoom no longer has. ``moves``: ``(occurrence, ZoomClass)``
    for remaining classes Zoom has at another time. ``extra``: Zoom's classes from now on that
    match no class here, soonest first.
    """

    cancel: list = field(default_factory=list)
    moves: list = field(default_factory=list)
    extra: list = field(default_factory=list)


def _pair(link_request, booked, state) -> tuple[dict, set]:
    """``({occurrence pk: ZoomClass}, {claimed index})``, by the rules in the module docstring."""
    zoom = list(state.classes)
    pairs, claimed = {}, set()
    if (
        link_request.repeat != LinkRequest.Repeat.WEEKLY
        and not state.recurring
        and len(zoom) == 1
        and len(booked) == 1
    ):
        return {booked[0].pk: zoom[0]}, {0}

    by_id = {}
    for index, item in enumerate(zoom):
        if item.occurrence_id:
            by_id.setdefault(item.occurrence_id, index)
    for occurrence in booked:
        index = by_id.get(occurrence.zoom_occurrence_id) if occurrence.zoom_occurrence_id else None
        if index is not None and index not in claimed:
            pairs[occurrence.pk] = zoom[index]
            claimed.add(index)
    for occurrence in booked:
        if occurrence.pk in pairs or occurrence.zoom_occurrence_id in state.deleted_ids:
            continue
        for index, item in enumerate(zoom):
            if index not in claimed and item.starts_at == occurrence.starts_at:
                pairs[occurrence.pk] = item
                claimed.add(index)
                break
    return pairs, claimed


def compare(link_request, classes, state, now) -> Comparison:
    """Criterion 14's table for one booking: ``state`` is ``None`` when the meeting is gone.

    ``classes`` is every class of the booking (the locked rows), soonest first.
    """
    remaining = link_request.remaining_classes(now, occurrences=classes)
    if state is None:
        return Comparison(cancel=list(remaining))

    booked = [occurrence for occurrence in classes if occurrence.is_booked()]
    pairs, claimed = _pair(link_request, booked, state)
    extra = [
        item
        for index, item in enumerate(state.classes)
        if index not in claimed and item.starts_at > now
    ]

    result = Comparison(extra=sorted(extra))
    for occurrence in remaining:
        found = pairs.get(occurrence.pk)
        if found is None:
            deleted = bool(occurrence.zoom_occurrence_id) and (
                occurrence.zoom_occurrence_id in state.deleted_ids
            )
            if deleted or not extra:
                result.cancel.append(occurrence)
        elif (found.starts_at, found.ends_at) != (occurrence.starts_at, occurrence.ends_at):
            result.moves.append((occurrence, found))
    return result
