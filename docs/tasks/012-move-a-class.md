# 012 — Move a class, or change the time of a booking's remaining classes

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Verifying <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

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

**Place in the split** (brief 011, Scope): second, after 011 and before 013.

**It's a go-live gate item** (owner, 2026-09-26: "we go live after all build"; D12). Production takes no real requests until 006, 011, 012, 013 and 014 are all done, each with its owner live check.

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
     - **G2 (D13):** the `date` widget carries `min` (today) and `max` (the last date 005's `DATE_TOO_FAR` allows), both set **on `MoveClassForm`**, so `partials/field.html` prints them with nothing passed in.
     - The two time fields reuse the request form's widgets (`type=time`, `step=300`), labels, help and "required" messages.
     - A test checks the rendered `min`, `max` and `step`.
   - `move_series` has `Starts at` and `Ends at`, filled in with the current times. Its lead (P2, D14):
     - n ≥ 2: `The new time applies to every class still to come: {n} classes, from {first date} to {last date}. The days stay the same.`
     - n = 1: `The new time applies to the one class still to come, on {date}. The day stays the same.`
   - **G1 (D13):** each form links `See it on the timetable` to `timetable_url`: the month of the class (one class) or of the first remaining class (series), filtered to the booking's account. It's built with `views.month_page_url(month, account_id)`, the one place a view builds that address (009 D9).
   - Errors use the error summary and field errors, and keep what was typed.
   - **"Filled in" means filled in in a real browser** (criterion 28, added in fix cycle 1): the rendered `value` attributes are ISO (`2026-10-07`, `08:30`), not localised text.
6. **Detail page.** On an approved booking:
   - each movable class gets `Move this class` (its accessible name includes the date);
   - a weekly booking with remaining classes and no class in progress gets `Change the time of the remaining classes`;
   - a moved class shows the tag `Moved` (icon plus word) and `Moved by {name} on {when}.`, with a full stop, like 011's cancelled note (P7, D14).
   - A row can carry both `Move this class` and `Cancel this class`, per the amended `class-rows.md` (G6).

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
    - If they differ: the database transaction rolls back, and Zoom is **put back fully** (criterion 32; amended 2026-10-02 by D18, replacing "**one** compensating `PATCH`"). Only when criterion 32's final check passes does the form re-render with `Zoom scheduled different dates from these classes, so nothing was changed. Tell whoever looks after the system.`
    - If putting it back fails, the message depends on how far it got (amended 2026-10-02 by D21, the designer's D.13). The pinned texts and the full step-to-message mapping are in criterion 32:
      - **no restoring `PATCH` was answered** (criterion 32's step 1 failed, or a second lock race came before it was sent): `MOVE_NOT_PUT_BACK`;
      - **a restoring `PATCH` was answered, but a later step failed or the final check didn't match:** `MOVE_PARTLY_PUT_BACK`.

      Either way there's one neutral `ERROR` log line (criterion 32).
12. **Zoom refused, for certain** (connection error, connect timeout, 429, any 4xx): everything is rolled back, and the form re-renders (200) with `We couldn't move it in Zoom: {phrase}. Nothing was changed. {next step}`. The next step (P6, D14) is:
    - temporary: `Try again in a few minutes.`
    - lasting: 011's `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.`

    **No move message ever suggests another account** (D11): 006's `NEXT_STEP_LASTING` ("Choose another free account…") is never used by a move. A test pins the message for each 006 error kind, and a scan of every move message (`MOVE_MESSAGES`) finds no `another free account`. **`MOVE_MESSAGES` includes `MOVE_PARTLY_PUT_BACK`** (added 2026-10-02, D21), so the scan covers it.
    - `ZoomMissingScope` gets its own text: `The Zoom app for {label} is missing the permission to change meetings. Nothing was changed. Ask whoever looks after the server to add the scopes listed in the README.`
13. **Zoom may have done it** (`maybe_done`). After the rollback, Zoom is put back to the database's times; setting them again is safe whatever Zoom did. For a one-class move that's one occurrence `PATCH`. For a series it's criterion 32's full put-back (amended 2026-10-02, D18). The message is one of:
    - put back, and (for a series) criterion 32's final check passed: `No answer from Zoom, so we put the class back to its old time there to be safe. Nothing was changed. Try again in a few minutes.`
    - the restoring `PATCH` itself wasn't answered or was refused, so no restoring `PATCH` landed, and Zoom may never have changed: `No answer from Zoom, and we couldn't check what it did. Nothing was changed here. Try again in a few minutes. If the class shows the new time in Zoom, trying again finishes the move.` This is **unchanged** by D21; this case never shows `MOVE_NOT_PUT_BACK`.
    - **series only:** a restoring `PATCH` was answered, but a later step of criterion 32 failed (the read-back, a delete, a per-class `PATCH`, the final `GET`, or a final check that didn't match), or a second lock race came after step 1 landed. Then it's **`MOVE_PARTLY_PUT_BACK`** and the `ERROR` line (amended 2026-10-02, D21; it used to be `MOVE_NOT_PUT_BACK`).
14. **Zoom's update limits** (research: 100 updates per meeting per day, and 100 creates or updates per user per day, reset at UTC midnight).
    - **How a daily limit is recognised** (amended 2026-10-02, owner: "Yes, read it"; D19). Inside `zoom_api._api_error`, **and only for an HTTP 429**:
      - it's `ZoomDailyLimit` when Zoom's rate-limit header says the limit is a daily one, or when Zoom's error `message` contains `daily` (case-insensitive);
        - **the header:** the backend confirms its name and values on https://developers.zoom.us/docs/api/rate-limits/ (Zoom's docs describe an `X-RateLimit-Type` header) and records them in its notes. If Zoom sends no such header, the message test alone decides;
      - otherwise it's `ZoomBusy`, as before.
      - **A body that isn't JSON, or has no `message`,** is read as "not daily". It never raises.
    - **Zoom's text is never shown or logged** (006 criterion 10, amended). It's read only to choose between the two fixed errors. No `user_message`, page, message, email or log record contains any part of Zoom's message or header values. The log records the error class name only, as today.
    - A daily-limit answer raises the lasting error `ZoomDailyLimit`, with the message `Zoom's daily limit for changing {label}'s meetings is used up. Nothing was changed. Try again after 5:30 am on {Tue 29 Sep 2026}.` (P5, D14).
      - The date is the day of Zoom's next reset: the next UTC midnight shown in Colombo time, formatted with `class_date`.
      - Tests: at the frozen now (Mon 28 Sep, 10:00) it's `Tue 29 Sep 2026`; at Tue 29 Sep, 02:00 it's `Tue 29 Sep 2026`.
    - **Tests** (mocked Zoom):
      - a 429 whose body carries **Zoom's documented daily-limit wording**, copied verbatim from the rate-limits page (the test names the URL in a comment) → `ZoomDailyLimit` and the message above;
      - a 429 with only the daily header value (if Zoom documents one) → `ZoomDailyLimit`;
      - a 429 whose message is a per-second wording (no `daily`), and one with an empty or non-JSON body → `ZoomBusy` and criterion 12's temporary message;
      - a 400 whose message contains `daily` → **not** `ZoomDailyLimit` (the rule is 429-only);
      - with `DEBUG` logging captured, no log record and no rendered page contains any word of Zoom's message.
    - The verifier's earlier test `test_the_live_api_never_claims_a_daily_limit` pinned the old fallback (every 429 is busy). It's amended deliberately to match this rule.
    - **A daily limit can now reach every Zoom call, not only the move's `PATCH`.** `ZoomDailyLimit`'s own phrase, the shared reset sentence and every other caller's text are pinned in **criterion 34** (D22). This criterion's move-`PATCH` message above is unchanged, but it's now built with criterion 34's reset helper.
15. **Saving fails after Zoom changed it.** A MySQL deadlock is retried once; repeating the `PATCH` is harmless. Any other failure puts Zoom back after the rollback, and shows the failure's normal message:
    - one class: one occurrence `PATCH` to the database's time;
    - series: criterion 32's full put-back (amended 2026-10-02, D18).

    If putting it back fails, criterion 32's mapping applies (amended 2026-10-02, D21):
    - one class, the undo `PATCH` refused or unanswered, or no occurrence ID to send it to: `MOVE_NOT_PUT_BACK`;
    - series, step 1 failed, or a second lock race before it was sent: `MOVE_NOT_PUT_BACK`;
    - series, a restoring `PATCH` answered and then any later step failed, the check didn't match, or a second lock race came after it: `MOVE_PARTLY_PUT_BACK`.

    Each case writes the neutral `ERROR` line.
16. **Success.** The view redirects (302) to the detail with:
    - `Moved the class to {Tue 6 Oct 2026, 9:00 am to 12:00 pm}. We emailed {email}.`, or
    - `Changed the time of {n} classes to {9:00 am to 12:00 pm}. We emailed {email}.`, which reads `1 class` when n = 1 (P2, D14; pluralised like 005's leads).
    - If the email failed: the warning `Moved, but the email to {email} didn't send. Tell them the new times yourself.`
    - With `manual`: no Zoom call is made, the form shows 006's manual notice (`This system can't see meetings made directly in Zoom. …`), and the success message adds ` This system can't reach Zoom: change it in Zoom too.`
17. **Races** (thread tests; flaky means FAIL):
    - **(a)** Two moves of the same class: exactly one `PATCH` commits its time. The other gets the clash or the "already moved" state after the lock, and its compensating `PATCH` (if any) restores the winner's time, not the old one.
    - **(b)** A move and an approval of another request into the same new time on the same account: exactly one wins, and no two booked classes overlap.
    - **(c)** A move and a cancel (011) of the same class: the final state is either cancelled, or moved and not cancelled. At most one email per committed action. The loser redirects with `That class was cancelled.` or proceeds on the moved class.
18. **The email** goes to the requester only, after the commit.
    - **Subject:** `Class times changed: {reference} {class_name}`.
    - **Body:** one pair per moved class, **on two lines** (P4, D14), with a blank line between pairs:
      ```
      Was: Wed 7 Oct 2026, 8:30 am to 11:30 am
      Now: Thu 8 Oct 2026, 9:00 am to 12:00 pm
      ```
    - Then, when `can_start` (G3): `Your Zoom link and start link stay the same. The start link follows the new times.`
    - When the provider can't start (P3, D14): `Your Zoom link stays the same.`, and the email mentions no start link anywhere. A test asserts that, case-insensitively.
    - It contains no join link, passcode, start link or host key.
19. **The start link follows.** After Wed 7 Oct moves to Thu 8 Oct 9:00–12:00, 011's `start_state` is `ready` at Thu 8 Oct 8:30 and not at Wed 7 Oct 8:00.

### Rules, security, verification

20. **Scopes.** The README's scope list gains `meeting:update:meeting:admin`, with https://developers.zoom.us/docs/integrations/oauth-scopes-granular/. `Check connection` stays as it is (D6).
    - **This is the docs writer's job at close** (agent plan step 6; main-session ruling, 2026-09-26). The verifier checks it after step 6, not as a build criterion. Its being missing before then is expected, not a build FAIL.
21. **Thin views.** The rules are on the models (criterion 2), and the Zoom work and transactions are in `services`.
22. **Template rules, no-JS, layout and accessibility** as in 011 criterion 35. The two forms use the busy button (P1, D14):

    | Form | Submit label | Busy text with `checks_zoom` | Busy text with `manual` |
    |---|---|---|---|
    | `move_class` | `Move the class and email the requester` | `Moving the class in Zoom…` | `Moving the class…` |
    | `move_series` | `Change the times and email the requester` | `Changing the times in Zoom…` | `Changing the times…` |
23. **No test reaches the network.** `FakeProvider` gains steerable update errors and a `patched` record.
24. **Automated checks:** as in 011 criterion 37.
25. **Prod walkthrough** (`ZOOM_PROVIDER=manual`, 8010):
    - move one class of a test booking;
    - change a series' time;
    - try a clashing time against another test booking and see the 409 message;
    - check static files.

    Screenshots at 1440 and 400: both forms, the clash error, and the detail's `Moved` markers.
26. **The owner's live check:**
    1. Move one class of a live 2-week booking, and check the occurrence in Zoom. **Then cancel that moved class in the app (011), and confirm it's gone in Zoom** (added 2026-10-02, review round 1). A `DELETE` answered with 3001 counts as done, so if the occurrence ID changed with the move, the cancel would "succeed" while the class stayed in Zoom. Only this live check catches that.
    2. Change the series time, and check every remaining occurrence, and that a class cancelled earlier (011) hasn't come back.
    3. The join link and meeting ID are unchanged.
    4. The start link opens only in the new window.
    5. Try a time that overlaps a meeting made directly in Zoom: it's refused.

### Added with the Design (2026-09-26)

27. **The detail page's series box** (G5, D13). `detail.html` keeps receiving `checks_zoom` (006). The `Change the time of the remaining classes` box uses it for **its lead sentence only** (Design D.1.3):
    - `checks_zoom` true: `Moves every class still to come to a new time of day, on the same days, in Zoom too, and emails the requester. To move just one class, use Move this class in the list above.`
    - `checks_zoom` false (manual): `Moves every class still to come to a new time of day, on the same days, and emails the requester. To move just one class, use Move this class in the list above.`

    **The box never shows the `Check Zoom for clashes first` warning notice.** That notice belongs to the move form (`zoom/move_form.html`, Design D.2.3), where it shows whenever `checks_zoom` is false.

    **Test:** render an approved weekly booking's detail page with the fake provider and with the manual provider. Assert that:
    - the series box holds the matching lead above, exactly;
    - the series box holds no `Check Zoom for clashes first` and no `notice--warn` in either case.

    Then render `zoom:move_series` with the manual provider and assert that `Check Zoom for clashes first` **is** there.

### Added in fix cycle 1 (2026-09-26)

28. **The forms really pre-fill** (the verifier's criterion 5 FAIL; owner `tmd-frontend`; D15).
    - `partials/field.html` renders a field's value through **the widget's own formatting** (`BoundField.value()` passed through the widget's `format_value()`, or Django rendering the widget itself), never `value="{{ field.value }}"`, which auto-localises a date to `Oct. 7, 2026` and a time to `7 a.m.`. Browsers drop both values.
    - It's fixed **once, in the shared partial**, not by pre-formatting `initial` in `apps/zoom/forms.py`, so every date or time field shown through the partial is right.
    - **Result:** the move-class GET renders `value="2026-10-07"` on `date` and `value="08:30"` / `value="11:30"` on the times. The move-series GET renders its two times the same way.
    - The verifier's test `test_move_views.py::test_the_rendered_move_page_prefills_the_current_date_and_times` passes, unchanged.
    - **005's request form must keep working.** Its date and time fields still render correctly empty on GET, and still keep typed values on an invalid POST, including a bound, invalid value such as `25:99`, which is re-shown as typed. Every other form using the partial is unchanged: the account form, the reject form, the approve form's manual fields and 011's cancel form.
      - Add a test that renders the request form bound with `first_date="2026-10-05"`, `start_time="08:30"` and an invalid `end_time="25:99"`, and asserts the three `value`s exactly.
      - 005's, 008's and 011's existing form tests pass unchanged.
29. **The five move messages the backend added are pinned** (the designer's D.12; D16). Placeholders are unchanged: `{when}` and `{occurrence}` are `str(occurrence)`, and `{times}` is `{start} to {end}` built with `class_time`.

    | # | Constant | Where | Status | Text (pinned) |
    |---|---|---|---|---|
    | 1a | `MOVED_A_MOMENT_AGO` | one-class form, `move_error`, 409 | replaced | `Someone else moved this class a moment ago. It's now {when}. We didn't make your change. If it still needs to move, check the time in the form and press the button again.` |
    | 1b | `TIMES_CHANGED_A_MOMENT_AGO` | series form, `move_error`, 409 | replaced | `Someone else changed the time of the remaining classes a moment ago. They're now {times}. We didn't make your change. If they still need a different time, check the times in the form and press the button again.` |
    | 2 | `MOVE_SERIES_OFF_PATTERN` | error flash on the detail after `zoom:move_series` redirects; and the series box's lead (criterion 31) | replaced | `The class now on {occurrence} was moved to a different day, so the remaining classes can't be changed together. Move each class on its own instead, with Move this class.` |
    | 3 | `MOVING_AT_THE_SAME_MOMENT` | either form, `move_error`, 409 | as written | `Someone else was changing this booking at the same moment. Nothing was changed. Try again.` |
    | 4 | `END_SAME_DAY` | field error on `end_time` (`Occurrence.move_errors`) | as written | `The class must end on the same day it starts. Check the end time.` |

    **Tests:** each text is asserted exactly, rendered with the fixtures, and the three rendered examples in D.12 match. For example, 1a renders `Someone else moved this class a moment ago. It's now Thu 8 Oct 2026, 9:00 am to 12:00 pm. We didn't make your change. …`.
30. **A stale form never overwrites someone else's move** (main-session ruling: a correctness bug; D17).
    - **What goes wrong today:** the move views take `expected` from the class's times as read when the POST **starts**. A move someone else made while this form was open is therefore overwritten, and the requester gets two contradictory emails.
    - **The fix:** each move form carries what it **showed**, in one hidden field, `shown`.
      - Its value is `signing.dumps([[pk, starts_at, ends_at], …], salt="apps.zoom.move-shown")`, with the times as epoch seconds. It's signed, so it can't be edited into something else.
      - For **one class** it's that class.
      - For **a series** it's every remaining class the page listed.
      - It's built by one model method, `LinkRequest.move_fingerprint(classes)`, and read back by `services`.
    - **The check** runs inside the move's locked transaction (the `_plan_move` re-check), **before** any Zoom lookup or `PATCH`. It compares each listed class that is still not cancelled and not started against its locked row:
      - any listed class whose `starts_at` or `ends_at` differs from what was shown → refuse (409) with message **1a** (one class) or **1b** (series) from criterion 29, naming the **current** time;
      - a listed class that was cancelled, or has started, since is simply left out (the existing rules already exclude it). A class cancelled meanwhile isn't a refusal.
    - **On refusal:**
      - no Zoom call of any kind, no database write and no email;
      - the form re-renders with what was typed kept, the `Current time` / `Current times` fact showing the new value, and **a fresh `shown`**, so pressing the button again (as 1a and 1b say) acts on the times now on screen. That's one of only three places `shown` is refreshed (criterion 33).
    - **A missing or unreadable `shown`** (a page from before this fix, or a tampered one): the form re-renders (400) with the non-field error `This page is out of date. Reload it, check the times, then try again.`. There's no Zoom call and no email.
    - The old `expected=` path taken from the POST-start read is removed. `shown` is the only source.
    - **Tests** (`transaction=True` where two users are involved):
      - **one class:** user A GETs `move_class` (capture `shown`). User B moves the same class through `services.move_class`. User A POSTs the old form. Expect a 409 with 1a naming B's time, A's typed values kept, **zero** HTTP calls recorded by mocked Zoom, zero emails, the class still at B's time, and one `moved_by` (B). Then A POSTs again with the re-rendered `shown`, and it succeeds.
      - **series:** the same with `move_series` and 1b. B's change can be either B's series move or B's one-class move of any listed class.
      - **cancel meanwhile:** A opens `move_series`. B cancels one listed class (011). A's POST succeeds and moves the others.
      - **tampered or missing `shown`:** a 400 and the out-of-date message.
31. **A blocked series change is explained on the detail page** (the designer's follow-up, accepted; D17). It mirrors 011's `cancel_blocked_message`.
    - New context variable `move_series_blocked` (str or `None`), from `LinkRequest.series_move_blocked_message()`. It's set only when the booking is approved and weekly, has remaining classes, has no class in progress, and still can't be changed together because a class was moved to a different day. It's `None` otherwise.
    - When it's set, the detail shows the `Change the time of the remaining classes` box with `move_series_blocked` (message 2, criterion 29) as its `p.box__lead`, and **no** button.
    - `can_move_series` is false in that case. The in-progress case still hides the box entirely (unchanged).
    - **Tests:**
      - move one class of ZL-0042 to another weekday, then render the detail: the box holds message 2 exactly and no link to `zoom:move_series`;
      - with nothing moved, `move_series_blocked` is `None` and the box has its criterion 27 lead and button;
      - with a class in progress, there's no box.

### Added after review round 1 (2026-10-02)

32. **Putting Zoom back after a failed move is complete, ordered and retried** (SF1, owner: "Undo fully", D18; SF2). One shared helper, `_put_zoom_back`, is used by criteria 11, 13 and 15.
    - **Locks and retry (SF2):**
      - It works in its own transaction, locking the request, then the account, then the classes, the same order as `approve()`, `cancel()` and the forward move (D2).
      - A MySQL deadlock (1213) or lock-wait timeout (1205) is retried **once**. A second one ends in `MOVE_NOT_PUT_BACK` and the `ERROR` line.
      - The target **times** always come from the **locked rows**, never from the failed attempt's in-memory progress (review nit).
      - The **occurrence ID** follows the rule in the "One class" bullet below: the locked row's ID first, and the attempt's looked-up ID only when the row's is blank (amended 2026-10-02 after fix-cycle-2 verification).
      - A test captures the SQL and asserts `SELECT … FOR UPDATE` on `zoom_linkrequest`, then `zoom_hostaccount`, then `zoom_occurrence`, before any restoring `PATCH`.
    - **One class** (weekly occurrence or one-off meeting): one `PATCH` back to the locked row's times.
      - **Which occurrence ID it uses** (amended 2026-10-02; the backend's disclosed deviation, which the fix-cycle-2 verifier ruled compliant):
        - the locked row's `zoom_occurrence_id` when it isn't blank;
        - **only when the locked row's ID is blank** (a booking that never stored one, for which the move looked it up with 011's `occurrence_id_for`, criterion 10): the ID that the failed attempt looked up from Zoom.
      - **Why the fallback:** with no ID at all, the undo would `PATCH` the meeting itself, which for a weekly booking changes the **whole series**, not the one class.
      - A one-off booking's class has no occurrence ID either way, and its undo `PATCH`es the meeting, as before.
      - **Pinned by** `test_a_blank_id_is_put_back_by_the_id_the_move_looked_up`.
      - **The one-class edge counts as done** (D21, as the main session recommended). If the undo `PATCH` is answered but the put-back's own (write-free) transaction then fails, Zoom already matches the database. So the put-back counts as **done**: the failure's normal message is shown, and there's no `MOVE_PARTLY_PUT_BACK` and no `ERROR` line. The transaction failure is logged at `WARNING` with the reference and the error class.
      - A test forces an exception in that transaction after a mocked, answered `PATCH`, and asserts this outcome.
    - **A series**, in this order:
      1. the restoring series `PATCH`, anchored at the first remaining class, with the database's start, duration and recurrence;
      2. `GET /meetings/{id}`, then `DELETE ?occurrence_id=` for every occurrence on a date whose class was **cancelled** (011). It uses **the same helper as the forward path** (criterion 10), so earlier-cancelled classes don't come back;
      3. **classes the series `PATCH` flattened are put back too.** A remaining class that an earlier one-class move left at a different time on its usual day isn't on the series pattern, and the restoring series `PATCH` has just reset it. Each such class gets one occurrence `PATCH` to its own stored time, using the ID read back in step 2. (Different-day moves can't reach here: criterion 31 blocks a series move whenever one exists.)
      4. **a final check:** one more `GET`. Zoom's non-deleted occurrences from the first remaining class must equal the database's remaining, non-cancelled classes, one to one by start **and** end. The read-back `occurrence_id`s are stored on those classes inside the same locked transaction, because a series `PATCH` may renumber them.
    - **When putting it back fails, the message says how far it got** (amended 2026-10-02 by D21, the designer's D.13). It's chosen by `back.landed`, which `_put_zoom_back` sets once a restoring `PATCH` has been answered:

      | Failure | Forward move certain? | `back.landed` | Message |
      |---|---|---|---|
      | one class: the undo `PATCH` refused or unanswered, or no occurrence ID to send it to | yes | no | `MOVE_NOT_PUT_BACK` |
      | one class: the undo `PATCH` answered, then its own transaction failed | yes | yes | **done**: no failure message from the put-back (see the one-class edge above) |
      | series, step 1: the restoring `PATCH` refused or unanswered, or a second lock race before it was sent | yes | no | `MOVE_NOT_PUT_BACK` |
      | series: step 2 (the read-back `GET` or a `DELETE`), step 3 (a per-class `PATCH`), step 4 (the final `GET`), or a final check that doesn't match | either | yes | `MOVE_PARTLY_PUT_BACK` |
      | series: a second lock race after step 1 of the first try landed | either | yes | `MOVE_PARTLY_PUT_BACK` |
      | no answer to the move, and step 1 not answered or refused either (criterion 13) | no | no | criterion 13's `We couldn't check what it did` message, **unchanged** |

      **The two texts (pinned, D21):**
      - **`MOVE_NOT_PUT_BACK`** (text replaced): `We couldn't save the new time here, or undo it in Zoom. {label}'s meeting {meeting_id} may still be at the new time in Zoom. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.`
      - **`MOVE_PARTLY_PUT_BACK`** (new): `We couldn't save the new time here. We put {label}'s meeting {meeting_id} back to the times saved here, but some classes in Zoom may not match this booking. A cancelled class may have come back, or a class moved on its own may be at the usual time. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.`

      Both texts go in the existing `move_error` notice, which needs no template change. Both are in `MOVE_MESSAGES` (criterion 12's scan).
    - **The `ERROR` log line is neutral** (D21). Exactly one record per failed put-back, worded so it's true in every case:

      `Moving {reference}: Zoom meeting {meeting_id} doesn't match this database: {move's error class} (putting it back: {failure class or "mismatch"}, restoring update answered: {yes|no})`

      It never claims what time Zoom has. It never holds a link, a token or Zoom's text. `restoring update answered` is `back.landed`.
    - **An unexpected error can't skip that line** (review round 2, nit; added 2026-10-02).
      - `_put_zoom_back` ends with a final `except Exception` that records the error's **class name** as `failure`, writes the same neutral `ERROR` line, and returns the criterion 32 table's message for the current `back.landed` (`MOVE_NOT_PUT_BACK` or `MOVE_PARTLY_PUT_BACK`).
      - The **move's own exception** is still the one the caller reports. The put-back's error never replaces it.
      - **Test:** a `RuntimeError` raised inside the put-back, before and after a restoring `PATCH` lands, gives exactly one neutral `ERROR` with `putting it back: RuntimeError` and the right message for each case.
    - **"Nothing was changed" is shown only after the final check passes.**
    - **Tests** (mocked Zoom; ZL-0042 with the Wed 14 Oct class **cancelled** and the Mon 12 Oct class earlier moved by itself to 13:00–16:00; a series move to 9:00–12:00 whose read-back is forced to differ):
      - the recorded calls are: forward `PATCH`, `GET`, then the restoring `PATCH`, `GET`, one `DELETE` for Wed 14 Oct, one occurrence `PATCH` putting Mon 12 Oct back to 13:00, and the final `GET`;
      - then the `DATES_DIFFER` message; the database's times and `moved_*` fields as before the attempt; the stored `zoom_occurrence_id`s equal the final read-back;
      - **`test_a_failure_at_any_step_of_putting_it_back_says_so`:** a failure injected at step 1 gives `MOVE_NOT_PUT_BACK`. The step 2 `GET`, step 2 `DELETE`, step 3 `PATCH`, step 4 `GET` and final-check-mismatch cases each give `MOVE_PARTLY_PUT_BACK`. Every case has exactly one `ERROR` naming the meeting ID, with `restoring update answered: no` for step 1 and `yes` for the rest;
      - a forced 1213 in the helper's transaction is retried once and succeeds;
      - **`test_a_second_lock_race_while_putting_it_back_says_so`:** a second 1213 after the first try's step 1 landed gives `MOVE_PARTLY_PUT_BACK`. A second 1213 before any restoring `PATCH` was sent gives `MOVE_NOT_PUT_BACK`;
      - **`test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back`** (keeps its name): no answer to the move, then step 1 answered and step 2 failing, gives **`MOVE_PARTLY_PUT_BACK`**. No answer to the move and no answer to step 1 gives criterion 13's unchanged message;
      - **one-class edge:** an answered undo `PATCH`, then a failing transaction, counts as done (the bullet above);
      - each message is asserted exactly, rendered with the fixtures, and matches D.13's two rendered examples;
      - the same restore used through criterion 13 (series, `maybe_done`) and criterion 15 (series, a save failure) runs the same four steps.
33. **`shown` is refreshed only where the person is told what changed** (review round 1, B1, the blocker; D20).
    - The hidden `shown` (criterion 30) gets a **fresh** value only in three places:
      - on **GET**;
      - on criterion 30's **409 stale refusal** (1a or 1b);
      - on criterion 30's **400 out-of-date page**.
    - **Every other re-render keeps the posted `shown` exactly as it was sent.** That covers an invalid form (200), a database or Zoom clash (409), a Zoom error, `maybe_done`, the daily limit, and `MOVING_AT_THE_SAME_MOMENT`. So a failed submit can never quietly accept someone else's move as "seen".
    - **Two-user test** (`transaction=True`; one class, then the same for a series with 1b):
      1. A opens `move_class` (capture `shown`).
      2. B moves the class through `services.move_class`.
      3. A posts an **invalid** time (end before start). Expect 200, the field error, the hidden input's value **equal to A's original `shown`**, and no Zoom call.
      4. A posts a **valid** time with that re-rendered form. Expect **409** with message **1a** naming B's time, **zero** Zoom calls recorded, **zero** emails, the class still at B's time and `moved_by` still B.
      5. A posts again with the 409 page's fresh `shown`, and it succeeds.
    - **Also tested:** a database-clash 409 re-render keeps the posted `shown`.
    - Criterion 30's "a fresh `shown`" bullet is limited by this criterion.

### Added after review round 2 (2026-10-02)

34. **A daily limit says when to try again, wherever it's hit** (review round 2, should-fix 1; the designer's D.14, all accepted; D22).
    - **The phrase, changed once in `ZoomDailyLimit.__init__`:**
      - `user_message` (the phrase): `Zoom's daily limit for this account is used up`
      - `reason_sentence` (unchanged code, so its output follows): `Zoom's daily limit for this account is used up.`
      - `ZoomDailyLimit` stays `lasting=True`. Its docstring's "the move's message names the day" becomes "every caller names the day".
    - **One reset helper.** `services.daily_reset_sentence(now=None)` returns P5's sentence exactly: `Try again after {time} on {date}.`
      - `{time}` is `class_time(zoom_daily_reset(now))`, which is always `5:30 am` in Colombo.
      - `{date}` is `class_date(zoom_daily_reset(now))`.
      - It's the only place the sentence is built. Criterion 14's `MOVE_DAILY_LIMIT` uses it too, and its text is unchanged.
    - **The daily case is checked before `lasting`** in every caller below. No other lasting error changes.
    - **The final texts** (pinned, D.14), rendered for Zoom 02 at the frozen now (Mon 28 Sep 2026, 10:00):

      | # | Caller | Template, and the change | Rendered (exact) |
      |---|---|---|---|
      | 1a | approve, the create (`create_failed_message` via `next_step`) | `CREATE_FAILED` unchanged. For `ZoomDailyLimit`, `next_step` returns `Choose another free account, or wait for this one. ` + the reset sentence | `We couldn't make the meeting in Zoom: Zoom's daily limit for this account is used up. Nothing was booked. Choose another free account, or wait for this one. Try again after 5:30 am on Tue 29 Sep 2026.` |
      | 1b | approve, the look-up before it (`lookup_failed_message` via `next_step`) | `LOOKUP_FAILED` unchanged; the same daily next step | `We couldn't check Zoom 02's meetings in Zoom, so nothing was booked. Zoom's daily limit for this account is used up. Choose another free account, or wait for this one. Try again after 5:30 am on Tue 29 Sep 2026.` |
      | 2 | cancel's `DELETE` (`cancel_failed_message`) | `CANCEL_FAILED` unchanged. The next step is the reset sentence alone | `We couldn't cancel it in Zoom: Zoom's daily limit for this account is used up. Nothing was cancelled. Try again after 5:30 am on Tue 29 Sep 2026.` |
      | 3 | the move form's step-1 look-up (`move_lookup_failed_message`) | `MOVE_LOOKUP_FAILED` unchanged. The next step is the reset sentence alone | `We couldn't check Zoom 02's meetings in Zoom, so nothing was changed. Zoom's daily limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.` |
      | 4 | Check connection (`check_connection`) | **new** `CHECK_DAILY_LIMIT` = `Couldn't check {label} with Zoom: {phrase}. Try again after {time} on {date}.`, chosen **before** the `lasting` test, so neither `Waiting won't fix this` nor `give them the Zoom error number` appears. The level stays `error` | `Couldn't check Zoom 02 with Zoom: Zoom's daily limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.` |
      | 5 | the approve page's account list (`services.availability`, the `unavailable` row's `zoom_problem`, `services.py:448`) | no code change: it prints `reason_sentence`. The row's own fix links stay (`availability-list.md`) | `Zoom's daily limit for this account is used up.` |

    - **No daily message** contains `Check connection`, `another free account` (except approve's 1a and 1b, where another account really helps), `Waiting won't fix this`, `429`, `rate limit`, `quota`, `UTC` or `API`. D11's move-message scan (criterion 12) still passes.
    - **Deliberate amendments** to other briefs' pinned behaviour, for the docs writer's dated notes at close:
      - 006 criteria 28 and 30(a): approve's daily next step;
      - 006 criterion 36: Check connection's daily row;
      - 011 criterion 12: cancel's daily next step.

      Every other error kind keeps its existing text in those criteria.
    - **Tests, one per caller plus the list** (mocked Zoom returning a 429 with Zoom's documented daily-limit wording; frozen now). Each asserts the rendered text above exactly:
      - `test_a_daily_limit_on_approves_create_says_when_to_try_again` (1a);
      - `test_a_daily_limit_on_approves_look_up_says_when_to_try_again` (1b);
      - `test_a_daily_limit_on_cancel_says_when_to_try_again` (2);
      - `test_a_daily_limit_on_the_moves_look_up_says_when_to_try_again` (3);
      - `test_a_daily_limit_on_check_connection_says_when_to_try_again` (4; also asserts the message level is `error` and the text has no `Waiting won't fix this`);
      - `test_a_daily_limit_on_the_account_list_names_the_reason` (5: the detail page's row shows `Couldn't check with Zoom` and the reason sentence);
      - `test_the_daily_reset_sentence_is_p5s` (the helper at the frozen now and at Tue 29 Sep, 02:00; and `MOVE_DAILY_LIMIT` built with it, its text unchanged).

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
- **D12: Go-live waits for every brief** (owner, 2026-09-26: "we go live after all build").
  - The go-live gate is now **006, 011, 012, 013 and 014**, each Done with its owner live check.
  - This replaces 006's D14 gate (006 + 011) and 011's Scope line "012–014 can follow after go-live". Both briefs carry dated amendment notes.
  - 013 and 014 say the same in their Scope.
  - **The docs writer** updates the README's go-live section and `docs/CHANGELOG.md` at this brief's close. If 011's close happens first, it's done there.
- **D13: The designer's contract gaps G1–G6** (Design D.10), put into the contract as listed (main session, 2026-09-26):
  - **G1:** `timetable_url` on the move form, built with `views.month_page_url()` (criterion 5).
  - **G2:** the date widget's `min`/`max` on `MoveClassForm`, and the request form's time widgets (criterion 5).
  - **G3:** `can_start` on `moved_body.txt` (criterion 18).
  - **G4:** the move form's `link_request` fields are listed.
  - **G5:** `detail.html` keeps `checks_zoom` for the series box (criterion 27).
  - **G6:** the component notes change outside this brief. **The designer** amends `docs/design/class-rows.md` (two actions per row, the `Moved` state and its CSS rule, `movable_ids` in the `with` values) and `docs/design/busy-button.md` ("Used by": `move_form.html` with criterion 22's labels and busy texts). That's a design step before the frontend (agent plan, step 1b).
  - **Recorded, not a gap:** the old time of a one-class move isn't stored, so the page says `Moved by … on …`, not "was 8:30 am". The old time appears only in the email. A `moved_from_starts_at` field is a follow-up if IT asks for it.
- **D14: The designer's copy proposals P1–P7 are accepted** (Design D.11; main session, 2026-09-26: clarity and safety fixes). The final texts are pinned in the criteria:
  - **P1:** the series form's busy text `Changing the times in Zoom…` (criterion 22).
  - **P2:** one remaining class reads as one, in the lead (criterion 5) and the flash (criterion 16).
  - **P3:** no start-link wording in the moved email for the manual provider (criterion 18).
  - **P4:** `Was:` and `Now:` on **two lines** (criterion 18).
  - **P5:** the daily-limit message names the day of the reset (criterion 14).
  - **P6:** a lasting error on a move never suggests another account. It uses 011's `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.` (criterion 12).
  - **P7:** a full stop after `Moved by {name} on {when}` (criterion 6).
- **D15: The pre-fill is fixed in the shared partial** (fix cycle 1; the verifier's criterion 5 FAIL; criterion 28).
  - `partials/field.html` hand-builds the `<input>` and prints `{{ field.value }}`. For an unbound date or time, that's a Python object, which the template engine localises for display. Browsers reject that as an input value.
  - The partial is the single place fields are drawn (CLAUDE.md: shared markup in `templates/partials/`), so the fix goes there. A zoom-only workaround would leave the same trap for the next form.
  - **Guard:** 005's request form, whose date and time fields also go through the partial, must behave exactly as before, including invalid typed values re-shown as typed (criterion 28's test).
- **D16: The designer's D.12 message review is adopted.** 1a, 1b and 2 are replaced with the designer's final texts, and 3 and 4 are approved as written. All five are pinned in criterion 29. The designer's reasons (the right next step, no double "to", true in both "different day" cases, active voice) are kept in D.12.
- **D17: Two correctness fixes, ruled by the main session in fix cycle 1:**
  - **Stale forms** (criterion 30). A move must act on what the person **saw**, not on what was in the database when they pressed the button. Otherwise two people moving the same class a minute apart both "succeed", the second silently undoes the first, and the requester gets two contradictory emails.
    - **Why a signed list of the shown times, not a version number:** it needs no new column or migration, it covers both kinds of move with one mechanism, and it lets a class cancelled meanwhile pass without a false refusal. A single "last changed" timestamp on the request would refuse after any cancel.
    - **The check runs under the same locks and before any Zoom call** (D2), so a refusal leaves both the database and Zoom untouched.
    - **The re-render carries a fresh `shown`,** so the "press the button again" in 1a and 1b really works.
  - **A blocked series change is explained** (criterion 31). When classes have been moved to different days, the series can't be changed together. The detail page now says so in the series box, instead of leaving the box out with no reason. This is the same pattern as 011's `cancel_blocked_message` (011 G2).
- **D18: A failed series move is undone fully** (owner, 2026-10-02: "Undo fully", the reviewer's option (a) for SF1; criterion 32). This amends criterion 11's "one compensating `PATCH`".
  - **Why:** a single restoring `PATCH` rebuilds the series from its pattern, so it brings back classes cancelled earlier (011) and flattens classes that were moved by themselves. Both happen in Zoom while the page says "Nothing was changed".
  - **The fix:** the restore reuses the forward path's read-back-and-delete helper, puts flattened one-class moves back with occurrence `PATCH`es, and then checks Zoom against the database. Only a passing check may say "Nothing was changed". Anything less is `MOVE_NOT_PUT_BACK`, with an `ERROR` line naming the meeting ID.
  - **Locks and retry (SF2, accepted):** the helper takes the same lock order as every other booking change (request, account, classes) and retries once on 1213/1205, so it can't deadlock against another booking's move or approval and then report the wrong thing.
  - **Cost:** a failed series move can make a few more Zoom calls (one `GET`, the deletes, a `PATCH` per flattened class, one more `GET`). That's rare, and correct beats cheap here.
- **D19: A daily-limit 429 is recognised from Zoom's own answer** (owner, 2026-10-02: "Yes, read it"; criterion 14).
  - **For a 429 only,** Zoom's rate-limit header or a `daily` in its message chooses `ZoomDailyLimit` over `ZoomBusy`.
  - **Why:** without it, every 429 says "Try again in a few minutes", which keeps failing all day once the daily limit is reached. "Try again after 5:30 am on {date}" is the true advice.
  - **What changes in 006:** its rule becomes "Zoom's text is never shown or logged". Reading it to pick between two of our fixed messages is allowed; displaying or logging it isn't. 006 criterion 10 carries a dated note.
- **D20: Stale-form protection survives a failed submit** (review round 1, B1; criterion 33). `shown` is refreshed only where the person is shown the current times: on GET, on the 409 stale refusal and on the 400 out-of-date page. Refreshing it on an invalid-form re-render let a second, valid post silently overwrite another person's move, which D17 exists to stop.
- **D21: When an undo fails, the message says how far it got** (the designer's D.13, accepted 2026-10-02 as a main-session ruling under the honesty rule, D.2.6). This amends D18's "anything less is `MOVE_NOT_PUT_BACK`".
  - **The problem:** since D18 the undo has four steps. Once its first restoring `PATCH` has landed, `Zoom now has … at the new time` is false.
  - **Two messages, chosen by the existing `back.landed` flag:**
    - `MOVE_NOT_PUT_BACK` (new text) when no restoring `PATCH` was answered. Zoom may still be at the new time.
    - **new** `MOVE_PARTLY_PUT_BACK` when one was answered but the undo didn't finish or didn't check out. Zoom is back to the saved times, but a cancelled class may have come back, or a class moved on its own may be at the usual time.

    Both end with one action (check that meeting against the Classes list) and who to tell. The mapping and texts are pinned in criterion 32. Criteria 11, 13 and 15 point to it.
  - **The `ERROR` log line becomes neutral** (`doesn't match this database`, plus `restoring update answered: yes/no`), because the old wording repeated the same false claim.
  - **`MOVE_PARTLY_PUT_BACK` joins `MOVE_MESSAGES`,** so criterion 12's "no other account" scan covers it.
  - **The one-class edge counts as done.** An answered undo `PATCH` followed by a failure of the put-back's own, write-free transaction leaves Zoom matching the database. Showing a "may not match" message there would be needlessly alarming. A `WARNING` records it.
  - **The designer's knock-on edits to their own section** (D.2.6's split row, D.3's count of four messages, D.12's reference) are theirs to make. Where the Design section still shows the old wording, the criteria win.
- **D22: A daily limit says when to try again, wherever it's hit** (review round 2, should-fix 1; the designer's D.14, all accepted by the main session on 2026-10-02, including "or wait for this one" and the fifth place, the account list). Criterion 34.
  - **Why:** since D19, every API 429 that's a daily limit is `ZoomDailyLimit`, which is lasting. So approve's create and look-up, cancel's `DELETE`, the move's step-1 look-up and Check connection all fell into their "lasting" next step ("press Check connection", "Waiting won't fix this"). That's untrue for a limit that resets at 5:30 am. Approve's create counts against the same per-user quota, so this does happen.
  - **One phrase, one reset helper:** the phrase is changed once (`Zoom's daily limit for this account is used up`), and it's true for any kind of call. Every caller already builds its message from it. One helper builds P5's reset sentence. The daily case is checked before `lasting` in each caller, so no other error's wording moves.
  - **Approve keeps "Choose another free account"** in front, because another account has its own quota. "or wait for this one" ties the reset sentence to this account.
  - **Cancel, the move and Check connection get the reset sentence alone,** because there's no other account to offer (D11).
  - **Check connection gets its own template**, `CHECK_DAILY_LIMIT`, so neither `Waiting won't fix this` nor "give them the Zoom error number" (there's no number) appears.
  - The move `PATCH`'s criterion 14 text is unchanged ("changing" is exact there).
- **D9: Information architecture.** No new nav. Two verbs on the request detail, each with its own page, and back to the detail:

  ```
  ZL-0042 (zoom:detail)
  ├── Move this class                          zoom:move_class   (per movable class)
  └── Change the time of the remaining classes zoom:move_series  (weekly)
  ```

**Risk register**

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | The series `PATCH` re-creates classes that were cancelled, or shifts held ones | Medium / **High** | Mitigate: delete cancelled dates straight after, verify by reading back, and restore the old series on mismatch (criteria 10 and 11). **Amended 2026-10-02 (D18):** the restore itself now re-deletes cancelled dates, puts flattened one-class moves back, and checks the result (criterion 32). That closes the residual that review round 1 found (SF1) | the DATES_DIFFER or `MOVE_NOT_PUT_BACK` message | backend |
| R2 | An occurrence-level `PATCH` can't change the date, or changes the occurrence ID | Medium / Medium | Confirm in the docs at build time (criterion 10). A blocker is reported, not worked around | the backend's note | backend |
| R3 | Zoom's daily update limits stop moves on a busy day | Low / Low | Mitigate: one `PATCH` per series (D3), and a message saying when to retry (criterion 14) | the daily-limit message | backend |
| R4 | An uncertain `PATCH` plus a failed restore leaves Zoom at the new time and the database at the old one | Low / Medium | Accept, and mitigate: the message tells IT that trying again finishes the move. 013's reconcile would mirror it | the restore-failed message | backend |
| R5 | The update scope isn't added to every account's app | Medium / Low | Mitigate: the README steps (D8), the pinned message, and the owner's live check | criterion 12's scope message | owner |
| R6 | A moved class's occurrence ID changes, so a later cancel's `DELETE` gets 3001, counts as done, and leaves the class in Zoom | Low / Medium | Mitigate: the backend's criterion 10 note on whether IDs survive a `PATCH`; the read-back stores IDs (criterion 32); **the owner's live check step 1 cancels a moved class and confirms it's gone** (added 2026-10-02) | the owner's step 1 result | owner, backend |

**Follow-ups** (recorded, not in this brief):

- **Message 1b is misleading after a same-day one-class move** (review round 1, nit; owner, 2026-10-02: "a copy fix for later").
  - 1b names `{times}` as the booking's `start_time`–`end_time`. After someone moved **one** class to another time on its usual day, a stale series form is refused with 1b, but "They're now {times}" shows the series times, which didn't change. The class that did change isn't named.
  - It's a copy fix for the designer and planner in a later brief: for example, name the changed class, as 1a does. The behaviour (the refusal itself) is correct, and isn't changed.

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
| `link_request` | LinkRequest | **G4:** reads `pk`, `reference`, `class_name`, `requester_name`, `requester_email`, `schedule_summary` and `host_account.label` |
| `occurrence` | Occurrence or `None` | Set for a one-class move. The form posts to `zoom:move_class link_request.pk occurrence.pk`, otherwise to `zoom:move_series link_request.pk` |
| `remaining` | list of Occurrence | Series only: the classes that will change (criterion 5's lead uses its length, first and last) |
| `form` | `MoveClassForm` or `MoveSeriesForm` | |
| `move_error` | str or `None` | Criteria 9 and 11–15's messages, in final form |
| `checks_zoom` | bool | False with `manual`: show 006's manual notice, and the manual busy texts (criterion 22) |
| `timetable_url` | str | **G1:** the month page for the class's month (one class) or the first remaining class's month (series), filtered to the booking's account. Built with `views.month_page_url(month, account_id)` (009 D9), so the template never learns the query shape |

`form`'s widgets carry G2's `min`/`max` on `date` and the request form's time widgets, all set on the form (criterion 5).

**Fix cycle 1 additions to `form`** (criterion 30): both `MoveClassForm` and `MoveSeriesForm` gain a hidden field, `shown` (`forms.CharField(widget=HiddenInput)`). The view sets its initial value from `LinkRequest.move_fingerprint(...)` on GET, and sets a fresh one on every re-render. The template renders it with `{{ form.shown }}` inside the `<form>` (a hidden input, not through `partials/field.html`). There's no new top-level context variable. The out-of-date error (criterion 30) arrives as a non-field error, so the existing error summary shows it.

**`partials/field.html`** (shared, criterion 28): its contract doesn't change (`field`, `narrow`, …). Only how it prints a value changes: through the widget's own formatting.

**`zoom/detail.html`** adds:
- `movable_ids` (set of int pks, any booking);
- `can_move_series` (bool, weekly with remaining classes and none in progress, **and** not blocked by criterion 31);
- **`move_series_blocked`** (str or `None`, criterion 31): message 2 from `LinkRequest.series_move_blocked_message()` when an approved weekly booking with remaining classes and none in progress can't be changed together. The box then shows it as its lead, with no button. `None` otherwise;
- `checks_zoom` (bool, already passed since 006; **G5:** it stays, and in the series box it picks the lead sentence only; no warning notice there, per criterion 27).

Each `Occurrence` exposes `moved_at` and `moved_by`.

**Emails:** `moved_subject.txt` / `moved_body.txt`: `link_request` and `moves` (list of `{old_start, old_end, occurrence}`).

### Placement and reuse

- **`apps/zoom` only.**
- **Reused:**
  - 006's `busy_times`, `zoom_clashes`, `known_meeting_ids`, the error kinds, `lasting`/`maybe_done`, and the preview cache's `forget_preview` (a move invalidates it);
  - 005's `availability_for(lock=True)`, the slot backstop and the deadlock retry;
  - 011's `occurrence_id_for`, `cancellable_classes` and the confirm-page layout patterns;
  - the request form's time-field widgets and help;
  - 009's `views.month_page_url()` for `timetable_url`;
  - 011's `NEXT_STEP` copy for Check connection (P6), and its `class_rows.html` partial, `busy-button` and flash components.
- **Components:** none new. `.classrows` (011) is extended with the `Moved` state and a second action. Its one definition, `docs/design/class-rows.md`, is amended by the designer (D13, G6), as is `busy-button.md`. There are no new tokens, icons (`Moved` uses the existing `calendar`) or JS.
- **Settings:** none. The new Zoom scope `meeting:update:meeting:admin` is owner setup in each Marketplace app (D8), so it's README work, not code or config.
- **Not built:** re-assigning accounts, changing weekdays, moving waiting requests.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Done (2026-09-26):** the owner answered Q4 and Q5 (D10 and D11).
   - **When the build can start:** once 011's code is verified and approved. That's now true: 011 is committed as `2d792e0`. This brief builds on 011's fields, `cancel()` and `class_rows.html`.
   - **011's owner live check is separate** and doesn't block 012. 011 can stay `Verifying` while 012 is built. The go-live gate (D12) still needs both.
1. **`tmd-ui-designer`:**
   - **1a. Done (2026-09-26):** the Design section is written. G1–G6 and P1–P7 are folded in as D13 and D14 (criteria 5, 6, 12, 14, 16, 18, 22 and the new 27). The contract is fixed.
   - **1b. Before the frontend starts (G6):** amend `docs/design/class-rows.md` (the "What a row shows" table replacing "at most one of", the `Moved` state and its CSS rule, `movable_ids` in the `with` values) and `docs/design/busy-button.md` ("Used by": `zoom/move_form.html` with criterion 22's labels and busy texts). It's design documentation only, with no templates or CSS.
     - **Done (2026-09-26)**, per the Design section's D.10 status line. The main session confirms both files carry the change before step 3b starts.
2. **`tmd-devops`: none.** There's no settings, env, dependency or compose change. The new scope `meeting:update:meeting:admin` is owner setup in each Marketplace app (D8), which the docs writer documents in step 6.
3. **In parallel, after step 1b:**
   - **3a. `tmd-django-backend`:**
     - everything in the MVT plan (models and migration `0008`, providers, `ZoomDailyLimit`, services, forms with G2's widgets);
     - views with every contract variable (G1, G3–G5);
     - the tests for criteria 1–23 and 27.

     It records the Zoom facts from criteria 10 and 14 in its notes. **Only the backend runs `pytest --create-db`** (it adds `0008`). When it has finished, it reports "backend pytest run finished".
   - **3b. `tmd-frontend`:** `move_form.html` (both kinds, criterion 22's labels and busy texts, the timetable link), the `detail.html` changes and the series box, the `class_rows.html` extension (the `Moved` state, two actions), the email layout (two-line `Was:`/`Now:`, P3's sentence) and the one CSS rule. It never uses `--create-db`. It runs `pytest` (reusing the database) only after the main session passes on the backend's signal.
4. **`tmd-test-verifier`:** criteria 1–25 and 27, with the thread tests 3 extra times. It's the next agent to run `pytest --create-db`, after both 3a and 3b have finished. Then the owner's live check (criterion 26) through the main session.
5. **`tmd-code-reviewer`:**
   - the order and lock scope;
   - that compensation is idempotent and every message honest;
   - that no move message offers another account (P6, D11);
   - the series re-anchoring and cancelled-date deletes (R1);
   - that the payload never touches `settings` (006 D19).

**Fix cycle 1** (2026-09-26, after the verifier's FAIL on criterion 5 and the designer's D.12). No devops step: no settings, env or dependency change.

- **F1, in parallel:**
  - **F1a. `tmd-django-backend`** (items 2–4):
    - criterion 29: the five pinned texts in `services.py`/`models.py`, with exact-text tests;
    - criterion 30: `shown` on both forms, `LinkRequest.move_fingerprint()`, the locked comparison in `_plan_move`, the fresh `shown` on re-render, the out-of-date error, removing the POST-start `expected` read, and the two-user tests;
    - criterion 31: `move_series_blocked` in the detail context, `can_move_series` false when blocked, and the tests.

    **Only the backend runs `pytest --create-db`.** It reports "backend pytest run finished".
  - **F1b. `tmd-frontend`** (items 1 and 4):
    - criterion 28: fix `partials/field.html` to print the widget-formatted value, and add the 005 request-form guard test;
    - criterion 30's template side: `{{ form.shown }}` inside both move forms;
    - criterion 31's template side: the series box with `move_series_blocked` as its lead and no button.

    It never uses `--create-db`. It runs `pytest` (reusing the database) only after the main session passes on the backend's signal. The verifier's failing test must then pass.
- **F2. `tmd-test-verifier`:** criteria 1–19, 21–25 and 27–31 again, the full checklist, and the prod walkthrough again. That includes a real-browser screenshot of the move forms showing the pre-filled date and times, and a two-browser (or two-session) run of criterion 30. It's the next agent to run `pytest --create-db`, after F1a and F1b. Criterion 20 is checked after step 6, not here.
- **F3. `tmd-code-reviewer`:** the stale-form check (under the locks, before any Zoom call, the fresh `shown` on re-render, the signing salt used for nothing else), the partial fix (no regressions for other forms), and the pinned texts. It also covers the existing step-5 focus list.
  - **Done (2026-10-02): round 1, CHANGES REQUESTED** (B1, SF1, SF2 and nits). The owner ruled on SF1 and the daily limit, giving D18–D20 and criteria 11, 13, 14, 15, 26, 32 and 33.

**Fix cycle 2** (2026-10-02, after review round 1). No devops step: no settings, env or dependency change.

- **C1, in parallel:**
  - **C1a. `tmd-django-backend`:**
    - B1 → criterion 33: refresh `shown` only on GET, the 409 stale refusal and the 400 page, with the two-user test;
    - SF1 → criterion 32 and the amended criteria 11, 13 and 15: the full put-back, sharing the forward path's read-back-and-delete helper, with the step-by-step failure tests;
    - SF2 → criterion 32: the lock order and the one retry;
    - the daily limit → criterion 14: the 429-only classification in `zoom_api._api_error`, the documented-wording test, and the deliberate amendment of `test_the_live_api_never_claims_a_daily_limit`. It records the confirmed header name and values from Zoom's rate-limits page;
    - the review nits that are the backend's: prefer the locked row's `zoom_occurrence_id`; the `host_account` comment; and the task-011 flaky test (compare against the requested token or decode it, not two `signing.dumps` outputs).

    **Only the backend runs `pytest --create-db`.** It reports "backend pytest run finished".
  - **C1b. `tmd-frontend`:** the review nits that are the frontend's:
    - in `partials/field.html`, rename the attrs loop variable so it no longer shadows `value`, and note in its header that choice widgets must never be passed;
    - the missing space in `detail.html`'s header comment.

    It never uses `--create-db`. It runs `pytest` (reusing the database) only after the main session passes on the backend's signal.
- **C2. `tmd-test-verifier`:** criteria 1–19, 21–25 and 27–33, with the thread and two-user tests run 3 extra times, plus the full checklist. It's the next agent to run `pytest --create-db`, after C1a and C1b. Criterion 20 is still checked after step 6. Criterion 26 (with its new cancel-after-move step) stays with the owner.
- **C3. `tmd-code-reviewer`, round 2:** criteria 32 and 33 first (every restore path, the lock order, the retry, the "nothing was changed" honesty, the `shown` refresh points), then the daily-limit rule (429-only, Zoom's text never shown or logged).
  - **It now runs after fix cycle 3**, below, not straight after C2.

**Fix cycle 3** (2026-10-02, the designer's D.13, accepted as D21). **Backend only.** No devops, designer or frontend step: both texts go in the existing `move_error` notice, so no template changes.

- **3.1. `tmd-django-backend`, after the verifier currently running (C2) has finished.** Starting earlier would collide with the verifier's `pytest --create-db` on the shared test database.
  - In `services.py`: replace `MOVE_NOT_PUT_BACK`'s text; add `MOVE_PARTLY_PUT_BACK`; select between them by `back.landed` per criterion 32's table; add `MOVE_PARTLY_PUT_BACK` to `MOVE_MESSAGES`; reword the `ERROR` line to criterion 32's neutral form; and treat the one-class edge as done, with a `WARNING`.
  - Tests: amend `test_a_failure_at_any_step_of_putting_it_back_says_so`, `test_a_second_lock_race_while_putting_it_back_says_so` and `test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back` to criterion 32's expectations; add the one-class-edge test, the exact-text tests and the log-line test.
  - **The backend runs `pytest --create-db`** (no other agent is running then) and reports "backend pytest run finished".
- **3.2. `tmd-test-verifier`:** re-checks criteria 11, 12, 13, 15 and 32 (and, as usual, runs the full checklist). It's the next agent to run `pytest --create-db`, after 3.1. If C2 reported a FAIL, its fixes are folded into this cycle before 3.2.
- **3.3. `tmd-code-reviewer`, round 2:** C3's focus list, plus D21: every failure maps to the right message, nothing claims a time Zoom may not have, the log line is neutral, and the one-class edge is right.
  - **Done (2026-10-02): round 2, CHANGES REQUESTED** (one should-fix, two nits; no blockers). That gives D22, criterion 34, and criterion 32's catch-all.

**Fix cycle 4** (2026-10-02, after review round 2). **Backend only.** No devops or frontend step: every text goes in an existing notice or flash, so no template changes. The designer's D.14 is the source of the texts, now pinned in criterion 34.

- **4.1. `tmd-django-backend`** (starts now, building from D.14):
  - **criterion 34:**
    - `ZoomDailyLimit`'s phrase and docstring;
    - the shared `daily_reset_sentence()` helper, with `MOVE_DAILY_LIMIT` switched to it and its text unchanged;
    - the daily check before `lasting` in `next_step`, `cancel_failed_message`, `move_lookup_failed_message` and `check_connection`;
    - the new `CHECK_DAILY_LIMIT`;
    - the seven named tests;
  - **criterion 32's nit:** a final `except Exception` in `_put_zoom_back` that writes the neutral `ERROR` line with the class name as `failure`, plus its test;
  - **the test nit** (`apps/zoom/tests/test_services.py:279`): it compares a clock-stamped start token, the same flake as 011's. Decode the token from the email body (or compare it with the token the email actually carries) instead of rebuilding it with `signing.dumps`.

  **Only the backend runs `pytest --create-db`.** It reports "backend pytest run finished".
- **4.2. `tmd-test-verifier`:**
  - re-checks criteria 14, 32 and 34, and that the other briefs' error texts named in criterion 34 still hold for every other error kind;
  - runs `test_services.py` 3 extra times, to show the flake is gone;
  - runs the full checklist.

  It's the next agent to run `pytest --create-db`, after 4.1.
- **4.3. `tmd-code-reviewer`, round 3:**
  - every caller checks the daily case before `lasting`;
  - one helper builds the reset sentence;
  - no daily message gives a next step that can't help;
  - the catch-all keeps the move's own exception and still writes the neutral line;
  - the test no longer depends on the clock.
- Then step 6 below.
  - The docs writer also adds the dated "Amended by 012" notes that criterion 34 lists, to 006 criteria 28, 30(a) and 36 and to 011 criterion 12.

6. **`tmd-docs-writer`:**
   - **README:** moving classes, the new scope and D8's steps, the daily limits;
   - **the go-live gate** (D12): 006 + 011 + 012 + 013 + 014, in the README's go-live section, if 011's close hasn't already done it;
   - `docs/CHANGELOG.md`;
   - closes the brief.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

This is built inside the approved f-desk direction. It reuses brief 011's patterns: the cancel confirm page, the class rows, the busy button and the flash messages. It also reuses the component notes in `docs/design/` (`class-rows`, `busy-button`, `flash-messages`, `form-section`, `availability-list`).

- Every **pinned** string in the criteria is used exactly as written. Where this section's wording differs from a criterion, **the criterion wins**.
- Wording marked *design copy* is new in this section.
- Proposed changes to pinned text are in D.11.
- The backend's four unpinned messages are reviewed in D.12 (2026-09-26).
- `MOVE_NOT_PUT_BACK` is revisited in D.13 (2026-10-02, accepted as D21): it splits into two messages, because since D18 "at the new time" is sometimes false.
- A daily limit outside a move gets its own reason and next step in D.14 (2026-10-02, a proposal, for review round 2's should-fix 1).
- **Refreshed 2026-09-26: the main session accepted G6 and P1–P7.**
  - P4 is settled as two separate lines, `Was:` then `Now:`.
  - The sections below now show the accepted wording.
  - The planner has pinned it in criteria 5, 6, 12, 14, 16, 18 and 22, and added criterion 27. This section was checked against them afterwards. If anything here still differs, the criteria win.
  - G6's two component notes are amended.

**Summary of what changes**

| Kind | What |
|---|---|
| New component | **none.** |
| Extended component | **Class rows** (`.classrows`, `zoom/partials/class_rows.html`). A row can now carry two actions (`Move this class` and `Cancel this class`), a `Moved` tag, and a `Moved by …` note. The amendment is written out in D.1.2 and in `docs/design/class-rows.md` (amended, G6) |
| New template | `zoom/move_form.html` (D.2): one template for both kinds of move, in the shell |
| New emails | `zoom/email/moved_subject.txt`, `zoom/email/moved_body.txt` (D.5) |
| Changed | `zoom/detail.html` (D.1): the per-row actions, the new `Change the time of the remaining classes` box, and the header comment. `zoom/partials/class_rows.html` (D.1.2) |
| Unchanged | the timetable month and day pages, the start page, the queue, and `occurrence_list.html` (D.4) |
| Icons | **none new.** `Moved` uses `calendar`, which is already in the sprite |
| Tokens | **none new.** One new CSS rule for `.classrows` (D.1.2) |
| JS | **none new.** The existing error-summary focus, busy button and flash Close blocks cover everything |

**Information architecture** (D9, unchanged): there's no new navigation. Two verbs sit on the request detail. Each opens its own page, and each page returns to the detail.

```
ZL-0042 (zoom:detail)
├── Move this class                            → zoom:move_class   → back to the detail with a flash
└── Change the time of the remaining classes   → zoom:move_series  → back to the detail with a flash
```

### D.1 Request detail: `zoom/detail.html`

#### D.1.1 Page structure (approved booking)

This order extends 011's D.1.1. The new box is item 4:

1. the decided line (`notice--ok`, unchanged);
2. **Request** (unchanged). After a series move, `When` shows the new time by itself, because `schedule_summary` follows the move (D4). After a one-class move, `When` is unchanged, and the moved class carries the `Moved` marker in the Classes list (D4);
3. **Classes**: gains `Move this class`, the `Moved` tag and the `Moved by …` note (D.1.2);
4. **Change the time of the remaining classes** (new box, D.1.3). It shows only when `can_move_series`;
5. **Cancel this booking** (011, unchanged). It stays last.

**Why the new box goes before Cancel:** the page reads from the smallest change to the largest: move one class, change the times of all of them, cancel all of them. The one destructive act stays at the bottom, as 011 decided.

The cancelled, waiting and rejected pages don't change. `movable_ids` is empty and `can_move_series` is false for them, so no move action appears.

#### D.1.2 The Classes box: `class_rows.html`, extended

The include gains one value:

```django
{% include "zoom/partials/class_rows.html" with occurrences=occurrences cancellable_ids=cancellable_ids movable_ids=movable_ids in_progress_id=in_progress_id link_request_pk=link_request.pk only %}
```

**What a row shows.** This replaces class-rows.md's rule that a row shows "at most one of: the action, the `In progress` tag, or the `Cancelled` tag". Each row is built from these parts, in this order:

| Part | When | Markup |
|---|---|---|
| Date | always | `span.classrows__when` (unchanged). For a moved class it's the **new** time. The old time isn't stored (D5 keeps only who and when), so the page never shows it |
| `Moved` tag | `occurrence.moved_at` and **not** `cancelled_at` | `span.tag.tag--plain` with `calendar` and `Moved` (pinned, criterion 6) |
| `In progress` tag | `pk == in_progress_id` | unchanged (011) |
| `Cancelled` tag | `cancelled_at` | unchanged (011) |
| `Move this class` | `pk in movable_ids` | `a.classrows__action` → `{% url 'zoom:move_class' link_request_pk occurrence.pk %}`: `Move this class<span class="visually-hidden"> on {{ occurrence.starts_at\|class_date }}</span>` (criterion 6: its accessible name includes the date) |
| `Cancel this class` | `pk in cancellable_ids` | unchanged (011) |
| Moved note | `moved_at` (cancelled or not: it's history) | `p.classrows__note`: `Moved by {{ occurrence.moved_by }} on {% include "zoom/partials/when.html" with at=occurrence.moved_at only %}.` (pinned text, criterion 6, plus a closing full stop) |
| Cancelled note | `cancelled_at` | unchanged (011). It goes after the moved note, so the notes read in the order things happened |

- **The tags are exclusive in practice.** A cancelled or in-progress class is never in `movable_ids` or `cancellable_ids`, so a row has either tags with no actions, or up to two actions. The only exception is `Moved`, which can sit beside the actions.
- **Why `Moved` is hidden on a cancelled class:** the class's state is "cancelled". Its history still shows in the `Moved by …` note, so nothing is lost, and the row keeps a single status word.
- **Why `tag--plain` and `calendar`:** a move isn't a problem or a warning. It's a neutral fact, like `Cancelled`. `calendar` ("the date or time changed") has a different shape from `slash` (cancelled) and `clock` (in progress). So the three are told apart by icon and word, not colour. `calendar` is also the timetable's nav icon, but that's in the sidebar and never next to a tag.
- **Action order: `Move this class` first.** The less final action comes first in reading and tab order.
- **One-off bookings:** `cancellable_ids` is empty for them (011: the whole-booking cancel covers the one class), but `movable_ids` isn't (criterion 6: "each movable class"). So the one-off's single row shows only `Move this class`.
- **After a series move,** every class it changed shows `Moved` and its note (criteria 1 and 6). On a long booking that's repetitive, but it's true, and the note is small (`--fs-help`).

**The CSS amendment** (in section 5n, after `.classrows__action`). There's one new rule, so that only the first action is pushed right and a second action sits beside it:

```css
/* A second action sits beside the first, not pushed apart (brief 012). */
.classrows__action ~ .classrows__action {
  margin-left: 0;
}
```

- The row's existing `gap` (`var(--space-1) var(--space-3)`) separates the two links by 12px. Each link is already 44px tall at every width.
- The 44px height is 44px of **hit area**. The two links' boxes don't overlap, and the 12px gap keeps them apart.
- Below 600px the existing rule (`margin-left: 0`) already applies to every action. The actions wrap together under the date, starting at the left edge.
- At 1400px and up (`.classrows--cols`), a row with a date, a `Moved` tag and both links is about 560px, a little wider than a column. It wraps: the date and tag on line 1, then the actions. That's acceptable. The 1400px threshold stays as it is.

#### D.1.3 The new box: `Change the time of the remaining classes`

It shows only when `can_move_series` (criterion 6). That means a weekly booking with remaining classes and no class in progress.

```html
<section class="box" aria-labelledby="move-series-title">
  <div class="box__head"><h2 class="box__title" id="move-series-title">Change the time of the remaining classes</h2></div>
  <div class="box__body">
    <p class="box__lead">…lead…</p>
    <a class="button button--secondary" href="{% url 'zoom:move_series' link_request.pk %}">Change the time of the remaining classes</a>
  </div>
</section>
```

**The lead** (*design copy*):

- `checks_zoom`: `Moves every class still to come to a new time of day, on the same days, in Zoom too, and emails the requester. To move just one class, use Move this class in the list above.`
- manual: `Moves every class still to come to a new time of day, on the same days, and emails the requester. To move just one class, use Move this class in the list above.`

The entry link is `button--secondary`, as `Cancel this booking` is. It only opens the form, and the form's own button does the work.

**When a class is in progress** the box isn't shown, and there's **no** separate "can't change the time now" notice.
- The row's `In progress` tag already says why.
- 011's `cancel_blocked_message` notice is already on the page with the end time (`… Cancel the rest of this booking after it ends at 11:30 am.`).
- A second, near-identical notice would add noise. If IT does open the series URL anyway, criterion 4's redirect shows criterion 2's in-progress message as a flash.

#### D.1.4 Wireframes

**Desktop (1440). ZL-0042, approved. Wed 7 Oct has been moved to Thu 8 Oct 9:00–12:00, and Mon 12 Oct was cancelled. `zoom` provider.**

```
ZL-0042: Grade 11 Physics                                         Home › Zoom link requests › ZL-0042
┌ ✓ Moved the class to Thu 8 Oct 2026, 9:00 am to 12:00 pm. We emailed nimal@polymath.edu.lk. (x) ┐  flash
┌ ✓ This request was approved by Anjali on Mon 28 Sep 2026, 9:40 am. ────────────────────────────┐  notice--ok
┌ Request ───────────────────────────────────────────────────────────────────────────────────────┐
│ …unchanged (Status, Class, When: Every Mon and Wed, 5–28 Oct 2026, 8:30 am to 11:30 am, …)     │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Classes (8) ───────────────────────────────────────────────────────────────────────────────────┐
│ 1. Mon 5 Oct 2026, 8:30 am to 11:30 am                          Move this class  Cancel this class │
│ 2. Thu 8 Oct 2026, 9:00 am to 12:00 pm  [▦ Moved]               Move this class  Cancel this class │
│    Moved by Anjali on Mon 28 Sep 2026, 10:12 am.                                                │  classrows__note
│ 3. Mon 12 Oct 2026, 8:30 am to 11:30 am  [⊘ Cancelled]                                         │
│    Cancelled by Anjali on Mon 28 Sep 2026, 10:04 am: The school is closed for the sports meet. │
│ 4. Wed 14 Oct 2026, 8:30 am to 11:30 am                         Move this class  Cancel this class │
│ …                                                                                              │
└────────────────────────────────────────────────────────────────────────────────────────────────┘  one column below 1400px
┌ Change the time of the remaining classes ──────────────────────────────────────────────────────┐
│ Moves every class still to come to a new time of day, on the same days, in Zoom too, and       │
│ emails the requester. To move just one class, use Move this class in the list above.           │
│ [ Change the time of the remaining classes ]                                                   │  button--secondary (a link)
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Cancel this booking ───────────────────────────────────────────────────────────────────────────┐
│ …unchanged (011)                                                                               │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400), same booking:**

```
┌──────────────────────────────────────┐
│ ZL-0042: Grade 11 Physics            │
│ Home › Zoom link requests › ZL-0042  │
│ ┌ ✓ Moved the class to Thu 8 Oct  ┐  │  flash
│ │   2026, 9:00 am to 12:00 pm. We │  │
│ │   emailed nimal@polymath.edu.lk.│  │
│ └─────────────────────────────────┘  │
│ …                                    │
│ ┌ Classes (8) ─────────────────────┐ │
│ │ 1. Mon 5 Oct 2026, 8:30 am to    │ │
│ │    11:30 am                      │ │
│ │    Move this class               │ │  44px each, wrap under the date,
│ │    Cancel this class             │ │  side by side when they fit
│ │ 2. Thu 8 Oct 2026, 9:00 am to    │ │
│ │    12:00 pm  [▦ Moved]           │ │
│ │    Move this class  Cancel this  │ │
│ │    class                         │ │
│ │    Moved by Anjali on Mon 28 Sep │ │
│ │    2026, 10:12 am.               │ │
│ │ 3. …  [⊘ Cancelled]              │ │
│ └──────────────────────────────────┘ │
│ ┌ Change the time of the remaining ┐ │
│ │ classes                          │ │  h2 wraps
│ │ Moves every class still to come  │ │
│ │ to a new time of day, …          │ │
│ │ [ Change the time of the         │ │  the label wraps inside the button;
│ │   remaining classes            ] │ │  still 44px or taller
│ └──────────────────────────────────┘ │
│ ┌ Cancel this booking ─────────────┐ │
```

**One-off (ZL-0043), approved:** the Classes list has one row, `1. Mon 5 Oct 2026, 8:30 am to 11:30 am … Move this class`. There's no `Cancel this class` (011) and no series box. The `Cancel this booking` box follows as in 011.

#### D.1.5 Outcomes that land on this page

They all arrive by redirect (302) and show in `partials/messages.html`, directly after the title row (`flash-messages.md`):

| From | Level → family | Icon | Role | Text (pinned) |
|---|---|---|---|---|
| one class moved, emailed | success → ok | `check-circle` | status | `Moved the class to {Tue 6 Oct 2026, 9:00 am to 12:00 pm}. We emailed {email}.` |
| series changed, emailed | success → ok | `check-circle` | status | `Changed the time of {n} classes to {9:00 am to 12:00 pm}. We emailed {email}.`, with `class{n\|pluralize:"es"}` (P2), so one class reads `Changed the time of 1 class to …` |
| the email failed | warning → warn | `alert-triangle` | status | `Moved, but the email to {email} didn't send. Tell them the new times yourself.` |
| any of the above, manual provider | as above | | | the text plus ` This system can't reach Zoom: change it in Zoom too.` |
| not movable (criterion 4) | error → bad | `alert-octagon` | alert | criterion 2's text: `That class has already started, so it can't be moved.`, `{class} is in progress. Change the time of the remaining classes after it ends at {end time}.` or `There are no classes left to change in this booking.` |
| lost a race to a cancel (criterion 17c) | error → bad | `alert-octagon` | alert | `That class was cancelled.` |

- After the redirect the page loads at the top. The flash is the first thing after the h1, and the moved row further down shows `Moved`.
- There's no scroll to the class. A focus jump would skip the flash, which is the confirmation.

### D.2 The move form: `zoom/move_form.html` (new, in the shell)

One template serves both kinds. `occurrence` set means one class; `None` means the series (contract).

#### D.2.1 Structure

| Part | One class (`occurrence`) | Series |
|---|---|---|
| `{% block title %}` | `Move this class: {reference}` | `Change the time: {reference}` |
| `{% block heading %}` (h1) | `Move this class` | `Change the time of the remaining classes` |
| Breadcrumb | Home › `Zoom link requests` (→ `zoom:queue`) › `{reference}` (→ `zoom:detail`) › `Move` (current) | … › `{reference}` › `Change the time` (current) |

- The h1 repeats the words of the link that led here, so IT knows at once that they landed where they meant to. The one-class h1 reads the same for a weekly class and for a one-off.
- The title and breadcrumb words are *design copy*.

**Content, in this order** (the same skeleton as 011's `cancel_confirm.html`):

1. **`move_error`**, when set: `div.notice.notice--bad[role=alert][tabindex=-1][data-error-summary]`, with `alert-octagon` and one `p` holding `{{ move_error }}`, printed as passed (auto-escaped, since the Zoom topic is inside it). There's **no `notice__title`**.
   - **Why no title,** unlike 011's `Not cancelled yet`: every message in criteria 9 and 11–15 already opens with what happened. A fixed title would be untrue for one of them. After a failed restore, `Zoom now has {label}'s meeting … at the new time`, so a title like "Not moved yet" would contradict the sentence under it. The honest message is the whole notice.
2. `partials/error_summary.html` with `form=form`, and `lead="We couldn't move it yet."` (one class) or `lead="We couldn't change the times yet."` (series) (*design copy*). Items 1 and 2 never show together: the service runs only after a valid form.
3. **One `div.box` > `div.box__body` > `div.box__form`** (640px). There's no box head, because the h1 names the page. Inside it:
   1. **`p.box__lead`**, the lead (D.2.2).
   2. **`p`**, what stays the same (D.2.2).
   3. **Manual only** (`not checks_zoom`): the warn notice (D.2.3).
   4. **`dl.facts`**:
      - `Request`: `{reference}: {class_name}` (`break-anywhere`);
      - `Booked on`: `{host_account.label}`;
      - `Requester`: `{requester_name}`, a line break, then `span.text-muted.break-anywhere` `{requester_email}`;
      - `Current time` (one class): `zoom/partials/class_span.html` with `occurrence.starts_at` and `ends_at`. It keeps showing the **stored** time after a failed POST, while the fields keep what was typed;
      - `Current times` (series): `zoom/partials/schedule.html` with `summary=link_request.schedule_summary`.
   5. **The timetable link** (G1): `p` > `a.tap-link` → `{{ timetable_url }}`: `See it on the timetable` (pinned, criterion 5; the same words as the detail page's link under `Booked on`). Then `p.field__help`:
      - `checks_zoom`: `Meetings made directly in Zoom aren't on the timetable. We check those when you press the button below.`
      - manual: `Meetings made directly in Zoom aren't on the timetable.`

      This is the page's "is it free?" help **before** submitting. The real check happens on submit (D.2.5).
   6. **The form** (`div.box__section`): `<form method="post" action="…" novalidate data-busy-form>` with `{% csrf_token %}`. The action is `{% url 'zoom:move_class' link_request.pk occurrence.pk %}` when `occurrence`, otherwise `{% url 'zoom:move_series' link_request.pk %}`.
      - **One class:**
        - `partials/field.html` with `field=form.date narrow=True only`. `min` and `max` come from the widget (G2).
        - `div.field-pair` holding `field.html` for `form.start_time`, then `form.end_time`.
      - **Series:** only the `div.field-pair` holding `start_time` and `end_time`.
      - **`div.form-actions`:**
        - `<button class="button button--primary" type="submit" data-busy-text="…">`: `Move the class and email the requester` (one class) or `Change the times and email the requester` (series) (*design copy*, D.2.4).
        - `a.button.button--quiet` → `zoom:detail`: `Keep the current time` (one class) or `Keep the current times` (series) (*design copy*). It's the safe way out, and it names what's kept, as 011's P4 did.
        - `p.visually-hidden[role=status][data-busy-status]`.
   7. **Series only:** `div.box__section` with `h2.box__subtitle` `Classes that will change ({remaining|length})` (*design copy*), then `zoom/partials/occurrence_list.html` with `occurrences=remaining only`. It shows their **current** times.
      - **Why after the form, not before it as on 011's confirm page:** a series can have 60 classes (30 rows even in two columns). The pinned lead already gives the count, the first date and the last date, so the list is there for checking, not for deciding. Put first, it would push the two fields and the button off every phone screen.

#### D.2.2 Lead text

| Case | `p.box__lead` | Second `p` (*design copy*) |
|---|---|---|
| one class, `checks_zoom` | `Choose a new date and time for this class. We change it in Zoom and email {requester_name} the old and new times.` (*design copy*) | `It stays on {label}, with the same Zoom link and start link. If {label} already has something at the new time, you'll be asked to choose another time. The class can't move to another Zoom account.` |
| one class, manual | `Choose a new date and time for this class. We email {requester_name} the old and new times.` | the same |
| series (both providers) | **pinned** (criterion 5): `The new time applies to every class still to come: {n} classes, from {first date} to {last date}. The days stay the same.` `{n}` is `remaining\|length`; the dates are `remaining.0.starts_at\|class_date` and `(remaining\|last).starts_at\|class_date`. **When one class remains** (P2, accepted): `The new time applies to the one class still to come, on {date}. The day stays the same.` | `They stay on {label}, with the same Zoom link and start link. Classes that have already happened keep their times, and cancelled classes stay cancelled. If {label} already has something at the new time, you'll be asked to choose another time. To change the days or the dates, cancel the rest of this booking and ask the requester to send a new request.` |

- The second paragraph is there for the two decisions IT can't see from the form: a busy account refuses the move, rather than switching accounts (D11), and a series keeps its days (D10). IT learns both before pressing, not from a refusal.
- `{label}` is `link_request.host_account.label`.

#### D.2.3 Manual provider (`checks_zoom` false)

Straight after the second paragraph comes `div.notice.notice--warn` with `alert-triangle`:

- `p.notice__title`: `Check Zoom for clashes first` (006's title, reused).
- `p`: the pinned first sentence `This system can't see meetings made directly in Zoom.`, then (*design copy*) ` Before you move it, check {label}'s meetings in Zoom at the new time. After you move it here, change it in Zoom too.` For the series, `move it` becomes `change the times`.

The success flash repeats the last point (criterion 16's manual suffix).

#### D.2.4 Fields, buttons and busy text

| Field | Label (pinned) | Help | Widget |
|---|---|---|---|
| `date` (one class) | `Date of the class` | *design copy*: `Any date within the next year. It doesn't have to be one of the booking's usual days.` | `DateInput(type=date)` with `min`/`max` (G2), shown `narrow` |
| `start_time` | `Starts at` | the request form's, reused: `Sri Lanka time, on a 5-minute step, like 8:30 am.` | the request form's `TimeInput(type=time, step=300)` |
| `end_time` | `Ends at` | the request form's, reused: `On the same day as it starts.` | the same |

- **Filled in** with the class's current values (one class) or the booking's current times (series) on GET (criterion 5). The form keeps what was typed on every re-render, including after a 409 or a Zoom error.
- **Field-level errors** come from criterion 2's model rules, 005's constants, and the request form's "required" messages. `partials/field.html` renders them unchanged.
- **Where "unchanged" shows:** `That's the time it's already booked for. Choose a different time.` is about the date and time together. The backend decides where it's attached (as a non-field error, or on `start_time`), and the error summary shows it either way. **Recommendation:** a non-field error, because no single field is wrong.

| Button | Idle label (*design copy*) | `data-busy-text` |
|---|---|---|
| one class, `checks_zoom` | `Move the class and email the requester` | `Moving the class in Zoom…` (pinned, criterion 22) |
| one class, manual | the same | `Moving the class…` (*design copy*; there's no Zoom call, as 011's `Cancelling…`) |
| series, `checks_zoom` | `Change the times and email the requester` | `Changing the times in Zoom…` (pinned, criterion 22; P1) |
| series, manual | the same | `Changing the times…` (*design copy*) |

These four rows are also in `docs/design/busy-button.md`'s "Used by" table (G6, amended).

- The labels are verb first, and they say the whole act, including the email. That's the same rule as `Approve and email the link` and `Cancel and email the requester`.
- **`button--primary`, not `button--danger`:** a move is reversible (move it back), keeps the links, and destroys nothing.

#### D.2.5 Availability and clash feedback

The form doesn't check availability while IT types. The contract has no preview, and one isn't needed: a refused move changes nothing, so the submit **is** the check (D2 step 1 runs a fresh Zoom lookup first).

| When | What IT sees | Source |
|---|---|---|
| Before typing | the facts (`Booked on`, `Current time`), the "stays on {label}, can't change account" paragraph, and `See it on the timetable` with its help line | contract, G1 |
| After submit, a clash | the `move_error` notice, focused. The fields keep the typed values, so IT changes the time and presses again | criterion 9 |

**The clash and "couldn't check" states** (criterion 9, pinned, all in the `move_error` notice):

| Case | Status | Example as rendered |
|---|---|---|
| a Zoom meeting at the new time | 409 | `Zoom 02 has a meeting in Zoom at that time: Staff briefing, Tue 6 Oct 2026 at 9:00 am. Choose another time.` |
| a booked class at the new time (including this booking's own other classes, criterion 7) | 409 | `Zoom 02 already has ZL-0042 Grade 11 Physics at that time. Choose another time.` |
| the slot backstop fired | 409 | `Zoom 02 was booked at that time a moment ago. Choose another time.` |
| the account isn't connected | 409 | `Zoom 02 isn't connected to Zoom, so this class can't be moved here. Set up its Zoom connection on the Zoom accounts page.` |
| Zoom couldn't be asked | 200 | `We couldn't check Zoom 02's meetings in Zoom, so nothing was changed. Zoom is busy right now. Try again in a few minutes.` |

**This is the refusal when the account is busy** (D11). The notice names what's in the way and asks for another time, and it never offers another account. The page's second paragraph (D.2.2) has already said why.

- A clash with the booking's own class names the booking itself (`ZL-0042 Grade 11 Physics`). That's true: two classes of one booking can't overlap on one account.
- The timetable link stays just below, so after a refusal IT can look for a free time without leaving the flow.

#### D.2.6 Zoom failure messages (criteria 11–15), in the same notice

The texts are all pinned, and they're printed as the backend passes them in `move_error`. They're listed here so the frontend and the verifier can see every state the notice must hold. In each one, the form keeps the typed values, and the button is the retry.

| Case | Message (pinned) | What it tells IT to do |
|---|---|---|
| Zoom refused, for certain (12) | `We couldn't move it in Zoom: {phrase}. Nothing was changed. {next step}`. `{next step}` is `Try again in a few minutes.`, or for a lasting error `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.` (P6, accepted). It never says "Choose another free account" | retry later, or ask for `Check connection` |
| the update scope is missing (12) | `The Zoom app for {label} is missing the permission to change meetings. Nothing was changed. Ask whoever looks after the server to add the scopes listed in the README.` | pass it on |
| Zoom's daily limit (14) | `Zoom's daily limit for changing {label}'s meetings is used up. Nothing was changed. Try again after 5:30 am on {Tue 29 Sep 2026}.` The day is the next reset, worked out by the backend and printed with `class_date` (P5, accepted) | wait until then |
| no answer, restore worked (13) | `No answer from Zoom, so we put the class back to its old time there to be safe. Nothing was changed. Try again in a few minutes.` | retry later |
| no answer, restore failed (13) | `No answer from Zoom, and we couldn't check what it did. Nothing was changed here. Try again in a few minutes. If the class shows the new time in Zoom, trying again finishes the move.` | retry. Retrying is safe |
| the series came back different (11) | `Zoom scheduled different dates from these classes, so nothing was changed. Tell whoever looks after the system.` | pass it on |
| Zoom changed, not saved, and no undo was answered (11, 13, 15, 32; D.13, D21): `MOVE_NOT_PUT_BACK` | `We couldn't save the new time here, or undo it in Zoom. {label}'s meeting {meeting_id} may still be at the new time in Zoom. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.` | check Zoom, then pass it on. The page and Zoom may disagree, and the message says so |
| Zoom changed, not saved, and the undo was only partly done (11, 13, 15, 32; D.13, D21): `MOVE_PARTLY_PUT_BACK` | `We couldn't save the new time here. We put {label}'s meeting {meeting_id} back to the times saved here, but some classes in Zoom may not match this booking. A cancelled class may have come back, or a class moved on its own may be at the usual time. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.` | check Zoom for a cancelled class that came back or a moved class at the usual time, then pass it on |

**Honesty check** (the reviewer's focus 2):
- Every message says what state Zoom and the app are in, with "Nothing was changed" or "here", and gives one next step.
- None of them is behind a generic title (D.2.1, item 1).
- None uses the words "error", "failed to", "API", "PATCH", "occurrence" or "scope" on its own. "scopes listed in the README" is addressed to the server admin, as the pinned text says.

#### D.2.7 Wireframes

**Desktop (1440), one class, GET, `zoom` provider:**

```
Move this class                                          Home › Zoom link requests › ZL-0042 › Move
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│  ┌──── .box__form, 640px ──────────────────────────────┐                                    │
│  │ Choose a new date and time for this class. We change │  box__lead                        │
│  │ it in Zoom and email Nimal Perera the old and new    │                                    │
│  │ times.                                               │                                    │
│  │ It stays on Zoom 02, with the same Zoom link and     │  p                                 │
│  │ start link. If Zoom 02 already has something at the  │                                    │
│  │ new time, you'll be asked to choose another time.    │                                    │
│  │ The class can't move to another Zoom account.        │                                    │
│  │ Request       ZL-0042: Grade 11 Physics              │  facts                             │
│  │ Booked on     Zoom 02                                │                                    │
│  │ Requester     Nimal Perera                           │                                    │
│  │               nimal@polymath.edu.lk                  │                                    │
│  │ Current time  Wed 7 Oct 2026, 8:30 am to 11:30 am    │                                    │
│  │ See it on the timetable                              │  tap-link                          │
│  │ Meetings made directly in Zoom aren't on the         │  field__help                       │
│  │ timetable. We check those when you press the button  │                                    │
│  │ below.                                               │                                    │
│  │ ──────────────────────────────────────────────────── │  box__section                      │
│  │ Date of the class                                    │                                    │
│  │ Any date within the next year. It doesn't have to be │                                    │
│  │ one of the booking's usual days.                     │                                    │
│  │ [ 07/10/2026   ▾]                                    │  narrow                            │
│  │ Starts at                  Ends at                   │  field-pair                        │
│  │ Sri Lanka time, on a       On the same day as it     │                                    │
│  │ 5-minute step, like 8:30 am. starts.                 │                                    │
│  │ [ 08:30 AM  ]              [ 11:30 AM  ]             │                                    │
│  │ [ Move the class and email the requester ]  Keep the current time │  primary + quiet      │
│  └──────────────────────────────────────────────────────┘                                    │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400), one class, after a Zoom clash (409):**

```
┌──────────────────────────────────────┐
│ Move this class                      │
│ Home › Zoom link requests › ZL-0042  │
│ › Move                               │
│ ┌ ⬣ Zoom 02 has a meeting in Zoom ─┐ │  notice--bad, no title,
│ │   at that time: Staff briefing,  │ │  focused on load
│ │   Tue 6 Oct 2026 at 9:00 am.     │ │
│ │   Choose another time.           │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ Choose a new date and time for   │ │
│ │ this class. We change it in Zoom │ │
│ │ and email Nimal Perera the old   │ │
│ │ and new times.                   │ │
│ │ It stays on Zoom 02, … can't     │ │
│ │ move to another Zoom account.    │ │
│ │ Request                          │ │  facts stack below 600px
│ │ ZL-0042: Grade 11 Physics        │ │
│ │ …                                │ │
│ │ Current time                     │ │
│ │ Wed 7 Oct 2026, 8:30 am to       │ │  still the stored time
│ │ 11:30 am                         │ │
│ │ See Zoom 02's bookings on the    │ │  tap-link, 44px
│ │ timetable                        │ │
│ │ Meetings made directly in Zoom … │ │
│ │ ──────────────────────────────── │ │
│ │ Date of the class                │ │
│ │ Any date within the next year. … │ │
│ │ [ 06/10/2026          ]          │ │  typed value kept
│ │ Starts at                        │ │  field-pair: one column
│ │ Sri Lanka time, on a 5-minute    │ │
│ │ step, like 8:30 am.              │ │
│ │ [ 09:00 AM                     ] │ │
│ │ Ends at                          │ │
│ │ On the same day as it starts.    │ │
│ │ [ 12:00 PM                     ] │ │
│ │ [ Move the class and email the ] │ │  full width, primary
│ │ [ requester                    ] │ │
│ │ [     Keep the current time    ] │ │  full width, quiet
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

**Desktop (1440), series, GET, manual provider:**

```
Change the time of the remaining classes     Home › Zoom link requests › ZL-0042 › Change the time
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│  ┌──── .box__form, 640px ──────────────────────────────┐                                    │
│  │ The new time applies to every class still to come:   │  box__lead (pinned)               │
│  │ 8 classes, from Mon 5 Oct 2026 to Wed 28 Oct 2026.   │                                    │
│  │ The days stay the same.                              │                                    │
│  │ They stay on Zoom 02, with the same Zoom link and    │  p                                 │
│  │ start link. Classes that have already happened keep  │                                    │
│  │ their times, and cancelled classes stay cancelled. … │                                    │
│  │ ┌ △ Check Zoom for clashes first ─────────────────┐  │  notice--warn (manual only)        │
│  │ │   This system can't see meetings made directly  │  │                                    │
│  │ │   in Zoom. Before you change the times, check   │  │                                    │
│  │ │   Zoom 02's meetings in Zoom at the new time.   │  │                                    │
│  │ │   After you change the times here, change them  │  │                                    │
│  │ │   in Zoom too.                                  │  │                                    │
│  │ └─────────────────────────────────────────────────┘  │                                    │
│  │ Request        ZL-0042: Grade 11 Physics             │                                    │
│  │ Booked on      Zoom 02                               │                                    │
│  │ Requester      Nimal Perera …                        │                                    │
│  │ Current times  Every Mon and Wed, 5–28 Oct 2026,     │  schedule partial                  │
│  │                8:30 am to 11:30 am                   │                                    │
│  │ See it on the timetable                              │                                    │
│  │ Meetings made directly in Zoom aren't on the         │                                    │
│  │ timetable.                                           │                                    │
│  │ ──────────────────────────────────────────────────── │                                    │
│  │ Starts at                  Ends at                   │  field-pair                        │
│  │ …help…                     …help…                    │                                    │
│  │ [ 08:30 AM  ]              [ 11:30 AM  ]             │                                    │
│  │ [ Change the times and email the requester ]  Keep the current times │                   │
│  │ ──────────────────────────────────────────────────── │                                    │
│  │ Classes that will change (8)                         │  h2.box__subtitle                  │
│  │ 1. Mon 5 Oct 2026, 8:30 am …   5. Mon 19 Oct 2026 …  │  occurrences--cols                 │
│  │ …                                                    │                                    │
│  └──────────────────────────────────────────────────────┘                                    │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

For the manual series notice, the design-copy sentence reads `Before you change the times, check {label}'s meetings in Zoom at the new time. After you change the times here, change them in Zoom too.`

**Phone (400), series:** the same single column. The fields stack. The two buttons are full width. The class list is one column below 768px and comes last.

#### D.2.8 States

| State | What the user sees |
|---|---|
| Default (GET) | the page as above. The fields hold the current values |
| Validation error | 200. The error summary (`We couldn't move it yet. 1 thing needs your attention.` / `We couldn't change the times yet. …`) is focused. It links to each field. Each field has `aria-invalid` and its pinned error (e.g. `Use a time on a 5-minute step, like 8:30 or 8:35.`, `That's the time it's already booked for. Choose a different time.`). Typed values are kept |
| Loading | the busy button (D.2.4). With no JS, the browser's own indicator. A double press does nothing (busy-button.md), and the server is safe anyway (criterion 17) |
| Clash, refused (409) | the `move_error` notice with criterion 9's message, focused. Typed values are kept (D.2.5) |
| Zoom couldn't be checked (200) | the same notice (D.2.5, last row) |
| Zoom failed (200) | the same notice, with criteria 11–15's message (D.2.6) |
| Nothing to move (criterion 4) | a GET or POST redirects to the detail with an error flash (D.1.5). The form is never shown |
| Success | 302 to the detail with the success or warning flash (D.1.5) |
| Empty | doesn't exist. A class with nothing to move never reaches the form (criterion 4) |
| No permission | anonymous: sign-in, then back here. A plain user: the existing `403.html` |
| Not found | 404 (criterion 4: not approved, a class from another request, or the series form on a one-off) |

### D.3 Error copy in one place

This is covered in D.1.5 (flashes), D.2.5 (clash) and D.2.6 (Zoom). Each message says what happened, whether anything changed, and one next step. The only messages without a "do this next" are the four that say `Tell whoever looks after the system.` That is the next step, because IT can't fix those from the app. The two from D.13 also ask IT to check the meeting in Zoom first.

### D.4 How the rest of the app reflects a move (no template changes)

| Where | What changes | Why no template work |
|---|---|---|
| **Detail, `When`** | a series move: the new time of day (D4). A one-class move: unchanged | `schedule_summary` is recomputed from the request's fields |
| **Detail, Classes** | the new time, the `Moved` tag and the note | D.1.2 |
| **Timetable, month and day** | the class shows at its new date and time on its account. The old slot shows free | `booked()` reads `starts_at`/`ends_at`. There's no "moved" marker on the timetable: an entry means "this account is taken then", and its history is on the detail page (the same reasoning as 011's D.4) |
| **Queue** | nothing. A moved booking stays in `Link sent` | |
| **Start page** (`zoom:start`) | the class time in its facts is the new one. The window follows it (criterion 19): the `too_early` sentence gives the new opening time | `start_state()` reads the stored times. The page doesn't say "moved": the teacher got the email, and the public page shows no history (011 criterion 22) |
| **Start link row and the approval email** | nothing. It's the same link (D1) | |

### D.5 The email (plain text)

#### D.5.1 `moved_subject.txt`

`Class times changed: {reference} {class_name}` (pinned). It's one line, with no trailing newline, like the other subjects.

#### D.5.2 `moved_body.txt`

```
Hello {requester_name},

The IT desk has changed the time of {n} class{n|pluralize:"es"} in your Zoom booking {reference} for {class_name}.

Was: Wed 7 Oct 2026, 8:30 am to 11:30 am
Now: Thu 8 Oct 2026, 9:00 am to 12:00 pm

{% if can_start %}Your Zoom link and start link stay the same. The start link follows the new times.{% else %}Your Zoom link stays the same.{% endif %}

Zoom doesn't tell the people you shared the link with. Please let your students know the new time{n|pluralize}.

If the new time doesn't work for you, reply to the IT desk.

Polymath College IT desk
```

- **`{n}`** is `moves|length`.
- **The pairs.** There's one `Was:` / `Now:` pair per moved class, soonest first, with a blank line between pairs.
  - `Was:` is `{old_start|class_date}, {old_start|class_time} to {old_end|class_time}`.
  - `Now:` is the same from `occurrence.starts_at`/`ends_at`. That's the `Occurrence.__str__` form, so it matches the approval email's class lines.
  - Two lines per pair keep the old and new times vertically aligned in any mail client, which is easier to compare than one long line (P4, now pinned in criterion 18).
- **Pinned** (criterion 18): the subject; the pairs; `Your Zoom link and start link stay the same. The start link follows the new times.`
- **Design copy:** the greeting and opening sentence, the students line, and the reply line. The students line mirrors 011's P5: Zoom doesn't tell students about a changed time either. The reply line mirrors the approval email's `To change the times, reply to the IT desk.`
- **The `else` branch** is P3, now pinned in criterion 18. It needs `can_start` in the context (G3). With the manual provider, the email mentions no start link anywhere. None of the design-copy lines say "start link", so criterion 18's case-insensitive test holds.
- It holds no join link, passcode, start link or host key (criterion 18). "start link" appears only as words, never as a URL.
- It's `{% autoescape off %}`, like the other bodies.

**Rendered, series move of ZL-0042 on Tue 6 Oct (7 classes left, `zoom` provider), shortened:**

```
Hello Nimal Perera,

The IT desk has changed the time of 7 classes in your Zoom booking ZL-0042 for Grade 11 Physics.

Was: Wed 7 Oct 2026, 8:30 am to 11:30 am
Now: Wed 7 Oct 2026, 9:00 am to 12:00 pm

Was: Mon 12 Oct 2026, 8:30 am to 11:30 am
Now: Mon 12 Oct 2026, 9:00 am to 12:00 pm

…

Your Zoom link and start link stay the same. The start link follows the new times.

Zoom doesn't tell the people you shared the link with. Please let your students know the new times.

If the new time doesn't work for you, reply to the IT desk.

Polymath College IT desk
```

### D.6 Copy

**Pinned, and used verbatim:** criterion 2 (all five messages), 5 (the three labels and the series lead), 6 (`Move this class`, `Change the time of the remaining classes`, `Moved`, `Moved by {name} on {when}`), 9 (five messages), 11–16 (all messages, flashes and the manual suffix), 17c (`That class was cancelled.`), 18 (the subject and the start-link sentence), and 22 (`Moving the class in Zoom…`).

**Design copy** (new here; the frontend owns it):

| Where | Text |
|---|---|
| Detail, series box lead | D.1.3 (two variants) |
| Form, titles and h1 | `Move this class: {reference}` / `Change the time: {reference}`; h1 `Move this class` / `Change the time of the remaining classes` |
| Form, breadcrumb | `Move` / `Change the time` |
| Form, leads | D.2.2 (the one-class lead, and the second paragraph for both kinds) |
| Form, facts | `Request`, `Booked on`, `Requester`, `Current time` / `Current times` |
| Form, timetable | the link is pinned (`See it on the timetable`, criterion 5); the help is design copy: `Meetings made directly in Zoom aren't on the timetable.` + ` We check those when you press the button below.` |
| Form, manual notice | the title `Check Zoom for clashes first` (006's) and D.2.3's second and third sentences |
| Form, date help | `Any date within the next year. It doesn't have to be one of the booking's usual days.` |
| Form, buttons | `Move the class and email the requester` / `Change the times and email the requester`; `Keep the current time` / `Keep the current times` |
| Form, busy (manual) | `Moving the class…` / `Changing the times…` |
| Form, error summary leads | `We couldn't move it yet.` / `We couldn't change the times yet.` |
| Form, series list | `Classes that will change ({n})` |
| Email | the opening sentence, the students line, the reply line |

These words never appear on any screen or email: "occurrence", "series" (IT reads "the remaining classes"), "PATCH", "API", "scope" (except inside the pinned README pointer), "recurrence", "slot".

### D.7 Accessibility

- **Landmarks and headings:**
  - **Detail:** h1, then an h2 per box. The new box's h2 is `Change the time of the remaining classes`. No new levels.
  - **Move form:** h1, then (series only) the h2 `Classes that will change`. The field labels are `<label>`s, not headings.
  - Everything is inside the shell's `main`.
- **Label, help and error wiring:** all through `partials/field.html`, unchanged. The label has `for`. The help is `#<name>-help`. On error the field has `aria-invalid="true"` and `aria-describedby="<name>-error <name>-help"`. The error summary links to `#id_date`, `#id_start_time` and `#id_end_time`, and lists non-field errors as text.
- **The `move_error` notice** is `role="alert"`, `tabindex="-1"` and `data-error-summary`, so it's announced and focused on load. Its whole text is the message (no title), so what's read first is what happened.
- **Unique link names:**
  - Each `Move this class` ends with a visually hidden ` on {date}` (criterion 6), as `Cancel this class` does. A screen reader's link list reads `Move this class on Wed 7 Oct 2026`, `Cancel this class on Wed 7 Oct 2026`, …
  - `Change the time of the remaining classes` appears as a heading and one link, so there's one link.
  - `See it on the timetable` (criterion 5) is the only timetable link on the form, so its name is unique on the page. "It" is the class or booking named by the h1 and the facts just above it.
- **Keyboard and focus order:**
  - **Detail, Classes:** per row, `Move this class`, then `Cancel this class`, in date order. Then the series link, then `Cancel this booking`.
  - **Form:** breadcrumb links → timetable link → `Date of the class` (one class) → `Starts at` → `Ends at` → the primary button → `Keep the current time(s)`. That's the visual order. The date and time inputs are native, so their keyboard behaviour is the browser's.
  - **After an error** (validation, clash or Zoom): focus is on the notice or summary (`app.js`, existing). With no JS, it's the first content after the title row. Tab then goes to the timetable link, and next to the first field.
  - **After success:** a normal page load of the detail. The flash is the first content after the h1. `role="status"` for success and warning, `role="alert"` for errors. Closing it returns focus to `<main>` (existing).
  - **Busy submit:** focus stays on the button (`aria-disabled`, not `disabled`), and the busy text is announced through `data-busy-status`.
  - There are no dialogs, so there's no focus to restore after one.
- **Touch targets:** every `.button` is 44px. `.classrows__action` is 44px at every width, with a 12px gap between the two actions. The timetable link and the flash and notice links are `.tap-link` (44px below 768px). The form's buttons are full width below 600px.
- **Status is never colour alone:** `Moved` is `calendar` plus the word, `In progress` is `clock` plus the word, and `Cancelled` is `slash` plus the word. Every notice has an icon and words. The primary button's words say the whole act.
- **Reflow and contrast:** no sideways scroll at 320, 400, 1024 or 1440 in either mode. Class names, emails and Zoom topics wrap anywhere (`break-anywhere`, or inside notices). There are no new colour pairs: `tag--plain`, `notice--bad`/`--warn`, the link colours and `button--primary` are all existing and AA.
- **Times:** every date and time on screen is in `<time datetime>`, through `class_span.html`, `when.html` and `schedule.html`.

### D.8 Progressive enhancement

- **Works with plain HTML and full page loads:** every page, state and message here. That covers the per-row links, the series link, both forms with validation, clash and Zoom errors, the timetable link, and the redirects with flashes. There's no `confirm()` dialog. The form page is the confirmation, and its button names the whole act.
- **Native inputs:** `type=date` and `type=time` with `step=300`. In a browser without them, they fall back to text boxes, and the help text (`like 8:30 am`) plus the server-side rules still guide the user.
- **What `app.js` adds (existing blocks only, no new JS):**
  - error-summary focus on `[data-error-summary]` (the `move_error` notice and the error summary);
  - the busy button on both forms;
  - flash Close on the detail.

  It binds only to `data-*` hooks. With JS off, the button stays as it is and the browser shows its own loading state.

### D.9 Build list for `tmd-frontend`

- **Templates** (each new or changed one starts with the `{# … #}` header naming its purpose and context; every include ends with `only`):
  - **New** `zoom/move_form.html` (D.2).
  - `zoom/partials/class_rows.html` (D.1.2): the `movable_ids` value, the `Moved` tag, the move action and the moved note. Header comment updated.
  - `zoom/detail.html` (D.1): the include's new value, the series box (D.1.3). Header comment gains `movable_ids`, `can_move_series`, `moved_at` and `moved_by`.
  - **New** `zoom/email/moved_subject.txt` and `moved_body.txt` (D.5).
- **CSS** (`static/css/style.css`): the one `.classrows__action ~ .classrows__action` rule (D.1.2). No tokens.
- **Icons:** none new (`calendar` is in the sprite).
- **JS:** none.
- **Component notes:** `docs/design/class-rows.md` and `docs/design/busy-button.md` are already amended (G6). Build from them.

### D.10 Gaps in the context contract (backend to add or confirm)

- **G1 — `timetable_url`** (str) on `zoom/move_form.html`: the month page for the class's month (one class), or the first remaining class's month (series), filtered to the booking's account. Build it with the existing `views.month_page_url(month, account_id)`, the one place a view builds that address (brief 009 D9), so the template doesn't learn the query shape. It drives D.2.1 item 5.
- **G2 — The date's limits on `MoveClassForm`.** The `date` widget carries `min` (today) and `max` (the last date 005's `DATE_TOO_FAR` allows), set on the form, as G7 did for `CancelForm`. `partials/field.html` then prints them from the widget with no `min`/`max` passed. (The alternative is `today`/`latest_date` in the context, as the request form does; the widget keeps it in one place.) The two time fields reuse the request form's widgets (`type=time`, `step=300`), labels, help and "required" messages, as the MVT plan says.
- **G3 — `can_start`** (bool) on `moved_body.txt`, for P3 (criterion 18). It has the same meaning as on `cancelled_body.txt` (011 G5).
- **G4 — Fields read from `link_request` on the form:** `pk`, `reference`, `class_name`, `requester_name`, `requester_email`, `schedule_summary` and `host_account.label`. They're on the object already. Please list them in the contract.
- **G5 — `detail.html` also passes `checks_zoom`** to the series box lead. It already has it (006), so this only confirms it stays.
- **G6 — Component notes: done** (accepted by the main session, and amended by the designer on 2026-09-26):
  - `docs/design/class-rows.md`: the "What a row shows" table replaces 011's "at most one of" rule. It adds the `Moved` state, the CSS rule and `movable_ids`, and updates the States and Behaviour sections.
  - `docs/design/busy-button.md`, "Used by": two `zoom/move_form.html` rows, with criterion 22's labels and busy texts.

**Status: all six resolved.** G1–G5 are in the criteria (5, 18, 27) and the context contract. G6 is done.
- **Not a gap, but recorded:** the old time of a one-class move isn't stored (D5 keeps only `moved_at`/`moved_by`). So the detail page can say `Moved by … on …`, but not "was 8:30 am". The email is where the old time appears. If IT asks for "was" on the page, that's a follow-up field (`moved_from_starts_at`), not part of this brief.

### D.11 Copy proposals

**Status: all seven accepted** by the main session (D14). They're pinned in criteria 5, 6, 12, 14, 16, 18 and 22, which are the source of truth. P4 is settled as two separate lines. The sections above use the pinned text. The proposals are kept below, as written, as the record of why each change was made.

- **P1 — Busy text for the series form.** Criterion 22 pins `Moving the class in Zoom…` for both forms. On the series form nothing named "the class" is being moved; up to 60 classes are changing time. **Proposal:** `Changing the times in Zoom…` on `move_series`, and `Moving the class in Zoom…` on `move_class` only.
- **P2 — One class remaining** (criterion 5's lead, and criterion 16's series flash).
  - Pinned as written, one remaining class reads `…every class still to come: 1 classes, from Wed 28 Oct 2026 to Wed 28 Oct 2026. The days stay the same.`, and the flash reads `Changed the time of 1 classes to …`.
  - **Proposal:**
    - lead, n = 1: `The new time applies to the one class still to come, on {date}. The day stays the same.`;
    - flash: `class{n|pluralize:"es"}`.
- **P3 — Don't mention a start link that was never sent** (the manual provider; 011's P3 precedent). In `moved_body.txt`, when `can_start` is false, the sentence becomes `Your Zoom link stays the same.` It needs G3.
- **P4 — What "one `Was: {old} / Now: {new}` pair" means** (criterion 18). This section reads it as two lines, `Was: …` then `Now: …` (D.5.2). If the criterion meant one line with a literal ` / `, the template prints `Was: {old} / Now: {new}` instead. **Please confirm which**, so the backend's test and the frontend's template agree. The recommendation is two lines: a 60-class email is 60 easy-to-compare pairs rather than 60 long lines.
- **P5 — "Try again after 5:30 am" is ambiguous** (criterion 14). Read at 10:00 am, it means tomorrow; read at 2:00 am, it means today. **Proposal:** the backend works out the next reset and prints its day: `Try again after 5:30 am on {Tue 29 Sep 2026}.` It uses `class_date`, so "today" and "tomorrow" never need computing in words.
- **P6 — The lasting "next step" in criterion 12.** 006's `NEXT_STEP_LASTING` starts `Choose another free account`, which is wrong for a move: a move can't change account (D11). **Proposal:** criterion 12 uses 011's `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.` for lasting errors, and `Try again in a few minutes.` otherwise. That's the same pair criterion 9's "couldn't be asked" row already uses, minus its `, then try again`.
- **P7 — A full stop after the moved note.** `Moved by {name} on {when}.` ends with a full stop, so it reads as a sentence, like the cancelled note does. A test matching the pinned text as a substring still passes.

### D.12 Backend messages reviewed

Added 2026-09-26. The backend added four messages that no criterion pins (Implementation notes, "Decisions and additions" 2, 3 and 9). The texts below were read from the code: `apps/zoom/services.py` (`MOVED_A_MOMENT_AGO`, `TIMES_CHANGED_A_MOMENT_AGO`, `MOVING_AT_THE_SAME_MOMENT`) and `apps/zoom/models.py` (`MOVE_SERIES_OFF_PATTERN`, `END_SAME_DAY`). Each one was checked on four points: is it plain, is it true, does it give one next step, and does it match the pinned move messages, 011's wording and D.11.

**Status: two approved as written, two with proposed replacements.** The replacements are proposals until the main session accepts them. Until then, the code's text stands.

| # | Constant, and where it shows | Text in the code | Verdict | Final text |
|---|---|---|---|---|
| 1a | `MOVED_A_MOMENT_AGO`: the `move_error` notice on the one-class form, 409 (criterion 17a) | `Someone else moved this class a moment ago, to {when}. Your change wasn't made. Choose the time again if it still needs to move.` | **Replace** | `Someone else moved this class a moment ago. It's now {when}. We didn't make your change. If it still needs to move, check the time in the form and press the button again.` |
| 1b | `TIMES_CHANGED_A_MOMENT_AGO`: the `move_error` notice on the series form, 409 (criterion 17a) | `Someone else changed the times of this booking a moment ago, to {times}. Your change wasn't made. Choose the time again if it still needs to change.` | **Replace** | `Someone else changed the time of the remaining classes a moment ago. They're now {times}. We didn't make your change. If they still need a different time, check the times in the form and press the button again.` |
| 2 | `MOVE_SERIES_OFF_PATTERN`: an error flash on the detail page, after the redirect from `zoom:move_series` (GET, or a POST whose locked re-check finds it) | `{occurrence} was moved to another day, so the remaining classes can't be changed together. Move each class on its own instead.` | **Replace** | `The class now on {occurrence} was moved to a different day, so the remaining classes can't be changed together. Move each class on its own instead, with Move this class.` |
| 3 | `MOVING_AT_THE_SAME_MOMENT`: the `move_error` notice on either form, 409 (a lock-wait timeout, or a second deadlock) | `Someone else was changing this booking at the same moment. Nothing was changed. Try again.` | **Approved** as written | the same |
| 4 | `END_SAME_DAY`: a field error on `end_time`, from `Occurrence.move_errors` (no form can trigger it) | `The class must end on the same day it starts. Check the end time.` | **Approved** as written | the same |

Rendered with the fixtures (ZL-0042, Zoom 02):

- **1a:** `Someone else moved this class a moment ago. It's now Thu 8 Oct 2026, 9:00 am to 12:00 pm. We didn't make your change. If it still needs to move, check the time in the form and press the button again.`
- **1b:** `Someone else changed the time of the remaining classes a moment ago. They're now 9:00 am to 12:00 pm. We didn't make your change. If they still need a different time, check the times in the form and press the button again.`
- **2:** `The class now on Thu 8 Oct 2026, 8:30 am to 11:30 am was moved to a different day, so the remaining classes can't be changed together. Move each class on its own instead, with Move this class.`

The placeholders don't change. `{when}` and `{occurrence}` are still `str(occurrence)`, and `{times}` is still `{start} to {end}` built with `class_time`. Only the words around them change.

**Why 1a and 1b change**

- **"Choose the time again" asks for the wrong action.** After the 409 the form re-renders with what IT typed still in the fields (D.2.4). There's nothing to choose again. The step that works is pressing the button, because the view re-reads the class's times on each POST. "Check the time in the form" comes first because the time IT typed may no longer make sense now that the class has moved.
- **The new time gets a sentence of its own** (`It's now …` / `They're now …`). In the series text, `changed the times … to 9:00 am to 12:00 pm` reads as two "to"s in a row. As its own sentence, the time is also easy to compare with `Current time` in the facts below, which now shows the same value (the view re-reads the class before the re-render).
- **`the remaining classes`, not `the times of this booking`.** That's what the series page, its h1 and the detail box call them (D.6: IT reads "the remaining classes").
- **`We didn't make your change`, not `Your change wasn't made`.** It's active voice, like the other move messages (`We couldn't move it in Zoom`, `we put the class back`). The house phrase `Nothing was changed.` isn't used here on purpose, because something **was** changed, by the other person. Saying "nothing" would be untrue.
- **Honesty check:** these messages come only from the locked re-check, before any `PATCH` (`_plan_move`). So "we didn't make your change" is true in Zoom as well as here. The other person's move emailed the requester. If IT presses again, the requester gets a second email whose `Was:` line is the other person's time, which is correct.

**Why 2 changes**

- **Its subject is misleading.** `{occurrence}` prints the class's **new** date. So `Thu 8 Oct 2026, 8:30 am to 11:30 am was moved to another day` reads as if the class left Thu 8 Oct, when that's where it moved **to**. `The class now on …` names the class by where it is, and that's the date IT will find in the Classes list, next to its `Moved` tag.
- **"a different day", not "another day".** The rule also fires when a class was moved onto one of the usual days that another remaining class already has (`day in seen`). "A different day" is true in both cases. "Off the usual days" would be false in the second.
- **The next step names the control** (`with Move this class`), the same way the series box's lead says `use Move this class in the list above` (D.1.3). The flash sits above the Classes list, so no "above" or "below" is needed.
- **Not proposed:** "move that class back to its usual day first". The old date isn't stored (D5; D.10 "not a gap"), so IT can't see where "back" is, and in the `day in seen` case a usual day may not free the booking either. One step that always works is better than two where one might not.
- **Consistency:** the in-progress text starts with a bare `{class}` (`… is in progress.`), and that works because it describes the class as it is now. This one describes a change, so it needs the `The class now on` frame.

**Why 3 is approved:** it follows 011's `Someone else was changing this booking at the same moment. Nothing was cancelled. Try again.` word for word, with `changed` in place of `cancelled`. `Nothing was changed.` is true in every path that returns it: either no `PATCH` was sent, or `_put_zoom_back` restored Zoom before the message was chosen. If the restore fails, one of criterion 11's two messages replaces it (D.13, D21): `MOVE_NOT_PUT_BACK` when no restoring update was answered, or `MOVE_PARTLY_PUT_BACK` when one was answered but the undo didn't finish. `Try again.` is one step, and the button is right below with the typed values kept.

**Why 4 is approved:** it follows 005's pinned `The class must end after it starts. Check the end time.`, and matches the request form's help `On the same day as it starts.` It sits on `end_time`, so the error summary links to that field. It can't show today, and it's right if it ever does.

**Two notes for the main session (not wording, and not changed here):**

- **Recommendation for a follow-up, needs a contract change:** when message 2 applies, `can_move_series` is false, so the `Change the time of the remaining classes` box just isn't shown on the detail page. Unlike the in-progress case (D.1.3), nothing else on the page says why. The `Moved` tag is there, but it doesn't say "that's why the box is missing". Message 2 is only ever seen from a stale page, or when two people act at once. A fix would pass the reason (for example, a `move_series_blocked` string from `series_move_blocked_message()`, shown only for this case) and render the box with that sentence as a `p.box__lead` and no button. That's a context-contract addition, so it's for the planner and the main session to decide, not folded in here.
- **For the reviewer (copy honesty depends on it):** the move views pass `expected` from the class's times **as read at the start of the POST** (`views.py`, `MoveClassView.move` / `MoveSeriesView.move`), not as the form page showed them at GET. So 1a and 1b cover a move committed between that read and the lock, and "a moment ago" is accurate. A move someone else made while this person had the form open for minutes is **not** detected. It's overwritten, and the requester gets both emails. The backend's note 2 says "as the page saw them". If that's the intent, it would need the shown times in the form (a hidden field). That's a behaviour question for the backend and the reviewer, not a copy change.

### D.13 MOVE_NOT_PUT_BACK revisited

Added 2026-10-02. **Status: accepted** by the main session (2026-10-02), and pinned by the planner as D21. The criteria are the source of truth. If they differ from the text here, the criteria win. D.2.6, D.3 and D.12 now use these two messages.

**The problem.** The pinned text says `Zoom now has {label}'s meeting {meeting_id} at the new time`. Since D18 (criterion 32), the put-back has four steps. If step 1, the restoring `PATCH`, lands and a later step fails, Zoom has the old pattern again. It may also have a cancelled class back, or a class moved on its own flattened to the usual time. "At the new time" is then false. That breaks D.2.6's honesty rule.

**The proposal: two messages, chosen by `back.landed`.** `back.landed` is the flag `_put_zoom_back` already sets once a restoring `PATCH` is answered, so no new state is needed. Two messages are better than one here. Each one tells IT what to look for in Zoom: the new time in one case, and a stray or flattened class in the other. Both end with the same next step.

| Constant | When (`_move`'s `else` branch) | Final text |
|---|---|---|
| `MOVE_NOT_PUT_BACK` (text replaced) | `not back.landed`. The forward move was answered, so Zoom certainly took the new time, and no restoring `PATCH` was answered | `We couldn't save the new time here, or undo it in Zoom. {label}'s meeting {meeting_id} may still be at the new time in Zoom. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.` |
| `MOVE_PARTLY_PUT_BACK` (new) | `back.landed`. A restoring `PATCH` was answered, but the put-back didn't finish, or its final check didn't match | `We couldn't save the new time here. We put {label}'s meeting {meeting_id} back to the times saved here, but some classes in Zoom may not match this booking. A cancelled class may have come back, or a class moved on its own may be at the usual time. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.` |

**Which failure each one covers**

| Failure | `certain` | `landed` | Message |
|---|---|---|---|
| One class: the restoring `PATCH` is refused or gets no answer, or there's no occurrence ID to send it to | yes | no | `MOVE_NOT_PUT_BACK` |
| Series, step 1: the restoring `PATCH` is refused or gets no answer, or a second lock race happens before it's sent | yes | no | `MOVE_NOT_PUT_BACK` |
| Series, step 2 (the read-back `GET` or a `DELETE`), step 3 (a per-class `PATCH`), step 4 (the final `GET`), or a final check that doesn't match | either | yes | `MOVE_PARTLY_PUT_BACK` |
| Series, a second lock race after the first try's step 1 landed | either | yes | `MOVE_PARTLY_PUT_BACK` |
| No answer to the move, and no answer to step 1 either (criterion 13) | no | no | criterion 13's `We couldn't check what it did` message, **unchanged** |

**Why each sentence is true in every case it covers**

- **`We couldn't save the new time here`.** In both cases the move's transaction rolled back. The put-back's transaction also stored nothing, since it only stores IDs once the check passes. So the page's `Current time(s)` and the Classes list are true.
- **`may still be at the new time` (with "may", not "now has").** A restoring `PATCH` that got no answer leaves `landed` false, but Zoom may have applied it. The forward move was certain, so the new time is the likely state. It isn't a known one, though.
- **`back to the times saved here`, not "its old time".** In criterion 17a's race, the times saved here are the winner's times, not this person's old ones. That phrase is exact either way, and it echoes the first sentence.
- **`some classes in Zoom may not match this booking`.** This is true after any failure at step 2, 3 or 4. The next sentence names the two ways it can go wrong, so IT knows what to look for. "Classes", "cancelled" and "moved on its own" are words the Classes list already shows (the `Cancelled` and `Moved` tags).
- **Next step:** `Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.` That's one action, then who to ask. The meeting ID is in the message, so IT can find the meeting. "Classes list" is the detail page's `Classes` box, which shows cancelled and moved classes with their tags.
- **Avoided words:** "occurrence", "PATCH", "series", "restore" and "error" are not used (D.6).

**Rendered with the fixtures** (Zoom 02, meeting `81234567890`):

- `We couldn't save the new time here, or undo it in Zoom. Zoom 02's meeting 81234567890 may still be at the new time in Zoom. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.`
- `We couldn't save the new time here. We put Zoom 02's meeting 81234567890 back to the times saved here, but some classes in Zoom may not match this booking. A cancelled class may have come back, or a class moved on its own may be at the usual time. Check that meeting in Zoom against this booking's Classes list, then tell whoever looks after the system.`

**Presentation: unchanged.** Both texts go in the same `move_error` notice (D.2.1, D.7): `notice--bad`, `role="alert"`, focused on load, with no title. The typed values are kept. Neither text needs a new class, icon or template change, because the template prints `move_error` as passed.

**Knock-on edits, once this is accepted (for the planner and backend, not done here):**

- **Criteria.** Criterion 11's last bullet, 13's "series only" bullet, 15 and 32 each name `MOVE_NOT_PUT_BACK`. They need to name the right one of the two.
  - Criterion 32's test `test_a_failure_at_any_step_of_putting_it_back_says_so`: the step 1 case expects `MOVE_NOT_PUT_BACK`. The step 2 `GET`, step 2 `DELETE`, step 3 `PATCH`, step 4 `GET` and mismatch cases expect `MOVE_PARTLY_PUT_BACK`.
  - `test_a_second_lock_race_while_putting_it_back_says_so` and `test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back` expect `MOVE_PARTLY_PUT_BACK`.
- **`MOVE_MESSAGES`** gains `MOVE_PARTLY_PUT_BACK`, so the "no other account" scan covers it.
- **The `ERROR` log line** says `Zoom meeting … has the new time`, which is false in the same cases. Suggestion: `Moving ZL-…: Zoom meeting … doesn't match this database: <move's error class> (putting it back: <failure>, restoring update answered: yes/no)`. This is log text, so it's the backend's call. It's flagged here because it repeats the same false claim.
- **One-class edge (backend's call).** For one class, `landed` with `not done` can only mean the put-back's no-write transaction failed after the `PATCH` was answered. Zoom then matches this database, so that case could be treated as `done`. If it isn't, `MOVE_PARTLY_PUT_BACK` still applies there, because every claim in it is a "may".
- **This section's own references: done** (2026-10-02, after acceptance). D.2.6's last row is now two rows. D.3 says "four" messages. D.12's "Why 3 is approved" points to these two messages (D.13, D21).

### D.14 Daily limit outside a move

Added 2026-10-02, for review round 2's should-fix 1. **Status: a proposal**, for the planner to pin. Until then, the current text stands.

**The problem.** A daily-limit 429 is `ZoomDailyLimit`, which is `lasting=True`. It can now reach every Zoom call, not only the move `PATCH`. Two parts of each message are then wrong:

- **The next step.** The lasting step says "press Check connection" or "Waiting won't fix this". Neither helps with a daily limit, and the second is untrue.
- **The reason.** The error's own phrase is `Zoom's daily limit for changing meetings is used up`. That's wrong for a list call (approve's and the move's look-up, and the approve page's account list), for a create, and for Check connection.

**One shared reason, one shared next step.** Every caller builds its message from the error's phrase, either as `{phrase}` or as `{reason}` (its sentence form). So the fix is to change the phrase **once**, in `ZoomDailyLimit.__init__`:

| | Text |
|---|---|
| **Phrase** (`user_message`) | `Zoom's daily limit for this account is used up` |
| **Sentence form** (`reason_sentence`, unchanged code) | `Zoom's daily limit for this account is used up.` |
| **Reset sentence** (one helper, built from `zoom_daily_reset()`, P5's wording exactly) | `Try again after {time} on {date}.` `{time}` is `class_time(reset)`, which is always `5:30 am` in Colombo. `{date}` is `class_date(reset)`. |

**Why one phrase works for all four:**

- **"For this account".** This is the house form. 006's phrases already say `this account's connection details` and `the Zoom app for this account`. In every place the phrase appears, the account is named nearby: by `{label}` in the same message, or by the account-list row the reason sits in.
- **Not "for changing meetings".** The phrase names no kind of call, so it's true for a list, a create, a delete and Check connection alike.
- **Not tied to Zoom's quota rules.** The phrase doesn't say whether the limit is the user's or the meeting's, or how many calls are allowed. Zoom has both kinds, and the advice ("after the reset") is the same for either. "Choose another free account" is still sound for approve, because a create counts against the account user's own quota.
- **The move `PATCH` keeps its pinned text.** Criterion 14's `Zoom's daily limit for changing {label}'s meetings is used up. …` uses its own template, not the phrase, and "changing" is exact for a `PATCH`. It's unchanged.

**The final texts** (rendered: Zoom 02, at Mon 28 Sep 2026, 10:00)

| # | Where | Template, and the change | Rendered |
|---|---|---|---|
| 1a | **Approve, the create** (`create_failed_message`, via `next_step`) | `CREATE_FAILED`, unchanged. For `ZoomDailyLimit`, `next_step` returns `Choose another free account, or wait for this one. Try again after {time} on {date}.` | `We couldn't make the meeting in Zoom: Zoom's daily limit for this account is used up. Nothing was booked. Choose another free account, or wait for this one. Try again after 5:30 am on Tue 29 Sep 2026.` |
| 1b | **Approve, the look-up before it** (`lookup_failed_message`, via the same `next_step`) | `LOOKUP_FAILED`, unchanged. The same daily next step | `We couldn't check Zoom 02's meetings in Zoom, so nothing was booked. Zoom's daily limit for this account is used up. Choose another free account, or wait for this one. Try again after 5:30 am on Tue 29 Sep 2026.` |
| 2 | **Cancel's `DELETE`** (`cancel_failed_message`) | `CANCEL_FAILED`, unchanged. For `ZoomDailyLimit`, the next step is the reset sentence alone | `We couldn't cancel it in Zoom: Zoom's daily limit for this account is used up. Nothing was cancelled. Try again after 5:30 am on Tue 29 Sep 2026.` |
| 3 | **The move form's step-1 look-up** (`move_lookup_failed_message`) | `MOVE_LOOKUP_FAILED`, unchanged. For `ZoomDailyLimit`, the next step is the reset sentence alone | `We couldn't check Zoom 02's meetings in Zoom, so nothing was changed. Zoom's daily limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.` |
| 4 | **Check connection** (`check_connection`) | A new template, `CHECK_DAILY_LIMIT` = `Couldn't check {label} with Zoom: {phrase}. Try again after {time} on {date}.`, chosen before the `lasting` test. It drops `Waiting won't fix this` (untrue) and `give them the Zoom error number` (there isn't one) | `Couldn't check Zoom 02 with Zoom: Zoom's daily limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.` |
| 5 | **The approve page's account list** (`services.py:448`, the "unavailable" row's reason). **Not in the reviewer's list**, but it shows the same phrase | No code change: it prints `reason_sentence` | `Zoom's daily limit for this account is used up.` The row's own fix links stay as they are (`docs/design/availability-list.md`) |

**Why each next step reads this way:**

- **Approve: "Choose another free account, or wait for this one."** The reviewer asked for "Choose another free account" first, since another account has its own quota, and that's the quick fix. "Or wait for this one" makes the reset sentence after it clearly about **this** account. Without it, `Choose another free account. Try again after …` reads like two steps to do in order. The reset sentence stays P5's, word for word.
- **Cancel, move look-up and Check connection: the reset sentence alone.** There's no other account to offer. A cancel or a move can't change account (D11), and Check connection is about one account. Waiting until the reset is the only true step. None of them says "Check connection" or "another free account", so D11's scan of the move messages still passes.
- **Every message keeps its "nothing was …" part.** Each one keeps the same shape: what happened, what didn't change, then when to try again. A daily-limit 429 is a certain refusal, so "nothing was booked / cancelled / changed" stays true.
- **Words avoided:** "429", "rate limit", "quota", "UTC" and "API". The reset is shown as a Colombo time and day (P5), so "today" or "tomorrow" never needs working out.

**Presentation: unchanged.** Each message appears where its caller's messages already go: the approve form's notice, the cancel form's notice, the move form's `move_error` notice, and the accounts page's flash. Each keeps its existing role, icon and focus. There are no new classes, icons or templates.

**For the planner and backend (not done here):**

- **Code:**
  - one helper for the reset sentence, which `move_failed_message`'s `MOVE_DAILY_LIMIT` may also use (its text unchanged);
  - the daily check runs **before** `lasting` in `next_step`, `cancel_failed_message`, `move_lookup_failed_message` and `check_connection`;
  - `ZoomDailyLimit`'s phrase and its docstring change ("the move's message names the day" becomes "every caller names the day").
- **Tests:** one per caller (1a, 1b, 2, 3, 4), asserting the rendered text above at the frozen now. Also one for row 5's reason. Existing tests that assert `str(ZoomDailyLimit())` only check that Zoom's own text is absent, so they're unaffected.
- **Not changed:** `ZoomDailyLimit` stays `lasting=True`. The daily check simply comes first, so no other lasting error changes.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-frontend (2026-09-26)

**Files changed**

| File | Change |
|---|---|
| `templates/zoom/partials/class_rows.html` | D.1.2: takes `movable_ids`. Row order is: date, `Moved` tag (`tag--plain` + `calendar`, only when `moved_at` and not `cancelled_at`), `Cancelled` or `In progress` tag, `Move this class` (`pk in movable_ids`), then `Cancel this class` (`pk in cancellable_ids`). Each action is a separate `.classrows__action` link whose visually hidden text ends ` on {class_date}`. Under the row come the notes: `Moved by {name} on {when}.` (whenever `moved_at` is set) and then the cancelled note. The actions depend only on the two sets. The template makes no movability decision of its own. Header comment rewritten. |
| `templates/zoom/detail.html` | The include passes `movable_ids=movable_ids`. The new `Change the time of the remaining classes` box (`can_move_series`) sits before `Cancel this booking`, and links to `zoom:move_series` as a `button--secondary`. Criterion 27: `checks_zoom` only adds ` in Zoom too,` to the lead. The box has no notice. Header comment gains `movable_ids`, `can_move_series`, `moved_at` and `moved_by`. |
| `templates/zoom/move_form.html` (new) | D.2, both kinds. Content order: the `move_error` notice (`notice--bad`, `role=alert`, `tabindex=-1`, `data-error-summary`, no title, auto-escaped); the error summary (lead `We couldn't move it yet.` or `We couldn't change the times yet.`); then one `box__form` holding the lead (pinned series lead with n = 1 / n ≥ 2, one-class lead chosen by `checks_zoom`), the second paragraph, the manual `Check Zoom for clashes first` warning (only when `not checks_zoom`, with the D.2.3 wording per kind), the facts (`Current time` via `class_span`, `Current times` via `schedule`), `See it on the timetable` → `timetable_url` with its help line, and the form. The form holds `date` (one class only, `narrow`; `min` and `max` come from the widget), a `field-pair` with `start_time` and `end_time`, the primary button with `data-busy-text` per criterion 22, `Keep the current time(s)` and the `data-busy-status` region. On the series form, `Classes that will change ({n})` and `occurrence_list` follow the form. |
| `templates/zoom/email/moved_subject.txt` (new) | `Class times changed: {reference} {class_name}`, one line, the same shape as the other subjects. |
| `templates/zoom/email/moved_body.txt` (new) | D.5.2: `Was:` and `Now:` on two lines per moved class, with a blank line between pairs. Both lines use `class_date` and `class_time` (the `class_span` form). Then either `Your Zoom link and start link stay the same. The start link follows the new times.` (`can_start`) or `Your Zoom link stays the same.`, then the students line (`time{n\|pluralize}`) and the reply line. `autoescape off`. |
| `static/css/style.css`, section 5n | One rule straight after `.classrows__action`: `.classrows__action ~ .classrows__action { margin-left: 0; }`. No tokens, and the existing below-600px rule is unchanged. |

No new icons (`calendar` was already in the sprite), no new JS, no `{% static %}` references and no Python.

**Spec deviations:** one, by main-session ruling on D.2.2 (2026-09-26).
- **The ruling:** the move form follows the email's rule (P3). When `checks_zoom` is false (the manual provider), the screen doesn't mention a start link.
- **The change:** both second paragraphs read `…with the same Zoom link and start link.` only when `checks_zoom` is true, and `…with the same Zoom link.` with the manual provider.
- **Why `checks_zoom`:** it's the flag the form's contract already has. The manual provider is the only one that is both not `checks_zoom` and not `can_start`.
- **Re-checked by stub render:** "start link" appears 0 times in the manual one-class and series forms, and once (that paragraph) with `checks_zoom`.

**Context contract notes for the backend**

- **The `moves` entries for `moved_body.txt` need attribute access:** `move.old_start`, `move.old_end` and `move.occurrence`. The contract's `{old_start, old_end, occurrence}` works as a dict or a namedtuple. A plain `(old_start, old_end, occurrence)` tuple, as in `MoveResult.moves`' annotation, would render blank lines.
- **Where the "unchanged" error goes:** it can be attached anywhere. The error summary lists non-field errors as text and field errors as links. D.2.4 recommends a non-field error.
- **`remaining` must be non-empty on the series form**, because the lead reads `remaining.0` (criterion 4 already guarantees this).
- No gaps found beyond these.

**Self-check**

- **Stub render.** I ran a scratch script inside the dev `web` container with a scratch URLconf that adds stub `zoom:move_class` and `zoom:move_series` routes (the backend's weren't in `apps/zoom/urls.py` yet), stub move forms matching G2, and `SimpleNamespace` objects. The container copy was deleted afterwards. All 15 renders passed:
  - detail pages: fake and manual providers, no series box, and a one-off booking;
  - move forms: one class and series with `checks_zoom` true and false, a series with one class left, a validation error and a clash;
  - emails: `can_start` true and false, one move, and the subject.
- **What the renders showed:**
  - The series box lead matched criterion 27's two sentences exactly, and neither box had a `notice--warn` or `Check Zoom for clashes first` (count 0 and 0).
  - The rows came out as designed: both actions in order, `Moved` with its note, a cancelled class with the moved note and then the cancelled note (no `Moved` tag), and a one-off row with only `Move this class`.
  - The date input rendered `min`, `max` and `required`. The time inputs rendered `step="300"`.
  - The busy texts were right for all four cases.
  - After an error, `aria-invalid` and `aria-describedby="end_time-error end_time-help"` were set, and the typed values were kept on a clash.
  - A `<`…`>` topic came out escaped in `move_error`.
  - The manual email has no `start link` (`grep -ic` = 0).
- **Not yet run.** `pytest --reuse-db apps/zoom apps/core` and the HTTP render on 8010 both need the backend's views, URLs and forms. The backend's "backend pytest run finished" note wasn't in this brief when I checked, so both are left for the main session to trigger, or for the verifier.

#### Fix cycle 1 (tmd-frontend, 2026-09-26)

**Files changed**

- `templates/partials/field.html` (criterion 28, D15): the value now comes from `field.subwidgets.0.data.value` (bound once in the partial's `{% with %}`) instead of `field.value`. The header comment explains why.
  - **Why this approach:** `BoundField.subwidgets[0].data` is the widget's own template context, and its `value` is `BoundField.value()` passed through the widget's `format_value()`. It's the same value Django's own `input.html` and `textarea.html` print. It's one expression, template-only, and it keeps the partial's hand-built markup (class, `aria-*`, `min`/`max`, `narrow`). Printing `{{ field }}` wasn't used: the class and the `aria-invalid`/`aria-describedby` wiring can't be passed to it from a template without Python changes.
  - **Behaviour:** an unbound date prints ISO (`2026-10-07`). A bound value is printed as typed, even when invalid (`25:99` stays `25:99`, because `format_value` returns a string unchanged). An empty value now gives no `value` attribute instead of `value=""`, which browsers treat the same way. The password guard from 010 is kept, as an explicit check on top of `PasswordInput` blanking its own value.
- `templates/zoom/move_form.html` (criterion 30): `{{ form.shown }}` straight after `{% csrf_token %}`, in the one `<form>` both kinds share. The header comment lists `shown`.
- `templates/zoom/detail.html` (criterion 31): the series box now shows when `can_move_series or move_series_blocked`. When `move_series_blocked` is set, the box's only content is `<p class="box__lead">{{ move_series_blocked }}</p>`, auto-escaped with no button. Otherwise it's unchanged (criterion 27's lead and button). The in-progress case still has no box, because the backend sets neither variable then. The header comment is updated.
- No CSS, JS, icon or partial additions.

**Spec deviations:** none in the templates. The time pre-fill (next item) needs a backend change.

**Context contract gaps**

- **G-F1 (blocks criterion 28's `08:30`; backend, one line each):** the widget's own formatting of a `time` is `08:30:00`, not `08:30`. `TimeInput` has no `format`, so it uses `TIME_INPUT_FORMATS[0]`, which is `%H:%M:%S` for `en`. I checked this in the dev container: `LinkRequestForm.Meta.widgets["start_time"].format_value(time(8, 30))` gives `'08:30:00'`, and the move-series page renders `value="08:30:00"`. That's a valid HTML5 time, which browsers fill in, but the verifier's test asserts `value="08:30"`, so it will still fail on the times. The date already passes (`2026-10-07`).
  - **Fix:** add `format="%H:%M"` to the two `forms.TimeInput(...)` widgets in `LinkRequestForm.Meta.widgets` (`apps/zoom/forms.py`, `start_time` and `end_time`). This mirrors `MoveClassForm.date`'s `format="%Y-%m-%d"`. The move forms copy these widgets, so it's fixed in one place. It isn't pre-formatting `initial`.
  - **Safe for 005:** its time fields have no initial value, and a bound value is a string, printed as typed.
- **G-F2:** the error summary loops over every field, hidden ones included. If `shown`'s problems are raised as a *field* error on `shown` rather than a non-field error, the summary would link to a hidden input. The contract says non-field, so this is only a note for the backend.
- **The criterion 28 guard test isn't written.** No test in `apps/` renders the request form with `25:99`. It's Python, so I didn't write it (main session's instruction). Checked by hand instead: `LinkRequestForm(data={first_date: "2026-10-05", start_time: "08:30", end_time: "25:99"})` through the partial renders `value="2026-10-05"`, `value="08:30"` and `value="25:99"` (the last with `aria-invalid="true"`). An unbound request form renders the time with no `value`.

**Self-check:** see "Fix cycle 1 self-check" below, added once the backend's fix-cycle run has finished.

#### Review round 1 nits (tmd-frontend, 2026-10-02)

- **`templates/partials/field.html`:** both attrs loops now read `{% for key, attr_value in attrs.items %}`, so they no longer shadow the outer `value`. The header comment now says the partial must never be given a choice widget (select, checkbox or radio), because for those `field.subwidgets.0` is the first option. **`templates/zoom/detail.html`:** added the missing space in the header comment (`criterion 31), in_progress_id`). No Python, CSS, JS or new partials. **Spec deviations and contract gaps:** none.
- **Self-check:** I rendered `partials/field.html` with stub contexts (`manage.py shell` in the dev `web` container; the script lives only in the session scratchpad) for every field any template passes to it. That's 11 forms: `LinkRequestForm`, `CancelForm`, `ApproveForm` (manual details), `RejectForm`, `MoveClassForm`, `MoveSeriesForm`, `HostAccountForm`, `OwnPasswordChangeForm`, `StaffSetPasswordForm`, `StaffCreateForm` and `StaffChangeForm`. Each field was rendered unbound, bound as typed (including `<`, `&` and quotes), and bound invalid (for example `25:99`), which gives 117 snippets: 30 with `aria-invalid`, 56 with a `value`, and no typed password echoed back. The before and after outputs were byte-identical: `diff` printed nothing and exited 0, `cmp` agreed, and both files have SHA-256 `2e7e4e7a…30172e69dfe5e63b13974230642c21`. Over HTTP on 8010 (dev), `/zoom/request/` returned 200 with 10 `.field` blocks. I didn't run pytest, as instructed, because the backend was running it.

### tmd-django-backend (2026-09-26)

**Files changed**

| File | Why |
|---|---|
| `apps/zoom/models.py` | `Occurrence.moved_at` / `moved_by`; criterion 2's rules and copy (`move_errors`, `move_blocked_message`, `series_move_errors`, `series_move_blocked_message`, `can_move_series`, `series_new_times`, `series_span_dates`); `new_slots()`; `OccurrenceQuerySet.clashing()` (criterion 7's database side, plain or locking); `is_remaining()` as the one rule behind `can_be_cancelled` / `can_be_moved`; `is_on_slot_step()` shared with `LinkRequest.clean()`. **Rename:** `cancellable_classes` → `remaining_classes` (MVT plan), callers updated in `services.py`, `views.py` and `tests/test_cancel_models.py`. No template used the old name. |
| `apps/zoom/migrations/0008_move_classes.py` (new) | The two nullable columns. Reversible (schema only). |
| `apps/zoom/errors.py` | `ZoomDailyLimit` (lasting). See the Zoom facts below for why `zoom_api` never raises it. |
| `apps/zoom/zoom_api.py` | `ZoomClient.patch()`. Like a create, it's never repeated after a timeout. |
| `apps/zoom/providers.py` | `update_payload()` (only `start_time`, `timezone`, `duration`, plus `recurrence` for a series); `update_occurrence` / `update_series` / `meeting_snapshot` on the base (no-ops for `manual`), the fake and the live provider; `weekly_starts()`. The fake gains `patched`, `update_errors` (a queue, so a test can let the move through and fail the restore) and `series` (so `meeting_snapshot` answers the way Zoom would, and a delete removes the occurrence). |
| `apps/zoom/services.py` | `move_class()`, `move_series()`, their shared `_move()` (step 1 `_move_check_first`, step 2 `_move_once`, `_move_series_in_zoom`, the compensating `_put_zoom_back`), `MovedClass`, `MoveResult`, `moved_message()`, `send_moved_email()`, `zoom_daily_reset()`, `move_failed_message()`, `move_lookup_failed_message()`, every pinned message, and `MOVE_MESSAGES` for the "another account" scan. `Outcome` gains `MOVED` and `INVALID`. |
| `apps/zoom/forms.py` | `MoveClassForm` (G2: the date widget's `min`/`max` are set on the form) and `MoveSeriesForm`. Both time fields are built from `LinkRequestForm.Meta` (label, help, messages, widget), so there's one definition. `clean()` asks the models' rules. |
| `apps/zoom/views.py` | `_MoveView`, `MoveClassView`, `MoveSeriesView` (`non_atomic_requests`); the detail context gains `movable_ids` and `can_move_series` and joins `moved_by`. |
| `apps/zoom/urls.py` | `zoom:move_class` (`requests/<pk>/classes/<occurrence_pk>/move/`) and `zoom:move_series` (`requests/<pk>/move/`). |
| `apps/zoom/tests/conftest.py` | A stub for `zoom/move_form.html`. |
| `apps/zoom/tests/test_move_models.py`, `test_move_services.py`, `test_move_views.py`, `test_move_race.py` (new) | Criteria 1–19, 22's context, 23 and 27 (see below). |

**Context contract as implemented: no deviations.**

- **`zoom/move_form.html`:**
  - `link_request`: the approved `LinkRequest`, `host_account` joined.
  - `occurrence`: the class, or `None` for the series.
  - `remaining`: `[]` for one class. For the series, the remaining classes, soonest first. **It's never empty on this page:** a series with none remaining redirects before rendering (criterion 4).
  - `form`, `move_error` (str or `None`, in final form), `checks_zoom` (bool).
  - `timetable_url`: `views.month_page_url(month, host_account_id)` for the class's month, or the first remaining class's month.
  - GET fills the form with the current values. A re-render after a failed POST keeps what was typed, and `occurrence` / `remaining` are re-read fresh, so the facts show the stored time.
- **`zoom/detail.html`:**
  - `movable_ids`: set of pks, the remaining classes of any approved booking; empty otherwise.
  - `can_move_series`: bool.
  - `checks_zoom`: unchanged.
  - `occurrences`: now also joins `moved_by`, so the `Moved by …` note costs no extra query.
- **Emails:** `moved_subject.txt` / `moved_body.txt` get `link_request`, `moves` and `can_start` (G3).
  - `moves` is a list of `services.MovedClass`, a frozen dataclass with named fields `old_start`, `old_end` and `occurrence`, as the frontend asked. The `occurrence` is at its new times.
- **Status codes:** 302 on success and for "nothing to move", 409 for a clash (criterion 9's 409 rows, and the lock races below), 200 for everything else.

**Decisions and additions (for the reviewer)**

1. **Compensation restores what the database holds, not a remembered "old" value.**
   - `_put_zoom_back` runs after the rollback, in its own short transaction. It locks the request, then the classes, and sets Zoom to the times stored *now*.
   - That's the old time, or the winner's time when another move of the same class committed first (criterion 17a). It's idempotent, so it's right whatever an unanswered `PATCH` did (D2).
   - It runs whenever an update may have reached Zoom (`changed`) and the move didn't commit. That includes a deadlock-retried attempt that then stopped for another reason.
   - **The messages pick themselves from what's true:**
     - an unanswered `PATCH` only: criterion 13's two messages;
     - Zoom certainly changed and the restore worked: the failure's own message;
     - the restore failed: criterion 11's "couldn't be saved here or put back", plus one `ERROR` line with the reference, the meeting ID and the error class.
   - A plain unexpected exception is re-raised after a successful restore (a 500, as before).
2. **Criterion 17a's "already moved" state.**
   - The views pass `expected`: the class's times (or the booking's `start_time`/`end_time`) as the page saw them. After the lock, a mismatch stops the move before any `PATCH`, with a 409.
   - **New, unpinned copy (designer, please check):**
     - `Someone else moved this class a moment ago, to {when}. Your change wasn't made. Choose the time again if it still needs to move.`
     - the series version, `Someone else changed the times of this booking a moment ago, to {times}. …`
     - `Someone else was changing this booking at the same moment. Nothing was changed. Try again.` (a lock-wait timeout or a second deadlock, as 011 has for cancel).
3. **A series can't be changed when a remaining class was moved to another day** (new, unpinned: `{class} was moved to another day, so the remaining classes can't be changed together. Move each class on its own instead.`).
   - **Why:** Zoom's series can only hold the pattern's days. The criterion 11 read-back could never match, so every try would spend two of Zoom's 100 daily updates (the move and the restore) and end in DATES_DIFFER.
   - **How it shows:** it's treated like "in progress": `can_move_series` is false, and the series URL redirects with it as a flash.
   - A class moved to another *time* on its own day doesn't block it.
4. **The series read-back comes before the deletes** (deviation from criterion 10's listed order "PATCH, then DELETE, then GET"). The order is `PATCH` → `GET` → a `DELETE ?occurrence_id=` for each pattern date in the span without a remaining class.
   - **Why:** Zoom's docs don't say occurrence IDs survive a series update, so the IDs to delete are read, not guessed.
   - **How criterion 11 is checked:** Zoom's non-deleted classes from the first remaining class on, less the ones just deleted, must equal the remaining classes at their new times, one to one. The new IDs are stored.
   - There's still exactly one `GET`, and everything is before the commit (criterion 8's series test pins it).
   - `end_times` is the number of pattern dates from the first to the last remaining class.
5. **A series restore is one `PATCH`** anchored at the first remaining class, as the brief says. Classes cancelled earlier may reappear in Zoom after a restore; only a failed series move leads there. This is R1's residual risk, and 013's reconcile would catch it. Worth a look in review.
6. **A blank occurrence ID** is looked up inside the lock (011's `occurrence_id_for`) and stored with the move. If Zoom has no such class, it's `ZoomMeetingNotFound` (lasting): "We couldn't move it in Zoom: Zoom error 3001. …".
7. **Lock order:** request → account → the booking's classes → the locking clash re-check (other classes and their requests, as `availability_for(lock=True)` does). The same order as `approve()` and `cancel()`; deadlocks are retried once. The only call made with locks held beyond the brief's is the occurrence-ID lookup `GET`, and only when no ID was stored.
8. **`manual`** makes no Zoom call at all, but the database checks, locks and slot backstop still apply.
9. **The unpinned `END_SAME_DAY`** (`The class must end on the same day it starts. Check the end time.`) exists for the model rule. No form can trigger it, because both times share one date.

**The Zoom facts (criteria 10 and 14), checked 2026-09-26**

- **An occurrence-level `PATCH` can change the date.** Zoom's Meetings API spec (`https://developers.zoom.us/api-hub/meetings/methods/endpoints.json`, `PATCH /meetings/{meetingId}`) says the `occurrence_id` query parameter supports changing `start_time`, `duration`, `agenda` and some settings. `start_time` is a full date-time, and nothing restricts it to the same day. **No blocker.**
- **Whether the `occurrence_id` survives an occurrence-level `PATCH`: the docs don't say.**
  - The implementation keeps the stored ID and makes no read-back, so criterion 8's one-class order is exactly one `PATCH`. This follows how Zoom's IDs behave in practice (they name the originally scheduled class).
  - **The owner's live check (criterion 26.1) must confirm it:** after moving one class, `GET /meetings/{id}` should still list the same `occurrence_id`, at the new time.
  - **If it doesn't,** a later cancel of that class would address a stale ID. The fix is a read-back `GET` after the one-class `PATCH`, and that's a one-function change in `_move_once`.
- **Scope:** the spec lists the granular scope `meeting:update:meeting:admin` for this endpoint (matches D8 and criterion 20). The rate label is `LIGHT`, and the endpoint's own note is "100 requests per day" per meeting.
- **Telling a daily-limit 429 from a per-second one** (https://developers.zoom.us/docs/api/rate-limits/):
  - The docs document the user-level limit: "100 create/update requests per day (UTC) per user", reset at 00:00 UTC.
  - They tell the two 429s apart **only by the error message's wording**: "You have reached the maximum per-second rate limit for this API…" versus "You have reached the maximum daily rate limit for this API. Refer to the response header…".
  - The `PATCH` spec lists only code 4001 (per second) under 429. **No distinct code, and no header is named.**
  - So, per criterion 14's rule, **every 429 stays `ZoomBusy`**, and `zoom_api` never reads Zoom's message text (006's rule).
  - `ZoomDailyLimit` and its P5 message exist and are tested through the fake provider, ready for when Zoom documents a signal. **For the docs writer:** the README should note the limit (criterion 14's fallback).
  - **Open for the owner, not blocking:** matching the documented message text would make the daily-limit message work today. That means amending 006's "Zoom's text is ignored" rule, so it's the owner's call.

**Tests** (all new, pytest style, no network, no `@responses.activate`):

| File | Criteria |
|---|---|
| `test_move_models.py` (30) | 1, 2 (every rule and pinned string), 3's slot helper, 7's `clashing()`, and the rename |
| `test_move_services.py` (62) | 3, 7, 9 (all five rows), 10 (the bodies' exact keys; query strings; the blank-ID lookup; the series `PATCH` → `GET` → `DELETE`), 11 (DATES_DIFFER and restore-failed with its one `ERROR` line), 12 (live, every error kind; the fake, every 006 kind; the "another free account" scan), 13 (both), 14 (the reset day at both pinned times; a live 429 stays busy), 15 (a deadlock retried, another failure restored, a restore failure), 16, the 17a restore-to-winner case, 18 (one class, series pairs, manual has no "start link"), 19, 23 |
| `test_move_views.py` (28) | 4 (URLs, non-atomic, permission, every 404, redirects with no Zoom call), 5 (context and initial values, G1, G2 on the widget **and on the rendered real page**, the reused time fields), 6 (`movable_ids`, `can_move_series`, `moved_by`), 9's statuses, 16's flashes (including n = 1, a failed email, manual), 27 (the real `detail.html` series box with fake and manual; the real manual `move_series` page shows the warning) |
| `test_move_race.py` (6) | 8 (the ordered log for one class and for a series) and 17 a, b and c on committed rows. Ran 3 extra times: 6/6 each time |

**Migrations:** `0008_move_classes` (`Occurrence.moved_at`, `Occurrence.moved_by`). No data migration.

**Dependencies and settings:** none. No `LOCAL_APPS` change.

**Self-check** (dev container, after the last code change):

- `ruff check .`: all checks passed. `ruff format .` reformatted 2 files; `ruff format --check .`: 113 files already formatted.
- `pytest --create-db`: passed (the full suite, 1231 tests, 0 failures; confirmed with a `--reuse-db` run straight after, which printed `1231 passed`).
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check`: no issues (0 silenced).
- **Not run by me:** the prod-stack HTTP walkthrough (criterion 25) and `check --deploy` (no settings changed). Those are the verifier's.

backend pytest run finished

### tmd-django-backend, fix cycle 1 (2026-09-26)

Scope: criteria 29, 30 and 31, plus the main session's three mid-cycle items (the `HH:MM` time widget format, criterion 28's Python guard test, and `shown` problems as non-field errors).

**Files changed**

| File | Why |
|---|---|
| `apps/zoom/models.py` | Criterion 29: `MOVE_SERIES_OFF_PATTERN` changed to D.12's message 2. `END_SAME_DAY` unchanged, with its comment now marking it approved. Criterion 30: `MOVE_SHOWN_SALT = "apps.zoom.move-shown"` and `LinkRequest.move_fingerprint(classes)`, the one builder of `shown`. Criterion 31: `LinkRequest.series_move_blocked_note()`. It is built on `series_move_blocked_message()` and returns message 2 only when the booking is approved and weekly, has remaining classes and has none in progress. Otherwise it returns `None`. |
| `apps/zoom/services.py` | Criterion 29: `MOVED_A_MOMENT_AGO` (1a) and `TIMES_CHANGED_A_MOMENT_AGO` (1b) changed to D.12's texts. `MOVING_AT_THE_SAME_MOMENT` (3) is unchanged. Criterion 30: the new `MOVE_PAGE_OUT_OF_DATE` (the main session's approved text), `read_move_shown(token)` (raises `signing.BadSignature` for a missing, edited, wrongly salted or malformed value) and `_as_shown()`. `move_class` / `move_series` / `_move` / `_plan_move` / `_move_check_first` / `_move_once` take `shown=` in place of `expected=`. The stale check sits in `_plan_move`. `MOVE_MESSAGES` gains the out-of-date text for the "another account" scan. |
| `apps/zoom/forms.py` | `LinkRequestForm.Meta.widgets`: `start_time` / `end_time` gain `format="%H:%M"`, because the move forms copy these widgets and without it a pre-filled value renders `08:30:00`. `_MoveFormMixin` is now a `forms.Form` holding the hidden `shown` (`CharField(widget=HiddenInput, required=False)`), `set_shown()` and a `clean()` that reads it back through `services.read_move_shown`. A bad value becomes a **non-field** error and sets `out_of_date`. |
| `apps/zoom/views.py` | Detail: `move_series_blocked`. `_MoveView`: every render puts a fresh `shown` on the form, taken from the same rows as the page's facts (`shown_classes()`: `[occurrence]` or `remaining`). `form_invalid` returns 400 when `form.out_of_date` is set. The service now gets `shown=form.cleaned_data["shown"]`. The POST-start `expected=` reads are removed. |
| `apps/zoom/tests/test_move_stale.py` (new) | Criterion 30's two-user tests on committed rows. |
| `apps/zoom/tests/test_move_views.py` | Existing POSTs now send `shown` (helpers `class_post` / `series_post`). New tests cover criterion 28's guard, the `HH:MM` widgets, a missing or edited `shown` (400), the rendered hidden input, and criterion 31. |
| `apps/zoom/tests/test_move_services.py` | The 17a tests use `shown=` and assert 1a and 1b exactly. New tests: a page for another class, one listed class moved, a class cancelled meanwhile left out, `read_move_shown` rejections, and the pinned texts 1a, 1b, 3 and out-of-date. |
| `apps/zoom/tests/test_move_models.py` | Message 2 rendered exactly, messages 2 and 4 as constants, `series_move_blocked_note()`'s cases, and `move_fingerprint`'s payload and salt. |
| `apps/zoom/tests/test_move_race.py` | The two `expected=` calls became `shown=`. |

**Context contract as implemented: no deviations.**
- `zoom/detail.html`: `move_series_blocked` (str or `None`). When it's set, `can_move_series` is false.
- Both move forms carry `form.shown`, a hidden input. No new top-level variable was added.

**How the stale check works (criterion 30)**
- **Where it runs.** `_plan_move` runs on the plain rows in step 1, before the Zoom lookup, and again on the locked rows in step 2, before any `PATCH`. A stale form is therefore refused before **any** Zoom call. The locked run is the one that decides.
- **What it compares.** Only classes that are still remaining. A class cancelled or started since is left out by the existing rules, not refused. A remaining class that the page didn't list counts as changed, and so does a one-class page signed for a different class. That also covers a valid token taken from another booking's page.
- **What a refusal does.** It returns 409 with no write and no email. The view re-reads the rows, so the re-render shows the current time in the facts and carries a fresh `shown`.
- **No `max_age` on the signature.** An old page is still fine if nothing it shows has changed.
- **`shown=None` skips the check.** This is only for direct `services` callers, such as tests and B's move in the two-user tests. The views always pass `shown`.
- **Note for the reviewer: 1b's `{times}`.** It is the booking's `start_time`–`end_time`, as before. When B's change was a one-class move on the same day, those times haven't changed, so 1b reads "They're now 8:30 am to 11:30 am". The placeholder follows criterion 29 exactly. The `Current times` fact and the class list show the moved class.

**Tests (criterion 30).** All run through the real views with Django's test client.
- **One class**, live provider behind `responses`: A GETs the page, B moves the class, and A POSTs. The result is 409 with 1a naming Thu 8 Oct 9:00–12:00, the typed values kept, **0** new HTTP calls, 0 emails, the class at B's time with `moved_by` B, and a fresh `shown` that decodes to B's times. A POSTs again and gets 302.
- **Series**, run twice (B changes the series, or B moves one listed class): 409 with 1b exactly, no fake-Zoom calls, rows unchanged. The re-POST gets 302.
- **Cancel meanwhile:** 302, the cancelled class untouched, and the others moved by A.
- **Missing, empty, edited, wrong salt or not a list**, on both forms: 400, non-field error only (`"shown" not in form.errors`), typed values kept, no calls, no email.

**Migrations:** none. **Dependencies and settings:** none.

**Self-check** (dev container, after the last change)
- `ruff format .`: 114 files unchanged. `ruff check .`: all checks passed. `ruff format --check .`: 114 files already formatted.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check`: no issues (0 silenced).
- `pytest --create-db`: **1262 passed**. A `--reuse-db` run straight after also gave 1262 passed.
- `test_move_stale.py` and `test_move_race.py` were run 2 more times: 11 passed each time.
- **The verifier's `test_move_views.py::test_the_rendered_move_page_prefills_the_current_date_and_times` passes**, unchanged. It is in the 1262. The frontend's `partials/field.html` fix had landed, and this cycle adds the `%H:%M` widget format. The criterion 28 guard `test_the_request_form_still_shows_typed_values_as_typed` also passes.

Fix cycle 1 … backend pytest run finished — `pytest --create-db`: 1262 passed in 86.32s.

### tmd-django-backend, review round 1 fixes (2026-10-02)

Scope: fix cycle 2's C1a. That's B1 (criterion 33), SF1 and SF2 (criterion 32, amended criteria 11, 13 and 15), the daily limit (criterion 14, D19), the backend's nits, and the task-011 flaky test. No template was touched.

**Files changed**

| File | Why |
|---|---|
| `apps/zoom/views.py` | **B1.** `_MoveView.get_context_data(refresh_shown=…)` signs a fresh `shown` only when the form is unbound (GET), when the service's result is `stale` (the 409 for 1a/1b), or when the form is `out_of_date` (the 400). Every other re-render keeps the posted value. The class docstring says why. |
| `apps/zoom/services.py` | **B1:** `MoveResult.stale`, set only by `_plan_move`'s two stale refusals. **SF1/SF2:** `_put_zoom_back` was rewritten (below). `_move` now picks its message from a `_PutBack(done, landed, failure)`. The forward series path is split into the shared `_tidy_series_in_zoom` (GET, then deletes) and `_store_series_ids` (a one-to-one check on start **and** end, then IDs stored). **Nits:** the `host_account = account` comment; the locked row's ID first. The module docstring is updated. |
| `apps/zoom/providers.py` | `ZoomClass(starts_at, ends_at, occurrence_id)`. `meeting_snapshot` now returns these, so a read-back can check ends (criterion 32). The live provider takes each class's `duration`, else the meeting's. The fake stores `ZoomClass` items. An occurrence update moves that item and keeps its ID. `snapshot_errors` steers read-back failures, like `update_errors`. |
| `apps/zoom/zoom_api.py` | **Criterion 14:** `_is_daily_limit(response)` and `RATE_LIMIT_TYPE_HEADER`; `_api_error` returns `ZoomDailyLimit` for a daily 429 only. The module docstring states 006's amended rule ("never shown or logged"). |
| `apps/zoom/errors.py` | `ZoomDailyLimit`'s docstring: `zoom_api` now raises it. |
| `apps/zoom/tests/test_move_stale.py` | Criterion 33's two two-user tests: one class, live provider, 1a; series, 1b. |
| `apps/zoom/tests/test_move_views.py` | Criterion 33: four kinds of failed submit keep the posted `shown`. Criterion 14: a page test that renders the daily-limit message and none of Zoom's text. |
| `apps/zoom/tests/test_move_services.py` | Criterion 32's tests (below) replace the two old criterion 11 tests. Criterion 14's tests replace `test_the_live_api_never_claims_a_daily_limit`, deliberately, as the criterion says. The fake read-back test now also covers ends, an occurrence update and a delete. |
| `apps/zoom/tests/test_move_race.py` | The criterion 8 series fixture now carries `duration`, as Zoom always sends it, because the read-back compares ends. |
| `apps/zoom/tests/test_cancel_views.py`, `test_cancel_services.py` | **The 011 flake.** The tests no longer compare two `signing.dumps` outputs, which embed the real clock's second. `:480` and `:582` (the lines the review named) compare against the token in the requested URL (`resolve(url).kwargs["token"]`). The same defect also sat at `test_cancel_views.py:331` and `test_cancel_services.py:582`; those now decode the link's token with `link_request_from_start_token`. `start_token` is unchanged. |

**B1 / criterion 33: shown on time.**
- **Shown on the old code.** The new two-user test failed against the code as it was:
  - at step 3, the invalid post came back with a fresh `shown`, not A's;
  - with that check removed, step 4 returned **302 instead of 409**, so A's valid post silently overwrote B's move.

  This was true for both the one-class and the series form.
- **Now:** the invalid post (200) keeps A's original `shown`. The valid post gets 409 with 1a (or 1b), zero Zoom calls, zero emails, and B's time and `moved_by` intact. The 409 page's fresh `shown` then goes through (302).
- **Clash re-renders:** `test_a_failed_submit_keeps_the_posted_shown` covers a database clash, a Zoom clash, a Zoom error and an invalid form. It posts a `shown` that no fresh one can equal (an extra, non-existent pk, which the stale check ignores), so a re-sign is caught even within the same second.

**SF1 / SF2 / criterion 32: how `_put_zoom_back` works.**
- **Locks and retry.** It runs in its own transaction and locks the request, then the account (now `select_for_update`), then the classes. A 1213 or 1205 is retried once; a second one gives `MOVE_NOT_PUT_BACK`.
- **One class.** One occurrence `PATCH` to the locked row's times. The ID is the locked row's `zoom_occurrence_id`. Only when that's blank does it use the ID the failed attempt looked up (`progress.zoom_occurrence_id`).
  - **Deviation from criterion 32's "never from in-memory progress", following the main session's nit instruction.** With a blank stored ID (a booking from before the live connection), the forward attempt looked the ID up, and the rollback then erased it. With no ID, the `PATCH` would address the whole weekly meeting and move every class.
  - With neither ID, nothing is sent (`ZoomMeetingNotFound`), and the message is honest.
  - Test: `test_a_blank_id_is_put_back_by_the_id_the_move_looked_up`.
- **A series runs criterion 32's four steps:**
  1. The restoring series `PATCH` is anchored at the first remaining class's **date**, at the booking's own `start_time`–`end_time` (D4 keeps them true). Anchoring at the first class's own time would flatten every class to it whenever that class was itself moved on its day.
  2. `_tidy_series_in_zoom`, the same helper the forward path uses: a `GET`, then a `DELETE` for each span date whose class was cancelled.
  3. One occurrence `PATCH` for each remaining class whose stored times differ from the pattern on its day, using the ID read in step 2.
  4. A final `GET`, compared with the remaining classes one to one by start and end (`_store_series_ids`, shared with the forward path). The IDs it returns are stored under the same locks.
- **Messages (`_move`):**
  - The put-back is done and the move was uncertain: criterion 13's "put back" message.
  - Neither the move nor the restoring `PATCH` was answered (`not landed`): criterion 13's "couldn't check" message.
  - Anything else that isn't done: `MOVE_NOT_PUT_BACK` plus exactly one `ERROR`. It reads `Moving ZL-…: Zoom meeting … has the new time, but it couldn't be saved here or put back: <move's error class> (putting it back: <put-back's error class or "mismatch">)`. It never includes a link, token or Zoom's text.
  - A put-back that's done leaves the failure's own message ("Nothing was changed" is now true). A plain unexpected exception is still re-raised after a successful put-back (a 500, as before).
- **For the reviewer (copy, not changed):** `MOVE_NOT_PUT_BACK` says "Zoom now has … at the new time". After a restoring `PATCH` that landed but a later step that failed, Zoom actually has the **old** pattern with possibly unfinished deletes or flattened classes. The next step ("Tell whoever looks after the system") is still right. The wording is pinned (criterion 11), so it's flagged for the designer and planner, not changed.

**Criterion 32's tests** (`test_move_services.py`). The booking is ZL-0042 with Wed 14 Oct cancelled and Mon 12 Oct moved alone to 13:00–16:00. The series moves to 9:00–12:00.
- `test_a_series_zoom_got_wrong_is_put_back_fully`:
  - the exact call order `PATCH, GET, PATCH, GET, DELETE(Wed 14 = 803), PATCH(802 → 2026-10-12T13:00:00), GET`;
  - the restoring body (`08:30`, 180, `end_times` 8);
  - `DATES_DIFFER`;
  - database state identical, and stored IDs equal the final read-back (`900`–`906`).
- `test_a_failure_at_any_step_of_putting_it_back_says_so`, with six cases: step 1 `PATCH`, step 2 `GET`, step 2 `DELETE`, step 3 `PATCH`, step 4 `GET`, and step 4 mismatch. Each gives `MOVE_NOT_PUT_BACK`, exactly one `ERROR` with the reference, meeting ID and failure class, no secrets, and the database unchanged.
- **Lock races:**
  - `test_a_lock_race_while_putting_it_back_is_retried_once[1213/1205]`: the four steps run twice, then `DATES_DIFFER`, with the IDs stored.
  - `test_a_second_lock_race_while_putting_it_back_says_so`: `MOVE_NOT_PUT_BACK`, and both tries re-deleted Wed 14.
  - Both use a commit-failure helper, `_fail_commits`. It skips the release Django makes just after a savepoint rollback, so a failed move doesn't use up the injected failure.
- `test_putting_it_back_locks_request_then_account_then_classes`: captured SQL shows `FOR UPDATE` on `zoom_linkrequest` < `zoom_hostaccount` < `zoom_occurrence` < the restoring `PATCH`, all after the forward `GET`.
- `test_every_failed_series_move_is_put_back_the_same_way`, with four forward triggers: dates differ, a failed forward read-back, a failed forward `DELETE`, and an unanswered forward `PATCH` (criterion 13). Each ends in the four steps, Wed 14 deleted again, Mon 12 back at 13:00, and the true message.
- `test_a_save_failure_after_the_series_move_is_put_back_the_same_way` (criterion 15): a deadlock on the commit, then again on the retry. Gives `MOVING_AT_THE_SAME_MOMENT` after the four steps.
- `test_any_other_save_failure_puts_the_series_back_then_raises`: a lost connection on the commit runs the four steps, then re-raises.
- **Criterion 13 for a series, both halves:**
  - `test_no_answer_and_a_failed_series_undo_keeps_criterion_13s_message`;
  - `test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back`.
- `test_one_class_is_put_back_with_the_locked_rows_id`.

**Criterion 14: the daily limit, and Zoom's facts, checked 2026-10-02.**
- **Today's page** (https://developers.zoom.us/docs/api/rate-limits/) gives the two 429 messages verbatim:
  - per second: "You have reached the maximum per-second rate limit for this API. Try again later.";
  - daily: "You have reached the maximum daily rate limit for this API. Refer to the response header for details on when you can make another request."

  The page **no longer names the header**.
- **The page's earlier version** (marketplace.zoom.us/docs/api-reference/rate-limits/, read through the Wayback Machine's 2021–2022 copies) documented `X-RateLimit-Type: QPS` for the per-second limit and `X-RateLimit-Type: Daily-limit` (with `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `Retry-After`) for the daily one.
- **The rule:** for a 429 only, it's `ZoomDailyLimit` if `X-RateLimit-Type` contains `daily` or the JSON `message` contains `daily`, both case-insensitive. Either signal is enough, and neither is required. A non-JSON body, a non-object body, or a missing or non-text `message` reads as "not daily" and never raises.
- **Zoom's text** is only compared, never stored, shown or logged. The log keeps the class name `ZoomDailyLimit`.
- **Tests:**
  - `test_a_429_is_the_daily_limit_only_when_zoom_says_daily`, nine cases: the documented daily text, any letter case, the header alone (both spellings), per-second text with `QPS`, a non-JSON body, an empty body, a JSON list, and a non-text message;
  - `test_daily_in_any_other_refusal_isnt_the_daily_limit`, a 400 with a `daily` message and the daily header, which gives `Zoom error 300`;
  - `test_zooms_daily_text_is_never_logged_or_kept`, with DEBUG logs captured;
  - `test_zooms_daily_text_never_reaches_the_page`, on the real `move_form.html`.
- **For the docs writer:** 006's "Zoom's text is ignored" wording in the README or CLAUDE.md, if any, becomes "never shown or logged" (D19).

**Context contract:** unchanged. `shown`'s refresh points follow criterion 33.

**Migrations:** none. **Dependencies and settings:** none.

**Self-check** (dev container, after the last change)
- `ruff check .`: all checks passed. `ruff format --check .`: 114 files already formatted.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check`: no issues (0 silenced).
- `test_move_stale.py`, `test_move_race.py`, `test_move_services.py` and `test_cancel_views.py` were run 2 more times with `--reuse-db`: 158 passed each time.

Review round 1 fixes … backend pytest run finished — `pytest --create-db`: 1298 passed in 57.00s.

### tmd-django-backend, fix cycle 3 (2026-10-02)

D21 (the designer's D.13): amended criteria 11, 12, 13, 15 and 32. Backend only, with no template change. Both texts go in the existing `move_error` notice. It started after the fix-cycle-2 re-verification (PASS), with no other agent running pytest.

**Files changed**
- `apps/zoom/services.py`:
  - **Messages.** `MOVE_NOT_PUT_BACK` now has criterion 32's pinned new text. `MOVE_PARTLY_PUT_BACK` is new, with its pinned text, and is in `MOVE_MESSAGES` (criterion 12's scan).
  - **Choosing a message.** `_move`'s failed-put-back branch picks between the two with `back.landed`.
  - **The `ERROR` line** is now criterion 32's neutral form.
  - **`_put_zoom_back`** treats the one-class edge as done. The docstrings on `move_class`/`_move`, `_PutBack` and `_put_zoom_back` say why.
- `apps/zoom/tests/test_move_services.py`: expectations updated per criterion 32, and the new tests below. `_fail_commits` now also takes a list, one error per failed commit, so a test can fail the move's commits and the put-back's commit differently.

**Message per failure, as built** (criterion 32's table):

| Failure | `back.landed` | Result |
|---|---|---|
| one class: the undo `PATCH` refused or unanswered, or no occurrence ID | no | `MOVE_NOT_PUT_BACK` + `ERROR` |
| one class: the undo `PATCH` answered, then the put-back's transaction failed | yes | **done**: the failure's normal message (or criterion 13's `MOVE_MAYBE_RESTORED` when the move went unanswered), a `WARNING`, and no `ERROR` |
| series, step 1 refused or unanswered, or both tries lost a lock race before it was sent | no | `MOVE_NOT_PUT_BACK` + `ERROR` |
| series, any later step, a final-check mismatch, or a second lock race after step 1 landed | yes | `MOVE_PARTLY_PUT_BACK` + `ERROR` |
| the move unanswered, and step 1 unanswered or refused (criterion 13) | no | `MOVE_MAYBE_NOT_RESTORED`, unchanged, with no `ERROR` (as before) |

For one class, `landed` and not `done` can no longer reach the message branch, because the edge makes it done. So one class only ever shows `MOVE_NOT_PUT_BACK`, as the table requires.

**The `ERROR` line** (one record per failed put-back), exactly:
`Moving {reference}: Zoom meeting {meeting_id} doesn't match this database: {type(cause).__name__} (putting it back: {back.failure}, restoring update answered: yes|no)`. `back.failure` is an error class name or `mismatch`. It contains no time claim, no link, no token and none of Zoom's text.

**One-class edge: how it's built, and one judgement for the reviewer.**
- In `_put_zoom_back`, any `DatabaseError` (including `OperationalError`) raised after a one-class undo `PATCH` was answered (`occurrence_id is not None and back.landed`) sets `done`. It logs `WARNING`, `Put {reference} back in Zoom, but its own transaction then failed: {error class}`, and returns.
- **No retry there, even for 1213/1205.** Criterion 32 says the put-back retries a lock race once. For one class, though, the `PATCH` is the transaction's last action and the transaction writes nothing. A retry could only send the same time again, so I count it as done straight away, as the edge bullet says ("counts as done"). A series still retries as before, and `test_a_lock_race_while_putting_it_back_is_retried_once` is unchanged and passes.
- A non-`OperationalError` `DatabaseError` in a series put-back still sets `failure` to its class name without a retry, the same as before (the handler was restructured, not changed in effect).

**Tests**
- **Amended:**
  - `test_a_failure_at_any_step_of_putting_it_back_says_so` (6 cases): step 1 gives `MOVE_NOT_PUT_BACK` and `answered: no`. Step 2 `GET`, step 2 `DELETE`, step 3 `PATCH`, step 4 `GET` and the mismatch each give `MOVE_PARTLY_PUT_BACK` and `answered: yes`. The whole `ERROR` line is asserted exactly.
  - `test_a_second_lock_race_while_putting_it_back_says_so`: gives `MOVE_PARTLY_PUT_BACK`, with the exact line (`OperationalError`, `yes`).
  - `test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back` (name kept): gives `MOVE_PARTLY_PUT_BACK`, with the exact line (`ZoomUnavailable`, `ZoomUnavailable`, `yes`).
  - `test_a_failure_after_zoom_changed_it_and_a_failed_restore` (one class): gives the new `MOVE_NOT_PUT_BACK`, with the exact line (`answered: no`).
- **New:**
  - `test_a_second_lock_race_before_any_restoring_update_says_not_put_back`: both tries lose a 1213 before step 1, and only the forward `PATCH` and `GET` are sent. Gives `MOVE_NOT_PUT_BACK` and `answered: no`.
  - `test_one_class_undone_then_its_own_transaction_failing_counts_as_done[lost connection|deadlock]`: the move's two commits lose a 1213 race, the undo `PATCH` is answered, then its commit fails. Expect `MOVING_AT_THE_SAME_MOMENT`, exactly 3 `PATCH`es (no second undo), no `ERROR`, the `WARNING` with reference and error class, and the database unchanged.
  - `test_the_error_line_is_neutral_and_holds_nothing_from_zoom`: a one-class undo refused with Zoom's error text, whose body holds `RAW-ZOOM-TEXT` and a secret. The exact neutral line is logged, with no `new time`, `has the` or `http` in it, and no Zoom text or secrets anywhere in the DEBUG log.
  - `test_the_two_put_back_messages_are_pinned`: both texts rendered with Zoom 02 / `81234567890` equal D.13's two rendered examples, character for character, and both are in `MOVE_MESSAGES`.
- **Shown failing on the old code first** (tests updated, `services.py` not yet changed, `--reuse-db`): 14 failed.
  - **Old wording:** the 6 step cases, the second-lock-race test, the halfway test, the one-class failed-restore test, the new lock-race-before test, the neutral-line test and the pinned-texts test all failed on the old `Zoom now has … at the new time` message or the old `has the new time` log line.
  - **The edge, `[lost connection]`:** failed because the old code returned `PROVIDER_ERROR` / `MOVE_NOT_PUT_BACK`.
  - **The edge, `[deadlock]`:** failed because the old code retried and sent a 4th `PATCH` (`too many values to unpack`).
  - **After the fix:** `test_move_services.py` gave 101 passed.

**Context contract:** unchanged. **Migrations:** none. **Dependencies and settings:** none.

**Self-check** (dev container, `polymath-tmd:dev`, after the last change)
- `ruff format .`: 1 file reformatted (the test file). `ruff check .`: all checks passed. `ruff format --check .`: 114 files already formatted.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check`: System check identified no issues (0 silenced).

Fix cycle 3 … backend pytest run finished — `pytest --create-db`: 1303 passed in 62.21s.

### tmd-django-backend, fix cycle 4 (2026-10-02)

Review round 2's should-fix 1 (criterion 34, D22, the designer's D.14) and its two nits (criterion 32's catch-all; the clock-stamped token test). Backend only: every text goes in an existing notice or flash, so no template change. I was the only agent running `pytest --create-db`.

**Files changed**
- `apps/zoom/errors.py`: `ZoomDailyLimit`'s phrase is now `Zoom's daily limit for this account is used up`. Its docstring now says every caller checks for it before `lasting` and names the reset day (it was "the move's message names the day"). It stays `lasting=True`. The module docstring's `lasting` bullet notes the exception.
- `apps/zoom/services.py`:
  - **The reset sentence.** `zoom_daily_reset()` moved up beside the approve messages, unchanged. `daily_reset_sentence(now=None)` is new: `DAILY_RESET` = `Try again after {time} on {date}.`, built from `class_time` / `class_date` of `zoom_daily_reset(now)`. This is the only place the sentence is built.
  - **The daily case comes before `lasting` in all four callers:**
    - `next_step`, which approve's create and look-up both use: `NEXT_STEP_DAILY` = `Choose another free account, or wait for this one. {reset}`;
    - `cancel_failed_message`: the reset sentence alone;
    - `move_lookup_failed_message`: the reset sentence alone;
    - `check_connection`: a new `except ZoomDailyLimit` before `except ProviderError`, giving the new `CHECK_DAILY_LIMIT` at level `error`.
  - **The move's own message.** `MOVE_DAILY_LIMIT` now ends `{reset}` and `move_failed_message` fills it from `daily_reset_sentence(now)`. Its rendered text is unchanged.
  - **The approve page's account list** (`availability`): no code change. It prints `reason_sentence`, so it follows the new phrase.
  - **`_put_zoom_back` catch-all** (criterion 32): it has a final `except Exception`. It sets `failure` to the error's class name only, never its text. `_move` then writes the same neutral `ERROR` line and picks `MOVE_NOT_PUT_BACK` / `MOVE_PARTLY_PUT_BACK` from `back.landed`, as before. The move's own exception stays `cause`: it's the one the line names and, when the put-back is done, the one re-raised. The one-class edge's code moved into a small helper, `_one_class_put_back_anyway`, which both the `DatabaseError` branch and the catch-all call. The docstring says `_put_zoom_back` never raises.
- `apps/zoom/tests/test_daily_limit.py` (new): criterion 34's seven named tests (below).
- `apps/zoom/tests/test_move_services.py`: three catch-all tests (four cases).
- `apps/zoom/tests/test_services.py`: the nit. `test_approval_email_carries_link_start_link_classes_and_recording` used to rebuild the start URL with a second `start_token()`, which carries the real clock's second. It now pulls the one token out of the email body with a regex, decodes it with `link_request_from_start_token` (asserting the booking), and builds the expected `START_BLOCK` from that token. This is the same approach as `test_cancel_services.py`'s `test_a_start_token_names_its_booking`.

**Criterion 34's texts, as built:** all five rendered texts equal the table exactly at the frozen now, and the tests assert them character for character.

**Two deviations in form only, not in text.** Neither changes any rendered message.
1. Criterion 34 writes `CHECK_DAILY_LIMIT` as `Couldn't check {label} with Zoom: {phrase}. Try again after {time} on {date}.`. As built it's `Couldn't check {label} with Zoom: {phrase}. {reset}`, filled from `daily_reset_sentence()`.
2. `MOVE_DAILY_LIMIT` and `NEXT_STEP_DAILY` likewise end with `{reset}`.

Why: the same criterion says the helper is "the only place the sentence is built". A literal `Try again after {time} on {date}.` in each template would be a second copy of P5.

**One judgement for the reviewer (the catch-all and the one-class edge).** Criterion 32 says the catch-all returns "the criterion 32 table's message for the current `back.landed`". That table's one-class row with `landed` is **done**, so the catch-all applies the one-class edge too. Once a one-class undo `PATCH` is answered, an unexpected error after it gives the same result as the `DatabaseError` edge: a `WARNING` naming the class, no `ERROR`, and the move's own outcome. The transaction writes nothing and the `PATCH` was its last action, so Zoom matches the database whatever failed. A series is unaffected: it gets `MOVE_PARTLY_PUT_BACK` once landed.

**Tests**
- `test_daily_limit.py`, criterion 34's names. Zoom answers each with a mocked `429` carrying `X-RateLimit-Type: Daily-limit` and Zoom's documented daily wording (`ZOOM_DAILY_TEXT`, imported from `test_move_services.py`). Every message is also scanned for criterion 34's banned words, and `another free account` is allowed only in 1a and 1b.
  - `test_the_daily_reset_sentence_is_p5s`:
    - the helper at the frozen now, and at Tue 29 Sep 02:00 Colombo, gives `Tue 29 Sep 2026`; at Tue 29 Sep 06:00 it gives `Wed 30 Sep 2026`;
    - `MOVE_DAILY_LIMIT` built with the helper, and `move_failed_message`, both equal criterion 14's pinned text;
    - the new phrase and its `reason_sentence`, and `lasting is True`.
  - `test_a_daily_limit_on_approves_create_says_when_to_try_again` (1a, through the service; no `DELETE`, nothing booked).
  - `test_a_daily_limit_on_approves_look_up_says_when_to_try_again` (1b, through the approve view's `approve_error`; no create).
  - `test_a_daily_limit_on_cancel_says_when_to_try_again` (2; nothing cancelled).
  - `test_a_daily_limit_on_the_moves_look_up_says_when_to_try_again` (3; no `PATCH`, the class unchanged).
  - `test_a_daily_limit_on_check_connection_says_when_to_try_again` (4; the flash is at level `error`, with no `Waiting won't fix this` and no `Zoom error number`).
  - `test_a_daily_limit_on_the_account_list_names_the_reason` (5):
    - the detail page's entry is `unavailable`, with `zoom_problem` equal to the sentence;
    - because the page templates are stubbed in these tests, the row is rendered with the real `zoom/partials/avail_item.html`, and shows `Couldn't check with Zoom` followed by the reason sentence.
- `test_move_services.py`, criterion 32's catch-all. The `RuntimeError` text holds `RAW-ZOOM-TEXT … 7731`, and every test also asserts that it's in no log record.
  - `test_an_unexpected_error_while_putting_a_series_back_still_says_so[before it lands | after it lands]`:
    - *before* raises from `_put_series_back`: `MOVE_NOT_PUT_BACK`, Zoom calls `PATCH, GET`, and the line `_DatesDiffer … RuntimeError … answered: no`;
    - *after* lets the restoring `PATCH` reach Zoom, then raises: `MOVE_PARTLY_PUT_BACK`, calls `PATCH, GET, PATCH`, and `… answered: yes`;
    - in both, exactly one `ERROR`, and the database is unchanged.
  - `test_an_unexpected_error_before_a_one_class_undo_lands_keeps_the_moves_error`: the move's commit is lost (`OperationalError` 2013), then the put-back raises before its `PATCH`. Gives `MOVE_NOT_PUT_BACK` and the line `OperationalError … RuntimeError … no`. Before this fix the `RuntimeError` escaped instead.
  - `test_an_unexpected_error_after_a_one_class_undo_lands_counts_as_done`: the undo `PATCH` is answered, then a `RuntimeError` follows. Gives no `ERROR`, the `WARNING` `Put ZL-… back in Zoom, but its own transaction then failed: RuntimeError`, and the move's own `OperationalError` is raised, not the `RuntimeError`.
- **Shown failing on the old code first.** The tests were written, `errors.py` and `services.py` were not yet changed, and the run used `--reuse-db`. **11 failed:**
  - the helper test: `services` had no `daily_reset_sentence`;
  - 1a, 1b, 2, 3 and 4: each got the old phrase `… for changing meetings …` and the old lasting step, either `… press Check connection for Zoom 02` or `Waiting won't fix this … Zoom error number`;
  - 5: got the old phrase;
  - all four catch-all cases: the `RuntimeError` escaped `move_series` / `move_class`.

  The token test passed on the old code too, as expected: it only removes a clock dependency.
- **After the fix:** these files gave all passed: `test_daily_limit.py`, `test_services.py`, `test_move_services.py`, `test_zoom_accounts_connection.py`, `test_cancel_services.py` and `test_zoom_approve.py`. That includes 006's and 011's existing per-kind message tables, so every other error kind keeps its text.

**Context contract:** unchanged. **Migrations:** none. **Dependencies and settings:** none.

**Self-check** (dev container, `polymath-tmd:dev`, after the last change)
- `ruff format .`: 2 files reformatted (the two test files). `ruff check .`: all checks passed. `ruff format --check .`: 115 files already formatted.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check`: System check identified no issues (0 silenced).

Fix cycle 4 … backend pytest run finished — `pytest --create-db`: 1314 passed in 67.80s.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: FAIL** (criterion 5; criterion 20 not yet done — see below). Everything else checked (1–19, 21–25, 27) holds up under automated tests, three extra race-module runs, and a real HTTP walkthrough on the prod image with `ZOOM_PROVIDER=manual`.

### Coverage table

| # | Criterion | Test(s) | Result |
|---|---|---|---|
| 1 | `moved_at`/`moved_by` fields | `test_the_moved_fields_are_optional_and_protect_the_user`, `test_a_new_class_has_not_been_moved` | ✅ |
| 2 | Model move rules + pinned copy | `test_the_rules_for_one_class_and_their_pinned_copy`, `test_the_series_rules_and_their_pinned_copy`, `test_the_pinned_one_class_messages`, `test_a_class_that_has_started_cant_be_moved`, `test_a_cancelled_class_cant_be_moved`, `test_a_class_in_progress_blocks_the_series`, `test_no_remaining_classes_blocks_the_series` | ✅ |
| 3 | What a move writes | `test_moving_one_class_writes_it_and_asks_zoom_once`, `test_changing_the_series_moves_every_remaining_class_and_the_request`, `test_a_series_change_never_touches_held_or_cancelled_classes`; confirmed live on prod: `schedule_summary` updated after a series move, one-class move leaves it alone | ✅ |
| 4 | URLs, access, 404s, blocked redirects | `test_the_urls_and_their_views_run_outside_the_request_transaction`, `test_moving_needs_the_review_permission`, `test_the_pages_are_404_for_what_cant_be_moved`, `test_a_class_that_has_started_goes_back_with_the_reason`, `test_a_series_in_progress_or_with_nothing_left_goes_back` | ✅ |
| 5 | The forms (labels, help, G1, G2, pre-fill) | `test_the_one_class_page_context`, `test_the_series_page_context`, `test_the_timetable_link_is_the_month_of_the_class`, `test_the_date_widget_carries_its_limits_and_the_times_their_step`, `test_the_rendered_move_page_carries_the_date_limits_and_time_steps` (min/max/step on the real page) — **plus the new `test_the_rendered_move_page_prefills_the_current_date_and_times`, which FAILS** | ❌ see Failures |
| 6 | Detail page: actions, Moved tag/note | `test_the_detail_offers_moves_on_an_approved_weekly_booking`, `test_a_one_off_has_its_class_movable_but_no_series`, `test_nothing_is_movable_while_waiting_or_cancelled_or_in_progress`; live screenshot `detail_1440.png` shows both actions per row, `Moved` tag, `Moved by … on ….` | ✅ |
| 7 | Clash rules (DB + Zoom) | `test_moving_onto_the_bookings_own_other_class_clashes`, `test_touching_the_bookings_own_time_isnt_a_clash`, `test_a_meeting_made_in_zoom_at_the_new_time_clashes`, `test_the_bookings_own_meeting_in_zoom_at_the_old_time_doesnt_clash`, `test_clashing_finds_overlaps_on_the_account_but_not_touching_or_excluded` | ✅ |
| 8 | Order of work | `test_a_move_asks_zoom_then_locks_writes_patches_then_commits`, `test_a_series_move_adds_the_read_back_and_the_deletes_before_the_commit` (both re-run 3 extra times, 0 flakes) | ✅ |
| 9 | Clash messages (5 rows) | `test_an_account_that_isnt_connected_refuses_the_move`, `test_when_zoom_cant_be_asked_nothing_is_changed`, `test_the_slot_backstop_says_booked_a_moment_ago`, `test_a_meeting_made_in_zoom_at_the_new_time_clashes`, `test_moving_onto_the_bookings_own_other_class_clashes`; live 409 reproduced over HTTP (see below) | ✅ |
| 10 | Zoom calls (bodies, order) | `test_one_class_of_a_weekly_booking_is_one_patch_of_its_occurrence`, `test_a_blank_occurrence_id_is_looked_up_first_and_kept`, `test_the_one_off_class_is_a_patch_of_the_meeting`, `test_a_series_is_one_patch_then_the_read_back_then_the_cancelled_dates_deletes`, `test_no_update_body_ever_carries_settings_topic_or_agenda` | ✅ (deviation reviewed, see below) |
| 11 | Series read-back / restore | `test_a_series_zoom_got_wrong_is_put_back_and_nothing_is_changed`, `test_when_the_restore_fails_too_it_says_so_and_logs_one_error` | ✅ |
| 12 | Zoom refused for certain | `test_zoom_refused_for_certain_rolls_back_with_one_message_per_kind`, `test_the_message_for_each_error_kind`, `test_no_move_message_ever_offers_another_account` | ✅ |
| 13 | `maybe_done` | `test_no_answer_puts_the_class_back_and_says_so`, `test_no_answer_and_a_failed_restore_says_trying_again_finishes_it`, `test_the_restore_sets_the_time_the_database_holds_now` | ✅ |
| 14 | Daily limit | `test_the_daily_reset_is_the_next_utc_midnight_in_colombo_time`, `test_the_live_api_never_claims_a_daily_limit` | ✅ |
| 15 | Saving fails after Zoom changed it | `test_a_deadlock_after_zoom_changed_it_is_retried_and_finishes`, `test_any_other_failure_after_zoom_changed_it_puts_zoom_back`, `test_a_failure_after_zoom_changed_it_and_a_failed_restore`, `test_a_lock_race_before_zoom_changes_nothing` | ✅ |
| 16 | Success flashes | `test_the_series_success_messages`, `test_the_one_class_success_message`, `test_the_manual_provider_changes_nothing_in_zoom_and_still_moves`, `test_one_remaining_class_reads_as_one`, `test_a_failed_email_is_a_warning`, `test_the_manual_provider_says_change_it_in_zoom_too`; live flashes reproduced over HTTP | ✅ |
| 17 a/b/c | Races | `test_two_moves_of_one_class_commit_one_time`, `test_a_move_and_an_approval_into_the_same_time_never_overlap`, `test_a_move_and_a_cancel_of_one_class_at_once` (all re-run 3 extra times, 0 flakes) | ✅ |
| 18 | The email | `test_the_moved_email_for_one_class`, `test_the_moved_email_for_a_series_has_a_pair_per_class`, `test_the_moved_email_with_the_manual_provider_mentions_no_start_link`; live console log shows two-line `Was:`/`Now:` pairs and `Your Zoom link stays the same.` with no "start link" under manual | ✅ |
| 19 | Start link follows | `test_the_start_link_follows_the_moved_class` | ✅ |
| 20 | README scope addition | — | ❌ not yet done, see below |
| 21 | Thin views | code read: `views.py`'s `_MoveView`/`MoveClassView`/`MoveSeriesView` parse, call `services`, choose a template/redirect; no business logic in the view | ✅ |
| 22 | Templates, no-JS, busy button, layout/a11y | live screenshots at 1440/400 (see below); `test_the_rendered_move_page_carries_the_date_limits_and_time_steps` | ✅ |
| 23 | No test reaches the network | `test_no_update_body_ever_carries_settings_topic_or_agenda`, project-wide `responses` mock in `test_move_services.py`/`test_move_race.py` | ✅ |
| 24 | Automated checks | see Checklist below | ✅ |
| 25 | Prod walkthrough | live HTTP run on 8010, `ZOOM_PROVIDER=manual` (see below) | ✅ |
| 26 | Owner's live check | — | pending, left for the owner as instructed |
| 27 | Series box lead / no warning | `test_the_series_box_lead_follows_checks_zoom_and_has_no_warning[fake/manual]`, `test_the_manual_series_form_warns_to_check_zoom_first`; live screenshot confirms manual lead text and no `notice--warn` in the box | ✅ |

### Backend deviations, judged against the criteria

- **Series order `PATCH → GET → DELETE`** (criterion 10 lists `PATCH, DELETE, GET`): **complies with the criteria as a group.** Criterion 8 only requires "the deletes… and one `GET`… all before the commit", not a fixed order between them, and criterion 11's read-back check needs the *new* occurrence IDs to know which pattern dates to delete — Zoom's docs don't say an ID survives the series `PATCH`, so guessing which IDs to delete before the `GET` would risk deleting the wrong occurrence. `test_a_series_is_one_patch_then_the_read_back_then_the_cancelled_dates_deletes` and the race test both pin `PATCH → GET → DELETE`, one `GET`, one `PATCH`, all before commit. Sound engineering reason, correctly tested, no observed harm.
- **Restoring Zoom to the DB's current times, not a remembered "old" value:** **complies**, and is explicitly required by criterion 17a ("restores the winner's time, not the old one"). `test_the_restore_sets_the_time_the_database_holds_now` proves it.
- **The series-restore R1 residual risk** (cancelled classes may reappear in Zoom after a failed-series-move restore): **accepted, correctly flagged.** Criterion 11 only requires the restoring `PATCH` to use "the old start, duration and recurrence" — it does not require re-deleting cancelled dates after a restore. The risk register (R1) already names this exact residual and assigns it to 013's reconcile. Confirmed in code (`services.py`'s restore path is one `PATCH`, no follow-up deletes) and flagged again in the backend's own notes for the reviewer. No criterion is violated; this is a legitimate design trade-off, correctly disclosed.
- **Four new unpinned messages** (two "already moved" races, one lock-wait-timeout message, one "moved to another day blocks the series" message): **within scope.** No criterion pins exact text for these states; criterion 17a only pins the *behaviour* ("restores the winner's time"), and the "moved to another day" case isn't in the brief's copy tables at all — it's a new rule the backend added (with reasoning) to stop a series move that could never pass criterion 11's read-back check. All four follow house style (what happened, "Nothing was changed", one next step) and are tested (`test_a_class_moved_since_the_page_was_shown_isnt_moved_again`, `test_a_series_changed_since_the_page_was_shown_isnt_changed_again`, `test_a_lock_race_before_zoom_changes_nothing`, `test_a_class_moved_to_another_day_blocks_the_series`). The brief's own notes flag them "designer, please check" / "worth a look in review" — correctly left for code review, not a verifier blocker.
- **`cancellable_classes` → `remaining_classes`:** **complies**, explicitly required by the MVT plan ("the backend renames it… and records the rename"). `test_remaining_classes_is_the_one_definition` confirms the old name is gone and callers were updated; the full suite (`test_cancel_models.py` etc.) still passes, confirming no caller was missed.
- **Every 429 treated as "busy" (criterion 14's fallback):** **complies.** Criterion 14 explicitly allows this ("If the two can't be told apart, every `429` stays `ZoomBusy`"), and the backend's notes show the research finding that Zoom's docs give no code or header to tell a daily 429 from a per-second one. `test_the_live_api_never_claims_a_daily_limit` proves a `429` with the daily-limit wording still returns "Zoom is busy right now", not `ZoomDailyLimit`.

### Checklist

- `ruff check .` — all checks passed. ✅
- `ruff format --check .` — 113 files already formatted. ✅
- `pytest --create-db` — run twice: **1231 passed** both times (matches the backend's report). ✅
- `test_move_models.py` + `test_move_services.py` + `test_move_views.py` + `test_move_race.py` — run 3 extra times with `--reuse-db`: **126 passed** every time, 0 failures, 0 flakes. ✅
- `python manage.py makemigrations --check --dry-run` — No changes detected. ✅
- `python manage.py check` — 0 issues. ✅
- `python manage.py check --database default` — 0 issues. ✅
- Migration `0008_move_classes` — confirmed reversible: `migrate zoom 0007` unapplies it, `migrate zoom 0008` re-applies cleanly. ✅
- `check --deploy` — **skipped, correctly:** the backend's Implementation notes confirm "Dependencies and settings: none", so no settings changed for this brief; 011's already-passing `check --deploy` (W021 only) is unaffected. n/a.
- `test_every_static_reference_in_templates_exists`, `test_css_colour_literals_live_only_in_the_root_palette_block` — still pass after the CSS and template changes. ✅

### Prod HTTP walkthrough (criterion 25)

`docker compose up -d --build` with `ZOOM_PROVIDER=manual`, waited for `web` healthy, confirmed `settings.ZOOM_PROVIDER == "manual"` inside the container. Created a throwaway superuser (`verifier012`) and three throwaway bookings/accounts via the ORM (approved through `services.approve()` with `ManualProvider`, exactly as the real approve flow leaves things), then drove the app over `http://localhost:8010` with `curl` (cookie jar) plus headless Edge for screenshots, following each CSRF token from its page.

- **Moved one class** (ZL-0626's Wed 7 Oct class, weekly): GET the form (200), POST a new date/time (200 → 302 → detail), flash `Moved the class to Wed 7 Oct 2026, 3:00 pm to 4:00 pm. We emailed verify-requester@example.com. This system can't reach Zoom: change it in Zoom too.`; detail page then shows `Moved` + `Moved by verifier012 on Sat 26 Sep 2026, 6:04 pm.` on that row.
- **Changed a series' time** (all 7 remaining classes of ZL-0626, 8:00–9:00 → 7:00–8:00): 200 → 302 → detail; `Request → When` updated to `Every Monday and Wednesday, 7:00 am to 8:00 am, …` (schedule_summary follows the move, D4); every one of the 7 rows shows `Moved` and its own note; the timetable page for October shows the 5 October classes at 7:00 am–8:00 am.
- **Clashing move, another test booking:** moved the one-off booking's class onto the weekly booking's own new time/account → **409**, notice `Verify Zoom V1 already has ZL-0626 Verify Weekly Class at that time. Choose another time.` (criterion 9's DB-clash row, verbatim pattern), `role="alert" tabindex="-1" data-error-summary`, no `notice__title` on that notice (the manual notice's own title is separate), typed values (`date="2026-10-12"`, `start_time="07:00"`, `end_time="08:00"`) kept in the re-rendered inputs, and the `Current time` fact still showed the *stored* time (Wed 30 Sep, 10:00–11:00 am), not the typed one — matches D.2.5 exactly.
- **The `Moved` tag and note, and the timetable/start-link following the move** — both confirmed live (screenshots and the timetable page above).
- **The "was/now" email in the console log:** confirmed two lines per pair (`Was: …` / `Now: …`), a blank line between pairs, `Your Zoom link stays the same.` (manual, `can_start` false) with `students line` reading "new time" (singular, one-class email) and "new times" (plural, series email) — pluralisation correct — and no start link anywhere in either email.
- **The manual move form never says "start link":** `grep -ic "start link"` = 0 across the one-class form, the series form, the one-off's form and the 409 re-render.
- **Static files:** hashed paths (`style.910cfb033e2d.css`, `app.2456fc2beeea.js`) all return 200.

Screenshots (1440 and 400, in the scratchpad `shots/`): `detail_1440.png`, `detail_400.png` (Classes list, both actions per row, `Moved` tag/note, the series box, `Cancel this booking`), `move_class_1440.png`, `move_class_400.png` (the one-class form, manual notice, facts, fields, buttons), `move_series_1440.png`, `move_series_400.png`, `move_clash_1440.png`, `move_clash_400.png` (the 409 notice, kept values). Layout matched the D.1.4/D.2.7 wireframes closely at both widths, no horizontal overflow observed.

All throwaway data (3 `LinkRequest`s, 2 `HostAccount`s, 1 superuser) was deleted after the walkthrough (dev and prod share the same database volume, so this was cleaned up once, from the dev stack, and confirmed at 0 remaining rows).

### Failures

**Criterion 5 — the move forms don't actually pre-fill on GET in a real browser.** `docs/tasks/012-move-a-class.md` criterion 5 and D.2.4 both require the fields to be "filled in with the class's current values" on GET. The context/form-level tests pass (`form.initial` is correct, and `str(form["date"])` renders correctly when the widget is exercised directly), but the **real rendered page** does not: `partials/field.html` (a shared partial, not part of this brief's changed-file list) builds the `<input>` tag by hand and writes `value="{{ field.value }}"`. For an unbound date/time field, `field.value` is the raw `datetime.date`/`datetime.time` object, and Django's template engine auto-localises objects on `{{ }}` output using the *display* formats (`DATE_FORMAT` = `"N j, Y"`, `TIME_FORMAT` = `"P"`), not the widget's own `format_value()` (which is what would honour `MoveClassForm.date`'s explicit `format="%Y-%m-%d"`, or would use the input formats for the shared `TimeInput`). The result, reproduced identically in both the dev test settings and the prod container:

  ```
  <input ... name="date" value="Oct. 7, 2026" min="2026-09-28" max="2027-09-28" ...>
  <input ... name="start_time" value="7 a.m." step="300" ...>
  ```

  `"Oct. 7, 2026"` and `"7 a.m."` are not valid HTML5 `date`/`time` values, so every browser silently discards them and shows the field empty (confirmed with a real headless-Edge screenshot: `move_class_1440.png` shows blank date and time boxes, not `07/10/2026`/`08:30 AM` as the D.2.7 wireframe shows). The same happens on `move_series.html`'s `start_time`/`end_time`. IT has to read the separate "Current time"/"Current times" fact and retype the whole date and time from scratch, which the criterion and wireframe both say shouldn't be necessary.

  Reproduction: `docker compose -f compose.yaml -f compose.dev.yaml exec web python manage.py shell -c "from django.template import Template, Context; from datetime import date; print(Template('{{ d }}').render(Context({'d': date(2026,10,7)})))"` → `Oct. 7, 2026`.

  A regression test proving this was added at `apps/zoom/tests/test_move_views.py::test_the_rendered_move_page_prefills_the_current_date_and_times` (fails today; confirmed with `pytest --reuse-db apps/zoom/tests/test_move_views.py -k prefills_the_current`, 1 failed). Every other test in the file still passes (28 passed alongside it), so this is isolated to this one behaviour.

  *(Planner, 2026-09-26: recorded as criterion 28 and D15. The fix cycle is in the agent plan.)*

  **Likely owner: `tmd-frontend`.** The fix belongs in `partials/field.html`'s date/time rendering (use the widget's own `format_value()`/rendering instead of hand-building `value="{{ field.value }}"`, or special-case date/time fields), since the widget-level `format=` the backend already set on `MoveClassForm.date` is silently ignored by this partial. A narrower fix inside `apps/zoom/forms.py` (e.g. passing pre-formatted ISO strings as `initial`) would work around it for this brief only and leave the same latent bug for any future date/time field pre-filled through `partials/field.html`.

**Criterion 20 — the README doesn't yet list `meeting:update:meeting:admin`.** Checked `README.md`'s Zoom scopes section (line ~372): it still lists only the four scopes from briefs 005/006/011; no mention of the new scope, D8's setup steps, or the daily-limit note. This matches the agent plan (docs-writer is step 6, after verification) and is not a code defect, but the acceptance criterion itself is not yet met, so it is reported as failing today rather than silently assumed. Owner: `tmd-docs-writer`, in the normal step-6 pass.

  *(Planner note, per the main session's ruling, 2026-09-26: criterion 20 is the docs writer's job at close (step 6). It isn't a build FAIL, and isn't part of fix cycle 1. The verifier re-checks it after step 6. Criterion 20 now says so.)*

### Tests added

- `apps/zoom/tests/test_move_views.py::test_the_rendered_move_page_prefills_the_current_date_and_times` — proves the criterion-5 defect above; will pass once the fix lands.

## Re-verification (fix cycle 1)

**Verdict: PASS** (criteria 1–19, 21–25, 27–31). Criterion 20 is the docs writer's job at step 6, still correctly not done; criterion 26 is the owner's live check, still pending. Both are reported as such, not as failures of this cycle.

Before starting, the working tree was put back in order per the coordinator's note: the leftover scratch file `apps/zoom/tests/test_dbg_tmp.py` (my own debug file from the interrupted run) was deleted; `templates/partials/field.html` and the `TimeInput(format="%H:%M")` widgets in `apps/zoom/forms.py` were already in their fix-cycle-1 state (no stale revert found — `git diff` matched the committed fix-cycle diff exactly); no pytest process was running in the `web` container (`ps` via `/proc`: only `runserver`); the compose project showed the dev stack running cleanly (`polymath-tmd:dev`, both containers healthy, not half-switched to prod). Pre-existing dev-DB clutter from earlier tasks' manual verification (`LinkRequest`s ZL-0019–ZL-0029/0042/0068, user `it.check`) was found but not deleted: `it.check` is `decided_by` on 6 historical approved requests (a `PROTECT` FK), so removing it risks a destructive failure or cascading deletes of unrelated records, and none of it is attributable to this interrupted session specifically. This is flagged for the owner rather than acted on destructively.

### Checklist (re-run from scratch)

- `ruff check .` — all checks passed. ✅
- `ruff format --check .` — 114 files already formatted. ✅
- `pytest --create-db` — run twice, clean (no file-redirect quirks this time): **1262 passed, 0 failed**, both times. ✅
- `test_move_models.py` + `test_move_services.py` + `test_move_views.py` + `test_move_race.py` + `test_move_stale.py` — run 3 extra times with `--reuse-db`: **157 passed** every time, 0 failures, 0 flakes. ✅
- `python manage.py makemigrations --check --dry-run` — No changes detected. ✅
- `python manage.py check` — 0 issues. ✅
- `python manage.py check --database default` — 0 issues. ✅
- Migration `0008_move_classes` — re-confirmed reversible: `migrate zoom 0007` unapplies it, `migrate zoom 0008` re-applies cleanly. ✅
- `check --deploy` (prod stack, `USE_HTTPS=True`, run for extra confidence even though no settings changed) — 2 warnings, both expected and accepted: `security.W021` (HSTS preload, accepted project-wide) and `zoom.W001` (expected: this walkthrough ran with `ZOOM_PROVIDER=manual`). No new or unexplained warning. ✅
- Static files on the prod image — `style.910cfb033e2d.css` and `app.2456fc2beeea.js` both 200. ✅

**One non-reproducing flake noted, unrelated to this brief.** An ad-hoc full-suite run with `-rA` (not one of the two official `--create-db` runs) showed one failure, `test_cancel_views.py::test_the_manual_provider_is_not_set_up` — a timestamp mismatch between two separate calls to `services.start_token()` (task 011's signed start-link, not touched by this brief). Rerun alone 5/5 times: passed every time. Did not reproduce in either of the two clean `--create-db` runs recorded above (both 1262/1262, 0 failures). This looks like real-clock second-boundary timing jitter in a pre-existing task-011 test, not a regression from fix cycle 1; flagged for awareness, not blocking this brief's criteria.

### Criteria 28–31: mapped to tests, spot-checked against the old code

**Criterion 28** (the forms really pre-fill, `D15`).
- Test: `apps/zoom/tests/test_move_views.py::test_the_rendered_move_page_prefills_the_current_date_and_times`, plus the 005-guard test (name read from the frontend's fix-cycle notes: the request-form bound-invalid-value test). Both pass.
- **Spot-check:** reverted `templates/partials/field.html` line 2's `value=field.subwidgets.0.data.value` back to the old `value=field.value`. Reran the prefill test: **failed**, reproducing the exact original defect (`value="Oct. 7, 2026"` / `value="7 a.m."` instead of ISO/`HH:MM`). Restored the one line, confirmed with `git diff` that the file matched its pre-revert state exactly, and the test passed again.
- **Confirmed live, real browser (Edge/Chromium, headless, 1440px):** `zoom:move_class` for an approved weekly booking rendered `10/06/2026` in the date input and `09:00 AM` / `12:00 PM` in the time inputs — the browser's native display of a correctly-formatted `value="2026-10-06"` / `value="09:00"` / `value="12:00"`. Screenshot: `move_class_1440.png` (scratchpad). The same page fetched over real HTTP confirmed the raw attributes directly: `value="2026-10-06"`, and the "unchanged" pinned error (criterion 2) rendered correctly when re-posting the same time.
- **005's request form still works:** empty GET renders no stray `value`; an invalid bound POST (`first_date=2026-10-05`, `start_time=08:30`, `end_time=25:99`) re-rendered all three values exactly as typed, with `aria-invalid="true"` on `end_time`, confirmed live over HTTP on the prod image.

**Criterion 29** (the five pinned messages).
- Tests: `test_move_models.py::test_the_pinned_one_class_messages`, `test_the_pinned_messages_2_and_4`, `test_the_blocked_note_is_only_for_a_moved_day`, `test_a_class_moved_to_another_day_blocks_the_series`; `test_move_services.py::test_the_pinned_race_messages`. All five texts (1a, 1b, 2, 3, 4) checked byte-for-byte against the brief's table, including the two D.12-exact rendered examples (`MOVED_1A`, `CHANGED_1B`). All match exactly. ✅

**Criterion 30** (the stale-form check, `D17`).
- Tests: `apps/zoom/tests/test_move_stale.py`'s four tests (one class, series ×2, cancel-meanwhile), run cleanly 3 extra times (11/11 each run, part of the 157-test re-runs above).
- **Spot-check:** added `shown = None` at the top of `services._plan_move`, disabling the stale comparison (simulating the pre-D17 "POST-start `expected=`" behaviour the brief describes as the bug). Reran `test_move_stale.py`: **3 of 4 tests failed** (`test_a_stale_one_class_form_is_refused_then_works_again`, both parametrizations of `test_a_stale_series_form_is_refused_then_works_again`) with `assert 302 == 409` — i.e. A's stale POST silently overwrote B's committed move, exactly the correctness bug D17 names. The fourth test (cancel-meanwhile) didn't hit the stale path and still passed, as expected. Restored the one line, confirmed with `grep` that no trace of the revert remained, and all 5 tests (4 + the parametrized pair counted once) passed again.
- **Confirmed live, two real HTTP sessions** against the same class of an approved weekly booking (manual provider, prod image): session A opened `move_class`, session B opened the same page, B moved the class first (200 → 302 → detail), then A posted its stale form. Result: **409**, the exact pinned message 1a naming B's new time (`Someone else moved this class a moment ago. It's now Wed 7 Oct 2026, 10:00 am to 11:00 am. …`), A's typed values (`14:00`, `15:00`, `2026-10-07`) kept in the re-rendered inputs, a fresh `shown` issued, the database still holding B's time (`2026-10-07 04:30:00+00:00`–`05:30:00+00:00` UTC = 10:00–11:00 Colombo, `moved_by` = the session's user), and the container's console-backend email log showing **exactly one** "Class times changed" email (B's) — none for A's refused attempt.

**Criterion 31** (the blocked series box, `D17`).
- Tests: `test_move_models.py::test_a_class_moved_to_another_day_blocks_the_series`, `test_the_blocked_note_is_only_for_a_moved_day`; `test_move_views.py::test_a_series_blocked_by_a_moved_day_is_explained_on_the_detail`, `test_nothing_moved_means_no_blocked_note_and_the_usual_box`, `test_a_class_in_progress_hides_the_box_and_has_no_blocked_note`, `test_other_bookings_never_carry_a_blocked_note`. All pass; the view test renders the real `detail.html` and asserts the exact message text and the absence of the `zoom:move_series` link.
- **Confirmed live:** moved one class of an approved weekly booking to a different weekday (Mon→Tue), then loaded the detail page over real HTTP. The `Change the time of the remaining classes` box held message 2 exactly (`The class now on Tue 6 Oct 2026, 9:00 am to 12:00 pm was moved to a different day, so the remaining classes can't be changed together. Move each class on its own instead, with Move this class.`) and carried **no** link/button to `zoom:move_series`. Screenshot: `detail_630_blocked_1440.png` (scratchpad), which also shows the row carrying both `Move this class` and `Cancel this class`, the `Moved` tag, and `Moved by verifier012 on Fri 2 Oct 2026, 9:42 am.` with its full stop (criteria 6 and 29 confirmed together in the same screenshot).

### Shared-partial regression sweep (`field.html`), real HTTP on the prod image, `ZOOM_PROVIDER=manual`

Built a throwaway superuser, a throwaway Zoom account and two throwaway approved bookings via the ORM (through `services.approve()` with manual meeting details, as the real approve flow leaves things), then drove every changed or field.html-dependent form over `http://localhost:8010` with a cookie-jar HTTP client, following each page's own CSRF token:

| Form | GET | Invalid POST: values kept + `aria-invalid` | Notes |
|---|---|---|---|
| 005 request form (public) | 200, label present, no stray date value | ✅ (`first_date`, `start_time` kept; `end_time="25:99"` kept as typed; `aria-invalid="true"` on `end_time`) | `<b>HTTP check</b>` rendered escaped, not raw |
| `zoom:account_add` | 200 | ✅ (`email="not-an-email"` kept, `aria-invalid` set) | |
| `zoom:account_edit` | 200, `value="Verify HTTP Account"` prefilled | — | |
| `accounts:staff_add` | 200 | ✅ (`email="bad"` kept) | |
| `accounts:staff_edit` | 200, `value="http.staff"` prefilled | — | |
| `accounts:staff_password` | 200, no password value in any input | ✅ (empty/invalid POST re-renders 200, no password value leaked) | |
| `accounts:password_change` (own) | 200, label for `old_password` | ✅ (invalid old password re-renders 200, no password value leaked) | |
| `zoom:cancel` | 200 | — (not posted; already covered by 011's own suite) | |
| `zoom:move_class` | 200, date/time prefilled ISO/`HH:MM`, `shown` hidden field present | ✅ (reposting the same time re-rendered the pinned "unchanged" non-field error, typed values kept) | |
| `zoom:move_series` | 200, times prefilled `HH:MM`, `shown` present | — (successful POST → 302 → detail) | |

No form lost its prefill, its kept-values-on-error behaviour, its `aria-invalid`/`aria-describedby` wiring, or its password guard after the `field.html` change. The password guard (010's rule, re-stated in the frontend's fix-cycle header comment) held on both password forms.

All throwaway records (2 `LinkRequest`s, 2 `HostAccount`s, 1 superuser, 1 staff user) were deleted via the ORM after the walkthrough, confirmed at 0 remaining rows.

### Stack restored

`docker compose up -d --build` (prod, `ZOOM_PROVIDER=manual`) was used for the walkthrough; afterwards `docker compose -f compose.yaml -f compose.dev.yaml up -d --build` restored the dev stack (the one running before this session started), confirmed healthy (`polymath-tmd:dev`, both containers up) with `python manage.py check` clean.

### Updated coverage table (28–31)

| # | Criterion | Test(s) | Result |
|---|---|---|---|
| 28 | Forms really pre-fill (shared `field.html`) | `test_the_rendered_move_page_prefills_the_current_date_and_times`, 005 bound-invalid guard test; spot-check revert fails on old code; live Edge screenshot | ✅ |
| 29 | Five pinned messages | `test_the_pinned_one_class_messages`, `test_the_pinned_messages_2_and_4`, `test_the_pinned_race_messages`, plus the D.12-exact rendered examples | ✅ |
| 30 | Stale form never overwrites another move | `test_move_stale.py` (4 tests, 3 extra reruns, 0 flakes); spot-check revert (`shown = None`) fails 3/4 on old code; live two-session HTTP race (409, message 1a, kept values, fresh `shown`, exactly one email, correct stored state) | ✅ |
| 31 | Blocked series change explained on detail | `test_a_class_moved_to_another_day_blocks_the_series`, `test_the_blocked_note_is_only_for_a_moved_day`, `test_a_series_blocked_by_a_moved_day_is_explained_on_the_detail`, `test_nothing_moved_means_no_blocked_note_and_the_usual_box`, `test_a_class_in_progress_hides_the_box_and_has_no_blocked_note`, `test_other_bookings_never_carry_a_blocked_note`; live screenshot | ✅ |

Criteria 1–19, 21–25 and 27 were re-run (not just re-read) as part of the full `pytest --create-db` passes above and are unchanged from the first verification pass; no regression found. Criterion 20 (README) remains correctly not-yet-done, owned by the docs writer at step 6. Criterion 26 (the owner's live check) remains pending, as instructed.

## Re-verification (fix cycle 2)

**Verdict: PASS** (criteria 1–19, 21–25, 27–33, with B1/SF1/SF2/D19 all re-tested and confirmed fixed). Criterion 20 is still correctly not done (docs writer, step 6). Criterion 26 remains the owner's live check, still pending.

### Checklist (re-run from scratch, dev stack, `polymath-tmd:dev`)

- `ruff check .` — all checks passed. ✅
- `ruff format --check .` — 114 files already formatted. ✅
- `pytest --create-db` — run twice: **1298 passed**, 0 failed, both times. ✅
- `test_move_models.py` + `test_move_services.py` + `test_move_views.py` + `test_move_race.py` + `test_move_stale.py` — run 3 extra times with `--reuse-db`: **193 passed** every time, 0 failures, 0 flakes. ✅
- `test_cancel_views.py` + `test_cancel_services.py` + `test_cancel_models.py` — run 5 extra times with `--reuse-db` to confirm the 011 flake is gone: **151 passed** every time, 0 failures. The `signing.dumps`-comparison defect the reviewer named (`test_cancel_views.py:480,582`, `test_cancel_services.py:582` and the matching line) is fixed; no non-reproducing failure seen in any of the 5 runs. ✅
- `python manage.py makemigrations --check --dry-run` — No changes detected. ✅
- `python manage.py check` — 0 issues. ✅
- Migration `0008_move_classes` — still the only migration for this brief; already confirmed reversible in the first verification pass, unchanged since. ✅
- `check --deploy` — **n/a, correctly:** no settings changed in this fix cycle (backend and frontend notes both confirm "Dependencies and settings: none").

### Spot-checks: new tests fail on the old code, then restore confirmed (step 2)

All three reverts were made with the Edit tool directly on the working tree (nothing here is committed, so "old code" means the pre-round-1-fix behaviour each criterion describes), the relevant test run to show the failure, then the edit undone and `git diff <file>` compared line-for-line against the pre-revert diff to confirm an exact restoration, then the test re-run to confirm it passes again.

- **B1 (criterion 33), the refresh points in `views.py`.** Changed `_MoveView.get_context_data`'s `if refresh_shown or not form.is_bound:` to `if True:` (simulating "every re-render signs a fresh `shown`", the blocker's own description). Reran `test_move_stale.py`: **2 of 7 failed** — `test_an_invalid_post_keeps_the_stale_shown_so_the_next_post_is_refused` and `test_an_invalid_series_post_keeps_the_stale_shown_too` — the other 5 (including the three already-fixed-in-cycle-1 stale tests) still passed. Restored the one line; `git diff apps/zoom/views.py` matched the pre-revert diff exactly; reran: **7/7 passed**.
- **Criterion 32's put-back steps, one of them.** In `_put_series_back`, inserted `back.done = True; return` immediately after the restoring series `PATCH`, before `_tidy_series_in_zoom` (simulating SF1's original "one `PATCH` only" restore). Reran `test_a_series_zoom_got_wrong_is_put_back_fully`: **failed** — `assert zoom.methods() == ["PATCH", "GET", "PATCH", "GET", "DELETE", "PATCH", "GET"]` got only `["PATCH", "GET", "PATCH"]` (the forward attempt's own `PATCH`/`GET` plus the one restoring `PATCH`), while the log still said "Put ZL-… back to its stored times" and the result was `DATES_DIFFER` — exactly SF1's complaint: the page would say "nothing was changed" after a restore that in Zoom's reality left cancelled classes undeleted and the flattened class unfixed. Restored the two lines; `git diff apps/zoom/services.py` matched exactly; reran: **passed**.
- **Criterion 14's daily-limit classification.** In `zoom_api._api_error`, changed `if status == 429: return ZoomDailyLimit() if _is_daily_limit(response) else ZoomBusy()` to `return ZoomBusy()` unconditionally (simulating the pre-D19 "every 429 stays busy" fallback; left `_token_error`'s unrelated, correctly-unconditional `ZoomBusy()` for 429 untouched). Reran `test_a_429_is_the_daily_limit_only_when_zoom_says_daily`: **4 of 9 cases failed** (`documented-daily-text`, `daily-any-case`, `daily-header`, `daily-header-any-case` — every case carrying a daily signal), while the 5 "not daily" cases (per-second, non-JSON, empty, non-object, non-text message) still passed, confirming the revert touched only the daily-signal path. Restored the one line; `git diff apps/zoom/zoom_api.py` matched exactly; reran together with `test_daily_in_any_other_refusal_isnt_the_daily_limit`: **10/10 passed**.

After all three reverts were undone, the full move/stale/race module run was repeated once more: **193 passed**, confirming no residual edit was left behind.

### Live, dev stack, fake provider (step 3)

A throwaway `HostAccount` ("Verify B1 Account", fake provider) and a throwaway weekly `LinkRequest` (ZL-0634, two users `verify_a`/`verify_b` in the IT desk group) were built **through real HTTP requests against the running dev server** (`http://localhost:8010`), not through `manage.py shell` — the first attempt used `manage.py shell` to approve the booking and failed with `ZoomMeetingNotFound` (Zoom error 3001) on the move, because `FakeProvider`'s steerable state is a **class-level, in-process** store (`providers.py`'s own docstring: "Class-level state so a test can inspect and steer the instance a view created"), and `manage.py shell` runs in a separate OS process from the dev server's `runserver` worker, so nothing created there is visible to it. Confirmed via `docker compose … logs web`: the approval that mattered (and the moves that followed) show **no reload** in between, i.e. one continuous server process, which is what made the HTTP-only approach work.

- **B1's two-session sequence, in full, over real HTTP, with two separate cookie jars:**
  1. A (`verify_a`) logs in, GETs `zoom:move_class` for ZL-0634's Tue 6 Oct 8:00–9:00 class (occurrence 940) and captures its `shown` and CSRF token. (This GET also re-confirmed criterion 28/5's pre-fill live: `value="2026-10-06"`, `value="08:00"`, `value="09:00"`.)
  2. B (`verify_b`) logs in separately, GETs the same page fresh, and POSTs a valid move to 10:00–11:00 → **302** to the detail page. Log: `Moved 1 class(es) of ZL-0634 on Verify B1 Account.` and one `Subject: Class times changed: ZL-0634 Verify B1 Class`.
  3. A POSTs an **invalid** time (end 08:00 before start 09:00) with A's original `shown` and CSRF → **200**, field error `The class must end after it starts. Check the end time.`, and the re-rendered hidden `shown` **byte-identical** to A's original value (confirmed by diffing the two captured tokens).
  4. A POSTs a **valid** new time (14:00–15:00) with that same re-rendered `shown` → **409**, notice `Someone else moved this class a moment ago. It's now Tue 6 Oct 2026, 10:00 am to 11:00 am. We didn't make your change. If it still needs to move, check the time in the form and press the button again.` (message 1a, naming B's time exactly).
  5. Server log for the whole sequence shows exactly **one** "Moved" line and **one** "Class times changed" email — A's steps 3 and 4 produced neither. DB check after step 4: occurrence 940 still at `04:30`–`05:30` UTC (= 10:00–11:00 Colombo, B's time), `moved_by = verify_b`.

  This reproduces the verifier's fix-cycle-1 live check but now also proves the fix-cycle-2 blocker (B1): the invalid post in step 3 did **not** refresh `shown`, so the stale check in step 4 still fired. All data (the `LinkRequest`, its `Occurrence`s, the `HostAccount` and both users) was deleted afterwards; confirmed 0 remaining rows.
- **A failed series move that is put back, steering the fake to fail: not reproducible live, by design, not attempted as a workaround.** `FakeProvider.update_errors` / `snapshot_errors` are set via plain Python attribute assignment, and the only place that happens is test code and `manage.py shell` — both of which run in a process separate from the dev server, per the finding above. Steering it live would need a debug-only endpoint added to product code, which is outside what a verifier may change. This path is instead covered by: (a) the full automated `test_move_services.py` suite (`test_a_series_zoom_got_wrong_is_put_back_fully`, the six `test_a_failure_at_any_step_of_putting_it_back_says_so` cases, the two lock-race tests, all passing in the `--create-db` runs above), and (b) this session's own spot-check revert above, which proved the mechanism is load-bearing (the old one-`PATCH` behaviour fails the exact test that guards it).

### Prod image, `ZOOM_PROVIDER=manual` (step 4)

`docker compose up -d --build` with `ZOOM_PROVIDER=manual` (confirmed inside the container: `settings.ZOOM_PROVIDER == "manual"`), waited for `web` healthy, created a throwaway superuser (`verifier012b`), a throwaway `HostAccount` and a throwaway one-off `LinkRequest` (ZL-0636), approved it via real HTTP with manual meeting details.

- **`zoom:move_class` form:** GET renders `value="2026-10-05"`, `value="09:00"`, `value="10:00"` (ISO/`HH:MM`, criterion 28 holds on the prod image) and the manual `Check Zoom for clashes first` notice (`checks_zoom` false). POSTing an invalid time (`start_time=25:99`) re-rendered **200** with `value="25:99"` kept exactly as typed and `aria-invalid="true"`.
- **One other `field.html` form, the public 005 request form:** POSTing `end_time=25:99` (with valid `first_date`/`start_time`) re-rendered **200** with all three values kept exactly as typed (`first_date="2026-10-05"`, `start_time="08:30"`, `end_time="25:99"`, `aria-invalid="true"` on `end_time`) — no regression from the `field.html` loop-variable rename (C1b).
- Static files: `/static/css/style.css` → 200; `staticfiles/css/style.910cfb033e2d.css` present (hashed, manifest storage working).

All throwaway records (2 `LinkRequest`s, 2 `HostAccount`s, 1 superuser) were deleted afterwards via the ORM; confirmed 0 remaining rows.

### Judgment on the backend's documented deviation (step 5)

**Criterion 32** says the put-back's "target times and occurrence IDs come from the locked rows, **never** from the failed attempt's in-memory progress." The implementation (`_put_one_class_back`, `services.py`) reads `target.zoom_occurrence_id or progress.zoom_occurrence_id` — i.e. it falls back to the failed attempt's own `progress.zoom_occurrence_id` **only when** the locked row's stored ID is blank.

**Ruling: complies, as a disclosed and soundly-reasoned exception — not a FAIL.**

- It is a literal deviation from the word "never", and the backend's own implementation notes say so in those terms, without hedging.
- But the data that fallback uses is not stale, remembered state: it is the ID `occurrence_id_for` looked up **fresh from Zoom, inside this same failed attempt**, moments before the transaction rolled back and erased it from the locked row. It reflects Zoom's actual current state at least as reliably as a plain `GET` would, not a guess carried over from an earlier, unrelated attempt.
- The alternative — strictly refusing to use it — is strictly worse in the one case it affects (a booking approved before the live Zoom connection, whose occurrence ID was never stored): the restore would send nothing and declare `ZoomMeetingNotFound`, even though a correct ID was just read back and is sitting in memory. "Never" bought no correctness here, only a guaranteed failure in an edge case the fix was clearly written to catch (there is a dedicated test, `test_a_blank_id_is_put_back_by_the_id_the_move_looked_up`, confirmed passing in this session's runs).
- The underlying review nit this criterion was built from said "prefer the locked row's `zoom_occurrence_id` over `progress`'s" — softer than "never" — and the backend's notes state the implementation "follows the main session's nit instruction," i.e. this reading was not invented unilaterally by the backend; it is explicitly flagged for the reviewer rather than buried.
- No honesty or safety property is weakened: when **both** IDs are blank, nothing is sent and `ZoomMeetingNotFound` is still raised and reported truthfully; the fallback only ever supplies a correct, freshly-verified ID, never a fabricated one.

This is reported precisely so the code reviewer can rule on the wording (tighten criterion 32's text to "the locked row's ID, falling back to the same attempt's own fresh look-up only when the locked row has none" rather than a bare "never") rather than being silently accepted or silently failed.

### Stack restored

`docker compose -f compose.yaml -f compose.dev.yaml up -d --build` restored the dev stack (`polymath-tmd:dev`, the one running before this session started); confirmed healthy and `python manage.py check` clean; a final `pytest --reuse-db` full-suite run passed (1298) to confirm the restore left the stack in a working state.

## Re-verification (fix cycle 3)

**Verdict: PASS**, scoped to D21 and criteria 11, 12, 13, 15 and 32 (amended twice), per the main session's instruction. Criteria 1–10, 14, 16–19, 21–25, 27–31 and 33 are unaffected by this cycle (no files besides `apps/zoom/services.py` and `apps/zoom/tests/test_move_services.py` changed) and were re-confirmed only by the two full `--create-db` runs below, not individually re-read. Criterion 20 (README) is still correctly not done — docs writer, step 6. Criterion 26 (owner's live check) remains pending.

### Checklist (dev stack, `polymath-tmd:dev`, already running; no other agent running pytest)

- `ruff check .` — all checks passed. ✅
- `ruff format --check .` — 114 files already formatted. ✅
- `pytest --create-db` — run twice: **1303 passed**, 0 failed, both times (matches the backend's report). ✅
- `test_move_models.py` + `test_move_services.py` + `test_move_views.py` + `test_move_race.py` + `test_move_stale.py` — run 3 extra times with `--reuse-db`: **198 passed** every time, 0 failures, 0 flakes. ✅
- `python manage.py makemigrations --check --dry-run` — No changes detected. ✅
- `python manage.py check` — System check identified no issues (0 silenced). ✅
- `check --deploy` — **n/a, correctly:** backend's notes confirm "Dependencies and settings: none" for this cycle; no settings changed.
- Prod HTTP walkthrough — **n/a, correctly:** this cycle is backend-only (`services.py` plus its own test file), no template, view-shape or settings change; nothing new to exercise over HTTP beyond what cycles 1–2 already proved for the surrounding views.

### Spot-check (step 2): old `MOVE_NOT_PUT_BACK` text and the old always-the-same message choice

Edited `apps/zoom/services.py` directly on the working tree (nothing here is committed for task 012 yet):
1. Replaced `MOVE_NOT_PUT_BACK`'s pinned D21 text with the pre-D21 wording (`"We couldn't save the new time here or undo it in Zoom. Zoom now has {label}'s meeting {meeting_id} at the new time. …"`, the false claim D21 exists to remove — confirmed as the old text from the brief's own D21/D.13 discussion, lines 466, 1375, 1416, 1694 of this brief).
2. Replaced `message = MOVE_PARTLY_PUT_BACK if back.landed else MOVE_NOT_PUT_BACK` with `message = MOVE_NOT_PUT_BACK` unconditionally (the old always-the-same choice D21 replaces).

Reran the affected tests (`--reuse-db`): **12 failed** — `test_a_failure_at_any_step_of_putting_it_back_says_so` (all 6 parametrized cases: `1 series patch`, `2 read-back`, `2 delete`, `3 class patch`, `4 final read-back`, `4 mismatch`), `test_a_second_lock_race_while_putting_it_back_says_so`, `test_a_second_lock_race_before_any_restoring_update_says_not_put_back`, `test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back`, `test_a_failure_after_zoom_changed_it_and_a_failed_restore`, `test_the_error_line_is_neutral_and_holds_nothing_from_zoom`, `test_the_two_put_back_messages_are_pinned` — every one on the exact-text or the mapping assertion (`MOVE_PARTLY_PUT_BACK` expected, `MOVE_NOT_PUT_BACK`'s old text returned, or vice versa). `test_one_class_undone_then_its_own_transaction_failing_counts_as_done` (both params) still passed, correctly: that path never reaches the `MOVE_NOT_PUT_BACK`/`MOVE_PARTLY_PUT_BACK` branch (it's `done`).

Reverted both edits; `diff` against a pre-edit copy of the file showed the two changes exactly and nothing else, confirming an exact restoration. Reran `test_move_services.py` alone: **101 passed** (matches the backend's reported count for that file).

### The ERROR log line (step 3)

Ran `test_the_error_line_is_neutral_and_holds_nothing_from_zoom` on the unmodified code with `-s` to see the captured line directly:

```
ERROR    apps.zoom.services:services.py:1447 Moving ZL-1847: Zoom meeting 81234567890 doesn't match this database: OperationalError (putting it back: ZoomRejected, restoring update answered: no)
```

This matches criterion 32's pinned form exactly: `Moving {reference}: Zoom meeting {meeting_id} doesn't match this database: {move's error class} (putting it back: {failure class or "mismatch"}, restoring update answered: {yes|no})`. The test also asserts, over the whole `caplog` at `DEBUG` with a Zoom refusal body carrying `RAW-ZOOM-TEXT` and a secret: no `new time`, `has the` or `http` anywhere in the line, and none of `RAW-ZOOM-TEXT`, `zoom.us` or any of the test's `SECRETS` constants anywhere in the full captured log. Passed on the unmodified code (see the two clean `--create-db` runs above).

### Judgement (step 4): the one-class undo-answered-then-transaction-fails edge

**Question:** once a one-class undo `PATCH` has been answered, does treating a later 1213/1205 (or any other `DatabaseError`) in the put-back's own transaction as **done**, with no retry, comply with criteria 32 and D21?

**Ruling: complies, and is explicitly required by the brief's own text, not just permitted.**

- Criterion 32's table states this outcome in so many words: "one class: the undo `PATCH` answered, then its own transaction failed | yes | yes | **done**: no failure message from the put-back (see the one-class edge above)." The bullet above it spells out why: "If the undo `PATCH` is answered but the put-back's own (write-free) transaction then fails, Zoom already matches the database. So the put-back counts as **done**." A retry is never mentioned for this edge; the general retry-once rule is stated for "a MySQL deadlock or lock-wait timeout" on the put-back as a whole, and the one-class edge is carved out from it by name.
- The code (`_put_zoom_back`, `services.py:1823-1855`) matches this precisely: the `DatabaseError` handler's first branch is `if one_class and back.landed:`, which fires for `OperationalError` (which covers both 1213/1205 and a dropped connection) and any other `DatabaseError`, sets `done = True`, logs one `WARNING` with the reference and error class name, and returns without looping back for another attempt. Only when that branch doesn't apply does the code fall through to the retry-on-1213/1205 logic.
- The reasoning holds up mechanically, not just by citation: for one class, the restoring `PATCH` is the transaction's last action and the transaction writes nothing to the database either side of it. Once Zoom has answered that `PATCH`, Zoom holds the time the locked row held at the moment it was read — which is the database's time, by definition of "locked row." A failure in committing (or holding the lock through) a transaction that made no writes cannot un-send the `PATCH` or change what Zoom now holds, so there's nothing a retry could fix: a second `PATCH` would send the identical value already confirmed delivered. This is different from the series path, where the `PATCH` is only step 1 of a multi-step restore and later steps (the read-back, deletes, flattened-class patches, the final check) are what make Zoom match — correctly, the series path still retries and does not short-circuit on `landed`.
- **Tests exist and pass for exactly this:** `test_one_class_undone_then_its_own_transaction_failing_counts_as_done[lost connection|deadlock]` (confirmed passing in both clean `--create-db` runs and the 3 extra `--reuse-db` re-runs above) asserts `MOVING_AT_THE_SAME_MOMENT`, exactly 3 `PATCH`es total (no second undo `PATCH`), no `ERROR` line, the `WARNING` line present with reference and error class, and the database left unchanged by the put-back's failed transaction.
- No honesty property is weakened: the message shown to IT (`MOVING_AT_THE_SAME_MOMENT`, or `MOVE_MAYBE_RESTORED` if the move itself went unanswered) is true — Zoom's state matches the database, nothing was silently left wrong — and no `ERROR` is suppressed that criterion 32 requires; criterion 32 requires an `ERROR` only for the "not done" outcomes, and this one is defined as done.

This was not a deviation needing disclosure — the backend's own fix-cycle-3 notes state it as the planned behaviour, cite the same criterion-32 bullet, and the brief agrees word for word. Nothing here needed a design-decision ruling from the main session the way the fix-cycle-2 occurrence-ID fallback did.

### Stack restored

The dev stack (`polymath-tmd:dev`, `db` and `web`) was already running when this cycle started and was never stopped or switched; `docker compose -f compose.yaml -f compose.dev.yaml ps` confirms both containers still `Up`/`healthy` at the end, with `python manage.py check` clean. No prod stack was started this cycle (not needed — see Checklist). The one file touched during the spot-check (`apps/zoom/services.py`) was restored to its pre-spot-check content; `diff` against a saved copy confirmed an exact match before the final test run.

## Re-verification (fix cycle 4)

**Verdict: PASS**, scoped to criterion 34 (D22) and criterion 32's two review-round-2 nits (the catch-all and the clock-stamped token test), per the main session's instruction. No settings, templates or migrations changed this cycle (backend's own report confirms this; `git status` before and after matches the session's opening snapshot exactly). Criteria 1–31 and 33 are unaffected (no files besides `apps/zoom/errors.py`, `apps/zoom/services.py`, `apps/zoom/tests/test_daily_limit.py` (new), `apps/zoom/tests/test_move_services.py` and `apps/zoom/tests/test_services.py` changed) and were re-confirmed only by the two full `--create-db` runs below, not individually re-read. Criterion 20 (README) remains correctly not done — docs writer, step 6. Criterion 26 (owner's live check) remains pending.

### Checklist (dev stack, `polymath-tmd:dev`, already running; confirmed by `docker inspect` as the dev image/mounts; no other agent running pytest)

- `ruff check .` — all checks passed. ✅
- `ruff format --check .` — 115 files already formatted. ✅
- `pytest --create-db` — run twice: **1314 passed**, 0 failed, both times (matches the backend's reported 1314). ✅
- `test_services.py` — run 3 extra times with `--reuse-db`: **43 passed** every time, 0 failures, 0 flakes. Confirms the clock-stamped-token flake (round 2 nit) is gone. ✅
- `test_move_models.py` + `test_move_services.py` + `test_move_views.py` + `test_move_race.py` + `test_move_stale.py` + `test_daily_limit.py` — run 3 extra times with `--reuse-db`: **209 passed** every time, 0 failures, 0 flakes. ✅
- `python manage.py makemigrations --check --dry-run` — No changes detected. ✅
- `python manage.py check` — System check identified no issues (0 silenced). ✅
- `check --deploy` — **n/a, correctly:** no settings changed this cycle (backend's notes: "Dependencies and settings: none"; the diff touches only `errors.py`, `services.py` and three test files).
- Prod HTTP walkthrough — **n/a, correctly:** backend-only cycle, every new text goes in an existing notice or flash with no template change (confirmed: `templates/` has no diff beyond what fix cycles 1–3 already covered, and `git status` shows no new template files this cycle).

As a final sanity check after the spot-checks below, the whole `apps/zoom/` suite was re-run once more: **987 passed**, 0 failures.

### Spot-checks (step 2)

Both done directly on the working tree (nothing for task 012 is committed yet), one at a time, each followed by re-reading the touched function to confirm an exact restoration (not just a visual `git diff`, since the whole file is uncommitted and a plain `git diff` would show the pre-existing, unrelated changes too):

1. **The daily-before-lasting check in one caller** (`move_lookup_failed_message`, `services.py:1265-1277`, criterion 34 row 3). Removed the `if isinstance(error, ZoomDailyLimit): step = daily_reset_sentence()` branch, leaving only the `elif error.lasting` / `else` pair.
   - Ran `test_daily_limit.py::test_a_daily_limit_on_the_moves_look_up_says_when_to_try_again`: **1 failed**. The rendered text fell back to the old lasting step (`"… Ask whoever manages the Zoom accounts to press Check connection for Zoom 02."`) instead of the reset sentence (`"… Try again after 5:30 am on Tue 29 Sep 2026."`), confirming the check is load-bearing.
   - Restored the two removed lines; re-read `services.py:1265-1277` and confirmed it matches the original exactly. Re-ran the same test: **1 passed**.
2. **The catch-all in `_put_zoom_back`** (`services.py:1884-1892`, criterion 32's nit). Removed the entire `except Exception as exc: … back.failure = type(exc).__name__` block (8 lines, including the one-class-edge check), leaving the `try` to fall straight to `else` with no catch for an unexpected exception.
   - Ran the four catch-all tests in `test_move_services.py -k unexpected_error`: **4 failed**, all with an unhandled `RuntimeError: RAW-ZOOM-TEXT unexpected detail 7731` propagating out of `_put_zoom_back` instead of being turned into the neutral `ERROR` line / `WARNING` / pinned message, confirming the catch-all is load-bearing.
   - Restored the removed block; re-read `services.py:1866-1900` and confirmed it matches the original exactly (the `except DatabaseError`, `except _DatesDiffer`, `except ProviderError`, `except Exception`, `else` chain, in order). Re-ran the same four tests: **4 passed**.

`git status --short` at the end of this cycle lists exactly the same files as the session's opening snapshot (13 modified, 7 untracked under `apps/zoom`/`templates/zoom`), confirming no residue from either spot-check.

### Other error kinds still show their earlier pinned text (step 3)

Only the daily case changed; every other error kind's text is unchanged, each proven by an existing test that passed unmodified in the runs above:

- **006 criterion 28** (approve's create failure, non-daily): `test_a_create_that_certainly_made_nothing` (`test_zoom_approve.py`) is parametrized over connection error, connect timeout, 429, a 401 and a Zoom 300 — all still render the pre-existing `Try again in a few minutes.` / `LASTING` ("… press Check connection for Zoom 01, then try again.") texts, untouched by criterion 34.
- **006 criterion 30(a)** (approve's look-up failure, non-daily): `test_if_zoom_cant_be_asked_at_approval_nothing_is_booked` (`test_zoom_approve.py`) is parametrized the same way, with the same unchanged `LASTING` text for the two lasting cases.
- **006 criterion 36** (Check connection, non-daily lasting): `test_zoom_accounts_connection.py:299-308`'s case still renders `"Couldn't check Zoom 03 with Zoom: Zoom error 300. Waiting won't fix this. Tell whoever looks after the server, and give them the Zoom error number."` exactly — the one text criterion 34 explicitly keeps out of the daily case (`test_a_daily_limit_on_check_connection_says_when_to_try_again` asserts this string is absent from the daily message).
- **011 criterion 12** (cancel, non-daily): `test_zoom_said_no_rolls_everything_back_with_one_message_per_kind` (`test_cancel_services.py`) is parametrized over connection error, timeout, 429, 401, a missing-scope 400, a 404 and a generic 400 — all keep the pre-existing `Try again in a few minutes.` / `LASTING` ("… press Check connection for Zoom 02, then try again.") texts.
- **The move messages**: `test_no_move_message_ever_offers_another_account` (`test_move_services.py:1132`) still scans every `MOVE_MESSAGES` entry, including the now-reset-sentence-bearing `MOVE_DAILY_LIMIT`, and finds no `another free account`; `MOVE_NOT_PUT_BACK` and `MOVE_PARTLY_PUT_BACK`'s D21 texts are unchanged (not touched by this cycle's diff).

### Template form: `{reset}` filled by `daily_reset_sentence()` (step 4)

Read `apps/zoom/tests/test_daily_limit.py` in full. Each of the five callers' tests asserts the fully rendered text against criterion 34's table, character for character, at the frozen now (Mon 28 Sep 2026, 10:00 Colombo):

- 1a `test_a_daily_limit_on_approves_create_says_when_to_try_again`: `"We couldn't make the meeting in Zoom: Zoom's daily limit for this account is used up. Nothing was booked. Choose another free account, or wait for this one. Try again after 5:30 am on Tue 29 Sep 2026."` — matches the table exactly.
- 1b `test_a_daily_limit_on_approves_look_up_says_when_to_try_again`: matches the table's row 1b exactly.
- 2 `test_a_daily_limit_on_cancel_says_when_to_try_again`: matches row 2 exactly.
- 3 `test_a_daily_limit_on_the_moves_look_up_says_when_to_try_again`: matches row 3 exactly.
- 4 `test_a_daily_limit_on_check_connection_says_when_to_try_again`: matches row 4 exactly, at level `ERROR`, with `Waiting won't fix this` and `Zoom error number` both asserted absent.
- 5 `test_a_daily_limit_on_the_account_list_names_the_reason`: the detail page's row, rendered through the real `zoom/partials/avail_item.html` (not a stub), shows `Couldn't check with Zoom` followed by `Zoom's daily limit for this account is used up.` — matches row 5.
- `test_the_daily_reset_sentence_is_p5s` confirms the helper alone (`"Try again after 5:30 am on Tue 29 Sep 2026."` at the frozen now and at 02:00 Colombo; rolls to `"Try again after 5:30 am on Wed 30 Sep 2026."` once past the reset at 06:00), and that `MOVE_DAILY_LIMIT` built through it still equals criterion 14's original pinned text.

The backend's two disclosed form-only deviations (`{reset}` as one placeholder rather than spelling out `Try again after {time} on {date}.` twice) change no rendered character; all texts above read exactly as the table specifies. All 1314+ passing tests back this, and all five were independently re-run in the 3 extra `--reuse-db` passes above with no flakes.

### Judgment (step 5): the catch-all and the one-class answered undo

**Question:** does generalising the one-class edge — once a one-class undo `PATCH` has been answered, *any* later error in the put-back's own transaction (not only a `DatabaseError`) counts as done — comply with criterion 32?

**Ruling: complies.**

- Read `services.py:1866-1900` and `1904-1912`. `back.landed` is set to `True` only inside `_restoring_update` (`services.py:1932-1935`), strictly after the restoring `update(**kwargs)` call has returned without raising — i.e. only once Zoom has actually answered the `PATCH`. The catch-all's guard, `if one_class and back.landed`, can therefore only fire for an exception raised *after* that point, inside the same write-free transaction, for a one-class move. That is exactly the condition criterion 32's one-class-edge prose describes: "If the undo `PATCH` is answered but the put-back's own (write-free) transaction then fails, Zoom already matches the database." That sentence is not qualified by failure type — it says "the put-back's own (write-free) transaction then fails," not "fails with a `DatabaseError`."
- The mechanical reasoning is independent of what kind of exception follows: the transaction makes no writes either side of the `PATCH`, so once Zoom has answered it, nothing left in that transaction — whatever throws afterwards — can change what Zoom now holds or what the database holds. A `RuntimeError` from an unrelated bug is no different, for this purpose, than a `1213` deadlock: Zoom already matches the database, and no further action could make it match any better.
- The main table's literal row ("one class: the undo `PATCH` answered, then its own transaction failed | yes | yes | **done**") sits directly under the `DatabaseError` handling in the code, but the prose above it states the general principle the table's row is an instance of, and the fix-cycle-3 re-verification (round 3 of this brief) already ruled the identical reasoning compliant for the `DatabaseError` case specifically, on exactly this prose.
- The one place of genuine textual tension is the review-round-2 nit's own wording ("returns the criterion 32 table's message for the current `back.landed` (`MOVE_NOT_PUT_BACK` or `MOVE_PARTLY_PUT_BACK`)"), which names only two outcomes and doesn't mention "done." Read narrowly, that sentence would forbid the generalisation. But the nit's purpose, stated in its own heading ("An unexpected error can't skip that line"), is to stop an uncaught exception from *escaping* `_put_zoom_back` ungoverned — not to relitigate the already-settled one-class-done outcome. Omitting "done" from that one-line summary reads as the nit not having been re-checked against the one-class edge when it was written, rather than as a deliberate narrowing: nothing in review round 2's text discusses the one-class edge at all, and the backend flagged the tension itself for the reviewer rather than resolving it silently.
- The series path is unaffected: `one_class` is `False` for a series, so a series always falls through to `back.failure = type(exc).__name__` and picks `MOVE_PARTLY_PUT_BACK` (once landed) via the normal post-loop logic — confirmed by `test_an_unexpected_error_while_putting_a_series_back_still_says_so[after it lands]` passing with `MOVE_PARTLY_PUT_BACK`, not "done," in all runs above.
- No honesty property is weakened: the message shown (the move's own outcome, e.g. `MOVING_AT_THE_SAME_MOMENT`) is true, Zoom matches the database, and criterion 32 requires an `ERROR` only for the "not done" outcomes — this one is, by the general principle, correctly "done."

This is the same judgment the backend reached in its fix-cycle-4 notes ("One judgement for the reviewer"); the main session should still route it to `tmd-code-reviewer` as the nit was originally theirs, but on the merits it complies with criterion 32 as written.

### Live, dev stack, fake provider (step 6)

**Could not be done over HTTP; relied on the tests instead, as the instruction allows.** Read `apps/zoom/providers.py:266-333` (`FakeProvider`): every steering hook (`update_errors`, `delete_error`, `unavailable`, `snapshot_errors`, etc.) is plain Python class-level state, set only by calling test code in the same process. There is no view, URL, query parameter or form field anywhere in `apps/zoom/urls.py` or `views.py` that exposes any of this to a browser session — consistent with the project's "no Django admin, no hidden magic" rule — and setting it from a separate `docker compose exec web python manage.py shell` process would not reach the already-running `runserver` process's memory, so it would have no visible effect even as a workaround. This was confirmed by inspection, not attempted against the running server. The daily-limit behaviour for Check connection and cancel is instead proven by `test_a_daily_limit_on_check_connection_says_when_to_try_again` and `test_a_daily_limit_on_cancel_says_when_to_try_again` (both in `test_daily_limit.py`, both re-run 3 extra times above with no flakes), which drive the same code paths (`services.check_connection`, `services.cancel`) through a mocked Zoom `429` exactly as a real daily-limit answer would arrive.

### Stack restored

The dev stack (`polymath-tmd:dev`, `db` and `web`) was already running when this cycle started (`Up 46 minutes`, `db` healthy) and was never stopped or switched; confirmed still `Up`/`healthy` at the end via `docker compose -f compose.yaml -f compose.dev.yaml ps`, with `python manage.py check` clean. No prod stack was started this cycle (not needed — see Checklist). Both files touched during the spot-checks (`apps/zoom/services.py`, edited twice, once per spot-check) were restored to their pre-spot-check content each time; `git status --short` at the end matches the session's opening snapshot exactly, and the full `apps/zoom/` suite (987 tests) passed cleanly after both restorations.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-10-02 (re-verification after fix cycle 1: PASS, 1262 tests ×2)

**Verdict: CHANGES REQUESTED.**

**Blocker**
- **B1: a form that fails validation loses its stale-form protection.**
  - Where: `views.py:751, 762-764`; `forms.py:339-345`.
  - What happens: every re-render calls `set_shown()`, which takes fresh times. The sequence that breaks it:
    1. A opens the move form.
    2. B moves the class.
    3. A posts an invalid time and gets a 200 with a new `shown`, and no warning.
    4. A posts a valid time, and B's move is undone.

    D17 forbids exactly this, and `test_move_stale.py` has no stale-plus-invalid case.
  - Fix: refresh `shown` only on GET, on the 409 stale refusal and on the 400 out-of-date page. Otherwise keep the posted value.
  - Test: A opens the form, B moves the class, A posts invalid (200), A posts valid. Expect 409 with 1a, zero Zoom calls and zero emails.
  - Owner: backend.

**Should fix**
- **SF1: a failed series move can bring cancelled classes back in Zoom, and the message says "Nothing was changed".**
  - Where: `services.py:1745-1756`.
  - What happens: the restore is one series PATCH. It never re-deletes the cancelled dates, and it flattens any single-class same-day move. Every restore path says "nothing was changed", which isn't true in Zoom.
  - Option (a), preferred by the reviewer: after a restore PATCH succeeds, run the same GET-and-delete as the forward path, sharing one helper. If that fails, show `MOVE_NOT_PUT_BACK` and log an ERROR. This changes criterion 11's "one PATCH".
  - Option (b): keep one PATCH, and log an ERROR plus an honest message that some classes may be back in Zoom.
  - **Owner to rule.**
- **SF2: `_put_zoom_back` has no deadlock retry and doesn't follow the lock order.**
  - Where: `services.py:1724-1759`.
  - What happens: it locks the request, then the classes, with no account lock. That can deadlock against another booking's move or approve, and then it shows the worst message while Zoom keeps the wrong time.
  - Fix: retry once on 1213/1205, and lock request, then account, then classes.
  - Owner: backend.

**Nits**
- `services.py:1737`: the restore should prefer the locked row's `zoom_occurrence_id` over `progress`'s.
- `field.html:2,4`: rename the attrs loop variable (it shadows `value`), and note in the header that choice widgets must never be passed.
- `services.py:1466`: message 1b is misleading after a same-day single-class move (pinned copy). Follow-up for the designer and planner.
- `detail.html:1`: a header comment is missing a space.
- `services.py:1604`: comment why `occurrence.host_account = account` is set.
- **The task-011 flake is a test defect.** `test_cancel_views.py:480, 582` compare two `signing.dumps` outputs, which embed the real-clock second. Compare against the requested token, or decode it. Optional: make `start_token` deterministic with `Signer.sign_object`, since it has no `max_age`.

**Recommendation, pending owner sign-off**
- Classify a 429 as `ZoomDailyLimit` when Zoom's message contains "daily" (or Zoom's rate-limit header says so). Otherwise it stays `ZoomBusy`.
- Zoom's text only picks between two of our fixed messages; it is never shown or logged. 006's rule would be reworded to "never shown or logged".
- Today every 429 says "Try again in a few minutes", which keeps failing on a day the limit is reached.

**Live check addition:** in step 26.1, after moving one class, cancel it and confirm it's gone in Zoom. A 404 on delete counts as done, so a changed occurrence ID would fail silently.

**Sound:**
- The lock order and sequence match `approve()` and `cancel()`, and the restore sets Zoom to the database's current times (17a).
- The stale check: a unique salt, it runs before any Zoom call and again under the locks, with the correct 400/409.
- `field.html` across every form, including the password guard.
- The pinned messages, P2, P5 and P6.
- The email.
- The criterion 27 and 31 templates, which stay presentation-only.
- Migration 0008 can be reversed.

### Round 2 — 2026-10-02 (after fix cycles 2 and 3; re-verification PASS, 1303 tests ×2)

**Verdict: CHANGES REQUESTED.** There are no blockers. The four focus areas are correct:
- **`_put_zoom_back` and its helpers:** the lock order is request, then account, then classes. The retry carries `landed` over. Every row of criterion 32's table picks the right message. The series anchor avoids flattening, and the ERROR line is neutral.
- **B1:** `stale` is set only by `_plan_move`'s two refusals. Every other re-render keeps the posted `shown`.
- **429 classification:** `_is_daily_limit` returns only a bool, and Zoom's text never leaves the function.
- **One-class edge:** "done" is true. A retry could only re-send the same time, and the edge is guarded to one class only.

**Should fix**
1. **A daily limit outside the move PATCH gets the wrong next step.**
   - **Where:** `services.py:206-208, 865-868, 1233-1238, 2192-2195`.
   - **Cause:** `zoom_api` raises `ZoomDailyLimit` (lasting) for every API 429. That means approve's create, cancel's DELETE, the move's step-1 lookup and Check connection now pick their "lasting" next step. That step says "press Check connection" or "Waiting won't fix this…", which can't help with a daily limit and breaks D.2.6. Approve's create counts against the same per-user daily quota, so this will happen in practice.
   - **Fix:** one helper for the reset sentence, using `zoom_daily_reset()` and P5's wording. In all four callers, check for the daily case before `lasting`. Approve keeps "Choose another free account" in front of the reset sentence. The designer writes the four texts, the planner pins them, the backend adds one test per caller.

**Nits**
- `tests/test_services.py:279`: the same clock-stamped token flake as in the 011 tests. Decode the token from the email body instead.
- `services.py:1826-1846`: `_put_zoom_back` has no final `except Exception`. An unexpected error escapes before the neutral ERROR line is written and replaces the move's own exception. Add a final catch that records the class name as `failure`.

### Round 3 — 2026-10-02 (after fix cycle 4; re-verification PASS, 1314 tests ×2)

**Verdict: APPROVE.** No blockers and no should-fix findings.

- **Should-fix 1 (round 2): fixed.**
  - The daily limit is checked before `lasting` in `next_step` (`services.py:236`, which also covers the leftover-meeting delete at :656), in `cancel_failed_message` (:901), in `move_lookup_failed_message` (:1271) and in `check_connection` (:2249, which uses `CHECK_DAILY_LIMIT`).
  - The account list picks up the new phrase.
  - `daily_reset_sentence()` is the only place the reset sentence is built.
  - Every other error kind takes its old branch.
- **Nits: fixed.**
  - The catch-all in `_put_zoom_back` (:1884-1892) never raises, keeps only the class name and keeps the move's own exception. The one-class rule lives in one helper, and `landed` is set only once `update()` has returned.
  - The token test now decodes the token from the email.
- **New nits (optional):**
  - The catch-all logs no traceback. That's the right default; if it ever has to be diagnosed, log stack frames without the message.
  - A daily-limit 429 on the public start page shows the generic "couldn't reach Zoom" text. That isn't a regression, and it's outside criterion 34.
- **For the docs writer at close:**
  - Add dated amendment notes to 006 (criteria 28, 30(a) and 36) and 011 (criterion 12).
  - Reword "Zoom's text is ignored" to "never shown or logged" (D19) wherever the README or CLAUDE.md still says it.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Status stays `Verifying`.** Round 3 approved everything with no blockers and no should-fix
findings; the round-3 "for the docs writer at close" list (dated amendment notes, and the D19
wording change) is done, below. The one thing still open is criterion 26, the owner's live check
against a real paid Zoom account (move one class and confirm it in Zoom, then cancel it and confirm
it's really gone; change a series' time and confirm every remaining occurrence, including that an
earlier cancel stays cancelled; confirm the join link, meeting ID and start-link window are
unchanged; try a time that overlaps a meeting made directly in Zoom). This brief closes (`Status:
Done`) once the owner reports criterion 26's results back; until then it stays exactly where round
3 left it.

**Files updated**

- `README.md`:
  - new subsection "Moving a class, or changing a series' time" under "Zoom link requests" (what a
    move can and can't do, the same clash checks as an approval, never offering another account,
    the one email, and what happens if Zoom's answer to a move is uncertain or fails);
  - "Connecting an account to Zoom": the scope list gains `meeting:update:meeting:admin`, and a new
    "Adding the move scope to an account connected before task 012" subsection gives the owner's
    D8 steps for an app set up before this task (add the scope in the Marketplace app, save, then
    restart `web` once every account is updated, since a token fetched earlier doesn't carry it);
  - "Known limits": a new bullet on Zoom's 100-creates-or-updates-a-day limit per Zoom user, when it
    resets, and that Zoom's own wording for the error is read only to recognise it, never shown or
    logged (D19);
  - the go-live gate rewritten: it now lists all five of 006, 011, 012, 013 and 014, each with its
    own owner live check, replacing the earlier "006 + 011" gate (D12).
- `CLAUDE.md`:
  - the `zoom` architecture bullet gains the move flow's lock order and single `PATCH` inside it,
    `_put_zoom_back`'s undo-and-recheck shape, the signed `shown` field that stops a stale form from
    overwriting someone else's move, and `services.daily_reset_sentence()` as the one place the
    daily-limit reset sentence is built, plus the "never shown or logged" wording for Zoom's own
    error text (D19, amending 006 criterion 10);
  - the shared form partials bullet gains `field.html`'s fix: it prints the widget's own formatted
    value, not the raw field value, so a date or time field really pre-fills instead of rendering a
    display-localised string a browser silently drops, and a reminder it must never be given a
    choice widget.
- `docs/CHANGELOG.md` — a new newest-first entry, 2026-10-02, "012: Move a class (awaiting the
  owner's live check)": user-visible changes (moving one class or a series' time, never offering
  another account, the one "was/now" email, honest undo-and-recheck messages, the daily-limit
  message, the owner setup needed before go-live), then technical notes (migration `0008`, the
  stale-form `shown` protection, the shared `field.html` pre-fill fix, the daily-limit
  classification and its one reset-sentence helper, the task-011 clock-stamped-token flake fix, the
  `cancellable_classes` → `remaining_classes` rename, the go-live gate update, and the verification
  and review verdicts) and follow-ups (message 1b's wording after a same-day one-class move, a
  daily limit on the public start page still showing the generic message, the undo catch-all
  logging no traceback by design, and briefs 013–014 next).
- `docs/tasks/006-live-zoom-connection.md` — dated "Amended by 012" notes on criteria 10 (the new
  `ZoomDailyLimit` error kind, for a daily-limit 429 only), 28 (approve's look-up-failure next step)
  and 30(a) (approve's create-failure next step), and 36 (Check connection's new `CHECK_DAILY_LIMIT`
  row), each pointing at criterion 34's exact wording. The existing criteria text is unchanged.
- `docs/tasks/011-cancel-and-start-link.md` — a dated "Amended by 012" note by criterion 3's method
  list recording the `cancellable_classes()` → `remaining_classes()` rename, and one on criterion 12
  (cancel's daily-limit next step). The existing criteria text is unchanged.
- `docs/design/class-rows.md` and `docs/design/busy-button.md` — checked against the brief and the
  built templates; both were already current (the designer amended them in step 1b, G6), so no
  change was needed.
- This brief (`docs/tasks/012-move-a-class.md`) — this Docs section. `Status` is left `Verifying`.
<!-- owner: tmd-docs-writer — files updated; closes Status -->
