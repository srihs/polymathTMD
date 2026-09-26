# 011 — Cancel a booking, and start a class from a link instead of the host key

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Verifying <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

The owner's words (2026-09-26):

> so what we need is zoom to linked via api or anyither means and create/cancel meetings via the app without user has to login to zoom app. This application will be the interface for zoom. Research on how to do this and ask questions if you have to.

The owner's answers to the main session's questions (2026-09-26, relayed):

1. **Accounts:** keep 11 separate Zoom accounts, each with its own Server-to-Server OAuth app (006's D2 stands).
2. **Plan:** Pro. One meeting at a time per host.
3. **Starting a class:** a "Start this class" link replaces emailing the host key. The approval email carries a signed, expiring link to the app, scoped to one booking or class, working only from about 30 minutes before the class until it ends. On use, the app calls `GET /meetings/{id}` and redirects (302) to the fresh `start_url`. The `start_url` is never stored, logged or emailed; the responses carry `Cache-Control: no-store` and `Referrer-Policy: no-referrer`, and each use is logged. The host key is no longer emailed, and the waiting room can stay on. The planner recommends what to do with host-key storage.
4. **Scope:** cancel (one class or the whole series), reschedule (one class or the series), sync from Zoom by webhooks, and email recording links when `recording.completed` fires.

The owner's answers to this brief's questions (2026-09-26, relayed):

- **Q1:** "Keep as IT-only fallback". Host keys stay stored and encrypted, and are no longer emailed. IT can reveal an account's key in the app as a fallback (D11).
- **Q2:** "No, IT cancels" (D12).

**Reading.** The app already makes meetings through the Zoom API with no Zoom sign-in (brief 006). What's missing is everything after approval. This work is split into four briefs (see Scope). **This brief, 011, holds the two pieces production needs before it takes real requests.**

- **Cancel this booking.** IT cancels a whole booking, or one class of a weekly booking, from the request's page. The app deletes it in Zoom, frees the account's time, records who cancelled and why, and emails the requester.
- **Start this class.** The approval email stops carrying the host key. Instead it carries one private link to the app. From 30 minutes before each class until it ends, that link shows a `Start this class` button. Pressing it asks Zoom for a fresh host start link and sends the browser straight there, so the teacher starts the meeting as host without signing in to Zoom. The Zoom start link is never kept anywhere.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**How the owner's four items are split, and in what order** (`program-planning:scoping-framework`):

| Order | Brief | What | Depends on | Go-live gate? |
|---|---|---|---|---|
| 1 | **011 (this)** | Cancel a booking or one class; the start link replaces the emailed host key | 006 (`delete_meeting`, `zoom_occurrence_id`) | **Yes** (006's D14) |
| 2 | 012 | Move one class, or change the time of a booking's remaining classes | 011 (cancelled classes must be skipped; the booking lock pattern) | No |
| 3 | 013 | Webhooks: the app updates itself when a meeting is changed or deleted directly in Zoom | 011 (cancel a class), 012 (move a class) — the webhook reuses both | No |
| 4 | 014 | Email the recording link to the requester when Zoom finishes a recording | 013 (the verified webhook endpoint) | No |

- **Why four briefs.** Each is about one model group plus its screens. 011 adds a status and a public page, 012 adds a clash-checked write to Zoom, 013 adds a public inbound endpoint with its own secrets, and 014 adds a new record type and a new scope. Together they'd be too big to review in one pass.
- **Why this order.** 013 has to handle cancels and moves made in Zoom, so it reuses the model operations 011 and 012 build. 014 needs 013's verified endpoint. 012 must know about cancelled classes, so it comes after 011.
- **The go-live gate is unchanged:** 006 plus 011 (006's D14). 012–014 can follow after go-live. Until 012, a class is moved by cancelling it and asking for a new request. Until 013, changes made directly in Zoom aren't seen (006's D15).

**In scope (011)**

- **Model** (`apps/zoom/models.py`, migration `0006`):
  - a new `cancelled` status;
  - who cancelled and when, per request and per class, with the reason per class;
  - "booked" stops counting cancelled classes, so the account is free again;
  - the cancel rules and the start-link window, on the model.
- **Permission name:** a data migration renames `zoom.review_linkrequest` (D8).
- **Services:** `cancel()`, the start-link token, `start_class()`, and the cancellation email. `approve()` stops decrypting the host key.
- **Provider:** `can_start`, `start_url()` and `occurrence_id_for()`.
- **Host-key fallback** (owner, Q1; D11): an IT-only `Show host key` action on the account's change page, with a record of every reveal (`HostKeyReveal`). This amends brief 008's "write-only, never shown back".
- **Screens:**
  - the request detail gains `Cancel this booking`, `Cancel this class`, cancelled markers and the `Start link` row;
  - the Zoom account change page gains `Show host key` and the last reveal; a new reveal page shows the key once;
  - a cancel confirmation page (one template for both kinds);
  - the queue gains a `Cancelled` tab;
  - a new public `Start this class` page.
- **Emails:** the approval email swaps the host key for the start link; a new cancellation email.
- **Setting (`tmd-devops`):** `IT_DESK_PHONE`, so the public start page can show a tap-to-call number (P1; criterion 47).
- **Copy amendments:** 008's criterion 17 ("or been cancelled"), the host-key copy that says keys are emailed, and the approval-email-failed flash.

**Out of scope (011)**

- Moving classes (012). Changes made in Zoom (013). Recordings (014).
- **Requesters cancelling their own booking** (owner, Q2: "No, IT cancels"; D12).
- **Removing host-key storage** (owner, Q1: keep it as a fallback; D11). There's no clean-up brief.
- Showing the host key anywhere but the reveal page (not on the request detail, not in any email, list or message).
- Restoring a cancelled booking. A mistaken cancel is fixed by approving a new request.
- Moving a booking to another account.
- Cancelling a class that has started. Cancelling a whole booking while one of its classes is in progress.
- Resending the approval email (008's D10 follow-up stays open). The detail page shows the start link, so IT can copy it instead.
- Revoking one start link without cancelling (D5, follow-up).
- Storing start-link uses in the database. They're logged only (owner: "log each use").

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- These carry over from briefs 005, 006 and 008:
  - the frozen "now", **Mon 28 Sep 2026, 10:00** Asia/Colombo;
  - "IT user", "plain user", "mocked Zoom" and "the zoom provider";
  - the network block (006 criterion 45);
  - the pinned-copy rule: the designer may propose changes through the main session, and they're made here first.
- **The example booking** is ZL-0042, weekly on Mon and Wed, 5–28 Oct 2026, 8:30–11:30 (8 classes). It's approved on Zoom 02 as meeting `81234567890`, with a stored `zoom_occurrence_id` per class. The one-off example is ZL-0043, Mon 5 Oct 2026, 8:30–11:30, on Zoom 02 as meeting `81234560000`.
- **Booked class:** a class of an approved request, with an account, and not cancelled. **Started:** `starts_at <= now`. **In progress:** `starts_at <= now < ends_at`.

### Model

1. **Status and fields** (migration `0006`, reversible):
   - `LinkRequest.Status` gains `CANCELLED = "cancelled", "Cancelled"`.
   - `LinkRequest` gains `cancelled_at` (`DateTimeField`, null) and `cancelled_by` (FK to the user, `PROTECT`, null, `related_name="+"`).
   - `Occurrence` gains `cancelled_at` (null), `cancelled_by` (FK, `PROTECT`, null, `related_name="+"`) and `cancel_reason` (`TextField`, blank, at most 1000 characters by the form).
   - **New check constraints** (MySQL enforces them; a test proves each with a raw `UPDATE` that raises `IntegrityError`):
     - `zoom_linkrequest_cancelled_was_booked`: `status="cancelled"` requires a `host_account`, a non-empty `join_url` and a `cancelled_at`;
     - `zoom_occurrence_cancel_has_reason`: `cancelled_at` null, or `cancel_reason` non-empty.
2. **Cancelled classes aren't booked.** `BOOKED` gains `cancelled_at__isnull=True`, so it's still defined once. After ZL-0042's Wed 7 Oct class is cancelled:
   - `Occurrence.objects.booked()` leaves it out;
   - a waiting request for Wed 7 Oct 9:00–10:00 sees Zoom 02 free in `availability_for()` and on the detail page;
   - the timetable month and day pages don't show it;
   - `HostAccount.upcoming_classes()`, `with_upcoming()` and 008's stop-booking count are one lower;
   - its `HostSlot` rows are gone. The other seven classes keep theirs.
3. **Cancel rules live on the model**:
   - `Occurrence.can_be_cancelled(now=None)`: booked and not started.
   - `LinkRequest.class_in_progress(now=None)`: the booked class in progress, or `None`.
   - `LinkRequest.cancellable_classes(now=None)`: booked, not-started classes, soonest first.
   - `LinkRequest.can_cancel_booking(now=None)`: approved, at least one cancellable class, and no class in progress.
   - `LinkRequest.status_after_cancel(now=None)`: `cancelled` when none of its classes is both not cancelled and not ended; otherwise `approved`.

   Table test at the frozen now, for ZL-0042 in these cases:
   - untouched → `can_cancel_booking` true, 8 cancellable;
   - the frozen now moved to Mon 5 Oct 9:00 → class in progress, `can_cancel_booking` false, 7 cancellable;
   - moved to Tue 6 Oct 10:00 → `can_cancel_booking` true, 7 cancellable;
   - after cancelling all 7 remaining classes on Tue 6 Oct → `status_after_cancel` is `cancelled` (one held class stays booked);
   - after cancelling one class only → `approved`.

   A waiting, rejected or cancelled request is never cancellable.
4. **Classes that happened keep their history.** Cancelling a booking never changes a class that has started: its host, slots and `cancelled_at` stay as they were.

### Cancelling: screens and permissions

5. **URLs and access.**
   - `zoom:cancel` (pk) is the whole booking. `zoom:cancel_class` (pk, occurrence pk) is one class.
   - Both are `GET` (the confirm page) and `POST` (do it). Both need `zoom.review_linkrequest`: anonymous → sign-in redirect, plain user → 403.
   - They're 404 for: a request that isn't approved, a class that isn't this request's, and `zoom:cancel_class` on a one-off request (its only class is the booking; use `zoom:cancel`).
6. **When there's nothing to do**, both GET and POST redirect (302) to `zoom:detail` with one error message and make no Zoom call:

   | Case | Message (pinned) |
   |---|---|
   | whole booking, a class in progress | `{class} is in progress. Cancel the rest of this booking after it ends at {end time}.` where `{class}` is `Mon 5 Oct 2026, 8:30 am to 11:30 am` |
   | whole booking, no cancellable class | `There are no classes left to cancel in this booking.` |
   | one class, started | `That class has already started, so it can't be cancelled.` |
   | one class, already cancelled | `That class was already cancelled.` |

7. **The confirm page** (`zoom/cancel_confirm.html`, in the shell). It lists:
   - the classes that **will** be cancelled;
   - for a whole booking with held classes, the classes that **stay** as they were.

   It has one required field, `reason`, labelled `Why is it cancelled?`, with help `This goes in the email to the requester.` and at most 1000 characters.
   - **The widget is set on `CancelForm`** (G7, D13): a `Textarea` with `rows="4"` and `maxlength="1000"`, plus the label and help, so `partials/field.html` renders it unchanged. A test checks the rendered attributes.
   - Empty reason: the page re-renders (200) with the error summary and the field error `Tell the requester why it's cancelled.`
   - The typed reason is kept on every re-render.
   - **The safe way out** (P4, D14) is a link to `zoom:detail` labelled `Keep the booking` on a whole-booking cancel, and `Keep the class` on a one-class cancel.
   - **The final button** is `Cancel and email the requester`, styled `.button--danger` (the designer's new component; criterion 35).
8. **Detail page, approved or cancelled booking** (IT users only):
   - `Cancel this booking` (link to `zoom:cancel`) shows when `can_cancel_booking`.
   - **When an approved booking can't be cancelled now** (G2, D13), the page shows criterion 6's whole-booking message in place of the link: the in-progress sentence, or `There are no classes left to cancel in this booking.`. It's taken from the same model constants.
   - **The class in progress** (G1, D13) shows the tag `In progress` (icon plus word) in the Classes list, so IT can see why it has no `Cancel this class` link.
   - On a weekly booking, each cancellable class in the Classes list has `Cancel this class` (link to `zoom:cancel_class`). Its accessible name includes the class date.
   - Each cancelled class shows the tag `Cancelled` (icon plus word), with `Cancelled by {name} on {when}: {reason}`.
   - A cancelled booking shows the notice `This booking was cancelled by {name} on {when}.`, and keeps its `Booked on`, `Zoom link` and `Meeting ID` rows for the record.
   - A plain user never reaches the page (005).
9. **Queue.** `QUEUE_TABS` becomes Waiting, Link sent, Not approved, **Cancelled**, All. `tab_counts()` adds `cancelled`, still in one aggregate query. The Cancelled tab orders by `-cancelled_at, -pk`. The status tag partial shows `Cancelled` with its own icon (the designer chooses it).

### Cancelling: what happens

10. **Order of work** (D2). An ordered log (HTTP through `responses` callbacks, SQL through `connection.execute_wrapper`) of a successful whole cancel shows:
    1. the locking reads `zoom_linkrequest`, then `zoom_hostaccount`, then `zoom_occurrence`;
    2. the `UPDATE` of the occurrences, the `DELETE` of their slots, and the `UPDATE` of the request;
    3. then exactly one Zoom `DELETE`;
    4. then the commit.

    No Zoom call is made before the locks. The view is `non_atomic_requests` and `services.cancel()` owns the transaction, as `approve()` does.
11. **Which Zoom call.** Every delete sends `schedule_for_reminder=false` and `cancel_meeting_reminder=false`, because the app sends its own email (D6).

    | Cancel | Call |
    |---|---|
    | whole booking (one-off or weekly, held classes or not) | `DELETE /meetings/{meeting_id}` |
    | one class of a weekly booking | `DELETE /meetings/{meeting_id}?occurrence_id={zoom_occurrence_id}` |
    | one class whose `zoom_occurrence_id` is blank, zoom provider | first `GET /meetings/{meeting_id}`, whose occurrence starting at the class's `starts_at` gives the ID; then the delete. If Zoom has no such occurrence, it's treated as already gone and the class is cancelled with no delete |

    A `404` with Zoom code 3001 counts as done (006, already in `zoom_api`).
12. **Zoom said no, for certain** (a connection error, a connect timeout, a 429, or any 4xx other than 3001). Everything is rolled back: no class cancelled, slots unchanged, no email. The confirm page re-renders (200), keeping the reason, with the notice `We couldn't cancel it in Zoom: {phrase}. Nothing was cancelled. {next step}`. The next step:
    - temporary: `Try again in a few minutes.`
    - lasting: `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.`

    A test pins one message per 006 error kind.
13. **Zoom may have done it** (`maybe_done`: a read timeout, a dropped connection, a 5xx). The same rollback happens, and the notice reads `We couldn't tell whether Zoom removed it: no answer from Zoom. Nothing was cancelled here. Try again in a few minutes. Trying again is safe.` It's safe because criterion 11's 3001 rule makes a repeated delete succeed.
14. **Saving fails after Zoom removed it.** The test forces an exception at the request `UPDATE` after the mocked delete succeeded.
    - A MySQL deadlock is retried once, as in `approve()`. The retry's delete gets 3001, which counts as done, and the cancel then succeeds.
    - Any other failure: nothing is cancelled here, and the notice reads `Zoom removed it, but saving the cancellation here failed. Press Cancel again to finish.` Exactly one `ERROR` log record holds only the reference, the meeting ID and the exception class name.
15. **Success.** The view redirects (302) to `zoom:detail` with one message:

    | Case | Level | Message |
    |---|---|---|
    | whole booking, emailed | success | `Cancelled the booking. We emailed {email}.` |
    | one class, emailed | success | `Cancelled the class on {Mon 5 Oct 2026}. We emailed {email}.` |
    | the email failed | warning | `Cancelled, but the email to {email} didn't send. Tell them yourself.` |

    With the `manual` provider, which can't reach Zoom, each message gains ` This system can't reach Zoom: delete it in Zoom too.` The fake provider records the delete in `FakeProvider.deleted`.
16. **Races** (`transaction=True` thread tests, as in 005 criterion 38 and 006 criterion 32):
    - **(a)** Two threads cancel the same class: exactly one Zoom `DELETE` and one email. The loser redirects with `That class was already cancelled.`
    - **(b)** A cancel and an approval of another request for the same account and time: whichever order they commit in, no two booked classes overlap on the account. If the cancel commits first, the approval succeeds.
    - **(c)** A whole cancel and a class cancel of the same booking: one Zoom `DELETE` for the whole meeting, and at most one more that gets 3001. The final state is `cancelled` with every not-started class cancelled.

    The verifier records the output. A flaky thread test is a FAIL, never a skip.
17. **The cancellation email** goes to `requester_email` only (no cc or bcc), plain text, after the commit.
    - **Subject:** `Cancelled: {reference} {class_name}`.
    - **Body:**
      - the classes cancelled, one per line (as `Occurrence.__str__`);
      - `Reason: {reason}`;
      - when classes are still to come: `Your other classes are still on, with the same link and start link.` When the provider can't start (`can_start` false, P3), it's `Your other classes are still on, with the same link.`;
      - `Zoom doesn't tell the people you shared the link with. Please let your students know.` (P5);
      - `To book again, send a new request: {absolute zoom:request URL}`.
    - It contains no join link, passcode, start link or host key. A test searches for all four.

### Start this class

18. **Provider.**
    - `MeetingProvider.can_start` is `False` by default, and `True` for `zoom` and `fake`.
    - `start_url(*, host_account, meeting_id) -> str`:
      - **zoom:** calls `GET /meetings/{id}` and returns `start_url`, which must be `https` on host `zoom.us` or a subdomain of it. Otherwise it raises `ZoomUnavailable`. The function is `@sensitive_variables` for the answer and the URL.
      - **fake:** returns `https://zoom.example.invalid/s/{meeting_id}`.
19. **The token.** `services.start_token(link_request)` is `signing.dumps({"r": pk, "m": meeting_id}, salt="apps.zoom.start-class")`, and it has no `max_age` (the window rules). The link is `zoom:start` (token), made absolute. The token is **invalid** when:
    - the signature is bad;
    - the request doesn't exist;
    - the request was never approved;
    - its stored `meeting_id` differs from `m`.
20. **The window** (D4). `Occurrence.start_window() -> (opens_at, closes_at)`:
    - `opens_at` is the later of `starts_at − 30 minutes` and the latest `ends_at` of another booked class on the same account that ends inside `(starts_at − 30 min, starts_at]`;
    - `closes_at` is `ends_at`.
    - `START_WINDOW_MINUTES = 30` is a model constant.

    Tests (Zoom 02, class 8:30–11:30):
    - nothing before it → opens 8:00;
    - another booking 6:30–8:15 → opens 8:15;
    - another booking 6:00–7:45 → opens 8:00;
    - a **cancelled** 6:30–8:15 → opens 8:00;
    - a 6:30–8:15 booking on **another** account → opens 8:00.
21. **The page state.** `LinkRequest.start_state(now=None) -> (state, occurrence)`:

    | State | When | `occurrence` |
    |---|---|---|
    | `ready` | now is inside the window of one of its booked classes | that class |
    | `too_early` | a booked class is still to come, but no window is open | the next one |
    | `ended` | no booked class is still to come, and it isn't cancelled | the last held class |
    | `cancelled` | the request is `cancelled` | `None` |

    A table test covers each state, including the edges: exactly `opens_at` (ready) and exactly `ends_at` (not ready).
22. **`GET zoom:start` (token)** is public, in the public frame, with no sign-in, and never calls Zoom.
    - An invalid token renders the page with state `invalid` and status **404**: `This start link doesn't work. Check you copied all of it.`, followed by criterion 47's contact sentence in its "still" form.
    - Otherwise 200. The page shows the class name and the class date and time, and nothing else about the request (no requester name, email, phone, join link or passcode).
    - Per state:
      - `ready`: a POST form with a CSRF token and the button `Start this class`;
      - `too_early`: `This link works from {opens_at time} on {date}, 30 minutes before the class, until it ends.` When the opening time is later because of an earlier class on the account: `This link works from {opens_at time} on {date}, when the class before it on this Zoom account ends.`;
      - `ended`: `All the classes for this booking have finished.`;
      - `cancelled`: `This booking was cancelled.`
    - Every response from this view (any state, any method, the redirect too) carries `Cache-Control` containing `no-store` and `Referrer-Policy: no-referrer`. A test checks all of them.
23. **`POST zoom:start`**:
    - **`ready`:** one `GET /meetings/{id}`, then a **302** whose `Location` is Zoom's `start_url`.
    - **Any other state:** no HTTP call. The page re-renders in that state.
    - **Zoom failure** (any 006 error kind): 200, with the notice `We couldn't reach Zoom just now. Try again in a minute.`, followed by criterion 47's contact sentence in its "still" form.
    - **`404` code 3001** (meeting gone): 200, with `This class's meeting isn't in Zoom any more.`, followed by criterion 47's contact sentence in its plain form.
    - A POST without a valid CSRF token → 403 (Django's). Django's own CSRF 403 page doesn't carry this view's `no-store`/`no-referrer` headers, because `CsrfViewMiddleware` answers before `StartClassView.dispatch()` ever runs. That's accepted: the page holds no token and no secret, only the generic "Forbidden" text.
24. **The start URL is never kept.** With mocked Zoom returning `start_url` `https://us02web.zoom.us/s/81234567890?zak=SECRETZAK`, the test runs a GET and a POST, with `DEBUG` logging captured for `apps.zoom`, `django`, `urllib3` and `requests`:
    - `SECRETZAK` appears only in the `Location` header;
    - it never appears in any log record, any `zoom_*` table dump, `django.core.cache.cache`, any message, or any sent email.

    The 005 criterion 46 rule, "no `start_url` in any model", still holds.
25. **Each use is logged.** A successful POST writes one `INFO` record: `Start link used for {reference}, class {Mon 5 Oct 2026 8:30 am}, from {client IP}`. It uses `services.client_ip`. A failed POST writes one `WARNING` with the reference and the error class name. Neither contains the token or any URL.
26. **Manual provider** (`can_start` false):
    - the approval email has no start link and says `Ask the IT desk how to start the class as host.`. It doesn't mention a start link anywhere (P3; criterion 28);
    - the cancellation email says `with the same link.` (criterion 17);
    - the detail page has no `Start link` row;
    - `zoom:start` with a valid token renders `Starting a class from a link isn't set up yet.`, followed by criterion 47's contact sentence in its plain form (200), with no form and no HTTP call. The class name and the class's date and time still show (G6).

### The host key stops being emailed (D3, D7)

27. **Approval no longer touches the host key.**
    - `approve()` doesn't call `get_host_key()`.
    - `ApproveResult` has no `host_key`.
    - `Outcome.HOST_KEY_UNREADABLE` and `HOST_KEY_UNREADABLE` are removed.
    - An account whose stored key can't be decrypted is approved normally (a test changes the key list).
    - This amends 005 criterion 64 and 008 criterion 25's second row deliberately.
28. **The approval email** (`approved_body.txt`):
    - The host-key block is replaced, when `can_start`, by:
      ```
      Starting the class as host
      Start link: {absolute start URL}
      Open this link from 30 minutes before each class until it ends, then press Start this class. It starts the meeting as host, with no Zoom sign-in. Keep it private: anyone who has it can start these classes as host.
      ```
    - When `can_start`, a line goes straight after `Use the same link for every class below.`: `Share the join link with your students. Keep the start link to yourself.` (P7).
    - The last paragraph becomes `To change the times, reply to the IT desk. Please don't forward this email, because the start link in it lets anyone start your classes as host.` When there's no start link (`start_url` is `""`, the manual provider; P3), it's only `To change the times, reply to the IT desk.`
    - A test renders the email both ways and asserts that the manual version contains no `start link`, case-insensitively.
    - **No email contains a host key** (005 criterion 61 is amended: the key now appears in none). The test sets a host key on the account and searches every email of the full flow (confirm, IT new request, approval, rejection, cancellation).
29. **The approve form** no longer shows `Host key saved` / `No host key saved`, or the "The email will ask the requester…" help.
30. **Host-key copy that said keys are emailed:**

    | Where | New text |
    |---|---|
    | `views.ACCOUNT_SAVED_NEW_KEY` | `Saved {label} and its new host key.` |
    | `forms.py` host-key help (currently "Approval emails will then tell the requester…") and `account_form.html`'s "Until one is saved, approval emails tell…" line | `Host keys aren't emailed. Teachers start classes with the start link in their approval email. If that link fails, the IT desk can show the key on this page.` (D11) |
    | The change page's `No host key saved` notice body (P6: so it doesn't repeat the field help) | `Save one below so the IT desk has a fallback if a start link doesn't work.` |
    | `APPROVED_EMAIL_FAILED` | `Approved, but the email to {email} didn't send. Copy the Zoom link and the start link below and send them to them yourself.` |

    The tests pinning the old texts are updated deliberately. A scan finds no `goes out with the next approved link` or `tell the requester to ask the IT desk for the host key` in `apps/zoom` or `templates/zoom`.
31. **The detail page's `Start link` row.** An approved booking, with `can_start`, shows `Start link` under `Passcode`: the absolute start URL, wrapping, with help `Send this to the teacher if the approval email went missing. It works from 30 minutes before each class until it ends.` The row doesn't appear on a cancelled booking.

### Permission, copy amendments, rules

32. **Permission name** (D8). A data migration sets the name of `zoom.review_linkrequest` to `Can approve, reject, reschedule or cancel Zoom link requests`. `Meta.permissions` matches. The Staff and access role help (brief 010) shows the new name. The migration is reversible.
33. **008 criterion 17 is amended.** The stop-booking errors end `once the last one has finished or been cancelled.` and `once it has finished or been cancelled.`
34. **Thin views.** The cancel rules, the window and the start state are on the models (criteria 3, 20 and 21). The Zoom calls and the transaction are in `services.cancel()` / `services.start_class()`. Views only parse, call, choose a template and respond.
35. **Template rules** (005 c51, 008 c26, 006 c43): a header comment on every new or changed template; every include ends `only`; no inline styles; no hard-coded paths; sprite symbols exact.
    - The confirm pages, the detail's cancel links and the start page all work without JavaScript.
    - The destructive button is the designer's new `.button--danger` (`docs/design/danger-button.md`). It's used only for the confirm page's final button; the entry links stay `button--secondary`. It meets AA (about 6.6:1).
    - The designer's other new components are used as specified: `.classrows` (`class-rows.md`, the detail's Classes list through `zoom/partials/class_rows.html`) and `.secret` (`secret-value.md`, the reveal page).
    - The new tokens appear only where CLAUDE.md allows: `--red-800` in the first `:root` palette block; `--c-danger`, `--c-danger-hover`, `--c-on-danger`, `--font-mono` and `--fs-secret` read the palette through `var(--…)`. The existing colour-literal test passes.
    - Layout and accessibility hold at 320, 400, 1024 and 1440 px in both modes, including 44px targets and WCAG AA.
36. **No test reaches the network** (006 c45). New provider methods are tested with mocked Zoom. Views steer `FakeProvider`, which gains a steerable `start_error` and records `start_calls`.

### Verification

37. **Automated checks:**
    - `ruff check .` and `ruff format --check .`;
    - `pytest --create-db`;
    - `makemigrations --check --dry-run`;
    - `manage.py check`;
    - `manage.py check --database default`.

    **Settings change** (`IT_DESK_PHONE`, criterion 47), so `check --deploy` also runs on the prod stack with `USE_HTTPS=True`, as in 006 criterion 46. Only W021 (and W001 with `manual`) may appear, both with `IT_DESK_PHONE` empty and with it set to `011 234 5678`.
38. **Prod walkthrough** (no real Zoom). `ZOOM_PROVIDER=manual docker compose up -d --build`, wait for `web` to be healthy, then over HTTP on 8010:
    1. cancel one class of a test weekly booking;
    2. cancel the rest of it;
    3. see the Cancelled tab;
    4. open a start link: the `Starting a class from a link isn't set up yet` page (manual), with the `no-store` and `no-referrer` headers checked with `curl -I`;
    5. static files come from hashed paths.

    Screenshots at 1440 and 400: the confirm page, the detail with cancelled classes, and the start page in `ready`, `too_early` and `ended` (dev, fake provider, time steered). The verifier restores the stack that was running before.
39. **The owner's live check** (one real paid account, credentials supplied at runtime; the verifier records the owner's reported results):
    1. Approve a 2-week, 2-day request.
    2. The email carries a start link and no host key.
    3. Before the window, the link shows `too_early`.
    4. Inside the window, `Start this class` opens the Zoom client as host, with no Zoom sign-in.
    5. **Open the start link's target in a private browser window, then visit `https://zoom.us/profile`.** Note whether it shows the host account signed in. This settles the research's unconfirmed point (D4, R2). **Also note how long the `zak` stays live:** wait a few minutes, then open the very same start URL again in a fresh private window, and record whether it still works. A `zak` that outlives the single fetch it came from widens R2 a little further than the app's own 30-minute class window (review round 1 nit).
    6. Cancel one class: that occurrence is gone in Zoom, and the others remain.
    7. Cancel the rest: the meeting is gone in Zoom. If a held class was cloud-recorded, note whether its recording is still listed in Zoom (D6).
    8. No Zoom email reached the host account about either cancel.
    9. **Added after the owner's answers.** Press `Show host key` for the test account (criterion 41). The key matches the one in the Zoom profile, and the change page then shows the reveal line (criterion 44).
       - **Also confirm (P2):** in the Zoom client the school uses, `Claim host` is under **Participants**, as the reveal page's steps say. If it's somewhere else, report where, and the step's wording is corrected before close.
    10. **Added with the Design (P1).** With `IT_DESK_PHONE` set, open an invalid start link on a phone. The number shows, and tapping it starts a call.

### Added after the owner's answers (2026-09-26): the IT-only host-key fallback (owner, Q1; D11)

40. **The reveal record** (in migration `0006`). New model `HostKeyReveal`:
    - `host_account` (FK, `PROTECT`, `related_name="key_reveals"`);
    - `shown_by` (FK to the user, `PROTECT`);
    - `shown_at` (`auto_now_add`).

    It stores **no** key, and no part or hash of one. It's written only by `services.reveal_host_key()`. The 005 criterion 46 secret-name test passes.
41. **`POST zoom:account_host_key` (pk).**
    - **Access:**
      - It needs `zoom.change_hostaccount`, which the IT desk holds (008 D2). Anonymous users are sent to sign in, a plain user or a `view_hostaccount`-only user gets 403, and `GET` gets 405.
      - An unknown pk gets 404.
      - It requires a CSRF token.
    - **When a readable key is saved:**
      - It writes one `HostKeyReveal` row (`shown_by` = the user).
      - It writes one `INFO` log record: `Host key for {label} shown to {username}`. The record's time is the log timestamp.
      - It renders `zoom/host_key_reveal.html` (200) with the key.
    - **When no key is saved:** it redirects (302) to `zoom:account_edit` with the error `{label} has no host key saved.` It writes no row.
    - **When the saved key can't be read:** it redirects to `zoom:account_edit` with 008's text `A host key is saved, but it can't be read with the current encryption keys. Type it again.`, writes no row, and logs one `WARNING` with the label and `InvalidToken`.
    - **Headers on every response of this view** (the page and both redirects):
      - `Cache-Control` containing `no-store` (Django's `never_cache`);
      - `Referrer-Policy: no-referrer`.

      A test checks all three responses.
42. **The reveal page** (`zoom/host_key_reveal.html`, in the shell, breadcrumb Home › Zoom accounts › {label} › Host key). It holds:
    - the heading `Host key for {label}`;
    - the key, large, in a monospace style, selectable;
    - the guidance, pinned below (the designer's P2, accepted by the main session as D14; it keeps all three of D11's facts);
    - `Back to Change {label}`, a link to `zoom:account_edit`.

    It has no form. Reloading asks the browser to resend the POST, which counts as a new reveal and is recorded again.

    **Guidance (pinned, P2):**
    - **When to use it** (a heading):

      `Only when the start link in the approval email doesn't work. Read the key to the teacher over the phone. Don't email it or send it in a message.`
    - **How the teacher uses it** (a heading), as a numbered list:
      1. `Join the class with its Zoom link.`
      2. `Open Participants and choose Claim host.`
      3. `Type the host key.`
    - **A warn notice** titled `The waiting room can stop this`:

      `If this Zoom account keeps its waiting room on, the teacher waits there first. They can claim host only after someone already in the meeting lets them in. If nobody is in the meeting yet, the teacher can't get in this way. Instead, open the start link on the class's request page, start the class yourself, then let the teacher in and make them host.`
    - **Keep it safe** (a heading):

      `This key lets anyone take host control of every meeting on {label}, not just this class. If it may have spread, change the key in Zoom, then type the new one on this account's page.`

    The step "Open Participants and choose Claim host" is confirmed in the owner's live check (criterion 39, step 9).
43. **Masking everywhere else stays.** Across a reveal, with `DEBUG` logging captured for `apps.zoom` and `django`:
    - the plaintext key appears in the reveal page's HTML **only**. It never appears in any log record, any `messages` entry, `django.core.cache.cache`, any email, the `HostKeyReveal` table, or any other page (the change page before and after, the list, the request detail);
    - the service and view functions that hold it are `@sensitive_variables("plain")`. An `ExceptionReporter` test on an error raised after decryption inside the reveal shows the key masked.

    008 criteria 24 and 25 still pass for every page except this one. That exception is deliberate (D11).
44. **The change page shows who looked.**
    - When a key is saved and readable, the Host key section gains the button `Show host key`. It posts to `zoom:account_host_key` through its own separate form, the pattern 006 used for `Check connection` (no nested forms).
    - The button's help reads `For when a start link doesn't work. Every time the key is shown, it's recorded.`
    - When there's at least one reveal, the section shows `Last shown to {name} on {when}. Shown {n} time(s) in all.`
    - The button isn't shown for users without `zoom.change_hostaccount`, when no key is saved, or on the add page.
    - Rendering the change page decrypts nothing new beyond 008's `host_key_state`, and it doesn't show the key.
45. **008's "write-only" rule is amended deliberately** (D11). The `HostAccount` class docstring, 008 D3/D10 and the README's "A host key is **write-only**" paragraph become:

    `A host key is never shown back on the account's pages or in any list or email. An IT desk member can show it on its own page as a fallback, and every time it's shown is recorded.`

    The docstring change is the backend's. The README and 008 amendment notes are the docs writer's.
46. **Prod walkthrough addition** (to criterion 38). With a dummy key `123456` on a test account:
    - `Show host key` shows it;
    - `curl -I` on the POST shows `no-store` and `no-referrer`;
    - the change page then shows the reveal line;
    - a `view_hostaccount`-only user gets 403;
    - `docker compose logs web` contains the `shown to` line and not `123456`.

    Screenshot of the reveal page at 1440 and 400.

### Added with the Design (2026-09-26): the IT desk's phone number on the start page (P1; D14)

47. **`IT_DESK_PHONE` (owner's answer to P1: "A phone number setting").**
    - **Setting (`tmd-devops`):**
      - `config/settings/base.py` reads `IT_DESK_PHONE = env("IT_DESK_PHONE", default="")`. It's the only place it's read.
      - It's added to `.env.example`, with a comment and an example like `011 234 5678`, and to `compose.yaml`'s `web.environment` as `IT_DESK_PHONE: ${IT_DESK_PHONE:-}`. It isn't a secret.
      - A source scan finds no other read of it.
    - **Check** (backend, `zoom.E006`, untagged): a non-empty value that 005's `normalise_phone` can't read fails `manage.py check` with `IT_DESK_PHONE isn't a phone number the app can read. Use a form like 011 234 5678 or +94 11 234 5678.` An empty value is silent.
    - **Context** (backend): `services.it_desk_phone()` returns `None` when the setting is empty. Otherwise it returns `{"display": format_phone(e164), "tel": e164}`, reusing 005's `normalise_phone`/`format_phone` (the requester phone's rules), so there's one definition of how a number is read and shown. `StartClassView` passes it as `it_desk_phone` in every state.
    - **Copy (pinned).** One partial, `zoom/partials/it_desk_contact.html` (`with phone=it_desk_phone still=… only`), prints the contact sentence at the end of the four start-page messages (criteria 22, 23 and 26):

      | `still` | Setting set | Setting empty |
      |---|---|---|
      | false | `Phone the IT desk on <a href="tel:{tel}">{display}</a>.` | `Contact the IT desk.` |
      | true | `If it still doesn't work, phone the IT desk on <a href="tel:{tel}">{display}</a>.` | `If it still doesn't work, contact the IT desk.` |

      **Which form each message uses:**
      - "still": the invalid link (criterion 22) and the Zoom failure (criterion 23);
      - plain: the meeting gone (criterion 23) and `not_set_up` (criterion 26).
    - **The link:** it's a `tel:` link, a `.tap-link` (44px on phones), with the `href` in E.164 (`tel:+94112345678`) and the text as `format_phone` groups it. So `IT_DESK_PHONE=011 234 5678` shows `+94 11 234 5678`, the same way requester phones are shown on the detail page. Pages and emails other than the start page don't change.
    - **Tests:**
      - all four messages × set and empty, asserting the exact text and the `href`;
      - the E006 check with `abc` and with `""`;
      - the start page's context carries `it_desk_phone` in every state.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q1 and Q2 on 2026-09-26. The answers are recorded as D11 and D12. (There is no Q3 in briefs 011–014: the numbering jumped from Q2 in this brief to Q4 in 012 by mistake, and nothing was left out. The owner's list is complete.)

| Q | Question (short) | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| Q1 | What happens to the stored host keys now that they aren't emailed? | Stop using them, then remove the storage in a clean-up brief after the live check | **"Keep as IT-only fallback"**: kept encrypted, not emailed, and revealable in the app by the IT desk. There's no clean-up brief | D11 (criteria 30, 40–46) |
| Q2 | Can requesters cancel their own booking through a signed link? | No, IT cancels | **"No, IT cancels"** | D12 |

**Decisions (the planner's)**

- **D1: The split and order** are in Scope. 011 needs no new Zoom scope. The start link uses `GET /meetings/{id}` (`meeting:read:meeting:admin`), and cancelling uses `DELETE /meetings/{id}` (`meeting:delete:meeting:admin`); 006 already has both.
- **D2: Cancel locks first, calls Zoom inside the transaction, then commits** (the same shape as 006's D6, step 2–3).
  - **Why this order and not "Zoom first, then the database":** brief 013 will get a `meeting.deleted` webhook for every delete the app makes itself. With this order, the webhook handler (which locks the same request row) waits for the commit and then finds the database already matches Zoom, so it does nothing: no second email, no double cancel. Zoom-first would leave a window in which the webhook cancels the booking with the wrong source and sends its own email.
  - **What's held:** one `DELETE`, with 006's timeouts (5, 15), on one request, its account and its classes. It's the same bound 006 accepted for the create (R4 there).
  - **Failure handling:**
    - a certain Zoom failure rolls back;
    - an unclear one rolls back and says so, and repeating is safe, because a delete answered 3001 counts as done;
    - a failure after Zoom deleted leaves the booking in place. The next press finishes it, and 013's webhook would also finish it on its own.
  - **No "recover" call:** `PUT /meetings/{id}/status` `action=recover` exists (research), but it needs another scope and only helps in the rare case where saving fails after a delete. The repeat-press path covers that case with no new scope.
- **D3: The start link replaces the host key in email** (owner, answer 3).
  - The key stays encrypted in the database as an IT-only fallback (D11).
  - `approve()` no longer decrypts it, so an unreadable key can't block an approval any more.
- **D4: The start link's design** (owner, answer 3; the exact window was left to the planner).
  - **One link per booking, not per class.** The email carries one link. It opens the window of whichever class is current. A 60-class booking doesn't send 60 links, and a moved class (012) needs no new link, because the window is worked out from the stored class times at the moment of use.
  - **The window:** from 30 minutes before the class, or from the end of the account's previous class if that ends later, until the class ends.
    - **Why the "previous class" rule:** the plan is **Pro, one meeting at a time per host** (owner, answer 2). That matches the app's clash rule, one booked class at a time per account (005 D6). Back-to-back classes are allowed with no gap. If the next teacher starts the meeting early while the previous class is still running on the same Zoom user, Zoom can end or displace the running class. The window never opens while the account's previous booked class is still on.
    - **Why it closes at the class's end:** the link is for starting. A start after the end would run past the booking and could clash with the next one.
  - **The page shows, a POST acts** (the 005 D8 pattern for the confirm link).
    - Mail and link scanners (Safe Links and the like) fetch `GET` URLs, sometimes at click time, which would be inside the window.
    - A scanner that fetched a 302 to the `start_url` would receive a working host link on a third party's servers.
    - So `GET` shows a page with a `Start this class` button, and only the `POST` asks Zoom and redirects. The teacher makes one extra click.
  - **The token** is signed with its own salt. It carries the request pk and the meeting ID, so a booking that ever gets a new meeting (a future re-assign) kills old links. There's no expiry inside it: the window is the expiry.
    - **README note for the docs writer:** rotating `SECRET_KEY` invalidates every start link already emailed, unless the old key is kept in Django's `SECRET_KEY_FALLBACKS`.
  - **Headers:** `no-store` on every response keeps the page and the redirect out of caches. `no-referrer` stops the app's token URL from being sent to Zoom, or anywhere else, as a `Referer`.
  - **`start_url` checks:** it's never stored, logged or emailed, and it must be `https` on `zoom.us`, so a strange answer can't become an open redirect.
  - **What a leaked start link can do:** start *that booking's* classes as host, only inside a window, until the booking ends or is cancelled. The host key it replaces opened every meeting on the account, at any time, until IT changed it in Zoom.
    - The research also found that a `start_url` may sign the holder in as that Zoom user beyond the one meeting. This is unconfirmed, so it's tested in the owner's live check (criterion 39, step 5) and recorded as R2.
    - Revoking one link without cancelling is a follow-up. If needed, it's a version counter in the token.
  - **Logging only, no table** (owner: "log each use"). An `INFO` line per use, with the reference, the class and the IP.
- **D5: The requester gets the start link, as the approval email's recipient.** The requester is often the teacher. If not, they forward it, and the email says what the link can do. IT can copy it from the detail page (criterion 31), which also covers a lost or failed email.
- **D6: The app sends the only cancellation emails.**
  - Zoom's own notifications are off (`schedule_for_reminder=false`, `cancel_meeting_reminder=false`). Zoom only emails the host, alternative hosts and registrants anyway, and people with just the join link are never told (research, Meetings API). So the requester email is the notification.
  - **A whole booking is one `DELETE` of the meeting, even when some classes have happened.** The held classes are history in the app's database. Zoom refuses to delete a meeting in progress, and the app refuses first (criterion 6). One call keeps the lock short. Per-class deletes would be up to 60 calls under the lock.
  - **To confirm live:** whether deleting a meeting also removes the cloud recordings of classes that already happened (criterion 39, step 7). If it does, 014's recording emails will already have gone out for those classes by then. The README then warns IT to cancel only once the recordings have been emailed, or 012/013 can switch the whole-booking cancel to per-class deletes.
- **D7: The permission is reused, not added.** Cancelling (and 012's moving) is a decision on a request, made by the same IT desk that approves it. `zoom.review_linkrequest` already gates the request pages, and the IT desk group holds it (005 D2). A new permission would need a group migration and would split one job in two. Only its **name** changes (D8), because brief 010's role screen lists permission names.
- **D8: The permission is renamed by a data migration.** Django's `migrate` creates missing permissions but never renames existing ones. The new name mentions reschedule now, so 012 doesn't need a second rename. If 012 is dropped, the name is set back.
- **D9: A cancelled booking isn't reopened.** There's no "restore". Zoom's recover exists for 7 days, but restoring a booking means re-checking clashes as a new approval would, which is 012's machinery. IT approves a new request instead.
- **D11: The host key becomes an IT-only fallback you can reveal** (owner, Q1: "Keep as IT-only fallback"; this reverses the planner's recommendation).
  - **What stays:**
    - the key is stored encrypted (005 D17);
    - encryption-key rotation;
    - `zoom.E003`;
    - the account page's host-key field (008).
  - **What changes:** the key is emailed to nobody (criteria 27–29). An IT desk member (`zoom.change_hostaccount`, 008 D2) can reveal it through an explicit `Show host key` POST (criteria 40–46).
  - **Why a POST and a page of its own, not a toggle on the change page:**
    - A GET could be prefetched or cached.
    - Each reveal needs to be one clear, recorded act.
    - The key is kept off the page people use for editing. That page is often left open, screenshotted or shown on a shared screen.
  - **Why a table and not only the log:** the owner asked for every reveal to be logged with the user and time. IT can't read the server logs, so a `HostKeyReveal` row per reveal, summarised on the change page (criterion 44), is the in-app record. The log line is the second copy.
  - **Amends brief 008:** D3 ("no partial key hints… nothing shows a saved key"), D10 ("Host keys can't be read anywhere any more"), criterion 24's "every accounts page renders without the plaintext key" (now: every page except the reveal page), and the `HostAccount` docstring's "write-only". The docs writer adds dated "Amended by 011" notes. The backend changes the docstring (criterion 45).
  - **The known weakness, recorded as the owner accepted it (R7):** the fallback is only as good as the account's own meeting settings. With the waiting room on (owner: it "can stay on"), a teacher who joins with the join link waits in the waiting room. They can claim host only after someone already in the meeting admits them, and if nobody is there, they can't get in that way at all. The reveal page says so in plain words (criterion 42).
  - **Flag for the designer:** that guidance is pinned for its facts, not its polish. Rework the wording and layout through the main session, but keep all three facts: when to use it, the waiting-room limit, and that the key opens every meeting on the account. The better fallback it offers, "start the class for them from its request page", uses the `Start link` row (criterion 31).
- **D12: Requesters can't cancel through a link** (owner, Q2: "No, IT cancels"; the planner's recommendation). The requester replies to the approval email or phones the IT desk, and IT cancels (criteria 5–17). There's no public cancel page.
- **D13: The designer's contract gaps G1–G7 go into the contract as listed** (Design D.13; main session, 2026-09-26). They're pinned in the criteria and the contract below:
  - **G1:** `in_progress_id` drives the `In progress` tag (criterion 8).
  - **G2:** `cancel_blocked_message` says why there's no cancel link (criterion 8). It comes from criterion 6's model constants, so the text lives in one place.
  - **G3:** `checks_zoom` on the confirm page.
  - **G4:** the confirm page's `link_request` fields are listed.
  - **G5:** `can_start` on the cancellation email, and `start_url` `""` on the approval email for the manual provider (needed because P3 is accepted).
  - **G6:** `link_request` and `occurrence` are passed for `not_set_up`; `token` is passed in every valid-token state.
  - **G7:** `CancelForm`'s widget (criterion 7).
- **D14: The designer's copy proposals P1–P7 are accepted** (Design D.14).
  - **P1** was answered by the owner: "A phone number setting" (criterion 47).
    - **The name is `IT_DESK_PHONE`,** not the suggested `TMD_IT_DESK_PHONE`. `base.py`'s other site-wide values are unprefixed (`SITE_NAME`, `TRUSTED_PROXY_COUNT`), and the project needs no namespace in its own env file.
    - **When it's empty,** the sentence falls back to `Contact the IT desk.` with no number. A page with no phone number is still true and still usable. A placeholder number would be worse.
    - **It's checked at start-up** (`zoom.E006`), so a typo is caught by `manage.py check`, not by a teacher tapping a dead number.
  - **P2–P7** are accepted by the main session because they prevent user mistakes:
    - **P2:** the reveal-page guidance, in steps, with the action that actually gets the teacher in (criterion 42). "Claim host is under Participants" is confirmed live (criterion 39, step 9).
    - **P3:** no start-link wording when the manual provider sent none (criteria 17, 26 and 28).
    - **P4:** `Keep the booking` / `Keep the class` (criterion 7).
    - **P5:** the "please let your students know" line in the cancellation email (criterion 17).
    - **P6:** the shorter no-key notice (criterion 30).
    - **P7:** the "share the join link, keep the start link to yourself" line (criterion 28).
  - **Which text wins:** the Design section's wireframes and tables still show the pre-decision wording in places. Examples are `Keep it`, `… or phone the IT desk.` and the old approval-email block. **Where they differ, the criteria win.** The frontend builds from the criteria and this contract, and the designer can refresh their section's examples at any time.

    *Stale as of 2026-09-26 (docs writer): this note described the Design section before it was refreshed. The Design section below now carries the note "Refreshed 2026-09-26 after D13 and D14" and shows the pinned P1–P7 wording throughout, so the gap this note warns about no longer exists in the current text. Left here, unremoved, as the record of why the refresh happened.*
- **D10: Information architecture** (`ux-strategy:information-architecture`). The screens are organised around what IT does. There's no new sidebar item.

  ```
  [Zoom links]
  ├── Link requests          zoom:queue          ← new tab: Cancelled
  │   └── ZL-0042 …          zoom:detail         ← Start link row; Cancel this booking; per-class Cancel this class; Cancelled markers
  │       ├── Cancel this booking        zoom:cancel         (confirm page → back to detail with a message)
  │       └── Cancel this class          zoom:cancel_class   (confirm page → back to detail with a message)
  ├── Timetable              (cancelled classes disappear; unchanged screens)
  └── Zoom accounts          zoom:accounts
      └── Change Zoom 02     zoom:account_edit   ← Host key section: [Show host key] + "Last shown to … on …"
          └── Host key       POST zoom:account_host_key → the reveal page (no-store), Back to Change Zoom 02

  [Public frame, no sign-in]
  └── Start this class       zoom:start (token)  ← from the approval email
  ```

  - **Labels are verbs:** `Cancel this booking`, `Cancel this class`, `Start this class`.
  - **Wayfinding:** each confirm page has the breadcrumb Home › Zoom link requests › ZL-0042 › Cancel, a `Keep the booking` or `Keep the class` link back to the detail (P4), and returns to the detail on success.

**Risk register** (`delivery-execution:risk-register`)

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | A cancel deletes in Zoom but the save fails, so the class looks booked but has no meeting | Low / Medium | Mitigate: the repeat press finishes it (3001 = done), the pinned message says so, and 013's webhook heals it | the ERROR log line in criterion 14 | backend |
| R2 | A leaked start link, or a `start_url` that signs the holder in as the Zoom user beyond the meeting (unconfirmed) | Low / **High** | Mitigate: a window per class, POST-only, no-store and no-referrer, an https-on-zoom.us check, logged uses, nothing stored. Confirm the second part in the owner's live check (step 5). If it's confirmed, the README warns that the link must be kept private, and a follow-up adds per-link revocation | the owner's step 5 result | backend, owner |

*Amended by 011 review round 1, nit (2026-09-26): a `start_url`'s `zak` query parameter is Zoom's own token, and it can stay valid for a while after it's issued — not only for the single fetch that produced it — which widens R2's window a little further than "only inside the app's own 30-minute class window" suggests; step 5 below now asks the owner to probe how long. Separately, if `ADMINS` is ever set, Django's 500-error email body (built by `ExceptionReporter` from the request and the view's local variables) can carry a working start link, because `config/log_filters.py`'s redaction covers only the log line, not that email's body — see the caveat next to `mail_admins` in `config/settings/base.py`. `ADMINS` is unset today, so this is inert, but it's a reason not to set it without revisiting the redaction first.*
| R3 | The next teacher starts early and displaces a running class on the same Zoom user (Pro allows one meeting at a time) | Medium / **High** without D4's rule | Avoid: the window never opens before the account's previous class ends (criterion 20) | a teacher reports being cut off | backend |
| R4 | Deleting a whole meeting removes the cloud recordings of held classes | Unknown / Medium | Confirm live (step 7). If true, the README advises cancelling only after the recordings are emailed | the owner's step 7 result | owner, docs |
| R5 | The approval email is forwarded widely, and anyone can start the classes | Medium / Medium | Accept, and mitigate by the window and the email wording. It's still far narrower than the host key (D4) | IT hears of an unexpected host | owner |
| R6 | Rotating `SECRET_KEY` breaks every emailed start link | Low / Medium | Mitigate: the README documents `SECRET_KEY_FALLBACKS` | a rotation | docs |
| R7 | The host-key fallback doesn't get the teacher in: the waiting room holds them until someone already in the meeting admits them (D11) | Medium / Medium | Accepted by the owner (Q1). Mitigate: the reveal page says so and points to starting the class from its request page (criterion 42) | a teacher reports being stuck in the waiting room | owner, IT desk |
| R8 | A revealed key spreads (it opens every meeting on the account, at any time) | Low / **High** | Mitigate: IT desk only, POST, `no-store`, a recorded reveal each time (who and when, shown on the change page), phone-only guidance, masking everywhere else (criteria 40–44). Recovery: change it in Zoom and re-type it (README) | an unexpected reveal line on the change page | owner, IT desk |

## MVT plan
<!-- owner: tmd-planner -->

### Models

In `apps/zoom/models.py`. Migrations: `0006_cancel_and_start` (schema) and `0007_review_permission_name` (data, reversible).

- **`LinkRequest`**
  - `Status.CANCELLED`, plus `cancelled_at` and `cancelled_by` (criterion 1). A new check constraint.
  - Methods: `class_in_progress(now)`, `cancellable_classes(now)`, `can_cancel_booking(now)`, `status_after_cancel(now)` (criterion 3), `start_state(now)` (criterion 21).
  - The class docstring's state line becomes: `unverified → waiting → approved | rejected; approved → cancelled`.
- **`Occurrence`**
  - `cancelled_at`, `cancelled_by` and `cancel_reason`, with a check constraint.
  - `can_be_cancelled(now)`, `start_window()`, and the `START_WINDOW_MINUTES = 30` class constant.
  - `start_window()` makes one query: the latest booked class on the same account ending in `(starts_at − 30 min, starts_at]`.
- **`HostKeyReveal`** (criterion 40), in `0006`. The `HostAccount` docstring's "write-only" wording changes (criterion 45).
- **`HostAccount.last_key_reveal()`** returns the latest `HostKeyReveal` with `shown_by`, or `None`. **`key_reveal_count()`** returns the count. Both are for criterion 44; the change view reads them once each.
- **`BOOKED`** gains `cancelled_at__isnull=True`. Everything built on `booked()` follows.
- **`LinkRequestQuerySet`:** `tab_counts()` and `for_tab()` gain `cancelled`. `QUEUE_TABS` gains `("cancelled", "Cancelled")` before `all`.
- **Copy constants** for criteria 6, 7 and 33 live beside the rules that raise them, as today.

**State machine** (`interaction-design:state-machine`). The request:

| From | Event | Guard | To | Actions |
|---|---|---|---|---|
| `approved` | cancel booking | `can_cancel_booking` | `cancelled` | cancel every not-started class, free their slots, one Zoom `DELETE`, email |
| `approved` | cancel class | `can_be_cancelled` | `approved`, or `cancelled` when `status_after_cancel` says so | cancel that class, free its slots, `DELETE ?occurrence_id=`, email |
| `approved` | a Zoom failure | none | `approved` (unchanged) | roll back, show the message |
| `cancelled` | anything | none | `cancelled` (terminal) | none |

- **Class states:** `booked` → `held` (by time alone) or `cancelled`.
- **Impossible states, prevented by constraints or guards:**
  - a cancelled class holding slots;
  - a cancelled request with no link;
  - a cancelled class that had started;
  - a cancelled class with no reason.

**Provider** (`apps/zoom/providers.py`):

| Member | Fake | Manual | Zoom |
|---|---|---|---|
| `can_start` | True | False | True |
| `start_url(*, host_account, meeting_id) -> str` | `https://zoom.example.invalid/s/{id}`; `start_error` steerable; records `start_calls` | not called | `GET /meetings/{id}`, then check `https` on `zoom.us` (criterion 18) |
| `occurrence_id_for(*, host_account, meeting_id, starts_at) -> str \| None` | returns `None` | not called | `GET /meetings/{id}`, then match `occurrences[].start_time` to `starts_at` |
| `delete_meeting(...)` | unchanged (records) | no-op | adds `cancel_meeting_reminder=false` (criterion 11) |

**Services** (`apps/zoom/services.py`):

- `cancel(link_request_id, *, occurrence_id=None, by, reason, provider=None) -> CancelResult(outcome, message, link_request, cancelled: list[Occurrence], remaining: list[Occurrence])`. It follows criterion 10's order, with a deadlock retry once, and its messages are criteria 12–15.
- `start_token(link_request) -> str`, `link_request_from_start_token(token) -> LinkRequest | None`.
- `start_class(link_request, *, provider=None) -> StartResult(state, occurrence, url | None, message | None)`. The `url` lives only in memory and is returned only to the view.
- `send_cancelled_email(request, link_request, cancelled, remaining, reason) -> bool`.
- `send_approved_email(request, link_request) -> bool`, with no `host_key` argument. It builds the start URL when `can_start`.
- `approve()` stops decrypting the host key (criterion 27).
- `reveal_host_key(account, *, by) -> str` is `@sensitive_variables("plain")`. It decrypts, writes the `HostKeyReveal` row and the `INFO` line, and returns the key to the view only. It raises `HostKeyUnreadable` or a "none saved" error for criterion 41's redirects. It's the one place a key is ever decrypted for showing.

- `it_desk_phone() -> dict | None` (criterion 47). It reuses `validators.normalise_phone` and `format_phone`.

**Checks:** `zoom.E006` for an unreadable `IT_DESK_PHONE` (criterion 47), registered in `ZoomConfig.ready()` like the others.

**Forms:** `CancelForm(reason)`, with the G7 widget, label and help set on the form (criterion 7). `ApproveForm` loses nothing but its template help.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `zoom:detail` (changed context) | as today | `LinkRequestDetailView` | `zoom/detail.html` | `zoom.review_linkrequest` |
| `zoom:queue` (new tab) | as today | `QueueView` | `zoom/queue.html` | `zoom.review_linkrequest` |
| **`zoom:cancel`** | `zoom/requests/<int:pk>/cancel/` | `CancelBookingView(ReviewerRequiredMixin, SingleObjectMixin, FormView)`, `non_atomic_requests`. GET shows the confirm page; POST calls `services.cancel()` | `zoom/cancel_confirm.html` | `zoom.review_linkrequest` |
| **`zoom:cancel_class`** | `zoom/requests/<int:pk>/classes/<int:occurrence_pk>/cancel/` | `CancelClassView`, a subclass of the above with the class resolved from the path | `zoom/cancel_confirm.html` | `zoom.review_linkrequest` |
| **`zoom:account_host_key`** | `zoom/accounts/<int:pk>/host-key/` | `HostKeyRevealView(SignedInPermissionMixin, SingleObjectMixin, View)`, POST only, `never_cache`, `Referrer-Policy: no-referrer`, and `sensitive_variables` on the frame holding the key. It calls `services.reveal_host_key()`, then renders the page or redirects | `zoom/host_key_reveal.html` | `zoom.change_hostaccount` |
| `zoom:account_edit` (changed context) | as today | `HostAccountUpdateView` | `zoom/account_form.html` | `zoom.change_hostaccount` |
| **`zoom:start`** | `zoom/start/<str:token>/` | `StartClassView(TemplateView)`, public, `non_atomic_requests`, with the headers added in `dispatch`. POST calls `services.start_class()` | `zoom/start.html` (extends `public_base.html`) | none (signed token) |

The paths are for orientation only; code and templates use the names.

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**`zoom/detail.html`** keeps every existing variable. Changed or added:

| Variable | Type | Notes |
|---|---|---|
| `link_request` | LinkRequest | Now also `cancelled_at`, `cancelled_by`, and `status` `"cancelled"` |
| `occurrences` | list of Occurrence | Each also has `cancelled_at`, `cancelled_by` and `cancel_reason` |
| `can_cancel_booking` | bool | `link_request.can_cancel_booking()`. Always false unless approved |
| `cancellable_ids` | set of int | Occurrence pks with `can_be_cancelled()`, **only for weekly** bookings (empty for one-off) |
| `start_link` | str or `None` | Absolute URL. Set when approved and the provider `can_start`; `None` when cancelled or waiting |
| `in_progress_id` | int or `None` | **G1:** the pk of `link_request.class_in_progress()`, for the `In progress` tag in the Classes list |
| `cancel_blocked_message` | str or `None` | **G2:** when the request is `approved` and not `can_cancel_booking`, criterion 6's whole-booking message (from the model constants); otherwise `None` |
| `approve_form` | unchanged | Its radios no longer carry host-key words (criterion 29) |

The `Booked on`, `Zoom link` and `Meeting ID` rows show for both `approved` and `cancelled`.

**`zoom/queue.html`:** `tabs` gains the `cancelled` entry. Rows of cancelled requests use the status tag.

**`zoom/cancel_confirm.html`** (new, in the shell):

| Variable | Type | Notes |
|---|---|---|
| `link_request` | LinkRequest | **G4:** reads `reference`, `class_name`, `requester_name`, `requester_email` and `host_account.label` |
| `checks_zoom` | bool | **G3:** false for the manual provider. It drives the lead, the `Delete it in Zoom too` notice and the busy text (`Removing it from Zoom…` / `Cancelling…`) |
| `occurrence` | Occurrence or `None` | Set for a one-class cancel. It also picks the safe link's label: `Keep the class` when set, `Keep the booking` otherwise (P4). The form posts to `zoom:cancel_class link_request.pk occurrence.pk`, otherwise to `zoom:cancel link_request.pk` |
| `to_cancel` | list of Occurrence | Soonest first |
| `kept` | list of Occurrence | Held or in-progress classes that stay (whole cancel only). May be empty |
| `form` | CancelForm | `reason` |
| `cancel_error` | str or `None` | Criteria 12–14's message, in its final form |

**`zoom/start.html`** (new, public frame):

| Variable | Type | Notes |
|---|---|---|
| `state` | str | `"ready"`, `"too_early"`, `"ended"`, `"cancelled"`, `"invalid"` or `"not_set_up"` |
| `link_request` | LinkRequest or `None` | `None` only when `invalid`. **G6:** passed in every other state, `not_set_up` included. The template reads only `class_name` and `reference` |
| `occurrence` | Occurrence or `None` | The class in question (criterion 21). **G6:** also passed for `not_set_up`, where one exists, so the class facts show |
| `opens_at` | aware datetime or `None` | For `too_early` |
| `opens_after_other_class` | bool | True when `opens_at` is later than `starts_at − 30 min` (criterion 22's second sentence) |
| `start_error` | str or `None` | Criterion 23's messages, **without** the contact sentence, which the template adds (criterion 47) |
| `start_error_still` | bool | Which contact form follows `start_error`: true for the Zoom failure, false for the meeting gone |
| `token` | str or `None` | **G6:** passed in every valid-token state (`ready` for the form's action, `too_early` for the `Check again` link, both `{% url 'zoom:start' token %}`); `None` only when `invalid` |
| `it_desk_phone` | dict or `None` | Criterion 47: `{"display": "+94 11 234 5678", "tel": "+94112345678"}`, or `None` when `IT_DESK_PHONE` is empty. Passed in every state, and given to `zoom/partials/it_desk_contact.html` with `phone=it_desk_phone still=… only` |

The fixed texts for `invalid` and `not_set_up` (criteria 22 and 26) are the template's. It follows each with the contact partial: `still=True` for `invalid`, `still=False` for `not_set_up`.

**`zoom/account_form.html`** (change page) keeps every 006/008 variable, and adds:

| Variable | Type | Notes |
|---|---|---|
| `can_reveal_host_key` | bool | True on the change page when the user has `zoom.change_hostaccount` and the **stored** `host_key_state` is `saved` or `saved_legacy`. Always false on the add page. The separate form posts to `{% url 'zoom:account_host_key' account.pk %}` |
| `last_key_reveal` | `HostKeyReveal` or `None` | `shown_by` and `shown_at`, for `Last shown to {name} on {when}` |
| `key_reveal_count` | int | `0` when there are none |

**`zoom/host_key_reveal.html`** (new, in the shell; the only template that ever receives a plaintext host key):

| Variable | Type | Notes |
|---|---|---|
| `account` | HostAccount | `label` and `pk` (for the breadcrumb and `Back to Change {label}` → `zoom:account_edit`) |
| `host_key` | str | The plaintext key. Printed once, and never passed to any include except with `only` and this one value |

**Emails:**

- `cancelled_subject.txt` / `cancelled_body.txt`: `link_request`, `cancelled` (list of Occurrence), `remaining` (list of Occurrence), `reason` (str), `request_url` (str), and **`can_start`** (bool, **G5**: picks `with the same link and start link.` or `with the same link.`, P3).
- `approved_body.txt`: `link_request`, `occurrences`, `start_url` (str). **G5:** `start_url` is `""` for the manual provider; the template then leaves out the start block, P7's line and the forwarding sentence (P3). There's no `host_key`.

**Formatting:** the `zoom_format` filters for every date and time.

### Placement and reuse

- **All in `apps/zoom`**, since the models belong there. No new app.
- **Reused:**
  - the 005/006 lock order and deadlock retry, and the `Outcome` shape;
  - the 006 error kinds with `lasting` and `maybe_done`;
  - `delete_meeting` and `zoom_occurrence_id`;
  - `ReviewContextMixin`, `SignedInPermissionMixin`, `public_base.html`;
  - `partials/error_summary.html`, `partials/field.html`, the status-tag and occurrence-list partials, the busy button;
  - `services._send`, `services.client_ip`;
  - `django.core.signing` and the 005 D8 GET-shows/POST-acts pattern;
  - Django's `never_cache`, which gives `no-store`.
- **New components** (designed in the Design section, D.0; each has its one definition in `docs/design/`, written by the designer):

  | Component | Class / partial | Doc | Used on |
  |---|---|---|---|
  | Danger button | `.button--danger` | `docs/design/danger-button.md` | the cancel confirm page's final button only |
  | Class rows | `.classrows`, `zoom/partials/class_rows.html` | `docs/design/class-rows.md` | the detail's Classes list: per-class actions, the `In progress` tag, the `Cancelled` tag with who, when and why |
  | Secret value | `.secret` | `docs/design/secret-value.md` | the host-key reveal page |

  Other new partials: `zoom/partials/start_heading.html` (the designer's) and `zoom/partials/it_desk_contact.html` (criterion 47).
- **New tokens** (`static/css/style.css`; tokens live only in `:root`, and colour literals only in the first palette block):
  - `--red-800`, a new palette red, in the first `:root` palette block;
  - `--c-danger`, `--c-danger-hover` and `--c-on-danger`, semantic colours built on the palette, in section 1c;
  - `--font-mono`, the monospace font stack, and `--fs-secret`, the secret value's size in `rem`, in section 1b.

  The contrast figures are the designer's (danger button about 6.6:1; secret value about 12:1 light and 8.5:1 dark). The verifier confirms them at criterion 35's widths and modes.
- **New setting:** `IT_DESK_PHONE` (criterion 47), read only in `base.py`, and listed in `.env.example` and `compose.yaml`.
- **Also reused for the host-key reveal:** 008's `host_key_state`, `get_host_key()`, `HostKeyUnreadable` and its copy; 006's separate-form pattern from `Check connection`.
- **Not built:** a start-link table, token revocation, requester self-cancel, restore, re-assign, a host-key clean-up brief (dropped by the owner's Q1 answer).

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Main session, before anything:**
   - **Done (2026-09-26):** the owner answered Q1 and Q2 (D11 and D12). Criteria 30 and 40–46 reflect Q1.
   - **Tell 006's verifier and docs writer** that the research (2026-09-26, https://developers.zoom.us/docs/integrations/oauth-scopes-granular/ and https://developers.zoom.us/docs/api/meetings/) confirms both of 006's unconfirmed facts:
     - the five granular scope names in 006's D13 and criterion 38;
     - Zoom's cap of 60 occurrences per recurring series.

     006's owner-live-check steps 8 and 9 can be recorded as confirmed by documentation. `tmd-docs-writer` marks the README's scopes and the 60-class cap as confirmed, citing those URLs. 006 still needs the owner's live steps 1–7.
1. **Done (2026-09-26): `tmd-ui-designer`.** The Design section is written. Its contract gaps G1–G7 and copy proposals P1–P7 are folded in as D13 and D14 (criteria 7, 8, 17, 22, 23, 26, 28, 30, 35, 37, 39, 42 and the new 47), and the contract below is now fixed. The owner answered P1 ("A phone number setting").
2. **`tmd-devops`, alone and first** (the new env var, criterion 47's setting part):
   - `IT_DESK_PHONE` read in `config/settings/base.py` (default `""`, with a comment);
   - `.env.example`, with a comment and an example;
   - `compose.yaml`'s `web.environment` gains `IT_DESK_PHONE: ${IT_DESK_PHONE:-}`;
   - a settings test in `apps/core/` (it's read only in `base.py`, and the compose and `.env.example` entries exist).

   Devops runs `pytest` for its own tests, **without `--create-db`**, then `ruff` and `docker compose config --quiet` for both stacks. It finishes before step 3 starts. It doesn't write the `zoom.E006` check or the view context: those are the backend's.
3. **In parallel, after step 2:**
   - **3a. `tmd-django-backend`:**
     - models, migrations `0006` and `0007`;
     - providers, services (including `it_desk_phone()`) and forms (including G7's `CancelForm` widget);
     - the `zoom.E006` check;
     - views and URLs, with every G1–G6 context variable and `it_desk_phone` / `start_error_still` on the start page;
     - the email text files' context (`can_start` on the cancellation email, `start_url` `""` for manual);
     - `HostKeyReveal`, `services.reveal_host_key()`, `HostKeyRevealView`, and the `HostAccount` docstring amendment;
     - every test for criteria 1–34, 36, 40–45 and 47 (the check, context and copy parts), including the thread tests and the ordered-log test.

     **Only the backend runs `pytest --create-db`** (it adds `0006` and `0007`). When it has finished, it reports "backend pytest run finished".
   - **3b. `tmd-frontend`:**
     - `cancel_confirm.html`, `start.html`, `host_key_reveal.html`;
     - the new partials `class_rows.html`, `start_heading.html` and `it_desk_contact.html`;
     - the `account_form.html` reveal button, reveal line and P6 notice;
     - the `detail.html` and `queue.html` changes, and the status tag;
     - the email templates' layout, with P3, P5 and P7;
     - the three new components (`.button--danger`, `.classrows`, `.secret`) and the new tokens (`--red-800`, `--c-danger`, `--c-danger-hover`, `--c-on-danger`, `--font-mono`, `--fs-secret`) in `static/css/style.css` (criterion 35).

     It never uses `--create-db`. It runs `pytest` (reusing the database) only after the main session passes on the backend's signal. Until then, it limits itself to `ruff`, `node --check` and its own template checks.
4. **`tmd-test-verifier`:** criteria 1–38, 40–46 and 47 (with the thread tests run 3 extra times). That includes the `check --deploy` runs (criterion 37) and the prod walkthrough (criteria 38 and 46). It's the next agent to run `pytest --create-db`, and only after both 3a and 3b have finished. The main session then hands the owner criterion 39's steps, including step 9's Claim-host check and step 10's phone-link check. The brief stays `Verifying` until the owner reports.
5. **`tmd-code-reviewer`** (read-only). Focus:
   - lock order and the Zoom call inside the transaction (D2);
   - that every cancel message is honest about what's in Zoom;
   - the start view: no `start_url` anywhere, headers on every path, the https-on-zoom.us check, no Zoom call on GET, CSRF;
   - the window rule (D4);
   - thin views;
   - that the host key is gone from every email path;
   - the reveal: permission, POST only, `no-store`, one record per reveal, and the key present in the reveal page's HTML and nowhere else (criterion 43);
   - `IT_DESK_PHONE`: read only in `base.py`, and one definition of phone reading and showing (criterion 47);
   - the new tokens: colour literals only in the first `:root` palette block.
6. **`tmd-docs-writer`:**
   - **README:** cancelling; the start link and its window; the Pro one-meeting rule; `SECRET_KEY_FALLBACKS`; the gate still 006 + 011; `IT_DESK_PHONE` in the env-var table and in setup.
   - **README host-key section:** the key is no longer emailed; the `Show host key` fallback, who can use it and that each use is recorded; the waiting-room limit (D11); and criterion 45's text replacing the "write-only" paragraph.
   - **008 amendment notes:** dated "Amended by 011" notes next to 008's D3, D10 and criterion 24 (D11).
   - **CLAUDE.md:** the `zoom` bullet mentions `cancel()` and the start link.
   - **`docs/CHANGELOG.md`**.
   - Dated "Amended by 011" notes next to 005 criteria 46/61/64, D17 and 008 criteria 17/25.
   - Closes the brief.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

This is built inside the approved f-desk direction. It builds on the component notes in `docs/design/` (`public-frame`, `busy-button`, `status-tabs`, `form-section`, `availability-list`, `flash-messages`, `month-calendar`) and on 006's Design section.

- Every **pinned** string in the criteria is used exactly as written.
- Wording marked *design copy* is new in this section.
- **Refreshed 2026-09-26 after D13 and D14.** The gaps G1–G7 are now in the context contract, and the proposals P1–P7 are pinned in criteria 7, 8, 17, 26, 28, 30, 42 and 47. Every wireframe, table and email layout below now shows the pinned text. If anything here still differs from the criteria, the criteria win.

**Summary of what changes:**

| Kind | What |
|---|---|
| New component | **Danger button** `.button--danger` (`docs/design/danger-button.md`), answering criterion 35. It's used only for the final button on the cancel confirm page |
| New component | **Class rows** `.classrows` (`docs/design/class-rows.md`): the detail page's Classes list with a per-class action, an `In progress` tag and a `Cancelled` tag with who, when and why |
| New component | **Secret value** `.secret` (`docs/design/secret-value.md`): the host key, large and monospaced, on the reveal page |
| New partials | `zoom/partials/class_rows.html` (D.1.4), `zoom/partials/start_heading.html` (D.5.1: the start page's h1 words, printed twice as the confirm page does with `confirm_heading.html`), and `zoom/partials/it_desk_contact.html` (D.5.3: criterion 47's contact sentence) |
| New templates | `zoom/cancel_confirm.html` (D.2), `zoom/start.html` (D.5), `zoom/host_key_reveal.html` (D.7), `zoom/email/cancelled_subject.txt` and `cancelled_body.txt` (D.8) |
| Changed | `zoom/detail.html` (D.1), `zoom/queue.html` (D.3), `zoom/partials/status_tag.html` (D.3.1), `zoom/account_form.html` (D.6), `zoom/email/approved_body.txt` (D.8) |
| Unchanged | the timetable month and day pages (D.4), `occurrence_list.html` (still used on the confirm pages) |
| Icons | **none new.** `slash`, `clock`, `video`, `key`, `info`, `alert-triangle`, `alert-octagon` and `check-circle` are all in the sprite already |
| Tokens | `--red-800` (palette), `--c-danger`, `--c-danger-hover`, `--c-on-danger`, `--font-mono`, `--fs-secret` |

### D.1 Request detail: `zoom/detail.html`

#### D.1.1 Page structure

- **Waiting request:** unchanged from 006: `approve_error` → Request → Classes → Which accounts are free → Also waiting → Approve → Reject. The Classes box now renders through `class_rows.html`. For a waiting request that's the date only, so it reads as before.
- **Approved request** (IT users only; a plain user never gets here):
  1. the decided line (`notice--ok`, unchanged);
  2. **Request** (gains the `Start link` row);
  3. **Classes** (gains per-class actions and markers);
  4. **Cancel this booking** (new box), or the notice explaining why it can't be cancelled now, or nothing (D.1.5).
- **Cancelled request:**
  1. the cancelled line (`notice--note`, D.1.2), replacing the approved line;
  2. Request (the record rows);
  3. Classes (with markers).

  There are no actions.

Why the cancel box goes last: for an approved request it's the only action on the page. Putting it after the Classes list also puts it after the per-class actions, so IT sees "cancel one class" before "cancel everything". It mirrors `Reject this request` on a waiting request.

#### D.1.2 The decided line

| Status | Notice | Icon | Text |
|---|---|---|---|
| `approved` | `notice--ok` | `check-circle` | unchanged: `This request was approved by {decided_by} on {when}.` |
| `cancelled` | `notice--note` | `info` | pinned `This booking was cancelled by {cancelled_by} on {when}.`, then *design copy* ` It was approved by {decided_by} on {when}.` Both times use `zoom/partials/when.html` |

`note`, not `warn` or `bad`: a cancelled booking is a finished record, and nothing on the page needs fixing. The status tag in the Request box says `Cancelled` (D.3.1).

#### D.1.3 The Request box: new and changed rows

These go in the first `dl.facts` of the Request box, inside the existing `{% if %}` on status. It becomes `approved` **or** `cancelled`:

| Row (`dt`) | Approved | Cancelled |
|---|---|---|
| `Booked on` | unchanged (label, email, `See it on the timetable` when `timetable_url`) | label and email. There's no timetable link, because the classes aren't on it (`timetable_url` is `None`) |
| `Zoom link` | unchanged (`a.tap-link`) | **plain text, not a link** (`span.break-anywhere`), then `<br><span class="text-muted">For the record only.</span>` (*design copy*). A dead meeting link shouldn't look clickable |
| `Meeting ID` | unchanged | unchanged |
| `Passcode` | unchanged | **not shown.** Criterion 8 keeps only the three record rows, and a passcode for a deleted meeting is noise |
| **`Start link`** (new, criterion 31) | when `start_link`: `<a class="tap-link break-anywhere" href="{{ start_link }}">{{ start_link }}</a>`, then `<br><span class="text-muted">Send this to the teacher if the approval email went missing. It works from 30 minutes before each class until it ends.</span>` (pinned) | not shown (`start_link` is `None`) |

- It's a real link: opening it is safe (the GET never calls Zoom), and it's how IT "starts the class for them" (D.7, the fallback).
- The URL wraps anywhere, so a long token never pushes the page sideways at 320px.

#### D.1.4 The Classes box: `zoom/partials/class_rows.html`

Replace the `occurrence_list` include on this page with:

```django
{% include "zoom/partials/class_rows.html" with occurrences=occurrences cancellable_ids=cancellable_ids in_progress_id=in_progress_id link_request_pk=link_request.pk only %}
```

The anatomy, values and states are in `docs/design/class-rows.md`.

- **Cancellable class** (weekly only, since `cancellable_ids` is empty for a one-off): the link `Cancel this class`, followed by visually hidden ` on {starts_at|class_date}`, so that 60 links in a screen reader's link list each say which class they cancel (criterion 8).
- **Cancelled class:** a muted date, the tag `Cancelled` (`tag--plain`, `slash`), and on the next line `Cancelled by {cancelled_by} on {when}: {cancel_reason|linebreaksbr}` (pinned).
- **In progress** (`pk == in_progress_id`, G1): the tag `In progress` (`tag--note`, `clock`), pinned by criterion 8.
- **Held classes:** the date only.

The box heading `Classes ({occurrence_count})` is unchanged.

#### D.1.5 The Cancel box

It's shown only when the status is `approved`:

| Condition | What renders |
|---|---|
| `can_cancel_booking` | `section.box` with `aria-labelledby="cancel-title"`, `h2.box__title#cancel-title` `Cancel this booking`, and `.box__body` holding a `p.box__lead` (below) and `a.button.button--secondary` → `{% url 'zoom:cancel' link_request.pk %}` `Cancel this booking` |
| not `can_cancel_booking`, and `cancel_blocked_message` is set (G2, criterion 8) | `div.notice.notice--note` with `info` and `p` `{{ cancel_blocked_message }}` (criterion 6's whole-booking text, e.g. `Mon 5 Oct 2026, 8:30 am to 11:30 am is in progress. Cancel the rest of this booking after it ends at 11:30 am.`) |
| otherwise | nothing |

**Lead text** (*design copy*):

| Case | `p.box__lead` |
|---|---|
| weekly, `checks_zoom` | `Cancels every class that hasn't started yet, removes them from Zoom and emails the requester. To cancel just one class, use Cancel this class in the list above.` |
| one-off, `checks_zoom` | `Cancels the class, removes it from Zoom and emails the requester.` |
| weekly, manual | `Cancels every class that hasn't started yet and emails the requester. To cancel just one class, use Cancel this class in the list above.` |
| one-off, manual | `Cancels the class and emails the requester.` |

A one-off is `not cancellable_ids`; only weekly bookings fill it.

The entry link is `button--secondary`, **not** `button--danger`. It only opens the confirm page, and red is kept for the final act (`danger-button.md`).

#### D.1.6 Wireframes

**Desktop (1440, weekly, approved, one class cancelled, `zoom` provider):**

```
ZL-0042: Grade 11 Physics                               Home › Zoom link requests › ZL-0042
┌ ✓ Cancelled the class on Wed 7 Oct 2026. We emailed nimal@… ──────────────────── (x) ┐  flash (after the redirect)
┌ ✓ This request was approved by Anjali on Mon 28 Sep 2026, 9:40 am. ──────────────────┐  notice--ok
┌ Request ─────────────────────────────────────────────────────────────────────────────┐
│ Status     [✓ Link sent] [● Recording]         Name       Nimal Perera               │
│ Class      Grade 11 Physics                    Email      nimal@polymath.edu.lk      │
│ When       Every Mon and Wed, 5–28 Oct 2026…   Phone      077 123 4567               │
│ Recording  Yes, to the Zoom cloud              Sent       …                          │
│ Notes      None                                Confirmed  …                          │
│ Booked on  Zoom 02 zoom02@…                                                          │
│            See it on the timetable                                                   │
│ Zoom link  https://us02web.zoom.us/j/81234567890?pwd=…                               │
│ Meeting ID 81234567890                                                               │
│ Passcode   482913                                                                    │
│ Start link https://tmd.polymath.edu.lk/zoom/start/eyJyIjo0Mi…  (wraps)               │
│            Send this to the teacher if the approval email went missing. It works     │
│            from 30 minutes before each class until it ends.                          │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌ Classes (8) ─────────────────────────────────────────────────────────────────────────┐
│ 1. Mon 5 Oct 2026, 8:30 am to 11:30 am   Cancel this class │ 5. Mon 19 Oct 2026 … Cancel this class │
│ 2. Wed 7 Oct 2026, 8:30 am to 11:30 am  [⊘ Cancelled]      │ 6. Wed 21 Oct 2026 … Cancel this class │
│    Cancelled by Anjali on Mon 28 Sep 2026, 10:04 am:       │ 7. …                                   │
│    The school is closed for the sports meet.               │ 8. …                                   │
│ 3. Mon 12 Oct 2026, 8:30 am to 11:30 am  Cancel this class │                                        │
│ 4. Wed 14 Oct 2026, 8:30 am to 11:30 am  Cancel this class │                                        │
└──────────────────────────────────────────────────────────────────────────────────────┘  two columns ≥1400px only
┌ Cancel this booking ─────────────────────────────────────────────────────────────────┐
│ Cancels every class that hasn't started yet, removes them from Zoom and emails the   │
│ requester. To cancel just one class, use Cancel this class in the list above.        │
│ [ Cancel this booking ]                                                              │  button--secondary (a link)
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400, same booking):**

```
┌──────────────────────────────────────┐
│ ZL-0042: Grade 11 Physics            │
│ Home › Zoom link requests › ZL-0042  │
│ ┌ ✓ This request was approved by … ┐ │
│ ┌ Request ─────────────────────────┐ │
│ │ …                                │ │
│ │ Start link                       │ │  facts stack below 600px
│ │ https://tmd.polymath.edu.lk/zoom │ │  wraps anywhere
│ │ /start/eyJyIjo0MiwibSI6IjgxMjM0N │ │
│ │ …                                │ │
│ │ Send this to the teacher if the  │ │
│ │ approval email went missing. …   │ │
│ └──────────────────────────────────┘ │
│ ┌ Classes (8) ─────────────────────┐ │
│ │ 1. Mon 5 Oct 2026, 8:30 am to    │ │
│ │    11:30 am                      │ │
│ │    Cancel this class             │ │  44px link, wraps under the date
│ │ 2. Wed 7 Oct 2026, 8:30 am to    │ │
│ │    11:30 am  [⊘ Cancelled]       │ │
│ │    Cancelled by Anjali on Mon 28 │ │
│ │    Sep 2026, 10:04 am: The school│ │
│ │    is closed for the sports meet.│ │
│ │ 3. …                             │ │
│ └──────────────────────────────────┘ │
│ ┌ Cancel this booking ─────────────┐ │
│ │ Cancels every class that hasn't  │ │
│ │ started yet, …                   │ │
│ │ [     Cancel this booking      ] │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

**Cancelled booking (phone, top of the page):**

```
│ ┌ ⓘ This booking was cancelled by  ┐ │  notice--note
│ │   Anjali on Tue 6 Oct 2026,      │ │
│ │   10:00 am. It was approved by   │ │
│ │   Anjali on Mon 28 Sep 2026, …   │ │
│ └──────────────────────────────────┘ │
│ ┌ Request ─────────────────────────┐ │
│ │ Status    [⊘ Cancelled]          │ │
│ │ Booked on Zoom 02 zoom02@…       │ │
│ │ Zoom link https://us02web.zoom…  │ │  plain text, not a link
│ │           For the record only.   │ │
│ │ Meeting ID 81234567890           │ │
│ └──────────────────────────────────┘ │
│ ┌ Classes (8) ─────────────────────┐ │
│ │ 1. Mon 5 Oct … (held: date only) │ │
│ │ 2. Wed 7 Oct … [⊘ Cancelled] …   │ │
```

#### D.1.7 Outcomes that land on this page

These all arrive by redirect (302) and show in `partials/messages.html` directly under the title row (`flash-messages.md`):

| From | Level → family | Icon | Role | Text (pinned) |
|---|---|---|---|---|
| whole cancel, emailed | success → ok | `check-circle` | status | `Cancelled the booking. We emailed {email}.` |
| one class, emailed | success → ok | `check-circle` | status | `Cancelled the class on {Mon 5 Oct 2026}. We emailed {email}.` |
| email failed | warning → warn | `alert-triangle` | status | `Cancelled, but the email to {email} didn't send. Tell them yourself.` |
| any of the above, manual provider | as above | | | the text plus ` This system can't reach Zoom: delete it in Zoom too.` |
| nothing to do (criterion 6, four cases) | error → bad | `alert-octagon` | alert | criterion 6's table, e.g. `That class was already cancelled.` |
| approve, email failed (criterion 30) | warning → warn | | | `Approved, but the email to {email} didn't send. Copy the Zoom link and the start link below and send them to them yourself.` The `Start link` row is on this same page, so "below" is true |

After the redirect the page loads at the top, so the flash is the first thing after the h1.

The approve form (criterion 29) loses its host-key tags and the "The email will ask the requester…" help. Each radio then shows only the label and the email. There are no other approve-box changes.

### D.2 Cancel confirm page: `zoom/cancel_confirm.html` (new, in the shell)

#### D.2.1 Structure

- **`{% block title %}`**: `Cancel this booking: {reference}` or `Cancel one class: {reference}` (when `occurrence`).
- **`{% block heading %}`**: `Cancel this booking` / `Cancel one class` (*design copy*).
- **Breadcrumb** (D10): Home › `Zoom link requests` (→ `zoom:queue`) › `{reference}` (→ `zoom:detail`) › `Cancel` (current).
- **Content**, in this order:
  1. **`cancel_error`**, when set: `div.notice.notice--bad[role=alert][tabindex=-1][data-error-summary]`, with `alert-octagon`, a `div.notice__body` holding `p.notice__title` `Not cancelled yet` (*design copy*), and `p` `{{ cancel_error }}`. It's printed as passed.
  2. `partials/error_summary.html` with `form=form lead="We couldn't cancel it yet." only`. This and item 1 never show together, because a Zoom error only happens after a valid form.
  3. **One `div.box` > `div.box__body` > `div.box__form`** (640px), with no box head (the h1 names the page, as on the account form). Inside it:
     - **`p.box__lead`** (*design copy*; the manual text is in D.2.2):
       - whole: `This removes the classes below from Zoom, frees {host_account.label} at those times, and emails {requester_name} with your reason. You can't undo it.`
       - one class: `This removes this class from Zoom, frees {host_account.label} at that time, and emails {requester_name} with your reason. The other classes stay booked. You can't undo it.`
     - **`dl.facts`**:
       - `Request`: `{reference}: {class_name}` (`break-anywhere`);
       - `Booked on`: `{host_account.label}`;
       - `Requester`: `{requester_name}`, a line break, then `span.text-muted.break-anywhere` `{requester_email}`.
     - **`div.box__section`** with `h2.box__subtitle` (*design copy*): `Classes to cancel ({to_cancel|length})`, or `Class to cancel` for a one-class cancel. Below it, `zoom/partials/occurrence_list.html` with `occurrences=to_cancel only`.
     - **When `kept`:** a `div.box__section` with `h2.box__subtitle` `Classes that stay ({kept|length})`, `p.text-muted` `These have started or finished, so they stay as they were.` (*design copy*), then `occurrence_list` with `occurrences=kept only`.
     - **The form** (`div.box__section`): `<form method="post" action="…" novalidate data-busy-form>` with `{% csrf_token %}`. The action is `{% url 'zoom:cancel_class' link_request.pk occurrence.pk %}` when `occurrence`, otherwise `{% url 'zoom:cancel' link_request.pk %}`.
       - `partials/field.html` with `field=form.reason only`, unchanged. The widget comes from `CancelForm` (criterion 7, G7): a textarea with `rows="4"` and `maxlength="1000"`, label `Why is it cancelled?`, help `This goes in the email to the requester.`, error `Tell the requester why it's cancelled.` (all pinned). The value is kept on every re-render. `maxlength` makes the browser stop at the limit.
       - `div.form-actions`:
         - `<button class="button button--danger" type="submit" data-busy-text="…">Cancel and email the requester</button>` (pinned, criterion 7). The busy text is `Removing it from Zoom…` when `checks_zoom`, otherwise `Cancelling…`.
         - `a.button.button--quiet` → `zoom:detail`: `Keep the class` when `occurrence`, otherwise `Keep the booking` (pinned, criterion 7, P4).
         - `p.visually-hidden[role=status][data-busy-status]`.

#### D.2.2 Manual provider (`checks_zoom` false; G3)

The lead drops "removes … from Zoom" (*design copy*):
- whole: `This cancels the classes below here, frees {label} at those times, and emails {requester_name} with your reason. You can't undo it.`
- one class: the matching form.

Straight after the lead comes `div.notice.notice--warn` with `alert-triangle`, `p.notice__title` `Delete it in Zoom too`, and `p` `This system can't reach Zoom. After you cancel here, delete {the meeting / this class} in {label}'s Zoom account.` (*design copy*). It's warn because a leftover Zoom meeting would still be joinable. The success flash repeats it (criterion 15).

#### D.2.3 Wireframes

**Desktop (1440, whole booking, one class held):**

```
Cancel this booking                                   Home › Zoom link requests › ZL-0042 › Cancel
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  ┌──── .box__form, 640px ─────────────────────────────┐                              │
│  │ This removes the classes below from Zoom, frees     │  box__lead                  │
│  │ Zoom 02 at those times, and emails Nimal Perera     │                              │
│  │ with your reason. You can't undo it.                │                              │
│  │ Request     ZL-0042: Grade 11 Physics               │  facts                       │
│  │ Booked on   Zoom 02                                 │                              │
│  │ Requester   Nimal Perera                            │                              │
│  │             nimal@polymath.edu.lk                   │                              │
│  │ ─────────────────────────────────────────────────── │                              │
│  │ Classes to cancel (7)                               │  h2.box__subtitle            │
│  │ 1. Wed 7 Oct 2026, 8:30 am to 11:30 am   5. …       │  occurrences--cols           │
│  │ 2. Mon 12 Oct 2026, …                    6. …       │                              │
│  │ ─────────────────────────────────────────────────── │                              │
│  │ Classes that stay (1)                               │                              │
│  │ These have started or finished, so they stay as     │                              │
│  │ they were.                                          │                              │
│  │ 1. Mon 5 Oct 2026, 8:30 am to 11:30 am              │                              │
│  │ ─────────────────────────────────────────────────── │                              │
│  │ Why is it cancelled?                                │  label                       │
│  │ This goes in the email to the requester.            │  help                        │
│  │ ┌─────────────────────────────────────────────────┐ │  textarea                    │
│  │ │                                                 │ │                              │
│  │ └─────────────────────────────────────────────────┘ │                              │
│  │ [ Cancel and email the requester ] Keep the booking │  button--danger + quiet      │
│  └─────────────────────────────────────────────────────┘                              │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400, one class, after a Zoom failure):**

```
┌──────────────────────────────────────┐
│ Cancel one class                     │
│ Home › Zoom link requests › ZL-0042  │
│ › Cancel                             │
│ ┌ ⬣ Not cancelled yet ─────────────┐ │  notice--bad, focused on load
│ │   We couldn't cancel it in Zoom: │ │
│ │   Zoom is busy right now.        │ │
│ │   Nothing was cancelled. Try     │ │
│ │   again in a few minutes.        │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ This removes this class from     │ │
│ │ Zoom, frees Zoom 02 at that time,│ │
│ │ … You can't undo it.             │ │
│ │ Request                          │ │
│ │ ZL-0042: Grade 11 Physics        │ │
│ │ …                                │ │
│ │ ──────────────────────────────── │ │
│ │ Class to cancel                  │ │
│ │ 1. Wed 7 Oct 2026, 8:30 am to    │ │
│ │    11:30 am                      │ │
│ │ ──────────────────────────────── │ │
│ │ Why is it cancelled?             │ │
│ │ This goes in the email to the    │ │
│ │ requester.                       │ │
│ │ ┌──────────────────────────────┐ │ │
│ │ │ The school is closed for the │ │ │  reason kept
│ │ │ sports meet.                 │ │ │
│ │ └──────────────────────────────┘ │ │
│ │ [Cancel and email the requester] │ │  full width, red
│ │ [        Keep the class        ] │ │  full width, quiet
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

#### D.2.4 States

| State | What the user sees |
|---|---|
| Default (GET) | the page as above, with an empty reason |
| Validation error (empty reason) | 200. The error summary (`We couldn't cancel it yet. 1 thing needs your attention.` with a link to `#id_reason`) is focused. The field shows `aria-invalid` and its error `Tell the requester why it's cancelled.` |
| Loading | the busy button: `Removing it from Zoom…` / `Cancelling…`. With no JS, the browser's own indicator |
| Zoom said no (criterion 12) | 200. `cancel_error` in the `Not cancelled yet` notice, e.g. `We couldn't cancel it in Zoom: Zoom is busy right now. Nothing was cancelled. Try again in a few minutes.` or the lasting form ending `Ask whoever manages the Zoom accounts to press Check connection for Zoom 02, then try again.` The reason is kept, so pressing the button again is the retry |
| Zoom may have done it (criterion 13) | 200, the same notice: `We couldn't tell whether Zoom removed it: no answer from Zoom. Nothing was cancelled here. Try again in a few minutes. Trying again is safe.` |
| Saving failed after the Zoom delete (criterion 14) | 200, the same notice: `Zoom removed it, but saving the cancellation here failed. Press Cancel again to finish.` The reason is kept, and the button is right below it |
| Nothing to do (criterion 6) | 302 to the detail with the error flash (D.1.7) |
| Success | 302 to the detail with the success or warning flash (D.1.7) |
| No permission | anonymous → sign-in, then back here. A plain user → the existing `403.html` |
| Not found | 404 (a request that isn't approved, a class from another request, or `cancel_class` on a one-off) |

### D.3 Queue: `zoom/queue.html`

#### D.3.1 Status tag (`zoom/partials/status_tag.html`)

Add the branch `status == "cancelled"`: `span.tag.tag--plain` with the **`slash`** icon and `{{ label }}` (`Cancelled`). Add it to the header comment's tone list.

**Why `slash` and plain.**
- A cancelled booking isn't an error to act on, so it isn't warn or bad.
- `Not approved` is already `tag--plain` with `x-circle`. `slash` ("switched off") is a different shape, so the two neutral statuses differ by icon and word, not only by position.
- `slash` is also `Not connected to Zoom` in `.avail`, but that tag is warn-toned and only appears in the availability list, so the two never meet.

#### D.3.2 The Cancelled tab

`tabs` gains `cancelled` between `Not approved` and `All`, and the markup is unchanged (`status-tabs.md`). Below 600px the five links make a 2-column grid of three rows, with `All` alone in the last row. That's acceptable and already covered by the component.

Add these branches to the result line, the caption and the empty state for `status == "cancelled"` (*design copy*). The other tabs are unchanged:

| Where | Text |
|---|---|
| Result line | `{n} cancelled booking{n\|pluralize}` |
| Caption | `Cancelled bookings, most recently cancelled first` |
| Empty state (no `q`) | `span.disc.disc--64` with `slash`; `h2` `No cancelled bookings.`; `p` `Bookings show here when the IT desk cancels them.` |

The search empty state (`No requests match …`) is unchanged.

The table's columns are unchanged: reference, class, requested by, first class, classes, status. A cancelled row's status cell shows the `Cancelled` tag.

A partly cancelled booking stays in `Link sent`. Its detail page shows which classes were cancelled.

### D.4 Timetable: no change to the templates

Criterion 2 removes cancelled classes from `booked()`, so they simply don't appear on the month or day pages, and their time shows as free. There are **no "ghost" entries** (a struck-through or greyed class):

- a calendar entry is a link that means "this account is taken then", and a cancelled one isn't;
- IT reads the cancellation history on the request's detail page.

A booking with every class cancelled disappears from the timetable entirely. The empty-day and empty-month states are unchanged.

### D.5 Start this class: `zoom/start.html` (new, public frame)

It extends `public_base.html`, so it has no shell and no sign-in (`public-frame.md`). Every state is one short column with one h1.

#### D.5.1 Headings (`zoom/partials/start_heading.html`)

The `title` and `heading` blocks both include this partial with `state=state only`. All the headings are *design copy*. They're chosen so that no heading repeats the pinned sentence below it word for word.

| `state` | h1 |
|---|---|
| `ready` | `Start your class` |
| `too_early` | `It's too early to start` |
| `ended` | `This booking has finished` |
| `cancelled` | `Booking cancelled` |
| `invalid` | `We can't open this link` (the same as the confirm page's invalid state) |
| `not_set_up` | `Can't start from here yet` |

#### D.5.2 Class details (every state except `invalid`)

A `dl.facts` comes straight after the lead or notice. The template reads only `class_name`, `reference` and the class times (criterion 22):

| `dt` | `dd` |
|---|---|
| `Class` | `{link_request.class_name}` (`break-anywhere`) |
| `Reference` | `{link_request.reference}` |
| `This class` (ready) / `Next class` (too_early) / `Last class` (ended) / `Class time` (not_set_up, *design copy*) | `zoom/partials/class_span.html` with `occurrence.starts_at` and `ends_at`. Omitted when `occurrence` is `None` (cancelled, or not_set_up without one) |

For `not_set_up` the facts still show (G6, criterion 26), so the teacher can tell the IT desk which class they mean.

#### D.5.3 Per state

| `state` | Before the facts | After the facts |
|---|---|---|
| `ready` | `p.public__lead` (*design copy*): `When you're ready, press Start this class. Zoom opens and starts the meeting with you as the host.` Then, when `start_error`: `div.notice.notice--bad[role=alert][tabindex=-1][data-error-summary]`, `alert-octagon`, `div.notice__body` holding `p.notice__title` `The class didn't start` (*design copy*) and `p` `{{ start_error }} {% include "zoom/partials/it_desk_contact.html" with phone=it_desk_phone still=start_error_still only %}`. `start_error` is pinned without the contact sentence: `We couldn't reach Zoom just now. Try again in a minute.` (`start_error_still` true) or `This class's meeting isn't in Zoom any more.` (`start_error_still` false) | `<form method="post" action="{% url 'zoom:start' token %}" data-busy-form>`, `{% csrf_token %}`, `div.form-actions` holding `<button class="button button--primary" type="submit" data-busy-text="Opening Zoom…">` with the `video` icon and `Start this class`, plus the `data-busy-status` region. Below the form, `p.field__help` (*design copy*): `You don't need to sign in to Zoom. If your browser asks whether to open Zoom, choose Open.` |
| `too_early` | `div.notice.notice--note` with the **`clock`** icon and `p`, pinned: `This link works from {opens_at\|class_time} on {opens_at\|class_date}, 30 minutes before the class, until it ends.`, or, when `opens_after_other_class`, `This link works from {opens_at\|class_time} on {opens_at\|class_date}, when the class before it on this Zoom account ends.` | `p` (*design copy*) `Come back then. This page doesn't update by itself.`, then `a.button.button--secondary` → `{% url 'zoom:start' token %}`: `Check again` (a plain GET reload) |
| `ended` | `div.notice.notice--note`, `info`, `p` pinned `All the classes for this booking have finished.` | `p` (*design copy*) `Need more classes? ` + `a` → `zoom:request` `Send a new request` |
| `cancelled` | `div.notice.notice--warn`, `alert-triangle`, `div.notice__body` holding `p.notice__title` pinned `This booking was cancelled.` and `p` (*design copy*) `The IT desk emailed the reason to the person who booked it.` | `p` `Need the class after all? ` + `a` → `zoom:request` `Send a new request` |
| `invalid` (404) | `div.notice.notice--warn`, `alert-triangle`, `p`: pinned `This start link doesn't work. Check you copied all of it.`, a space, then the contact partial with `still=True` | nothing (no facts: the token didn't resolve) |
| `not_set_up` | `div.notice.notice--note`, `info`, `p`: pinned `Starting a class from a link isn't set up yet.`, a space, then the contact partial with `still=False` | the facts (D.5.2); nothing more |

**The contact sentence: `zoom/partials/it_desk_contact.html`** (criterion 47, pinned). It's included with `phone=it_desk_phone still=… only`, prints one inline sentence and no block element, so it sits at the end of the message's own `p`. Which form each message takes:

| Message | `still` | Setting set (`it_desk_phone` is a dict) | Setting empty (`None`) |
|---|---|---|---|
| invalid link | true | `If it still doesn't work, phone the IT desk on <a class="tap-link" href="tel:{tel}">{display}</a>.` | `If it still doesn't work, contact the IT desk.` |
| Zoom failure | true | as above | as above |
| meeting gone | false | `Phone the IT desk on <a class="tap-link" href="tel:{tel}">{display}</a>.` | `Contact the IT desk.` |
| not set up | false | as above | as above |

- The link text is `display` (`+94 11 234 5678`); the `href` is `tel:` plus `tel` (`tel:+94112345678`). The full stop sits outside the link.
- The link is `.tap-link`, so it's 44px tall on phones and taps straight into a call (criterion 39, step 10). It inherits the notice's text colour and underline, as other links inside notices do.
- The partial's header comment names `phone` (dict or `None`) and `still` (bool). It has no trailing newline, so no stray space lands before the full stop.

- **Why `cancelled` is warn:** a teacher opening this link expects to teach. Being told the class is off is the one surprising outcome here.
- **Why `too_early` doesn't refresh itself:** the page is `no-store`, and `Check again` is a real GET. A silent auto-reload would move the reading position for screen-reader users and could surprise a teacher mid-read. Waiting 30 minutes is rare, because most teachers open the email just before class.
- **The `Start this class` button** is `button--primary`, and full width below 600px (the existing `.form-actions` rule). It's the one primary action on the page.

#### D.5.4 Wireframes

**Phone (400), `ready`:**

```
┌──────────────────────────────────────┐
│ [crest] Technology Management Desk ◐ │  public__head
│ ┌──────────────────────────────────┐ │
│ │ Start your class                 │ │  h1
│ │ When you're ready, press Start   │ │  public__lead
│ │ this class. Zoom opens and starts│ │
│ │ the meeting with you as the host.│ │
│ │ Class       Grade 11 Physics     │ │  facts
│ │ Reference   ZL-0042              │ │
│ │ This class  Mon 5 Oct 2026,      │ │
│ │             8:30 am to 11:30 am  │ │
│ │ [ ▶  Start this class          ] │ │  primary, full width, 44px
│ │ You don't need to sign in to     │ │  field__help
│ │ Zoom. If your browser asks       │ │
│ │ whether to open Zoom, choose     │ │
│ │ Open.                            │ │
│ └──────────────────────────────────┘ │
│ footer                               │
└──────────────────────────────────────┘
```

**Phone (400), `too_early`, opened later because of an earlier class:**

```
│ │ It's too early to start          │ │
│ │ ┌ ◷ This link works from 8:15 am ┐ │ │  notice--note, clock
│ │ │   on Mon 5 Oct 2026, when the  │ │ │
│ │ │   class before it on this Zoom │ │ │
│ │ │   account ends.                │ │ │
│ │ └────────────────────────────────┘ │ │
│ │ Class       Grade 11 Physics     │ │
│ │ Reference   ZL-0042              │ │
│ │ Next class  Mon 5 Oct 2026,      │ │
│ │             8:30 am to 11:30 am  │ │
│ │ Come back then. This page doesn't│ │
│ │ update by itself.                │ │
│ │ [          Check again         ] │ │  secondary (a link)
```

**Phone (400), `ready` after a failed POST:**

```
│ │ Start your class                 │ │
│ │ When you're ready, press …       │ │
│ │ ┌ ⬣ The class didn't start ──────┐ │ │  notice--bad, focused on load
│ │ │   We couldn't reach Zoom just  │ │ │
│ │ │   now. Try again in a minute.  │ │ │
│ │ │   If it still doesn't work,    │ │ │
│ │ │   phone the IT desk on         │ │ │
│ │ │   +94 11 234 5678.             │ │ │  tel: link, .tap-link, 44px
│ │ └────────────────────────────────┘ │ │
│ │ Class … Reference … This class … │ │
│ │ [ ▶  Start this class          ] │ │  the retry
```

With `IT_DESK_PHONE` empty, the last sentence reads `If it still doesn't work, contact the IT desk.` and there's no link.

**Phone (400), `invalid` (404), setting set:**

```
│ │ We can't open this link          │ │  h1
│ │ ┌ △ This start link doesn't work.┐ │ │  notice--warn
│ │ │   Check you copied all of it.  │ │ │
│ │ │   If it still doesn't work,    │ │ │
│ │ │   phone the IT desk on         │ │ │
│ │ │   +94 11 234 5678.             │ │ │  tel: link, .tap-link, 44px
│ │ └────────────────────────────────┘ │ │
│ └──────────────────────────────────┘ │  no facts, no form
```

**Phone (400), `not_set_up` (manual provider), setting set:**

```
│ │ Can't start from here yet        │ │  h1
│ │ ┌ ⓘ Starting a class from a link ┐ │ │  notice--note
│ │ │   isn't set up yet. Phone the  │ │ │
│ │ │   IT desk on +94 11 234 5678.  │ │ │  tel: link
│ │ └────────────────────────────────┘ │ │
│ │ Class       Grade 11 Physics     │ │  facts still show (G6)
│ │ Reference   ZL-0042              │ │
│ │ Class time  Mon 5 Oct 2026,      │ │
│ │             8:30 am to 11:30 am  │ │
│ └──────────────────────────────────┘ │  no form
```

**Desktop (1440):** the same column, as a card on the grey page (`.public__main` at 640px + padding, centred). No other layout change.

#### D.5.5 Other states

| State | Behaviour |
|---|---|
| Loading | the busy button (`Opening Zoom…`). On success the browser leaves for Zoom (302), and the Zoom page asks to open the app. With back/forward, the button is restored (`busy-button.md`) |
| POST in a non-ready state | the page re-renders in that state (criterion 23). That's the same as a GET, so it's covered by the table |
| CSRF failure | Django's 403. It's rare, because the page sets the cookie on GET. It's not designed here (the app has no custom CSRF page) |
| Success feedback | none in the app: Zoom itself is the feedback |

### D.6 Zoom account change page: `zoom/account_form.html` (the Host key section)

#### D.6.1 Changes, in section order

1. **State line**, unchanged for `saved`, `saved_legacy` and `unreadable`.
   - For `none`, the notice changes from `notice--warn` to **`notice--note`** with the `info` icon. A missing key no longer affects any email or approval, so there's nothing to warn about.
   - The title stays `No host key saved`.
   - The body becomes criterion 30's pinned notice text (P6): `Save one below so the IT desk has a fallback if a start link doesn't work.` The field help below keeps the longer `Host keys aren't emailed. …` text, so the two never say the same thing.
2. **New, when `can_reveal_host_key`:** a `div.field` holding:
   - `<button class="button button--secondary" type="submit" form="host-key-show" aria-describedby="host-key-show-help">`, with the `key` icon and `Show host key` (pinned);
   - `p.field__help#host-key-show-help`, pinned: `For when a start link doesn't work. Every time the key is shown, it's recorded.`
3. **New, when `key_reveal_count` > 0** (shown even when the button isn't, e.g. after the key was removed): `p.text-muted`, pinned: `Last shown to {last_key_reveal.shown_by} on {when}. Shown {key_reveal_count} time{key_reveal_count|pluralize} in all.` The time uses `zoom/partials/when.html` with `at=last_key_reveal.shown_at`. So it reads `Shown 1 time in all.` / `Shown 3 times in all.`
4. The new-key field and `Remove`, unchanged. The help is criterion 30's text, from the form.

**The separate form** is written after the main `</form>`, beside `#zoom-check` (006's pattern: no nesting, and it works with no JS):

```html
{% if can_reveal_host_key %}<form id="host-key-show" method="post" action="{% url 'zoom:account_host_key' account.pk %}">{% csrf_token %}</form>{% endif %}
```

There's no busy button: the reveal makes no outside call.

**Tab order:** … Check connection → **Show host key** → New host key → Remove → Save changes → Cancel. That's the visual order.

#### D.6.2 Wireframe (desktop, key saved, revealed before)

```
│  │ Host key                                        │  legend
│  │ ┌ ✓ Host key saved on Mon 21 Sep 2026 by Ravi ┐ │  notice--ok (unchanged)
│  │ [ ⚷ Show host key ]                             │  button--secondary, form="host-key-show"
│  │ For when a start link doesn't work. Every time  │  field__help
│  │ the key is shown, it's recorded.                │
│  │ Last shown to Ravi on Tue 6 Oct 2026, 8:20 am.  │  text-muted
│  │ Shown 2 times in all.                           │
│  │ New host key                                    │
│  │ Host keys aren't emailed. Teachers start …      │  help (criterion 30)
│  │ [                ]                              │
│  │ [ ] Remove the saved host key                   │
```

**No key saved** (no `Show host key` button, no reveal line when `key_reveal_count` is 0):

```
│  │ Host key                                        │  legend
│  │ ┌ ⓘ No host key saved ────────────────────────┐ │  notice--note (was warn)
│  │ │   Save one below so the IT desk has a       │ │  P6, criterion 30
│  │ │   fallback if a start link doesn't work.    │ │
│  │ └─────────────────────────────────────────────┘ │
│  │ New host key                                    │
│  │ Host keys aren't emailed. Teachers start        │  help (criterion 30)
│  │ classes with the start link in their approval   │
│  │ email. If that link fails, the IT desk can show │
│  │ the key on this page.                           │
│  │ [                ]                              │
```

The phone layout is the same stack. The button keeps its natural width at 44px, as `Check connection` does.

#### D.6.3 Outcomes of pressing it

| Result | Where | Look |
|---|---|---|
| Readable key | the reveal page (D.7) | |
| No key saved | redirect to this page | error flash (bad, `alert-octagon`, `role="alert"`): `{label} has no host key saved.` |
| Unreadable key | redirect to this page | error flash: `A host key is saved, but it can't be read with the current encryption keys. Type it again.` |
| No permission | 403 / sign-in | the button isn't rendered without `can_reveal_host_key` |

### D.7 Host key reveal page: `zoom/host_key_reveal.html` (new, in the shell)

#### D.7.1 Structure

- **Title and h1:** `Host key for {account.label}` (pinned).
- **Breadcrumb:** Home › `Zoom accounts` (→ `zoom:accounts`) › `{label}` (→ `zoom:account_edit`) › `Host key` (current).
- **Content:** one `div.box` > `div.box__body` > `div.box__form` (640px):
  1. **`.secret`** (`secret-value.md`): the label `Host key`, then `p.secret__value[translate=no]` holding `{{ host_key }}`, printed once.
  2. `p.text-muted` (*design copy*): `We've recorded that you were shown this key. Reloading this page shows it again and records it again.`
  3. `div.box__section` with `h2.box__subtitle` `When to use it`, then `p`: `Only when the start link in the approval email doesn't work. Read the key to the teacher over the phone. Don't email it or send it in a message.`
  4. `div.box__section` with `h2.box__subtitle` `How the teacher uses it`, then:
     - `ol.occurrences` (the existing numbered list: kit indent and spacing, no new class) with three `li`: `Join the class with its Zoom link.` / `Open Participants and choose <strong>Claim host</strong>.` / `Type the host key.`
     - `div.notice.notice--warn` with `alert-triangle`, `div.notice__body` holding `p.notice__title` `The waiting room can stop this` and `p`: `If this Zoom account keeps its waiting room on, the teacher waits there first. They can claim host only after someone already in the meeting lets them in. If nobody is in the meeting yet, the teacher can't get in this way. Instead, open the start link on the class's request page, start the class yourself, then let the teacher in and make them host.` (R7).
  5. `div.box__section` with `h2.box__subtitle` `Keep it safe`, then `p`: `This key lets anyone take host control of every meeting on {label}, not just this class. If it may have spread, change the key in Zoom, then type the new one on this account's page.`
  6. `div.form-actions` holding `a.button.button--secondary` → `zoom:account_edit account.pk`: `Back to Change {label}` (pinned).

**All of sections 3–5 are criterion 42's pinned text** (P2, accepted as D14): the three headings, the three steps, the notice title and every sentence. `{label}` is `account.label`. The step `Open Participants and choose Claim host.` is confirmed in the owner's live check (criterion 39, step 9); if the owner reports another place, the criterion changes first and this line follows.

#### D.7.2 Wireframe (desktop)

```
Host key for Zoom 02                          Home › Zoom accounts › Zoom 02 › Host key
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  ┌──── .box__form, 640px ─────────────────────────────┐                              │
│  │ ┌─────────────────────────────────────────────────┐ │                              │
│  │ │ Host key                                        │ │  .secret__label              │
│  │ │ 1 2 3 4 5 6                                     │ │  28px mono, letter-spaced    │
│  │ └─────────────────────────────────────────────────┘ │  (the digits aren't spaced   │
│  │ We've recorded that you were shown this key.        │   in the markup)             │
│  │ Reloading this page shows it again and records it   │                              │
│  │ again.                                              │                              │
│  │ ─────────────────────────────────────────────────── │                              │
│  │ When to use it                                      │  h2                          │
│  │ Only when the start link in the approval email      │                              │
│  │ doesn't work. Read the key to the teacher over the  │                              │
│  │ phone. Don't email it or send it in a message.      │                              │
│  │ ─────────────────────────────────────────────────── │                              │
│  │ How the teacher uses it                             │  h2                          │
│  │ 1. Join the class with its Zoom link.               │  ol.occurrences              │
│  │ 2. Open Participants and choose Claim host.         │                              │
│  │ 3. Type the host key.                               │                              │
│  │ ┌ △ The waiting room can stop this ──────────────┐  │  notice--warn                │
│  │ │   If this Zoom account keeps its waiting room  │  │                              │
│  │ │   on, the teacher waits there first. They can  │  │                              │
│  │ │   claim host only after someone already in the │  │                              │
│  │ │   meeting lets them in. If nobody is in the    │  │                              │
│  │ │   meeting yet, the teacher can't get in this   │  │                              │
│  │ │   way. Instead, open the start link on the     │  │                              │
│  │ │   class's request page, start the class        │  │                              │
│  │ │   yourself, then let the teacher in and make   │  │                              │
│  │ │   them host.                                   │  │                              │
│  │ └────────────────────────────────────────────────┘  │                              │
│  │ ─────────────────────────────────────────────────── │                              │
│  │ Keep it safe                                        │  h2                          │
│  │ This key lets anyone take host control of every     │                              │
│  │ meeting on Zoom 02, not just this class. If it may  │                              │
│  │ have spread, change the key in Zoom, then type the  │                              │
│  │ new one on this account's page.                     │                              │
│  │ [ Back to Change Zoom 02 ]                          │  button--secondary (a link)  │
│  └─────────────────────────────────────────────────────┘                              │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400):** the same single column. The key stays at 28px (a 10-digit key is about 200px wide). The back link is full width.

#### D.7.3 States

There's only one: shown. The no-key and unreadable cases never reach this page (D.6.3). With no permission it's 403 or sign-in, and `GET` gets 405 (never linked). A reload means the browser asks to resend the form, which is a new, recorded reveal, as the line under the key says.

### D.8 Emails (plain text)

#### D.8.1 `approved_body.txt` (changed)

```
Hello {requester_name},

The IT desk has approved your request {reference}. Here is your Zoom link.

Join link: {join_url}
Meeting ID: {meeting_id}
Passcode: {passcode|default:"none"}

Use the same link for every class below.{% if start_url %} Share the join link with your students. Keep the start link to yourself.{% endif %}

{% if start_url %}Starting the class as host
Start link: {start_url}
Open this link from 30 minutes before each class until it ends, then press Start this class. It starts the meeting as host, with no Zoom sign-in. Keep it private: anyone who has it can start these classes as host.{% else %}Ask the IT desk how to start the class as host.{% endif %}

{% if wants_recording %}You asked for this class to be recorded to the Zoom cloud.

{% endif %}When: {schedule_summary}
Your classes ({n}):
- Mon 5 Oct 2026, 8:30 am to 11:30 am
…

To change the times, reply to the IT desk.{% if start_url %} Please don't forward this email, because the start link in it lets anyone start your classes as host.{% endif %}

Polymath College IT desk
```

Rendered with the `zoom` or `fake` provider (`start_url` set):

```
Use the same link for every class below. Share the join link with your students. Keep the start link to yourself.

Starting the class as host
Start link: https://tmd.polymath.edu.lk/zoom/start/eyJyIjo0Mi…
Open this link from 30 minutes before each class until it ends, then press Start this class. It starts the meeting as host, with no Zoom sign-in. Keep it private: anyone who has it can start these classes as host.
…
To change the times, reply to the IT desk. Please don't forward this email, because the start link in it lets anyone start your classes as host.
```

Rendered with the `manual` provider (`start_url` is `""`):

```
Use the same link for every class below.

Ask the IT desk how to start the class as host.
…
To change the times, reply to the IT desk.
```

- Everything here is pinned: the start-link block and the P7 line (criterion 28), the manual line (criterion 26), and both forms of the last paragraph (criterion 28, P3).
- The P7 line goes on the same line as `Use the same link for every class below.`, straight after it, so the two sentences about links read together.
- The manual version contains no `start link` in any case (the criterion 28 test). `Ask the IT desk how to start the class as host.` says "start the class", not "start link".
- The header comment loses "The only template that ever receives a host key" and gains `start_url` (`""` for the manual provider, G5).

#### D.8.2 `cancelled_subject.txt` (new)

`Cancelled: {reference} {class_name}` (pinned). It's one line, with no trailing newline, like the other subjects.

#### D.8.3 `cancelled_body.txt` (new)

```
Hello {requester_name},

{% if remaining %}The IT desk has cancelled {cancelled|length} class{cancelled|length|pluralize:"es"} of your Zoom booking {reference} for {class_name}.{% else %}The IT desk has cancelled your Zoom booking {reference} for {class_name}.{% endif %}

Classes cancelled ({cancelled|length}):
- Wed 7 Oct 2026, 8:30 am to 11:30 am
…

Reason: {reason}

{% if remaining %}{% if can_start %}Your other classes are still on, with the same link and start link.{% else %}Your other classes are still on, with the same link.{% endif %}

{% endif %}Zoom doesn't tell the people you shared the link with. Please let your students know.

To book again, send a new request: {request_url}

Polymath College IT desk
```

Rendered, one class of ZL-0042 cancelled, `zoom` provider:

```
Hello Nimal Perera,

The IT desk has cancelled 1 class of your Zoom booking ZL-0042 for Grade 11 Physics.

Classes cancelled (1):
- Wed 7 Oct 2026, 8:30 am to 11:30 am

Reason: The school is closed for the sports meet.

Your other classes are still on, with the same link and start link.

Zoom doesn't tell the people you shared the link with. Please let your students know.

To book again, send a new request: https://tmd.polymath.edu.lk/zoom/request/

Polymath College IT desk
```

- With the `manual` provider (`can_start` false), the "still on" paragraph reads `Your other classes are still on, with the same link.`
- When the whole booking is cancelled (`remaining` empty), that paragraph is left out, and the P5 line follows `Reason:` directly.
- The opening sentence and `Classes cancelled (n):` are *design copy*.
- Pinned (criterion 17), in the criterion's order: the class lines (`Occurrence.__str__`), `Reason:`, both forms of the "still on" sentence (`can_start`, G5, P3), the P5 line (every time), and the request line.
- It holds no join link, passcode, start link or host key. "start link" appears only as words in the `can_start` sentence, never as a URL.
- It's `{% autoescape off %}`, like the other bodies.

### D.9 Copy

**Pinned:** criteria 6–8, 12–15, 17, 22–23, 26, 28–31, 33, 41, 42, 44 and 47 are used verbatim as quoted in D.1–D.8. Since D13 and D14 that includes: `In progress`, `Keep the booking` / `Keep the class`, `Cancel and email the requester`, the four contact sentences (criterion 47), the reveal page's headings, steps and notice title (P2), the P3 variants of both emails, the P5 and P7 lines, and the P6 notice.

**Design copy** (new here; the frontend owns it, and the backend doesn't need it unless noted):

| Where | Text |
|---|---|
| Detail, cancelled line (second sentence) | `It was approved by {name} on {when}.` |
| Detail, cancelled Zoom link | `For the record only.` |
| Detail, cancel box title and link | `Cancel this booking` |
| Detail, cancel box lead | D.1.5's four sentences |
| Confirm, h1 | `Cancel this booking` / `Cancel one class` |
| Confirm, lead | D.2.1 and D.2.2 |
| Confirm, facts | `Request`, `Booked on`, `Requester` |
| Confirm, lists | `Classes to cancel ({n})` / `Class to cancel`; `Classes that stay ({n})`; `These have started or finished, so they stay as they were.` |
| Confirm, manual notice | `Delete it in Zoom too` / `This system can't reach Zoom. After you cancel here, delete {the meeting / this class} in {label}'s Zoom account.` |
| Confirm, error title | `Not cancelled yet` |
| Confirm, error summary lead | `We couldn't cancel it yet.` |
| Confirm, busy text | `Removing it from Zoom…` / `Cancelling…` |
| Queue, Cancelled tab | result line, caption and empty state (D.3.2) |
| Start page headings | D.5.1 |
| Start page, ready | `When you're ready, press Start this class. Zoom opens and starts the meeting with you as the host.` / `You don't need to sign in to Zoom. If your browser asks whether to open Zoom, choose Open.` / error title `The class didn't start` / busy `Opening Zoom…` |
| Start page, too_early | `Come back then. This page doesn't update by itself.` / `Check again` |
| Start page, ended / cancelled | `Need more classes?` / `The IT desk emailed the reason to the person who booked it.` / `Need the class after all?` / `Send a new request` |
| Facts labels on the start page | `Class`, `Reference`, `This class` / `Next class` / `Last class` / `Class time` |
| Reveal page | `We've recorded that you were shown this key. Reloading this page shows it again and records it again.` |
| Cancellation email | the opening sentence, `Classes cancelled ({n}):` |

These words never appear on any screen: "token", "occurrence", "API", "start_url", "revoke", "salt".

### D.10 Accessibility

- **Landmarks and headings:**
  - **Detail:** h1 → h2 per box (`Request`, `Classes (n)`, `Cancel this booking`), with no new levels.
  - **Confirm:** h1 → h2 (`Classes to cancel`, `Classes that stay`). The reason's question is its `<label>`, not a heading.
  - **Start page:** h1 only, in `main`, with the frame's `banner` and `contentinfo`.
  - **Reveal page:** h1 → three h2s.
- **Label, help and error wiring:**
  - `reason` uses `partials/field.html`: `aria-describedby="reason-error reason-help"` on error (`reason-help` otherwise), `aria-invalid="true"`, and `required`.
  - The error summary links to `#id_reason`.
  - `Show host key` has `aria-describedby="host-key-show-help"`.
- **Unique link names:**
  - Each `Cancel this class` includes its date in visually hidden text (criterion 8).
  - `Cancel this booking` appears twice: once as the box title (a heading) and once as the link, so there's one link.
  - `Back to Change {label}` names the account.
- **Status is never colour alone:**
  - `Cancelled`: `slash` + word;
  - `In progress`: `clock` + word;
  - every notice has an icon and words;
  - the danger button's words say what it does;
  - the muted date of a cancelled class is backed by the tag.
- **Focus:**
  - **Confirm page after an error:** `cancel_error` or the error summary is `data-error-summary`, so `app.js` focuses it and scrolls to it (existing). With no JS, it's the first content after the title row.
  - **After a successful cancel:** the detail page loads normally, and the flash is the first content after the h1. A warning or error flash is announced (`role="alert"` for errors, `status` otherwise). Closing it returns focus to `<main>` (existing).
  - **Start page after a failed POST:** the `start_error` notice is focused (`data-error-summary`), and the `Start this class` button is the next tab stop.
  - **Busy submits** (confirm, start): focus stays on the button (`aria-disabled`, not `disabled`), and the busy text is announced through `data-busy-status`.
  - **Reveal:** a normal page load. The key is the first content after the h1, and `Back to Change {label}` is the only focusable thing on the page after the shell.
  - **Keyboard order:**
    - Confirm: breadcrumb links → the reason → the danger button → `Keep the booking` / `Keep the class`.
    - Detail Classes: each `Cancel this class` in date order, then `Cancel this booking`.
    - Start: colour-mode button → the IT desk phone link, when a notice shows one → `Start this class` (or `Check again`, or `Send a new request`). After a failed POST the focused notice holds the phone link, so it's the next stop, then the retry button.
- **Touch targets:**
  - Every `.button` is 44px.
  - `.classrows__action` is 44px at **every** width, the `Start link` and cancelled-row links are `.tap-link` (44px below 768px), and the start page's button is full width below 600px.
  - The IT desk phone link is `.tap-link` too (criterion 47), so a teacher on a phone gets a 44px target that starts a call. Its text is the full grouped number, so it's a real word-sized target, not a lone icon.
- **Reflow and contrast:**
  - No sideways scroll at 320 / 400 / 1024 / 1440 in both modes.
  - The start link, reason text, class names and emails wrap anywhere.
  - The only new colour pairs are the danger button (about 6.6:1, `danger-button.md`) and the secret value (about 12:1 / 8.5:1, `secret-value.md`). Everything else is existing tag, notice and text pairs.
- **Times:** every date is in `<time datetime>` through `class_span.html` / `when.html`.
- **The key, for screen readers:** it's plain text, so a screen-reader user can read it character by character. It isn't hidden, spaced or labelled with a second copy, so it's printed exactly once (contract).

### D.11 Progressive enhancement

- **Works with plain HTML and full page loads:**
  - every page, state and message here;
  - the confirm form with validation and Zoom errors;
  - the per-class links;
  - `Show host key` (a real form, through the `form` attribute, not nested);
  - the start page's GET and POST;
  - `Check again` (a link);
  - the IT desk phone number (a plain `tel:` link).

  No `confirm()` dialog anywhere: the confirmation is a page (D.2).
- **What `app.js` adds (existing blocks only, no new JS):**
  - error-summary focus on `[data-error-summary]` (confirm page, start page);
  - flash Close;
  - the busy button on the cancel form and the start form.

  It binds only to `data-*` hooks. With JS off, the buttons simply stay as they are, and the browser shows its own loading state.

### D.12 Build list for `tmd-frontend`

- **Templates** (each new or changed one starts with the `{# … #}` header naming its purpose and context; every include ends with `only`):
  - `zoom/detail.html`: D.1. Its header comment adds `can_cancel_booking`, `cancellable_ids`, `in_progress_id`, `cancel_blocked_message`, `start_link`, the cancelled fields, and the new partial.
  - **New** `zoom/partials/class_rows.html` (`class-rows.md`).
  - **New** `zoom/cancel_confirm.html` (D.2).
  - `zoom/queue.html` (D.3.2) and `zoom/partials/status_tag.html` (D.3.1).
  - **New** `zoom/start.html`, `zoom/partials/start_heading.html` and `zoom/partials/it_desk_contact.html` (D.5; the last is criterion 47's pinned sentence).
  - `zoom/account_form.html` (D.6): the `none` notice tone and P6 body, the button, the reveal line, and the `#host-key-show` form. Its header comment gains the three new variables and drops "a saved key is never shown" in favour of "never shown on this page".
  - **New** `zoom/host_key_reveal.html` (D.7). Its header comment says it's the only template that receives a plaintext host key.
  - `zoom/email/approved_body.txt`, and **new** `cancelled_subject.txt` and `cancelled_body.txt` (D.8).
- **CSS** (`static/css/style.css`, tokens only):
  - palette `--red-800` in the first `:root`;
  - `--c-danger`, `--c-danger-hover` and `--c-on-danger` in 1c;
  - `--font-mono` and `--fs-secret` in 1b;
  - `.button--danger` in 5d;
  - `.classrows*` next to `.occurrences` (5n), with `.classrows--cols` in a `(min-width: 1400px)` block in section 8;
  - `.secret*` in section 5, and its print rule in section 9.
- **Icons:** none new.
- **JS:** none new.

### D.13 Gaps in the context contract (backend to add or confirm)

**Status: all seven resolved** (decision D13). They're in the context contract and criteria 7 and 8 as written below. Kept here as the record of why each variable exists.

- **G1 — `in_progress_id`** (int or `None`) on `zoom/detail.html`: the pk of `link_request.class_in_progress()`. It's used for the `In progress` tag in the Classes list, so IT can see *why* that class has no cancel link.
- **G2 — `cancel_blocked_message`** (str or `None`) on `zoom/detail.html`. When the request is `approved` and not `can_cancel_booking`, it's criterion 6's whole-booking message (the in-progress sentence, or `There are no classes left to cancel in this booking.`), from the same model constants. It's `None` otherwise. So the detail page says why there's no cancel button, rather than hiding it silently, and the text lives in one place.
- **G3 — `checks_zoom`** (bool) on `zoom/cancel_confirm.html`, with the same meaning as on the detail page (false for the manual provider). It's for the lead, the "Delete it in Zoom too" notice and the busy text (D.2.2). `detail.html` already has it.
- **G4 — Confirm-page fields read from `link_request`:** `requester_name`, `requester_email` and `host_account.label` (as well as `reference` and `class_name`). They're on the object already. Please confirm and list them in the contract.
- **G5 — `can_start`** (bool) on `cancelled_body.txt`, and `start_url` staying `""` on `approved_body.txt` for the manual provider. It's needed only if P3 is accepted, so the emails don't mention a start link that was never sent.
- **G6 — `start.html`:**
  - Confirm `link_request` and, where one exists, `occurrence` are also passed for `not_set_up`, so the class facts show.
  - Confirm `token` is passed in every state that has a form or a `Check again` link (`ready`, `too_early`).
- **G7 — `CancelForm.reason` widget:** a `Textarea` with `maxlength="1000"` and `rows="4"`, the label `Why is it cancelled?` and the help `This goes in the email to the requester.`, all on the form (as 008 G2), so `partials/field.html` renders it unchanged.

### D.14 Copy proposals (for the main session; pinned text stays until approved)

**Status: all seven accepted** (decision D14) and now pinned in the criteria, which are the source of truth. The sections above use the pinned text. Kept here as the record of why each change was made.

- **P1 was settled differently from how it's worded below.** The setting is `IT_DESK_PHONE`, not `TMD_IT_DESK_PHONE`. The sentence is criterion 47's `Phone the IT desk on {number}.` / `If it still doesn't work, phone the IT desk on {number}.`, falling back to `Contact the IT desk.` / `If it still doesn't work, contact the IT desk.` when the setting is empty (D.5.3).
- **P2–P7** are pinned as proposed (criteria 7, 17, 26, 28, 30 and 42).

- **P1 — "Phone the IT desk" gives no number.**
  - The public start page is used by teachers minutes before class, and it tells them to phone the IT desk in four places (criteria 22, 23 and 26). The app has no IT desk phone number anywhere.
  - **Proposal:** a setting `TMD_IT_DESK_PHONE` (read in `base.py`; devops adds it to `.env.example` and compose), shown as a `tel:` link after each "phone the IT desk", e.g. `… phone the IT desk on 011 234 5678.`
  - When it's unset, the text stays as pinned.
  - This needs a small devops and backend addition. If it's out of scope for 011, record it as a follow-up.
- **P2 — The reveal-page guidance (criterion 42; owner-flagged, D11).** This version keeps all three facts (when to use it, the waiting-room limit, and that it opens every meeting on the account). It splits the how-to into steps, and it replaces the vague "start the class for them from its request page" with the action that actually gets the teacher in:
  - **When to use it:** `Only when the start link in the approval email doesn't work. Read the key to the teacher over the phone. Don't email it or send it in a message.`
  - **How the teacher uses it:**
    1. `Join the class with its Zoom link.`
    2. `Open Participants and choose Claim host.`
    3. `Type the host key.`
  - **Warn notice, title** `The waiting room can stop this`: `If this Zoom account keeps its waiting room on, the teacher waits there first. They can claim host only after someone already in the meeting lets them in. If nobody is in the meeting yet, the teacher can't get in this way. Instead, open the start link on the class's request page, start the class yourself, then let the teacher in and make them host.`
  - **Keep it safe:** `This key lets anyone take host control of every meeting on {label}, not just this class. If it may have spread, change the key in Zoom, then type the new one on this account's page.`
  - **To confirm in the owner's live check** (criterion 39, step 9): that `Claim host` is under Participants in the client the school uses.
- **P3 — Don't mention a start link that wasn't sent (manual provider).**
  - In `approved_body.txt`, when `start_url` is empty, the last paragraph becomes just `To change the times, reply to the IT desk.`
  - In `cancelled_body.txt`, when the provider can't start, `…with the same link and start link.` becomes `…with the same link.` (needs G5).
- **P4 — `Keep it` → `Keep the booking` / `Keep the class`.** "It" is ambiguous next to a red button, and naming the thing kept makes the safe choice unmistakable. It's a label only.
- **P5 — Tell the students** (cancellation email, before the request line): `Zoom doesn't tell the people you shared the link with. Please let your students know.` D6 establishes that people with only the join link are never told, so without this line the teacher may assume Zoom told them.
- **P6 — Don't say the same thing twice on the change page.**
  - With no key saved, the `No host key saved` notice and the field help would both show criterion 30's text.
  - **Proposal:** the notice body becomes `Save one below so the IT desk has a fallback if a start link doesn't work.`, and the field help keeps criterion 30's text.
- **P7 — Tell the two links apart in the approval email.** After `Use the same link for every class below.`, add `Share the join link with your students. Keep the start link to yourself.` The email now carries two Zoom-looking links, and a teacher who shares the wrong one gives every student host control.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops (agent plan step 2, criterion 47's setting part, 2026-09-26)

**Files changed**
- `config/settings/base.py`: `IT_DESK_PHONE = env("IT_DESK_PHONE", default="")`, at the end of the "Zoom link requests" block, with a comment giving the reason (the start page's tap-to-call number), that it isn't a secret, what empty means, and that `zoom.E006` checks a non-empty value. This is the only read.
- `.env.example`: `IT_DESK_PHONE=` (empty), after `HOST_KEY_ENCRYPTION_KEYS`, with a comment giving where it shows, that it isn't a secret, what empty does, the example formats `011 234 5678` / `+94 11 234 5678`, and that `manage.py check` reports an unreadable value (`zoom.E006`).
- `compose.yaml`: `web.environment` gains `IT_DESK_PHONE: ${IT_DESK_PHONE:-}` with a one-line comment. `compose.dev.yaml` inherits it (the merged dev config shows `IT_DESK_PHONE: ""`).
- `apps/core/test_it_desk_phone_settings.py` (new, devops-owned platform tests, same pattern as `test_zoom_settings.py`): the `base.py` read with an empty default; a source scan of `apps/` and `config/` that finds no other env read of `IT_DESK_PHONE`; the compose entry; the `.env.example` entry with no value and a comment line above it. The E006 check and the view context aren't tested here; they're the backend's.

**New env var:** `IT_DESK_PHONE`, default `""` (optional, not a secret). The local `.env` wasn't edited.
**Dependency changes:** none. **Migrations:** none. **Contract deviations:** none.
**Nothing else in the plan falls to devops.** D1 says 011 needs no new Zoom scope, so there are no owner-doc scope changes.

**Operational steps for the user:** none required. To show a number, add `IT_DESK_PHONE=011 234 5678` (the real number) to `.env` and recreate `web` (`docker compose up -d`). No rebuild is needed; the image didn't change.

**Handed to `tmd-docs-writer` (plan step 6, already listed):** README env-var table and setup: `IT_DESK_PHONE`, optional, empty by default, e.g. `011 234 5678`.

**Self-check (2026-09-26)**
- `docker compose config --quiet`: OK. `docker compose -f compose.yaml -f compose.dev.yaml config --quiet`: OK.
- Dev container: `ruff check .`: `All checks passed!`. `ruff format --check .`: `101 files already formatted`.
- Dev container: `pytest` (reusing the DB, no `--create-db`): `923 passed in 47.82s`.
- Dev container: `makemigrations --check --dry-run`: `No changes detected`. `manage.py check`: `System check identified no issues (0 silenced).`
- Prod stack (`ZOOM_PROVIDER=manual docker compose up -d --build`, `web` healthy, `/healthz/` 200 on 8010), `docker compose exec -e USE_HTTPS=True web python manage.py check --deploy`:
  - `IT_DESK_PHONE` empty: only `security.W021` and `zoom.W001`, `2 issues (0 silenced)`.
  - `-e "IT_DESK_PHONE=011 234 5678"`: only `security.W021` and `zoom.W001`, `2 issues (0 silenced)`. `settings.IT_DESK_PHONE` read back as `'011 234 5678'`.
  - E006 doesn't exist yet (the backend adds it), so the verifier repeats both runs at step 4.
- The dev stack was running before, and it's restored (`polymath-tmd:dev`, `manage.py check` clean). Only `polymath-tmd` containers were touched, and no volumes were changed.

### tmd-frontend (agent plan step 3b, 2026-09-26)

**Files changed**
- **New templates:** `templates/zoom/cancel_confirm.html` (D.2), `templates/zoom/start.html` (D.5, six states, in `public_base.html`), `templates/zoom/host_key_reveal.html` (D.7, `.secret` plus the pinned P2 guidance), `templates/zoom/email/cancelled_subject.txt` and `cancelled_body.txt` (D.8.2–D.8.3).
- **New partials:**
  - `templates/zoom/partials/class_rows.html` (`class-rows.md`): the `Cancel this class` link with the visually hidden ` on {date}`, the `In progress` tag (`tag--note`, `clock`), and the `Cancelled` tag (`tag--plain`, `slash`) with its note.
  - `templates/zoom/partials/start_heading.html` (D.5.1).
  - `templates/zoom/partials/it_desk_contact.html` (criterion 47's four sentences). It has no trailing newline, and the full stop sits outside the `tel:` `.tap-link`.
- **Changed templates:**
  - `zoom/detail.html`:
    - the cancelled line (`notice--note`);
    - the Booked on, Zoom link and Meeting ID rows for `approved` or `cancelled`. On a cancelled booking the Zoom link is plain text with `For the record only.`, and the Passcode row is left out;
    - the `Start link` row when `start_link` is set;
    - the Classes box through `class_rows.html`;
    - the `Cancel this booking` box (`button--secondary` link, D.1.5's four leads), or `cancel_blocked_message` in a `notice--note`;
    - the approve radios lose the host-key tags and help (criterion 29);
    - the header comment is updated.
  - `zoom/queue.html`: the Cancelled result line, caption and empty state (D.3.2).
  - `zoom/partials/status_tag.html`: `cancelled` shows as `tag--plain` with `slash`.
  - `zoom/account_form.html`:
    - the `none` notice is now `notice--note` / `info` with the P6 body;
    - `Show host key` (`form="host-key-show"`, `key` icon, `aria-describedby`) and its help;
    - the `Last shown to … Shown n time(s) in all.` line;
    - the separate `#host-key-show` form after the main form;
    - the header comment is updated.
  - `zoom/email/approved_body.txt`: rewritten to D.8.1 / criterion 28. There's no `host_key`, and with `start_url` `""` there's no start-link wording.
- **CSS (`static/css/style.css`):**
  - Tokens:
    - 1a: `--red-800`;
    - 1b: `--font-mono` and `--fs-secret`;
    - 1c: `--c-danger`, `--c-danger-hover` and `--c-on-danger`, with no dark override, per `danger-button.md`.
  - Components:
    - 5d: `.button--danger` and its `:hover`;
    - 5n: `.classrows*`;
    - section 5, before 5o: `.secret*`.
  - Section 8:
    - a new `@media (min-width: 1400px)` block for `.classrows--cols`;
    - `.classrows__action { margin-left: 0 }` below 600px.
  - Section 9: `@media print` `.secret__value { visibility: hidden }`.
- **JS:** none. The existing busy-button and error-summary blocks cover the cancel form, the start form and both error notices through `data-*` hooks. The busy block keeps the `video` icon.
- **Python:** none touched.

**Spec deviations (all small; none changes pinned copy)**
1. **Start page, `ended` / `cancelled`:** the `Send a new request` link is a `.tap-link`, so it's 44px on phones (the UI conventions' target size). D.5.3 had a plain `a`.
2. **Cancel confirm, `Classes that stay`:** the note `These have started or finished…` is `p.box__lead`, not `p.text-muted`. The colour is the same, and the lead's bottom margin separates it from the list, because `p` has no margin in the reset.
3. **Spacing uses the existing `.stack` helper, with no new CSS:**
   - the start page's column;
   - the reveal page's steps plus warn notice;
   - the reveal page's `Keep it safe` paragraph plus the back link. So `Back to Change {label}` sits inside the last section rather than after it; the visual order is D.7.1's.
4. **Account form:** `Show host key`, its help and the reveal line share one `div.field`, rendered when either shows. The order is D.6.1's.
5. **Note for tests, not a deviation:** the reveal page's step 2 wraps `Claim host` in `<strong>`, per D.7.1. Its text content is the pinned sentence, but a raw-HTML substring search for `Open Participants and choose Claim host.` won't match, so compare text content.
6. **Suggestion for the designer:** a one-off booking's whole cancel reads `This removes the classes below … at those times` for a single class. That's D.2.1's copy as written, and a singular form could follow.

**Context contract gaps:** none. I checked `apps/zoom/views.py` and `services.py` as they stand now. Every name the templates read is passed with the contract's name:
- the detail's G1/G2 and `start_link`;
- the confirm page's `checks_zoom`, `to_cancel`, `kept` and `cancel_error`;
- every start-page variable, including `token`, `start_error_still` and `it_desk_phone`;
- the three account-page variables;
- `account` and `host_key`;
- the emails' `start_url` and `can_start`.

**Self-check (2026-09-26)**
- **Render check with stub contexts**, in the dev container: a scratch URLconf stood in for the four new URL names while the backend's weren't there yet. `render_to_string` ran with an HTML-balance check on 32 variants:
  - detail: approved weekly, in progress, one-off manual, cancelled, waiting;
  - confirm: whole, one class manual with `cancel_error`, empty reason;
  - queue: Cancelled with rows, and empty;
  - start: every state, with the phone set and empty, and both `start_error` forms;
  - reveal page;
  - account: saved and revealed, saved once, no key but revealed before, add;
  - the approved email both ways, three cancelled-body cases, and the subject.

  Result: `0 problem(s)`. Pinned strings are present verbatim. The manual approved email has no `start link` (case-insensitive) and no `host key`. The cancelled bodies have no join link, passcode or `zoom/start`.
- **Guard rules run standalone** (`apps/core/tests.py`'s rules; pytest wasn't run yet, per the plan):
  - every template opens with `{# #}`;
  - every include ends `only`;
  - no `style="`;
  - no hard-coded `href`/`action`;
  - sprite: no undefined and no unused symbols;
  - no colour literals outside the first `:root`;
  - no px font sizes;
  - every `var(--…)` is defined.
- **HTTP on 8010** (dev stack):
  - `/healthz/` 200;
  - `/zoom/requests/?status=cancelled` 200 with `No cancelled bookings.`;
  - the detail, the approved tab and the account change page return 500 `Unknown column 'zoom_linkrequest.cancelled_at'`. The backend's migration `0006` isn't applied to the dev DB yet, so this isn't a template fault. Re-check them over HTTP after the backend's run.

### tmd-django-backend (agent plan step 3a, 2026-09-26)

**Files changed**
- `apps/zoom/models.py`:
  - `Status.CANCELLED`;
  - `cancelled_at` / `cancelled_by` on `LinkRequest`, and `cancelled_at` / `cancelled_by` / `cancel_reason` on `Occurrence`, with both check constraints;
  - `BOOKED` gains `cancelled_at__isnull=True`;
  - the cancel rules: `class_in_progress`, `cancellable_classes`, `can_cancel_booking`, `cancel_booking_blocked_message`, `status_after_cancel`, and `Occurrence.is_booked` / `can_be_cancelled` / `cancel_blocked_message`;
  - `Occurrence.START_WINDOW_MINUTES`, `start_window()`, `opens_after_other_class()` and `LinkRequest.start_state()`;
  - the criterion 6 copy constants, and criterion 33's stop-booking wording;
  - `QUEUE_TABS`, `tab_counts()` and `for_tab()` gain `cancelled`;
  - `HostKeyReveal`, plus `HostAccount.last_key_reveal()` / `key_reveal_count()`;
  - the permission's new name in `Meta`;
  - the `HostAccount` docstring carries criterion 45's sentence.
- `apps/zoom/errors.py`, `zoom_api.py`: `ZoomMeetingNotFound`, for a 404 with code 3001. It's a `ZoomRejected` subclass whose message is still "Zoom error 3001", and it lets the start page say "isn't in Zoom any more".
- `apps/zoom/validators.py`: `is_zoom_https_url()`, the one https-on-zoom.us rule. `ApproveForm.clean_join_url` and the start redirect both use it now.
- `apps/zoom/providers.py`:
  - `can_start`, `start_url()` and `occurrence_id_for()`;
  - the delete adds `cancel_meeting_reminder=false`;
  - `FakeProvider` gains `start_calls`, `start_error` and `delete_error`.
- `apps/zoom/services.py`:
  - `cancel()`, with `CancelResult` and `cancelled_message()`: the lock order, Zoom inside the transaction, the deadlock retry and the honest messages;
  - the start link: `start_token`, `start_link`, `link_request_from_start_token`, `start_state` and `start_class`, with `StartResult`;
  - `reveal_host_key()` and `NoHostKeySaved`;
  - `it_desk_phone()`;
  - `send_approved_email(request, link_request)`: no host key, and `start_url` is the link or `""`;
  - `send_cancelled_email()`;
  - `approve()` no longer decrypts. `HOST_KEY_UNREADABLE` and `Outcome.HOST_KEY_UNREADABLE` are removed, and `ApproveResult` has no `host_key`.
- `apps/zoom/forms.py`: `CancelForm` (G7's widget, label, help and error); criterion 30's host-key help; the approve form's docstrings lose the host-key words.
- `apps/zoom/checks.py`, `apps.py`: `zoom.E006`, untagged.
- `apps/zoom/views.py`, `urls.py`:
  - new views `CancelBookingView`, `CancelClassView`, `StartClassView` and `HostKeyRevealView`, and the `no_referrer` decorator;
  - the new context on the detail and change pages;
  - `APPROVED_EMAIL_FAILED` and `ACCOUNT_SAVED_NEW_KEY` as criterion 30 sets them;
  - new URLs `zoom:cancel`, `zoom:cancel_class`, `zoom:start` and `zoom:account_host_key`.
- `apps/zoom/migrations/0006_cancel_and_start.py`, `0007_review_permission_name.py`.
- **Tests, new:** `test_cancel_models.py`, `test_cancel_services.py`, `test_cancel_views.py`, `test_cancel_race.py`.
- **Tests, updated deliberately** for the amended copy and behaviour: `conftest.py` (page stubs for the three new templates, and the `booked_on` factory), `test_accounts.py`, `test_models.py`, `test_race.py`, `test_review_fixes.py`, `test_services.py`, `test_views.py`, `test_zoom_api.py`, `test_zoom_approve.py`, `test_zoom_provider.py`.

**Context contract, as implemented.** Every variable in the contract is supplied, with the listed names and types:
- `detail.html`, including G1 and G2;
- `queue.html`;
- `cancel_confirm.html`, including G3 and G4;
- `start.html` (G6): `it_desk_phone` and `start_error_still` are in every state, the invalid one included;
- `account_form.html`: `can_reveal_host_key`, `last_key_reveal` and `key_reveal_count`, also set on the add page as `False` / `None` / `0`;
- `host_key_reveal.html`;
- both emails (G5).

Deviations and interpretations:
- **A cancelled booking's cancel URLs aren't 404.** Criterion 5 says 404 for "a request that isn't approved". Waiting, rejected and unverified requests get 404. A *cancelled* booking instead redirects with criterion 6's message ("That class was already cancelled." or "There are no classes left to cancel in this booking."). With a 404 there, race 16(a)'s loser would get a 404 whenever the winner cancelled the last class.
- **Criterion 14's forced failure is at the commit, not "at the request UPDATE".** Criterion 10 puts every write before the Zoom delete, so the commit is the only step after Zoom has removed it. The test makes `cancel()`'s commit fail once (inside a test transaction, that's its savepoint release). That's where the deadlock retry and the "press Cancel again" path are proved.
- **The race tests use the `committed` fixture, not `transaction=True`,** exactly as 005's and 006's thread tests do: its flush would wipe the `IT desk` group. The effect is the same, real commits on separate connections.
- **Host-key help (criterion 30), matching D.6.2.** On the change page, the new-key field's help is its old instruction followed by criterion 30's sentence:
  - "Leave it empty to keep the saved key. Host keys aren't emailed. …"
  - "Type the 6 to 10 digits … Host keys aren't emailed. …"

  `remove_host_key`'s help keeps only "Tick this if the saved key is wrong and you don't have the new one yet."
- **Unpinned copy added:**
  - `CANCELLING_AT_THE_SAME_MOMENT`, for a lock timeout before anything reached Zoom: "Someone else was changing this booking at the same moment. Nothing was cancelled. Try again."
  - `CancelForm`'s error for a reason over 1000 characters: "Keep the reason to 1000 characters or fewer."
- **Honesty details:**
  - A failed occurrence *lookup* (a GET) is never reported as "may have removed it".
  - If an earlier attempt's delete went through and a later one fails, the message is criterion 14's.
  - With the fake provider, a class with no stored Zoom occurrence ID is cancelled with no delete: `occurrence_id_for` returns `None`, as the MVT plan says.
- `StartClassView` also answers HEAD (as GET), so the walkthrough's `curl -I` sees the headers.

**Migrations:**
- `0006_cancel_and_start`: schema only. Every new column is nullable or blank, and it's reversible.
- `0007_review_permission_name`: data, a `RunPython` with a reverse.

Both were applied on the dev DB, reversed to `0005` and applied again, so the dev stack now has them. That clears the 500s in the frontend's HTTP note above.

**Dependencies and settings:** none new. `IT_DESK_PHONE` is devops's. The backend only reads `settings.IT_DESK_PHONE`, in `checks.py` and `services.py`.

**For the docs writer:** rotating `SECRET_KEY` breaks every start link already emailed, unless the old key is kept in `SECRET_KEY_FALLBACKS`. The token has its own salt (`apps.zoom.start-class`) and no expiry.

**Self-check output (2026-09-26, dev container unless noted)**
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `105 files already formatted`.
- `pytest --create-db`: `1080 passed in 47.94s`. The thread tests (`test_cancel_race.py`, `test_race.py`, `test_zoom_race.py`) also passed 3 more times in a row.
- `makemigrations --check --dry-run`: `No changes detected`.
- `manage.py check` and `check --database default`: `no issues`. With `-e IT_DESK_PHONE=abc`: `zoom.E006`, with the pinned message.
- Prod stack (`ZOOM_PROVIDER=manual docker compose up -d --build`, `web` healthy, `/healthz/` 200 on 8010), `docker compose exec -e USE_HTTPS=True web python manage.py check --deploy`:
  - `IT_DESK_PHONE` empty: only `security.W021` and `zoom.W001` (`2 issues`);
  - `IT_DESK_PHONE=011 234 5678`: only `security.W021` and `zoom.W001` (`2 issues`). `services.it_desk_phone()` read back `{'display': '+94 11 234 5678', 'tel': '+94112345678'}`.
- `curl -I /zoom/start/not-a-token/` on the prod stack: 404, with `Referrer-Policy: no-referrer` and `Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private`.
- The dev stack was running before, and it's restored: `runserver`, `/healthz/` 200, `0006` and `0007` applied.

backend pytest run finished

#### Review round 1 fixes (tmd-django-backend, 2026-09-26)

**Files changed**
- `apps/zoom/views.py`:
  - SF1: `ReviewContextMixin.get_queryset` joins `cancelled_by` (the cancelled-booking notice), and `review_context` loads the classes with `occurrences.select_related("cancelled_by")` (each "Cancelled by …" row).
  - SF2: `CancelBookingView.get_context_data` takes `kept` from `LinkRequest.kept_classes()`.
- `apps/zoom/models.py`:
  - SF2: `LinkRequest.kept_classes(now=None, *, occurrences=None)`, next to `cancellable_classes`. It returns booked classes with `starts_at <= now`, soonest first. It uses `is_booked()`, not the view's old `cancelled_at is None` test. The two give the same answer on the confirm page, because only an approved booking reaches it and every class of an approved booking has an account.
  - Nit: a comment at `Occurrence.START_WINDOW_MINUTES` names `zoom/start.html`, `zoom/detail.html` and `zoom/email/approved_body.txt`, the three templates that type out "30 minutes". I grepped to confirm there are exactly three.
- `apps/zoom/forms.py`, nit: `CANCEL_REASON_MAX_LENGTH = 1000` is now the one constant.
  - `max_length` reads it, and so does `CANCEL_REASON_TOO_LONG`, through an f-string whose text is unchanged.
  - The widget's explicit `maxlength` is dropped. Django's `CharField.widget_attrs` still writes `maxlength="1000"` from `max_length`, so the G7 test passes unchanged.
- `apps/zoom/migrations/0006_cancel_and_start.py`, nit: the docstring now says that reversing it after real cancels has two effects:
  - Who cancelled, when and why are lost.
  - Requests stay in the `cancelled` status, which the reversed code doesn't know. A cancelled class on a booking that's still approved would also look booked again, without its slots.

  It advises a backup first. The change is to the docstring only, so there's no schema change.
- `apps/zoom/tests/test_cancel_views.py`: `test_the_detail_runs_the_same_queries_however_many_classes_were_cancelled`. It runs on the real templates, because the stubs never read `cancelled_by`.
  - With 1 cancelled class and with 4, each cancelled by a different user, the detail page runs the same number of queries.
  - With the whole booking cancelled, it runs no more than that.
  - With the SF1 fix reverted, the test fails (`11 == 8`); with the fix it passes.
- `apps/zoom/tests/test_cancel_models.py`:
  - `test_the_kept_classes_are_the_booked_ones_that_have_started`: 4 moments, one of them with a class in progress and one with a cancelled class. Given the list, the rule runs 0 queries. `kept` and `cancellable` are disjoint, and together they cover every booked class.
  - `test_a_request_that_was_never_booked_keeps_no_classes`.

**Context contract:** unchanged. `kept` on `cancel_confirm.html` is still a list of Occurrence, with the same contents.

**Migrations:** none added. `0006` changed in its docstring only.

**Dependencies and settings:** none.

**Self-check output (dev container)**
- `ruff format .`: `107 files left unchanged`. `ruff check .`: `All checks passed!`. `ruff format --check .`: `107 files already formatted`.
- `pytest --create-db`: `1087 passed, 1 skipped in 63.39s`.
  - The skip is `apps/core/test_gunicorn_access_log.py`, devops's concurrent change: `could not import 'gunicorn'` in the dev image. It isn't from this round.
  - The count is 1081 + 6 new tests.
- `makemigrations --check --dry-run`: `No changes detected`.
- `manage.py check`: `System check identified no issues (0 silenced)`.
- I didn't touch the Dockerfile or the gunicorn config. The dev stack was left running as I found it.

#### Review round 1 nit: start tokens in the access log (tmd-devops, 2026-09-26)

**Files changed**
- `docker/gunicorn.conf.py` (new): sets `logger_class` to `HiddenStartTokenLogger`, a `glogging.Logger` subclass whose `atoms()` replaces `/zoom/start/<anything>` with `/zoom/start/[hidden]/`. That covers the token, the trailing slash and any `?query`. It rewrites every string atom, so the request line, `U`, the Referer (set when the start form posts back) and the environ and header atoms are all covered, and on a start path it empties `q`. It also matches on the percent-decoded text, so `/zoom/st%61rt/<token>/` is hidden too. Every other path is logged unchanged. The module docstring says why.
- `Dockerfile`: the prod `CMD` adds `--config docker/gunicorn.conf.py`, with a comment. Bind address, socket and log targets stay on the `CMD` line.
- `requirements/dev.txt`: `-r prod.txt` in place of `-r base.txt`, so the dev image has gunicorn for the test. `gunicorn==26.2.0` is still pinned once, in `prod.txt`. Its `win32` marker keeps it off the host `.venv`, where the test skips.
- `apps/core/test_gunicorn_access_log.py` (new, 6 tests):
  - the Dockerfile passes the config;
  - the typed prefix still matches `reverse("zoom:start")`;
  - the token, the query and the Referer are hidden, including the percent-encoded path;
  - other paths and queries are logged unchanged.

**New env vars:** none. **Dependencies:** none new. `gunicorn==26.2.0` is now also installed in the dev image. **Migrations:** none.

**Operational steps for the user:** rebuild both images (`docker compose -f compose.yaml -f compose.dev.yaml up -d --build`; prod: `ZOOM_PROVIDER=manual docker compose up -d --build`).

**Proof (prod stack, `ZOOM_PROVIDER=manual`, `web` healthy)**, `docker compose logs web`:
```
"GET /zoom/start/[hidden]/ HTTP/1.1" 404 13443 "-" "curl/8.21.0"
"GET /zoom/start/[hidden]/ HTTP/1.1" 404 13443 "-" "curl/8.21.0"          (was ?next=secret)
"GET /accounts/login/ HTTP/1.1" 200 15020 "-" "curl/8.21.0"
"POST /zoom/start/[hidden]/ HTTP/1.1" 403 1367 "http://127.0.0.1:8010/zoom/start/[hidden]/" "curl/8.21.0"
```

**Found during this work:** Django's own loggers still wrote the raw token path, for example `django.request: Not Found: /zoom/start/<token>/` and `django.security.csrf: Forbidden (CSRF cookie not set.): /zoom/start/<token>/`. The coordinator approved a follow-up, recorded below.

**Self-check**
- `docker compose config --quiet`, both stacks: OK. Both images rebuilt.
- Dev container:
  - `ruff check .`: `All checks passed!`. `ruff format --check .`: `107 files already formatted`.
  - `pytest --reuse-db`: `1093 passed`. The access-log file alone: `6 passed`.
  - `manage.py check`: `no issues`.
- Prod `check --deploy` with `USE_HTTPS=True`: only `security.W021` and `zoom.W001` (`2 issues`). Settings didn't change.
- I didn't run `--create-db`. The dev stack is restored (`polymath-tmd:dev`, `/healthz/` 200), and no volumes were touched.

#### Follow-up (approved by the coordinator): start tokens in Django's logs (tmd-devops, 2026-09-26)

**Files changed**
- `config/settings/log_filters.py` (new; a helper, not a settings module). It is now the one definition of the rule:
  - `HIDDEN_START_PATH`, the prefix regex and `hide_start_token()`, which also matches the percent-decoded form;
  - `HideStartTokenFilter`, a `logging.Filter` that rewrites the merged message (message and args) when it holds a token, and the traceback text (`exc_text`). It keeps every record.

  It lives under `config/settings/` because devops owns that path and gunicorn loads it before Django, so it must not import Django or app code.
- `config/settings/base.py`, `LOGGING`:
  - `filters` adds `hide_start_token`, and it's on every handler: `console`, plus `mail_admins`, Django's default re-declared only to add the filter (it still sends nothing, because `ADMINS` is unset). Filters go on handlers, not loggers, because logger filters miss records that propagate from `django.security.<Name>` child loggers.
  - `loggers.django` now uses `["mail_admins"]` only, and `loggers.django.server` uses `[]` with `propagate: True`. Both reach the filtered root console instead of Django's unfiltered default handlers.
  - Side effects: DEBUG runs no longer print `django.*` lines twice, and runserver's request lines now use the `simple` format (`… INFO django.server: "GET … HTTP/1.1" 200 …`).
- `docker/gunicorn.conf.py`: its own copy of the regex is gone. It now imports `hide_start_token` from `log_filters.py`, after adding the project root to `sys.path` (gunicorn reads the file before it sets up the app's path). Same behaviour.
- `apps/core/test_log_filters.py` (new, 11 tests):
  - a real 404 and a CSRF 403 on the start path, read from the configured console handler (caplog's handler has no filter). Both log `/zoom/start/[hidden]/` and never the token;
  - a normal 404 elsewhere, which still logs its path;
  - the typed prefix equals `reverse("zoom:start")`;
  - the query, the percent-encoded path and the Referer forms;
  - a traceback holding a token;
  - every `LOGGING` handler carries the filter;
  - `django.server` propagates to the filtered console.
- `apps/core/test_gunicorn_access_log.py`: the `reverse()` test moved to the new file, and the docstring points there.

**New env vars / dependencies / migrations:** none.

**Operational steps for the user:** rebuild both images, as above.

**Proof (prod stack, `ZOOM_PROVIDER=manual`, `web` healthy)**, `docker compose logs web` for these requests:
- `/zoom/start/abc.def/`
- the same path with `?next=secret`
- `/zoom/st%61rt/abc.def/`
- `/accounts/login/`
- `/no-such-page/`
- a POST to the start path with a Referer

```
WARNING django.request: Not Found: /zoom/start/[hidden]/                       (x3, one per start form)
"GET /zoom/start/[hidden]/ HTTP/1.1" 404 13443 "-" "curl/8.21.0"              (x3)
"GET /accounts/login/ HTTP/1.1" 200 15020 "-" "curl/8.21.0"
WARNING django.request: Not Found: /no-such-page/
"GET /no-such-page/ HTTP/1.1" 404 179 "-" "curl/8.21.0"
WARNING django.security.csrf: Forbidden (CSRF cookie not set.): /zoom/start/[hidden]/
"POST /zoom/start/[hidden]/ HTTP/1.1" 403 1367 "http://127.0.0.1:8010/zoom/start/[hidden]/" "curl/8.21.0"
```
`grep -c abc.def` over the same log window: `0`.

On the dev stack, runserver logs `WARNING django.server: "GET /zoom/start/[hidden]/ HTTP/1.1" 404`.

**Remaining caveat (for the docs writer / R-list):** if `ADMINS` is ever set, the 500 email body is built by Django's `ExceptionReporter` from `record.request` and the frame locals. The filter redacts the subject but not that body, so the email could carry the token. It's inert today, because `ADMINS` isn't set anywhere.

**Self-check**
- `docker compose config --quiet`, both stacks: OK. Prod and dev images rebuilt.
- Dev container:
  - `ruff check .`: `All checks passed!`. `ruff format --check .`: `109 files already formatted`.
  - `pytest --reuse-db`: `1103 passed`.
  - `makemigrations --check --dry-run`: `No changes detected`.
  - `manage.py check`: `no issues`.
- Prod `check --deploy` with `USE_HTTPS=True`: only `security.W021` and `zoom.W001` (`2 issues (0 silenced)`).
- The dev stack is restored (`polymath-tmd:dev`, `/healthz/` 200). Only `polymath-tmd` containers were touched, and no volumes were changed.

#### Review round 2 fixes (tmd-devops, 2026-09-26)

**Files changed**
- **Should-fix 1, the filter can crash the caller:** in `HideStartTokenFilter.filter()`, the `getMessage()`, `formatException()` and redaction steps now run inside `try/except Exception` and write to locals only. On any failure the filter returns `True` and leaves the record untouched, so `emit()` reports it through `handleError` ("--- Logging error ---") as before. The docstring says why.
  - New test in `apps/core/test_log_filters.py`: `test_a_malformed_log_call_does_not_raise_into_the_caller`. It sends a `"%s %s"` record with one arg through the configured console handler, and checks that nothing is raised, that the record is unchanged, and that `--- Logging error ---` appears on stderr.
  - With the `except` disabled, it fails: `TypeError: not enough arguments for format string`. With the fix it passes.
- **Nit, the module's location:** it moved from `config/settings/log_filters.py` to `config/log_filters.py`. Updated: `LOGGING`'s `"()"` path in `base.py`, the import and docstring in `docker/gunicorn.conf.py`, and the import and docstring in `apps/core/test_log_filters.py`. The `sys.path` line in the gunicorn config is unchanged, because it already adds the project root, which is what `config.log_filters` needs.
- **Nit, the ADMINS comment:** the comment above `mail_admins` in `base.py` now says: don't set `ADMINS` without first revisiting the start-token redaction of email bodies, because the 500 email body (the request and the view's local variables) can hold a working start link.

**New env vars / dependencies / migrations:** none. **Operational steps:** rebuild both images, as before.

**Self-check**
- Dev container:
  - `ruff check .`: `All checks passed!`. `ruff format --check .`: `109 files already formatted`.
  - `pytest --reuse-db`: `1104 passed`.
  - `makemigrations --check --dry-run`: `No changes detected`.
  - `manage.py check`: `no issues`.
- `docker compose config --quiet`, both stacks: OK.
- Prod stack (`ZOOM_PROVIDER=manual`, rebuilt, `web` healthy):
  - `check --deploy` with `USE_HTTPS=True`: `2 issues`, the accepted `security.W021` and `zoom.W001`;
  - the log shows `django.request: Not Found: /zoom/start/[hidden]/`, `django.security.csrf: Forbidden (CSRF cookie not set.): /zoom/start/[hidden]/`, the access lines `GET` and `POST /zoom/start/[hidden]/`, and `"GET /accounts/login/ HTTP/1.1" 200`;
  - `abc.def` occurrences: `0`.
- The dev stack is restored (`polymath-tmd:dev`, `/healthz/` 200).

## Verification
<!-- owner: tmd-test-verifier -->

**Verdict: PASS**, subject to two notes: (a) the two backend interpretation deviations below are judged compliant, but worth the reviewer's eyes; (b) criterion 39 (the owner's live check with a real paid Zoom account) is explicitly out of scope for this pass and stays pending.

### Judged interpretation deviations

1. **Criterion 5 vs criterion 16(a): a cancelled booking's cancel URLs redirect, not 404.** The brief has a genuine internal tension: criterion 5 says 404 for "a request that isn't approved" (a literal reading includes `cancelled`), but criterion 16(a) requires the loser of a same-class race to see the friendly `That class was already cancelled.` message, not a 404, and that race's winning commit can flip the request's own status to `cancelled`. The backend resolved this by 404-ing only `unverified`/`waiting`/`rejected` requests and classes belonging to another request, and redirecting a `cancelled` request with criterion 6's message instead. Verified: `test_the_cancel_pages_are_404_where_there_is_nothing_of_that_kind` 404s `waiting` and `rejected` only; `test_cancel_race.py::test_a_whole_cancel_and_a_class_cancel_at_once` and the manual race repro below both show the graceful message, never a 404. **Judgment: compliant** — favouring the explicit, testable race requirement over an ambiguous literal reading is sound, permission and 404-for-truly-wrong-kind are both still enforced, and the deviation is honestly disclosed. Flagging for the code reviewer / planner to confirm intent, not a defect.
2. **Criterion 14's forced failure is at the commit, not "at the request UPDATE".** Criterion 10's fixed order (every write, then the Zoom `DELETE`, then commit) makes the literal criterion-14 instruction impossible — the request `UPDATE` happens *before* the Zoom delete, never after. The backend's test (`test_a_deadlock_after_zoom_removed_it_is_retried_and_the_retry_finishes`, `test_any_other_failure_after_zoom_removed_it_says_press_cancel_again`) fails the transaction's savepoint commit instead, which is the only step left after Zoom answers. **Judgment: compliant**, and the only coherent way to test "saving fails after Zoom removed it" given criterion 10's order.
3. **Two unpinned messages** (`CANCELLING_AT_THE_SAME_MOMENT`, `CancelForm`'s over-1000-characters error): both are new copy for edge cases the criteria don't pin verbatim. Both are now asserted by name/text in tests — the first already was (`test_a_lock_race_before_zoom_says_nothing_was_cancelled`), the second was missing an exact-text assertion so I added `test_a_reason_over_1000_characters_names_the_limit` (see Tests added). **Judgment: compliant**, no pinned-copy rule broken.

### Acceptance criteria (47)

| # | Verdict | Evidence |
|---|---|---|
| 1 | ✅ | `test_the_cancelled_status_and_fields_exist`, `test_a_cancelled_request_must_have_been_booked_and_say_when`, `test_a_cancelled_class_must_say_why` (raw-`UPDATE` `IntegrityError` per constraint) |
| 2 | ✅ | `test_a_cancelled_class_is_not_booked_and_frees_the_account`; live: cancelling one class of ZL-0612 freed it from the timetable (verified `/zoom/timetable/?month=2026-10` no longer lists it) while the booking's other classes stayed |
| 3 | ✅ | `test_the_cancel_rules_of_zl42_at_three_moments` (table test matches the brief's cases exactly), `test_after_cancelling_the_seven_left_on_tuesday_the_booking_is_cancelled`, `test_after_cancelling_one_class_the_booking_stays_approved`, `test_a_request_that_is_not_approved_is_never_cancellable` |
| 4 | ✅ | `test_cancelling_a_booking_never_changes_a_class_that_has_started` |
| 5 | ✅* | `test_the_cancel_pages_are_404_where_there_is_nothing_of_that_kind`, `test_cancelling_needs_the_review_permission` (sign-in redirect, then 403); live: anonymous → login redirect confirmed with a valid CSRF token; unknown-pk equivalents 404. *See deviation 1 above for the cancelled-booking sub-case. |
| 6 | ✅ | `test_nothing_to_do_goes_back_to_the_detail_with_one_message`; live: exact pinned messages reproduced |
| 7 | ✅ | `test_the_cancel_form_sets_its_own_widget_label_help_and_error`; live: confirm page shows `rows="4"`, `maxlength="1000"`, label, help, danger button text and `Keep the class`/`Keep the booking` verbatim (screenshots) |
| 8 | ✅ | `test_the_detail_of_an_approved_weekly_booking`, `test_the_detail_while_a_class_is_in_progress`, `test_the_detail_of_a_cancelled_booking`; live: detail page for ZL-0612 showed `Cancelled` tags, `Cancelled by … on …: reason`, the cancelled-booking notice, and `Booked on`/`Zoom link`/`Meeting ID` retained (screenshot) |
| 9 | ✅ | `test_the_queue_has_a_cancelled_tab_counted_in_one_query`, `test_the_cancelled_tab`; live: `/zoom/requests/?status=cancelled` showed `1 cancelled booking.`, correct caption and `tag--plain`/`slash` |
| 10 | ✅ | `test_the_cancel_views_run_outside_the_request_transaction`; the ordered-log test is in `test_cancel_services.py` (lock → writes → one delete → commit, asserted via the same `responses`/`connection.execute_wrapper` pattern as 006) |
| 11 | ✅ | `test_a_whole_weekly_booking_is_one_delete_of_the_meeting`, `test_one_class_is_a_delete_of_its_occurrence`, `test_a_class_with_no_stored_occurrence_id_is_looked_up_first`, `test_a_class_zoom_no_longer_has_is_cancelled_with_no_delete`, `test_a_delete_answered_no_such_meeting_counts_as_done` |
| 12 | ✅ | `test_zoom_said_no_rolls_everything_back_with_one_message_per_kind`; live: manual-provider "Delete it in Zoom too" notice confirmed |
| 13 | ✅ | `test_zoom_may_have_done_it_rolls_back_and_says_so` |
| 14 | ✅* | see deviation 2; `test_a_deadlock_after_zoom_removed_it_is_retried_and_the_retry_finishes`, `test_any_other_failure_after_zoom_removed_it_says_press_cancel_again` (one `ERROR` record, exact text) |
| 15 | ✅ | `test_cancelling_a_whole_booking_redirects_with_the_message_and_emails`, `test_cancelling_one_class_names_its_date`, `test_an_email_failure_keeps_the_cancel_and_warns`, `test_the_manual_provider_adds_delete_it_in_zoom_too`; live: exact messages reproduced for both whole-booking and one-class cancels under the manual provider |
| 16 | ✅ | `test_cancel_race.py` (a, b, c) — run once in the full suite, then 3 additional standalone runs with no flakiness (15/15 passed each time) |
| 17 | ✅ | `test_the_cancellation_email_for_one_class`, `test_the_cancellation_email_for_a_whole_booking_has_no_still_on_line`, `test_the_cancellation_email_with_the_manual_provider_mentions_no_start_link`, `test_no_email_of_the_whole_flow_carries_a_host_key`; live: real cancellation email captured from the console log for ZL-0613, byte-for-byte matching D.8.3 (subject, class lines, `Reason:`, "still on" line, P5 line, request URL; no join link/passcode/start link/host key) |
| 18 | ✅ | `test_which_providers_can_start`, `test_the_zoom_provider_returns_zooms_start_url`, `test_a_start_url_that_isnt_https_on_zoom_us_is_refused` |
| 19 | ✅ | `test_a_start_token_names_its_booking`, `test_a_cancelled_bookings_token_still_opens_its_page`, `test_invalid_start_tokens` |
| 20 | ✅ | `test_the_start_window` (table test matches the brief's 5 cases) |
| 21 | ✅ | `test_the_start_state`, `test_the_start_state_of_a_one_off_at_its_end_is_ended`, `test_the_start_state_skips_cancelled_classes_and_knows_a_cancelled_booking`; live: `ready`/`too_early`/`ended` all reproduced with real (unfrozen) time on the dev+fake stack |
| 22 | ✅ | `test_the_start_page_shows_each_state_without_asking_zoom`, `test_an_invalid_start_link_is_a_404_page`; live: invalid token → 404 with pinned text; `no-store`/`no-referrer` present on every GET response checked, including the invalid-token 404 |
| 23 | ✅ | `test_pressing_start_in_the_window_redirects_to_zoom`, `test_pressing_start_too_early_calls_nothing`, `test_a_failed_start_rerenders_with_the_message`, `test_pressing_start_needs_a_csrf_token`; live: POST on `ready` redirected 302 to the fake `start_url` with `no-store`/`no-referrer`; POST with no CSRF token → Django's 403 (note: that 403 is emitted by `CsrfViewMiddleware` before `StartClassView.dispatch()` runs, so it doesn't itself carry the view's `no-store`/`no-referrer` headers — the backend's own test for this case doesn't assert headers either, which is the correct scope) |
| 24 | ✅ | `test_the_start_url_is_never_kept_anywhere` (backend, mocked); live: the real fake `start_url` (`https://zoom.example.invalid/s/…`) never appeared anywhere in `docker compose logs web` across the whole session |
| 25 | ✅ | `test_starting_a_ready_class_asks_zoom_once_and_logs_the_use`, `test_a_failed_start_says_what_to_do_and_logs_a_warning`; live: log line `Start link used for ZL-0615, class Sat 26 Sep 2026 1:10 pm, from 172.23.0.1` — reference, class, IP only, no token/URL |
| 26 | ✅ | `test_the_manual_provider_is_not_set_up`, `test_the_manual_provider_is_not_set_up_and_calls_nothing`; live: manual provider showed `Starting a class from a link isn't set up yet.` with facts and no form, for both an approved and a cancelled request (provider gate takes priority, confirmed live) |
| 27 | ✅ | `test_an_account_whose_stored_key_cant_be_decrypted...` (in `test_zoom_approve.py`, updated deliberately) confirms `approve()` no longer decrypts; grep confirms `HOST_KEY_UNREADABLE`/`Outcome.HOST_KEY_UNREADABLE` removed |
| 28 | ✅ | `test_no_email_of_the_whole_flow_carries_a_host_key`; live: real approval email for ZL-0613 (manual provider) matched the manual branch of D.8.1 exactly — no host key, no start-link block, `Ask the IT desk how to start the class as host.`, shortened last paragraph |
| 29 | ✅ | live: fetched the waiting-request detail page's approve form HTML — no `Host key saved`/`No host key saved` tags, no "email will ask" help text |
| 30 | ✅ | `test_no_old_host_key_email_copy_is_left`; live: `No host key saved` notice is `notice--note`/`info` with the exact P6 text, distinct from the field help |
| 31 | ✅ | live: on the manual-provider account tested, no `Start link` row shows on the detail page (correct, `can_start` false); the row's markup/help text is otherwise present and pinned in `zoom/detail.html` (frontend template review) — not independently exercised against the `zoom`/`fake` provider over HTTP in this pass, but covered by backend context tests |
| 32 | ✅ | `test_the_review_permission_has_its_new_name_and_the_migration_reverses` |
| 33 | ✅ | grep of `apps/zoom` confirms both amended stop-booking sentences end "…or been cancelled." / "…has finished or been cancelled." |
| 34 | ✅ | reviewed `views.py`: `CancelBookingView`/`CancelClassView`/`StartClassView`/`HostKeyRevealView` all parse → call a service/model method → choose template → respond, no business logic in the view bodies |
| 35 | ✅ | `test_css_colour_literals_live_only_in_the_root_palette_block`, `test_icon_sprite_appears_exactly_once_on_rendered_pages`, `test_every_static_reference_in_templates_exists` all pass; live screenshots at 1440 and (500, see note) show the danger button, class rows and secret value rendering as designed with no visible overflow |
| 36 | ✅ | `test_an_unregistered_zoom_call_never_leaves_the_machine` passes; `FakeProvider.start_error`/`start_calls` exist and are used by the backend's own tests |
| 37 | ✅ | see Checklist below — all five checks reproduced independently by the verifier, including the three `IT_DESK_PHONE` × `check --deploy` combinations |
| 38 | ✅ | full walkthrough reproduced live (see Checklist/prod walkthrough below): cancel one class, cancel the rest, Cancelled tab, `not_set_up` start page with `curl -I` headers, hashed static paths (`theme-init.23a9a55193e6.js`) |
| 39 | ⏳ pending | owner's live check with a real paid Zoom account — explicitly out of scope for this pass per the task instructions ("leave the owner's live-check items pending") |
| 40 | ✅ | `test_a_reveal_record_holds_no_key`; model has no key/hash field (source review) |
| 41 | ✅ | `test_the_reveal_is_for_the_it_desk_only`, `test_the_reveal_needs_a_csrf_token`, `test_revealing_a_key_shows_it_and_records_who`, `test_revealing_when_no_key_is_saved`, `test_revealing_an_unreadable_key`; live: full flow reproduced — POST with valid CSRF (IT user) → 200 with the key and `no-store`/`no-referrer`; anonymous with valid CSRF → sign-in redirect; `view_hostaccount`-only user → 403 (Django's own 403 page, confirming a real permission denial, not a CSRF artifact); unknown pk → 404; GET → 405; no-key account → redirect with the exact flash text |
| 42 | ✅ | `test_revealing_a_key_shows_it_and_records_who`; live screenshot of the reveal page shows the pinned headings, three numbered steps (`Claim host` correctly wrapped in `<strong>`, text content matches the pinned sentence), the warn notice, and "Keep it safe", byte-for-byte |
| 43 | ✅ | `test_the_key_is_on_the_reveal_page_and_nowhere_else`, `test_an_error_after_decryption_in_the_view_masks_the_key`; live: the dummy key `123456` never appeared in `docker compose logs web`, nor on the account change page after a reveal |
| 44 | ✅ | `test_the_change_page_offers_the_reveal_and_says_who_looked`, `test_the_reveal_is_not_offered_without_a_readable_key_or_on_add`, `test_the_reveal_count_shows_even_after_the_key_is_removed`; live: change page showed `Last shown to it.verify011 on Sat 26 Sep 2026, 12:57 pm. Shown 1 time in all.` after one reveal |
| 45 | ✅ | `test_the_account_docstring_states_the_amended_rule` |
| 46 | ✅ | live, reproduced exactly as specified: `Show host key` showed `123456`; `curl`'s response headers showed `no-store` and `no-referrer` on the reveal POST; the change page then showed the reveal line; a `view_hostaccount`-only user got 403; `docker compose logs web` contained the `shown to` line and zero occurrences of `123456` |
| 47 | ✅ | `test_the_it_desk_phone`, `test_check_e006_refuses_a_phone_number_it_cant_read`, `test_check_e006_runs_with_manage_py_check`, `test_the_window_opens_after_the_class_before_on_the_same_account`; live: `check --deploy` with `IT_DESK_PHONE` empty/set both showed only W021+W001; `abc` produced `zoom.E006` with the pinned message; the four contact-sentence combinations (still/plain × set/empty) reproduced verbatim with the correct `tel:` `href` and `.tap-link` class |

### Checklist ("Verify a change")

- `ruff check .` ✅ `All checks passed!`
- `ruff format --check .` ✅ `105 files already formatted`
- `pytest --create-db` ✅ run twice: `1080 passed` (before my added test), `1081 passed` (after). Race/thread modules (`test_cancel_race.py`, `test_race.py`, `test_zoom_race.py`) run 3 further times standalone: `15 passed` every time, no flakiness.
- `makemigrations --check --dry-run` ✅ `No changes detected`
- `manage.py check` ✅ and `check --database default` ✅ both `System check identified no issues`
- `check --deploy` on prod, `USE_HTTPS=True`, `ZOOM_PROVIDER=manual` ✅:
  - `IT_DESK_PHONE` empty: `security.W021`, `zoom.W001` only (2 issues)
  - `IT_DESK_PHONE=011 234 5678`: same 2 issues only
  - `IT_DESK_PHONE=abc`: `zoom.E006` (pinned message) plus the same 2 warnings
- Prod walkthrough over HTTP on 8010 ✅ (see below)
- Dev+fake walkthrough for `ready`/`too_early`/`ended` states ✅ (see below)

**Prod walkthrough evidence (manual provider, throwaway data, all cleaned up afterwards):**
- Cancelled one class of a test weekly booking (`Cancel this class` on Wed 7 Oct) → flash `Cancelled the class on Wed 7 Oct 2026. We emailed … This system can't reach Zoom: delete it in Zoom too.`, class shows `Cancelled` tag and `Cancelled by … on …: reason`.
- Cancelled the rest of the booking → flash `Cancelled the booking. We emailed … This system can't reach Zoom: delete it in Zoom too.`, `This booking was cancelled by … on … It was approved by … on …` notice, `Zoom link` becomes plain text with `For the record only.`, `Passcode` row gone, `Booked on` loses its timetable link.
- Cancelled tab: `/zoom/requests/?status=cancelled` → `1 cancelled booking.`, correct caption, `Cancelled` tag.
- Timetable: the fully-cancelled booking no longer appears on `/zoom/timetable/?month=2026-10`; a still-booked one-off on the same account still does.
- Start link states reachable under `manual`: `invalid` (garbage token, 404, pinned text), `not_set_up` (valid token on both an approved and a cancelled request — provider gate wins), all with the class facts shown per G6.
- Headers: `no-store`/`no-referrer` confirmed on every start-page response checked (GET valid token, GET invalid token/404, reveal POST, reveal error redirects).
- Host key: `Show host key` on a dummy-key (`123456`) test account showed the key on the reveal page only; change page then showed `Last shown to … Shown 1 time in all.`; `view_hostaccount`-only user got 403; log contained no `123456`.
- Approval and cancellation emails read from the console log for a real approve→cancel flow on a manual-provider test account — matched D.8.1/D.8.3 exactly, no secrets leaked.
- Static files served from hashed paths (`theme-init.23a9a55193e6.js` etc.).

**Dev+fake walkthrough:** approved three throwaway one-off bookings timed against real (unfrozen) clock time to reach `ready`, `too_early` and `ended` naturally. `ready`'s POST redirected (302) to the fake provider's `https://zoom.example.invalid/s/…` URL with `no-store`/`no-referrer`; the usage was logged with reference/class/IP only.

### Tests added

- `apps/zoom/tests/test_cancel_views.py::test_a_reason_over_1000_characters_names_the_limit` — the only coverage gap found: the over-1000-character `CancelForm` error was checked for failing validation, but its exact pinned-in-implementation-notes text (`Keep the reason to 1000 characters or fewer.`) wasn't asserted anywhere.

No other tests were missing: the backend's `test_cancel_models.py` (21 tests), `test_cancel_services.py` (37 tests), `test_cancel_views.py` (42 tests, now 43), and `test_cancel_race.py` (6 tests) between them map to every criterion above.

### A note on 400px screenshots

Headless Edge (both legacy and `--headless=new`) has a reproducible minimum-content-width quirk on this machine: pages requested at exactly `--window-size=400,…` render with content laid out wider than 400 CSS px and the PNG crops rather than reflows, visibly cutting text — confirmed as a **tooling artifact, not a product bug**, by: (a) a trivial static HTML page wraps correctly at exactly 400px with the same tool/flags; (b) the identical app pages render with clean wrapping and no overflow at 500px with room to spare; (c) 1440px screenshots are correct throughout. Narrow-width screenshots below are therefore taken at 500px (still below the app's 600px facts-stacking breakpoint) rather than 400px. This is a limitation of my screenshot tooling in this session, not a finding about the product; it should not block the verdict, but a future verifier should use a tool that handles sub-500px viewports if a true 400px screenshot is required.

**Screenshots taken** (in the scratchpad, `shots/`, 1440px and 500px unless noted):
- `cancel_confirm_whole_1440.png` / `_500.png` — whole-booking cancel confirm page
- `cancel_confirm_class_1440.png` / `_500.png` — one-class cancel confirm page
- `detail_cancelled_1440.png` / `_500.png` — request detail, fully cancelled booking
- `host_key_reveal_1440.png` / `_500.png` — the host-key reveal page
- `start_ready_1440.png` / `_500.png`, `start_too_early_1440.png` / `start_tooearly_500.png`, `start_ended_1440.png` / `_500.png` — dev+fake stack, real clock time
- `start_not_set_up_1440.png` / `_400.png`, `start_invalid_1440.png` / `_400.png` — prod stack (these two rendered correctly even at literal 400px, likely because the public frame's content is short enough not to trip the tooling quirk)

### Cleanup

- All throwaway `LinkRequest`s (`Verify 011 Weekly`, `Verify 011 OneOff`, `Verify 011 Approve Flow`, `Live Ready`, `Live Ended`, `Live TooEarly`), `HostAccount`s (`Verify 011`, `Verify 011 NoKey`, `Verify 011 Live`, `Verify 011 Ended`, `Verify 011 TooEarly`) and users (`it.verify011`, `view.verify011`, `verifier011`) deleted from the dev DB; confirmed zero remaining afterwards.
- The one extra session row the frontend's HTTP self-check created today for the first superuser (`srimal`, pk 25 — the only one of that user's 5 sessions created 2026-09-26 rather than 2026-09-25) deleted; the user account itself was untouched.
- No volumes were touched (`down -v` never used). Only `polymath-tmd` project containers were touched.
- Stack restored to the dev overlay that was running at the start (`polymath-tmd:dev`, `/healthz/` → 200, `manage.py check` clean).

### Re-verification (round 1 fixes)

**Verdict: PASS.** Re-run after the backend's round 1 fixes (SF1, SF2, the three nits) and devops's two follow-ups (the gunicorn access-log filter, then the `LOGGING`-wide `log_filters.py` filter). Criterion 39 (the owner's live check on a real paid Zoom account) remains explicitly out of scope for this pass and stays pending, as in round 1.

**Checklist ("Verify a change"), all reproduced independently:**

- `ruff check .` ✅ `All checks passed!`
- `ruff format --check .` ✅ `109 files already formatted`
- `pytest --create-db` ✅ run twice, both times **`1103 passed`**, 0 skipped, 0 failed. Matches devops's reported figure exactly.
- `makemigrations --check --dry-run` ✅ `No changes detected`
- `manage.py check` ✅ `System check identified no issues (0 silenced).`
- `check --deploy` on the prod stack, `USE_HTTPS=True`, `ZOOM_PROVIDER=manual` (settings changed — `LOGGING`) ✅, all three `IT_DESK_PHONE` variants:
  - empty: `security.W021`, `zoom.W001` only (2 issues)
  - `011 234 5678`: same 2 issues only
  - `abc`: `zoom.E006` (pinned message) plus the same 2 warnings

**SF1 and SF2 shown to fail on the pre-fix code (spot-check with a temporary revert, restored, confirmed with `git diff`):**

- **SF1** (`ReviewContextMixin.get_queryset` / `review_context` missing `select_related("cancelled_by")`): reverted both call sites in `apps/zoom/views.py` to drop the join, ran `test_the_detail_runs_the_same_queries_however_many_classes_were_cancelled` alone — failed with `assert 11 == 8` (identical to the backend's own figures). Restored the two call sites verbatim; the test passed again, and `test_cancel_models.py` + `test_cancel_views.py` together passed clean (90 tests) on a fresh run.
- **SF2** (`LinkRequest.kept_classes`): temporarily renamed the model method in `apps/zoom/models.py` so the view's caller couldn't find it — `test_the_kept_classes_are_the_booked_ones_that_have_started` (all 4 parametrisations) and `test_a_request_that_was_never_booked_keeps_no_classes` failed with `AttributeError: 'LinkRequest' object has no attribute 'kept_classes'`. Restored the method verbatim; both tests passed again.
- After both reverts were undone, `git diff --stat -- apps/zoom/models.py apps/zoom/views.py` showed the same totals as before the spot-check (356 / 313 lines changed from the pre-011 baseline), and a grep for the temporary marker names found nothing left behind.
- **One non-reproducible blip, noted for the record, not held against the verdict:** immediately after restoring the SF1 code (mid live-edit of the two files), a single combined run of `test_cancel_models.py test_cancel_views.py` showed one unrelated failure, `test_the_start_page_shows_each_state_without_asking_zoom[moment2-ended-...]`. It is not a thread/race test, so the brief's "never a skip" rule for flaky *thread* tests doesn't strictly apply, but it was investigated anyway: run alone it passed, and three subsequent full reruns of both files (90 tests each) all passed clean with no failures. The most likely cause is a transient artifact of editing the source files live in the same window pytest was invoked (a stale bytecode read on the bind-mounted dev container), not a genuine flake in the feature — the two official `--create-db` runs earlier in this session (1103/1103, no failures) already prove the untouched code is stable.

**Log verification on the prod stack (`ZOOM_PROVIDER=manual`), token-hiding (devops's two follow-ups):**

- Built a real approved one-off booking directly in the database (dummy key, `starts_at` 5 minutes in the past / `ends_at` 25 minutes ahead, so the window is open) and took its real signed start token via `services.start_token()`.
- **On the dev stack (fake provider, so the state is genuinely `ready`):** GET the token → 200 with the start form; POST with a valid CSRF token → 302 to the fake `start_url` (`https://zoom.example.invalid/s/81234599999`) with `Referrer-Policy: no-referrer` and `Cache-Control: … no-store …`; POST with no CSRF token → 403. `docker compose -f compose.yaml -f compose.dev.yaml logs web` showed each request logged exactly once, as `/zoom/start/[hidden]/`, including the `Start link used for ZL-0621, class Sat 26 Sep 2026 2:12 pm, from 172.23.0.1` service log line (reference, class, IP only) and the `django.server` request lines. `grep -c` for the raw token payload and for `zoom.example.invalid` over the whole dev log: **0** both times.
- **On the prod stack (manual provider, same underlying database — the volume is shared between overlays):** GET the same valid token → 200, `not_set_up` copy (provider gate wins, as criterion 26 requires); POST with no CSRF → 403; GET a garbage token → 404. `docker compose logs web` (gunicorn access log **and** Django's own `django.request` / `django.security.csrf` lines) showed `/zoom/start/[hidden]/` throughout, including on the CSRF-forbidden line and the Referer header of the 403 access-log entry. `grep -c` for the token payload over the whole prod log window: **0**. A normal path (`GET /healthz/`) still logged normally (5 hits) — the filter isn't swallowing ordinary traffic.

**Dev logging still works normally (no doubling):** the runserver output for the GET/POST/CSRF-fail sequence above showed exactly one `django.server` line per request (200, then 302, then 403), each correctly leveled (`INFO`/`INFO`/`WARNING`), with no duplicate lines and no un-filtered second copy — confirming the `Implementation notes` claim that moving `django`'s loggers off their default handlers removed the old double-print, without losing any dev-time visibility.

**Detail page re-walked with several cancelled classes, and the confirm page (prod stack, manual provider, throwaway data):**

- Built a weekly booking (Zoom-account-approved, 8 classes, Mon/Wed 5–28 Oct 2026) and cancelled 3 of its 8 classes as two different IT users, then logged in over HTTP as a throwaway superuser and fetched the real (non-stub) detail page.
- Confirmed: `Classes (8)` with 5 live `Cancel this class` links (each carrying the visually-hidden `on {date}` suffix) and 3 `classrows__item--cancelled` rows, each with `Cancelled` (`tag--plain`, `slash`) and `Cancelled by {user} on {when}: {reason}` naming the correct canceller and reason per class; the `Cancel this booking` box showing the manual-provider four-case lead text; `Booked on` / `Zoom link` / `Meeting ID` / `Passcode` all present (still `approved`); no `Start link` row (manual provider, `can_start` false).
- Fetched the whole-booking cancel confirm page (GET): `Classes to cancel (5)`, no `Classes that stay` section (none held/in-progress), the manual-provider lead and `Delete it in Zoom too` notice, the danger button and `Keep the booking` link, all byte-for-byte matching D.2.1/D.2.2.
- Submitted the cancel (POST, real CSRF token from the page) → 302 to the detail page with the flash `Cancelled the booking. We emailed verify011rw@example.com. This system can't reach Zoom: delete it in Zoom too.` The re-fetched detail page then showed: the `notice--note` line `This booking was cancelled by … on … It was approved by … on …`; `Zoom link` as plain text followed by `For the record only.`; `Meeting ID` retained; `Passcode` and `Start link` both gone; `Booked on` with no `See it on the timetable` link; all 8 classes now `classrows__item--cancelled`.
- Confirmed the Cancelled tab: `/zoom/requests/?status=cancelled` → `1 cancelled booking.`

**Cleanup:** all throwaway `LinkRequest`s (pks 621, 622, plus their 9 occurrences), `HostAccount`s (`Verify011R Round1`, `Verify011R Weekly`) and users (`it.verify011r`, `it.verify011round1`, `it.verify011round1b`) deleted from the database (shared by both overlays); a post-delete count confirmed zero remaining. No `down -v` used, no volumes touched. Only `polymath-tmd` project containers were touched throughout (dev → prod → dev). Stack restored to the dev overlay that was running before this pass started: `docker compose -f compose.yaml -f compose.dev.yaml up -d`, `manage.py check` clean, `/healthz/` → 200.

**Tests added:** none. Round 1's coverage gap (`test_a_reason_over_1000_characters_names_the_limit`) is already in the tree from the previous pass; this pass found no further gap.

**Failures:** none.

### Re-verification (round 2 fix)

**Verdict: PASS.** Scoped re-check of devops's round-2 should-fix (the log filter is now fail-safe) plus its two nits (module moved to `config/log_filters.py`; an `ADMINS` caveat comment added). Criterion 39 (the owner's live check on a real paid Zoom account) remains pending, unchanged from rounds 1 and 2.

- `ruff check .` ✅ `All checks passed!`. `ruff format --check .` ✅ `109 files already formatted`.
- `pytest --create-db` ✅ run twice, both times **`1104 passed`**, 0 skipped, 0 failed — matches devops's reported figure exactly.
- `makemigrations --check --dry-run` ✅ `No changes detected`.
- `manage.py check` ✅ `System check identified no issues (0 silenced).`
- `check --deploy` on the prod stack (`ZOOM_PROVIDER=manual`, rebuilt, `web` healthy), `USE_HTTPS=True`: only `security.W021` and `zoom.W001`, both with `IT_DESK_PHONE` empty and with it set to `011 234 5678`.
- **The fail-safe, shown to matter:** temporarily replaced `HideStartTokenFilter.filter()`'s `try/except Exception: return True` with a no-op `if True:` (source in the conversation record) in `config/log_filters.py`, restarted the dev container the source is bind-mounted into, and ran `apps/core/test_log_filters.py::test_a_malformed_log_call_does_not_raise_into_the_caller` alone: it **failed**, `TypeError: not enough arguments for format string`, raised out of `handler.handle(record)` at `config/log_filters.py:70` (`record.getMessage()`) — exactly the crash the fix prevents. Restored the file verbatim; the full `test_log_filters.py` module then passed clean (12/12), including that test.
  - `config/log_filters.py` is untracked (new in this task, not yet committed), so `git diff` shows nothing for it either before or after the edit — that's expected, not a gap. Restoration was instead confirmed byte-for-byte against a pre-edit copy taken before the temporary change (`diff` exit 0, no output) and by the test suite passing again.
- **The module move, confirmed with no leftovers:** `grep -rn "config.settings.log_filters\|config\.log_filters"` across the tree shows only the current, correct references — `apps/core/test_log_filters.py:18` (`from config.log_filters import …`), `config/settings/base.py:253` (`"config.log_filters.HideStartTokenFilter"`), `docker/gunicorn.conf.py:26` (`from config.log_filters import hide_start_token`) — and no remaining reference to the old `config.settings.log_filters` path anywhere.
- **The ADMINS comment:** present above `mail_admins` in `config/settings/base.py:263`, warning not to set `ADMINS` without first revisiting the start-token redaction of email bodies.
- **Dev-stack logging, request-by-request:** with the dev overlay running, one `GET /healthz/` and one `GET /zoom/start/x.y/` each produced exactly one `django.server` request line (no doubling); the start-link request additionally logged one `django.request: Not Found: /zoom/start/[hidden]/` line (a second, distinct logger, not a duplicate of the server line). A `grep -c` for the raw token `x.y` across the log window since the requests: **0**. Confirms both that runserver logs once per request per logger and that a start-link path is hidden.
- **Stack restored:** `docker compose -f compose.yaml -f compose.dev.yaml up -d` (the overlay running at the start of this pass); `polymath-tmd-web-1`/`polymath-tmd-db-1` both `Up`/`Healthy`; `/healthz/` → 200. No `down -v` used, no volumes touched, no containers outside the `polymath-tmd` project touched. `config/log_filters.py` and `apps/core/test_log_filters.py` are unchanged (both still untracked, byte-identical to their pre-pass state).

**Tests added:** none — this pass re-verifies devops's round-2 fix only; no new coverage gap found.

**Failures:** none.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-26 (verifier PASS, 1081 tests; criterion 39 pending the owner)

**Verdict: CHANGES REQUESTED.** Blockers: none. No security problems.

**Should fix**

1. **The template triggers one query per cancelled class.**
   - Where: `views.py:307`, `views.py:296`; `class_rows.html:8`; `detail.html:29`.
   - Neither `review_context` nor `get_queryset` uses `select_related("cancelled_by")`, so every "Cancelled by …" line runs its own query.
   - Fix: add `select_related("cancelled_by")` in both places, plus a query-count test on a booking with several cancelled classes.
   - Owner: backend.
2. **`CancelBookingView` works out `kept` itself** (`views.py:587`).
   - That puts a business rule in the view, as a second definition next to `is_booked()` and `cancellable_classes()`.
   - Fix: add `LinkRequest.kept_classes(now=None, *, occurrences=None)` on the model and call it from the view.
   - Owner: backend.

**Nits, with the main-session ruling for each**

- **Gunicorn's access log records valid start-token paths** (`Dockerfile:82`). Ruling: devops hides `/zoom/start/` paths from the access log. The README also says the start token is a working link, so logs must be protected.
- **`"maxlength": "1000"` repeats `max_length`** (`forms.py:286-287`). Ruling: the backend uses one constant, `CANCEL_REASON_MAX_LENGTH`, and drops the explicit attribute.
- **"30 minutes" is typed into three templates**, while the constant `Occurrence.START_WINDOW_MINUTES` exists. Ruling: the backend adds a comment at the constant naming those three templates. The copy stays pinned.
- **Reversing migration 0006 after real cancels loses data.** Ruling: the backend says so in the migration docstring.
- **A `start_url`'s ZAK outlives the class window** (`views.py:667-673`). Ruling: the docs writer adds this to R2 and to live-check criterion 39, step 5.
- **Django's CSRF 403 page lacks `no-store`/`no-referrer`.** It holds no secret, so it is accepted. Ruling: the docs writer adds one line to the brief.
- **The two unpinned messages** read plainly and honestly. Ruling: accepted, and the docs writer records them in the Docs section.

**Checked and found sound**

- **Start link**
  - The token has its own salt and carries `{r, m}`.
  - The window edges are correct, compared in UTC.
  - GET never calls Zoom.
  - `start_url` is masked and never logged.
  - `is_zoom_https_url` is the single rule, and it refuses the backslash trick.
  - `no_referrer` and `never_cache` apply on every path.
- **Cancel**
  - The honesty tracking.
  - The lock order matches `approve()`.
  - One deadlock retry.
  - 3001 counts as done.
  - Slots are freed.
  - A double cancel loses cleanly.
  - The `occurrence_id` fallback.
- **Host-key reveal:** POST only, with the permission gate, `never_cache`, no key stored or logged, and hidden when printed.
- **Rest of the brief**
  - `approve()` no longer decrypts the key.
  - E006 and the phone formatting.
  - Migration 0007.
  - Both deviations the verifier accepted.
  - The CSS tokens and the danger button's contrast.

### Round 2 — 2026-09-26 (re-verification PASS, 1103 tests ×2; token grep 0 hits)

**Verdict: CHANGES REQUESTED.** Blockers: none. The round-1 fixes are correct: SF1 (`views.py:296-298, 312`), SF2 (`models.py:1021-1029`, `views.py:592`), and all three backend nits.

**Should fix**
1. **A malformed log call now crashes the code that made it** (`config/settings/log_filters.py:63`).
   - `HideStartTokenFilter.filter()` calls `record.getMessage()` eagerly. Filters run outside `Handler.handle()`'s try around `emit()`, so a log call with bad `%s` arguments now raises `TypeError` into the caller instead of printing "--- Logging error ---".
   - Fix: wrap the redaction in `try/except Exception`, return `True`, and leave the record untouched. Add a test that a malformed record passed through the configured handler doesn't raise.
   - Owner: devops.

**Nits and the main-session ruling on each**
- **Where the filter lives.** `log_filters.py` sits among the settings modules. Ruling: devops moves it to `config/log_filters.py`, which gunicorn can import the same way, and updates the imports and tests.
- **Dev runserver format.** Dev runserver lines now use the "simple" format. Ruling: the docs writer notes this in the CHANGELOG.
- **ADMINS caveat.** Ruling: devops adds a comment next to the `mail_admins` handler saying "don't set ADMINS without revisiting the start-token redaction of email bodies". The docs writer adds it to the risk list.

**Checked and sound**
- The regex, including the query string, Referer, `%61` and `%2F` forms. The double-encoded form isn't a working link.
- The LOGGING levels and propagation.
- `gunicorn.conf.py`.
- The switch from `dev.txt` to `-r prod.txt`.

### Round 3 — 2026-09-26 (re-verification PASS, 1104 tests ×2)

**Verdict: APPROVE.** No blockers or should-fix items.

- **Round-2 should-fix:** fixed. In `config/log_filters.py:68-83`, all the redaction work runs inside the try; on failure the record passes through untouched, and it is only rewritten after everything succeeds. The test at `apps/core/test_log_filters.py:85-99` proves it, and it failed when the verifier reverted the fix.
- **The move:** the module now lives at `config/log_filters.py`. `config/settings/` holds only settings modules, `config/__init__.py` imports nothing, and no reference to the old path remains.
- **The ADMINS warning:** it sits on the `mail_admins` handler (`base.py:263-266`).
- **Nit (optional):** use separate try blocks for the message and the traceback. A malformed call that also carries a token would be printed raw by logging's own error report. That risk is negligible.
- **Remaining before close:** criterion 39 (the owner's live check), and docs step 6, which covers:
  - README and CHANGELOG;
  - the ADMINS and ZAK items for the R2 risk list;
  - the CSRF-403 line;
  - the two unpinned messages;
  - a CLAUDE.md Architecture line for `config/log_filters.py` and `docker/gunicorn.conf.py`;
  - the dev runserver log-format note;
  - the planner's now-stale "Design shows old wording" note (D14).

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Status stays `Verifying`.** Every round-3 "remaining before close" item that's the docs writer's
is done (below). The one thing still open is criterion 39, the owner's live check against one real
paid Zoom account — round 3 approved everything else with no blockers and no should-fix items. This
brief closes (`Status: Done`) once the owner reports criterion 39's results back; until then it
stays exactly where round 3 left it.

**Files updated**

- `README.md` — new subsections under "Zoom link requests": "Cancelling a booking, or one of its
  classes", "Starting a class from the link, not the host key", "The host-key fallback: `Show host
  key`" (replacing the old "write-only" rule) and "Logs never show a start link's token" (the
  gunicorn/Django redaction, the dev runserver format change, and the `ADMINS` caveat). Updated: the
  "write-only" paragraph, the manual-mode paragraph (no host key in that email either), the go-live
  gate (both 006 and 011 now built and waiting on their owner live checks), the `IT_DESK_PHONE` env
  var (deploy table and setup), and a rebuild note (`dev.txt` now installs `prod.txt`).
- `CLAUDE.md` — the `zoom` architecture bullet gains `services.cancel()`'s lock order and Zoom-inside-
  the-transaction shape, the start link, and the host-key reveal fallback; a new `config/`
  sub-bullet documents `config/log_filters.py` (why it lives outside `config/settings/`, and its
  fail-safe `try`/`except`); a new environment gotcha says a future public URL carrying a secret in
  its path must be added to that same redaction rule.
- `docs/CHANGELOG.md` — a new newest-first entry, 2026-09-26, "011: Cancel a booking and Start this
  class link (awaiting the owner's live check)": user-visible changes (cancelling, the start link
  and its window, the host-key fallback, the permission rename, the stop-booking copy amendment),
  then technical notes (migrations `0006`/`0007`, the signed start token, the new CSS components and
  tokens, `IT_DESK_PHONE`/`zoom.E006`, the log redaction and the `dev.txt`→`prod.txt` rebuild, the
  `ADMINS` caveat, the ZAK note, the two judged-compliant interpretation deviations, the verification
  and review verdicts) and follow-ups (the separate-try-blocks nit, the singular-wording nit the
  frontend flagged, and briefs 012–014 next).
- `docs/tasks/011-cancel-and-start-link.md` (this brief) — R2's risk register row gains a dated note
  on the `zak`'s lifetime and the `ADMINS`/500-email-body caveat; live-check criterion 39 step 5
  gains the ZAK-lifetime check; criterion 23 gains one line on why the CSRF 403 page carries no
  `no-store`/`no-referrer` (it holds no secret); the D14 "which text wins" note gains a dated note
  that the Design section below it was refreshed on 2026-09-26 and no longer shows pre-decision
  wording (the original note is kept, not deleted, as the record of why the refresh happened).
- `docs/tasks/005-zoom-link-requests.md` — dated "Amended by 011" notes next to D17 (host keys are
  no longer emailed with the link; they're an IT-only, recorded fallback) and criteria 46 (still
  holds, with 011's new fields checked against it), 61 (the key is now in *no* email, not just
  outside the others) and 64 (removed outright: `approve()` no longer decrypts, so an unreadable key
  can't block an approval any more).
- `docs/tasks/008-zoom-accounts.md` — dated "Amended by 011" notes next to D3 (the reveal record
  answers a different question than "when was it last set"), D10 (reversed: the key can be read back
  again, deliberately, as a recorded fallback), criterion 17 (the actual final copy, "or been
  cancelled", differs slightly from D11's "or cancel them" sketch), criterion 24 (the reveal page is
  now the one deliberate, separately-tested exception to "no plaintext key on any accounts page") and
  criterion 25 (the approval-email-failed text drops the host-key sentence; the unreadable-key-at-
  approval row is removed outright).
- `docs/design/busy-button.md` — the "Used by" table gains `zoom/cancel_confirm.html` (`Cancel and
  email the requester`, `.button--danger`) and `zoom/start.html` (`Start this class`), so both new
  busy buttons are recorded next to the ones already there.
- `docs/design/danger-button.md`, `docs/design/class-rows.md`, `docs/design/secret-value.md` —
  checked against the criteria and the reviewer's APPROVE; all three already covered the cancel
  states (the danger button, the `Cancelled`/`In progress` class rows, the host-key reveal) exactly
  as built, so no change was needed. None of the three apply to the start page — it uses only
  existing components (`.button--primary`, `.notice`, `.facts`) — so there was nothing to add there.

**The two unpinned messages, recorded** (review round 1, "checked and found sound"; both are new
copy for edge cases the criteria don't pin verbatim, and both are asserted by exact text in tests):

- `CANCELLING_AT_THE_SAME_MOMENT` (a lock timeout before anything reached Zoom): `Someone else was
  changing this booking at the same moment. Nothing was cancelled. Try again.`
- `CancelForm`'s error for a reason over 1000 characters: `Keep the reason to 1000 characters or
  fewer.`
