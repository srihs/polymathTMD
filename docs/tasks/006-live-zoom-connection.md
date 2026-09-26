# 006 — Live Zoom connection: make meetings through the Zoom API, and check Zoom for clashes before booking

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Verifying <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

The owner's words, most recent first (2026-09-25):

> No we have to discard the spreadsheet. plan this work now on connecting the app to zoom etc.

> so is zoom is liked to the system? when arequest approved is it created automatically?

> if it is not connected, how do we know "free for every class date and time"?

The owner's answers to this brief's questions, and a clarification (2026-09-25, relayed by the main session):

- **Q1:** "Keep Zoom's defaults".
- **Q2:** "No, always dated".
- **Q3:** "Separate, right after".
- **What "discard the spreadsheet" means:** "after the system comes, they will not be using spreadsheet to manage zoom links". The file stays on disk and is not deleted. Nothing is imported from it, and it is never a data source (D18).

**Reading.** Today the app is not connected to Zoom. When IT approves a request, the `manual` provider makes IT create the meeting in Zoom by hand and paste its details. The "free for every class" check only sees bookings made **through the app**. Brief 005 planned to close that gap by importing the future bookings from IT's spreadsheet (brief 007). The owner has now discarded the spreadsheet, so **brief 007 is dropped**. Bookings made before go-live, or made directly in Zoom later, exist **only in Zoom**.

This brief connects the app to Zoom, with one Server-to-Server OAuth app for each paid host account (brief 005, D16). With the live `zoom` provider:

1. Before an account is offered, and again before it is booked, the app **asks Zoom for that account's scheduled meetings**. Any meeting that overlaps a class makes the account busy, whether or not the app booked it. This check is now **the only protection for the bookings that exist only in Zoom**. If Zoom can't be asked, the app **fails closed**: it offers and books nothing.
2. On approval, the app **creates the meeting in Zoom**. A one-off class gets a single meeting. A weekly class gets one recurring meeting whose dates match the request's classes exactly. Cloud recording is switched on when the requester asked for it. The app stores the join link, meeting ID and passcode, and emails them with the host key, as it does today.
3. Every failure leaves the database and Zoom consistent. That covers Zoom errors, rate limits, timeouts, bad credentials, and a database failure after Zoom has already made the meeting. The IT person gets a plain message saying what happened and what to do.
4. The IT desk can see and set each account's Zoom connection on the Zoom accounts page, and can **check the connection** there.

Credentials come only from the server's environment, never from the database or the repo. `manual` stays available as a fallback.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**How the work is split, and in what order**

| Brief | What | Status after this brief |
|---|---|---|
| 007 | Spreadsheet import | **Dropped** (owner, 2026-09-25: "discard the spreadsheet"; D18). Nothing is imported, and `openpyxl` is never added. The file stays on disk and is not deleted |
| **006 (this)** | Live `zoom` provider. Zoom-side clash check in the preview and at approval. Failure handling and rollback. Connection fields and the "Check connection" button on the Zoom accounts page. Settings, checks, env and compose plumbing. **The `delete_meeting` provider call** (rollback needs it, and 011 reuses it). The Zoom occurrence IDs stored per class, so 011 can cancel a single class | Planned |
| **011** | "Cancel this booking": a `cancelled` status, the screens, the email, and freeing the slots. It calls 006's `delete_meeting`. It also amends 008's criterion 17 copy | Next, after 006 (D1) |

**011 stays separate, and is built straight after 006** (owner, Q3: "Separate, right after"). The planner's reasons:

- 006 is already one full reviewable change: an external API, secrets, a concurrency-sensitive rewrite of `approve()`, and three screens touched.
- 011 adds a new status to the state machine, new screens and a new email, and it amends 008's copy. That is a second model-and-screens group.
- 006 builds and tests every Zoom call 011 needs (`delete_meeting`, and `occurrence_id` per class). 011 is then pure app work, with no new Zoom plumbing.

**New go-live gate** (this replaces brief 005's D14/D19 gate and the README's item 1). Production must not take real requests until **all** of these are true:

1. **006 is done**, and production runs `ZOOM_PROVIDER=zoom`.
2. Every active paid account has a working Zoom connection. That means `check_zoom_connections` passes and `manage.py check --database default` reports no `zoom.E004`.
3. **011 "Cancel this booking" is done** (brief 008, D11).

With `manual`, the app can't see meetings made in Zoom. That is why `manual` now raises the deploy warning `zoom.W001` (criterion 5).

**In scope (006)**

- **`apps/zoom/zoom_api.py` (new):** the only module that talks HTTP to Zoom. It holds:
  - the fixed HTTPS endpoints;
  - the Server-to-Server OAuth token fetch, with a short in-process token cache;
  - one request helper with timeouts;
  - the mapping from Zoom errors to our error types;
  - paging.

  It is the only module that imports `requests`.
- **`apps/zoom/providers.py`:**
  - the interface grows `checks_zoom`, `busy_times()`, `delete_meeting()` and `check_connection()`;
  - `ProviderError` gets subclasses by kind;
  - new `ZoomProvider`;
  - `FakeProvider` gains steerable busy times, an "unavailable" switch and a deleted-meetings log;
  - `ManualProvider` gets `checks_zoom = False`.
- **`apps/zoom/services.py`:**
  - `approve()` is reordered: look up Zoom first, then take the locks, then create, then save, with a compensating delete (D6);
  - new `availability(link_request, occurrences)` combines the database clashes with the Zoom clashes for the preview (D8);
  - new `check_connection(account)`.
- **Models:**
  - `HostAccount.credential_set` gets a format validator and new help text, and goes on the form;
  - new property `HostAccount.zoom_connection_state`;
  - new property `LinkRequest.zoom_marker`;
  - new field `Occurrence.zoom_occurrence_id`;
  - the module docstring loses "the 007 import";
  - `HostAccount.label`'s help text loses "old spreadsheet";
  - migration `0005`.
- **Screens:**
  - the request detail shows Zoom clashes, `Couldn't check with Zoom`, `Not connected to Zoom`, the time of the Zoom check, and the manual-mode notice;
  - the Zoom accounts list gets a `Zoom connection` column;
  - the change page gets the `Zoom connection name` field and a `Check connection` button.
- **Management command:** `check_zoom_connections`.
- **Checks:**
  - `zoom.E001` and `zoom.E002` are updated;
  - new: `zoom.E004` (database-tagged), `zoom.E005` and `zoom.W001` (deploy).
- **Settings and env (`tmd-devops`):**
  - `ZOOM_CREDENTIAL_SETS` plus three variables per set, read in `base.py` into `ZOOM_S2S_SECRETS`;
  - a git-ignored `zoom-credentials.env`, loaded through `env_file:`, and its `.example`;
  - `.gitignore` and **`.dockerignore`** entries;
  - `urllib3` logging pinned to `WARNING`;
  - `prod.py` message;
  - `.env.example`;
  - `requests` added to `base.txt` and `responses` to `dev.txt`.
- **Security fix found while planning (`tmd-devops`):** `.dockerignore` doesn't exclude `/Dashboard 2A.xlsx` or the other root office files that `.gitignore` excludes. `Dockerfile` line 62 (`COPY --chown=app:app . .`) therefore **copies the spreadsheet, which holds host keys, into the prod image** on this machine. The fix is criterion 44: the same root-anchored patterns go into `.dockerignore`. **It was delivered early, ahead of the rest of this brief, as an urgent `tmd-devops` fix** (main session, 2026-09-25). The spreadsheet itself stays on disk (D18).

**Out of scope (006)**

- Cancelling or changing bookings, a `cancelled` status, and deleting Zoom meetings from any screen (011).
- Webhooks (D13). The app doesn't learn about changes made directly in Zoom to meetings it created. The limits are listed in D15.
- Showing Zoom-only meetings on the timetable (brief 009). That is a follow-up for the changelog.
- Per-occurrence meetings as a fallback (D5: never needed for our patterns).
- Storing connection-check results, tokens or any Zoom credential in the database.
- Changing the approval email's wording, the host-key rules, the public form or the queue.
- Any import of past or future bookings.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- These carry over from briefs 005 and 008:
  - the frozen "now", **Mon 28 Sep 2026, 10:00** Asia/Colombo, and the way time is frozen;
  - "IT user", "plain user" and "key-less viewer";
  - the rule on pinned copy: the designer may propose changes through the main session, and they are made here first.
- **"Mocked Zoom"** means HTTP responses registered with `responses`. **No test reaches the network** (criterion 45).
- **"Zoom-connected account"** means an active paid account whose `credential_set` names a set present in `settings.ZOOM_S2S_SECRETS`. Tests set `ZOOM_S2S_SECRETS` through the `settings` fixture, with obviously fake values such as `test-account-id`.
- **"The zoom provider"** means `ZoomProvider`, selected by `ZOOM_PROVIDER=zoom`, or constructed directly in a test.
- The owner's answers to Q1–Q3 are recorded as D19–D21. The criteria below already reflect them.

### Settings, credentials and checks

1. **Provider values.** `providers.PROVIDERS` is exactly `fake`, `manual` and `zoom`.
   - Any other `ZOOM_PROVIDER` fails `manage.py check` with `zoom.E002`, and its message lists all three values.
   - The default in `base.py` stays `manual`.
2. **Credentials come from env only.**
   - `base.py` reads `ZOOM_CREDENTIAL_SETS`, a comma-separated list of slugs such as `zoom-01,zoom-02`.
   - For each slug it reads `ZOOM_S2S_<NAME>_ACCOUNT_ID`, `ZOOM_S2S_<NAME>_CLIENT_ID` and `ZOOM_S2S_<NAME>_CLIENT_SECRET`, where `<NAME>` is the slug upper-cased with `-` turned into `_`. So `zoom-01` gives `ZOOM_S2S_ZOOM_01_ACCOUNT_ID`.
   - They go into `settings.ZOOM_S2S_SECRETS`: `{slug: ZoomCredentials(account_id, client_id, client_secret)}`, where `ZoomCredentials` is a frozen dataclass whose `repr` shows only the slug.
   - The name rule is one function in `base.py`, unit-tested with `zoom-01` → `ZOOM_S2S_ZOOM_01`.
   - A source scan finds no `ZOOM_S2S_` env read outside `config/settings/base.py`.
   - No model field, migration or fixture holds any of these values.
3. **Masked in error reports.** `SafeExceptionReporterFilter().get_safe_settings()["ZOOM_S2S_SECRETS"]` equals the cleansed substitute (`********************`), and so does `ZOOM_CREDENTIAL_SETS` if it is ever matched. The setting's name contains `SECRET` so that Django masks it. A test proves this.
4. **`zoom.E005` (untagged, no database).** It applies when `ZOOM_PROVIDER=zoom`. `manage.py check` reports `zoom.E005` when any of these is true:
   - `ZOOM_CREDENTIAL_SETS` is empty;
   - a listed slug is missing any of its three values;
   - a slug doesn't match `^[a-z0-9]+(-[a-z0-9]+)*$`;
   - two slugs map to the same `<NAME>`.

   The message names the slug and the missing variable **names**, never a value. With `fake` or `manual`, E005 is silent.
5. **Deploy checks.**
   - `zoom.E001`, the fake provider under `--deploy`, now reads `The fake Zoom provider makes links that don't work. Set ZOOM_PROVIDER=zoom in production.`
   - `prod.py` still refuses to start with `fake`, with a message that names `zoom`.
   - **New `zoom.W001`** (deploy only), with `manual`: `ZOOM_PROVIDER=manual can't see meetings made directly in Zoom, so it can double-book them. Set ZOOM_PROVIDER=zoom before taking real requests.`
   - With `zoom` and valid sets, `check --deploy` adds nothing, and only W021 stays accepted.
6. **`zoom.E004` (tagged `database`).** It runs with `manage.py check --database default`. When `ZOOM_PROVIDER=zoom`, every active paid `HostAccount` must have a non-empty `credential_set` that is a key of `ZOOM_S2S_SECRETS`. Each offender gets one error: `{label} has no working Zoom connection: {reason}.`, where the reason is either `no Zoom connection name is set` or `the server has no connection details called {slug}`.
   - Inactive or free accounts never trigger it.
   - With the `zoom_hostaccount` table missing (before `migrate`), it returns no errors instead of crashing.
   - It is silent for `fake` and `manual`.
7. **Env plumbing (`tmd-devops`).**
   - `compose.yaml`'s `web` gains `env_file: [{path: ./zoom-credentials.env, required: false}]`. The stack starts with or without the file.
   - The repo has `zoom-credentials.env.example`, which lists every variable name with empty values and a comment per line. It has no real value.
   - `zoom-credentials.env` is listed in `.gitignore` and `.dockerignore`.
   - The `ZOOM_PROVIDER` comment in `.env.example` lists `zoom`.
   - `LOGGING` in `base.py` sets the `urllib3` logger to `WARNING`, whatever `LOG_LEVEL` is.

### The Zoom HTTP client (`apps/zoom/zoom_api.py`)

8. **HTTPS and fixed hosts only.**
   - Every request goes to `https://zoom.us/oauth/token` or to a URL under `https://api.zoom.us/v2/`. These are module constants, not settings.
   - Every request passes an explicit timeout of `(5, 15)` seconds (connect, read).
   - A source scan finds no `verify=False` and no `http://` in `apps/zoom/`.
   - A test with mocked Zoom asserts the scheme and host of every recorded call.
9. **Token.**
   - The token request is a `POST` with HTTP Basic auth made from the client ID and secret, `grant_type=account_credentials` and the account ID. The backend confirms against Zoom's docs whether the account ID must go in the body or the query, and records which.
   - The token is cached **in process memory only**, per credential set, until 300 seconds before `expires_in`. Two API calls within that time make one token request. After it expires, the next call makes a new one.
   - An API `401` with a cached token drops the token, fetches one new token, and retries the call **once**. A second `401` raises the auth error (criterion 10).
   - The token is never written to the database, to Django's cache, or to a log. A test searches `django.core.cache.cache` and every `zoom_*` table dump for it.
10. **Error mapping.** Each failure raises a `ProviderError` subclass whose `user_message` is fixed by the table. None of them contains Zoom's raw response text, a URL, or a credential.

    | Zoom response | Error kind | `user_message` (lower-case phrase, used inside the sentences below) | `lasting` |
    |---|---|---|---|
    | connection error, timeout, or HTTP 5xx | `ZoomUnavailable` | `no answer from Zoom` | `False` (temporary) |
    | HTTP 429 | `ZoomBusy` | `Zoom is busy right now` | `False` (temporary) |
    | token request 400 or 401, or API 401 after the one retry | `ZoomAuthFailed` | `Zoom didn't accept this account's connection details` | **`True`** |
    | API 400 or 401 with Zoom code 4700 or 4711 (missing scope) | `ZoomMissingScope` | `the Zoom app for this account is missing a permission` | **`True`** |
    | API 404 with Zoom code 1001 (no such user) | `ZoomUserNotFound` | `Zoom has no user with this account's sign-in email` | **`True`** |
    | any other 4xx | `ZoomRejected` | `Zoom error {code}` (Zoom's numeric `code`, or the HTTP status if none) | **`True`** |

    - **`lasting`** (D23) is a class attribute on `ProviderError`, `False` by default. It tells the message builders whether "try again in a few minutes" is honest advice. Waiting fixes only the two temporary kinds. A unit test pins the flag for all six kinds, and for plain `ProviderError` (the fake's), which is temporary.
    - **`ZoomRejected` counts as lasting.** The main session's list named only three lasting kinds, but a 4xx that isn't auth, scope or user (a refused field, say) doesn't fix itself with time either (D23).
    - Only a `401` gets a retry (criterion 9). There's no automatic retry on 429, 5xx or timeouts.
    - A `POST` that creates a meeting is **never** repeated by the client.
11. **Nothing secret is logged.** A test captures logging at `DEBUG` for `apps.zoom`, `django`, `urllib3` and `requests` through:
    - a token fetch;
    - a list;
    - a create whose mocked response carries a `start_url` and a `password`;
    - a delete;
    - each error in criterion 10.

    No captured record, and no `str()` of a raised error, contains:
    - the client secret, client ID or account ID;
    - the access token;
    - `Basic ` or `Bearer `;
    - the join URL, the passcode or the `start_url`.

    Every function that holds a secret or a token is decorated with `@sensitive_variables` naming those locals. An `ExceptionReporter` test on an error raised inside the token fetch shows the secret masked.

### What counts as busy in Zoom (`ZoomProvider.busy_times`)

12. **Listing.** `busy_times(host_account=…, start=…, end=…)` does the following:
    - It calls `GET /users/{host_account.email}/meetings?type=scheduled&page_size=300`, following `next_page_token` for up to 10 pages. More pages than that raises `ZoomUnavailable` (fail closed).
    - It returns `BusyTime(starts_at, ends_at, topic, meeting_id)` items, aware and in UTC, only for meetings overlapping `[start, end)`.
    - **Type 2** gives one interval, `start_time` + `duration`.
    - **Type 8** (recurring, fixed time) gives one interval per entry in `occurrences` from `GET /meetings/{id}`, skipping entries whose `status` is `deleted`. If the listing already carries every occurrence, the backend may skip the extra `GET`, and records this in the Implementation notes.
    - **Ignored** (owner, Q2: "No, always dated"; D20): type 1 (instant), type 3 (recurring with no fixed time), type 4 (personal meeting ID, PMI), and any meeting with no `start_time`. The README tells IT to always schedule classes with a date and time.

    The test uses mocked Zoom with:
    - two pages;
    - a type-8 meeting with one deleted occurrence;
    - a type-3 meeting and a type-4 (PMI) meeting, neither of which is returned;
    - a meeting that touches the window end-to-start, which isn't returned (D6 of brief 005: touching isn't a clash).
13. **Meetings the app already knows.**
    - A Zoom meeting whose ID equals the `meeting_id` of an `approved` request on the same account is left out of the Zoom clashes. The database check already reports it, so it isn't shown twice.
    - A Zoom meeting whose `agenda` contains **this** request's `zoom_marker` (`Polymath TMD ZL-0042`) is left over from a failed attempt at this request. It is never a clash, and `approve()` deletes it before creating (criterion 27).
    - A meeting carrying **another** request's marker is an ordinary clash.
14. **Weekday mapping.** A pure function maps ISO weekdays to Zoom's `weekly_days`: 1→2, 2→3, 3→4, 4→5, 5→6, 6→7, 7→1. It is unit-tested for all seven, and for `"1,3"` → `"2,4"`.

### The availability preview on the request detail

15. **States per account.** With a provider whose `checks_zoom` is true (`zoom`, or `fake` in tests), each `availability` entry on a waiting request carries a `zoom_state`:

    | `zoom_state` | When | Tag (icon + word) | Offered in `Book it on`? |
    |---|---|---|---|
    | `checked` | Zoom answered | `Free for all {n} classes` or `Busy for {k} of {n} classes` (as in 005) | only if no database clash and no Zoom clash |
    | `unavailable` | Zoom couldn't be asked (any criterion 10 error) | `Couldn't check with Zoom` (warning), plus the reason as a sentence, e.g. `Zoom is busy right now.` | no |
    | `not_connected` | the account isn't Zoom-connected (no HTTP is made for it) | `Not connected to Zoom` (warning) | no |

    - `busy_count` counts the request's classes that clash with **either** a database booking **or** a Zoom meeting, each class once.
    - A Zoom clash row shows the date, this request's time, and `In Zoom: {topic}, {start}–{end}`, with no link. The topic is escaped.
    - **Contract points from the Design (D22):**
      - **G1:** `account_edit_allowed` is set on **every** entry, whatever its state. It is true exactly when the user has `zoom.change_hostaccount`. It drives the fix link on both `unavailable` and `not_connected` rows. A test checks it on an entry in each state, for an IT user (true) and for a user without the permission (false).
      - **G2:** `zoom_clashes` is sorted by `occurrence.starts_at`, then `busy.starts_at`. A test gives the provider busy times in reverse order.
      - **G6:** `zoom_problem` is a **sentence**: the criterion 10 phrase with its first letter capitalised and a full stop added (`Zoom is busy right now.`), the same form as criterion 28's reason sentence. It is `""` unless the state is `unavailable`. A test checks all six error kinds.
16. **Checked at.** When at least one account was checked, the page shows `Checked with Zoom at {10:02 am}.`, using `zoom_checked_at`.
17. **Nothing can be checked.** When every bookable account is `unavailable` or `not_connected`:
    - there's no approve form;
    - a warning notice reads `We couldn't check the Zoom accounts just now, so nothing can be approved. Reload the page in a few minutes. If this keeps happening, ask whoever manages the Zoom accounts to press Check connection for each account.` (the second sentence was added by D24, P2);
    - the reject form stays.

    When some accounts were checked and none is free, the existing 005 notice (`No paid Zoom account is free…`) applies.

    **Which notice wins when there's no approve form** (G3, confirmed in D22): `has_started` first, then `all_unchecked`, then "none free".
    - `approve_form` is `None` in all three cases.
    - `has_started` is always in the context, including when `all_unchecked` is true.
    - A test builds a started request whose accounts are all unchecked, and asserts that the started notice's text appears and the criterion 17 text doesn't.
18. **Manual mode.**
    - With `manual`, no HTTP is made. Every entry has `zoom_state="off"`, and availability is exactly as in 005.
    - The approve box shows the notice `This system can't see meetings made directly in Zoom. Before you approve, check the chosen account's meetings in Zoom.`
19. **Speed and freshness.**
    - Zoom lookups for the accounts run in parallel, at most 6 at a time, with an overall deadline of **8 seconds**. An account without an answer by then is `unavailable` with the reason `no answer from Zoom`.
    - Each account's result is cached for **60 seconds** in Django's default cache, keyed by the account and the request's window. It holds busy times and topics only, never a token.
    - Two loads of the same detail page within 60 seconds make one set of HTTP calls. A load 61 seconds later makes new ones. This is tested with call counts on mocked Zoom.
    - **Approval never uses this cache** (criterion 21).
20. **No transaction during HTTP.**
    - `LinkRequestDetailView` is `non_atomic_requests`, so no database transaction is open while Zoom is asked. A test asserts `connection.in_atomic_block` is false inside the mocked HTTP callback.
    - The page's SQL query count doesn't change with the number of Zoom meetings returned (1 compared with 50).

### Approving with the zoom provider

21. **Order of work** (D6). A test records one ordered log of HTTP calls (via `responses` callbacks) and SQL statements (via `connection.execute_wrapper`) during a successful approve. The log shows:
    1. the Zoom list call(s) for the **chosen account only**, which are **fresh** (never cached), before any `SELECT … FOR UPDATE`;
    2. then the locking reads (`zoom_linkrequest`, then `zoom_hostaccount`, then `zoom_occurrence`), the occurrence `UPDATE` and the slot `INSERT`;
    3. then exactly one `POST /users/{email}/meetings`;
    4. then the `UPDATE` of `zoom_linkrequest`, then the commit.
22. **One-off class.** The approval of a one-off request, 5 Oct 2026, 08:30–11:30, `wants_recording=False`, sends this JSON body and nothing else:
    - `topic` = class name;
    - `type` = `2`;
    - `start_time` = `"2026-10-05T08:30:00"`;
    - `timezone` = `"Asia/Colombo"` (from `settings.TIME_ZONE`);
    - `duration` = `180`;
    - `agenda` = `"Polymath TMD ZL-{pk:04d}"`;
    - `settings` = `{"auto_recording": "none"}` and nothing more. The payload never contains `join_before_host`, `jbh_time` or `waiting_room` (criterion 49; owner, Q1).

    From the mocked response the app stores:
    - `meeting_id` = `str(id)`;
    - `join_url`;
    - `passcode` = `password`.

    The response's `start_url` is not on `Meeting`, not in any `zoom_*` row, not in a log and not in a message (criterion 46 of 005 still holds). The approval email is sent as in 005, criterion 35.
23. **Weekly class.** The approval of 005 criterion 5's request (Mon and Wed, 5–28 Oct, 8 classes) sends:
    - `type` = `8`;
    - `start_time` = `"2026-10-05T08:30:00"` (the first class);
    - `recurrence` = `{"type": 2, "repeat_interval": 1, "weekly_days": "2,4", "end_times": 8}`.

    When the mocked response's `occurrences` start at exactly the 8 stored `Occurrence.starts_at` values, each `Occurrence.zoom_occurrence_id` is set to the matching `occurrence_id`. One-off classes keep it blank.
24. **Dates don't match.** When Zoom's returned occurrences differ from ours in number or in any start time:
    - the app sends `DELETE /meetings/{id}` once;
    - nothing is booked: status `waiting`, no slots, no occurrence host;
    - no email is sent;
    - the detail re-renders (200) with `Zoom scheduled different dates from this request, so the meeting was removed from Zoom and nothing was booked. Tell whoever looks after the system.`
25. **Recording.** `wants_recording=True` sends `"auto_recording": "cloud"`, and `False` sends `"none"`, explicitly, so an account-wide default never records a class nobody asked to record.
26. **A Zoom clash found at approval** (a meeting made in Zoom after the page loaded; the mocked list returns it):
    - no `POST` is made and nothing is booked;
    - the response is **409**, with `{label} has a meeting in Zoom at an overlapping time: {topic}, {Mon 5 Oct 2026} at {8:00 am}. Choose another free account.`;
    - availability is refreshed.
27. **Leftover from a failed attempt.** If the list for the chosen account returns a meeting carrying **this** request's marker, the app sends `DELETE /meetings/{id}` for it before the create. It then approves normally, so exactly one meeting for the request is left in Zoom. If that delete fails, the approval stops before the create. It uses criterion 28's message for the error (with its temporary or lasting next step), and nothing is booked.
28. **Zoom can't be asked at approval.** If the list call fails with any criterion 10 error:
    - no `POST` is made, nothing is booked and no email is sent;
    - the page re-renders (200) with `We couldn't check {label}'s meetings in Zoom, so nothing was booked. {Reason sentence} {Next step}`

    The reason sentence is the criterion 10 phrase with its first letter capitalised and a full stop added, e.g. `Zoom is busy right now.` The next step depends on the error's `lasting` flag (D23, P1):
    - **temporary:** `Try again in a few minutes.`
    - **lasting:** `Choose another free account, and ask whoever manages the Zoom accounts to press Check connection for {label}.`

    A test pins one message for each of the six kinds.
29. **Not connected.** Choosing an account that isn't Zoom-connected makes no HTTP call and books nothing. The response is 409, with `{label} isn't connected to Zoom yet, so it can't be booked. Choose another free account, or set up its Zoom connection on the Zoom accounts page.`
30. **The create fails** (mocked connection error, 5xx, 429, 401 after the retry, a 4xx with a code, or a read timeout). Everything is rolled back: status `waiting`, no slots, no occurrence host, no email. The message depends on whether Zoom can have made the meeting anyway (D25):

    - **(a) Zoom certainly made nothing.** This covers a connection error or connect timeout (nothing reached Zoom), a 429, and any 4xx. The message (D25, P3; this replaces 005's `Zoom didn't create the meeting: …`) is:
      - temporary: `We couldn't make the meeting in Zoom: {phrase}. Nothing was booked. Try again in a few minutes.`
      - lasting: `We couldn't make the meeting in Zoom: {phrase}. Nothing was booked. Choose another free account, and ask whoever manages the Zoom accounts to press Check connection for {label}.`
    - **(b) Zoom may have made it** (a **read timeout** or an **HTTP 5xx** on the create `POST`: the request reached Zoom, and the answer never came back or came back as an error). After the rollback, the app makes **one** best-effort clean-up: one list call for the chosen account, then `DELETE` for every meeting whose `agenda` carries this request's `zoom_marker` (D6, criterion 13). The message always starts `We couldn't make the meeting in Zoom: no answer from Zoom, so Zoom may have made it anyway. Nothing was booked here.` It then ends with exactly one of these, matching what the clean-up actually did:

      | Clean-up result | Ending |
      |---|---|
      | found one or more meetings with the marker and deleted them all | ` We found it in {label}'s Zoom account and removed it. Try again in a few minutes.` |
      | the list worked and found no meeting with the marker | ` We didn't find it in {label}'s Zoom account. Try again in a few minutes. If it turns up there later, the next try removes it before making a new one.` |
      | the list or a delete failed | ` We couldn't check {label}'s Zoom account for it. Try again in a few minutes. If a meeting for {reference} is there, the next try removes it before making a new one.` |

      Each ending is truthful because of criterion 27: every later approve of this request deletes marker meetings before it creates. That is the only thing the app promises.
    - Tests cover each (a) kind, and all three (b) endings, using the recorded mocked calls to prove the clean-up list and deletes happened or not.
    - **005's criterion 40 is amended deliberately.** The fake's `ProviderError("Zoom is not responding")` is temporary and certain, so it now reads `We couldn't make the meeting in Zoom: Zoom is not responding. Nothing was booked. Try again in a few minutes.` Its test is updated to match.
31. **Saving fails after Zoom made the meeting.** The test forces an exception at the request `UPDATE`, after the mocked create has succeeded. The app then:
    - sends `DELETE /meetings/{id}` **once, after the rollback**;
    - books nothing;
    - shows the normal message for that failure. A MySQL deadlock is retried once, as in 005, and a second create is then allowed, because the first meeting was deleted.

    If that `DELETE` also fails:
    - the message is `Zoom made meeting {meeting_id} on {label}, but it couldn't be saved here or removed from Zoom. Delete that meeting in Zoom, then try again.`;
    - exactly one `ERROR` log record contains only the reference, the account label, the meeting ID and the exception class name.
32. **Idempotency and races** (`transaction=True` thread tests, as in 005 criterion 38):
    - **(a)** Two threads approve **the same** request: exactly one `POST` create, one approval and one email.
    - **(b)** Two threads approve **different** overlapping requests on the same account: one is approved and the other gets the conflict. Exactly **one** `POST` create is made, because the loser is stopped by the locked database re-check before it reaches Zoom.
    - **(c)** A second approve POST after success redirects with `This request has already been decided.` and makes **no** HTTP call.

    The verifier records the thread tests' output. If they're flaky, that's a FAIL, never a skip.
33. **Fake and manual still behave as in 005.** With `fake`, 005's criteria 35–41 pass unchanged, except for criterion 40's wording, which criterion 30 amends. The fake's Zoom check returns no busy times unless a test steers it. With `manual`, 005's criterion 36 passes unchanged, and no HTTP is made on any path.

### Zoom accounts page (amends brief 008)

34. **Connection name field.** `HostAccountForm` gains `credential_set`, labelled `Zoom connection name`, and placed after `sort_order`.
    - Help text: `The name of this account's Zoom connection on the server, like zoom-01. Whoever looks after the server tells you the name.`
    - It is optional. A value must match `^[a-z0-9]+(-[a-z0-9]+)*$` and be at most 40 characters. Otherwise the error is `Use lower-case letters, numbers and hyphens only, like zoom-01.`
    - A value the server doesn't have yet **is allowed**. The state line says so (criterion 35).
    - Brief 008's D5 and its test `"credential_set" not in form.fields` are amended deliberately.
    - **G4 (D22):**
      - The widget attributes are set on `HostAccountForm`: `autocomplete="off"`, `autocapitalize="none"`, `spellcheck="false"` and `maxlength="40"`.
      - The label and help text are on the form too (008 G2).
      - `Meta.fields` and `field_order` put `credential_set` straight after `sort_order`: `label, email, notes, is_paid, is_active, sort_order, credential_set, host_key, remove_host_key`.
      - A test checks the rendered attributes and the field order.
35. **Connection state.** `HostAccount.zoom_connection_state` reads only `settings.ZOOM_S2S_SECRETS`, with no HTTP and no query. It returns:
    - `"none"` when no name is set;
    - `"missing"` when the name is set but isn't on the server;
    - `"ready"` otherwise.

    Where it shows:
    - **List:** a new column, `Zoom connection`, after `Host key`. It shows an icon and a word: `Set up`, `Not set up` or `Missing on the server`. Brief 008's criterion 4 is amended.
    - **Change page:** the same word, plus, for `missing`, `The server has no Zoom connection called {slug}.`

    Rendering the list, add and change pages makes **no** HTTP call (mocked Zoom registry empty, no error).
36. **Check connection.** `POST zoom:account_check` (pk):
    - It needs `zoom.change_hostaccount`: anonymous users are sent to log in, a plain user or key-less viewer gets 403, and `GET` gets 405. It is non-atomic.
    - With a `ready` connection, it calls the token endpoint, then `GET /users/{email}`, then `GET /users/{email}/meetings?page_size=1`. It uses `ZoomProvider` whatever `ZOOM_PROVIDER` is, so the connection can be proved before switching.
    - It redirects (302) to `zoom:account_edit` with one message:

    | Result | Level | Message |
    |---|---|---|
    | works, user `type` 2 (licensed) | success | `The Zoom connection works for {label}.` |
    | works, user `type` 1 (Basic) on a paid account | warning | `The Zoom connection works for {label}, but Zoom says {email} is a Basic (free) user. Free users' meetings end after 40 minutes. Untick Paid account, or ask the Zoom account owner to give this user a licence.` |
    | name not set | error | `{label} has no Zoom connection name yet. Type it in, save, then check again.` |
    | name not on the server | error | `The server has no Zoom connection called {slug}. Ask whoever looks after the server to add it, then check again.` |
    | `ZoomAuthFailed` | error | `Zoom didn't accept the connection details called {slug}. Check the account ID, client ID and client secret on the server, and that the Zoom app is activated.` |
    | `ZoomMissingScope` | error | `The Zoom app for {slug} is missing a permission. Add the scopes listed in the README, then check again.` |
    | `ZoomUserNotFound` | error | `The connection works, but that Zoom account has no user {email}. Check the Zoom sign-in email.` |
    | `ZoomUnavailable` / `ZoomBusy` (temporary) | error | `Couldn't check {label} with Zoom: {phrase}. Try again in a few minutes.` |
    | `ZoomRejected` (lasting; D23) | error | `Couldn't check {label} with Zoom: {phrase}. Waiting won't fix this. Tell whoever looks after the server, and give them the Zoom error number.` |

    - Nothing is stored about the result.
    - **G5 (D22):** on the change page, `account` is present whenever `can_check_connection` is true, because the check form's action uses `account.pk`. `can_check_connection` is always false on the add page.
37. **Command.** `manage.py check_zoom_connections` runs the same check for every active paid account, ordered by `sort_order` and `label`. It prints one line per account, `{label}: works` or `{label}: {message}`, and exits **1** if any account fails. No line contains a secret, a token or an account ID.

### Security

38. **Least-privilege scopes.** The README lists the exact scopes: create a meeting, list a user's meetings, view a meeting, delete a meeting, and view a user (D13). **No others.** The backend confirms the exact scope names against Zoom's Marketplace and endpoint docs at build time, and records them in the Implementation notes. The README uses those names.
39. **No webhooks.** No URL name or path in `apps/zoom/urls.py` contains `webhook`, and no view accepts requests from Zoom.
40. **No token or credential in the browser.** None of the following contains any credential value or token: the detail page, the accounts pages, the check redirect's messages, or the approval email. This is tested by searching the rendered output for the fake credential values.

### Tests, dependencies, template rules

41. **Model and migration.**
    - `0005` adds `Occurrence.zoom_occurrence_id`, a `CharField(20, blank=True)`, labelled `Zoom occurrence ID`. It also changes the `help_text` of `credential_set` and `label`, and adds the `credential_set` validator.
    - `makemigrations --check` is clean.
    - The 005 criterion 46 test for secret-named fields still passes, and `zoom_occurrence_id` doesn't match its pattern.
42. **Dependencies.**
    - `requirements/base.txt` pins `requests` with the comment `# HTTP client for the Zoom API (brief 006, D3)`.
    - `requirements/dev.txt` pins `responses` with `# mocks Zoom at the HTTP layer in tests (brief 006, D3)`.
    - The prod image builds with no build tools added. No Zoom SDK is added.
43. **Template rules.** Brief 005 criterion 51 and brief 008 criterion 26 apply to every changed template:
    - a header comment;
    - every include ends with `only`;
    - no inline styles;
    - no hard-coded paths;
    - the sprite is used exactly.

    The detail and accounts pages work without JavaScript. The layout and accessibility rules of 005 criterion 54 and 008 criterion 28 hold for the new states at 320, 400, 1024 and 1440 px, in both modes.
44. **Delivered early (2026-09-25, `tmd-devops`, an urgent fix ahead of this brief).** Devops's notes go in its Implementation notes, pasted in by the main session. The verifier still re-checks this criterion in step 4, including the `zoom-credentials.env` entry if the early fix didn't add it. **Secrets stay out of the image.** `.dockerignore` excludes `zoom-credentials.env` and the root-anchored office-file patterns `.gitignore` already has (`/Dashboard 2A.xlsx`, `/*.xlsx`, `/*.xlsm`, `/*.xls`, `/*.ods`, `/*.csv`, `/data/private/`). After `docker compose build`, `docker compose run --rm --no-deps web ls /app` lists neither `Dashboard 2A.xlsx` nor `zoom-credentials.env`.
45. **No test reaches the network.**
    - An autouse fixture in the project-level `conftest.py` starts a `responses.RequestsMock` for **every** test, so any unregistered `requests` call raises `ConnectionError`. A test proves that a call to `https://api.zoom.us/v2/users/x` with nothing registered raises.
    - `test.py` keeps `ZOOM_PROVIDER = "fake"`.
    - A fixture clears the token cache and the preview cache before each test.

### Verification (CLAUDE.md "Verify a change", all five, plus the owner's live check)

46. **Automated checks.** These all pass:
    - `ruff check .` and `ruff format --check .`;
    - `pytest --create-db`;
    - `makemigrations --check --dry-run`;
    - `manage.py check`;
    - `manage.py check --database default`.

    Settings change, so `check --deploy` is also run on the prod stack with `USE_HTTPS=True`, **twice**:
    1. with `ZOOM_PROVIDER=zoom`, `ZOOM_CREDENTIAL_SETS=zoom-test` and dummy values for its three variables. Only W021 may appear. The check makes no HTTP call;
    2. with `ZOOM_PROVIDER=manual`. Only W021 and **`zoom.W001`** may appear, which proves the warning fires.
47. **Prod stack walkthrough** (the verifier does **not** contact Zoom). The verifier runs `ZOOM_PROVIDER=manual docker compose up -d --build`, waits for `web` to be healthy, and works over HTTP on 8010:
    1. The manual-mode notice (criterion 18) appears on a waiting request's detail.
    2. The accounts list shows the `Zoom connection` column.
    3. Setting `Zoom connection name` to `zoom-test` on a test account shows `Missing on the server`.
    4. `Check connection` for an account with no name shows criterion 36's `name not set` message, with no outbound call.
    5. Static files come from hashed paths.

    Screenshots go in the scratchpad:
    - the detail with each Zoom state, rendered in dev with the fake provider steered (`Couldn't check with Zoom`, `Not connected to Zoom`, a Zoom clash row, and "nothing can be checked"), at 1440 and 400;
    - the accounts list at 1440 and 400;
    - the change page with each connection state at 1440.

    The verifier restores the stack that was running before.
48. **The owner's live check.** The owner runs this with one real paid account and credentials they supply at runtime; the verifier never sees them. The main session gives the owner these steps, and the verifier records the owner's reported results in Verification. Before starting, the owner puts the three values in `zoom-credentials.env`, sets `ZOOM_PROVIDER=zoom`, and leaves that account's **host key empty** on the Zoom accounts page, so no real key reaches the console email log.
    1. `Check connection` shows `The Zoom connection works for {label}.`
    2. The owner creates a meeting **directly in Zoom** on that account for a future time T. A request overlapping T shows that account `Busy` with `In Zoom: {topic}`, and doesn't offer it.
    3. A weekly request (2 weeks, 2 days, `Record this class` ticked) approved on that account appears in Zoom as one recurring meeting. It has 4 occurrences at the right Colombo times and automatic cloud recording on. The emailed link, ID and passcode match Zoom.
    4. With a deliberately wrong client secret (restart), the detail shows `Couldn't check with Zoom`, `Check connection` shows the auth message, and nothing can be approved.
    5. Clean-up: the owner deletes the test meetings in Zoom (011 isn't built yet) and restores the real secret.

    The owner also notes, for the record, what that account's own Zoom settings are for "join before host" and "waiting room". The app doesn't set either (D19).

### Added after the owner's answers (2026-09-25)

49. **Zoom's meeting defaults are left alone** (owner, Q1: "Keep Zoom's defaults"; D19). For every create the zoom provider sends (one-off and weekly, recording asked for or not), the JSON body recorded by mocked Zoom:
    - has a `settings` object whose only key is `auto_recording`;
    - contains **none** of the keys `join_before_host`, `jbh_time` or `waiting_room`, at any level.

    The test builds all four combinations and asserts both points. A source scan of `apps/zoom/` also finds none of those three names outside tests.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q1–Q3 on 2026-09-25, and clarified what "discard the spreadsheet" means. The answers are recorded as D18–D21. The main session's rulings on the Design section's gaps and copy proposals are D22–D25.

**Owner's answers**

| Q | Question (short) | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| Q1 | Should the app switch on "join before host" and switch off the waiting room? | Yes to both | **"Keep Zoom's defaults"**: the app sets neither | D19 (amends D10; criteria 22 and 49) |
| Q2 | Does IT book classes as recurring meetings with no fixed time, or on a personal meeting ID? | No, so ignore them | **"No, always dated"** | D20 (criterion 12) |
| Q3 | 011: separate, or folded into 006? | Separate, straight after 006 | **"Separate, right after"** | D21 |
| (clarification) | What does "discard the spreadsheet" mean? | none | "after the system comes, they will not be using spreadsheet to manage zoom links" | D18 |

**Supplied by the owner, not design questions:**

- The three credential values for each of the 11 paid accounts, from whoever administers each Zoom subscription (the setup steps are in D16).
- A real paid account for the live check in criterion 48.

**Decisions (the planner's)**

- **D1: 007 is dropped, and 011 stays separate** (see Scope). 006 includes `delete_meeting` and stores `Occurrence.zoom_occurrence_id`, so 011 can cancel a whole series (`DELETE /meetings/{id}`) or one class (`?occurrence_id=`) with no new Zoom plumbing.
- **D2: Credentials. Three variables per set, one explicit list, a git-ignored env file, and nothing in the database.** This supersedes 005's D16 naming idea of one colon-joined variable per set.
  - **Why three variables:**
    - Zoom's Marketplace shows the account ID, client ID and client secret as three separate values to copy.
    - Nothing documents that they can never contain `:`.
    - Three names can be checked one by one (E005).
  - **Why the explicit list `ZOOM_CREDENTIAL_SETS`, not a scan of every `ZOOM_S2S_*` variable:** no hidden magic. E005 can say exactly which variable is missing.
  - **Delivery:** 11 × 3 + 1 = 34 variables would bloat `compose.yaml`. `web` therefore loads `zoom-credentials.env` through `env_file` with `required: false`. This is the documented exception, planned in 005's D16, to "list every env var in `web.environment`". It needs Docker Compose 2.24 or later for `required:`, which devops confirms on this machine.
  - **Masking:** the setting is named `ZOOM_S2S_SECRETS`, so Django's `SafeExceptionReporterFilter` (which matches `SECRET`) masks it on debug and error pages.
  - **In the image:** the file is excluded from the image by `.dockerignore`.
  - **Rules:** secrets are alphanumeric, so there's no `$` problem, but the "no `$` in env values" rule still applies. A set may be shared by several accounts, because the Zoom user is chosen by `HostAccount.email` (see D10), so a multi-user subscription works with one app.
- **D3: `requests` plus `responses`, not the standard library, and not a Zoom SDK** (CLAUDE.md "Less code": the reason for the new dependencies).
  - **`requests`:**
    - it's pure Python and maintained under the PSF;
    - it verifies certificates by default;
    - it takes connect and read timeouts per call;
    - it pools connections across the preview's parallel calls.
  - **`responses` (dev only)** mocks at `requests`' transport adapter. Our real code builds the URLs, headers and JSON, and parses the responses, so tests prove the actual HTTP behaviour. A global mock also turns any accidental real call into an error (criterion 45).
  - **Rejected:**
    - **stdlib `urllib.request`:** no new runtime dependency, but tests would then run against a transport fake of our own, which proves our fake rather than the HTTP path. Timeouts, error bodies and paging would also mean more hand-written code.
    - **Zoom SDKs:** there's no official, maintained Python server SDK. The community wrappers hide the HTTP layer we need to control for timeouts, retries and logging, and add surface for about five endpoints.
- **D4: Tokens are cached in process memory only.**
  - One token per credential set per Gunicorn worker. It's refreshed 5 minutes before it expires, and once on a `401`. Zoom lets several valid tokens exist per app, so 3 workers are fine.
  - It is **not** kept in Django's cache. That cache could later be configured as the database or Redis, which would put a live credential outside the process.
  - The preview's threads share the dictionary under a lock.
- **D5: Recurrence.**
  - **One-off:** a type 2 meeting.
  - **Weekly:** a type 8 meeting with `recurrence.type=2`, `repeat_interval=1`, the mapped `weekly_days` and `end_times = number of classes`, starting at the **first stored class**. That is always on a ticked day, so Zoom's series and our occurrences start together.
  - 005's 60-class cap matches Zoom's documented maximum for `end_times`. The backend re-checks the current docs. If Zoom's limit is now lower, that's a blocker to report, not something to work around silently.
  - After the create, the returned occurrences are compared with ours. On any difference, the meeting is deleted and nothing is booked (criterion 24).
  - **No per-occurrence fallback.** Every pattern the form accepts (one time slot, chosen weekdays, a first and last date, at most 60 classes) is exactly a Zoom weekly series. A fallback would never run, yet it would need up to 60 creates while holding the locks (see D6), and it would give the requester up to 60 different links.
- **D6: The approval order, and why the create call happens while locks are held.** In `services.approve()`, per attempt:
  1. **No locks, no transaction.** Read the request, its classes and the chosen account.
     - If the account isn't Zoom-connected → criterion 29.
     - Otherwise, ask Zoom for the account's busy times across the request's window. The lookup is fresh, never cached.
     - A Zoom clash → criterion 26. A lookup failure → criterion 28.
     - Delete this request's own leftovers → criterion 27.
     - This is the slow part (several calls, possibly paged), so it runs **before** any lock.
  2. **In one transaction**, as in 005:
     - lock the request, then the account;
     - re-check the status, whether the first class has started, and that the account is still bookable;
     - decrypt the host key;
     - do the locking database clash re-check;
     - write the occurrence hosts and the slots.
  3. **Still inside it: one `POST` create** (the token was normally fetched in step 1). Then verify the occurrences, set `zoom_occurrence_id`, save the request, and commit.
  4. **After a failure:** if anything fails after step 3's create returned, the transaction rolls back. The meeting is then deleted **outside** it (the compensating delete, criterion 31). A read timeout on the create gets the best-effort clean-up in criterion 30.

  **Why step 3 holds locks (justified, as the task asks):**
  - The alternative is to commit a reservation first (a new `booking` status), create outside the locks, then confirm. That adds a state to the state machine, a sweeper for stuck reservations, and an orphan-slot recovery path, for about one approval a day. That is more code and more ways to fail.
  - What is actually held is bounded and narrow:
    - one `POST`, with timeouts (5, 15), so about 20 seconds at worst and usually under a second;
    - only two rows (the request and the account) plus that request's own classes;
    - the only waiters are another approval or an account edit **of the same account**, and `innodb_lock_wait_timeout` (50 seconds) is above the worst case;
    - the preview, the queue, the timetable and the public form don't take these locks.

  **The remaining window:** a meeting typed into Zoom by hand in the second or two between step 1 and step 3. It is accepted and documented (R1). App-against-app races are still fully prevented by the locks and the slot backstop, which are unchanged.

  **Idempotency:**
  - The request row lock makes a same-request double approve create at most one meeting.
  - The agenda marker `Polymath TMD ZL-0042` lets a retry recognise and remove a meeting left by an earlier failed attempt, because Zoom has no idempotency key.
  - An orphan that can't be removed shows up as an ordinary Zoom clash on that account. The failure is safe: a false "busy", never a double booking.
- **D7: What counts as busy in Zoom.**
  - Every scheduled meeting with a time (types 2 and 8, with deleted occurrences skipped) on that account's user, including meetings the app didn't make.
  - The same overlap rule as 005's D6: touching end-to-start doesn't clash.
  - Meetings the app already has as approved bookings are de-duplicated by meeting ID.
  - Instant meetings, meetings with no fixed time and PMI meetings are ignored (D20).
  - Any doubt fails closed: an error, too many pages, or a deadline missed means the account isn't offered or booked.
- **D8: The preview is live and parallel, with a 60-second cache.** It uses `concurrent.futures`, at most 6 threads, an 8-second deadline, and no database access in the threads.
  - **Why a short cache and not live only:** reloading the page, and the re-render after a failed approve or reject, would otherwise repeat about 11 or more lookups each time.
  - **Why a cache is safe here:** the approval always re-asks Zoom fresh for the chosen account (D6), and the app's own new bookings are seen through the database check.
  - **Where it lives:** Django's default cache, which is per process `LocMem` today. It holds busy times and topics, which aren't secrets.
  - **No open transaction:** the detail view is made `non_atomic_requests`, so no database transaction is held open during the calls.
- **D9: Failure handling.**
  - **One mapping:** criterion 10 is the single table from Zoom errors to our error types.
  - **No automatic retries**, except the one token refresh on a `401`. A retry of a create could make a second meeting, and a retry of a lookup only delays the answer the IT person needs.
  - **Messages** say what happened, that nothing was booked, and what to do next (criteria 26–31). The next step depends on the `lasting` flag (D23), and after an ambiguous create the message reports what the clean-up found (D25).
  - **Rate limits** are per Zoom account, and each paid account is its own subscription. At about one request a day with the cache, we stay far below them.
- **D10: The meeting payload is minimal.**
  - The fields are:
    - `topic` (the class name);
    - `agenda` (the marker);
    - `start_time` and `timezone` (from `settings.TIME_ZONE`);
    - `duration`;
    - `recurrence` (weekly only);
    - `settings`: only an explicit `auto_recording` (criterion 25). Everything else follows the account's own Zoom settings, including join before host and the waiting room (D19, criterion 49).
  - The Zoom user is `HostAccount.email`, used as `userId`. It isn't `me`, which is ambiguous for account-level apps.
  - The passcode is Zoom's own (`password`, at most 10 characters, which fits `LinkRequest.passcode`).
  - `start_url` is dropped where the response is parsed.
- **D11: Checks.**
  - **E005** (untagged, settings only) blocks `check` and `migrate` when `zoom` is chosen but the credential sets are broken. That is a whole-site misconfiguration.
  - **E004** needs the database, so it is tagged `database` and runs with `check --database default`. The README and the gate tell ops to run it. At runtime, an account that isn't connected is simply never offered or booked (criteria 15, 29). One unconnected account doesn't stop the site from starting, because that would take the public form down with it.
  - **W001** makes the "manual can't see Zoom" risk visible in `check --deploy`.
- **D12: Checking a connection from the page, plus a command for ops.**
  - It is a POST (it calls out), gated by `change_hostaccount`, which the IT desk holds (008, D2).
  - It proves:
    - the credentials (the token);
    - the user and their licence (`GET /users/{email}`, where a Basic user on a paid account is flagged);
    - the list scope.
  - It can't prove the create and delete scopes without making a real meeting. The owner's live check (criterion 48) covers those.
  - Results are shown, not stored. That means no new fields and no stale "last checked" data.
  - The command reuses `services.check_connection` for scripted checks after a secret rotation.
- **D13: Security.**
  - **Least-privilege scopes (granular names; the backend confirms them):**
    - `meeting:write:meeting:admin` (create a meeting);
    - `meeting:read:list_meetings:admin` (list a user's meetings);
    - `meeting:read:meeting:admin` (view a meeting, for recurring occurrences);
    - `meeting:delete:meeting:admin` (delete, for rollback and 011);
    - `user:read:user:admin` (view a user, for the connection check).
  - If a Marketplace app offers only classic scopes, the equivalents are `meeting:write:admin`, `meeting:read:admin` and `user:read:admin`.
  - **Not requested:** recording, user write, report, account, webinar or webhook scopes.
  - **HTTPS only**, with fixed hosts and certificate checks always on.
  - **No webhooks.** Nothing in this brief needs Zoom to call us: availability is asked for live at decision time. A public inbound endpoint would add a verification secret and an attack surface for no gain. They can be revisited if D15's drift matters in practice.
  - **The spreadsheet leaves the image** (criterion 44).
- **D14: The go-live gate** is 006, running `zoom` with every paid account connected, plus 011 (see Scope). It replaces 005's D14 and D19, and item 1 of 008's prerequisites.
- **D15: Known limits (for the README), with no code in this brief:**
  - Instant meetings, meetings with no fixed time and PMI meetings aren't seen as busy (D20).
  - Whether a teacher with only the host key can get in depends on each account's own "join before host" and "waiting room" settings (D19).
  - Changes made directly in Zoom to a meeting the app created aren't seen by the app. That includes moving it, or deleting it or one of its classes. The app keeps it as booked, so the account can look busy when it isn't. That errs on the safe side. Cancelling goes through 011.
  - The second or two between the lookup and the create (D6).
  - The timetable shows only app bookings (follow-up).
- **D16: The owner's setup, for each of the 11 paid accounts** (the docs writer turns this into the README section; no values ever go in the repo):
  1. Sign in at `marketplace.zoom.us` as the **owner or an admin of that Zoom subscription**. An admin's role needs the "Server-to-Server OAuth app" permission, under User Management → Roles.
  2. **Develop → Build App → Server-to-Server OAuth App → Create.** Name it `Polymath TMD`.
  3. **App Credentials:** copy the **Account ID**, **Client ID** and **Client Secret**.
  4. **Information:** fill in the required company and developer contact fields.
  5. **Scopes:** add exactly the D13 scopes, and nothing else.
  6. **Activation:** activate the app.
  7. In that subscription's Zoom settings, make sure **cloud recording** is enabled, since requesters can ask for it. Also make sure the account user's **host key** is set in its Zoom profile, and type it on the Zoom accounts page as today.
     - **Also check "Allow participants to join before host" and "Waiting room"** (Settings → Meeting). The app leaves both to the account (D19). A teacher who has only the host key has to be let into the meeting before they can "Claim host". So join before host needs to be on and the waiting room off, unless someone who can admit them is always there.
  8. On the server, in `zoom-credentials.env` (next to `.env`, never committed): add the slug to `ZOOM_CREDENTIAL_SETS`, e.g. `zoom-01`, then set `ZOOM_S2S_ZOOM_01_ACCOUNT_ID`, `ZOOM_S2S_ZOOM_01_CLIENT_ID` and `ZOOM_S2S_ZOOM_01_CLIENT_SECRET`.
  9. Recreate `web` (`docker compose up -d`) so it reads the file.
  10. On the Zoom accounts page, set that account's `Zoom connection name` to the slug, save, and press `Check connection`.
  11. When every paid account works: run `manage.py check_zoom_connections` and `manage.py check --database default`, then set `ZOOM_PROVIDER=zoom` in `.env` and recreate `web`.

  **Rotating a secret:** regenerate it on the app's App Credentials page, update the file, recreate `web`, and press `Check connection`. The two free accounts need no app, because they're never booked.
- **D17: Tests never call Zoom.**
  - A project-wide `responses` mock is always on, so an unregistered URL raises.
  - `ZoomProvider` tests register exact responses.
  - View tests steer `FakeProvider`: busy times per account, "unavailable" per account, and a record of deleted meetings.
  - The only live call is the owner's step in criterion 48.
- **D18: "Discard the spreadsheet" means it stops being used, not that it is deleted** (owner: "after the system comes, they will not be using spreadsheet to manage zoom links").
  - `Dashboard 2A.xlsx` stays on disk. No agent deletes it, moves it, reads it, imports from it or copies anything out of it. It is never a data source.
  - It stays git-ignored, and it is excluded from the Docker build context (criterion 44).
  - Bookings made before go-live exist only in Zoom, and the Zoom-side check (D7) protects them.
- **D19: The app keeps each Zoom account's own meeting defaults** (owner, Q1: "Keep Zoom's defaults"; this amends D10 and replaces the planner's recommendation).
  - The create payload sets only `auto_recording`. It never sends `join_before_host`, `jbh_time` or `waiting_room` (criteria 22 and 49).
  - **Risk the owner accepts:** the approval email tells the teacher to join and "Claim host" with the host key. If an account's own settings have the waiting room on, or join before host off, a teacher with only the host key can be **held in the waiting room**, or left waiting for a host who never starts the meeting. Nobody is there to admit them, so the class can't start.
  - **Mitigations:**
    - the setup step in D16, step 7, tells the owner to check both settings in each Zoom account;
    - the README repeats it under "Connecting to Zoom" and in the known limits (D15);
    - the owner's live check (criterion 48) records the test account's values.
  - Nothing in the app detects these settings. Reading them would need an extra account-settings scope, which D13 doesn't grant.
- **D20: Only dated meetings count as busy** (owner, Q2: "No, always dated", the planner's default).
  - These are ignored by the Zoom-side check: type 1 (instant), type 3 (recurring with no fixed time), type 4 (personal meeting ID, PMI), and any meeting with no `start_time` (criterion 12).
  - The README tells IT to always schedule classes in Zoom with a date and time, never on a no-fixed-time meeting or a PMI, because the app can't see those.
- **D21: 011 stays separate and comes straight after 006** (owner, Q3: "Separate, right after", the planner's default). See Scope and D1.

**Rulings on the Design section's contract gaps and copy proposals (2026-09-25)**

- **D22: The designer's contract gaps G1–G6 go into the contract as listed** (Design D.8). They're pinned in criteria 15 (G1, G2, G6), 17 (G3), 34 (G4) and 36 (G5), and in the context contract below.
  - **G3's order is confirmed: `has_started`, then `all_unchecked`, then "none free".**
    - A request whose first class has started can't be approved whatever Zoom says, so that notice is the true reason.
    - When no account could be checked, "No paid Zoom account is free" would be a claim the app can't make. It doesn't know whether they're free.
    - "None free" is left for when accounts were checked and found busy.
- **D23: Advice matches whether waiting helps** (the designer's P1, accepted by the main session under CLAUDE.md's rule that errors say how to fix the problem).
  - Every `ProviderError` carries a class attribute, `lasting` (`False` by default).
  - **Temporary:** `ZoomUnavailable` (no connection, a timeout, a 5xx) and `ZoomBusy` (429). The advice is `Try again in a few minutes.`
  - **Lasting:** `ZoomAuthFailed`, `ZoomMissingScope`, `ZoomUserNotFound` and `ZoomRejected`. The advice is `Choose another free account, and ask whoever manages the Zoom accounts to press Check connection for {label}.` (criteria 28 and 30). On the Check connection page itself, `ZoomRejected` gets its own "waiting won't fix this" text (criterion 36).
  - **Why `ZoomRejected` counts as lasting, although the main session named only three kinds:** it is every other 4xx, which means Zoom refused the request itself. Repeating the same request later gets the same answer. Calling it temporary would give exactly the wrong advice P1 set out to remove. Criterion 10's table pins all six kinds.
  - `ZoomNotConnected` and the date mismatch keep their own messages (criteria 29 and 24).
- **D24: Criterion 17's notice gains a sentence for when reloading won't help** (P2, accepted): `If this keeps happening, ask whoever manages the Zoom accounts to press Check connection for each account.`
- **D25: "We couldn't make the meeting in Zoom: …", worded truthfully for each failure** (P3, accepted, then checked against D6's marker design).
  - **The problem:** a read timeout or a 5xx on the create `POST` means the request reached Zoom. Zoom may have made the meeting anyway, so "nothing exists in Zoom" can't be claimed. "Nothing was booked" is still true **in the app**, and the text says "here" to keep the two apart.
  - **What the app does and says** (criterion 30(b)):
    - it makes one clean-up attempt (list, then delete every meeting carrying this request's `zoom_marker`);
    - the message then reports what that attempt **actually found**: removed, not found, or couldn't check;
    - each ending points to the one promise the design keeps (criterion 27): the next approve of this request deletes marker meetings before it creates one.
  - **Where no hedge is needed:** a connection error or connect timeout (nothing reached Zoom), a 429 and a 4xx are certain failures. They get the plain P3 sentence with no hedge.
  - **Orphans are still safe:** a leftover the app couldn't remove makes the account look busy. It can never cause a double booking (D6).
  - **005's criterion 40 is amended:** the fake's error now uses the P3 sentence.

**Risk register** (`delivery-execution:risk-register`, applied by the planner)

| # | Risk | Likelihood / impact | Mitigation in this brief | Owner |
|---|---|---|---|---|
| R1 | A booking that exists only in Zoom is missed: the list semantics, paging, no-fixed-time meetings, or the gap between lookup and create. **Added at close (review round 1 nit, docs-writer, 2026-09-25):** recurring series are read one after another, not in parallel, so an account with many of them (20 or more) can miss the availability preview's 8-second deadline | Low / **High** (double-booked class); the recurring-series read is Low / Low, because it fails closed to `Couldn't check with Zoom` rather than missing a clash | Fail closed on any error or page overflow (D7). Recurring meetings are expanded. The owner confirmed classes are always dated (D20). The owner's live check (criterion 48, step 2). The gap is seconds and documented. If the series-read limit bites in practice, the fix is to read them in parallel inside `busy_times` | backend, owner |
| R2 | An orphan meeting is left in Zoom after a failure | Low / Low | The compensating delete (criterion 31), the marker clean-up (criteria 27, 30), and the orphan message. An orphan only causes a false "busy" | backend |
| R3 | A credential or token leaks through logs, error pages, the image, the repo or the browser | Low / **High** | Env only, `ZOOM_S2S_SECRETS` masked, `sensitive_variables`, `urllib3` at `WARNING`, `.dockerignore`, and tests (criteria 3, 9, 11, 40, 44) | devops, backend, reviewer |
| R4 | Locks held during a slow create block another approval | Low / Low | A single `POST`, timeouts, narrow locks (D6) | backend |
| R5 | Zoom changes scope names or API behaviour | Medium / Medium | All HTTP in one module, the connection check, `manual` as a fallback, and confirmed names in the Implementation notes | backend, docs |
| R6 | Rate limits | Low / Low | The per-account limits, the 60-second preview cache, no retries (D9) | backend |
| R7 | Changes made directly in Zoom drift from the app | Medium / Low | Documented (D15). Cancelling goes through 011. Webhooks deferred | docs |
| R8 | The spreadsheet with host keys is baked into the prod image today | **Present** / **High** | `.dockerignore` fix (criterion 44, delivered early). The owner has been told that images built before the fix contain it | devops |
| R9 | A teacher with only the host key is held in the waiting room, or can't join before the host, because of an account's own defaults (D19, accepted by the owner) | Medium / Medium (the class can't start) | The setup note (D16, step 7), the README, and the owner's check (criterion 48). The app never overrides the settings (criterion 49) | owner, docs |

## MVT plan
<!-- owner: tmd-planner -->

### Models

In `apps/zoom/models.py`, with one migration, `0005_zoom_connection`. It is numbered after `0004`. If another brief lands first, the later one renumbers.

**`HostAccount`**

- `credential_set` stays `SlugField(40, blank=True)` and gains:
  - a `RegexValidator(r"^[a-z0-9]+(-[a-z0-9]+)*$", message=…)` (criterion 34);
  - the new help text (criterion 34);
  - the verbose name `Zoom connection name`.
- `label`'s help text loses "like the heading in the old spreadsheet". It becomes `IT's short name for the account, like Zoom 01.`
- New property `zoom_connection_state -> "none" | "missing" | "ready"`. It reads `settings.ZOOM_S2S_SECRETS`, with no query and no HTTP.
- New method `is_zoom_connected() -> bool`, which is `zoom_connection_state == "ready"`. It is the one definition, used by the preview, `approve()` and E004.
- `bookable()` is **unchanged**. It is a business rule (in use and paid), and "connected" is an operational state, checked separately so that `manual` still works without credentials.

**`LinkRequest`**

- New property `zoom_marker -> str`: `f"Polymath TMD {self.reference}"`. It is the one place the agenda marker is defined.

**`Occurrence`**

- New field `zoom_occurrence_id = CharField("Zoom occurrence ID", max_length=20, blank=True)`. It is set only by `approve()` for weekly meetings, and read by 011.

**The module docstring:** "the 007 import" is removed from the list of paths that share `clean()`.

**No new status.** The state table in 005 is unchanged: a failed approval stays `waiting`, as today.

**Provider layer (`apps/zoom/providers.py`), the D4 interface of 005, extended:**

| Member | Fake | Manual | Zoom |
|---|---|---|---|
| `needs_manual_details` | False | True | False |
| `checks_zoom` | True | False | True |
| `busy_times(*, host_account, start, end) -> list[BusyTime]` | Class-level steerable `busy`/`unavailable` per account id | never called | Criteria 12 and 13 |
| `create_meeting(*, link_request, host_account, occurrences, manual=None) -> Meeting` | As today | As today | Criteria 22–25 |
| `delete_meeting(*, host_account, meeting_id, occurrence_id=None)` | Records in `deleted` | No-op | `DELETE /meetings/{id}[?occurrence_id=]`, with `schedule_for_reminder=false` |
| `check_connection(host_account) -> ConnectionResult` | not used | not used | Criterion 36 (always `ZoomProvider`) |

- `Meeting` gains `occurrence_ids: tuple[tuple[datetime, str], ...] = ()`. It still has no `start_url`.
- `BusyTime(starts_at, ends_at, topic, meeting_id, agenda)` is a frozen dataclass.
- `ProviderError(user_message)` keeps its shape, and gains the class attribute `lasting = False` (D23). Its subclasses are `ZoomUnavailable`, `ZoomBusy`, `ZoomAuthFailed`, `ZoomMissingScope`, `ZoomUserNotFound`, `ZoomRejected(code)` and `ZoomNotConnected`.

**`apps/zoom/zoom_api.py` (new):**

- `ZoomClient(slug, credentials)` has `get`, `post` and `delete`, plus `paged(path, params, key, max_pages=10)`.
- It holds the module-level token cache, a dictionary under a `threading.Lock`, and `reset_token_cache()` for tests.
- It is the only importer of `requests`. Every function holding a secret or token is `@sensitive_variables`.

**`apps/zoom/services.py`:**

- **`approve()`:** the order in D6. The existing outcomes stay, and the Zoom outcomes map onto `CONFLICT` (409: a Zoom clash, not connected) and `PROVIDER_ERROR` (200: lookup or create failures, date mismatch, orphan). The new copy constants live here, next to 005's.
- **`availability(link_request, occurrences, *, provider=None) -> AvailabilityResult`:**
  - it calls `HostAccount.objects.availability_for()` (unchanged, database only);
  - if `provider.checks_zoom`, it runs the parallel, cached Zoom lookups (D8) for connected accounts;
  - it returns the entries in the context contract, plus `zoom_checked_at` and `all_unchecked`.

  Views stay thin, and it is the one place that combines the two sources.
- **`check_connection(account) -> ConnectionResult(level, message)`** (criterion 36).

**`apps/zoom/checks.py`:** E001 copy, E002 lists three values, new E004 (`Tags.database`), E005 and W001 (`Tags.deploy`), all registered explicitly in `ZoomConfig.ready()` as today.

**`apps/zoom/management/commands/check_zoom_connections.py`** (criterion 37).

**Information architecture** (`ux-strategy:information-architecture`). No new page and no new nav item. Each change sits where the task happens:

```
[Zoom links]
├── Link requests      zoom:queue
│   └── ZL-0042 …      zoom:detail   ← availability now says what Zoom says, per account
├── Timetable          zoom:timetable (unchanged; Zoom-only meetings are a follow-up)
└── Zoom accounts      zoom:accounts ← new "Zoom connection" column
    ├── Add a Zoom account       zoom:account_add   ← "Zoom connection name" field
    └── Change Zoom 03           zoom:account_edit  ← field, state line, [Check connection]
                                  └─ POST zoom:account_check → back here with a message
```

- **Labels** use the IT desk's words: `Zoom connection`, `Set up`, `Not set up`, `Missing on the server`, `Check connection`, `Couldn't check with Zoom`, `Not connected to Zoom` and `In Zoom:`. There's no "credential set", "OAuth", "scope" or "token" on any screen. The README carries the technical names for whoever looks after the server.
- **Wayfinding:** the check returns to the page where it was pressed. A `Not connected to Zoom` account on a request detail links to its `Change {label}` page for users with `change_hostaccount`.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `zoom:detail` (changed) | `zoom/requests/<int:pk>/` | `LinkRequestDetailView`, now `@method_decorator(transaction.non_atomic_requests, name="dispatch")`. `review_context` calls `services.availability()` | `zoom/detail.html` | `zoom.review_linkrequest` |
| `zoom:approve` (changed) | as today | `ApproveView`, unchanged apart from rendering the new outcomes. It is already non-atomic | `zoom/detail.html` (re-render) | `zoom.review_linkrequest` |
| `zoom:reject` (unchanged; its re-render gets the new context through `review_context`) | as today | `RejectView` | `zoom/detail.html` | `zoom.review_linkrequest` |
| `zoom:accounts` (changed context) | as today | `HostAccountListView` | `zoom/accounts.html` | `zoom.view_hostaccount` |
| `zoom:account_add` / `zoom:account_edit` (changed form and context) | as today | `HostAccountCreateView` / `HostAccountUpdateView` | `zoom/account_form.html` | `add_` / `change_hostaccount` |
| **`zoom:account_check`** (new) | `zoom/accounts/<int:pk>/check/` | `HostAccountCheckView(SignedInPermissionMixin, SingleObjectMixin, View)`, POST only, `non_atomic_requests`. It calls `services.check_connection`, then `messages.<level>` and a redirect to `zoom:account_edit` | none (302) | `zoom.change_hostaccount` |

The paths above are for orientation only: templates and code use the names.

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Everywhere:** unchanged from 005 and 008.

**`zoom/detail.html`** (detail, approve and reject re-renders). Every existing variable is kept. Changed or added:

| Variable | Type | Notes |
|---|---|---|
| `availability` | list of dict | Each entry: `account` (HostAccount), `is_free` (bool: **offered**, meaning no database clash, no Zoom clash and `zoom_state` in `checked`/`off`), `has_host_key` (bool), `busy_count` (int, criterion 15), `clashes` (list of `{occurrence, other}`, database, unchanged), **`zoom_clashes`** (list of `{occurrence: Occurrence, busy: BusyTime}`, where `busy.starts_at`/`ends_at` are aware and `busy.topic` is str (maybe empty). **G2:** sorted by `occurrence.starts_at`, then `busy.starts_at`), **`zoom_state`** (`"checked"`, `"off"`, `"unavailable"` or `"not_connected"`), **`zoom_problem`** (str. **G6:** a capitalised sentence ending in a full stop, e.g. `Zoom is busy right now.`, for `unavailable`, else `""`), **`account_edit_allowed`** (bool. **G1:** set on **every** entry, true when the user has `zoom.change_hostaccount`, and used for the fix link on both `unavailable` and `not_connected` rows) |
| `checks_zoom` | bool | The provider asks Zoom. False for `manual` (show criterion 18's notice) |
| `zoom_checked_at` | aware datetime or `None` | Criterion 16 |
| `all_unchecked` | bool | Criterion 17. When true, `approve_form` is `None` |
| `has_started` | bool | Unchanged from 005, and **G3:** always present, including when `all_unchecked` is true. The template's no-approve-form notice goes, in order: `has_started`, then `all_unchecked`, then "none free" (D22). `approve_form` is `None` in all three |
| `free_count` | int | Now counts offered accounts only |
| `approve_error` | str or `None` | Carries criteria 24 and 26–31's messages, in their final form: the lasting or temporary next step (D23) and the timeout endings (D25). The template prints it as is |

**`zoom/accounts.html`:** every `accounts` item also exposes `zoom_connection_state` (`"none"`, `"missing"` or `"ready"`), a model property with no query. Nothing else changes.

**`zoom/account_form.html`:**

| Variable | Type | Notes |
|---|---|---|
| `form` | `HostAccountForm` | Gains `credential_set` (after `sort_order`). **G4:** its widget has `autocomplete="off"`, `autocapitalize="none"`, `spellcheck="false"` and `maxlength="40"`, set on the form along with its label and help (criterion 34) |
| `account` | `HostAccount` or `None` | Unchanged from 008. **G5:** always present when `can_check_connection` is true, because the check form's action uses `account.pk` |
| `zoom_connection_state` | str | From the **stored** row (like `host_key_state`), `"none"` on add |
| `zoom_connection_name` | str | The stored slug, for the `missing` sentence. `""` on add |
| `can_check_connection` | bool | True on change pages for users with `change_hostaccount`. Always false on the add page. The button posts to `{% url 'zoom:account_check' account.pk %}`. It is shown for every state, since criterion 36 explains `none` and `missing` |

**Messages:** criterion 36's messages arrive through `messages` on `zoom:account_edit`, at the levels in its table.

**Formatting:** the `zoom_format` filters (`class_date`, `class_time`) for every Zoom time. Topics are auto-escaped.

### Placement and reuse

- **`apps/zoom`:**
  - new: `zoom_api.py` and `management/commands/check_zoom_connections.py`;
  - changed: `providers.py`, `services.py`, `checks.py`, `models.py`, `forms.py`, `views.py` and `urls.py`;
  - migration `0005`.
- **Tests:**
  - new: `tests/test_zoom_api.py`, `tests/test_zoom_provider.py`, `tests/test_zoom_approve.py` (ordering, compensation, races), `tests/test_zoom_preview.py` and `tests/test_zoom_accounts_connection.py`;
  - changed: `conftest.py` (steerable fake, cache resets), `test_accounts.py` (the `credential_set` amendment), and the checks tests.
  - New project-level `conftest.py`: the global `responses` mock (criterion 45). It is owned by `tmd-devops`, since it's test infrastructure and not zoom code.
- **`templates/zoom/`:** `detail.html`, `accounts.html` and `account_form.html`. The designer decides whether a new `zoom/partials/zoom_clash.html` is worth it. Icons come from the sprite, with any new symbols listed by the designer.
- **`config/`:** `settings/base.py` (credential parsing, `LOGGING` for `urllib3`), `settings/prod.py` (message) and `settings/test.py` (unchanged provider).
- **Root:** `compose.yaml`, `zoom-credentials.env.example`, `.env.example`, `.gitignore`, `.dockerignore`, `requirements/base.txt` and `requirements/dev.txt`.
- **Reused:**
  - 005's `availability_for` (the database clashes), the slot backstop, the locks, the deadlock retry, and the `Outcome`/`ApproveResult` shapes;
  - the error summary and the notice, tag and availability components;
  - `SignedInPermissionMixin`;
  - Django's cache, messages, `sensitive_variables`, `SafeExceptionReporterFilter`, `non_atomic_requests` and system checks with tags;
  - stdlib `concurrent.futures`.
- **Not built:**
  - webhooks;
  - a Zoom SDK;
  - token or result storage;
  - a new status;
  - per-occurrence meetings;
  - a Zoom settings screen beyond the one field;
  - timetable changes.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Done (2026-09-25).** The owner answered Q1–Q3 (D19–D21) and was told about R8. Criterion 44 was delivered early by `tmd-devops`. The main session pastes devops's notes into the Implementation notes.
1. **Done (2026-09-25): `tmd-ui-designer`.** The Design section is written. Its gaps G1–G6 and proposals P1–P3 are folded in as D22–D25. The contract above is now fixed.
2. **`tmd-devops`, alone and first.** The backend and frontend both need `requests` and `responses` in the rebuilt dev image before they can run anything. It delivers:
   - `requests` and `responses` pinned, and the dev image rebuilt;
   - the `base.py` credential parsing, `ZOOM_S2S_SECRETS` and the `urllib3` logging;
   - the `prod.py` message;
   - `compose.yaml` `env_file`, `zoom-credentials.env.example`, `.env.example` and `.gitignore`;
   - the project-level `conftest.py` network block.

   Criteria 2, 3, 7, 42 and 45. Criterion 44 was delivered early; this step only adds `zoom-credentials.env` to `.dockerignore` if the early fix didn't. Devops runs its own `pytest --create-db`, and finishes it before step 3 starts.
3. **In parallel, after step 2:**
   - **3a. `tmd-django-backend`:**
     - `zoom_api.py` (with the `lasting` flag, D23), providers, services (with D25's clean-up endings), checks and the command;
     - models and migration `0005`;
     - forms (G4), views (G1–G3, G5 and G6 in the context) and URLs;
     - every test for criteria 1, 4–6, 8–41 and 49 (the logic), including the amended 005 criterion 40 test.

     It records the confirmed scope names, the token-endpoint parameter placement and the list/occurrence behaviour in the Implementation notes.
   - **3b. `tmd-frontend`:** the build list in Design D.7, against the fixed contract. That means the templates (including `zoom/partials/avail_item.html`), `account_tag.html`'s `kind="zoom"`, the icons, the CSS and the busy-button JS. It covers criteria 15–18, 34–36 (the markup) and 43.

   **Only the backend runs `pytest --create-db`** (they share `test_<MYSQL_DATABASE>`, and the backend adds `0005`). The frontend never uses `--create-db`. It runs `pytest` (reusing the database) only after the backend has reported that its `--create-db` run finished. Until then, it limits itself to `ruff` and its own template checks. The main session passes that signal on.
4. **`tmd-test-verifier`:** criteria 1–47 and 49 (44 is re-checked even though it was delivered early), including both `check --deploy` runs and the prod walkthrough, without contacting Zoom. It is the next agent to run `pytest --create-db`, and only after both 3a and 3b have finished.
   - A FAIL goes back to 2, 3a or 3b with the report.
   - Then the **main session gives the owner criterion 48's steps**. The verifier records the owner's reported results. Until the owner has run them, the task stays in `Verifying`, not `Done`.
5. **`tmd-code-reviewer`** (read-only). Focus:
   - secrets: env only, masking, logging, the image, the browser;
   - HTTPS and scopes;
   - `approve()` ordering, lock scope and the compensating delete;
   - fail-closed paths;
   - thread safety of the token cache and the preview;
   - that views stay thin.

   It also checks that every approve-failure message is honest about what exists in Zoom (D25), and that the next step it gives matches the `lasting` flag (D23). CHANGES REQUESTED goes back to step 2, 3a or 3b, then step 4.
6. **`tmd-docs-writer`:** updates the docs, then closes the brief.
   - **README:** a new "Connecting to Zoom" section (D16's setup, the scopes, rotating a secret, `check_zoom_connections`, `check --database default`), D15's known limits, and the manual-mode paragraph reworded as a fallback.
   - **Two README notes from the owner's answers:**
     - check "join before host" and "Waiting room" in each Zoom account (D19);
     - always schedule classes in Zoom with a date and time, never on a no-fixed-time meeting or a PMI (D20).
   - **Design follow-ups at close:** append D.1.4's states to `docs/design/availability-list.md`, and keep `docs/design/busy-button.md` as the busy button's one definition.
   - **The go-live gate replaced** (D14). The docs that mention 007 or the import are listed below.

**Docs that mention 007, the import or the old gate, for the docs writer to fix at close.** Closed briefs are records: add a dated "Amended by 006" note next to each passage rather than rewriting history.

| File | Where | What to fix |
|---|---|---|
| `README.md` | lines 251–264 ("Manual mode, until a later brief adds the live Zoom API"; go-live gate item 1: "A later brief (007) imports the bookings…") | Replace with the D14 gate. `manual` becomes the fallback |
| `CLAUDE.md` | the `zoom` bullet under Architecture ("`manual` for production until a later brief adds the live Zoom API"; "the importer in task 007 is the first other caller") | The providers are now `fake`/`manual`/`zoom`. Drop the 007 caller. Keep the "call `approve()` outside an open transaction" rule, and note that it now also makes HTTP calls |
| `CLAUDE.md` | Environment gotchas: the `ZOOM_PROVIDER` bullet; "Adding an env var" | The `zoom-credentials.env` `env_file` exception (D2). `check --database default` for E004. `check --deploy` is run with `ZOOM_PROVIDER=zoom` and dummy sets, because `manual` now raises `zoom.W001` |
| `docs/CHANGELOG.md` | line 99 (010 entry), line 142 (008 follow-ups), lines 185–186 and 193–196 (005 entry: the gate, and "brief 007 imports future bookings…") | Add the 006 entry. Note that 007 was dropped on 2026-09-25 and that the gate is now 006 + 011 |
| `docs/tasks/005-zoom-link-requests.md` | line 48 (the 007 row), line 50 (the gate), line 96, line 494, lines 571–576 (D14), lines 625–628 (D19), line 1041, line 1055, around line 2474 (the Docs section's 007 item) | Add an "Amended by 006 (2026-09-25): 007 dropped; gate = 006 + 011" note. Also D4 and D16 (the provider and naming, superseded by 006's D2) |
| `docs/tasks/008-zoom-accounts.md` | line 51 ("Briefs 006 and 007 … keep their numbers"), line 57 (prerequisite 1), line 419 (D11: "alongside brief 007"), line 597, line 1323, and D5 at line 407 (`credential_set` now on the form) | Amendment notes |
| `docs/tasks/009-zoom-timetable.md` | line 1299 (the go-live prerequisites, naming 011 only) | Doesn't name 007. Add that the gate now also needs 006 |
| `docs/tasks/010-staff-and-access.md` | line 472 ("brief 005's go-live gate") | Doesn't name 007. Point to the gate as redefined by 006 |
| `apps/zoom/models.py` | module docstring, line 12 ("the 007 import") | **Code, fixed by the backend in step 3**, not the docs writer |
| Memory note `zoom-requests-feature.md` (outside the repo) | line 30 already records the drop and the new gate | **Main session**, not the docs writer. Add D18's meaning of "discard": the file stays on disk, but it is never used or imported |

**Next after 006:** plan brief 011 ("Cancel this booking") on top of 006's `delete_meeting` and `zoom_occurrence_id`.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

Built inside the approved f-desk direction, and on the component notes from 005 and 008 (`availability-list.md`, `form-section.md`, `flash-messages.md`, `status-tabs.md`, and 008's Design D.1–D.8). Every pinned string in the criteria is used **exactly as written**. Anything marked *design copy* below is new wording from this section. Anything marked *proposal* needs the main session's approval (see D.9); the layout doesn't depend on it.

**Summary of what changes:**

| Kind | What |
|---|---|
| New component | **Busy submit button** (`data-busy-text`), in `docs/design/busy-button.md`: a small JS enhancement for the two slow POSTs |
| Extended component | `.avail` gains one element, `.avail__note` (D.1.4). The docs writer copies D.1.4 into `docs/design/availability-list.md` at close, so the component stays defined in one place |
| Small CSS additions | `.avail__note`, `.datagrid--wrap-tags`, `.button[aria-disabled="true"]` (D.7) |
| New partial | `zoom/partials/avail_item.html`: one availability row with all its states (D.1.3). Chosen instead of the planner's suggested `zoom_clash.html`, because the state logic, not the clash line, is what makes `detail.html` hard to read |
| Changed partial | `zoom/partials/account_tag.html` gains `kind="zoom"` (D.2.2) |
| New icons | `i-help-circle` and `i-link`, both Feather (D.7) |
| Emails | **No change.** `approved_body.txt` already prints whatever link, ID and passcode are stored, and the brief rules out changing its wording. `request_sent.html` and the confirm email say nothing about how links are made, so they're correct as they are |

### D.1 Request detail: `zoom/detail.html`

#### D.1.1 Page structure (the order is unchanged from 005)

`approve_error` notice → decided line → **Request** → **Classes** → **Which accounts are free** (changed) → **Also waiting at overlapping times** → **Approve and send the link** (changed), or the no-approve notice (changed) → **Reject this request**.

#### D.1.2 The `Which accounts are free` box: the lead

`p.box__lead`, chosen in this order:

| Condition | Lead text |
|---|---|
| `availability` is empty | unchanged from 008 D.6 (`No paid Zoom accounts are set up yet. …`) |
| `all_unchecked` | *design copy:* `None of the {total} paid account(s) could be checked with Zoom.` |
| `checks_zoom` is false (manual) | unchanged from 005: `{free_count} of {total} paid accounts are free for every class. Checked against approved bookings when this page loaded.` |
| otherwise (`checks_zoom`) | `{free_count} of {total} paid accounts are free for every class. Checked against approved bookings when this page loaded.` then, when `zoom_checked_at` is set, a space and the pinned `Checked with Zoom at <time datetime="{iso}">{zoom_checked_at\|class_time}</time>.` (criterion 16) |

- `{total}` is `availability|length`, as today, and the plurals are as today.
- The "checked at" time matters because of the 60-second cache: it can be up to a minute older than the page.

#### D.1.3 One row: `zoom/partials/avail_item.html`

Include it with `{% include "zoom/partials/avail_item.html" with entry=entry total=occurrence_count only %}`, inside the existing `ul.avail`. It renders one `li.avail__item`: `.avail__who` (name and email, unchanged), **one** tag, then the row's detail. Branch on `entry.zoom_state` **first**:

| `zoom_state` | Tag (column 2) | Below (full width) |
|---|---|---|
| `"unavailable"` | `tag tag--warn`, icon **`help-circle`**, `Couldn't check with Zoom` (pinned) | `p.avail__note`: `{entry.zoom_problem}` (pinned, e.g. `Zoom is busy right now.`), then *design copy* ` It can't be booked until Zoom can be checked.` Then, when `entry.account_edit_allowed`, a space and `a.tap-link` → `zoom:account_edit entry.account.pk`: `Check the Zoom connection for {label}` |
| `"not_connected"` | `tag tag--warn`, icon **`slash`**, `Not connected to Zoom` (pinned) | `p.avail__note`: *design copy* `This account has no working Zoom connection yet, so it can't be booked.` Then either a space and `a.tap-link` → `zoom:account_edit entry.account.pk`: `Set up the Zoom connection for {label}` (when `account_edit_allowed`), or ` Ask someone in the IT desk to set it up.` |
| `"checked"` or `"off"`, `is_free` | `tag tag--ok`, `check-circle`, `Free for all {n} classes` (unchanged) | nothing |
| `"checked"` or `"off"`, not free | `tag tag--warn`, `alert-triangle`, `Busy for {busy_count} of {n} classes` (unchanged) | `ul.avail__clashes`: the database clash `li`s first, exactly as 005 renders them, then one `li` per `entry.zoom_clashes` item (below) |

**The Zoom clash line** (criterion 15). It's one `li` in the same `ul.avail__clashes`, on two lines:

```html
<li>{% include "zoom/partials/class_span.html" with start=clash.occurrence.starts_at end=clash.occurrence.ends_at only %}<br>
    In Zoom: <span class="break-anywhere">{{ clash.busy.topic|default:"a meeting with no name" }}</span>, {{ clash.busy.starts_at|class_time }}–{{ clash.busy.ends_at|class_time }}</li>
```

- Line 1 is the class: its date and this request's time, the same partial the database rows use.
- Line 2 is the pinned `In Zoom: {topic}, {start}–{end}`, with an en dash and no link, since there's nothing in the app to link to.
- The topic is auto-escaped. *Design copy:* an empty topic reads `a meeting with no name`.
- **Why two lines and not "clashes with":** the database rows read "… clashes with ZL-0031 Grade 10 Science". "Clashes with In Zoom: …" doesn't read as a sentence, and the Busy tag above already says these are clashes. The `In Zoom:` prefix is what tells the two kinds apart. That's words, not colour.
- The backend orders `zoom_clashes` by class start (gap G2).

**Why these icons:** `help-circle` means "we don't know" (the account may well be free). `slash` means "switched off / not set up", matching the staff list's `Switched off`. Busy keeps `alert-triangle`. So the three non-free states have three different icons as well as three different words.

**Why no database clashes on the unavailable and not-connected rows:** the account isn't offered either way, and one clear reason reads faster than a mixed list. When Zoom answers again, the row shows its full clash list.

#### D.1.4 `.avail__note` (added to the `.avail` component)

| Part | Spec |
|---|---|
| `.avail__note` | `grid-column: 1 / -1; margin: 0; color: var(--c-text); line-height: var(--lh-body);` |
| Link inside | ported link colour and underline. `.tap-link` makes it 44px below 768px |
| Below 600px | unchanged (one column: who, tag, note) |

Contrast: `--c-text` on `--c-surface` 12.44 (light) / 6.45 (dark), as in `status-tabs.md`.

**States for `availability-list.md`** (the docs writer appends these rows to its States table at close):

| State | Tag | Below |
|---|---|---|
| Couldn't check (another service didn't answer) | `tag--warn`, `help-circle`, `Couldn't check with Zoom` | `.avail__note`: the reason, what it means, and an optional fix link |
| Not connected | `tag--warn`, `slash`, `Not connected to Zoom` | `.avail__note`: what it means, and a fix link or who to ask |
| Busy because of the other service | `tag--warn`, `alert-triangle`, `Busy for …` | a `.avail__clashes` `li` on two lines: the class, then `In Zoom: {topic}, {start}–{end}` |

#### D.1.5 Desktop wireframe (1440, `zoom` provider, mixed states)

```
ZL-0042: Grade 11 Physics                        Home › Zoom link requests › ZL-0042
┌ Request … ┐  ┌ Classes (8) … ┐   (unchanged)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Which accounts are free                                                          │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1 of 4 paid accounts are free for every class. Checked against approved          │  box__lead
│ bookings when this page loaded. Checked with Zoom at 10:02 am.                   │
│                                                                                  │
│ Zoom 01                                          [✓ Free for all 8 classes]      │
│ zoom01@polymath.edu.lk                                                           │
│ ──────────────────────────────────────────────────────────────────────────────── │
│ Zoom 02                                          [△ Busy for 2 of 8 classes]     │
│ zoom02@polymath.edu.lk                                                           │
│   • Wed 7 Oct 2026, 8:30 am to 11:30 am clashes with ZL-0031 Grade 10 Science,   │  database clash
│     9:00 am to 12:00 pm                                                          │
│   • Mon 12 Oct 2026, 8:30 am to 11:30 am                                         │  Zoom clash, line 1
│     In Zoom: Grade 11 revision (old booking), 9:00 am–10:00 am                   │           line 2
│ ──────────────────────────────────────────────────────────────────────────────── │
│ Zoom 03                                          [? Couldn't check with Zoom]    │
│ zoom03@polymath.edu.lk                                                           │
│ Zoom is busy right now. It can't be booked until Zoom can be checked.            │  .avail__note
│ Check the Zoom connection for Zoom 03                                            │  link (edit allowed)
│ ──────────────────────────────────────────────────────────────────────────────── │
│ Zoom 04                                          [⊘ Not connected to Zoom]       │
│ zoom04@polymath.edu.lk                                                           │
│ This account has no working Zoom connection yet, so it can't be booked.          │
│ Set up the Zoom connection for Zoom 04                                           │
└──────────────────────────────────────────────────────────────────────────────────┘
┌ Approve and send the link ────────────────────────────────────────────────────────┐
│  Book it on                                                                      │
│  (•) Zoom 01  zoom01@…  [⚷ Host key saved]                                       │  only offered accounts
│  [ Approve and email the link ]                                                  │  busy: "Making the meeting in Zoom…"
└──────────────────────────────────────────────────────────────────────────────────┘
┌ Reject this request … ┐
```

(In the real page the note's link sits inline after the sentence and wraps naturally. It's drawn on its own line here only for width.)

#### D.1.6 Phone wireframe (400)

```
┌──────────────────────────────────────┐
│ ZL-0042: Grade 11 Physics            │
│ ┌──────────────────────────────────┐ │
│ │ Which accounts are free          │ │
│ ├──────────────────────────────────┤ │
│ │ 1 of 4 paid accounts are free    │ │
│ │ for every class. Checked …       │ │
│ │ Checked with Zoom at 10:02 am.   │ │
│ │ Zoom 02                          │ │  one column below 600px:
│ │ zoom02@polymath.edu.lk           │ │  who, tag, detail
│ │ [△ Busy for 2 of 8 classes]      │ │
│ │ • Mon 12 Oct 2026, 8:30 am to    │ │
│ │   11:30 am                       │ │
│ │   In Zoom: Grade 11 revision     │ │
│ │   (old booking), 9:00 am–        │ │
│ │   10:00 am                       │ │
│ │ ──────────────────────────────── │ │
│ │ Zoom 03                          │ │
│ │ zoom03@polymath.edu.lk           │ │
│ │ [? Couldn't check with Zoom]     │ │
│ │ Zoom is busy right now. It can't │ │
│ │ be booked until Zoom can be      │ │
│ │ checked. Check the Zoom          │ │  44px tap-link
│ │ connection for Zoom 03           │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

#### D.1.7 The approve box, and the notice when there's no approve form

**With `approve_form`.** It's inside `.box__form`, in this order:

1. `partials/error_summary.html` (unchanged).
2. **Manual mode only** (`not checks_zoom`), criterion 18. It's a `div.notice.notice--warn` with the `alert-triangle` icon and `div.notice__body`:
   - `p.notice__title`: *design copy* `Check Zoom for clashes first`;
   - `p`: `This system can't see meetings made directly in Zoom. Before you approve, check the chosen account's meetings in Zoom.` (pinned).

   It's **warn**, not note, because it's a real double-booking risk. It comes **before** the existing `Create the meeting in Zoom first` note, because you check first, then create.
3. The existing manual `notice--note` (when `needs_manual_details`), unchanged.
4. The form, unchanged, apart from the submit button. The button gains `data-busy-text`: `Making the meeting in Zoom…` when `checks_zoom`, `Approving…` otherwise. The `<form>` gains `data-busy-form`, and `.form-actions` gains the empty `p.visually-hidden[role=status][data-busy-status]` (`busy-button.md`).

**Without `approve_form` (the `{% else %}` branch).** It's one `div.notice.notice--warn` with `alert-triangle` and `p`, in this order of precedence:

| Condition | Text |
|---|---|
| `has_started` | unchanged (`The first class has already started. …`) |
| `all_unchecked` | `We couldn't check the Zoom accounts just now, so nothing can be approved. Reload the page in a few minutes. If this keeps happening, ask whoever manages the Zoom accounts to press Check connection for each account.` (pinned, criterion 17; the last sentence is D24) |
| otherwise | unchanged (`No paid Zoom account is free for every class in this request. …`) |

The reject box stays in every case.

**Wireframe (400, `all_unchecked`):**

```
│ ┌ △ We couldn't check the Zoom ────┐ │  notice--warn, in place of the approve box
│ │   accounts just now, so nothing  │ │
│ │   can be approved. Reload the    │ │
│ │   page in a few minutes. If this │ │
│ │   keeps happening, ask whoever   │ │
│ │   manages the Zoom accounts to   │ │
│ │   press Check connection for     │ │
│ │   each account.                  │ │
│ └──────────────────────────────────┘ │
│ ┌ Reject this request ─────────────┐ │
```

#### D.1.8 Approval outcomes

**Success.** Unchanged from 005: a redirect to the detail with the success flash `Approved. The link was emailed to {email}.`, or the warning flash if the email failed. The `Request` box then shows `Booked on`, `Zoom link`, `Meeting ID` and `Passcode`, which are now Zoom's real values. Nothing new is designed; the link is already a `tap-link` and `break-anywhere` wraps a long URL.

**Every failure** (criteria 24 and 26–31). It uses the existing top-of-page `div.notice.notice--bad[role=alert][tabindex=-1][data-error-summary]`, with the `alert-octagon` icon, `p.notice__title` `Nothing was booked`, and `p` `{{ approve_error }}`. It's re-rendered with the refreshed availability, so a now-busy or unchecked account shows its new state in the list and has left the radio list.

| Criterion | Status | `approve_error` (pinned, filled in) | What the user does next |
|---|---|---|---|
| 26 Zoom clash | 409 | `Zoom 02 has a meeting in Zoom at an overlapping time: Grade 11 revision, Mon 5 Oct 2026 at 8:00 am. Choose another free account.` | picks another free account below |
| 29 not connected | 409 | `Zoom 04 isn't connected to Zoom yet, so it can't be booked. Choose another free account, or set up its Zoom connection on the Zoom accounts page.` | as it says |
| 28 lookup failed, temporary (`ZoomUnavailable`, `ZoomBusy`) | 200 | `We couldn't check Zoom 02's meetings in Zoom, so nothing was booked. Zoom is busy right now. Try again in a few minutes.` | waits and retries |
| 28 lookup failed, lasting (`ZoomAuthFailed`, `ZoomMissingScope`, `ZoomUserNotFound`, `ZoomRejected`) | 200 | `We couldn't check Zoom 02's meetings in Zoom, so nothing was booked. Zoom didn't accept this account's connection details. Choose another free account, and ask whoever manages the Zoom accounts to press Check connection for Zoom 02.` | picks another free account, and passes the account on to IT |
| 27 leftover delete failed | 200 | criterion 28's message, with its temporary or lasting next step, e.g. `We couldn't check Zoom 02's meetings in Zoom, so nothing was booked. No answer from Zoom. Try again in a few minutes.` | as criterion 28 |
| 30(a) create failed, Zoom certainly made nothing, temporary | 200 | `We couldn't make the meeting in Zoom: Zoom is busy right now. Nothing was booked. Try again in a few minutes.` | waits and retries |
| 30(a) create failed, Zoom certainly made nothing, lasting | 200 | `We couldn't make the meeting in Zoom: Zoom error 300. Nothing was booked. Choose another free account, and ask whoever manages the Zoom accounts to press Check connection for Zoom 02.` | picks another free account, and passes the account on to IT |
| 30(b) create failed, Zoom may have made it; clean-up found and removed it | 200 | `We couldn't make the meeting in Zoom: no answer from Zoom, so Zoom may have made it anyway. Nothing was booked here. We found it in Zoom 02's Zoom account and removed it. Try again in a few minutes.` | waits and retries |
| 30(b) as above; clean-up found nothing | 200 | `We couldn't make the meeting in Zoom: no answer from Zoom, so Zoom may have made it anyway. Nothing was booked here. We didn't find it in Zoom 02's Zoom account. Try again in a few minutes. If it turns up there later, the next try removes it before making a new one.` | waits and retries |
| 30(b) as above; clean-up couldn't check | 200 | `We couldn't make the meeting in Zoom: no answer from Zoom, so Zoom may have made it anyway. Nothing was booked here. We couldn't check Zoom 02's Zoom account for it. Try again in a few minutes. If a meeting for ZL-0042 is there, the next try removes it before making a new one.` | waits and retries |
| fake provider (005 criterion 40, amended by criterion 30) | 200 | `We couldn't make the meeting in Zoom: Zoom is not responding. Nothing was booked. Try again in a few minutes.` | retries |
| 24 dates differ | 200 | `Zoom scheduled different dates from this request, so the meeting was removed from Zoom and nothing was booked. Tell whoever looks after the system.` | reports it |
| 31 saved-then-failed, delete also failed | 200 | `Zoom made meeting 812 3456 7890 on Zoom 02, but it couldn't be saved here or removed from Zoom. Delete that meeting in Zoom, then try again.` | deletes the meeting in Zoom, then retries |
| 32c already decided | 302 | the existing error flash `This request has already been decided.` | none |

- The `Nothing was booked` title holds for every row, including 30(b) and 31: nothing was booked **in the app**, and the sentence says what's left in Zoom.
- The example messages above are criteria 24 and 26–31 filled in with `Zoom 02` and `ZL-0042`. Where an example and a criterion ever differ, the criterion wins. The frontend renders `approve_error` as passed and builds none of this text.
- Meeting IDs print as the backend passes them. The frontend adds no formatting.

### D.2 Zoom accounts list: `zoom/accounts.html` (amends 008 D.1)

#### D.2.1 The new column

It goes after `Host key` and before `Upcoming classes` (criterion 35).

| # | `<th scope="col">` | Cell | Phone label (`datagrid__label`) |
|---|---|---|---|
| 6 | `Zoom connection` | `{% include "zoom/partials/account_tag.html" with kind="zoom" state=account.zoom_connection_state paid=account.is_paid active=account.is_active only %}` | `Zoom connection` |

- `Upcoming classes` becomes column 7.
- The lead text and the caption are **unchanged**.
- The table gains the modifier **`datagrid--wrap-tags`**: `<table class="datagrid datagrid--wrap-tags" role="table">`. With seven columns beside the standard sidebar at 1024px, the no-wrap tags (`Free (40-minute limit)`, `Missing on the server`) would push the table past its box. The modifier lets tags in this table wrap onto two lines instead (D.7). Criterion 43's 1024 check is the proof.

#### D.2.2 `account_tag.html`, `kind="zoom"`

The partial's header comment gains the new kind and its three `with` values (`state`, `paid`, `active`).

| `state` | Condition | Class | Icon | Word (pinned) |
|---|---|---|---|---|
| `"ready"` | any | `tag tag--plain` | **`link`** | `Set up` |
| `"none"` | `paid` and `active` | `tag tag--warn` | `alert-triangle` | `Not set up` |
| `"none"` | otherwise (free, or not in use) | `tag tag--plain` | `slash` | `Not set up` |
| `"missing"` | any | `tag tag--warn` | `alert-triangle` | `Missing on the server` |

**Why these tones.** They follow 008 D.4: the good state is plain with an object icon (`Saved` / `key`, `Set up` / `link`), and warn is kept for things that stop a booking. A free or unused account never needs a connection (D16: "The two free accounts need no app"), so its `Not set up` stays calm. The word is the same either way. Only the emphasis changes, so status is never colour alone. `Missing on the server` is always a mistake (a name was typed that the server doesn't have), so it's always warn.

#### D.2.3 Wireframes

**Desktop (1440):**

```
│ Accounts (5)                                                  [ + Add a Zoom account ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Classes can be booked only on accounts that are paid and in use. For safety, …         │
│ Name     Zoom sign-in email      Type      In use      Host key     Zoom connection          Upcoming classes │
│ Zoom 01  zoom01@polymath.edu.lk  [▭ Paid]  [✓ In use]  [⚷ Saved]    [🔗 Set up]              2 booked …       │
│ Zoom 03  zoom03@polymath.edu.lk  [▭ Paid]  [✓ In use]  [△ Not saved] [△ Missing on the server] None booked    │
│ Zoom 05  zoom05@polymath.edu.lk  [▭ Paid]  [✓ In use]  [⚷ Saved]    [△ Not set up]           None booked      │
│ Zoom 07  zoom07@polymath.edu.lk  [◷ Free (40-minute limit)] [‖ Not in use] [⚷ Saved] [⊘ Not set up] None booked │
```

**At 1024 (standard sidebar):** the same row. The `Type` and `Zoom connection` tags may wrap to two lines (`[△ Missing on / the server]`), and the table fits its box.

**Phone (400):** the card pattern from 008, with one more row:

```
│ │ ┌──────────────────────────────┐ │ │
│ │ │ Name       Zoom 03  (link)   │ │ │
│ │ │ Sign-in    zoom03@polymath.  │ │ │
│ │ │ email      edu.lk            │ │ │
│ │ │ Type       [▭ Paid]          │ │ │
│ │ │ In use     [✓ In use]        │ │ │
│ │ │ Host key   [△ Not saved]     │ │ │
│ │ │ Zoom       [△ Missing on     │ │ │  wraps inside the value column
│ │ │ connection   the server]     │ │ │
│ │ │ Upcoming   None booked       │ │ │
│ │ └──────────────────────────────┘ │ │
```

**States:** as in 008 D.1. Rendering the list makes no HTTP call (criterion 35), so there's no loading state.

### D.3 Add and change: `zoom/account_form.html` (amends 008 D.2)

#### D.3.1 The new section

It's a new `fieldset.formsection` with the legend **`Zoom connection`** (*design copy*). It sits **between `Booking` and `Host key`**, so the field comes straight after `sort_order` in both the form order and the screen order (criterion 34; 008 G1's rule that field order = screen order = error-summary order). The form's field order becomes: `label, email, notes, is_paid, is_active, sort_order, credential_set, host_key, remove_host_key`.

In this order, inside the section:

1. **State line (change only)**, a `.notice` with no role, not focusable, like the host-key state line (008 D.3). It's from the **stored** row (`zoom_connection_state`, `zoom_connection_name`):

   | `zoom_connection_state` | Notice | Icon | `p.notice__title` (pinned word) | `p` |
   |---|---|---|---|---|
   | `"ready"` | `notice--ok` | `check-circle` | `Set up` | *design copy:* `The server has a Zoom connection called {zoom_connection_name}. Press Check connection to make sure Zoom accepts it.` |
   | `"missing"` | `notice--warn` | `alert-triangle` | `Missing on the server` | `The server has no Zoom connection called {zoom_connection_name}.` (pinned) then *design copy* ` Check the name for typing mistakes, or ask whoever looks after the server to add it.` |
   | `"none"` | `notice--note` | `info` | `Not set up` | *design copy:* `Paid accounts in use need a Zoom connection before classes can be booked on them.` |

   `none` uses the neutral note tone on this page, because the stored paid/in-use flags aren't reliable on an error re-render (008 G3's problem). The sentence states the rule instead.
2. **The field** `credential_set`, rendered with `partials/field.html` and `narrow=True`:
   - label `Zoom connection name` (pinned);
   - help `The name of this account's Zoom connection on the server, like zoom-01. Whoever looks after the server tells you the name.` (pinned);
   - error `Use lower-case letters, numbers and hyphens only, like zoom-01.` (pinned).

   The typed value is kept on error, as with every field except the host key. The widget attributes go on the form (gap G4).
3. **Check connection (change only, `can_check_connection`)**. It's a `div.field` holding:
   - `<button class="button button--secondary" type="submit" form="zoom-check" data-busy-text="Checking with Zoom…" aria-describedby="zoom-check-help">Check connection</button>` (label pinned);
   - `p.field__help#zoom-check-help`, *design copy*: `Asks Zoom whether this account's saved connection works. Save your changes first: checking reloads this page.`;
   - the empty `p.visually-hidden[role=status][data-busy-status]`.

   **Not nested.** The button lives inside the main form's markup, but it submits a separate, empty form written **after** the main `</form>` and still inside `.box__form`:

   ```html
   <form id="zoom-check" method="post" action="{% url 'zoom:account_check' account.pk %}" data-busy-form>{% csrf_token %}</form>
   ```

   The HTML `form` attribute ties the button to it. This works with no JS and never nests forms, and the button can sit in the section it belongs to. Pressing Enter in a main-form field still submits the main form, because the main form's first submit button is `Save changes`. The check button isn't part of the main form.

   It shows for every stored state, since criterion 36 explains `none` and `missing` in its message.

**Add page:** only the field (with its help). There's no state line and no check button, because there's nothing saved to check.

#### D.3.2 Wireframes

**Desktop (1440, change, `missing`):**

```
Change Zoom 03                                   Home › Zoom accounts › Zoom 03
┌ flash, only after a check (D.3.3) ────────────────────────────────────────┐
┌────────────────────────────────────────────────────────────────────────────┐
│  ┌──── .box__form, 640px ─────────────────────────┐                         │
│  │ The account …                                   │                         │
│  │ ─────────────────────────────────────────────── │                         │
│  │ Booking …  (Order last)                         │                         │
│  │ ─────────────────────────────────────────────── │                         │
│  │ Zoom connection                                 │  legend                 │
│  │ ┌ △ Missing on the server ────────────────────┐ │  notice--warn           │
│  │ │   The server has no Zoom connection called  │ │                         │
│  │ │   zoom-3. Check the name for typing         │ │                         │
│  │ │   mistakes, or ask whoever looks after the  │ │                         │
│  │ │   server to add it.                         │ │                         │
│  │ └─────────────────────────────────────────────┘ │                         │
│  │ Zoom connection name                            │                         │
│  │ The name of this account's Zoom connection on   │                         │
│  │ the server, like zoom-01. Whoever looks after … │                         │
│  │ [zoom-3              ]                          │                         │
│  │ [ Check connection ]                            │  button--secondary      │
│  │ Asks Zoom whether this account's saved          │  field__help            │
│  │ connection works. Save your changes first: …    │                         │
│  │ ─────────────────────────────────────────────── │                         │
│  │ Host key …                                      │                         │
│  │ [ Save changes ]  Cancel                        │                         │
│  └─────────────────────────────────────────────────┘                         │
└────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400, change, after a failed check):**

```
┌──────────────────────────────────────┐
│ Change Zoom 03                       │
│ Home › Zoom accounts › Zoom 03       │
│ ┌──────────────────────────────────┐ │
│ │ ⬣ Zoom didn't accept the         │ │  flash--bad, role=alert
│ │   connection details called      │ │
│ │   zoom-03. Check the account ID, │ │
│ │   client ID and client secret on │ │
│ │   the server, and that the Zoom  │ │
│ │   app is activated.          (x) │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ The account …                    │ │
│ │ Booking …                        │ │
│ │ ──────────────────────────────── │ │
│ │ Zoom connection                  │ │
│ │ ┌ ✓ Set up ────────────────────┐ │ │  the stored state: the name exists,
│ │ │   The server has a Zoom      │ │ │  even though Zoom refused it
│ │ │   connection called zoom-03. │ │ │
│ │ │   Press Check connection …   │ │ │
│ │ └──────────────────────────────┘ │ │
│ │ Zoom connection name             │ │
│ │ …help…                           │ │
│ │ [zoom-03          ]              │ │
│ │ [ Check connection ]             │ │  natural width, 44px
│ │ Asks Zoom whether …              │ │
│ │ ──────────────────────────────── │ │
│ │ Host key …                       │ │
│ │ [      Save changes      ]       │ │
│ │ [         Cancel         ]       │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

The state line (`Set up`: the server has the name) and the flash (Zoom refused it) can disagree. That's correct, and the words make it clear: the line describes the setup, and the flash describes what Zoom just said. Results aren't stored (D12), so the line never claims "works".

#### D.3.3 Check-connection feedback

The redirect lands on `zoom:account_edit`. The message shows in `partials/messages.html` directly under the title row, using the families in `flash-messages.md`:

| Result | Level → family | Icon | Role |
|---|---|---|---|
| works | success → ok | `check-circle` | status |
| works, Basic user | warning → warn | `alert-triangle` | status |
| every error in criterion 36 | error → bad | `alert-octagon` | alert |

The text is exactly criterion 36's table. The two `Couldn't check …` errors differ only in their next step, which matches the error's `lasting` flag (D23):

- temporary (`ZoomUnavailable`, `ZoomBusy`): `Couldn't check Zoom 02 with Zoom: Zoom is busy right now. Try again in a few minutes.`
- lasting (`ZoomRejected`): `Couldn't check Zoom 02 with Zoom: Zoom error 300. Waiting won't fix this. Tell whoever looks after the server, and give them the Zoom error number.`

Both are error flashes (`bad`, `alert-octagon`, `role="alert"`). After the redirect the page starts at the top, so the flash is the first thing read after the h1. Nothing else changes on the page, and nothing is stored.

**Other states:**

| State | Behaviour |
|---|---|
| Validation error on `credential_set` | the error summary (link → `#id_credential_set`) and `.field__error` under the field, value kept. On a re-render the state line still shows the **stored** state |
| Loading | the check is a full-page POST, and the busy button covers the wait (`busy-button.md`). With no JS, it's the browser's own indicator |
| Unknown `pk` on the check | 404 |
| No permission | 403 / login redirect (criterion 36). The button is only rendered when `can_check_connection` |
| `GET` to the check URL | 405. It's never linked |

### D.4 Copy

**Pinned** (criteria 15–18, 24, 26–31, 34–36), used verbatim: see D.1–D.3.

**Design copy** (new in this section; the backend doesn't need it unless noted):

| Where | Text |
|---|---|
| Availability lead, `all_unchecked` | `None of the {n} paid account(s) could be checked with Zoom.` |
| Unavailable row, after the reason | `It can't be booked until Zoom can be checked.` |
| Unavailable row, link | `Check the Zoom connection for {label}` |
| Not-connected row | `This account has no working Zoom connection yet, so it can't be booked.` |
| Not-connected row, link / no-permission line | `Set up the Zoom connection for {label}` / `Ask someone in the IT desk to set it up.` |
| Zoom clash with no topic | `a meeting with no name` |
| Manual notice title | `Check Zoom for clashes first` |
| Approve busy text | `Making the meeting in Zoom…` / `Approving…` |
| Form section legend | `Zoom connection` |
| State line, `ready` | `The server has a Zoom connection called {slug}. Press Check connection to make sure Zoom accepts it.` |
| State line, `missing` (after the pinned sentence) | `Check the name for typing mistakes, or ask whoever looks after the server to add it.` |
| State line, `none` | `Paid accounts in use need a Zoom connection before classes can be booked on them.` |
| Check button help | `Asks Zoom whether this account's saved connection works. Save your changes first: checking reloads this page.` |
| Check busy text | `Checking with Zoom…` |

No screen says "credential set", "OAuth", "scope", "token" or "API" (planner's IA rule). The one exception is pinned: criterion 36's `ZoomMissingScope` message points to "the scopes listed in the README". It's meant for whoever runs the server, so it's acceptable.

### D.5 Accessibility

- **Landmarks and headings:** unchanged. The detail page stays h1 → h2 per box. There are no new headings: row states are list content, and the new form group is a `fieldset`/`legend`, so the page outline stays h1 → content.
- **Label, help and error wiring:**
  - `credential_set` uses `partials/field.html`, which gives `aria-describedby="credential_set-error credential_set-help"` (error first) and `aria-invalid="true"` on error.
  - The check button has `aria-describedby="zoom-check-help"`.
- **Status is never colour alone:**
  - every new state is an icon plus a word (`Couldn't check with Zoom` / `help-circle`, `Not connected to Zoom` / `slash`, `Set up` / `link`, `Not set up` / `alert-triangle` or `slash`, `Missing on the server` / `alert-triangle`);
  - Zoom clashes are told apart from database clashes by the words `In Zoom:`;
  - the notices have icons and titles.
- **Link text:** each fix link names its account (`Check the Zoom connection for Zoom 03`), so it's unique in a screen reader's link list.
- **Focus:**
  - **Failed approve:** the `approve_error` notice is `data-error-summary`, so `app.js` focuses and scrolls to it (existing). Without JS, it's the first content after the title row.
  - **After the check redirect:** normal page-load focus, and the flash is first after the h1. An error flash is `role="alert"`, so it's announced. Its Close button returns focus to `<main>` (existing).
  - **During a busy submit:** focus stays on the button, because `aria-disabled` is used, not `disabled`. The new text is announced through the polite `data-busy-status` region.
  - **Tab order on the change page:** Name → Sign-in email → Notes → Paid account → In use → Order → Zoom connection name → Check connection → (New) host key → Remove → Save changes → Cancel. That's the visual order.
  - **Tab order on the detail availability box:** each row's links, top to bottom (the database clash links, then the fix link).
- **Touch targets:**
  - `.button` is 44px, including Check connection.
  - The fix links and clash links are `.tap-link` (44px below 768px).
- **Reflow and contrast:**
  - 320, 400, 1024 and 1440, in both modes, with no sideways page scroll (the accounts table fits with `datagrid--wrap-tags`).
  - Long topics and slugs wrap through `.break-anywhere` / `overflow-wrap`.
  - Every colour pair is an existing tag, notice or text token, already checked AA at its size (008 D.4, `availability-list.md`).
- **Time:** `Checked with Zoom at …` is wrapped in `<time datetime>`.

### D.6 Progressive enhancement

- **Works with plain HTML and full page loads:**
  - every availability state;
  - approving, with every failure re-render;
  - the "nothing can be checked" notice;
  - the manual notice;
  - the accounts column;
  - the connection field and its errors;
  - Check connection (a real form, through the `form` attribute), and every check message as a flash.

  The detail page can take up to about 8 seconds to load while Zoom is asked (criterion 19). That's the browser's normal loading state, and there's nothing to enhance without making the page asynchronous, which the brief doesn't ask for.
- **What `app.js` adds:**
  - the existing error-summary focus and flash Close;
  - **new:** the busy submit button (`data-busy-form`, `data-busy-text`, `data-busy-status`; `busy-button.md`), on the approve form and the check form.

  It binds to `data-*` hooks only. With JS off, the button simply stays as it is.

### D.7 Build list for `tmd-frontend`

- **Templates:**
  - `zoom/detail.html`: the lead (D.1.2), the row include, the manual notice, the busy hooks, and the no-approve precedence (D.1.7). The header comment lists the new context variables.
  - **New** `zoom/partials/avail_item.html` (D.1.3), with a header comment.
  - `zoom/accounts.html`: the column and `datagrid--wrap-tags` (D.2).
  - `zoom/partials/account_tag.html`: `kind="zoom"` (D.2.2).
  - `zoom/account_form.html`: the new section and the separate check form (D.3).
  - Every include ends with `only` (criterion 43).
- **Icons** (`partials/icons.html`): add Feather `i-help-circle` and `i-link`, and extend the header comment ("Brief 006 added …"). Both are used.
- **CSS** (`static/css/style.css`, tokens only):
  - `.avail__note` (D.1.4), in section 5m;
  - `.datagrid--wrap-tags .tag { white-space: normal; text-align: left; }`, next to the datagrid rules;
  - `.button[aria-disabled="true"] { cursor: progress; }`, in 5d.
- **JS** (`static/js/app.js`): one block for the busy button, per `busy-button.md`.

### D.8 Gaps in the context contract (backend to add or confirm)

**Status (2026-09-25):** all six are folded into the criteria as D22 (G1, G2, G6 in criterion 15; G3 in criterion 17; G4 in criterion 34; G5 in criterion 36).

- **G1 — `account_edit_allowed` is also used on `unavailable` rows** (for the "Check the Zoom connection" link), not only `not_connected`. It's the same bool, so there's no new variable. Please confirm it's set on every entry.
- **G2 — `zoom_clashes` order.** Sort it by `occurrence.starts_at`, then `busy.starts_at`, so the lines read in date order after the database clashes.
- **G3 — Precedence when there's no approve form.** `has_started` wins over `all_unchecked`, which wins over "none free". Please confirm `approve_form` is `None` in all three, and that `has_started` is still passed when `all_unchecked` is true.
- **G4 — Widget attributes for `credential_set`,** set on `HostAccountForm`: `autocomplete="off"`, `autocapitalize="none"`, `spellcheck="false"`, `maxlength="40"`. The label and help text are also on the form (008 G2), and the field comes after `sort_order` in `Meta.fields`.
- **G5 — `account` on the change page** must be present whenever `can_check_connection` is true (for `account.pk` in the check form's action). It is today; it's noted so it stays so.
- **G6 — `zoom_problem`** ends with a full stop and is capitalised (criterion 28's "reason sentence" form), because the row appends another sentence after it.

### D.9 Copy proposals (for the main session; pinned text stays until approved)

**Status (2026-09-25):** all three were accepted and pinned: P1 as D23 (criteria 10, 28, 30 and 36), P2 as D24 (criterion 17) and P3 as D25 (criterion 30, which also adds the "Zoom may have made it anyway" form). D.1.7, D.1.8 and D.3.3 now quote the pinned text. The proposals below are kept as the record of what was asked.

- **P1 — "Try again in a few minutes" is the wrong advice for lasting errors.** In criteria 28 and 30, a `ZoomAuthFailed`, `ZoomMissingScope`, `ZoomUserNotFound` or `ZoomRejected` won't fix itself with time. Proposal: keep the pinned tail for `ZoomUnavailable` and `ZoomBusy`. For the lasting kinds, use `Choose another free account, and ask whoever manages the Zoom accounts to press Check connection for {label}.` This needs one backend flag per error kind (transient or lasting). The layout doesn't change.
- **P2 — Criterion 17's notice when reloading won't help** (for example, `zoom` switched on before any account is connected). Proposal: append `If this keeps happening, ask whoever manages the Zoom accounts to press Check connection for each account.` It's copy only.
- **P3 — Criterion 30's sentence with `no answer from Zoom`** reads `Zoom didn't create the meeting: no answer from Zoom.` That's clumsy, and after a read timeout it may not even be true (Zoom may have made it). Proposal: `We couldn't make the meeting in Zoom: no answer from Zoom. Nothing was booked. Try again in a few minutes.` It keeps the same slot and the same tail.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops (early fix, criterion 44, 2026-09-25)

Urgent fix ahead of the rest of 006: the spreadsheet with Zoom host keys was inside the local `polymath-tmd:latest` and `:dev` images, because both runtime stages `COPY . .` and `.dockerignore` didn't exclude it. No image had been pushed.

**Files changed**
- `.dockerignore`:
  - **Private data:** the root-anchored patterns mirrored from `.gitignore` (`/Dashboard 2A.xlsx`, `/*.xlsx`, `/*.xlsm`, `/*.xls`, `/*.ods`, `/*.csv`, `/data/private/`).
  - **Credentials:** `zoom-credentials.env`, because `.env.*` doesn't match it.
  - **Other local-only root items:** `.cache` (pip's cache), `.mailmap` (contributor email addresses), `.claude`, `docs`, `CLAUDE.md`, `OVERSIGHT_LOG.md` and the root `logo.png` (the served images are in `static/img/`). Nothing at runtime reads any of them.
  - Each group carries a comment saying why.
- `.gitignore`: `/.cache/` (pip's cache), so it no longer shows as untracked.
- `apps/core/tests.py`: `test_dockerignore_keeps_private_data_out_of_the_image`. It checks that `.dockerignore` lists every pattern above plus `.env` and `.cache`.

**Contract deviations / migrations / new env vars / new deps:** none.

**Image check** (`docker run --rm --entrypoint sh <image> -c 'ls -A /app'`, plus a filesystem-wide `find` for `*.xlsx`, `*.csv`, `.cache` and `zoom-credentials.env`, leaving out `/usr` and `/opt/venv`)
- **`polymath-tmd:latest`** (new ID `93fe9da60385`): `.env.example README.md apps config docker manage.py media pyproject.toml requirements static staticfiles templates`. The `find` found nothing.
- **`polymath-tmd:dev`** (new ID `573fca43e60c`): the same list without `staticfiles`. The `find` found nothing.
- **Bind mount:** the running dev container still sees the spreadsheet through the `compose.dev.yaml` bind mount. That's by design; it isn't in the image. Criterion 44's `docker compose run --rm --no-deps web ls /app` is therefore meaningful only on the prod stack.

**Old images and build cache**
- **Old images:** the old `5439548e7ed4` (`:dev`) and `bbf97733fc25` (`:latest`) were already removed by the daemon when the rebuild re-tagged them. No dangling `polymath-tmd` images remained, so nothing was pruned. The `<none>` image `3466ba4a4828` is used by `polymathlib-db-1`, and was left alone.
- **Build cache: not cleared, for the owner to decide.** The cache is shared by every project on this machine and carries no project label, so the owner decides whether to clear anything.
  - **Likely to hold the spreadsheet:** 21 entries, attributed by step name, date and size. They're `[prod 2/3]` / `[dev 2/3] COPY --chown=app:app . .` steps, created 2026-09-24/25 before the fix, at 4.1–7.2 MB (one is 130 MB). The clean context is now 1.83 MB and the spreadsheet is 1.58 MB.
  - **Too small to hold it:** earlier entries of that step are 0.9–1.9 MB.
  - **Keep:** the fixed layers `i3xsa8a7t237znadamd8o2m05` and `jqusnfta2gtzzv89l6i71rko3`.
  - **Effect of clearing:** it only makes the next build of whichever project owned an entry slower.

  ```
  for id in wpzu9l8h5w8ta0ohukvr87hr1 u47a8jlfz9i874526epu27ske igst16t2f8cb20spg3phxsw65 jkga874gkkf0tjybz4ua43t8k vtxz4r5tfgdcevgf6enynqynj oy5rd1tkrubc8508nmgpv49pu n5ayto7wxsc4s57a3mm1f3ore w0hw8qj787wmaengn4sst3tz7 t3b44qudr9ju7hpvq4i54bmt2 jxlxt6c501hmo6shpnc2gfnzc wwv2svj0irtjnjqte7d84fprb hre2zqjm5a0mvgmi3sk1gxs6m n4b80rz5tj9o5bsxflpbjhvfb rcf66gij8j457xwin6jej1hp7 5slw75edab3x06rh407fd1r2f x713rtdsm6hkj9tacyexbhr3y o49ysox49x7m6ofte4ohr4kl2 8in7k7ts1umila4cu3uu9jrpr vdbyc2u53pbqea660b1g98uhz 59mf0tstmmelhwsaq4gpbmib7 phtq9tg5n63vkdvewrjnwkcp5; do docker builder prune -f --filter id=$id; done
  ```

**Operational steps for the user**
- **Nothing to rebuild:** both images are rebuilt, and the dev stack is running again.
- **Earlier images held the host keys** (R8). If any copy of them could have left the machine, rotate the Zoom host keys.
- The spreadsheet itself stays at the repo root, as the owner asked.

**Self-check output** (2026-09-25)
- `docker compose config --quiet`: passes for prod and for dev.
- **Prod rebuild** (`ZOOM_PROVIDER=manual docker compose up -d --build`): `web` became `healthy`, and `/healthz/` on 8010 returned 200.
- **Dev rebuild** (`-f compose.yaml -f compose.dev.yaml up -d --build`): `web` is up, and `/healthz/` on 8010 returned 200.
- `ruff check .`: All checks passed. `ruff format --check .`: 84 files already formatted.
- `pytest --create-db` in the dev container: 700 passed in 35.80s.
- `makemigrations --check --dry-run`: No changes detected.
- `manage.py check`: System check identified no issues (0 silenced).
- `check --deploy` wasn't run, because no settings changed.
- The later `.gitignore` edit needed no re-run: git alone reads that file.

### tmd-devops (step 2, 2026-09-25)

Criteria 2, 3, 7, 42 and 45 (the settings, env and test-infrastructure parts). Criterion 44's `zoom-credentials.env` line was already in `.dockerignore` from the early fix, so `.dockerignore` is unchanged here.

**Files changed**
- `requirements/base.txt`: `requests==2.34.2`, under the comment `# HTTP client for the Zoom API (brief 006, D3)`. It's pure Python, so the prod image needs no build tools.
- `requirements/dev.txt`: `responses==0.26.3`, under `# mocks Zoom at the HTTP layer in tests (brief 006, D3)`. It pulls in `PyYAML` 6.0.3 (a wheel), dev only.
- `config/settings/base.py`:
  - `ZOOM_PROVIDER`'s comment lists `zoom`, `manual` and `fake`. The default stays `manual`.
  - New section "Zoom connection":
    - `ZoomCredentials(slug, account_id, client_id, client_secret)`, a frozen dataclass. The three values are `field(repr=False)`, so `repr`/`str` show `ZoomCredentials(slug='zoom-01')` only.
    - `zoom_credential_env_prefix(slug)` is the one naming rule (`zoom-01` → `ZOOM_S2S_ZOOM_01`).
    - `read_zoom_credentials(env, slugs) -> (secrets, missing)` reads the three variables per slug and strips them. A blank value counts as missing. It never raises, so E005 can report problems readably.
    - `ZOOM_CREDENTIAL_SETS`: the list from the env var, stripped, with empty entries dropped.
    - `ZOOM_S2S_SECRETS`: `{slug: ZoomCredentials}`, **complete sets only**. Its name contains `SECRET`, so Django masks it.
    - `ZOOM_CREDENTIAL_MISSING`: `{slug: [missing variable names]}`, names only. This addition isn't pinned in the brief. It exists so the backend's `zoom.E005` can name missing variables without reading env itself (criterion 2's scan).
  - `LOGGING`: `loggers.urllib3.level = "WARNING"`, whatever `LOG_LEVEL` is.
- `config/settings/prod.py`: still refuses `fake`. The message is now `The fake Zoom provider can't run in production. Set ZOOM_PROVIDER=zoom (or manual, the fallback).`
- `compose.yaml`: `web` gains `env_file: [{path: ./zoom-credentials.env, required: false}]`, with a comment on why. None of the Zoom credential names is in `web.environment`: an `environment` entry takes precedence over `env_file`, so an interpolated `${ZOOM_CREDENTIAL_SETS:-}` there would blank the file's value. This is D2's documented exception to the three-places rule. Docker Compose here is v5.5.1, well past the 2.24 needed for `required:`.
- `zoom-credentials.env.example` (new, tracked): `ZOOM_CREDENTIAL_SETS=` and the three `ZOOM_S2S_ZOOM_01_*=` lines. Every value is empty, and each has its own comment line. The header explains the slug rule, the file's place, "no `$`" and "recreate `web`".
- `.env.example`: the `ZOOM_PROVIDER` comment lists `zoom`, `manual` (the fallback, with W001) and `fake`. It also says that the credentials go in `zoom-credentials.env`, not `.env`.
- `.gitignore`: `zoom-credentials.env`. `git check-ignore` confirms it; the `.example` stays tracked.
- `conftest.py` (new, project root): the network block. An autouse fixture `http_mock` runs `responses.start()` on `responses`' **default** mock for every test, then `stop()` and `reset()` afterwards. Any unregistered `requests` call raises `requests.exceptions.ConnectionError`. The patch is on the adapter class, so worker threads are covered too.
- `apps/core/test_zoom_settings.py` (new, 15 tests). This is a separate file from `apps/core/tests.py`, so it can't collide with backend edits. It covers:
  - the prefix rule;
  - complete versus missing sets;
  - `repr` shows the slug only;
  - criterion 2's source scan (no `os.environ`, `getenv(` or `env(` on a line with `ZOOM_S2S_` outside `base.py`);
  - `get_safe_settings()` masks `ZOOM_S2S_SECRETS`, and a technical 500 page shows no fake credential value (criterion 3);
  - `prod.py` refuses `fake` and names `ZOOM_PROVIDER=zoom` (run in a subprocess);
  - the `urllib3` level;
  - the compose `env_file` block, and that no Zoom credential name is listed under `environment`;
  - the `.gitignore` entry;
  - the `.example` file's names and empty values;
  - the `.env.example` wording;
  - the network block (main thread, a worker thread, and a registered reply recorded in `http_mock.calls`).

**For `tmd-django-backend`**
- **Settings to read:** `settings.ZOOM_S2S_SECRETS[slug].account_id` / `.client_id` / `.client_secret`; `settings.ZOOM_CREDENTIAL_SETS` (the slugs, in order); `settings.ZOOM_CREDENTIAL_MISSING`.
- **E005 inputs:**
  - an empty `ZOOM_CREDENTIAL_SETS`;
  - `ZOOM_CREDENTIAL_MISSING`, which already holds the variable names;
  - slugs that fail the pattern;
  - duplicate names: `from config.settings.base import zoom_credential_env_prefix` and compare the prefixes. The module is already imported whenever the settings derive from `base`, so this doesn't run it again.
- **Invalid slugs:** a slug that fails the pattern but has all three variables still lands in `ZOOM_S2S_SECRETS`. E005 is what rejects it, and `HostAccount.credential_set`'s validator can't point at it anyway.
- **In tests:**
  - Register replies with `http_mock.add(...)` / `http_mock.get(...)` or `responses.add(...)`; both are the same mock. Read `http_mock.calls`.
  - **Don't use `@responses.activate` or `with responses.RequestsMock()`.** Leaving the decorator stops the global block for the rest of that test.
  - For a test that needs a fresh registry mid-test, call `http_mock.reset()`.
  - Construct `ZoomCredentials` from `config.settings.base` with keyword arguments.
- **The token and preview cache resets** (criterion 45, third bullet) belong in the zoom tests' conftest, since `reset_token_cache()` is backend code. The project conftest doesn't import `apps.zoom`.

**Deviations from the brief**
- Added `ZOOM_CREDENTIAL_MISSING`, explained above.
- **Host runs don't read the file:** `base.py` doesn't `read_env` `zoom-credentials.env`. The brief pins delivery through compose `env_file`. `read_env` would also warn on every start where the file is missing, and host-side runs are only for tests, which set `ZOOM_S2S_SECRETS` through the `settings` fixture. A host run of `manage.py` doesn't see the file; values can be put in the shell environment for that.

**New env vars** (in `zoom-credentials.env`, not `.env`; D2):
- `ZOOM_CREDENTIAL_SETS`, default empty.
- `ZOOM_S2S_<NAME>_ACCOUNT_ID`, `ZOOM_S2S_<NAME>_CLIENT_ID` and `ZOOM_S2S_<NAME>_CLIENT_SECRET` per slug, default empty (the set is then "missing").

**Dependency changes:** `requests==2.34.2` (runtime; it brings `urllib3` 2.8.0, `certifi`, `idna` and `charset-normalizer`), and `responses==0.26.3` (dev only; it brings `PyYAML` 6.0.3). The prod image contains `requests` and not `responses`.

**Operational steps for the user**
- **Rebuild:** the dev image is rebuilt, and the dev stack is running again. The prod image was rebuilt too.
- **Production later:** copy `zoom-credentials.env.example` to `zoom-credentials.env` next to `.env`, fill it in (D16), then `docker compose up -d`. No value ever goes in the repo.
- **A prod-image caveat:** a local `docker compose run … web` needs `ZOOM_PROVIDER=manual` in front of it, as `up` does. Otherwise the entrypoint's migrate hits the prod guard (seen once during the self-check; that also showed the new message).
- **For the docs writer:** the README "Running with Docker" / "Deploying the image" sections need to mention `zoom-credentials.env`. That wording goes to `tmd-docs-writer` at step 6.

**Self-check output** (2026-09-25)
- `docker compose config --quiet`: passes for dev and prod.
- **`env_file`, live:** a temporary `zoom-credentials.env` with dummy values (`zoom-test`) made `settings.ZOOM_S2S_SECRETS` equal `{'zoom-test': ZoomCredentials(slug='zoom-test')}`, with `ZOOM_CREDENTIAL_MISSING` = `{}`. After deleting the file and recreating `web`, both settings were empty and the stack started normally.
- **Dev rebuild** (`-f compose.yaml -f compose.dev.yaml up -d --build`): `requests 2.34.2` and `responses 0.26.3` are installed.
- `ruff check .`: All checks passed. `ruff format --check .`: 86 files already formatted.
- `pytest --create-db` (dev container): **715 passed in 42.74s**, which is the earlier 700 plus 15 new.
- `makemigrations --check --dry-run`: No changes detected.
- `manage.py check`: no issues. `manage.py check --database default`: no issues.
- **Prod rebuild** (`ZOOM_PROVIDER=manual docker compose up -d --build`): `web` became `healthy`, and `/healthz/` on 8010 returned 200.
- `check --deploy` (prod, `-e USE_HTTPS=True -e ZOOM_PROVIDER=manual`): only `security.W021`. `zoom.W001` doesn't exist yet; the backend adds it. The `ZOOM_PROVIDER=zoom` run of criterion 46 has to wait for the backend to add `zoom` to `PROVIDERS`.
- **`/app` in the prod image:** `.env.example README.md apps config conftest.py docker manage.py media pyproject.toml requirements static staticfiles templates zoom-credentials.env.example`. No spreadsheet, and no `zoom-credentials.env`.
- **Stack restored:** the dev stack is running again, and `/healthz/` on 8010 returned 200.

### tmd-frontend (step 3b, 2026-09-25)

Design D.1–D.7 and `docs/design/busy-button.md`, built against the context contract (G1–G6, D22). Every pinned string is used exactly as the criteria write it. `approve_error`, `zoom_problem` and the check-connection flashes are printed exactly as the backend supplies them; the templates write none of that text.

**Files changed**
- **New: `templates/zoom/partials/avail_item.html`** (D.1.3). One `li.avail__item`, branching on `entry.zoom_state` first:
  - `unavailable`: `tag--warn` + `help-circle` + `Couldn't check with Zoom`, then `p.avail__note` with `{{ entry.zoom_problem }}`, then ` It can't be booked until Zoom can be checked.`, and, when `account_edit_allowed`, the `tap-link` `Check the Zoom connection for {label}` → `zoom:account_edit`.
  - `not_connected`: `tag--warn` + `slash` + `Not connected to Zoom`, then `p.avail__note` with the link `Set up the Zoom connection for {label}`, or ` Ask someone in the IT desk to set it up.`.
  - `checked`/`off`: Free or Busy as in 005. The busy list prints the database clash lines first, then one line per `zoom_clashes` item: `class_span`, `<br>`, `In Zoom: {topic}, {start}–{end}` (the topic is auto-escaped; an empty one reads `a meeting with no name`), with no link.
  - Included as `{% include "zoom/partials/avail_item.html" with entry=entry total=occurrence_count only %}`.
- **`templates/zoom/detail.html`:**
  - The header comment lists the new context (`zoom_clashes`, `zoom_state`, `zoom_problem`, `account_edit_allowed`, `checks_zoom`, `zoom_checked_at`, `all_unchecked`) and the new partial.
  - The lead (D.1.2): `all_unchecked` → `None of the {n} paid account(s) could be checked with Zoom.` (pluralised like the other lead). Otherwise the 005 sentence, plus ` Checked with Zoom at <time datetime="…">{class_time}</time>.` when `checks_zoom` and `zoom_checked_at`.
  - The row loop is now the include.
  - The approve box: with `not checks_zoom`, the `notice--warn` `Check Zoom for clashes first` plus the pinned criterion 18 sentence, placed before the existing `Create the meeting in Zoom first` note.
  - Busy hooks: `data-busy-form` on the approve `<form>`; `data-busy-text` on its button (`Making the meeting in Zoom…` when `checks_zoom`, otherwise `Approving…`); an empty `p.visually-hidden[role=status][data-busy-status]` in `.form-actions`.
  - The no-approve-form notice, in the order `has_started`, then `all_unchecked` (criterion 17's text with D24's sentence), then "none free".
- **`templates/zoom/accounts.html`:** the table is `datagrid datagrid--wrap-tags`. It has a new `Zoom connection` column after `Host key`, with a `datagrid__label` for phones, rendering `account_tag.html` with `kind="zoom" state=account.zoom_connection_state paid=account.is_paid active=account.is_active only`. The header comment is updated.
- **`templates/zoom/partials/account_tag.html`:** adds `kind="zoom"` (D.2.2): `ready` → plain/`link`/`Set up`; `missing` → warn/`alert-triangle`/`Missing on the server`; `none` → warn/`alert-triangle`/`Not set up` when `paid and active`, otherwise plain/`slash`/`Not set up`. The header comment lists the new `with` values.
- **`templates/zoom/account_form.html`:** a new `fieldset.formsection` `Zoom connection`, between `Booking` and `Host key` (D.3.1).
  - The state line appears on change only, from the stored `zoom_connection_state`/`zoom_connection_name`: ok/`Set up`, warn/`Missing on the server`, or note/`Not set up`, each with its D.3.1 sentence. The slug is wrapped in `.break-anywhere`.
  - `form.credential_set` is rendered through `partials/field.html` with `narrow=True`, so its label, help, widget attributes and error wiring all come from the form.
  - When `can_check_connection`, a `div.field` holds the `Check connection` button (`button--secondary`, `form="zoom-check"`, `data-busy-text="Checking with Zoom…"`, `aria-describedby="zoom-check-help"`), the help `p.field__help#zoom-check-help` and the empty `data-busy-status` region.
  - The separate empty `<form id="zoom-check" method="post" action="{% url 'zoom:account_check' account.pk %}" data-busy-form>{% csrf_token %}</form>` comes after the main `</form>`, inside `.box__form`. It's also gated on `can_check_connection`, so the add page has neither the button nor the form.
- **`templates/partials/icons.html`:** adds Feather `i-help-circle` and `i-link`, and the header comment gains "Brief 006 added …". Both are used.
- **`static/css/style.css`** (tokens only, no new tokens):
  - 5d: `.button[aria-disabled="true"] { cursor: progress; }`.
  - 5j: `.datagrid--wrap-tags .tag { white-space: normal; text-align: left; }`.
  - 5m: `.avail__note` (full-width grid column, no margin, `--c-text`, `--lh-body`).
  - The Responsive section is unchanged: below 600px `.avail__item` is already one column, and `.tap-link` is already 44px below 768px.
- **`static/js/app.js`:** new block **10. Busy submit button**, listed in the file's block index.
  - It finds the button through `[data-busy-form] [data-busy-text]`, or through `[form="<id>"][data-busy-text]` for the check button, and the live region inside the form or beside the button.
  - On submit, a second press is prevented. Otherwise it sets `data-busy`, sets `aria-disabled="true"` (never `disabled`), swaps only the button's text nodes, so an icon would stay, and writes the same text into the status region. It does nothing if another handler already prevented the submit.
  - `pageshow` with `persisted` restores the idle state.
  - It binds to `data-*` hooks only. With JS off, both forms post normally.

**Spec deviations:** none.
- **Icons:** the preloaded `solar-duotone-bold` skill wasn't applied. CLAUDE.md and D.7 fix the icon set as the Feather sprite, and mixing families is ruled out.

**Context contract gaps:** none new. Two dependencies on the backend, both already in the contract:
1. **`HostAccountForm` must have `credential_set` (G4).** Until it does, `zoom:account_add` and `zoom:account_edit` return **500** (`VariableDoesNotExist: Failed lookup for key [field] in ''` inside `partials/field.html`). I saw this on 8010 against the current, pre-006 form. It isn't guarded in the template on purpose: a guard would hide a missing field.
2. **The URL name `zoom:account_check` must take `pk`.** The check form reverses it whenever `can_check_connection` is true.

**Self-check output** (2026-09-25; the backend hadn't reported "backend pytest run finished", so **no pytest was run**, as instructed)
- **Stub-context render check** (a scratchpad script run through `manage.py shell` in the dev container; it uses `render_to_string` with the real `base.html`, the real `ApproveForm`, and a stub `zoom:account_check` route; nothing is written): **ALL CHECKS PASSED.** It rendered 12 cases:
  - the detail page with mixed states: the free row; the busy row with a DB clash and two Zoom clashes, one topic with HTML escaped and one empty; unavailable with its link; not connected with and without `account_edit_allowed`; the `Checked with Zoom at <time datetime="2026-09-28T10:02:00+05:30">10:02 am</time>.` lead; the approve busy text for `zoom`;
  - manual (the notice and `Approving…`, and no checked-at line);
  - `all_unchecked` (the lead and the criterion 17 notice, with neither of the other two);
  - `has_started` together with `all_unchecked` (only the started notice);
  - none free (only the 005 notice);
  - `approve_error` (printed verbatim under `Nothing was booked`);
  - the accounts list (the column, the label, all four tag variants, and `datagrid--wrap-tags`);
  - the change page for `missing`, `ready` and `none`: the attributes `autocomplete`/`autocapitalize`/`spellcheck`/`maxlength`, `aria-describedby="credential_set-help"`, the check button markup, the check form **not nested** and carrying its CSRF token, and the screen order Order → Zoom connection name → Check connection → Save changes;
  - the field error (`aria-invalid` plus `credential_set-error credential_set-help`, value kept);
  - the add page (the field only, with no state line, button or check form).
- **Host-side replicas of the file-scan guards in `apps/core/tests.py`:**
  - every include ends with `only`;
  - no `style="`;
  - no hard-coded `href`/`action` paths;
  - every `<use>` points at a defined symbol, and every symbol is used;
  - no colour literal outside the first `:root`;
  - each changed template starts with a one-line `{# … #}`.

  Result: **none failed.**
- `node --check static/js/app.js`: OK. `ruff check .`: All checks passed. `ruff format --check .`: 86 files already formatted.
- **HTTP on 8010** (dev stack, a temporary session for the dev superuser, deleted afterwards):
  - `/zoom/requests/42/` returned **200**. It has 3 `avail__item`, `data-busy-form`, `data-busy-text`, `data-busy-status`, and the manual notice, because the current view doesn't pass `checks_zoom` yet.
  - `/zoom/accounts/` returned **200**. It has `datagrid--wrap-tags`, the `Zoom connection` header and labels, and a tag in every row.
  - `app.js` and `style.css` returned **200**.
  - `/zoom/accounts/add/` and `/zoom/accounts/13/edit/` returned **500**, the backend dependency in gap 1 above.
- **Still to run once the backend reports:** `pytest --reuse-db apps/zoom apps/core` (once), and a repeat of the HTTP check for the add and change pages.

**Review round 1 fixes** (2026-09-25; SF2 and SF3, template side only; no Python touched)
- **SF2, `templates/zoom/partials/account_tag.html`:** the `kind="zoom"` branch now tests `{% elif needs_zoom_connection %}`, not `paid and active`, so the template no longer re-derives "bookable". `paid` and `active` are gone from the `with:` list; nothing else used them. The header comment now says the model decides.
- **SF2, `templates/zoom/accounts.html`:** the include passes `kind="zoom" state=account.zoom_connection_state needs_zoom_connection=account.needs_zoom_connection only`. The header's context list gains `needs_zoom_connection`. This is the partial's only `kind="zoom"` caller.
- **SF3, `templates/zoom/partials/avail_item.html`:** prints `{{ clash.busy.display_topic }}`, still auto-escaped. The hard-coded `a meeting with no name` is gone from `templates/`. The header's `busy` entry names `display_topic`.
- **Depends on the backend:** `HostAccount.needs_zoom_connection` and `BusyTime.display_topic`. Neither existed when these edits were made. Until they land, the missing attribute renders as `""`: an unconnected account shows the plain/`slash` tag, and a Zoom clash shows an empty topic. No error is raised.
- **Self-check:**
  - **Stub-context render** (`manage.py shell` in the dev container, `render_to_string`, stubs only): **FAILS: none**. It covered the tag for `none`+true (warn/`alert-triangle`), `none`+false (plain/`slash`), `ready` (`link`) and `missing`. Passing the old `paid`/`active` keys no longer turns the tag warn. `avail_item` prints the stub's `display_topic`, escaped, and never the old literal.
  - **HTTP on 8010** (dev stack, a temporary superuser session, deleted afterwards): `/zoom/accounts/` **200** with the `Zoom connection` column; `/zoom/requests/42/` **200** with 3 `avail__item`.
  - **After the backend's round 1 marker:** `apps/zoom/models.py:451` `HostAccount.needs_zoom_connection` and `apps/zoom/providers.py:105` `BusyTime.display_topic` are both `@property`. The template paths already matched the coordinator's (`clash.busy.display_topic`; `account.needs_zoom_connection`, passed from accounts.html), so nothing more changed.
  - **pytest, not conclusive.** I ran `pytest --reuse-db apps/zoom` twice, not once as instructed.
    - First run: I captured only the last five lines, the 58%–100% progress rows, all dots with no `F` or `E`. The earlier rows went unseen.
    - Second run, with `-q -p no:randomly`: I meant to recover the summary line, but `-q` on top of the `addopts` `-q` suppressed it, so its result is unknown.
    - I haven't run it a third time, so treat the pass/fail result as unconfirmed. The verifier's full run settles it.

### tmd-django-backend (step 3a, 2026-09-25)

Criteria 1, 4–6, 8–41 and 49 (the logic). **backend pytest run finished**: the final `pytest --create-db` completed at the end of this step (899 passed), so the frontend can now run `pytest --reuse-db`.

**The frontend's two dependencies are met.** `HostAccountForm` has `credential_set` (G4), and `zoom:account_check` takes `pk`. `test_zoom_accounts_connection.py::test_no_credential_or_token_reaches_a_page_a_message_or_the_email` renders the **real** detail, list, add and change templates with a 200 each (criterion 40).

**Files changed**
- `apps/zoom/errors.py` (new): `ProviderError` and its six kinds plus `ZoomNotConnected`, with `lasting` (D23), `maybe_done` (D25) and `reason_sentence` (G6). It's a separate module so that `zoom_api.py` and `providers.py` can both raise them without an import cycle; `providers.py` re-exports them.
- `apps/zoom/zoom_api.py` (new): the only HTTP module and the only importer of `requests`. It holds the fixed hosts, the `(5, 15)` timeouts, redirects off, the process-memory token cache (per set, 300 s margin, per-set fetch lock), the single retry after a `401`, the criterion 10 mapping, and paging (at most 10 pages, then `ZoomUnavailable`). Every function holding a credential, a token or Zoom's answer is `@sensitive_variables`.
- `apps/zoom/providers.py`:
  - `PROVIDERS` is `fake`, `manual`, `zoom`; the interface gains `checks_zoom`, `is_connected()`, `busy_times()` and `delete_meeting()`.
  - `Meeting` gains `occurrence_ids` and `recurring`, and its link and passcode are left out of `repr`. `BusyTime` is new.
  - New `ZoomProvider`, and pure `meeting_payload()` / `zoom_weekly_days()`.
  - `FakeProvider` gets steerable `busy`, `unavailable`, `not_connected` and `delay`, and records `busy_calls` and `deleted`. `next_error` may also be a `ProviderError` instance.
- `apps/zoom/services.py`:
  - `availability()` combines the database and Zoom (parallel, 6 workers, 8 s deadline, 60 s cache, fail closed).
  - `approve()` follows D6's order: `_check_zoom_first` (no locks), then the transaction with one create, then compensation. `_create_failed` produces 30(a) and 30(b) with the clean-up endings.
  - Also new: `check_connection()` / `ConnectionResult`, and every pinned message (criteria 24, 26–31 and 36). The old `PROVIDER_FAILED` is replaced.
- `apps/zoom/checks.py` and `apps/zoom/apps.py`: E001 and E002 copy; new E005 (untagged), W001 (deploy) and E004 (`Tags.database`), each registered explicitly.
- `apps/zoom/models.py`:
  - `credential_set` gets its verbose name, help and validator, and `label`'s help changes.
  - New: `zoom_connection_state_for()`, `HostAccount.zoom_connection_state`, `is_zoom_connected()`, `LinkRequest.zoom_marker`, `agenda_has_marker()` and `Occurrence.zoom_occurrence_id`.
  - The module docstring's "the 007 import" is gone, and so is `clean()`'s "imports".
- `apps/zoom/validators.py`: `CREDENTIAL_SET_PATTERN`, `CREDENTIAL_SET_ERROR` and `validate_credential_set`.
- `apps/zoom/forms.py`: `credential_set` is declared on `HostAccountForm` (G4) with one validator and the pinned error, and placed after `sort_order`. The model's `SlugField` would otherwise add its own slug message.
- `apps/zoom/views.py`:
  - The detail view is `non_atomic_requests` and gets the new context. `RejectView` is non-atomic too (see deviations).
  - The change page gets `zoom_connection_state` / `zoom_connection_name` from the **stored** row, plus `can_check_connection`.
  - New `HostAccountCheckView`.
- `apps/zoom/urls.py`: `zoom:account_check`.
- `apps/zoom/management/commands/check_zoom_connections.py` (new).
- `apps/zoom/migrations/0005_zoom_connection.py` (new).
- **Tests.** New: `test_zoom_api.py`, `test_zoom_provider.py`, `test_zoom_preview.py`, `test_zoom_approve.py`, `test_zoom_race.py`, `test_zoom_accounts_connection.py` and the helper `zoommock.py`. Changed:
  - `conftest.py`: token and preview caches cleared around every test.
  - `test_accounts.py`: the 008 D5 and criterion 4 amendments.
  - `test_services.py` / `test_views.py`: the 005 criterion 40 amendment, and E001/E002.
  - `test_race.py`: a test-database guard (see deviation 8).

  No test uses `@responses.activate`; all use the project-wide `http_mock`.

**Context contract, as implemented.** Every name matches the contract; there are no deviations. Points worth knowing:
- `zoom_checked_at` is the *earliest* check time among the checked accounts, so with the cache it never claims fresher data than is shown. It's `None` when nothing was checked, and always with `manual`.
- `all_unchecked` is false when `availability` is empty (008's "no accounts" lead applies instead).
- `busy.topic` can be `""`; the design's `a meeting with no name` is the template's to print. The criterion 26 message uses the same words.
- `approve_error` always arrives in its final form. Meeting IDs are raw digits (`81234567890`).

**Confirmed against Zoom, with one honest limit.** This session had no web access, so I couldn't re-read Zoom's live docs. The items below come from Zoom's published API and Server-to-Server OAuth documentation as I know it. The owner's live check (criterion 48) is the real confirmation, and the docs writer should treat the names as "to confirm at setup" if Marketplace shows anything different.
- **Scopes:**
  - `meeting:write:meeting:admin`
  - `meeting:read:list_meetings:admin`
  - `meeting:read:meeting:admin`
  - `meeting:delete:meeting:admin`
  - `user:read:user:admin`

  The classic equivalents are `meeting:write:admin`, `meeting:read:admin` and `user:read:admin`.
- **Token:** `POST https://zoom.us/oauth/token` with HTTP Basic (client ID and secret). `grant_type=account_credentials` and `account_id` go in a **form-encoded body**, not the query. Zoom accepts either; the body keeps the account ID out of URLs.
- **Recurring meetings:** the list isn't trusted to carry every occurrence, so each type-8 meeting is read once with `GET /meetings/{id}` (deduplicated), and `occurrences` with `status: deleted` are skipped. The optional skip in criterion 12 isn't taken.
- **`end_times` limit:** 60, matching 005's cap, from memory and not re-checked live. If Zoom's limit is now lower, that's the blocker D5 describes.

**Deviations and additions beyond the brief** (each is small; the reviewer should look at 1 and 2):
1. **Leftover and clean-up deletes first wait on the request's row lock** (`_wait_for_other_attempts`, with no HTTP inside the lock). I found this race while building criterion 27. Attempt B's step-1 list could see attempt A's *in-flight* marker meeting (A holds the locks during its create) and delete it, and A would then commit a booking whose meeting is gone. Waiting briefly for the lock means any marker meeting B listed belongs to a finished attempt. If the request is then approved, B stops (step 1) or keeps the stored meeting ID (30(b) clean-up). This is only reached when marker meetings exist, so criterion 21's order on the normal path is unchanged.
2. **`is_connected(account)` is on the provider interface.** `ZoomProvider` uses `HostAccount.is_zoom_connected()`. The fake treats every account as connected unless steered, which keeps 005's behaviour for `fake` (criterion 33) and still lets tests and screenshots show `not_connected`.
3. **`maybe_done` also covers a connection dropped after sending** (`ConnectionError` wrapping urllib3's `ProtocolError`), because Zoom may have acted then (the D25 truthfulness rule). A refused connection and a connect timeout stay "certain", as pinned.
4. **Approval writes its fresh lookup into the preview cache**, and forgets the entry after any failure. That's how criterion 26's re-render shows the new clash. Approval never *reads* the cache (tested: a primed cache still gets a fresh list call).
5. **`RejectView` is `non_atomic_requests`** as well. Its invalid-reason re-render asks Zoom, and `reject()` is one conditional UPDATE.
6. **Smaller choices:**
   - A delete answered `404` with Zoom code 3001 counts as done.
   - Redirects aren't followed; a 3xx maps to `ZoomRejected`.
   - A meeting with no `duration` is assumed to be 60 minutes (fail closed).
   - A weekly meeting whose dates differ and whose delete then fails gets criterion 31's orphan message.
   - `check_zoom_connections` counts the Basic-user warning as a failure (exit 1), because that account can't be booked safely.
   - `ZoomNotConnected` is lasting.
7. **The marker match isn't a bare substring.** `agenda_has_marker()` refuses a following digit, because `ZL-1234` is a prefix of `ZL-12345`.
8. **Pre-existing hazard fixed in `test_race.py`.** pytest-django sets up the test database only when some collected test has a `django_db` mark. `test_race.py` run on its own (and my new `test_zoom_race.py`) therefore wrote committed rows to the **dev** database. `committed` now refuses unless the connection is a `test_` database, and each module carries one marked test so the test database is always set up. I checked the dev database afterwards: no `Race …` rows, and no `race-it` user.

**Risk for the owner's live check (new, for the risk register).** Recurring meetings are read one at a time. An account with many recurring series (say 20 or more) could miss the preview's 8-second deadline and show `Couldn't check with Zoom`. That fails closed, so it's safe but annoying, and approval has no such deadline. If it happens in practice, the fix is to read the series in parallel inside `busy_times`.

**Migrations:** `0005_zoom_connection`. It adds `Occurrence.zoom_occurrence_id` (`CharField(20, blank=True)`), and changes `credential_set`'s verbose name, help and validator and `label`'s help. It's schema only, and reversible. The shared dev and prod database is now on 0005 (the prod entrypoint migrated it).

**Dependencies and settings:** nothing new beyond devops's step 2. The code reads `ZOOM_S2S_SECRETS`, `ZOOM_CREDENTIAL_SETS` and `ZOOM_CREDENTIAL_MISSING`. `checks.py` imports `zoom_credential_env_prefix` from `config.settings.base` for E005's name-collision test, as devops suggested; env is still read only in `base.py`.

**For the verifier:** `FakeProvider`'s steering is class-level (`FakeProvider.busy[pk] = [BusyTime(...)]`, `.unavailable[pk] = ZoomBusy()`, `.not_connected = {pk}`). For criterion 47's dev screenshots, steer it in a `manage.py shell` script that renders the page with the test `Client`. A running dev server can't be steered from outside.

**Self-check output** (dev container unless noted)
- `ruff check .`: All checks passed. `ruff format --check .`: 96 files already formatted.
- `pytest --create-db`: **899 passed in 47.89s** (715 before, plus 184 new). The thread tests (`test_race.py`, `test_zoom_race.py`) and the preview tests passed 8 runs in a row.
- `makemigrations --check --dry-run`: No changes detected.
- `manage.py check` and `manage.py check --database default` (fake): no issues.
- **Prod stack** (`ZOOM_PROVIDER=manual docker compose up -d --build`, `web` healthy, `/healthz/` 200). The dummy values were passed with `exec -e` only; no file was written.
  - `check --deploy` with `USE_HTTPS=True`, `ZOOM_PROVIDER=zoom`, `ZOOM_CREDENTIAL_SETS=zoom-test` and three `dummy-…-not-real` values: **only `security.W021`**, exit 0.
  - `check --deploy` with `USE_HTTPS=True` and `ZOOM_PROVIDER=manual`: **`security.W021` and `zoom.W001`**, exit 0.
  - `check` with `ZOOM_PROVIDER=zoom` and no sets: `zoom.E005 … ZOOM_CREDENTIAL_SETS is empty.`
  - `check --database default` with `zoom` and the dummy set: `zoom.E004` for the two local accounts that have no connection name, which is correct.
- **Stack restored:** `docker compose -f compose.yaml -f compose.dev.yaml up -d`. `web` is running `polymath-tmd:dev`, `/healthz/` on 8010 returned 200, and `showmigrations zoom` shows `[X] 0005_zoom_connection`.

#### Review round 1 fixes (tmd-django-backend, 2026-09-25)

**Files changed**
- `apps/zoom/providers.py`:
  - **SF1.** `ZoomProvider.busy_times` reads Zoom's answer inside `try … except UNREADABLE_ANSWER: raise ZoomUnavailable() from None`. That covers `AttributeError`, `KeyError`, `OverflowError`, `TypeError` and `ValueError`, so a bad `start_time`, a non-object item or an absurd duration are all caught. The catch wraps only the reading, never the HTTP calls, so a `ProviderError` keeps its own kind. Recurring series are now fetched after the list has been read, not in the middle of reading it; they're still read once each, in the same order.
  - `create_meeting`'s occurrence parse already fell back to `()`, which leads to criterion 24's "dates differ" removal, not a 500. It's unchanged, and no other Zoom time is parsed on the approve or clean-up paths.
  - **SF3.** New `BusyTime.display_topic`. `UNNAMED_MEETING` now lives here, beside `BusyTime`, because `services` imports `providers` and not the other way round; `services.UNNAMED_MEETING` re-exports it.
  - **Nit.** Every `ZoomProvider` call uses `with self._client(...) as client:`.
- `apps/zoom/zoom_api.py` (nit): `ZoomClient.close()`, `__enter__` and `__exit__`. `close()` is safe to call twice, and `__exit__` never swallows an error.
- `apps/zoom/services.py`:
  - `ZOOM_CLASH` is now built with `busy.display_topic` (SF3).
  - `_approve_once`'s docstring names the trade-off when the COMMIT's outcome is ambiguous (nit).
  - `remember_preview`'s docstring says "one per process, so each Gunicorn worker" (nit).
- `apps/zoom/models.py` (SF2): new `HostAccount.needs_zoom_connection`, which is `is_bookable_with(is_active=…, is_paid=…)`.
- `apps/zoom/forms.py` (SF3): `CREDENTIAL_SET_HELP` is now `HostAccount._meta.get_field("credential_set").help_text`. The model owns the text and the form borrows it. The name stays, for any importer.
- `apps/zoom/checks.py`:
  - E005's bad-name hint is `CREDENTIAL_SET_ERROR` (SF3).
  - A comment explains the `config.settings.base` import (nit).
  - The redundant `order_by` is gone (nit).
- `apps/zoom/management/commands/check_zoom_connections.py`: the redundant `order_by` is gone (nit). `Meta.ordering` is still `sort_order, label`.
- Tests, 17 new:
  - `test_zoom_provider.py`:
    - unreadable answers (text time, numeric time, non-object, overflowing duration) → `ZoomUnavailable` with `__cause__ is None` and `__suppress_context__`;
    - an unreadable series → the same;
    - every provider call closes its client, including on failure;
    - `display_topic`.
  - `test_zoom_api.py`: `close()` and `with` release the session, and an error still propagates.
  - `test_zoom_approve.py`:
    - `start_time` "garbage" at approval, three ways (another meeting, this request's own leftover, a non-object) → criterion 28's exact message, a 200 re-render, no POST and no DELETE;
    - the 30(b) clean-up list holding "garbage" → `CREATE_MAYBE_MADE` plus the `CLEANUP_FAILED` ending, with no DELETE.
  - `test_zoom_accounts_connection.py`:
    - `needs_zoom_connection` for all four flag combinations, and agreeing with `bookable()`;
    - the accounts list's objects carry it;
    - the form's help is the model's;
    - E005's hint is `NAME_RULE`.

**Context contract, for the frontend's parallel changes.** Nothing new is added to the context; both values are attributes on objects already in it.
- **SF2, `account_tag.html`:** it's `account.needs_zoom_connection`, on each object in the accounts list's `accounts`. Pass it to the partial in `accounts.html` in place of `paid=… active=…`, e.g. `needs=account.needs_zoom_connection`. The partial's key name is the frontend's call. The **change page doesn't include `account_tag.html`**, so the change page's context doesn't change.
- **SF3, `avail_item.html`:** the path is **`clash.busy.display_topic`, not `clash.display_topic`**. Each item of `entry.zoom_clashes` is a dict `{occurrence, busy}`, and `display_topic` is on the `BusyTime` in `busy`. The template's `|default:"a meeting with no name"` can then go.

**Migrations:** none. The model's help text is unchanged (the form now reads it from the model), and `makemigrations --check` reports no changes.

**Dependencies and settings:** none.

**Self-check output** (dev container; the dev stack was running and still is)
- `ruff format .`: 1 file reformatted (a new test). Then `ruff format --check .`: 96 files already formatted. `ruff check .`: All checks passed.
- `pytest --create-db`: **916 passed in 54.82s** (899 + 17 new).
- `makemigrations --check --dry-run`: No changes detected.
- `manage.py check` and `manage.py check --database default`: no issues.

**backend pytest run finished**

#### Review round 2 fixes (tmd-django-backend, 2026-09-25)

**Review round 2 fixes:** SF1 and the `UNNAMED_MEETING` nit are fixed. This corrects the round-1 note above, which wrongly said `create_meeting`'s occurrence parse was already safe.

**Files changed**
- `apps/zoom/providers.py`:
  - **SF1.** `create_meeting` now reads Zoom's occurrence list inside `except UNREADABLE_ANSWER:`, not `(KeyError, TypeError, ValueError)`. A non-object occurrence (`AttributeError`) or an overflowing time (`OverflowError`) now falls back to `()`. From there `approve()` takes criterion 24's DATES_DIFFER removal, where before it raised a 500 after Zoom had already made the meeting. A comment at the handler says why it must not raise.
  - **Nit.** The `UNNAMED_MEETING` comment no longer mentions a re-export.
- `apps/zoom/services.py` (nit): the unused `UNNAMED_MEETING` re-export and its `# noqa: F401` are gone. Ruff reports no other unused imports.
- `apps/zoom/tests/test_zoom_approve.py`: new `test_an_unreadable_occurrence_in_zooms_answer_removes_the_meeting_and_books_nothing`, parametrised over three non-objects (a string, an int and a list) in a weekly create's `occurrences`. Each case checks for a 200 re-render with the exact DATES_DIFFER message, exactly one DELETE (to the made meeting), and nothing booked. **On the old handler all three cases failed** with an uncaught `AttributeError` (for example `'list' object has no attribute 'get'`) raised from `providers.py` `create_meeting`. They pass with the fix.

**Context contract:** unchanged. **Migrations:** none. **Dependencies and settings:** none.

**Self-check output** (dev container; the dev stack was running and still is)
- `ruff check .`: All checks passed. `ruff format .`: 96 files left unchanged. `ruff format --check .`: 96 files already formatted.
- `pytest --create-db`: **919 passed in 57.32s** (916 + 3 new parametrised cases).
- `makemigrations --check --dry-run`: No changes detected.
- `manage.py check`: System check identified no issues (0 silenced).

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS (48 of 49 criteria; criterion 48 stays pending, owner action required).**

Verified 2026-09-25. Ran the full "Verify a change" checklist, re-checked every automated
criterion, walked both prod-image scenarios (`manual`, and `zoom` with dummy env-only
credentials) over HTTP/in-process, checked the dev DB for the `test_race.py` hazard, and took
the required screenshots. No product code was changed; only throwaway verification scripts were
used and removed (see "Tests added" and "Method notes" below).

### Checklist

| Check | Result |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `ruff format --check .` | ✅ 96 files already formatted |
| `pytest --create-db` (run 1) | ✅ **899 passed** in 46.61s |
| `pytest --create-db` (run 2) | ✅ 899 passed (confirmed via a third `--reuse-db` run, 899 passed in 51.28s) |
| `apps/zoom/tests/test_race.py` + `test_zoom_race.py`, 3 extra runs | ✅ 9 passed each run, no flakiness (3.56s / 3.28s / 3.25s) |
| `test_race.py` run alone | ✅ 5 passed (module-collection guard works; see hazard check below) |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `manage.py check` | ✅ 0 issues |
| `manage.py check --database default` | ✅ 0 issues (dev DB, `ZOOM_PROVIDER=fake`, E004 silent as designed) |
| `check --deploy`, prod, `USE_HTTPS=True`, `ZOOM_PROVIDER=zoom`, `ZOOM_CREDENTIAL_SETS=zoom-test` + 3 dummy values via `-e` | ✅ only `security.W021`, exit 0, no HTTP made (checks.py never imports `zoom_api`/`requests`) |
| `check --deploy`, prod, `USE_HTTPS=True`, `ZOOM_PROVIDER=manual` | ✅ `security.W021` and `zoom.W001`, exit 0 |
| Criterion 44 image check | ✅ prod image `/app` (with dotfiles) = `.env.example README.md apps config conftest.py docker manage.py media pyproject.toml requirements static staticfiles templates zoom-credentials.env.example` — no spreadsheet, no `zoom-credentials.env`. `find / -xdev` for `*.xlsx/*.xlsm/*.xls/*.ods/*.csv/zoom-credentials.env` inside the running prod container: no matches |
| Prod walkthrough (manual mode, HTTP on 8010) | ✅ see below |
| Prod walkthrough (zoom mode, dummy env-only creds) | ✅ see below |
| Dev-DB leftover check (`test_race.py` hazard) | ✅ see below |

### Test-database-hazard check (step 3 of the brief)

Queried the **dev** database (`polymath_tmd`) directly: `User.objects.filter(username__icontains='race')`, `HostAccount.objects.filter(label__istartswith='Race')`, `LinkRequest.objects.filter(class_name__istartswith='Race')` — **all empty**, both before and after this session's test runs. No leftover rows from tasks 008/010's earlier bare `test_race.py` runs, and none from this session.

Confirmed the new guard actively refuses a non-`test_` database. `apps/zoom/tests/test_race.py`'s `committed` fixture asserts `connection.settings_dict["NAME"].startswith("test_")` before yielding. I drove that exact code path directly (`committed.__wrapped__(...)`) with `connection.settings_dict["NAME"]` monkeypatched to `"polymath_tmd"`: it raised `AssertionError: committed rows must go to the test database…`, and with the real test DB name it proceeded normally. This was done in a throwaway scratch test file (`apps/zoom/tests/test_guard_check_scratch.py`), run, and then deleted — it is not part of the repo. `test_race.py` and `test_zoom_race.py` each also carry a `@pytest.mark.django_db`-marked `test_committed_rows_go_to_the_test_database`, which is what makes pytest-django set the test database up even when the module is collected alone (confirmed: `pytest apps/zoom/tests/test_race.py` alone — 5 passed, all against `test_polymath_tmd`).

### Acceptance criteria

| # | Result | Evidence |
|---|---|---|
| 1 | ✅ | `test_zoom_provider.py`/checks tests: `PROVIDERS == ("fake","manual","zoom")`; bad value → `zoom.E002` listing all three; default stays `manual` |
| 2 | ✅ | `apps/core/test_zoom_settings.py` (prefix rule, source scan, no `ZOOM_S2S_` reads outside `base.py`) |
| 3 | ✅ | `test_zoom_settings.py`: `get_safe_settings()["ZOOM_S2S_SECRETS"]` masked; confirmed independently — no dummy value appeared in the deploy-check output or prod-mode page renders (see below) |
| 4 | ✅ | `checks.py` E005 tests (empty set, missing var, bad slug, duplicate name) |
| 5 | ✅ | E001/prod.py/W001 tests; **re-confirmed live**: both `check --deploy` runs above match exactly |
| 6 | ✅ | E004 tests (offender message, inactive/free excluded, table-missing case, silent for fake/manual); **re-confirmed live**: dummy `zoom-test` set + `check --database default` reported E004 for the two unconnected local accounts (backend self-check, reproduced) |
| 7 | ✅ | `compose.yaml` `env_file`, `zoom-credentials.env.example` present with empty values, `.gitignore`/`.dockerignore` entries confirmed, `LOGGING.urllib3=WARNING` test |
| 8 | ✅ | `test_zoom_api.py`: fixed hosts, `(5,15)` timeout, no `verify=False`/`http://` scan, scheme/host assertions |
| 9 | ✅ | `test_zoom_api.py`: Basic auth + body `account_id`, 300s cache margin, single 401 retry, second 401 raises |
| 10 | ✅ | `test_zoom_api.py::test_api_failures_map_to_fixed_phrases` (all 6 kinds), `test_the_lasting_flag_and_phrase_of_each_kind`, `test_a_plain_provider_error_is_temporary_and_certain` |
| 11 | ✅ | `test_zoom_api.py::test_an_error_report_from_inside_the_token_fetch_masks_the_secret`, `test_sensitive_variables_mark_every_function_holding_a_secret_or_token` |
| 12 | ✅ | `test_zoom_provider.py` (paging, type-2/8/deleted-occurrence, type-1/3/4 ignored, touching-window not a clash) |
| 13 | ✅ | provider/approve tests: de-dup by `meeting_id`, marker exclusion, other-marker clash |
| 14 | ✅ | weekday-mapping unit test, all 7 + `"1,3"` case |
| 15 | ✅ | `test_zoom_preview.py`: `zoom_state` table, `account_edit_allowed` per state/permission (G1), `zoom_clashes` ordering (G2), `zoom_problem` sentence for all 6 kinds (G6); **re-confirmed visually** — screenshot `mixed_states_1440.png` shows a Busy row with a Zoom clash line, an `unavailable` row, and a `not_connected` row together |
| 16 | ✅ | preview test for `zoom_checked_at`; **visually confirmed** — "Checked with Zoom at 4:11 pm." on the mixed-states screenshot |
| 17 | ✅ | `test_zoom_preview.py`/`test_views.py`: no approve form, D24 sentence, reject stays, G3 ordering (`has_started` beats `all_unchecked` beats "none free"); **visually confirmed** — `all_unchecked_1440.png` shows the exact pinned text with D24's added sentence and no approve form |
| 18 | ✅ | manual-mode tests; **visually confirmed** — `detail_manual_1440.png`/`_400.png` show the pinned notice |
| 19 | ✅ | preview tests: 6-worker/8s-deadline, 60s cache, two loads within 60s → one HTTP set, 61s later → new calls |
| 20 | ✅ | `test_zoom_race.py::test_no_transaction_is_open_while_zoom_is_asked`; query-count test independent of meeting count |
| 21 | ✅ | `test_zoom_approve.py` ordered-log test (HTTP before locks, then locking reads/UPDATE/INSERT, then one POST, then UPDATE+commit) |
| 22 | ✅ | one-off payload test (exact JSON, stored fields, `start_url` dropped everywhere) |
| 23 | ✅ | weekly payload test (`recurrence`, `weekly_days`, `zoom_occurrence_id` matching) |
| 24 | ✅ | date-mismatch test (delete, no booking, no email, 200 + pinned message) |
| 25 | ✅ | recording on/off → explicit `auto_recording` test |
| 26 | ✅ | clash-at-approval test (no POST, 409, pinned message, availability refreshed) |
| 27 | ✅ | leftover-marker delete-before-create test, and the failed-delete-stops-approval sub-case |
| 28 | ✅ | list-fails-at-approval test, all 6 kinds, temporary/lasting next-step pinned |
| 29 | ✅ | not-connected 409 test |
| 30 | ✅ | `test_zoom_approve.py`: (a) all certain-failure kinds, (b) all three clean-up endings (found/not-found/couldn't-check), amended criterion-40-equivalent fake message |
| 31 | ✅ | save-fails-after-create test (compensating DELETE, retry-then-succeeds, DELETE-also-fails message + one ERROR log line) |
| 32 | ✅ | (a)/(b)/(c) thread tests in `test_zoom_race.py`, run 4 times total this session (once in the full suite, 3 extra) — no flakiness |
| 33 | ✅ | fake/manual unaffected: full suite includes unmodified 005 criteria 35-41 (amended 40) and 36 |
| 34 | ✅ | `test_accounts.py`: field present, help text, regex/40-char validation, G4 widget attributes and field order; **visually confirmed** — all 3 account-state screenshots show name/order/attributes |
| 35 | ✅ | `zoom_connection_state` tests (none/missing/ready, no HTTP/no query); **visually confirmed** on list and change-page screenshots |
| 36 | ✅ | `test_zoom_accounts_connection.py`: permission/method/non-atomic, token→user→list order, all 8 message rows; **re-confirmed live in zoom mode** — `ZoomAuthFailed` produced the exact pinned message with the real slug, and the "name not set" message fired instantly with no outbound call (manual-mode walkthrough) |
| 37 | ✅ | `check_zoom_connections` tests; **re-confirmed live** — real run against dummy `zoom-test` printed one line per account and exited 1, no secret in output |
| 38 | ✅ | scope names recorded in backend's Implementation notes, matched against D13; README to be written by docs-writer |
| 39 | ✅ | grep of `apps/zoom/urls.py` and views: no `webhook` name/path |
| 40 | ✅ | `test_zoom_accounts_connection.py::test_no_credential_or_token_reaches_a_page_a_message_or_the_email`; **re-confirmed live** — searched the zoom-mode detail page, check-connection redirect page and `check_zoom_connections` output for all three dummy values: zero matches |
| 41 | ✅ | migration `0005` reviewed (field, help text, validator); `makemigrations --check` clean; secret-field-pattern test still passes |
| 42 | ✅ | `requirements/base.txt`/`dev.txt` comments confirmed; prod image built with no extra build tools (devops self-check) |
| 43 | ✅ | frontend's host-side template-rule replicas plus the file-scan tests in `apps/core/tests.py`, part of the 899-test run |
| 44 | ✅ | re-checked independently in step 4 above (not just devops's earlier self-check): pattern list confirmed in `.dockerignore`, image build + `ls -A /app` + filesystem `find` all clean |
| 45 | ✅ | project `conftest.py` reviewed; `test_zoom_api.py::test_an_unregistered_zoom_call_never_leaves_the_machine` passed as part of the 899-test run; `config/settings/test.py` keeps `ZOOM_PROVIDER="fake"` |
| 46 | ✅ | both `check --deploy` runs reproduced live, exact output above |
| 47 | ✅ | reproduced live: manual-mode notice, accounts list column, `zoom-test` → "Missing on the server", check-connection "name not set" with no call, hashed static paths (`style.fe7f37415158.css`, `app.2456fc2beeea.js`). Screenshots: `detail_manual_{1440,400}.png`, `accounts_list_{1440,400}.png`, `mixed_states_{1440,400}.png` (unavailable + not_connected + Zoom-clash row together), `all_unchecked_{1440,400}.png` ("nothing can be checked"), `account_state_{none,missing,ready}_1440.png` (change page, all 3 connection states) |
| 48 | ⏳ **Pending — owner action required.** | Not run; no real Zoom account or credentials were available to or used by this verifier. See "Owner's live check" below |
| 49 | ✅ | `test_zoom_provider.py`: `settings` object has only `auto_recording`, none of `join_before_host`/`jbh_time`/`waiting_room` at any level, all 4 combinations; source scan confirmed independently (`grep -rn` for those 3 names in `apps/zoom/` outside `tests/`: no matches) |

### Owner's live check (criterion 48) — steps to give the owner

The main session should hand the owner exactly this (from the brief, §criterion 48), and the
verifier will record the reported results once run:

1. Put the three real credential values in `zoom-credentials.env` (next to `.env`, never
   committed), set `ZOOM_PROVIDER=zoom`, and leave that one account's **host key empty** on the
   Zoom accounts page first, so no real key reaches the console email log.
2. Recreate `web` (`docker compose up -d`) so it reads the file.
3. On the Zoom accounts page, set that account's Zoom connection name and press **Check
   connection** — expect `The Zoom connection works for {label}.`
4. In Zoom itself, create a meeting directly on that account for a future time T. A request
   overlapping T should show that account Busy with `In Zoom: {topic}`, and not offer it.
5. Approve a weekly request (2 weeks, 2 days, "Record this class" ticked) on that account.
   Confirm in Zoom: one recurring meeting, 4 occurrences at the right Colombo times, automatic
   cloud recording on, and the emailed link/ID/passcode match what Zoom shows.
6. Restart with a deliberately wrong client secret and confirm the detail page shows "Couldn't
   check with Zoom", Check connection shows the auth message, and nothing can be approved.
7. Clean up: delete the test meetings in Zoom (011 isn't built yet), restore the real secret,
   and note that account's own "join before host" / "waiting room" settings for the record (D19).
8. **Added after review round 1 (SF4).** On marketplace.zoom.us, open the Server-to-Server OAuth
   app's Scopes page and confirm the five scope names in criterion 38 / the backend's
   Implementation notes are exactly what's granted (`meeting:write:meeting:admin`,
   `meeting:read:list_meetings:admin`, `meeting:read:meeting:admin`,
   `meeting:delete:meeting:admin`, `user:read:user:admin`), with no others needed. The backend
   wrote these from memory (no web access during this brief); the docs writer marks them
   "confirmed" only once the owner reports back here.
9. **Added after review round 1 (SF4).** In Zoom's current API docs for
   `POST /users/{userId}/meetings`, confirm `recurrence.end_times` still allows at most 60. D5's
   cap (`end_times = number of classes`, capped at 60 by the request form) was also written from
   memory. If Zoom's limit is now lower than 60, that's a blocker to report, not something to
   work around silently.

Until the owner reports these results, the task stays in **Verifying**, not **Done**. Criterion 48
stays pending after this re-verification round too: steps 8 and 9 are additions to what the owner
is asked to check, not something the verifier can confirm without web access to Zoom's live
Marketplace and docs.

### Tests added

None required adding — the existing 899 tests already cover every automatable criterion,
including the network block and the six error kinds. This session added only throwaway
verification scripts (deleted before finishing): a guard-check test for `test_race.py`'s new
`test_` database assertion, and several `manage.py shell` scripts used to steer `FakeProvider`
and render pages for screenshots. None were committed; `git status` after this session shows no
new files under `apps/`.

### Method notes (for reviewer transparency)

- The zoom-mode fail-closed walkthrough (step 5) used `docker compose exec -e ZOOM_PROVIDER=zoom
  -e ZOOM_CREDENTIAL_SETS=zoom-test -e ZOOM_S2S_ZOOM_TEST_*=dummy-*-not-real web python manage.py
  shell` to drive the real view/service code through Django's test `Client` and a `subprocess`
  call to `check_zoom_connections`, rather than recreating the long-running prod container —
  `compose.yaml` deliberately keeps individual Zoom credential names out of `web.environment`
  (D2), so a container recreated via `docker compose up` cannot pick up per-variable `-e`
  overrides without writing `zoom-credentials.env` to disk, which the task told me not to do.
  This exercises the exact same production code paths (real settings module, real views, real
  templates) with dummy env-only credentials against the real, reachable Zoom API, which
  returned genuine `400 invalid_client` responses — mapping to `ZoomAuthFailed` (**lasting**,
  not "temporary"). I could not force a genuinely temporary (`ZoomUnavailable`) response because
  the container has real internet egress to `zoom.us`/`api.zoom.us` and `/etc/hosts` is
  read-only for the non-root `app` user, so I did not fabricate one; `ZoomAuthFailed` is still a
  fully valid, observed fail-closed path covering all four required checks (Couldn't-check row,
  no approve form, Check-connection error message, `check_zoom_connections` exit code), and no
  credential value appeared anywhere in the output or in `docker compose logs`.
- Dev-mode screenshots of Zoom states used `FakeProvider`'s class-level steering plus Django's
  test `Client`, per the backend's note that a running dev server can't be steered from outside.
  Rendered HTML was saved with a `<base href="http://127.0.0.1:8010/">` tag and then opened
  locally in headless Chromium (Playwright, installed to the scratchpad only) so real CSS/JS/icon
  assets loaded from the live dev server.
- A throwaway superuser (`verifier_temp`) was created for the prod-image HTTP walkthrough and
  deleted afterwards; account 15's `credential_set` (set to `zoom-test` mid-walkthrough) was
  reverted to `''` afterwards. The dev database's row counts (2 users, 4 accounts, 13 requests)
  match the pre-session state.

### Re-verification (round 1 fixes) — 2026-09-25

**Verdict: PASS (48 of 49 criteria; criterion 48 still pending the owner).** Re-ran the full
"Verify a change" checklist against the backend's and frontend's round 1 fixes (SF1–SF3), confirmed
SF1–SF3 each with either a revert-and-restore or a direct code/test inspection, re-walked the prod
manual-mode HTTP scenario plus a dev fake-provider clash scenario, and added SF4's two extra
owner-live-check steps. No product code changes remain: every temporary revert made for this
round's spot-checks was restored and confirmed byte-identical with `diff` against a scratchpad
backup before the final full test run. `git status` after this session still shows only the same
files the previous verification round listed as modified/untracked — no new files under `apps/`.

**Checklist**

| Check | Result |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `ruff format --check .` | ✅ 96 files already formatted |
| `pytest --create-db` (run 1) | ✅ **916 passed** in 56.25s |
| `pytest --create-db` (run 2) | ✅ **916 passed** in 58.13s |
| `pytest --create-db` (run 3, after the SF1/SF2/SF3 revert-and-restore spot-checks, to confirm the working tree was left clean) | ✅ **916 passed** in 59.38s |
| `makemigrations --check --dry-run` | ✅ No changes detected (checked twice: before and after the prod/dev stack switches) |
| `manage.py check` | ✅ 0 issues |
| `manage.py check --database default` | ✅ 0 issues |
| `check --deploy`, prod, `USE_HTTPS=True`, `ZOOM_PROVIDER=zoom`, `ZOOM_CREDENTIAL_SETS=zoom-test` + 3 dummy values via `-e` | ✅ only `security.W021`, exit 0 |
| `check --deploy`, prod, `USE_HTTPS=True`, `ZOOM_PROVIDER=manual` | ✅ `security.W021` and `zoom.W001`, exit 0 |
| Criterion 44 image check (re-run independently this round) | ✅ `ZOOM_PROVIDER=manual docker compose run --rm --no-deps web ls -A /app` → `.env.example README.md apps config conftest.py docker manage.py media pyproject.toml requirements static staticfiles templates zoom-credentials.env.example`; filesystem-wide `find / -xdev` for `*.xlsx/*.xlsm/*.xls/*.ods/*.csv/zoom-credentials.env` inside `polymath-tmd:latest`: no matches |
| Prod walkthrough (manual mode, HTTP on 8010) | ✅ see below |
| Dev walkthrough (fake provider, Zoom clash, `display_topic`) | ✅ see below |
| Stack restored | ✅ dev stack running again, `/healthz/` 200, no leftover test data |

**Backend's reported 916 confirmed.** Both required `pytest --create-db` runs (and a third,
post-spot-check, run) came back **916 passed**, no flakiness, matching the backend's self-check
exactly (899 + 17 new from the round 1 fixes).

**SF1–SF3, confirmed with tests that fail on the pre-fix code**

- **SF1 (`providers.py`, `busy_times`).** Confirmed live: with the fix in place,
  `test_zoom_approve.py::test_an_unreadable_zoom_answer_at_approval_is_criterion_28s_message`
  passes for all three parametrised cases (another meeting's garbage `start_time`, this
  request's own leftover, and a non-object list entry), each producing criterion 28's exact
  message (`We couldn't check Zoom 01's meetings in Zoom, so nothing was booked. No answer from
  Zoom. Try again in a few minutes.`) with a 200, no `POST`, no `DELETE`. Temporarily reverted
  the fix (removed the `try/except UNREADABLE_ANSWER: raise ZoomUnavailable() from None` wrapping
  around the list-reading loop and the per-series reading, restoring the bare unwrapped code) and
  re-ran the same test: all three cases **failed**, each with an unhandled
  `AttributeError: 'str' object has no attribute 'get'` bubbling out of the view as an
  unhandled 500 (visible in the pytest traceback through
  `services.approve → _check_zoom_first → provider.busy_times → providers.py:322`). Restored
  `apps/zoom/providers.py` from a pre-revert scratchpad copy and confirmed byte-identical with
  `diff`. This is the criterion-28-not-a-500 behaviour the review asked to be pinned, and it now
  is.
- **SF2 (`account_tag.html` / `HostAccount.needs_zoom_connection`).** This is a DRY
  consolidation, not a behaviour fix: `is_bookable_with(is_active=True, is_paid=True)` (which
  `needs_zoom_connection` is built on) is defined as exactly `is_active and is_paid`
  (`models.py:147-153`), the same two flags the template used to test directly. Confirmed live
  over HTTP on the prod stack that the three paid+active accounts (`Zoom 01`/`02`/`03`) render
  `tag--warn` + `alert-triangle` + "Not set up", and the one free account (`Zoom free`) renders
  `tag--plain` + `slash` + "Not set up" — exactly the output the pinned rule requires. Then
  temporarily reverted both the template (`{% elif needs_zoom_connection %}` back to
  `{% elif paid and active %}`) and `accounts.html`'s `with:` values (`needs_zoom_connection=…`
  back to `paid=… active=…`) and re-ran the full `apps/zoom` + `apps/core` suite: **729 passed**,
  no failures. So, honestly: **no existing test would have caught this one on the old code**,
  because the old and new logic are behaviourally identical for every real combination of flags
  — the review's own wording ("the template re-derives the rule") already frames this as a
  code-quality/DRY finding rather than a functional bug, and that framing holds up. The dedicated
  new unit tests (`test_only_an_account_that_can_be_booked_needs_a_zoom_connection`,
  `test_the_accounts_list_warns_only_where_a_connection_is_needed`) pin the model property and
  the view's context directly; they would fail if the property were removed or returned the
  wrong value, but they do not exercise the template's own (now-removed) copy of the rule.
  Restored both files from scratchpad backups and confirmed byte-identical with `diff`.
- **SF3 (`BusyTime.display_topic`).** Stronger case: `services.py`'s criterion 26 message
  builder (`ZOOM_CLASH`, `services.py:568`) and `avail_item.html`'s clash line both now call
  `busy.display_topic`, so the property is a genuine single dependency, not just parallel
  identical text. Temporarily removed the `display_topic` property from `BusyTime` in
  `providers.py` and re-ran `test_zoom_provider.py`, `test_zoom_approve.py` and
  `test_zoom_preview.py`: **4 tests failed** with `AttributeError: 'BusyTime' object has no
  attribute 'display_topic'`
  (`test_a_zoom_meeting_with_no_topic_has_a_plain_name`,
  `test_a_meeting_made_in_zoom_since_the_page_loaded_stops_the_approval`,
  `test_a_meeting_with_no_topic_is_named_plainly`,
  `test_the_fake_provider_can_be_steered_to_a_zoom_clash`). Restored `providers.py` from a
  scratchpad backup and confirmed byte-identical with `diff`. Also confirmed live in the dev
  stack (fake provider, steered via `manage.py shell` + Django's test `Client` against
  `/zoom/requests/42/`): a Zoom clash with an empty topic renders `In Zoom: a meeting with no
  name`, and one with `topic="Staff <b>Meeting</b>"` renders `In Zoom: Staff
  &lt;b&gt;Meeting&lt;/b&gt;` — auto-escaped, matching criterion 15's "the topic is escaped".
  The forms.py (`CREDENTIAL_SET_HELP`) and checks.py (`CREDENTIAL_SET_ERROR`) halves of SF3 are
  the same category as SF2 (single-sourcing text that was already identical in both places), so
  no behavioural test distinguishes old from new there either; `test_accounts.py`'s
  `field.help_text == HostAccount._meta.get_field("credential_set").help_text` and
  `test_zoom_accounts_connection.py`'s `E005's hint is NAME_RULE` assertion pin the single
  source going forward.

**Prod-image HTTP walkthrough (manual mode, `ZOOM_PROVIDER=manual`, 8010)**

Rebuilt with `ZOOM_PROVIDER=manual docker compose up -d --build`; `web` became healthy. Created a
throwaway superuser (`verifier_r1`), logged in with cookie-based `curl` session and each form's
own CSRF token.

- **Accounts list tag states.** `/zoom/accounts/` (200): `Zoom 01`/`02`/`03` (paid, active, no
  connection name) each show `tag--warn` + `alert-triangle` + "Not set up"; `Zoom free`
  (unpaid) shows `tag--plain` + `slash` + "Not set up" — SF2's fixed rule, confirmed rendered.
  Setting `Zoom 01`'s `credential_set` to `zoom-test` (not in `ZOOM_S2S_SECRETS`) via the real
  change form (200 → 302) then showed `tag--warn` + `alert-triangle` + "Missing on the server" on
  the list and `The server has no Zoom connection called zoom-test.` on the change page — then
  reverted to `''` and confirmed via `manage.py shell`.
- **`Check connection` with no name set** (criterion 47.4): `POST /zoom/accounts/14/check/`
  (account with an empty `credential_set`) → 302 to the change page, flash message `Zoom 02 has
  no Zoom connection name yet. Type it in, save, then check again.` — the exact criterion 36
  "name not set" message, and no outbound call is possible before that check runs (the view
  short-circuits on an empty name).
- **Manual-mode notice** (criterion 18): `/zoom/requests/42/` (200) shows `This system can't see
  meetings made directly in Zoom. Before you approve, check the chosen account's meetings in
  Zoom.` verbatim.
- **Hashed static paths**: `style.fe7f37415158.css`, `app.2456fc2beeea.js`,
  `theme-init.23a9a55193e6.js` all loaded from hashed filenames.
- **Criterion 44 image check**, re-run independently (see checklist table above): clean.

Deleted the throwaway superuser and confirmed `credential_set` on account 13 was back to `''`
afterwards (`manage.py shell`).

**Dev walkthrough (fake provider, SF3's `display_topic`, criterion 15)**

Switched to the dev stack (`docker compose -f compose.yaml -f compose.dev.yaml up -d --build`;
volumes and prior data kept). Per the backend's note that a running dev server can't be steered
from outside, drove `FakeProvider.busy[account.pk]` class-level steering through
`manage.py shell` + Django's test `Client` (with `HTTP_HOST=127.0.0.1`, and clearing the 60-second
preview cache between the two steered calls so each saw its own busy times) against
`/zoom/requests/42/`:

- an empty-topic `BusyTime` produced `In Zoom: a meeting with no name`;
- a `BusyTime` with `topic="Staff <b>Meeting</b>"` produced `In Zoom: Staff
  &lt;b&gt;Meeting&lt;/b&gt;`, correctly escaped.

Both confirm `clash.busy.display_topic` is wired end-to-end, matching the backend's and
frontend's coordinated fix.

**SF4 — added to the owner's live check.** Appended two new steps (8 and 9) to "Owner's live
check (criterion 48) — steps to give the owner" above: confirming the five scope names (criterion
38) on marketplace.zoom.us, and confirming Zoom's current `recurrence.end_times` cap of 60 (D5)
in Zoom's API docs. Both are things the backend wrote from memory with no web access this
session; this verifier likewise has no live access to Zoom's Marketplace or docs, so neither can
be confirmed here. **Criterion 48 stays pending** — the owner's report now needs to cover these
two extra confirmations as well as the original seven steps.

**Tests added:** none required. This round only re-confirmed the backend's and frontend's own
round 1 test additions, plus throwaway scratchpad scripts used for the revert/restore spot-checks
and the dev-stack steering (all deleted before finishing; none committed).

**Stack restored:** dev overlay, matching what was running at the start of this session.
`/healthz/` on 8010 returned 200. Row counts (2 users, 4 host accounts) match the pre-session
state; no throwaway user or test data remains.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-25 (verifier PASS 48/49, criterion 48 pending the owner)

**Verdict: CHANGES REQUESTED.** Blockers: none.

**Should fix**
1. **A malformed Zoom time isn't treated as a Zoom failure** (`providers.py:105-110, 364, 385`).
   - `parse_zoom_time` raises `ValueError`, and approve() catches only `ProviderError` (`services.py:541, 790`).
   - A bad `start_time` during the step-1 lookup or the 30(b) clean-up therefore gives a 500, not the pinned message.
   - Fix: in `busy_times`, raise `ZoomUnavailable() from None`, and add a test that approves with `start_time` set to "garbage".
   - Owner: backend.
2. **The template re-derives the "bookable" rule** (`account_tag.html:2`).
   - `{% elif paid and active %}` repeats `BOOKABLE_FLAGS` / `is_bookable_with`.
   - Fix: pass a model-derived value instead. Main-session ruling: add `HostAccount.needs_zoom_connection`, built on `is_bookable_with`, and pass that to the partial.
   - Owner: backend, then frontend.
3. **Copy is defined in more than one place.**
   - `forms.py:294` `CREDENTIAL_SET_HELP` duplicates the model's `help_text` (`models.py:340-341`).
   - `checks.py:112` hard-codes `CREDENTIAL_SET_ERROR` (`validators.py:17`).
   - `avail_item.html:15` hard-codes `services.UNNAMED_MEETING`. Main-session ruling: add `BusyTime.display_topic`.
   - Owner: backend, plus frontend for the template.
4. **Zoom facts that were never checked against Zoom's docs.** The scope names (criterion 38) and the `end_times` limit of 60 (D5) were written from memory.
   - Fix: add both checks to the owner's live check (criterion 48). The docs writer marks the scopes "confirmed" only after the owner reports back.
   - Owner: main session / verifier.

**Nits**
- `services.py:705-713`: if the COMMIT itself fails ambiguously (MySQL 2013), the result can be an approved request with a deleted meeting. The trade-off is accepted; name it in `_approve_once`'s docstring.
- `zoom_api.py:139`: `ZoomClient`'s `requests.Session` is never closed. Add `close()` or a context manager, and use it in `ZoomProvider`.
- `providers.py:297-306`: recurring series are read one after another, against the 8-second preview deadline. Add this to the risk register.
- `services.py:283-293`: the preview cache is LocMem, one per Gunicorn worker. Say "per worker" in the docstring.
- `checks.py:26`: importing `config.settings.base` directly needs a comment explaining why.
- `checks.py:143`, `check_zoom_connections.py:22`: `order_by("sort_order","label")` repeats `Meta.ordering` and can go.
- Docs at close: CLAUDE.md still names "the importer in task 007" as a caller of approve(). The "Adding an env var" gotcha also needs the `zoom-credentials.env` `env_file` exception.

**Checked and found sound:**
- Credential handling: read from env in `base.py` only; masking verified; `sensitive_variables` on every frame; urllib3 pinned to WARNING; `zoom_api.py` as the only HTTP module, with HTTPS, `allow_redirects=False`, no `verify=`, Basic auth plus a form body, and errors raised `from None`.
- approve(): the order, the compensating delete, deadlock retry, idempotency, and `_wait_for_other_attempts`, which fits the lock order.
- Recurring meetings: the weekday mapping, Colombo time, exact-match dates that fail safe, and the cap of 60.
- The clash check: types 2 and 8 only, fails closed, no database use in threads, and a locked token cache.
- D19, the pinned messages, the test_race guard, and the network block.

### Round 2 — 2026-09-25 (re-verification PASS, 916 tests ×3)

**Verdict: CHANGES REQUESTED** (one new small item). Blockers: none.

**Round-1 items: all fixed.**
- SF1 is fixed (`providers.py:314-338`).
- SF2 is fixed: `needs_zoom_connection` (`models.py:450-460`), `account_tag.html:2`, `accounts.html:33`.
- SF3 is fixed: `display_topic`, the help text coming from the model, and `CREDENTIAL_SET_ERROR`.
- SF4 is fixed: steps 8 and 9 of the owner's live check.
- All nits are fixed.

**Should fix**
1. **`create_meeting` misses two exception types when reading Zoom's occurrence list** (`providers.py:356-363`).
   - It catches only `(KeyError, TypeError, ValueError)`. It misses `AttributeError` and `OverflowError`, which `UNREADABLE_ANSWER` covers.
   - This error happens after Zoom has made the meeting but before `made` is assigned (`services.py:680`). So no compensating delete runs, and IT gets a 500. The meeting stays in Zoom until the next attempt's marker clean-up removes it.
   - Fix: change the handler to `except UNREADABLE_ANSWER:`, so it falls back to `()` and then to criterion 24's DATES_DIFFER removal. Add a test in which a weekly create's `occurrences` holds a non-object; it should get DATES_DIFFER and exactly one DELETE.
   - Owner: backend.

**Nits**
- `services.py:53-54`: the `UNNAMED_MEETING` re-export has no users. Drop it, along with the comment at `providers.py:64`.
- **Risk register:** reading recurring series one after another against the 8-second preview limit still isn't in the register. Main-session ruling: the docs writer adds it to R1 or R6 at close.
- **At close:** fix CLAUDE.md's "importer in task 007" wording, and add the `zoom-credentials.env` `env_file` exception to "Adding an env var".

### Round 3 — 2026-09-25 (after round-2 fix; backend self-check 919)

**Verdict: APPROVE.** No blockers or should-fix findings.

- **Round-2 should-fix 1: fixed.**
  - `providers.py:361-364` now uses `except UNREADABLE_ANSWER:`, the same tuple `busy_times` uses. Its comment explains why it can't raise.
  - An empty `occurrence_ids` falls through to `_DatesDiffer`, so the compensating delete runs with `made` already set.
  - The new test, `test_zoom_approve.py:241-258`, goes through the real view and checks the DATES_DIFFER message, exactly one DELETE, and nothing booked.
- **The unused re-export is removed.** `UNNAMED_MEETING` is now defined once, at `providers.py:64`.
- **Carried to close:** the risk-register entry for series reads made one after another, CLAUDE.md's "importer in task 007" wording, and the `zoom-credentials.env` exception in "Adding an env var".
- **Conditions:** this approval depends on the parallel re-verification passing. The task stays **Verifying** until the owner runs criterion 48, including steps 8 and 9.

### Re-verification (round 2 fix) — 2026-09-25

**Verdict: PASS (48 of 49 criteria; criterion 48 still pending the owner).** Re-checked the
round-2 review's one "should fix" item (`create_meeting`'s occurrence-parsing exception handler,
now `except UNREADABLE_ANSWER:`), the new three-case test, and the removed unused
`UNNAMED_MEETING` re-export, then re-ran the full "Verify a change" checklist. Dev stack was
already running and was left running.

**Checklist**

| Check | Result |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `ruff format --check .` | ✅ 96 files already formatted |
| `pytest --create-db` (run 1) | ✅ **919 passed** in 61.38s |
| `pytest --create-db` (run 2) | ✅ **919 passed** in 64.60s |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `manage.py check` | ✅ System check identified no issues (0 silenced) |
| `manage.py check --database default` | ✅ System check identified no issues (0 silenced) |
| dev `/healthz/` | ✅ 200 |
| Stack | ✅ dev stack, unchanged, still running after this round |

**Backend's reported 919 confirmed**, both runs, no flakiness.

**Spot-check: the new test fails on the pre-fix handler.** Temporarily changed
`create_meeting`'s handler back to `except (KeyError, TypeError, ValueError):` and ran
`test_an_unreadable_occurrence_in_zooms_answer_removes_the_meeting_and_books_nothing` alone: all
three parametrised cases (`"not a class"`, `7`, `["a", "list"]`) **failed**, each with an
uncaught `AttributeError: 'list' object has no attribute 'get'` raised from `providers.py`'s
`create_meeting`, exactly as the backend's notes describe — confirming the test would have
caught the pre-fix regression. Restored `except UNREADABLE_ANSWER:` and re-ran the same test
file: all cases passed again (46 passed). `git diff apps/zoom/providers.py` after the restore
shows only the review round 2 fix itself (`except UNREADABLE_ANSWER:` at line 361, with the
"why it must not raise" comment) — no residue from the temporary edit.

**The other round-2 fix confirmed by inspection:** the unused `UNNAMED_MEETING` re-export and
its `# noqa: F401` are gone from `apps/zoom/services.py`; `UNNAMED_MEETING` is now defined and
used only in `apps/zoom/providers.py` (`grep` confirms no reference remains in `services.py`).

**No product code changes remain from this round's verification.** `git status` after this
session shows the same files as modified/untracked that the previous verification round listed
— no new files under `apps/`.

**Acceptance criteria:** unchanged from the previous round's table (48/49 ✅, criterion 48 ⏳
pending the owner's live check — not re-run here, no real Zoom account or credentials were used).

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Files updated (2026-09-25):**

- **`README.md`:** the "Zoom link requests" section is rewritten for live Zoom —
  - a new "Zoom providers" table (`fake` / `manual` / `zoom`, when to use each);
  - a new "Connecting an account to Zoom" walkthrough (D16's 11 setup steps), `zoom-credentials.env`
    (copied from `zoom-credentials.env.example`, never committed, never baked into the image), the
    five scopes — **marked unconfirmed until the owner's live check, criterion 48 step 8** — where
    the connection name goes and how to press Check connection, rotating a secret, and
    `check_zoom_connections`;
  - a "rules to follow" list: always schedule dated meetings in Zoom, never no-fixed-time or PMI
    (D20); check each account's own "join before host" and "waiting room" settings (D19); a meeting
    made directly in Zoom now counts as busy;
  - "known limits" (D15), including the new risk that recurring series are read one after another
    against the 8-second preview deadline, and the 60-classes-per-series cap — **marked unconfirmed
    until the owner's live check, criterion 48 step 9**;
  - the manual-mode paragraph reworded as a fallback, and the go-live gate replaced with D14's
    (006, running `zoom` with every paid account connected, plus 011);
  - every trace of the spreadsheet import (brief 007) as a data source or a go-live step is gone;
    the spreadsheet's only remaining mention anywhere in the repo is in `.gitignore`/`.dockerignore`;
  - the "Running with Docker" section now mentions `zoom-credentials.env`, that a local prod run
    with `.env`'s `ZOOM_PROVIDER=fake` needs `ZOOM_PROVIDER=manual` or `=zoom` in front of the
    command (not a `.env` edit), and a security note that builds made before 2026-09-25 could have
    copied `Dashboard 2A.xlsx` into the image;
  - the "Deploying the image" env-var table's `ZOOM_PROVIDER` row is updated, with a note that Zoom
    credentials live only in `zoom-credentials.env`, never in that table or `web.environment`.
- **`CLAUDE.md`:**
  - the `zoom` app bullet now names the live provider, `zoom_api.py` as the only HTTP module, that
    Zoom credentials never touch the database, and `approve()`'s asks-before-locks-one-create order
    with its compensating delete and marker clean-up. The "importer in task 007" wording is gone —
    there is no second caller of `services.approve()` today;
  - "Adding an env var" gains the `zoom-credentials.env` `env_file` exception (Zoom credential
    variables deliberately stay out of `web.environment`);
  - the `ZOOM_PROVIDER` gotcha now covers `manual` raising `zoom.W001` under `check --deploy`, and
    running `check --database default` for `zoom.E004`;
  - a new gotcha for the root `conftest.py` network block and never using `@responses.activate`.
  - Every change is additive or reworded in place; no section or bullet was deleted.
- **`docs/CHANGELOG.md`:** a new newest-first entry, 2026-09-25, "006: Live Zoom connection (awaiting
  the owner's live check)", marked as such throughout, plus a Security line for the `.dockerignore`
  spreadsheet fix. The 005, 008 and 009 entries' follow-ups that named brief 007 each gain a dated
  "*Superseded 2026-09-25 …*" note pointing at the 006 entry; their original text is left as written,
  per "don't rewrite history".
- **`docs/design/availability-list.md`:** the three new states from brief 006 D.1.4 (Couldn't check /
  `help-circle`, Not connected / `slash`, and a busy row mixing a database clash with a Zoom-only
  clash) are added to the States table, and `.avail__note` is added to the Values table. The origin
  line now credits brief 006 too. `docs/design/busy-button.md` is already brief 006's own component
  doc and needed no change.
- **`docs/tasks/006-live-zoom-connection.md`** (this file): the risk register's R1 row gains the
  recurring-series-read risk that review round 1 asked for (a nit, resolved by the main session's
  authorisation to edit the planner's section directly); this Docs section; Status left at
  `Verifying`.
- **`docs/tasks/005-zoom-link-requests.md`, `008-zoom-accounts.md`, `009-zoom-timetable.md`,
  `010-staff-and-access.md`:** every passage the agent plan listed that named the 007 import or the
  old go-live gate gains a short dated "*Amended by 006 (2026-09-25): 007 dropped; gate = 006 + 011*"
  note (or, where a brief didn't name 007, a note that the gate now also needs 006). 005's D4 and D16
  additionally note that 006's actual interface and credential naming (D2) supersede those outlines.
  008's D5 notes that `credential_set` is now on the form, as 006 delivered. None of the four briefs'
  own text is rewritten — each note is appended next to the passage it corrects.
- **Not touched, by design:** `apps/zoom/models.py`'s module docstring (fixed by the backend in step
  3, per the agent plan) and the memory note `zoom-requests-feature.md` (outside the repo; the main
  session's own job, not this agent's).

**Status stays `Verifying`, not `Done`.** Verification is PASS on 48 of 49 criteria (919 tests, run
twice, across three re-verification rounds) and Review is APPROVE (round 3). The one open item is
criterion 48, the owner's live check against one real paid Zoom account — including confirming the
Marketplace scope names (step 8) and Zoom's current `recurrence.end_times` cap (step 9), both of
which the README above marks "unconfirmed" until then. This brief closes, and Status moves to
`Done`, once the owner reports those results and the verifier records them.
