# 013 — Keep bookings in step with Zoom: webhooks for meetings changed or deleted in Zoom

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Planned <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

The owner's words (2026-09-26):

> so what we need is zoom to linked via api or anyither means and create/cancel meetings via the app without user has to login to zoom app. This application will be the interface for zoom. Research on how to do this and ask questions if you have to.

The owner's scope answer (2026-09-26, relayed): "sync from Zoom via webhooks (the app updates itself when a meeting is changed or deleted in Zoom; needs a public HTTPS address)". Brief 011 has the full answers and the split. The owner's answer to Q6 (2026-09-26): "Production domain" (D9).

**Reading.** The app is meant to be the only way meetings are managed. Still, someone with a Zoom login can change or delete a class in Zoom directly, and today the app never finds out (006 D15, R7). The booking then keeps holding the account (a false "busy"), and the requester's link silently stops working.

Zoom can call the app when a meeting changes. Each of the 11 Server-to-Server apps gets an event subscription for `meeting.deleted` and `meeting.updated`, pointing at the app's public HTTPS address, with its own secret token. The app:

1. proves each call really came from that account's Zoom app;
2. ignores repeats;
3. asks Zoom for the meeting's current state;
4. brings the booking into line:
   - a class deleted in Zoom is cancelled here, and its time freed;
   - a class moved in Zoom is moved here, if the account is free at the new time;
   - anything it can't copy safely is flagged for IT;
5. emails the requester as the app's own cancel and move do.

A `Check against Zoom` button and a nightly command do the same for any event that was missed.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**Place in the split** (brief 011, Scope): third, after 011 (cancel a class) and 012 (move a class), which it reuses. 014 then adds recordings to this endpoint.

**In scope**

- **Settings (`tmd-devops`):** a fourth, optional variable per credential set, `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`; the `.example` and README; check `zoom.W002`.
- **The endpoint:** `zoom:webhook` (one path per credential set). It verifies the signature and timestamp, answers Zoom's URL validation, and records each event for idempotency.
- **Model** (migration `0009`): `ZoomEvent` (the idempotency record) and `LinkRequest.zoom_attention` (what IT needs to look at).
- **`services.reconcile(link_request)`:** the one place that brings a booking into line with Zoom. It's used by the webhook, the `Check against Zoom` button and the `sync_zoom_bookings` command.
- **Screens:** the `Check against Zoom` button and the "needs a look" notice on the detail page; a `Needs a look` tag in the queue.
- **Emails:** requester emails reuse 011's cancellation email and 012's moved email. There's a new IT "needs a look" email.
- **006's criterion 39 and D13 ("no webhooks") are amended deliberately.**

**Out of scope**

- `recording.completed` (014). Until then it's answered 200 and ignored.
- Meetings the app didn't book (made before go-live or by hand). They're already seen live by 006's clash check, and events about them are ignored.
- Mirroring changes to topic, agenda or settings.
- Restoring a meeting deleted in Zoom (011 D9).
- A job queue or worker (005 D9). Processing is in the request, bounded as D4 describes.
- Pruning old `ZoomEvent` rows (a follow-up; a few rows a day).

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- These carry over from 005, 006, 011 and 012: the frozen now, ZL-0042 and ZL-0043, mocked Zoom and the network block, "booked", "started" and "remaining", and the pinned-copy rule.
- **Test secret:** the set `zoom-02` with `webhook_secret="test-webhook-secret"` in `ZOOM_S2S_SECRETS` through the `settings` fixture. **Signed POST:** a request whose `x-zm-request-timestamp` is the frozen now in epoch seconds, and whose `x-zm-signature` is `v0=` plus the hex HMAC-SHA256 of `v0:{timestamp}:{raw body}` under the test secret (https://developers.zoom.us/docs/api/webhooks/).

### Settings and checks (`tmd-devops` builds 1; backend builds 2)

1. **The webhook secret comes from env only.**
   - `read_zoom_credentials` also reads `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`, which is **optional**: a set is complete without it.
   - `ZoomCredentials` gains `webhook_secret: str = field(default="", repr=False)`.
   - It's inside `ZOOM_S2S_SECRETS`, so Django masks it (006 criterion 3; the test is extended).
   - `zoom-credentials.env.example` lists the fourth name per set, with an empty value and a comment.
   - 006's source scan still finds no `ZOOM_S2S_` env read outside `base.py`.
2. **`zoom.W002`** (tagged `database`, with the `zoom` provider only). For each active paid account whose set has no webhook secret, there's one warning:

   `{label}'s Zoom connection has no webhook secret, so changes made directly in Zoom to its meetings aren't seen here.`

   It's silent for `fake`/`manual`, and when the table is missing.

### The endpoint

3. **URL and method.** `zoom:webhook` (slug), at `zoom/webhooks/<slug:slug>/`.
   - It accepts **POST only** (GET → 405). It's `csrf_exempt` and `non_atomic_requests`, with no sign-in.
   - **No other view is CSRF-exempt:** a source scan finds `csrf_exempt` exactly once in `apps/`, and a test with `Client(enforce_csrf_checks=True)` gets 403 on `zoom:approve`, `zoom:cancel` and `zoom:start` without a token.
4. **What's refused before any work:**
   - a slug that isn't in `ZOOM_S2S_SECRETS`, or whose set has no webhook secret → **404** with the site's normal 404 page, and no log above `INFO`;
   - a `Content-Length` over 256 KB → **413**, without reading the body.
5. **Signature and replay window** (D2). The headers `x-zm-request-timestamp` (digits only) and `x-zm-signature` must both be present.
   - The signature must equal `"v0=" + hex(HMAC-SHA256(secret, "v0:{ts}:{raw body}"))`, compared with `hmac.compare_digest`.
   - The timestamp must be within **300 seconds** of now, in either direction.
   - Any failure → **401** with an empty body, and one `WARNING` log naming the slug and the reason word only (`missing`, `stale` or `bad signature`), never a header value or the body.
   - Tests:
     - valid;
     - each header missing;
     - a signature one character off;
     - a body with one byte changed after signing;
     - a timestamp 301 seconds old;
     - one 301 seconds ahead;
     - a body signed with **another set's** secret.
6. **URL validation** (`event` = `endpoint.url_validation`). It's verified by criterion 5 like every event. Then:
   - `payload.plainToken` must match `^[A-Za-z0-9_-]{1,256}$`, or the answer is **400** (D2: this stops the endpoint being used to sign attacker-chosen text such as `v0:…`);
   - otherwise the answer is **200** JSON, exactly `{"plainToken": p, "encryptedToken": hex(HMAC-SHA256(secret, p))}`.
   - It makes no database query and no HTTP call (a test counts both).
7. **The event is from this set's Zoom account.** For every other event, `payload.account_id` must equal the set's `account_id` (`compare_digest`). If not → **401**, and a `WARNING` with the slug and `wrong account`.
8. **Repeats are ignored** (D3). Each accepted event is keyed by `(slug, SHA-256 of the raw body)`, unique in `ZoomEvent`.
   - A second delivery of the same body gets **200**, with no Zoom call, no booking change and no email.
   - Two concurrent deliveries (thread test) lead to exactly one reconcile and one set of emails.
9. **Events that aren't handled** (anything but `meeting.deleted` and `meeting.updated`, including `recording.completed` until 014) → **200**, recorded with outcome `ignored`.
10. **Response codes and retries** (Zoom retries after 5, 20 and 60 minutes; research, webhooks doc):

    | What happened | Response | `ZoomEvent` row kept? |
    |---|---|---|
    | handled: changed, no change, ignored, or not our meeting | 200 | yes, with its outcome |
    | reconcile couldn't ask Zoom (any 006 error kind) | **503** | **no**, so Zoom's retry does the work |
    | any other exception | **500**, one `ERROR` log (reference and exception class) | **no** |

    The row is written in the **same transaction** as the booking changes, so an event is never marked done without its changes, and never changed twice.
11. **`ZoomEvent` holds no secrets.** Its fields are `slug`, `event`, `body_sha256`, `event_ts`, `received_at`, `outcome` (`changed`, `no_change`, `needs_a_look`, `ignored`, `not_ours`), and `link_request` (FK, null, `SET_NULL`). There's no body, no header, no URL and no token. The secret-name test (005 c46) passes.

### Bringing a booking into line: `services.reconcile()`

12. **Which booking.** For `meeting.deleted`/`meeting.updated`, `payload.object.id` is looked up among `approved` requests whose `meeting_id` matches **and** whose `host_account.credential_set` equals the URL's slug.
    - No match → outcome `not_ours`, 200, no Zoom call.
    - A match on another slug's account is never touched: `not_ours`, plus a `WARNING`.
13. **Ask Zoom first, then lock.** `reconcile()` calls `GET /meetings/{id}` with **no transaction open**. A `404` with code 3001 means "gone". Then, in one transaction, it locks the request, the account and the classes (011's order), and compares. A test asserts `connection.in_atomic_block` is false inside the mocked HTTP callback.

    **Why a fresh `GET` and not the payload:** it's always the current truth, so events that arrive out of order, or with a partial payload, can't mislead it (D4).
14. **The rules.** Only the booking's **remaining** classes (booked and not started) are ever changed. Held and cancelled classes aren't touched.

    | Zoom's state | What the app does |
    |---|---|
    | meeting gone (3001) | every remaining class is cancelled with `cancel_reason` `Cancelled directly in Zoom.` and `cancelled_by` empty; slots are freed; the status follows 011's `status_after_cancel` |
    | a weekly class's occurrence is deleted or missing | that class is cancelled the same way |
    | a class's start or duration differs (matched by `zoom_occurrence_id`, or the single meeting for a one-off) | it's **moved here** through 012's model operation, with `moved_by` empty, **if** no other booked class on the account overlaps the new time. Otherwise it's left as it is, and a needs-a-look sentence is added |
    | Zoom has an occurrence from now on that matches no class here (added in Zoom, or the series was rebuilt) | nothing is changed; a needs-a-look sentence is added |
    | only the topic, agenda or settings changed | nothing |

    There's a table test per row, and one for held classes staying untouched.
15. **Needs a look.** `LinkRequest.zoom_attention` (a `TextField`, blank) holds the pinned sentences, one per line:
    - `The class on {Mon 5 Oct 2026, 8:30 am} was moved in Zoom to {Tue 6 Oct 2026, 9:00 am to 12:00 pm}, but {label} already has {reference} {class_name} then, so it wasn't moved here.`
    - `Zoom has a class on {Tue 6 Oct 2026, 9:00 am to 12:00 pm} that isn't booked here.`

    Where it shows:
    - The detail page shows a warn notice, `Changed in Zoom: needs a look`, with the sentences and the next step: `Move or cancel the class here, or change it back in Zoom, then press Check against Zoom.`
    - The queue shows the tag `Needs a look` (icon plus word) on that row.
    - It's **cleared** by the next reconcile that finds nothing to flag.
16. **Emails** (after the commit; only when something changed):
    - classes cancelled → 011's cancellation email, with the reason `Cancelled directly in Zoom.`, one email per reconcile;
    - classes moved → 012's moved email, one per reconcile;
    - needs a look set or changed → one email to every IT recipient (005 D9), subject `Needs a look: {reference} was changed in Zoom`, with the sentences and the absolute `zoom:detail` URL.
    - **No change → no email.** The same sentences again → no second IT email.
17. **The app's own changes are no-ops** (D1). After 011's `cancel()` or 012's `move_class()`/`move_series()` commits, delivering the matching webhook gives outcome `no_change`, zero writes to bookings, and zero emails.
    - **Thread test:** the webhook arrives while `cancel()` holds the request lock, after its Zoom `DELETE`. The reconcile waits, then finds no change. There's one cancellation email in total.
18. **Check against Zoom.** `POST zoom:sync` (pk) needs `zoom.review_linkrequest` and is `non_atomic`. It runs `reconcile()` and redirects to the detail with one message:
    - `Checked with Zoom: nothing had changed.` (success)
    - `Checked with Zoom: {n} change(s) copied here. We emailed {email}.` (success)
    - `Checked with Zoom: some changes need a look.` (warning)
    - `We couldn't check with Zoom: {phrase}. {next step}` (error, with 006's temporary or lasting next step)

    The button shows on approved bookings with remaining classes, when the provider `checks_zoom`.
19. **Nightly backstop.** `manage.py sync_zoom_bookings` reconciles every approved booking with remaining classes on a connected account.
    - It prints one line per booking that changed or needs a look, then `Checked {n} bookings: {c} changed, {a} need a look, {f} couldn't be checked.`
    - It exits **1** if any couldn't be checked.
    - No line contains a secret, a link or a token.

### Security, rules, verification

20. **Nothing secret is logged or shown.** With `DEBUG` logging captured across a validation, a signed event, a bad signature and a reconcile, no record contains:
    - the webhook secret;
    - an `x-zm-signature` value;
    - the raw body;
    - a join link or `start_url`;
    - the access token.

    The view and the verifier function are `@sensitive_variables` / `@sensitive_post_parameters` for the secret, the signature and the body.
21. **Thin views.** Verification is one function (`webhooks.verify(request, slug) -> Credentials | Refusal`), the rules are in `reconcile()` and the model operations from 011 and 012, and the view only maps results to responses.
22. **Template rules, no-JS, layout and accessibility,** as in 011 criterion 35, for the notice, the tag and the button.
23. **No test reaches the network.** Webhook tests post signed bodies with Django's test `Client`, and Zoom's `GET` is mocked.
24. **Automated checks** as in 011 criterion 37. Settings change, so **`check --deploy` runs on the prod stack** as in 006 criterion 46, with a dummy set **including** a dummy webhook secret: only W021 may appear. The `check --database default` run shows `zoom.W002` for a dummy set without one.
25. **Prod walkthrough** (no real Zoom; the verifier signs with a dummy secret passed by `exec -e`, as 006's verifier did):
    - `GET` → 405;
    - an unsigned `POST` → 401;
    - a signed URL validation → the exact JSON;
    - a repeated signed event → 200 with one `ZoomEvent` row;
    - an unknown slug → 404;
    - a `Check against Zoom` press on a manual-mode booking isn't offered.

    Screenshots at 1440 and 400: the needs-a-look notice and the queue tag (dev, fake provider steered).
26. **The owner's live check** (after D6's setup on one account):
    1. Marketplace validates the endpoint.
    2. Deleting one class of a live weekly test booking **in Zoom** cancels it here within a minute and emails the requester.
    3. Changing a one-off's time in Zoom moves it here.
    4. Moving it in Zoom onto another app booking's time gives `Needs a look` and the IT email.
    5. Cancelling in the app sends exactly one email.
    6. Deleting the whole meeting in Zoom cancels the rest.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q6 on 2026-09-26 (there is no Q3 in briefs 011–014; see 011's note).

| Q | Question (short) | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| Q6 | What public HTTPS address will Zoom call? | The production domain behind the TLS proxy; only `/zoom/webhooks/…` exposed if the rest is internal | **"Production domain"** | D9 (and D6's steps 0a–0c) |

**Supplied by the owner at setup, not a design question:** the production domain's actual name, which goes into each of the 11 Marketplace apps (D6, step 2). The code never needs it: the path is reversed by name, and the host is whatever Zoom calls.

**Decisions (the planner's)**

- **D1: The app's own changes can't echo back.** 011 and 012 change Zoom **inside** the locked transaction. The webhook's reconcile locks the same request row, so it waits for the commit and then finds the database already matching Zoom (criterion 17). No "expected change" table is needed.
- **D2: Webhook security.**
  - **One path per credential set** (`/zoom/webhooks/zoom-01/`). The slug picks the secret to check against. Slugs aren't secrets. Trying every secret against every call would be slower and would blur which account spoke.
  - **Signature:** Zoom's `v0` HMAC-SHA256 over the timestamp and the **raw** body (read before any parsing), compared in constant time.
  - **Replay window:** 300 seconds, so a captured request can't be replayed later. Duplicate deliveries inside the window are caught by D3.
  - **Account check:** the payload's `account_id` must be the set's own. This is defence in depth if one secret ever leaks: it can't forge events for another account's bookings, and criterion 12 limits each slug to its own accounts.
  - **URL validation isn't an HMAC oracle.** The validation reply returns `HMAC(secret, plainToken)`. If an unsigned validation were answered for any `plainToken`, an attacker could ask for `plainToken = "v0:{ts}:{body}"` and get a valid signature for a forged event. So validation is verified like everything else, **and** `plainToken` is limited to URL-safe characters, which can never contain `:` (criterion 6).
  - **CSRF-exempt only here** (criterion 3). The signature replaces CSRF: a browser can't produce it.
  - **Size cap** at 256 KB; the largest events are a few KB.
- **D3: Idempotency by `(slug, body hash)`**, stored in the **same transaction** as the changes (criterion 10).
  - Zoom's retries resend the same body, so the hash matches. The unique index makes two concurrent deliveries serialise: the second's insert waits, then fails as a duplicate, and gets a 200 no-op.
  - Only the hash is kept, never the body. Payloads carry join links and, for recordings, download tokens.
- **D4: Reconcile from a fresh `GET`, not from the payload.** One function, three triggers (webhook, button, nightly command).
  - Order and partial payloads don't matter.
  - A missed event is fixed by the next trigger.
  - The rules are tested once.

  **The 3-second budget:** Zoom expects a quick reply (research). The `GET` is usually well under a second, and emails go after the commit. If Zoom times out anyway and retries, D3 makes the retry a no-op, so a slow reply costs nothing. With no job queue (005 D9), this is the least code that's still correct.
- **D5: What a deletion in Zoom does: the class is cancelled here, and the requester is emailed.**
  - The owner asked for the app to "update itself". The requester's link is dead either way, so they need to know.
  - IT is not emailed about plain deletions (they made them), only about what the app couldn't copy (needs a look).
  - A mistaken deletion is recovered in Zoom within 7 days, then with a new request (011 D9).
- **D6: Owner setup** (for the README).

  **Once, for the server (owner, Q6: "Production domain"; D9):**

  - **0a.** Zoom calls the app's real production domain over `https://`, with a certificate from a public authority, through the existing TLS proxy. `USE_HTTPS=True`, and the proxy sends `X-Forwarded-Proto` (CLAUDE.md, "HTTPS in prod").
  - **0b. If the rest of the app is internal-only, expose only the webhook path.** At the proxy, allow requests from the internet to `/zoom/webhooks/` (and everything under it) and nothing else. Every other path stays internal. The signature (D2) is what protects this path. An IP allow-list of Zoom's addresses at the proxy is optional extra hardening, and the app never relies on one.
  - **0c. The proxy must pass the request through unchanged.** No body rewriting, re-encoding or compression changes to the request body, because the signature covers the exact bytes. It must also pass the `x-zm-signature` and `x-zm-request-timestamp` headers, and allow bodies up to 256 KB. The domain must be in `ALLOWED_HOSTS` (it already is for production).

  **Then, per paid account:**

  1. On marketplace.zoom.us, open the account's `Polymath TMD` app, then **Features → General Features → Event Subscriptions**, and switch it on. Name it `Polymath TMD sync`.
  2. **Event notification endpoint URL:** `https://{domain}/zoom/webhooks/{connection name}/`, where the connection name is the account's `Zoom connection name`, like `zoom-01`.
  3. **Events:** Meeting → **Meeting has been deleted** and **Meeting has been updated**. Nothing else until 014.
  4. Copy the **Secret Token** into `zoom-credentials.env` as `ZOOM_S2S_ZOOM_01_WEBHOOK_SECRET`, then recreate `web`.
  5. Press **Validate** in Marketplace. It passes only once the server has the secret. Then save.
  6. Run `manage.py check --database default`: no `zoom.W002` should remain.
  7. **Schedule** `docker compose exec -T web python manage.py sync_zoom_bookings` nightly (host cron or Task Scheduler).

  **No new API scope is needed.** Meeting events use the meeting read scope the app already has (https://developers.zoom.us/docs/api/meetings/events/). The backend confirms this against Marketplace at build time.

  **The research's point on accounts:** with 11 separate accounts there are 11 apps, 11 secrets, and events arriving from each account. That's why D2 gives one path and one secret per set.
- **D9: Zoom calls the production domain** (owner, Q6: "Production domain"; the planner's recommendation).
  - It's the app's real HTTPS domain, behind the TLS proxy. If the rest of the app is internal-only, only `/zoom/webhooks/…` is exposed (D6, steps 0a–0c).
  - Brief 014 uses the same endpoint and address.
  - Nothing in code depends on the domain.
- **D7: 006 is amended deliberately.** Criterion 39 (no webhook URL) and D13 ("No webhooks") are replaced by this brief. The docs writer adds dated notes.
- **D8: Information architecture.** No new page. Status is shown where IT already looks, and one verb is added:

  ```
  Link requests (zoom:queue)          ← "Needs a look" tag on affected rows
  └── ZL-0042 (zoom:detail)           ← "Changed in Zoom: needs a look" notice; [Check against Zoom] → POST zoom:sync
  [no screen] zoom:webhook (slug)     ← Zoom only
  ```

**Risk register**

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | Forged or replayed events change bookings | Low / **High** | Avoid: signatures, the 300-second window, the account check, one slug per secret, validation not an oracle, idempotency (criteria 4–8) | 401 warnings in the log | backend, reviewer |
| R2 | A missed event (the server is down beyond Zoom's 3 retries) leaves drift | Medium / Medium | Mitigate: the nightly command and the button (criteria 18 and 19) | the command's summary | owner (cron) |
| R3 | Out-of-order events, or an app change and its echo, cause flapping emails | Low / Low | Avoid: a fresh `GET` and the lock ordering (D1, D4) | duplicate emails reported | backend |
| R4 | Zoom retries while a slow reconcile is still running | Low / Low | Mitigate: the unique hash in the same transaction (D3) | `ZoomEvent` shows a retry | backend |
| R5 | A move in Zoom onto another booking's time | Low / Medium | Mitigate: not copied; needs a look plus an IT email (criteria 14–16) | the IT email | IT desk |
| R6 | The proxy isn't opened for the webhook path, or it alters the body and breaks signatures | Medium / **High** for 013–014 | Mitigate: D6 steps 0a–0c; the owner's live check step 1 | Marketplace validation fails | owner, devops |
| R7 | A leaked webhook secret | Low / Medium | Mitigate: the account check and per-slug scope limit the damage; rotate in Marketplace (**Regenerate** the token) plus the env file | unexpected 200s from unknown IPs | owner |

## MVT plan
<!-- owner: tmd-planner -->

### Models

Migration `0009_zoom_sync`, numbered after 012's `0008`.

- **`ZoomEvent`**: `slug` (`SlugField` 40), `event` (`CharField` 60), `body_sha256` (`CharField` 64), `event_ts` (`BigIntegerField`, null), `received_at` (auto), `outcome` (choices, criterion 11), `link_request` (FK, null, `SET_NULL`, `related_name="+"`).
  - Constraint: `UniqueConstraint(slug, body_sha256)`.
  - Docstring: why only a hash is kept.
- **`LinkRequest.zoom_attention`** (`TextField`, blank), plus a property `zoom_attention_lines` (a list of str).
- **No other model change.** Cancelling and moving reuse 011's and 012's model operations, with `by=None`.

### Placement of the code

- **`apps/zoom/webhooks.py` (new):** `verify()`, `url_validation_reply()`, `MAX_AGE_SECONDS = 300`, `MAX_BODY_BYTES = 256 * 1024`. Pure functions over bytes and headers, so they're easy to unit-test. `hmac` and `hashlib` come from the standard library.
- **`services.py`:** `reconcile(link_request, *, provider=None) -> ReconcileResult(outcome, cancelled, moved, attention)`, and `send_attention_email(...)`. It reuses `cancel`'s and `_move`'s locked-write helpers from 011 and 012, factored so reconcile calls them **without** making a second Zoom call (Zoom already changed).
- **`providers.py`:** `meeting_state(*, host_account, meeting_id) -> MeetingState | None` (`None` = gone). `MeetingState` holds only the times, occurrence IDs and statuses: no link, no `start_url`.
- **`checks.py`:** `zoom.W002`.
- **`management/commands/sync_zoom_bookings.py`.**
- **Settings (`tmd-devops`):** `base.py`'s `read_zoom_credentials` gains the optional part, and `zoom-credentials.env.example` too. There's no compose change, since the `env_file` already carries it.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| **`zoom:webhook`** | `zoom/webhooks/<slug:slug>/` | `ZoomWebhookView(View)`: POST only, `csrf_exempt`, `non_atomic_requests`. It calls `webhooks.verify`, then either the validation reply or `services.handle_event(credentials, event)`, and maps the result to 200/401/404/413/503/500 | none (JSON or empty) | Zoom's signature |
| **`zoom:sync`** | `zoom/requests/<int:pk>/sync/` | `SyncBookingView(ReviewerRequiredMixin, SingleObjectMixin, View)`, POST only, `non_atomic` | none (302) | `zoom.review_linkrequest` |
| `zoom:detail`, `zoom:queue` (changed context) | as today | as today | as today | as today |

### Context contract

**`zoom/detail.html`** adds:
- `zoom_attention_lines` (list of str, may be empty);
- `can_sync` (bool: approved, remaining classes, `checks_zoom`, and the user holds the review permission).

**`zoom/queue.html`:** each row's `link_request.zoom_attention` is truthy for the `Needs a look` tag. There's no new query: it's a column on the row.

**Emails:** `attention_subject.txt` / `attention_body.txt`: `link_request`, `lines` (list of str), `detail_url` (str). Requester emails reuse 011's and 012's templates and contexts.

### Placement and reuse

- **`apps/zoom` only.**
- **Reused:**
  - 011's `cancel` rules and `status_after_cancel`, and 012's move rules and slot rewrite;
  - 006's error kinds, `zoom_api`, and the credential-set plumbing;
  - 005's lock order, the IT recipients and `_send`;
  - the `messages` framework;
  - `hmac` and `hashlib` from the standard library.
- **No new dependency.** Zoom's SDKs aren't needed to check an HMAC.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Done (2026-09-26):** the owner answered Q6 (D9). **Start only after 011 and 012 are Done.** Before the owner's live check, the owner (or `tmd-devops`, if the proxy is in this repo's hands) sets up D6's steps 0a–0c.
1. **`tmd-ui-designer`:** the needs-a-look notice, the queue tag, the `Check against Zoom` button and its messages, and the IT email.
2. **`tmd-devops`, alone first:** criterion 1 (the optional fourth variable, the `.example`, and the settings tests). It runs `pytest --create-db`.
3. **In parallel, after step 2:**
   - **3a. `tmd-django-backend`:** `webhooks.py`, the endpoint, `reconcile()`, the model and migration `0009`, `zoom.W002`, the command, and the tests for criteria 2–23. It confirms D6's scope note and records it. It signals when its `pytest --create-db` is finished.
   - **3b. `tmd-frontend`:** the detail notice and button, the queue tag, the email layout. It runs `pytest` after the signal.
4. **`tmd-test-verifier`:** criteria 1–25, including both `check --deploy` runs and the signed-request walkthrough. Then the owner's live check (criterion 26) through the main session, once the production domain's webhook path is reachable (D6, steps 0a–0c).
5. **`tmd-code-reviewer`:** security first (every item of D2, raw-body handling, no secret in logs), then no HTTP under locks, then idempotency in the same transaction, then the echo-free design (D1).
6. **`tmd-docs-writer`:**
   - **README:** "Keeping in step with Zoom", with D6's steps (including the proxy steps 0a–0c), the nightly command, rotating a webhook secret, and 006 D15's limit marked resolved.
   - **CLAUDE.md:** the `zoom` bullet (the webhook endpoint, `reconcile()` as the one sync path, and the one `csrf_exempt` view) and the env gotcha for the fourth variable.
   - **`docs/CHANGELOG.md`**, the 006 amendment notes (D7), and closes the brief.
