# 012 — Move a class, or change the time of a booking's remaining classes

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Planned <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

The owner's words (2026-09-26):

> so what we need is zoom to linked via api or anyither means and create/cancel meetings via the app without user has to login to zoom app. This application will be the interface for zoom. Research on how to do this and ask questions if you have to.

The owner's scope answer (2026-09-26, relayed): "reschedule a booking (one class or the series)", along with cancel, webhook sync and recording links. Brief 011 has the full answers and the four-brief split.

**Reading.** IT can move an approved class to another date or time, or change the time of every class still to come in a weekly booking, from the request's page, without signing in to Zoom. The move stays on the same Zoom account and the same meeting, so the join link and the start link don't change. The new time must pass exactly the checks an approval passes:

- no booked class on that account overlaps it in the database;
- Zoom shows no other meeting on that account at that time;
- the same locks and the 5-minute slot backstop apply.

Zoom is changed through `PATCH /meetings/{id}`, and the requester is emailed the old and new times.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**Place in the split** (brief 011, Scope): second, after 011 and before 013. It's not a go-live gate item.

**In scope**

- **Model** (migration `0008`):
  - `Occurrence.moved_at` and `moved_by`;
  - the move rules on the model;
  - a series move also updates the request's `start_time` and `end_time`, so `schedule_summary` stays true.
- **Provider:** `update_occurrence()` and `update_series()` (`PATCH`), plus reading a series back (already in `busy_times`' `GET`).
- **Services:** `move_class()`, `move_series()`, and the "classes moved" email.
- **Screens:**
  - `Move this class` (for any movable class, one-off or weekly);
  - `Change the time of the remaining classes` (weekly);
  - the detail page's `Moved` markers.
- **Zoom scope:** `meeting:update:meeting:admin`, added to each account's app (setup steps in D8).
- **Zoom's update limits** get their own message (criterion 14).

**Out of scope**

- **Moving a booking to another account** (owner, Q5: "No, refuse the move"; D11). That means a new meeting and a new join link, so it's re-approval, not a move.
- **Changing the weekdays or the dates of a series** (owner, Q4: "Time of day only"; D10).
- Moving a class that has started. A series move while a class is in progress.
- Moving a waiting request (the requester sends a new one, as today).
- Changes made in Zoom (013).

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- These carry over from briefs 005, 006 and 011:
  - the frozen now, Mon 28 Sep 2026, 10:00;
  - ZL-0042 (weekly, Mon and Wed, 5–28 Oct, 8:30–11:30, Zoom 02, meeting `81234567890`) and ZL-0043 (one-off);
  - mocked Zoom and the network block;
  - "booked", "started" and "in progress";
  - the pinned-copy rule.
- **Movable class:** booked, not cancelled and not started. **Remaining classes:** a booking's movable classes.

### Model

1. **Fields** (migration `0008`, reversible): `Occurrence.moved_at` (null) and `moved_by` (FK to the user, `PROTECT`, null, `related_name="+"`). They're set on every class a move changes.
2. **Rules on the model**, with pinned errors:
   - `Occurrence.move_errors(*, starts_at, ends_at, now=None) -> dict` reuses 005's rules and copy: `TIME_STEP`, `END_BEFORE_START`, `DATE_PASSED` and `DATE_TOO_FAR`. The end must be on the same day as the start. It adds:
     - started: `That class has already started, so it can't be moved.`;
     - unchanged: `That's the time it's already booked for. Choose a different time.`
   - `LinkRequest.series_move_errors(*, start_time, end_time, now=None) -> dict` applies the time rules to every remaining class, and adds:
     - a class in progress: `{class} is in progress. Change the time of the remaining classes after it ends at {end time}.`;
     - none remaining: `There are no classes left to change in this booking.`;
     - unchanged: as above.

   These are unit-tested without views.
3. **What a move writes:**
   - The moved classes get their new `starts_at`/`ends_at`, `moved_at` and `moved_by`.
   - Their old `HostSlot` rows are replaced by rows for the new times.
   - A **series** move also sets `LinkRequest.start_time`/`end_time` to the new times.
   - A **one-class** move leaves the request's fields alone. The Classes list is the record, and the moved class shows `Moved`.
   - Cancelled and held classes are never touched.

### Screens

4. **URLs and access.**
   - `zoom:move_class` (pk, occurrence pk) and `zoom:move_series` (pk). Both are GET (the form) and POST.
   - Both need `zoom.review_linkrequest` (brief 011 D7; the permission's name already says "reschedule").
   - They're 404 for: a request that isn't approved, a class that isn't the request's, and `move_series` on a one-off booking.
   - A class that isn't movable, or a series with none remaining or one in progress, redirects (302) to the detail with criterion 2's message as an error, and makes no Zoom call.
5. **The forms.**
   - `move_class` has `Date of the class`, `Starts at` and `Ends at`, filled in with the class's current values. Their help follows the request form's (5-minute steps, Sri Lanka time).
   - `move_series` has `Starts at` and `Ends at`, filled in with the current times. Its lead is `The new time applies to every class still to come: {n} classes, from {first date} to {last date}. The days stay the same.`
   - Errors use the error summary and field errors, and keep what was typed.
6. **Detail page.** On an approved booking:
   - each movable class gets `Move this class` (its accessible name includes the date);
   - a weekly booking with remaining classes and no class in progress gets `Change the time of the remaining classes`;
   - a moved class shows the tag `Moved` (icon plus word) and `Moved by {name} on {when}`.

### Clash-safe moving (D2)

7. **What counts as a clash for the new times:**
   - **Database:** any booked class on the booking's account overlapping a new time. That includes this booking's own other classes, but not the classes being moved.
   - **Zoom:** any busy time on that account overlapping a new time, **except**:
     - meetings whose ID is this booking's `meeting_id` (the database check already covers its classes);
     - meetings carrying another approved request's known meeting ID (006 c13, unchanged).

     006's touching rule holds.
   - Tests:
     - moving the Wed 7 Oct class onto Mon 5 Oct 8:30 clashes with the booking's own class;
     - moving it to Wed 7 Oct 11:30–12:30 doesn't (touching);
     - a Zoom-only meeting at the new time clashes;
     - the booking's own meeting in Zoom at the old time doesn't.
8. **Order of work.** An ordered log of a successful one-class move shows:
   1. the Zoom list call(s) for the booking's account, **fresh**, spanning the new times, before any lock;
   2. the locking reads (`zoom_linkrequest`, `zoom_hostaccount`, `zoom_occurrence`) and the locking clash re-check;
   3. the slot `DELETE` and `INSERT` and the occurrence `UPDATE`;
   4. exactly one `PATCH`;
   5. the commit.

   A series move adds, after the `PATCH`, the occurrence deletes of criterion 10 and one `GET /meetings/{id}`, all before the commit.
9. **Clash messages** (the form re-renders, keeping the typed values; nothing changes, and nothing is sent to Zoom after the list):

   | Case | Status | Message (pinned) |
   |---|---|---|
   | Zoom meeting at the new time | 409 | `{label} has a meeting in Zoom at that time: {topic}, {Mon 5 Oct 2026} at {8:00 am}. Choose another time.` (topic through `display_topic`) |
   | booked class at the new time (preview or locked re-check) | 409 | `{label} already has {reference} {class_name} at that time. Choose another time.` |
   | the slot backstop fired | 409 | `{label} was booked at that time a moment ago. Choose another time.` |
   | the account isn't connected | 409 | `{label} isn't connected to Zoom, so this class can't be moved here. Set up its Zoom connection on the Zoom accounts page.` |
   | Zoom couldn't be asked | 200 | `We couldn't check {label}'s meetings in Zoom, so nothing was changed. {Reason sentence} {next step}`, with 006's temporary next step or `Ask whoever manages the Zoom accounts to press Check connection for {label}.` |

### What is sent to Zoom

10. **The calls.** Bodies carry only `start_time` (Colombo local, `%Y-%m-%dT%H:%M:%S`), `timezone`, `duration` and, for a series, `recurrence`. They never carry `settings`, `topic` or `agenda` (006 D19; a test asserts the keys).

    | Move | Call |
    |---|---|
    | one class of a weekly booking | `PATCH /meetings/{id}?occurrence_id={zoom_occurrence_id}`. A blank ID is looked up first with 011's `occurrence_id_for` |
    | the one-off booking's class | `PATCH /meetings/{id}` |
    | the remaining classes of a series | `PATCH /meetings/{id}`, starting at the first remaining class at its new time, with `recurrence` `{type 2, repeat_interval 1, weekly_days (unchanged), end_times or end_date_time}` covering the last remaining date. Then `DELETE ?occurrence_id=` for each date in that span whose class was **cancelled** (011), so Zoom doesn't bring it back. Then `GET /meetings/{id}` |

    The backend confirms in Zoom's docs and records in its notes (https://developers.zoom.us/docs/api/meetings/):
    - whether an occurrence-level `PATCH` may change the date as well as the time. If it can't, that's a blocker to report, not a workaround;
    - whether the `occurrence_id` survives an occurrence-level `PATCH`. If it doesn't, the class's new ID is read back with a `GET`.
11. **A series must come back exactly right.** After the series `PATCH` and deletes, Zoom's non-deleted occurrences starting from the first remaining class must equal the remaining, non-cancelled classes at their new times, one to one. Their new `occurrence_id`s are stored.
    - If they differ: the database transaction rolls back, and **one** compensating `PATCH` restores the old series, with the old start, duration and recurrence. The form re-renders with `Zoom scheduled different dates from these classes, so nothing was changed. Tell whoever looks after the system.`
    - If the restore fails too: `Zoom now has {label}'s meeting {meeting_id} at the new time, but it couldn't be saved here or put back. Tell whoever looks after the system.`, plus one `ERROR` log line with the reference, the meeting ID and the error class.
12. **Zoom refused, for certain** (connection error, connect timeout, 429, any 4xx): everything is rolled back, and the form re-renders (200) with `We couldn't move it in Zoom: {phrase}. Nothing was changed. {next step}`.
    - `ZoomMissingScope` gets its own text: `The Zoom app for {label} is missing the permission to change meetings. Nothing was changed. Ask whoever looks after the server to add the scopes listed in the README.`
13. **Zoom may have done it** (`maybe_done`). After the rollback, one best-effort `PATCH` puts back the old values; setting the old time again is safe whatever Zoom did. The message is one of:
    - restore worked: `No answer from Zoom, so we put the class back to its old time there to be safe. Nothing was changed. Try again in a few minutes.`
    - restore failed: `No answer from Zoom, and we couldn't check what it did. Nothing was changed here. Try again in a few minutes. If the class shows the new time in Zoom, trying again finishes the move.`
14. **Zoom's update limits** (research: 100 updates per meeting per day, and 100 creates or updates per user per day, reset at UTC midnight).
    - The backend confirms from Zoom's docs how a daily-limit `429` is told apart from a per-second one (a response code or header), and records it.
    - A daily-limit answer raises the new lasting error `ZoomDailyLimit`, with the message `Zoom's daily limit for changing {label}'s meetings is used up. Nothing was changed. Try again after 5:30 am.`
    - If the two can't be told apart, every `429` stays `ZoomBusy`, and the README notes the limit.
15. **Saving fails after Zoom changed it.** A MySQL deadlock is retried once; repeating the `PATCH` is harmless. Any other failure gets a compensating `PATCH` back to the old values after the rollback, and the failure's normal message. If that restore fails, criterion 11's "couldn't be saved here or put back" message and log line apply.
16. **Success.** The view redirects (302) to the detail with:
    - `Moved the class to {Tue 6 Oct 2026, 9:00 am to 12:00 pm}. We emailed {email}.`, or
    - `Changed the time of {n} classes to {9:00 am to 12:00 pm}. We emailed {email}.`
    - If the email failed: the warning `Moved, but the email to {email} didn't send. Tell them the new times yourself.`
    - With `manual`: no Zoom call is made, the form shows 006's manual notice (`This system can't see meetings made directly in Zoom. …`), and the success message adds ` This system can't reach Zoom: change it in Zoom too.`
17. **Races** (thread tests; flaky means FAIL):
    - **(a)** Two moves of the same class: exactly one `PATCH` commits its time. The other gets the clash or the "already moved" state after the lock, and its compensating `PATCH` (if any) restores the winner's time, not the old one.
    - **(b)** A move and an approval of another request into the same new time on the same account: exactly one wins, and no two booked classes overlap.
    - **(c)** A move and a cancel (011) of the same class: the final state is either cancelled, or moved and not cancelled. At most one email per committed action. The loser redirects with `That class was cancelled.` or proceeds on the moved class.
18. **The email** goes to the requester only, after the commit.
    - **Subject:** `Class times changed: {reference} {class_name}`.
    - **Body:** one `Was: {old} / Now: {new}` pair per moved class, then `Your Zoom link and start link stay the same. The start link follows the new times.`
    - It contains no join link, passcode, start link or host key.
19. **The start link follows.** After Wed 7 Oct moves to Thu 8 Oct 9:00–12:00, 011's `start_state` is `ready` at Thu 8 Oct 8:30 and not at Wed 7 Oct 8:00.

### Rules, security, verification

20. **Scopes.** The README's scope list gains `meeting:update:meeting:admin`, with https://developers.zoom.us/docs/integrations/oauth-scopes-granular/. `Check connection` stays as it is (D6).
21. **Thin views.** The rules are on the models (criterion 2), and the Zoom work and transactions are in `services`.
22. **Template rules, no-JS, layout and accessibility** as in 011 criterion 35. The two forms use the busy button (`Moving the class in Zoom…`).
23. **No test reaches the network.** `FakeProvider` gains steerable update errors and a `patched` record.
24. **Automated checks:** as in 011 criterion 37.
25. **Prod walkthrough** (`ZOOM_PROVIDER=manual`, 8010):
    - move one class of a test booking;
    - change a series' time;
    - try a clashing time against another test booking and see the 409 message;
    - check static files.

    Screenshots at 1440 and 400: both forms, the clash error, and the detail's `Moved` markers.
26. **The owner's live check:**
    1. Move one class of a live 2-week booking, and check the occurrence in Zoom.
    2. Change the series time, and check every remaining occurrence, and that a class cancelled earlier (011) hasn't come back.
    3. The join link and meeting ID are unchanged.
    4. The start link opens only in the new window.
    5. Try a time that overlaps a meeting made directly in Zoom: it's refused.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q4 and Q5 on 2026-09-26 (there is no Q3 in briefs 011–014; see 011's note).

| Q | Question (short) | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| Q4 | What can a series move change? | The time of day only | **"Time of day only"** | D10 |
| Q5 | If the booking's own account is busy at the new time, offer another account? | No, refuse and name the clash | **"No, refuse the move"** | D11 |

**Decisions (the planner's)**

- **D1: Same account, same meeting.** A move never changes `host_account`, `meeting_id` or `join_url`. That's why the links survive, and why a busy account refuses the move (owner, Q5; D11).
- **D2: The same safety as approval** (006 D6, 005 D5):
  - step 1, no locks: a fresh Zoom list for the account over the new times;
  - step 2, one transaction: locks in the order request, account, classes; a locking clash re-check; the slots rewritten (the unique index is still the backstop);
  - step 3: `PATCH` inside the transaction, then the commit.

  **After a failure:** a compensating `PATCH` puts Zoom back. Setting old values again is idempotent, so the uncertain (`maybe_done`) case can be handled truthfully.

  **Why Zoom is changed inside the transaction:** 013's `meeting.updated` webhook then waits for the commit and finds the database already matching (011 D2's reasoning).
- **D3: A series move is one `PATCH` of the series from the first remaining class**, not one `PATCH` per class.
  - **Why:** a 60-class series would use 60 of the account user's 100 daily updates, and the lock would be held through 60 calls.
  - Held classes are history in the app. Zoom only needs the future part, so the series is re-anchored at the first remaining class.
  - Classes cancelled earlier are deleted again straight after (criterion 10), and the result is verified by reading it back (criterion 11), as 006 verified the create.
- **D4: The request's `start_time`/`end_time` follow a series move** (criterion 3). `schedule_summary`, which pages and emails print, then stays true. A one-class move is an exception, shown on its class (`Moved`), so the summary isn't rewritten into something like "every Monday except…".
- **D5: `moved_at` and `moved_by` on the class.** It's the only record of who moved it, since there's no admin log (008 D3's reasoning). 013 leaves `moved_by` empty for moves made in Zoom.
- **D6: `Check connection` isn't extended.** Proving the update scope would mean changing a real meeting. A missing scope shows up on the first move, with its own message (criterion 12), and in the owner's live check.
- **D7: The permission name was already set by 011** (its D8), so there's no migration for it here.
- **D8: Owner setup, per paid account** (for the README):
  1. On marketplace.zoom.us, open the account's `Polymath TMD` Server-to-Server OAuth app, then **Scopes → Add Scopes**, and add `meeting:update:meeting:admin` (Meeting → "Update a meeting").
  2. Save. The app stays activated. No new credentials are needed, and nothing changes on the server.
  3. Tokens made before the change don't carry the new scope. They run out within the hour, so restarting `web` after all 11 apps are updated makes the next call fetch a fresh one at once.
- **D10: A series move changes the time of day only** (owner, Q4: "Time of day only").
  - The weekdays and the dates stay. `MoveSeriesForm` has only `start_time` and `end_time` (criterion 5).
  - Different days, or a longer run, means cancelling the rest (011) and a new request.
  - A shorter run means cancelling the later classes one by one (011).
- **D11: A move never changes account** (owner, Q5: "No, refuse the move").
  - When the booking's account is busy at the new time, the move is refused with criterion 9's message.
  - There's no offer of another account, because that would mean a new meeting and new links (D1).
- **D9: Information architecture.** No new nav. Two verbs on the request detail, each with its own page, and back to the detail:

  ```
  ZL-0042 (zoom:detail)
  ├── Move this class                          zoom:move_class   (per movable class)
  └── Change the time of the remaining classes zoom:move_series  (weekly)
  ```

**Risk register**

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | The series `PATCH` re-creates classes that were cancelled, or shifts held ones | Medium / **High** | Mitigate: delete cancelled dates straight after, verify by reading back, and restore the old series on mismatch (criteria 10 and 11) | the DATES_DIFFER message | backend |
| R2 | An occurrence-level `PATCH` can't change the date, or changes the occurrence ID | Medium / Medium | Confirm in the docs at build time (criterion 10). A blocker is reported, not worked around | the backend's note | backend |
| R3 | Zoom's daily update limits stop moves on a busy day | Low / Low | Mitigate: one `PATCH` per series (D3), and a message saying when to retry (criterion 14) | the daily-limit message | backend |
| R4 | An uncertain `PATCH` plus a failed restore leaves Zoom at the new time and the database at the old one | Low / Medium | Accept, and mitigate: the message tells IT that trying again finishes the move. 013's reconcile would mirror it | the restore-failed message | backend |
| R5 | The update scope isn't added to every account's app | Medium / Low | Mitigate: the README steps (D8), the pinned message, and the owner's live check | criterion 12's scope message | owner |

## MVT plan
<!-- owner: tmd-planner -->

### Models

In `apps/zoom/models.py`. Migration `0008_move_classes`, numbered after 011's `0006`/`0007`; renumber if needed.

- `Occurrence`: `moved_at`, `moved_by`, `move_errors()`, and a small `new_slots()` helper that reuses `HostSlot.covering`.
- `LinkRequest`: `series_move_errors()`. "Remaining classes" (booked, not started) is exactly 011's `cancellable_classes(now)`. **One definition only:** the backend renames it to `remaining_classes(now)`, updates 011's callers, and records the rename.
- The copy constants for criterion 2 go beside them.

**Provider** (`providers.py`):

| Member | Fake | Manual | Zoom |
|---|---|---|---|
| `update_occurrence(*, host_account, meeting_id, occurrence_id=None, starts_at, ends_at)` | records in `patched`; `update_error` steerable | no-op | `PATCH` per criterion 10 |
| `update_series(*, host_account, meeting_id, link_request, classes, weekdays) -> Meeting` (with `occurrence_ids`) | records, returns fake IDs | no-op | `PATCH`, then the deletes of the cancelled dates, then `GET`; returns the occurrences read back |
| `meeting_snapshot(...)` | returns the recorded state | none | `GET /meetings/{id}`; the old series for the compensating `PATCH` |

A new error kind in `errors.py`: `ZoomDailyLimit(ProviderError)`, `lasting=True` (criterion 14). `zoom_api._api_error` maps to it only when Zoom's daily-limit signal is confirmed.

**Services:**

- `move_class(link_request_id, occurrence_id, *, starts_at, ends_at, by, provider=None) -> MoveResult`
- `move_series(link_request_id, *, start_time, end_time, by, provider=None) -> MoveResult`

`MoveResult(outcome, message, link_request, moves: list[tuple[old_start, old_end, Occurrence]])`. They share one private `_move(...)` with 006's structure (the lookup, the locked transaction, compensation). `send_moved_email(request, link_request, moves) -> bool`.

**Forms:** `MoveClassForm(date, start_time, end_time)` and `MoveSeriesForm(start_time, end_time)`. Their `clean()` calls the model rules, so the form and the service agree.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| **`zoom:move_class`** | `zoom/requests/<int:pk>/classes/<int:occurrence_pk>/move/` | `MoveClassView(ReviewerRequiredMixin, SingleObjectMixin, FormView)`, `non_atomic_requests` | `zoom/move_form.html` | `zoom.review_linkrequest` |
| **`zoom:move_series`** | `zoom/requests/<int:pk>/move/` | `MoveSeriesView`, the same base | `zoom/move_form.html` | `zoom.review_linkrequest` |
| `zoom:detail` (changed context) | as today | `LinkRequestDetailView` | `zoom/detail.html` | `zoom.review_linkrequest` |

### Context contract

**`zoom/move_form.html`** (new, one template, in the shell):

| Variable | Type | Notes |
|---|---|---|
| `link_request` | LinkRequest | Reference, class name, `host_account.label` |
| `occurrence` | Occurrence or `None` | Set for a one-class move. The form posts to `zoom:move_class link_request.pk occurrence.pk`, otherwise to `zoom:move_series link_request.pk` |
| `remaining` | list of Occurrence | Series only: the classes that will change (criterion 5's lead uses its length, first and last) |
| `form` | `MoveClassForm` or `MoveSeriesForm` | |
| `move_error` | str or `None` | Criteria 9 and 11–15's messages, in final form |
| `checks_zoom` | bool | False with `manual`: show 006's manual notice |

**`zoom/detail.html`** adds:
- `movable_ids` (set of int pks, any booking);
- `can_move_series` (bool, weekly with remaining classes and none in progress).

Each `Occurrence` exposes `moved_at` and `moved_by`.

**Emails:** `moved_subject.txt` / `moved_body.txt`: `link_request` and `moves` (list of `{old_start, old_end, occurrence}`).

### Placement and reuse

- **`apps/zoom` only.**
- **Reused:**
  - 006's `busy_times`, `zoom_clashes`, `known_meeting_ids`, the error kinds, `lasting`/`maybe_done`, and the preview cache's `forget_preview` (a move invalidates it);
  - 005's `availability_for(lock=True)`, the slot backstop and the deadlock retry;
  - 011's `occurrence_id_for`, `cancellable_classes` and the confirm-page layout patterns;
  - the request form's time-field widgets and help.
- **Not built:** re-assigning accounts, changing weekdays, moving waiting requests.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Done (2026-09-26):** the owner answered Q4 and Q5 (D10 and D11). **Start only after 011 is Done**, since this brief builds on its fields and `cancel()`.
1. **`tmd-ui-designer`:** the move form (both kinds), the clash and failure states, the detail's `Moved` markers and links, and the email.
2. **In parallel, after the Design:**
   - **2a. `tmd-django-backend`:** everything in the MVT plan and the tests for criteria 1–23. It records the Zoom facts from criteria 10 and 14 in its notes. It runs `pytest --create-db` and signals.
   - **2b. `tmd-frontend`:** `move_form.html`, the detail changes, the email layout and CSS. It runs `pytest` after the signal.
3. **`tmd-test-verifier`:** criteria 1–25, with the thread tests 3 extra times. Then the owner's live check (criterion 26) through the main session.
4. **`tmd-code-reviewer`:**
   - the order and lock scope;
   - that compensation is idempotent and every message honest;
   - the series re-anchoring and cancelled-date deletes (R1);
   - that the payload never touches `settings` (006 D19).
5. **`tmd-docs-writer`:** the README (moving classes, the new scope and D8's steps, the daily limits), `docs/CHANGELOG.md`, and closes the brief.
