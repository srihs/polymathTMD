# Changelog

Newest first. One entry per task. Each entry lists user-visible changes, then technical notes.

## 2026-09-26 — 011: Cancel a booking and Start this class link (awaiting the owner's live check)

- The IT desk can now cancel a booking — the whole thing, or just one class of a weekly booking —
  from the request's own detail page. Cancelling deletes the meeting in Zoom, frees the Zoom account
  at those times so it can be booked again, and asks IT to type a reason, which goes straight into
  an email to the requester. Zoom itself never tells anyone: it only emails hosts, alternative hosts
  and registrants, never someone who was only sent the join link, so the app's email is the only
  notice anyone gets, and it reminds the requester to tell their own students. A class that's already
  started, or a whole booking while one of its classes is in progress, can't be cancelled. The queue
  gets a new **Cancelled** tab.
- The approval email no longer carries the host account's host key. It now carries one private
  **start link** instead, scoped to the booking. From 30 minutes before each class — or from when
  the account's previous booked class ends, if that's later — until the class ends, opening the link
  shows a **Start this class** button; pressing it sends the teacher's browser straight to a fresh
  Zoom host link, so they start the meeting as host with no Zoom sign-in. Outside that window the
  page explains when it will work, with a tap-to-call number for the IT desk if `IT_DESK_PHONE` is
  set. The link is never stored or logged, works from no sign-in, and is meant to be treated like a
  key: anyone holding it can start the booking's classes as host until it ends.
- The host key stays in the system, encrypted, as an **IT-only fallback** for when a start link
  doesn't work: an IT desk member can read it back, once, on its own page, with **Show host key** on
  the Zoom account's Change page. Every reveal is recorded — who and when — and summarised on the
  Change page. The reveal page also explains the waiting-room weakness of this fallback and points to
  the better one (start the class yourself from the request's Start link, then hand the teacher
  host).
- The "Can approve or reject Zoom link requests" permission is renamed "Can approve, reject,
  reschedule or cancel Zoom link requests" (no change to who holds it).
- The Zoom accounts stop-booking errors (task 008) now end "...once the last one has finished or
  been cancelled", since cancelling a class is now a way to free an account sooner.
- Technical notes:
  - **New migrations:** `zoom/0006_cancel_and_start` (schema: `LinkRequest.Status.CANCELLED`,
    `cancelled_at`/`cancelled_by` on `LinkRequest`, `cancelled_at`/`cancelled_by`/`cancel_reason` on
    `Occurrence`, two new check constraints, and the new `HostKeyReveal` model — reversible, though
    reversing after real cancels loses who/when/why and can leave a cancelled class looking booked
    again) and `zoom/0007_review_permission_name` (data, renames the permission, reversible).
  - **The start link** is a signed token (`django.core.signing`, its own salt
    `apps.zoom.start-class`, no separate expiry — the class's own time window is the expiry),
    resolved by `services.link_request_from_start_token()` and served by the public, sign-in-free
    `zoom:start` view. `GET` never calls Zoom; only `POST` does, and only inside the window. Every
    response carries `Cache-Control: no-store` and `Referrer-Policy: no-referrer`. A fresh
    `start_url` from Zoom must be `https` on `zoom.us` or it's refused. Rotating `SECRET_KEY`
    invalidates every start link already emailed unless the old key is kept in
    `SECRET_KEY_FALLBACKS`.
  - **New components and tokens** in `static/css/style.css`: `.button--danger` (the cancel confirm
    page's final button; `docs/design/danger-button.md`), `.classrows` (the detail page's per-class
    actions and tags; `docs/design/class-rows.md`) and `.secret` (the host-key reveal page;
    `docs/design/secret-value.md`), built on new tokens `--red-800`, `--c-danger`,
    `--c-danger-hover`, `--c-on-danger`, `--font-mono` and `--fs-secret` — all in section 1's
    `:root` blocks, `--red-800` in the first, colour-only block, per the existing rule.
  - **New setting `IT_DESK_PHONE`** (optional, empty by default), read only in `base.py`, checked at
    start-up by the new `zoom.E006` (an unreadable phone number fails `manage.py check`).
  - **Log redaction, so a start link's token is never written to disk:** a new module,
    `config/log_filters.py` (deliberately outside `config/settings/`, because `docker/gunicorn.conf.py`
    imports it before Django's app registry exists, so it must not import Django or app code), hides
    every `/zoom/start/<token>/` path — including its query string and any `Referer` header — from
    gunicorn's access log and from every handler in Django's own `LOGGING`. The filter fails safe: a
    malformed log call still reaches `logging`'s own error report instead of crashing the caller
    (review round 2, should-fix 1). A side effect: the dev server no longer double-prints `django.*`
    request lines, so `runserver`'s own lines now use the plain "simple" format instead of Django's
    default. `requirements/dev.txt` now installs `-r prod.txt` instead of `-r base.txt` (so the dev
    image also has Gunicorn, for a test that exercises the real access-log config) — **rebuild both
    images** after pulling this change.
  - **Don't set `ADMINS`** without first revisiting this redaction: Django's 500-error email body is
    built by `ExceptionReporter` from the request and the view's local variables, and the filter
    only redacts the log line, not that email's body. `ADMINS` is unset by default, so this is inert
    today.
  - **A `start_url`'s ZAK can stay valid for a while after it's issued,** beyond the single meeting
    it was fetched for — unconfirmed research, recorded as risk R2 and checked in the owner's live
    check (step 5 below).
  - **Judged interpretation deviations** (both reviewed and accepted as compliant): a *cancelled*
    booking's own cancel URLs redirect with a friendly message rather than 404ing, so that the loser
    of a same-class cancel race sees "That class was already cancelled." instead of a 404; and
    criterion 14's "saving fails after Zoom removed it" is tested by failing the transaction's
    commit, the only step left after Zoom answers, because the brief's own fixed lock order (every
    write, then the Zoom delete, then commit) makes a literal "fails at the request UPDATE" reading
    impossible.
  - Two unpinned, plainly-worded messages were added and are now covered by name/text assertions: a
    lock-timeout-before-Zoom message (`Someone else was changing this booking at the same moment.
    Nothing was cancelled. Try again.`) and the cancel reason's over-1000-characters error (`Keep the
    reason to 1000 characters or fewer.`).
  - Django's CSRF 403 page (shown for a start-page POST with no valid CSRF token) doesn't carry this
    view's `no-store`/`no-referrer` headers, because `CsrfViewMiddleware` answers before the view
    runs — accepted, since that page holds no secret.
  - Verified PASS (1104 tests, three re-verification rounds) and reviewed APPROVE (round 3, after two
    rounds of should-fix items); see `docs/tasks/011-cancel-and-start-link.md`. **Criterion 39, the
    owner's live check against one real paid Zoom account (including whether a `start_url` signs the
    holder into more than the one meeting, and whether deleting a meeting also removes the recordings
    of classes that already happened), hasn't been run yet — this task stays open until the owner
    reports it.** The README's go-live gate now lists both 006 and 011 as waiting on their owner live
    checks.
  - Follow-ups: an optional nit from review round 3 — use separate `try` blocks for the log message
    and the traceback in `config/log_filters.py`, so a malformed call that also carries a token isn't
    printed raw by `logging`'s own error report (the risk is judged negligible, so it's not blocking);
    the frontend flagged that a one-off booking's whole-cancel confirm page reads "removes the
    classes below … at those times" even though there's only one class, and suggested a singular
    wording as a future copy polish; briefs 012 ("move a class"), 013 (Zoom webhook sync, so changes
    made directly in Zoom are picked up) and 014 (email the recording link when Zoom finishes one)
    are next, in that order, none of them a go-live prerequisite.

## 2026-09-25 — 006: Live Zoom connection (awaiting the owner's live check)

- The app can now talk to Zoom for real. With `ZOOM_PROVIDER=zoom`, before an account is offered or
  booked the app asks Zoom whether it already has a meeting at that time — including meetings made
  directly in Zoom, not just ones the app booked — and on approval it creates the real meeting in
  Zoom: one meeting for a one-off class, one recurring meeting for a weekly series, with cloud
  recording switched on when the requester asked for it. The emailed link, meeting ID and passcode
  are now Zoom's real values.
- If Zoom can't be reached, the app fails closed: nothing is offered or booked, and IT sees a plain
  message saying what happened and what to try next. An account whose Zoom connection isn't set up
  shows "Not connected to Zoom" and can't be booked.
- The Zoom accounts page gets a new **Zoom connection** column and field (`Zoom connection name`),
  and a **Check connection** button that asks Zoom directly whether the saved details work.
- `manual` (paste the meeting details in by hand) stays as a fallback, but now raises a deploy
  warning, because it can't see meetings made directly in Zoom.
- The spreadsheet-import brief (007) is **dropped** — the owner decided IT will stop using the
  spreadsheet to manage Zoom links once this system is live, rather than have it imported. The file
  itself stays on disk; it's never read by the app.
- Security: builds made before this task's early `.dockerignore` fix could copy
  `Dashboard 2A.xlsx` (Zoom host keys) into the Docker image, because `.dockerignore` didn't exclude
  it the way `.gitignore` already did. Anyone who built an image before 2026-09-25 should rebuild it
  and consider rotating the host keys it could have reached. The spreadsheet stays on disk either
  way — it was never a data source and never will be.
- Technical notes:
  - **New module, `apps/zoom/zoom_api.py`:** the only module that talks HTTP to Zoom, and the only
    importer of `requests`. Fixed HTTPS hosts, a `(5, 15)`-second timeout on every call, a
    process-memory Server-to-Server OAuth token cache per credential set (refreshed 5 minutes early
    and once on a `401`), and the one mapping from Zoom's errors to a fixed set of user-facing
    messages (`apps/zoom/errors.py`).
  - **Credentials are env-only, never in the database.** `ZOOM_CREDENTIAL_SETS` plus three
    `ZOOM_S2S_<NAME>_*` variables per account, read only in `config/settings/base.py` into
    `settings.ZOOM_S2S_SECRETS` (masked in error reports because its name contains `SECRET`). They
    ship through a new git-ignored `zoom-credentials.env` (copied from
    `zoom-credentials.env.example`), loaded via `compose.yaml`'s `env_file:`, deliberately kept out
    of `web.environment`.
  - **`services.approve()` is reordered:** it asks Zoom for the chosen account's meetings *before*
    taking any locks, then takes the locks, then makes exactly one `POST` create call while holding
    them, then verifies and saves. Any failure after the create rolls back and sends a compensating
    `DELETE`; a request's own leftover meetings (identified by an `agenda` marker,
    `Polymath TMD ZL-{pk:04d}`) are cleaned up before a retry creates a new one.
  - **New model fields (migration `zoom/0005_zoom_connection`):** `HostAccount.credential_set` gains
    a format validator and new help text; `Occurrence.zoom_occurrence_id` (set for weekly meetings,
    read by task 011 to cancel a single class).
  - **New system checks:** `zoom.E004` (database-tagged: a paid account with no working Zoom
    connection), `zoom.E005` (a broken `ZOOM_CREDENTIAL_SETS`/`ZOOM_S2S_*` setup) and `zoom.W001`
    (deploy-tagged: `manual` can't see meetings made directly in Zoom).
  - **New management command**, `check_zoom_connections`, checks every active paid account's
    connection and exits non-zero if any fails.
  - **New dependencies:** `requests` (runtime; the only HTTP client Zoom code uses) and `responses`
    (dev only, mocks Zoom at the HTTP layer in tests).
  - **New root-level `conftest.py`:** an autouse `responses` mock blocks every test from reaching the
    real network; any unregistered call raises instead. No test uses `@responses.activate`.
  - **New go-live gate:** replaces the one from briefs 005 and 008. Production must not take real
    requests until this task is done and running with `ZOOM_PROVIDER=zoom` and every active paid
    account connected, **and** task 011 ("Cancel this booking") exists.
  - Verified PASS (48 of 49 automated criteria; 919 tests, run twice, across three re-verification
    rounds) and reviewed APPROVE (round 3, after two rounds of should-fix items); see
    `docs/tasks/006-live-zoom-connection.md`. **Criterion 48, the owner's live check against one real
    paid Zoom account (including confirming the exact Marketplace scope names and Zoom's current
    `recurrence.end_times` cap), hasn't been run yet — this task stays open until the owner reports
    it.**
  - *2026-09-26: the scope names and the 60-occurrence recurring-series cap are now confirmed from
    Zoom's own documentation (https://developers.zoom.us/docs/integrations/oauth-scopes-granular/,
    https://developers.zoom.us/docs/api/meetings/), so criterion 48's steps 8–9 are satisfied;
    steps 1–7 still need the owner's live check.*
  - Follow-ups: task 011, "Cancel this booking", is next, straight after this task (owner's
    decision); reading an account's recurring series one after another, rather than in parallel,
    against the availability preview's 8-second deadline, is accepted for now (see the risk
    register) and can be revisited if it causes trouble in practice; showing Zoom-only meetings on
    the timetable (brief 009) stays a follow-up.

## 2026-09-25 — 009: Zoom timetable (month calendar)

- IT desk staff now have a **Zoom timetable** in the sidebar (**Zoom links → Timetable**): one
  calendar month, weeks Monday to Sunday, with each day's box showing that day's classes — start
  time, class name and Zoom account — up to three, then a `+N more` link that opens a **day page**
  listing every class that day (the day number opens it too).
- A class still waiting for IT approval shows a `Waiting for IT` tag instead of an account.
- An account filter narrows the month and day pages to one Zoom account; filtering hides waiting
  classes, since they have no account yet. `Previous month` / `Next month` links move a month at a
  time and keep the filter.
- On a phone, the month becomes a day-by-day list showing only the days that have classes.
- An approved request's detail page now has a `See it on the timetable` link straight to its month
  and account, and every row on the Zoom accounts list has a `Timetable` link.
- The timetable is read-only: nothing is booked, moved or cancelled from it.
- Technical notes:
  - **No migrations.** The page adds no model fields.
  - **`apps/zoom/timetable.py`** (new) holds every pure calculation — month arithmetic, the Mon–Sun
    week grid, day grouping, the `+N more` cap — with no database access, so it's unit-tested
    without the database and the views stay thin.
  - **Two SQL queries per page** (plus the shell's fixed queries), the same with or without the
    account filter: one for the filter's accounts, one for the classes. `OccurrenceQuerySet`
    gained `in_period()` and `for_timetable()`; `HostAccountQuerySet` gained `timetable_accounts()`
    (and the underlying `with_timetable_flag()`, `.only()`-limited to what the page reads).
  - **Accessible weekday columns through the phone reflow.** Below 768px the month grid becomes a
    day list from the same markup; empty and out-of-month cells are clipped (`.visually-hidden`
    plus `visibility: hidden` on their contents), never `display: none`, and every cell carries
    `aria-colcount`/`aria-colindex` — `display: none` drops a cell from the accessibility tree and
    a screen reader then recomputes column headers from whatever's left, misreporting the weekday
    (review round 1, SF1; independently re-checked with Windows UI Automation at 400px in round 2).
  - **Four new CSS tokens** in the layout-geometry `:root` block (section 1b) of `style.css`:
    `--cal-day-min`, `--cal-num`, `--cal-time-w`, `--cal-ref-w`. No colour literals were added.
  - Verified PASS (699 tests, across two rounds, plus a prod-stack walkthrough and a UI Automation
    check at 400px) and reviewed APPROVE (round 2, after one round-1 should-fix — the phone-reflow
    weekday defect above — was resolved); see `docs/tasks/009-zoom-timetable.md`.
  - Follow-ups: leaving `aria-current="date"` off an empty "today" cell on phones; the `.only()` on
    the accounts query is also inherited by `timetable_accounts()`, worth a note for future reuse;
    the previous/next month links have no special handling at the 2000/2100 date range limits
    (accepted as a known limit — nobody books classes in 1999 or 2101); the day list's entry rows
    borrow `--tab-h` rather than a row-height token of their own; and brief 011, "Cancel this
    booking", stays a go-live prerequisite (see the 005, 008 and 010 entries above). *Superseded
    2026-09-25: the go-live gate's other prerequisite is task 006 (the live Zoom connection), not
    brief 007 — see the 006 entry above.*

## 2026-09-25 — 010: Staff and access; Django admin removed

- Staff accounts, roles and passwords are now managed on a new **Staff and access** page
  (sidebar → Administration), not the Django admin — which is gone from the app entirely.
- Superusers and anyone with the new **Staff managers** role can list everyone who can sign in,
  add a person with a starting password, change someone's name/username/email/roles, switch
  someone off (nobody is deleted — their past decisions stay attached to them), and set a new
  password for them (this signs that person out everywhere immediately).
- A Staff manager can only give or take away a role whose rights they already hold themselves —
  so, for example, someone who should be able to add people to `IT desk` needs to be in `IT desk`
  too. They can't change their own roles, and can't manage a superuser or another Staff manager.
  Giving someone the `Staff managers` role is one-way for a non-superuser: once given, only a
  superuser can take it back.
- Every signed-in user now has **Change your password** in their user menu; changing it keeps you
  signed in on the browser you're using.
- Opening a page you don't have the role for now shows a plain "You can't open this page" message
  instead of Django's bare 403 page.
- Technical notes:
  - **Migrations (`apps/accounts`):** `0002_alter_user_managers` (the new `UserQuerySet`/
    `UserManager`, no schema change); `0003_staff_managers_group`, a data migration creating the
    `Staff managers` group with exactly `view_user`, `add_user` and `change_user` (reversible,
    idempotent); `0004_remove_admin_leftovers`, which drops the leftover `django_admin_log` table
    and deletes the stale `admin` `ContentType` rows (and their permissions/group links) that
    uninstalling `django.contrib.admin` doesn't clean up on its own. Its reverse is a no-op.
  - **`django.contrib.admin` is removed** from `INSTALLED_APPS` and `config/urls.py`; `/admin/`
    now 404s. `django.contrib.auth`, `contenttypes`, `sessions` and `messages` are unchanged.
    `apps/accounts/admin.py` is deleted. `manage.py createsuperuser` still works — it belongs to
    `django.contrib.auth` — but is documented as first-account bootstrap only.
  - **The access rules live on `User`**, not in views or templates: `can_give_role`,
    `granted_permissions`, `can_be_managed_by` and `access_change_error`. `granted_permissions()`
    reads a person's roles directly rather than Django's `get_all_permissions()`, which reports
    nothing for a switched-off user and would otherwise let a peer read a switched-off Staff
    manager as harmless and re-enable them.
  - **The moved partials.** `templates/zoom/partials/error_summary.html`, `field.html`,
    `field_error.html`, `choice_group_head.html` and `check_field.html` moved to
    `templates/partials/`, because the new `accounts` templates need them and apps don't reach
    into each other's template folders. Every `zoom` include was updated; nothing else changed for
    `zoom`.
  - **The password-leak fix.** `partials/field.html` used to write `value="{{ field.value }}"`
    unconditionally, which on a bound password field would echo a typed password back on a failed
    submit. It now skips `value` for password widgets — one fix in the shared partial covers every
    password form (add a person, set someone's password, change your own).
  - **`apps/core/mixins.py`:** `SignedInPermissionMixin`, factored out of `apps/zoom/views.py` so
    `accounts` can use the same anonymous/403 gate without either app importing the other's views.
  - No new settings, env vars or dependencies.
  - Verified PASS (570 tests, across two rounds) and reviewed APPROVE (round 2, after one round-1
    should-fix — "only roles they hold" — was resolved); see
    `docs/tasks/010-staff-and-access.md`.
  - Follow-ups: two cosmetic, markup-only nits in `staff_form.html` (a duplicated CSS class on a
    locked role row, and a locked role showing the posted rather than stored state after a refused
    crafted submit) — nothing is saved wrongly either way; moving `accounts`' and `zoom`'s shared
    date-display format into `apps/core` so both apps read one source instead of `accounts`
    repeating brief 005's format by hand; and brief 011, "Cancel this booking", which stays a
    go-live prerequisite alongside brief 007 (see the 005 and 008 entries above). *Superseded
    2026-09-25: brief 007 (the spreadsheet import) was dropped; the go-live gate is now task 006
    (the live Zoom connection) plus brief 011 — see the 006 entry above.*

## 2026-09-25 — 008: Zoom accounts page

- IT desk staff now manage Zoom host accounts on their own page, from the sidebar's **Zoom links →
  Zoom accounts** item: a list of every account (in use first), an "Add a Zoom account" screen, and
  a "Change {name}" screen. Anyone in the `IT desk` group can use it — there's no separate role.
- A host key is now **write-only** everywhere: type it once and it's never shown again, to anyone,
  on any screen. The list and change page instead say whether a key is saved, and when and by whom
  it was last set.
- An account can no longer be taken out of use, or marked as not paid, while it still has an
  upcoming (not-yet-finished) approved class. The change page explains how many classes are booked,
  over which dates, and when the change becomes possible.
- Accounts are never deleted, only taken out of use.
- The Django admin no longer has anything Zoom-related: host accounts, host keys and link requests
  are all gone from `/admin/`. Every message that used to say "in the admin" now points to the Zoom
  accounts page instead. Staff users and the `IT desk` group are still managed in the Django admin,
  until brief 010 gives them in-app screens too.
- Technical notes:
  - **Migrations:** `zoom/0003_hostaccount_host_key_changed` adds `host_key_changed_at` and
    `host_key_changed_by` to `HostAccount` (who last set or removed its key, and when), and rewords
    the `host_key_encrypted` field's `help_text` away from the admin. `zoom/0004_it_desk_manages_host_accounts`
    is a data migration that grants the `IT desk` group Django's built-in `zoom.view_hostaccount`,
    `zoom.add_hostaccount` and `zoom.change_hostaccount` permissions — not a custom "manage"
    permission, and no `delete_hostaccount` — so the group now holds exactly four permissions.
    Reversible and idempotent.
  - **The stop-booking rule** (`HostAccount.stop_booking_errors()`) runs inside the same transaction
    as the save, locking the account row and its booked `Occurrence`/`LinkRequest` rows
    (`select_for_update(of=("self", "link_request"))`) before counting upcoming classes, so it can't
    race `services.approve()` booking a class on the account at the same moment. A two-connection
    test (`apps/zoom/tests/test_race.py`) proves this at both READ COMMITTED (Django's MySQL
    default) and REPEATABLE READ (MySQL's own default), catching a review-round-1 bug that only
    showed up at the stricter level.
  - `apps/zoom/admin.py` and `apps/zoom/tests/test_admin.py` are deleted; brief 005's admin-based
    tests are re-proved against the in-app screens instead.
  - Brief 005's optional review nit 2 (masking the host key local in the key-cleaning code) is now
    done: `apps/zoom/validators.py`'s `validate_host_key` carries `@sensitive_variables`, alongside
    every other method that touches a plaintext key.
  - No settings, env vars or dependencies changed; the `.env.example` comment on
    `HOST_KEY_ENCRYPTION_KEYS` now points to the Zoom accounts page instead of the admin.
  - Verified PASS (398 tests, across two rounds, including a two-connection race test and a rebuilt
    production-stack walkthrough) and reviewed APPROVE (round 2, after one round-1 blocker was
    fixed); see `docs/tasks/008-zoom-accounts.md`.
  - Follow-ups: brief 011, "Cancel this booking", is a go-live prerequisite alongside brief 007 —
    until it exists, a wrong or unneeded approval can't be undone in the app, and (from this task
    onwards) an account with a booking can't be taken out of use until that class is over; "send the
    approval email again" is a smaller follow-up for when that email fails to send; and one optional
    nit is still open, adding a mention of brief 008's stop-check race to `test_race.py`'s module
    docstring. *Superseded 2026-09-25: brief 007 (the spreadsheet import) was dropped; the go-live
    gate is now task 006 (the live Zoom connection) plus brief 011 — see the 006 entry above.*

## 2026-09-25 — 005: Zoom link requests (without the live Zoom connection)

- Anyone can ask for a Zoom link for a class, with no sign-in, at a public form staff can share by
  link. It covers one-off and weekly classes and an optional recording request, and asks for the
  requester's name, email and phone. IT never sees the request until the requester confirms their
  email through a link that stays valid for one day.
- IT desk staff review confirmed requests in a queue (Waiting / Link sent / Not approved / All, with
  search). For each waiting request they see exactly which paid Zoom accounts are free for every
  class in it, and which are busy, with the clashing booking named and linked. Approving books a
  free account and emails the requester; rejecting asks for a reason and emails that instead.
- The approval email carries the Zoom link and the booked account's host key, so the teacher can
  take host control, plus a line reminding them if they asked for the class to be recorded.
- Nobody is promised a reply time anywhere on the form, the confirmation pages or the emails — only
  that IT will email the requester once they've looked at the request.
- Technical notes:
  - **New app, `apps/zoom`** (label and namespace `zoom`): models, QuerySets, `services.py`
    (approve/reject orchestration), `providers.py` (a swappable meeting-provider interface, with
    `fake` for dev/tests and `manual` for production until a later brief adds the live Zoom API),
    `crypto.py`, forms, views, admin, checks and two migrations — the models/constraints, and a data
    migration that creates the `IT desk` group with the one permission
    `zoom.review_linkrequest`. New public frame `templates/public_base.html`, for pages with no
    sign-in.
  - **New dependency:** `cryptography` (Fernet/`MultiFernet`) encrypts host keys at rest. They're
    never stored or logged in plaintext, and appear in exactly one outgoing email (the approval
    email). `manage.py rotate_host_keys` re-encrypts every stored key when the key list is rotated.
  - **New/moved env vars:** `ZOOM_PROVIDER` (`manual`/`fake`; the production image now refuses to
    start with `fake`), `TRUSTED_PROXY_COUNT`, `HOST_KEY_ENCRYPTION_KEYS` (required). The `EMAIL_*`
    settings moved from `prod.py` into `base.py` and now pass through `compose.yaml`'s
    `web.environment` — before this, production mail never left the container.
  - **New system checks:** `zoom.E001` (the fake provider can't run in a `--deploy` check),
    `zoom.E002` (an unknown `ZOOM_PROVIDER`), `zoom.E003` (a missing or invalid
    `HOST_KEY_ENCRYPTION_KEYS`).
  - **Conflict-free booking** is enforced three ways: a live clash preview on the request detail
    page, a locked re-check inside the approval transaction, and a database-level backstop — a
    `HostSlot` table with a unique `(host_account, starts_at)` on 5-minute slots, so MySQL itself
    refuses an overlapping booking even if application code somehow tried to store one.
  - **Go-live gate:** production must not take real bookings yet. A later brief needs to import the
    bookings already on IT's spreadsheet first, or the conflict engine can't see them and could
    double-book an account.
  - Verified PASS (308 tests, across two rounds), including a manual-mode walkthrough on the rebuilt
    production stack and proof that the production image refuses to start with
    `ZOOM_PROVIDER=fake`. Reviewed APPROVE (round 2, with two optional nits); see
    `docs/tasks/005-zoom-link-requests.md`.
  - Follow-ups: brief 006 adds the live Zoom provider (one Server-to-Server OAuth credential set per
    paid host account); brief 007 imports future bookings from the spreadsheet, gates go-live, and
    must call `services.approve()` only outside an open transaction — nested inside one, a real
    deadlock would break the retry's savepoint (review round 2, nit 1, carried forward as a required
    item for brief 007). One optional nit is still open: masking the `host_key` local in the admin
    form's `clean_host_key`. *Superseded 2026-09-25: brief 007 (the spreadsheet import) was dropped;
    the go-live gate is now task 006 (the live Zoom connection) plus brief 011 — see the 006 entry
    above. The "outside an open transaction" rule for `services.approve()` still holds; task 006's
    live provider is now the first other caller, not an importer.*

## 2026-09-24 — 004: The approved design becomes the app's theme

- Sign-in and Home now use the client-approved look: a purple sidebar, a top bar, a page title
  and breadcrumb row, and a settings panel for colour mode, page width, sidebar size and sidebar
  colour. The app opens light with the purple sidebar even if the device prefers dark; dark mode
  stays one click away, in the settings panel or the top bar's colour-mode button, and the choice
  is remembered in that browser.
- The top bar's search field and notifications bell are visible, matching the approved look, but
  say plainly that they aren't ready yet: the search field reads "Search is coming soon" and can't
  be typed into or submitted, and the bell's panel says "No notifications yet." Both arrive for
  real with the Zoom link request feature (task 005).
- The sidebar only lists pages that exist today: Home, plus Admin for staff. Home is a single
  "Hello, {name}" card; no made-up figures, requests or devices are shown.
- Sign-in now matches the approved concept exactly: the concept's help text, a full-width
  password field, no show/hide button, and no "Forgot your password" line (owner correction,
  D18 — "login page design is different than the concept", resolved as "Match the concept
  exactly"). Kept on purpose, as the owner asked: the error announcement (with its curly
  apostrophe), focus moving to the password box after a wrong password, username autofocus on
  first load, and the empty-fields check.
- Technical notes:
  - **Files:** `templates/base.html` is now the f-desk document and shell, split into partials
    under `templates/partials/` (`sidebar.html`, `topbar.html`, `top_search.html`,
    `notifications.html`, `user_menu.html`, `colour_mode_button.html`, `messages.html`,
    `footer.html`, `settings_dialog.html`, `icons.html`), each included with
    `{% include … with … only %}`. `templates/registration/login.html` and `templates/core/home.html`
    are ported to the new look. `templates/partials/icon_templates.html` (the old JS toast
    template) is deleted.
  - `static/css/style.css`, `static/js/app.js` are replaced, and `static/js/theme-init.js` is new:
    it applies a saved layout choice before first paint and publishes the four settings' allowed
    values and defaults once, as `window.tmdLayout`, so `app.js` has no second copy.
  - Icons switch from inlined Solar Bold Duotone to one Feather sprite (MIT), `partials/icons.html`.
    Fonts switch from Nunito/Nunito Sans/Cinzel to IBM Plex Sans (SIL OFL 1.1).
  - CSS tokens are now role-named (no value in a token's name) and type sizes are in `rem` with
    unitless line heights, so the browser's font-size preference works; layout geometry stays in
    `px`. Colour literals live only in the first `:root` palette block, checked by a test.
  - `apps/accounts/models.py`: `User.initials` (a read-only model property, no migration), used
    for the user menu's avatar.
  - Django `messages` now render through one partial, in the page flow directly under the title
    row (not a floating toast), because that works with JS off and doesn't cover content on a
    phone.
  - **Owner correction (D18), after this task's first close:** `registration/login.html`'s form
    column was rebuilt to follow `design/f-desk/login.html` exactly. Removed: the show/hide JS
    block from `static/js/app.js`, `.field__row`/`.signin__help` from `static/css/style.css`, and
    the now-unused `eye` symbol from `partials/icons.html`. `docs/design/password-field.md` and
    its Design-section rows are marked superseded, since the app no longer has a show/hide
    control.
  - No settings, env var, dependency or route changed.
  - Tests: 83 passing (up from 36; 76 at this task's first close, then 7 more for D18), covering
    the shell markup, the CSS token and `rem` rules, the search/notifications placeholders,
    `User.initials`, and the concept-exact sign-in markup. Three existing `apps/core/tests.py`
    tests were deliberately rewritten to match text content rather than exact markup, because the
    sign-out button and Admin link now carry an icon; every `apps/accounts/tests.py` test is
    unchanged.
  - Verified PASS (83 tests, dev and prod stacks) and reviewed APPROVE; see
    `docs/tasks/004-app-theme-f-desk.md`, including its D18 owner-correction record.
  - Follow-ups recorded for brief 005: the shell assumes a signed-in user, so the public Zoom
    request form must either override `{% block body %}` like `login.html` does, or branch on
    `user.is_authenticated` in `topbar.html`/`sidebar.html`; wire the search field to a real form
    and give the bell real content, or record why not; port `.tag` and check it renders at 10.5px
    (the client's own choice, held from task 003).

## 2026-09-24 — 003: Look-alike of the client's reference layout

- The client asked for the Technology Management Desk to look and work like a specific admin
  template of theirs: the same typeface, the same sidebar-and-top-bar shell, light and dark mode,
  and a layout settings panel. `design/f-desk/` is a new static prototype built to that shape, in
  the Polymath crest purple, so the client can compare it side by side with their own reference
  template before anything is ported into the app.
- It shows the same six screens and sample school content as directions `a`–`e` (sign in, home,
  requests list, device record, raise-a-request form, design kit), re-dressed with a collapsible
  grouped sidebar, a top bar (search, notifications, user menu), a page-title and breadcrumb row,
  cards, a footer, and a settings panel for colour mode, page width, sidebar size and sidebar
  colour.
- It is built from scratch: nothing was copied from the client's reference template, only observed
  and measured. What's different from that template is recorded in full in the task brief's "What
  the client will notice" list (`docs/tasks/003-reference-lookalike-prototype.md` → Review →
  Round 2); in short, it is sparser (no sparklines, promo cards or illustrations), everything is a
  little taller for easier tapping, and the settings panel offers four choices instead of seven.
- Directions `a`–`e` were not selected; they stay in `design/` unchanged, as a record.
- Technical notes:
  - Folder: `design/f-desk/` (`login.html`, `dashboard.html`, `requests.html`, `device.html`,
    `request-form.html`, `ui-kit.html`, `style.css`, `theme-init.js`, `app.js`, `README.md`,
    `assets/`, `screenshots/`). Design spec: `docs/design/directions/f.md`.
  - No CSS/JS framework or component library (decision D2): plain CSS grid, flexbox and custom
    properties; `<details>`/`<summary>` for the sidebar's expandable group and the dropdowns; a
    `<dialog>` for the settings panel; `:target` plus `inert` for the phone drawer (D14); native
    scrolling instead of a third-party scrollbar; one inline SVG chart instead of a charting
    library.
  - Text sizes match the client's reference template, including 10.5px status tags — the owner's
    deliberate choice over a larger-text floor (D9). WCAG AA contrast (4.5:1 text, 3:1 non-text)
    holds in both light and dark mode and on all three sidebar tones.
  - Porting into `templates/` and `static/` is a follow-up brief (004) and does not start until the
    client has approved this prototype against their reference template (D13).
  - Verified PASS (44/44 fidelity rows against the reference template, after one fix cycle and
    re-verification) and reviewed APPROVE (round 2); see
    `docs/tasks/003-reference-lookalike-prototype.md`.
  - Follow-ups recorded for brief 004: switch sizes from `px` to `rem`; rename value-named tokens
    (for example `--space-52px`) to role-named ones; add `{# … #}` purpose-and-context header
    comments to every template; fix the settings panel's "Icons only" option not staying synced
    after a menu-button collapse; check content reflow at 320px as well as 400px.

## 2026-09-24 — 002: Five design directions

- Five clickable prototype directions — Ledger, Parchment, Broadsheet, Signpost and Workbench — for the owner to browse and compare, in `design/`. Each has its own sign-in, home, requests list, device record, request form and design-kit page, at both desktop and phone sizes.
- All five show the same sample school content (the same people, devices and requests) so what differs between them is the design, not the data.
- `design/README.md` is the place to start: it indexes and compares all five in one table.
- Technical notes:
  - Folders: `design/a-ledger/`, `design/b-parchment/`, `design/c-broadsheet/`, `design/d-signpost/`, `design/e-workbench/`. Each is self-contained static HTML/CSS/JS, openable from `file://`, with no build step and no dependency on `static/` or `templates/`.
  - One direction brief per variation in `docs/design/directions/` (`a.md`–`e.md`), plus its own `README.md` indexing and comparing all five.
  - Decisions worth knowing: acceptance criterion 27 (five distinct desktop navigation mechanisms) was relaxed by decision D9 after `a` and `d` were both built as left-vertical navs; the full record, including that `d`'s `Requests` count badge was removed during round 1 to force a literal pass and then restored in round 2 once the reviewer flagged that the design had been edited to satisfy the measurement rather than the user, is in the brief's D9 section.
  - No `apps/`, `templates/`, `static/`, `config/`, `docker/`, compose, packaging or requirements file changed; no migrations. The app's current stylesheet (`static/css/style.css`) is untouched and stays the app's look until the owner picks a direction for it to replace.
  - Recorded follow-ups for whichever direction is ported or kept: e-workbench's phone layout puts the request queue below the stats and actions and needs its list/record panes split; b-parchment's `assets/crest.png` has no alpha channel and should be re-cut with one; and four non-blocking nits from review round 3 — a stray raw `2px` value in `e-workbench/style.css`'s box-shadow instead of a token, an inert `z-index` on `.utility__panel`, `docs/design/directions/README.md` describing d-signpost's rail with the wrong item count and tile size, and `e-workbench/ui-kit.html`'s open-state specimen repeating the "account menu" label.
  - Verified PASS (all 37 acceptance criteria, after three rounds of fixes) and reviewed APPROVE; see `docs/tasks/002-design-directions.md`.

## 2026-09-16 — 001: Fix the three findings from the foundation baseline verification

- The sign-in page's browser tab now reads "Sign in · Polymath TMD" instead of showing the server's address.
- After a failed sign-in attempt, screen readers announce the error message together with the field, not as a separate, easy-to-miss alert.
- The "Admin" link on the home page now shows only for staff members; other signed-in users no longer see a link they can't use.
- Technical notes:
  - **Root cause:** Django's `LoginView` injects its own `site_name` into the template context from `get_current_site()` (the request host, since `django.contrib.sites` isn't installed), which silently overrode the project's own `site_name` context processor.
  - **Fix:** renamed the context processor's key from `site_name` to `tmd_site_name` in `apps/core/context_processors.py`, and updated `templates/base.html` and `templates/core/home.html` to read the new key. A guard test (`apps/core/tests.py::test_no_template_reads_the_colliding_site_name_variable`) stops the old name from coming back.
  - `templates/registration/login.html`: both inputs' `aria-describedby` now includes `login-error` (before the existing help id) whenever `form.errors` is set.
  - `templates/core/home.html`: the "Admin" link is now wrapped in `{% if user.is_staff %}`.
  - `templates/base.html`, `templates/registration/login.html` and `templates/core/home.html` each gained a `{# … #}` header comment naming their purpose and expected context variables, per CLAUDE.md.
  - No settings, migrations, env vars or dependencies changed.
  - Verified PASS and reviewed APPROVE; see `docs/tasks/001-foundation-verification-fixes.md`. The review's nits are optional follow-ups, not required by this task: de-duplicate the `_title()` test helper (`apps/accounts/tests.py`, `apps/core/tests.py`), de-duplicate the Admin-link regex in `apps/core/tests.py`, and a possible later task to give `static/js/app.js`'s client-side empty-fields check the same `aria-describedby`/`aria-invalid` wiring.

## 2026-09-16 — Project foundation (before task briefs)

- A sign-in page in the Polymath College design, a placeholder home page, and the Django admin.
- Technical notes:
  - **Stack:** Django 5.2 LTS, MySQL 8.4 (utf8mb4) and WhiteNoise. The app runs in Docker (a `prod` Gunicorn image and a `dev` overlay with live reload) and answers liveness probes at `/healthz/`.
  - **Custom user model:** `accounts.User`.
  - **Brand images:** `static/img/crest.png`, `crest-chip.png` and `favicon-32.png` are generated from `logo.png`.
  - **Claude Code agent team:** added in `.claude/agents/`, and the task-brief workflow in `docs/tasks/`.
