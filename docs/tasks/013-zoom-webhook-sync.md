# 013 — Keep bookings in step with Zoom: webhooks for meetings changed or deleted in Zoom

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Verifying <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

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

**It's a go-live gate item** (owner, 2026-09-26: "we go live after all build"; brief 012, D12). Production takes no real requests until 006, 011, 012, 013 and 014 are all done, each with its owner live check. So the webhook path and the production domain (D6, steps 0a–0c) must work before go-live, not after.

**In scope**

- **Settings (`tmd-devops`):** a fourth, optional variable per credential set, `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`; the `.example` and README; check `zoom.W002`.
  *Amended by 015 (2026-11-02):* the webhook secret is no longer a fourth env variable. It is a field on the connection (015 criterion 1).
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
  *Amended by 015 (2026-11-02):* the "test secret" is set on a test `ZoomConnection` (`set_webhook_secret`), not in `ZOOM_S2S_SECRETS` (015).

### Settings and checks (`tmd-devops` builds 1; backend builds 2)

1. **The webhook secret comes from env only.**
   *Amended by 015 (2026-11-02):* **superseded.** The webhook secret is an encrypted field on `ZoomConnection`, set on the connection page (015 criterion 1, D3).
   - `read_zoom_credentials` also reads `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`, which is **optional**: a set is complete without it.
   - `ZoomCredentials` gains `webhook_secret: str = field(default="", repr=False)`.
   - It's inside `ZOOM_S2S_SECRETS`, so Django masks it (006 criterion 3; the test is extended).
   - `zoom-credentials.env.example` lists the fourth name per set, with an empty value and a comment.
   - 006's source scan still finds no `ZOOM_S2S_` env read outside `base.py`.
2. **`zoom.W002`** (tagged `database`, with the `zoom` provider only). For each active paid account whose set has no webhook secret, there's one warning:
   *Amended by 015 (2026-11-02):* W002's hint is now "Add the webhook secret on the Zoom connection's page", with an unreadable form (015 criterion 33).

   `{label}'s Zoom connection has no webhook secret, so changes made directly in Zoom to its meetings aren't seen here.`

   It's silent for `fake`/`manual`, and when the table is missing.

### The endpoint

3. **URL and method.** `zoom:webhook` (slug), at `zoom/webhooks/<slug:slug>/`.
   - It accepts **POST only** (GET → 405). It's `csrf_exempt` and `non_atomic_requests`, with no sign-in.
   - **No other view is CSRF-exempt:** a source scan finds `csrf_exempt` exactly once in `apps/`, and a test with `Client(enforce_csrf_checks=True)` gets 403 on `zoom:approve`, `zoom:cancel` and `zoom:start` without a token.
4. **What's refused before any work:**
   *Amended by 015 (2026-11-02):* the unknown-name and no-secret lookup is now one query on `ZoomConnection`, and an unreadable secret is a 404 with one `WARNING` (015 criterion 27, D9).
   - a slug that isn't in `ZOOM_S2S_SECRETS`, or whose set has no webhook secret → **404** with the site's normal 404 page, and no record above `INFO` from the app's own loggers (`apps.zoom` and its children). Django's own `django.request` line (`Not Found: /zoom/webhooks/zoom-99/`) is expected and allowed (D14);
   - a `Content-Length` over 256 KB → **413**, without reading the body.
5. **Signature and replay window** (D2). The headers `x-zm-request-timestamp` (digits only) and `x-zm-signature` must both be present.
   - The signature must equal `"v0=" + hex(HMAC-SHA256(secret, "v0:{ts}:{raw body}"))`, compared with `hmac.compare_digest`.
   - The timestamp must be within **300 seconds** of now, in either direction.
   - Any failure → **401** with an empty body, and exactly one `WARNING` record **from the app's own loggers** (`apps.zoom` and its children), naming the slug and the reason word only (`missing`, `stale` or `bad signature`), never a header value or the body. Django's own `django.request` line for the 401 (`Unauthorized: /zoom/webhooks/zoom-02/`) is expected, allowed and not counted (D14).
   - **Tests assert on the app's loggers by name** (for example `caplog` filtered to records whose `name` starts with `apps.zoom`), not on every record. The criterion 20 check, that no record of any logger holds a secret, a signature or the body, still covers every logger, `django.request` included.
   - Tests:
     - valid;
     - each header missing;
     - a signature one character off;
     - a body with one byte changed after signing;
     - a timestamp 301 seconds old;
     - one 301 seconds ahead;
     - a body signed with **another set's** secret.
6. **URL validation** (`event` = `endpoint.url_validation`). It's verified by criterion 5 like every event. Then:
   *Amended by 015 (2026-11-02):* criterion 6's "no database query" becomes exactly one query, the connection lookup (015 criterion 27).
   - `payload.plainToken` must match `^[A-Za-z0-9_-]{1,256}$`, or the answer is **400** (D2: this stops the endpoint being used to sign attacker-chosen text such as `v0:…`);
   - otherwise the answer is **200** JSON, exactly `{"plainToken": p, "encryptedToken": hex(HMAC-SHA256(secret, p))}`.
   - It makes no database query and no HTTP call (a test counts both).
7. **The event is from this set's Zoom account.** For every other event, `payload.account_id` must equal the set's `account_id` (`compare_digest`). If not → **401**, and a `WARNING` with the slug and `wrong account`.
8. **Repeats are ignored** (D3). Each accepted event is keyed by `(slug, SHA-256 of the raw body)`, unique in `ZoomEvent`.
   - A second delivery of the same body gets **200**, with no Zoom call, no booking change and no email.
   - Two concurrent deliveries (thread test) lead to exactly one reconcile and one set of emails.
9. **Events that aren't handled** (anything but `meeting.deleted` and `meeting.updated`, including `recording.completed` until 014) → **200**, recorded with outcome `ignored`.
   - **With a provider that doesn't `checks_zoom`** (`manual`), a verified `meeting.deleted` or `meeting.updated` is also answered **200** and recorded `ignored`, with no Zoom call and no booking change (D13). The app can't ask Zoom for the current state there, and answering 503 would only make Zoom retry three times for nothing. A test posts a signed `meeting.deleted` under `manual` and asserts 200, one `ignored` row, zero HTTP calls and the booking unchanged.
10. **Response codes and retries** (Zoom retries after 5, 20 and 60 minutes; research, webhooks doc):

    | What happened | Response | `ZoomEvent` row kept? |
    |---|---|---|
    | handled: changed, no change, ignored, or not our meeting | 200 | yes, with its outcome |
    | reconcile couldn't ask Zoom (any 006 error kind, including criterion 14's "couldn't be checked") | **503** | **no**, so Zoom's retry does the work |
    | a lock race: a MySQL deadlock after its one retry, or a lock-wait timeout (G5's "the webhook has its own answer"; added 2026-11-02, D15) | **500**, one `ERROR` log (reference and exception class) | **no** |
    | a verified body that isn't a Zoom event (no `event` or no `payload` object), or criterion 6's bad validation token (added 2026-11-02, D15) | **400**, empty body (`UNREADABLE`) | **no** |
    | any other exception | **500**, one `ERROR` log (reference and exception class) | **no** |

    **Logging at the edges** (D14 applies; app loggers only): the 413 of criterion 4 writes one `WARNING` with the slug and `too large`; an unknown slug writes nothing above `INFO`. A test covers each new row, its status and its log.

    **The `payload` check runs before the account check** (review round 1, S2; D18). A signed body with an `event` but no `payload` object, or with a `payload` that isn't an object (a string, a list, `null`), is **400** (`UNREADABLE`). It is **not** a 401, and it writes no `wrong account` `WARNING`. Criterion 7's account check runs only once `payload` is an object. **Test:** each of the three bad shapes gets a 400, no `wrong account` record, and no `ZoomEvent` row.

    The row is written in the **same transaction** as the booking changes, so an event is never marked done without its changes, and never changed twice.
11. **`ZoomEvent` holds no secrets.** Its fields are `slug`, `event`, `body_sha256`, `event_ts`, `received_at`, `outcome` (`changed`, `no_change`, `needs_a_look`, `ignored`, `not_ours`), and `link_request` (FK, null, `SET_NULL`). There's no body, no header, no URL and no token. The secret-name test (005 c46) passes.

### Bringing a booking into line: `services.reconcile()`

12. **Which booking.** For `meeting.deleted`/`meeting.updated`, `payload.object.id` is looked up among `approved` **and `cancelled`** requests whose `meeting_id` matches **and** whose `host_account.credential_set` equals the URL's slug (amended 2026-11-02, D15).
   *Amended by 015 (2026-11-02):* matching is by connection: `host_account.zoom_connection_id` replaces `credential_set == slug` (015 criterion 28).
    - **Why cancelled ones too:** the echo of a whole booking cancelled in the app (011) arrives as `meeting.deleted` for a booking that is now `cancelled`. Criterion 17 needs that echo recorded as `no_change`, not `not_ours`.
    - **A matched `cancelled` booking is never sent to Zoom and never changed.** Its event is recorded `no_change`, with no `GET`, no write and no email. A test delivers the echo of an app-made whole cancel and asserts exactly that.
    - No match → outcome `not_ours`, 200, no Zoom call.
    - A match on another slug's account is never touched: `not_ours`, plus a `WARNING`.
13. **Ask Zoom first, then lock.** `reconcile()` calls `GET /meetings/{id}` with **no transaction open**. A `404` with code 3001 means "gone". Then, in one transaction, it locks the request, the account and the classes (011's order), and compares. A test asserts `connection.in_atomic_block` is false inside the mocked HTTP callback.

    **Why a fresh `GET` and not the payload:** it's always the current truth, so events that arrive out of order, or with a partial payload, can't mislead it (D4).
14. **The rules.** Only the booking's **remaining** classes (booked and not started) are ever changed. Held and cancelled classes aren't touched.

    | Zoom's state | What the app does |
    |---|---|
    | meeting gone (3001) | every remaining class is cancelled with `cancel_reason` `Cancelled directly in Zoom.` and `cancelled_by` empty; slots are freed; the status follows 011's `status_after_cancel` |
    | a weekly class's occurrence is listed by Zoom as **deleted** | that class is cancelled the same way |
    | a weekly class's occurrence is **missing** from Zoom altogether (amended 2026-11-02, D15) | cancelled the same way **only when** Zoom has no unmatched occurrence from now on. If Zoom does have one, the series was probably rebuilt in Zoom (new IDs at new times), so **nothing is cancelled**, and each of Zoom's unmatched occurrences gets the "isn't booked here" sentence (criterion 15). Classes with no stored occurrence ID are matched by their start |
    | a class's start or duration differs (matched by `zoom_occurrence_id`, or the single meeting for a one-off) | it's **moved here** through 012's model operation, with `moved_by` empty, **if** the new time passes 012's move rules **and** no other booked class on the account overlaps it. A clash leaves it as it is, with criterion 15's clash sentence. A time 012's rules refuse (off the 5-minute step, across midnight, already passed, or more than a year ahead) also leaves it as it is, with criterion 15's "can't be booked here" sentence (amended 2026-11-02, D15): copying it would break the slot grid |
    | Zoom has an occurrence from now on that matches no class here (added in Zoom, or the series was rebuilt) | nothing is changed; a needs-a-look sentence is added |
    | only the topic, agenda or settings changed | nothing |

    There's a table test per row, and one for held classes staying untouched. The "missing" row has two tests: missing with no unmatched occurrence (cancelled), and missing with unmatched occurrences, a rebuilt series (nothing cancelled, flagged).

    **Couldn't be checked** (amended 2026-11-02, D15): a meeting whose Zoom type is neither 2 (scheduled) nor 8 (weekly, fixed time), or an answer the code can't read, is `ZoomUnavailable`. That means "couldn't be checked", with 006's phrase `no answer from Zoom`: a 503 on the webhook (criterion 10), the error flash on the button (criterion 18), and a couldn't-be-checked line in the command (criterion 19). **Nothing is cancelled or moved** for a meeting the app couldn't read. A test covers a type-3 meeting and an unreadable answer.

    **When the last remaining class is cancelled** and `status_after_cancel` makes the booking `cancelled`, reconcile sets `LinkRequest.cancelled_at` (now) and leaves `cancelled_by` empty, as 011's `cancel()` sets both (G1, D10). 011's check constraint `zoom_linkrequest_cancelled_was_booked` still holds. A test checks both fields after a whole meeting is deleted in Zoom.
15. **Needs a look.** `LinkRequest.zoom_attention` (a `TextField`, blank) holds the pinned sentences, one per line:
    - `The class on {Mon 5 Oct 2026, 8:30 am} was moved in Zoom to {Tue 6 Oct 2026, 9:00 am to 12:00 pm}, but {label} already has {reference} {class_name} then, so it wasn't moved here.`
    - `Zoom has a class on {Tue 6 Oct 2026, 9:00 am to 12:00 pm} that isn't booked here.`
    - `The class on {old} was moved in Zoom to {new}, but that time can't be booked here, so it wasn't moved here.` (`ZOOM_MOVE_NOT_BOOKABLE`; pinned 2026-11-02, D15). `{old}` and `{new}` use the same formats as the clash sentence above. It covers a new time off the 5-minute step, across midnight, already passed, or more than a year ahead. A test renders it for each of the four.

    Where it shows:
    - The detail page shows a warn notice, `Changed in Zoom: needs a look`, with the sentences and the next step: `Move or cancel the class here, or change it back in Zoom, then press Check against Zoom.`
    - The queue shows the tag `Needs a look` (icon plus word) on that row.
    - It's **cleared** by the next reconcile **that actually asked Zoom** and found nothing to flag (amended 2026-11-02, D15).
      - **A check that didn't ask Zoom never clears it.** That covers a booking with nothing left to check, a provider that can't reach Zoom, and a lookup that failed.
      - The only other way a flag is cleared is criterion 28's, when no class remains.
      - A test shows a flag surviving a failed lookup and a `manual` provider.
16. **Emails** (after the commit; only when something changed):
    - classes cancelled → 011's cancellation email, with the reason `Cancelled directly in Zoom.`, one email per reconcile;
    - classes moved → 012's moved email, one per reconcile;
    - **The requester emails say the change was made in Zoom** (P6, D11; G2). Both templates gain `in_zoom` (bool, default false). Reconcile sends `in_zoom=True`; 011's `cancel()` and 012's moves leave it false, and their emails are **unchanged** (a test renders each both ways).
      - **Cancelled, `in_zoom`** (`cancelled_body.txt`). The opening sentence is replaced by:
        - classes still to come (`remaining` not empty): `{n} class{n|pluralize:"es"} of your Zoom booking {reference} for {class_name} {n|pluralize:"was,were"} cancelled directly in Zoom.`
        - nothing still to come: `Your Zoom booking {reference} for {class_name} was cancelled directly in Zoom.`

        After the `Reason:` line it adds `If you didn't expect this, reply to the IT desk.`. Everything else is 011's, including P3's `can_start` variant and the students line. Rendered for one class of ZL-0042: `1 class of your Zoom booking ZL-0042 for Grade 11 Physics was cancelled directly in Zoom.` (D.5.1).
      - **Moved, `in_zoom`** (`moved_body.txt`). The opening sentence is replaced by `The time of {n} class{n|pluralize:"es"} in your Zoom booking {reference} for {class_name} was changed directly in Zoom.`. Everything else is 012's (`Was:`/`Now:` pairs, the link sentence, the students line, and `If the new time doesn't work for you, reply to the IT desk.`). Rendered for ZL-0043: `The time of 1 class in your Zoom booking ZL-0043 for Staff briefing was changed directly in Zoom.` (D.5.2).
      - Neither `in_zoom` email says `The IT desk has` anywhere (a test asserts it): the app doesn't know who changed Zoom.
    - needs a look set or changed → one email to every IT recipient (005 D9), subject `Needs a look: {reference} was changed in Zoom`, with the sentences and the absolute `zoom:detail` URL.
    - **No change → no email.** The same sentences again → no second IT email.
17. **The app's own changes are no-ops** (D1). After 011's `cancel()` or 012's `move_class()`/`move_series()` commits, delivering the matching webhook gives outcome `no_change`, zero writes to bookings, and zero emails.
    - **Thread test:** the webhook arrives while `cancel()` holds the request lock, after its Zoom `DELETE`. The reconcile waits, then finds no change. There's one cancellation email in total.
18. **Check against Zoom.** `POST zoom:sync` (pk) needs `zoom.review_linkrequest` (anonymous → sign in, plain user → 403, `GET` → 405) and is `non_atomic`. It runs `reconcile()` and redirects (302) to the detail with **exactly one** message. The texts are pinned (amended 2026-10-30 by D11, the designer's P1–P5, and D10, G4–G6). `{n}` is the number of classes copied, `len(cancelled) + len(moved)`. `{email}` is `link_request.requester_email`. Whether the requester email went is `ReconcileResult.emailed` (G6).

    | Case | Level | Message (pinned) |
    |---|---|---|
    | nothing copied, nothing to look at | success | `Checked with Zoom: this booking matches Zoom.` (P5) |
    | copied, emailed | success | `Checked with Zoom: {n} change{n\|pluralize} copied here. We emailed {email}.` (P1) |
    | copied, the email failed | warning | `Checked with Zoom: {n} change{n\|pluralize} copied here, but the email to {email} didn't send. Tell them yourself.` (P2) |
    | copied, emailed, and needs a look | warning | `Checked with Zoom: {n} change{n\|pluralize} copied here, and some changes need a look. We emailed {email}.` (P3) |
    | copied, the email failed, and needs a look | warning | `Checked with Zoom: {n} change{n\|pluralize} copied here, and some changes need a look. The email to {email} didn't send, so tell them about the copied change{n\|pluralize} yourself.` (the designer's P10, accepted 2026-10-30; D11) |
    | nothing copied, needs a look | warning | `Checked with Zoom: some changes need a look.` |
    | Zoom couldn't be asked | error | `We couldn't check with Zoom: {phrase}. {next step}`, where the next step (P4) is `Try again in a few minutes.` for a temporary error, 011's `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.` for a lasting one, and `services.daily_reset_sentence()` **alone** for `ZoomDailyLimit`, checked before `lasting` (012 criterion 34). Rendered daily: `We couldn't check with Zoom: Zoom's daily limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.` |
    | a lock race (G5): a MySQL deadlock (1213) is retried once, as `approve()`, `cancel()` and the moves do; a second one, or a lock-wait timeout (1205) | error | 012's `MOVING_AT_THE_SAME_MOMENT`, reused (the same constant): `Someone else was changing this booking at the same moment. Nothing was changed. Try again.` |
    | **nothing to check** (G4; `can_sync` false: a stale page or a hand-made POST), with a provider that doesn't `checks_zoom` | error | `This system can't reach Zoom, so it can't check this booking.` |
    | nothing to check, no remaining classes (approved or cancelled) | error | `There are no classes left to check in this booking.` |

    - The provider is tested first, then the remaining classes. Neither G4 case makes a Zoom call.
    - **"Matches Zoom" only after Zoom was asked** (review round 1, N2; D18). If the booking has nothing left to check by the time `reconcile()` runs (the last class ended, or it was cancelled, after the view's check), `reconcile()` returns a distinct `NOT_ASKED` outcome, with no Zoom call. The view maps it to the G4 flash `There are no classes left to check in this booking.` (`NOTHING_LEFT_TO_CHECK`), never to `this booking matches Zoom.` A test makes the booking's last class end between the view's check and the call.
    - A request that was never approved (unverified, waiting or rejected) is a **404**.
    - No message offers `another free account`, `Waiting won't fix this`, `429`, `quota` or `API`.
    - **Tests:** one per row, each asserting the level and the exact text (`1 change` and `3 changes` for P1). The lock-race test forces 1213 twice.

    The button shows on approved bookings with remaining classes, when the provider `checks_zoom` (`can_sync`).
19. **Nightly backstop.** `manage.py sync_zoom_bookings` reconciles every approved booking with remaining classes on a connected account.
    - It prints one line per booking that changed, needs a look **or couldn't be checked** (P9, D11), in the forms of Design D.6. The couldn't-be-checked line is pinned: `{reference} ({label}): couldn't be checked: {reason sentence}`, for example `ZL-0042 (Zoom 02): couldn't be checked: Zoom is busy right now.`
    - Then the summary, with plurals (P9; amended 2026-10-30): `Checked {n} booking{n|pluralize}: {c} changed, {a} need{a|pluralize:"s,"} a look, {f} couldn't be checked.`. Rendered: `Checked 1 booking: 0 changed, 1 needs a look, 0 couldn't be checked.` and `Checked 12 bookings: 2 changed, 0 need a look, 1 couldn't be checked.`
    - **The backend's extra lines, pinned** (2026-11-02, D15; D.6 didn't cover these cases). Each follows D.6's `{reference} ({label}): …` form:
      - copied, with a flag that was already known (no new IT email): `{reference} ({label}): {counts}, and still needs a look. Emailed the requester.`;
      - the IT email failed: the line ends `The email to the IT desk didn't send.`;
      - a lock race: `{reference} ({label}): couldn't be checked: Someone else was changing this booking at the same moment.`. It counts towards `{f}`.
    - **Under `manual`:** the command checks nothing, prints only `This system can't reach Zoom, so no bookings were checked.` and exits **0**. That's a configuration, not a failure, and `zoom.W001` already reports it.
    - **Bookings on accounts with no working Zoom connection are skipped,** and aren't counted in `{n}`. `zoom.E004` reports those accounts.
    - It exits **1** if any couldn't be checked.
    - It also runs criterion 28's sweep, which prints nothing.
    - These lines are pinned as the backend wrote them. If any needs wording work, the designer proposes it through the main session.
    - **One booking's failure never stops the run** (review round 1, N3; D18). Each booking is checked inside its own `try`. An unexpected exception counts that booking as couldn't-be-checked, prints `{reference} ({label}): couldn't be checked: {exception class name}.` and logs one `ERROR` (reference and class name), and then the run goes on to the next booking.
    - **Tests for the lines that had none** (review round 1, S3):
      - **the lock race:** a booking whose reconcile returns `LOCK_RACE` prints the pinned lock-race line, counts once in `{f}`, and makes the command exit **1**;
      - **the IT email failing:** a booking newly flagged while the IT email backend raises prints a line ending `The email to the IT desk didn't send.`;
      - **N3:** a `RuntimeError` in one booking of three gives two checked bookings, one couldn't-be-checked line, `{f}` = 1 and exit 1.
    - No line contains a secret, a link, a token, a class name or an email address.
    - **Tests:** each pinned line and both rendered summaries, and the exit code.

### Security, rules, verification

20. **Nothing secret is logged or shown.** With `DEBUG` logging captured across a validation, a signed event, a bad signature and a reconcile, no record contains:
    - the webhook secret;
    - an `x-zm-signature` value;
    - the raw body;
    - a join link or `start_url`;
    - the access token.

    The view and the verifier function are `@sensitive_variables` / `@sensitive_post_parameters` for the secret, the signature and the body.
    - **The parsed event is masked too** (review round 1, N1; D18). `services.handle_event` is `@sensitive_variables("event")`, because the parsed body holds join links. An `ExceptionReporter` test on an error raised inside `handle_event` shows `event` masked.
    - `base.py`'s comment warning about `ADMINS` error emails names webhook bodies alongside the other secrets.
21. **Thin views.** Verification is one function (`webhooks.verify(request, slug) -> Credentials | Refusal`), the rules are in `reconcile()` and the model operations from 011 and 012, and the view only maps results to responses.
    - **One definition of "still on"** (review round 1, N4; D18): the classes still to come after a cancel are one model method beside `remaining_classes`. 011's cancellation email and reconcile both call it, and a source scan finds the rule written once.
22. **Template rules, no-JS, layout and accessibility,** as in 011 criterion 35, for the notice, the tag and the button.
23. **No test reaches the network.** Webhook tests post signed bodies with Django's test `Client`, and Zoom's `GET` is mocked.
24. **Automated checks** as in 011 criterion 37. Settings change, so **`check --deploy` runs on the prod stack** as in 006 criterion 46, with a dummy set **including** a dummy webhook secret: only W021 may appear. The `check --database default` run shows `zoom.W002` for a dummy set without one.
   *Amended by 015 (2026-11-02):* the dummy webhook secret is set on a connection, not passed as env (015).
25. **Prod walkthrough** (no real Zoom; the verifier signs with a dummy secret passed by `exec -e`, as 006's verifier did). **Over HTTP on port 8011**, not 8010, which another project now holds (main session, 2026-10-30). The port is passed as a run-time override only, `WEB_PORT=8011 ZOOM_PROVIDER=manual docker compose up -d --build`, never by editing `.env`. Every HTTP check, screenshot and `curl` in this brief uses 8011 until the owner decides otherwise.
   *Amended by 015 (2026-11-02):* the dummy secret is typed on the connection page, not passed as env (015).
    - `GET` → 405;
    - an unsigned `POST` → 401;
    - a signed URL validation → the exact JSON;
    - a repeated signed event → 200 with one `ZoomEvent` row;
    - an unknown slug → 404;
    - a `Check against Zoom` press on a manual-mode booking isn't offered.

    Also: the Zoom account change page shows criterion 29's "no webhook secret" notice for a connection without one (the dummy set without a secret), and nothing new under `manual`.

    Screenshots at 1440 and 400 (dev, fake provider steered, on 8011): the needs-a-look notice, the queue tag, a class row with each Zoom note (criterion 27), a booking cancelled in Zoom, and the account change page in criterion 29's three states.
26. **The owner's live check** (after D6's setup on one account):
   *Amended by 015 (2026-11-02):* the Secret Token is typed on the connection page (015).
    1. Marketplace validates the endpoint. **Also confirm no new API scope is needed** (amended 2026-11-02, D15). The only new Zoom call in this brief is `GET /meetings/{id}`, which 011's start link and `occurrence_id_for` already use under `meeting:read:meeting:admin`. Check that the app's Scopes page lists nothing new as required, and that the event subscription saves with the existing scopes. If Marketplace asks for a scope, record its name; the docs writer adds it to the README.
    2. Deleting one class of a live weekly test booking **in Zoom** cancels it here within a minute and emails the requester.
    3. Changing a one-off's time in Zoom moves it here.
    4. Moving it in Zoom onto another app booking's time gives `Needs a look` and the IT email.
    5. Cancelling in the app sends exactly one email.
    6. Deleting the whole meeting in Zoom cancels the rest.
    7. **Added 2026-10-30 (P7):** after steps 2–6, the account's change page shows `Last heard from Zoom on {when}`, with a time within the last few minutes.
    8. **Added 2026-10-30 (P6):** the requester emails from steps 2 and 3 say `… directly in Zoom` and never `The IT desk has`.

### Added with the Design (2026-10-30)

27. **Where a change came from is decided on the model** (G1, D10).
    - New properties, with no query:
      - `Occurrence.moved_in_zoom`: `moved_at` is set and `moved_by_id` is `None`;
      - `Occurrence.cancelled_in_zoom`: `cancelled_at` is set and `cancelled_by_id` is `None`;
      - `LinkRequest.cancelled_in_zoom`: the same, on the booking.

      They're true only for reconcile's changes, because user keys are `PROTECT` (nobody is deleted), so an empty `*_by` with its time set can only mean the app copied the change from Zoom.
    - **Pages use them, never a template test on `*_by`.** The texts are pinned (the designer's D.1.2 and D.1.5):
      - class row, moved in Zoom: `Moved directly in Zoom. Copied here on {when}.` (`when` = `moved_at`);
      - class row, cancelled in Zoom: `Cancelled directly in Zoom. Copied here on {when}.` (`when` = `cancelled_at`; the stored reason isn't printed after it, being the same words);
      - the detail page's line for a booking cancelled in Zoom (`notice--note`, `info`): `This booking was cancelled directly in Zoom. The change was copied here on {when}. It was approved by {decided_by} on {when}.`
      - The app-made forms are unchanged: `Moved by {name} on {when}.` (012), `Cancelled by {name} on {when}: {reason}` and `This booking was cancelled by {name} on {when}.` (011).
    - **Tests:** the three properties in all four combinations of time and person, and rendered pages for each Zoom form. **No rendered page contains `by None`** (a test asserts it on the detail page after reconcile cancels one class, moves one class, and cancels a whole booking).
28. **A needs-a-look flag never outlives the booking** (G3, D10).
    - `zoom_attention` is cleared (set to `""`) whenever a booking stops having remaining classes:
      - in the model operation that makes a booking `cancelled`, which **both** 011's `cancel()` and reconcile use, so it's cleared in the same transaction;
      - in `sync_zoom_bookings`, which runs one `UPDATE` clearing it on every **approved** booking with no remaining classes (all its classes have been held).
    - So no `Needs a look` tag or notice is ever left on a booking that nothing can clear (`can_sync` is false there, and the nightly run skips it).
    - Clearing it sends no email.
    - **Tests:**
      - a flagged booking cancelled in the app, and one whose last class is cancelled in Zoom, both end with an empty `zoom_attention`;
      - a flagged booking whose last class has ended is cleared by the command;
      - the command's sweep is one `UPDATE` (captured SQL);
      - a flagged booking that still has remaining classes keeps its flag.
29. **The Zoom account page shows whether changes made in Zoom are seen here** (P7, D11, D12).
   *Amended by 015 (2026-11-02):* `webhook_secret_set` is now the stored connection's `has_webhook_secret`, and the `False` notice's body changes (015 criterion 20). `webhook_secret_set_for` is removed.
    - **Context on `zoom/account_form.html`** (change page, from the **stored** connection name, as 006's `zoom_connection_state` is):
      - `webhook_secret_set`: `True` or `False` when the stored connection is `ready` **and** the provider `checks_zoom`; `None` otherwise (the add page, a connection that isn't `ready`, or `manual`). It reads `settings.ZOOM_S2S_SECRETS[slug].webhook_secret` through one model-level function beside `zoom_connection_state_for`. It's never the secret, only whether there is one.
      - `last_zoom_event_at`: an aware datetime or `None`. It's the newest `ZoomEvent.received_at` for the stored slug (D12: derived, not stored), read with one aggregate query, `ZoomEvent.objects.last_received_at(slug)`. It's `None` when `webhook_secret_set` isn't `True`, or when no event has been recorded.
    - **Texts (pinned, P7), inside the existing `Zoom connection` section:**
      - **`webhook_secret_set` true:** the `Set up` notice gains `Changes made directly in Zoom are copied here. Last heard from Zoom on {when}.` (`when` through `zoom/partials/when.html`), or, with no event yet, `Changes made directly in Zoom are copied here. Nothing heard from Zoom yet.`
      - **`webhook_secret_set` false:** a second notice, `notice--warn` with `alert-triangle`, titled `Changes made in Zoom aren't seen here`, with the body `The server has no webhook secret for {name}. Until it has one, a class changed or deleted directly in Zoom stays as it was here until its booking is checked against Zoom. Ask whoever looks after the server to add it. The README explains how.` (`{name}` is the stored connection name.)
      - **`None`:** nothing new is shown.
    - The accounts list is unchanged.
    - **Tests:**
      - all three states render their exact text;
      - a set shared by two accounts shows the same `last_zoom_event_at` on both;
      - the change page's query count rises by at most one;
      - no rendered page contains the test webhook secret.

### Added after review round 1 (2026-11-02)

30. **A stale Zoom answer never undoes a change the app just made** (review round 1, B1, the blocker; D16).
    - **Before its `GET`,** `reconcile()` reads the booking's **fingerprint**: its `status`, plus `(pk, starts_at, ends_at, cancelled_at)` for each of its classes, sorted by pk. It's one model method, `LinkRequest.sync_fingerprint()`.
    - **Under the locks** (criterion 13's order), it computes the fingerprint again from the locked rows, **before** comparing with Zoom or writing anything.
      - **Same:** it carries on as criteria 14–16 say.
      - **Different:** something committed between the `GET` and the lock (an app move, cancel or approval, or another reconcile). It rolls back, writes no `ZoomEvent` row, and **tries once more from the start**: a new fingerprint, a new `GET`, and the locks again.
      - **Different again:** it returns **`LOCK_RACE`**, having changed nothing. Then the button shows 012's `MOVING_AT_THE_SAME_MOMENT` (criterion 18's lock-race row), the webhook answers **500** and keeps no row, so Zoom retries (criterion 10), and the command prints its pinned lock-race line, counted in `{f}` (criterion 19).
    - This is separate from the one MySQL-deadlock retry (G5), and each happens at most once. A reconcile therefore makes at most two meeting `GET`s, plus criterion 31's user check.
    - **Thread tests** (`transaction=True`, committed data, as 012's race tests):
      - **a move lands between the `GET` and the lock:** the webhook's reconcile `GET`s the old time; then `services.move_class()` commits a new time for the same class (its `PATCH` mocked); then the reconcile takes the lock. Expect the fingerprint mismatch, one retry whose second `GET` returns the moved time, outcome `no_change`, the class still at the app's time with `moved_by` the IT user (not `None`), **no `in_zoom` requester email**, and no IT email. The move's own email is the only requester email;
      - **a cancel lands in the same gap:** the same shape with `services.cancel()` on one class. Expect no flag, no IT email, no `in_zoom` email, and the class cancelled by the IT user;
      - **two changes in a row:** a second app change also lands between the retry's `GET` and its lock. Expect `LOCK_RACE`, no booking change, no email, and (on the webhook) a 500 with no `ZoomEvent` row.
31. **"Gone" is double-checked with Zoom before anything is cancelled** (review round 1, S1; owner: "Double-check with Zoom"; D17).
    - When a meeting `GET` answers `404` with code 3001, from any trigger (webhook, button or command), reconcile **first confirms the account's host user exists on that connection**: one `GET /users/{host_account.email}` with the same credentials. This is 006's Check connection call, under `user:read:user:admin`, which the app already has, so no new scope is needed.
      - **The user is found:** the meeting really is gone, and criterion 14's "meeting gone" row applies.
      - **The user isn't found** (`404` code 1001, so most likely the wrong Zoom account or credentials): the booking is **couldn't be checked**, with `ZoomUserNotFound`.
      - **The user check itself fails** (any 006 error kind): the booking is **couldn't be checked**, with that error.
      - In both couldn't-be-checked cases **nothing is cancelled, nothing is flagged, nobody is emailed**, the webhook answers **503** with no `ZoomEvent` row, the button shows criterion 18's error row, and the command prints its couldn't-be-checked line.
    - **The reason shown to IT is 006's existing phrase**, so no new wording is needed. `ZoomUserNotFound` is lasting, so with P4's next step the button reads (pinned):

      `We couldn't check with Zoom: Zoom has no user with this account's sign-in email. Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.`

      That's the right step: Check connection (006 criterion 36) shows exactly which part of the connection is wrong. The command's line reads `{reference} ({label}): couldn't be checked: Zoom has no user with this account's sign-in email.`
    - The user check runs **only** on a 3001, so a normal reconcile makes no extra call.
    - **Tests:**
      - **a wrong-account 3001:** the meeting `GET` answers 3001 and the user `GET` answers 1001. Nothing is cancelled, there are no emails, the webhook gets a 503 with no row, the button shows the pinned text, and the command prints its line and exits 1;
      - **the user check failing:** the meeting `GET` answers 3001 and the user `GET` times out. The same, with `no answer from Zoom`;
      - **a real deletion:** the meeting `GET` answers 3001 and the user `GET` answers 200. Every remaining class is cancelled and the requester is emailed, as in criterion 14;
      - **the call count:** a reconcile whose meeting `GET` answers 200 makes no user `GET`.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q6 on 2026-09-26 (there is no Q3 in briefs 011–014; see 011's note).

| Q | Question (short) | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| Q6 | What public HTTPS address will Zoom call? | The production domain behind the TLS proxy; only `/zoom/webhooks/…` exposed if the rest is internal | **"Production domain"** | D9 (and D6's steps 0a–0c) |

**Supplied by the owner at setup, not a design question:** the production domain's actual name, which goes into each of the 11 Marketplace apps (D6, step 2). The code never needs it: the path is reversed by name, and the host is whatever Zoom calls.

**Decisions (the planner's)**

- **D1: The app's own changes can't echo back.** 011 and 012 change Zoom **inside** the locked transaction. The webhook's reconcile locks the same request row, so it waits for the commit and then finds the database already matching Zoom (criterion 17). No "expected change" table is needed.
  - *Amended 2026-11-02 (review round 1, B1; D16):* the lock ordering covers only an event that arrives **after** the app's change has started. Reconcile asks Zoom **before** it takes the lock (criterion 13, so no HTTP runs under a lock). So an app change can still commit **between** reconcile's `GET` and its lock, and reconcile would then compare a stale Zoom answer with the fresh database, copying the old time back as an "in Zoom" move. Criterion 30's fingerprint closes that gap: under the lock, reconcile checks that the booking is still the one it asked Zoom about, and asks again if not.
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
  *Amended by 015 (2026-11-02):* steps 4-5 are now: type the Secret Token in **Webhook secret** on the connection page and save. Validate passes at once, with no recreate (015).

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
- **D10: The designer's contract gaps G1–G8 go in as the designer recommends** (Design D.12; main session, 2026-10-30).
  - **G1:** the model decides where a change came from (`moved_in_zoom`, `cancelled_in_zoom`), so no template tests `*_by`. Reconcile sets `cancelled_at` on a booking it cancels (criteria 14 and 27).
  - **G2:** `in_zoom` on the two requester emails (criterion 16).
  - **G3:** clear `zoom_attention` when no classes remain, in the cancel operation and in a sweep in `sync_zoom_bookings` (criterion 28).
  - **G4:** two error flashes when there's nothing to check (criterion 18).
  - **G5:** a lock race reuses 012's `MOVING_AT_THE_SAME_MOMENT` (criterion 18).
  - **G6:** `ReconcileResult.emailed` (criterion 18).
  - **G7:** the designer amends `docs/design/class-rows.md` and `busy-button.md` before the frontend starts (agent plan, step 1b).
  - **G8:** the IT email's `link_request` fields are listed in the contract.
- **D11: Copy proposals P1–P7 and P9 are accepted; P8 is a follow-up** (Design D.10; main session, 2026-10-30, clarity and honesty fixes in line with 012's D.2.6).
  - **P1:** plurals instead of `(s)`.
  - **P2:** a warning when the email failed, since `We emailed` would be untrue.
  - **P3:** both facts in one flash.
  - **P4:** a next step that fits one booking on one account: 011's Check-connection step for lasting errors, and `daily_reset_sentence()` alone for the daily limit (012 criterion 34).
  - **P5:** `this booking matches Zoom`, which is true even right after IT changed Zoom back.
  - **P6:** requester emails that don't claim the IT desk made a change it may not have made.
  - **P7:** the account page's sync state (criterion 29).
  - **P9:** the command names each booking it couldn't check, and uses plurals.
  - **P10, accepted (main session, 2026-10-30):** criterion 18's "copied, the email failed, and needs a look" row uses the designer's P10, replacing the planner's interim text. It says what to tell the requester (only the copied changes, since the requester is never told about needs-a-look lines), which "Tell them yourself" left open.
  - **Which text wins:** the Design section still marks D.10 as "proposals" and shows some pre-decision wording, such as criterion 18's old flashes in D.7. Where it differs from the criteria, the criteria win. The designer can refresh their own section at any time.
- **D12: `last_zoom_event_at` is derived from `ZoomEvent`, not stored** (P7; main session asked the planner to decide).
  *Amended by 015 (2026-11-02):* the first bullet's "env-only, with no database row" is now a row on `ZoomConnection`. `last_zoom_event_at` is still derived from `ZoomEvent`, as decided (015).
  - **Where it could have lived:**
    - **the credential set:** it's env-only, with no database row (006 D2);
    - **a column on `HostAccount`:** it would need a write on every event, and would disagree across accounts sharing one set;
    - **`ZoomEvent`:** it already records every accepted event with `slug` and `received_at`. That makes it the one source, at one aggregate query on the change page.
  - **What "heard" means:** an event that passed criteria 4–7 and was recorded, including `ignored`, `not_ours` and the app's own echoes (criterion 17). That's why it works as a health check: every cancel and move made in the app echoes back within seconds.
  - Signed-out refusals (401), URL validations (no row, criterion 6) and 503/500 answers (row not kept, criterion 10) don't count.
  - **Consequence:** the `ZoomEvent` pruning follow-up must keep the newest row per slug.
- **D13: With `manual`, verified meeting events are recorded `ignored`** (planner's decision, 2026-10-30, **confirmed by the main session as a ruling, 2026-10-30**; criterion 9). `manual` can't ask Zoom for a meeting's state, so reconcile can't run. A 503 would only make Zoom retry three times for nothing. The account page doesn't claim changes are copied under `manual` (criterion 29's `None`). `manual` already warns that it can't see Zoom (`zoom.W001`).
- **D14: Log counts in this brief are the app's own records only** (main session ruling, 2026-10-30, after devops found the conflict; criteria 4 and 5).
  - Django's built-in `django.request` logger writes a `WARNING` for every 4xx (`Not Found: …`, `Unauthorized: …`). Counted, it would make criterion 4's "nothing above INFO" and criterion 5's "exactly one WARNING" impossible to meet.
  - Those lines carry only the method, the path and the slug, and slugs aren't secret (D2). So they're expected and allowed.
  - **`LOGGING` is not changed to silence them.** Muting a framework logger to make a count pass would be hidden magic, and it would also hide real 4xx noise from whoever reads the logs.
  - Counts apply to `apps.zoom` and its children, and tests assert on those loggers by name. Criterion 20's "nothing secret in any record" still covers every logger, Django's included.
- **D15: The backend's build-time decisions, accepted** (Implementation notes, "Decisions and additions to review"; main session, 2026-11-02).
  - **A rebuilt series isn't a cancellation** (criterion 14). A class missing from Zoom is cancelled only when Zoom has no unmatched future occurrence; otherwise it's flagged. Cancelling would email the teacher that every class was cancelled, after IT had only changed the series' time in Zoom.
  - **A time that can't be booked here isn't copied** (criteria 14 and 15). The new pinned sentence says so, because copying such a time would break the slot grid.
  - **Unreadable meetings count as "couldn't be checked"** (criterion 14). Nothing is cancelled for a meeting the app couldn't read; the event is retried, and the button and command say so.
  - **The webhook matches cancelled bookings too, and leaves them alone** (criterion 12). That lets the echo of an app-made whole cancel be `no_change`, as criterion 17 needs.
  - **The extra webhook answers and command lines are pinned as built** (criteria 10 and 19). Any wording change goes through the designer and the main session.
  - **A check that didn't ask Zoom never clears a flag** (criterion 15). Clearing a flag on a check that never looked would hide a real mismatch.
  - **No new scope, confirmed in the owner's live check** (criterion 26, step 1). The backend couldn't reach Marketplace, so this rests on the code alone until then.
  - **Noted, not changed:** the nightly command builds its email links from the first `ALLOWED_HOSTS` entry and `USE_HTTPS` (Follow-ups).
- **D16: Reconcile checks the booking didn't change under it** (review round 1, B1, the blocker; criterion 30).
  - Asking Zoom before taking the lock keeps HTTP out of locks (criterion 13), but it leaves a gap in which an app change can commit, and a stale answer would then be copied back over it as an "in Zoom" change, with a false email.
  - **The fix:** a fingerprint of the booking (its status, and each class's times and cancel time) is taken before the `GET` and compared under the lock. On a mismatch, it asks Zoom once more; on a second mismatch it returns `LOCK_RACE` and changes nothing.
  - **Why a fingerprint and not a lock across the `GET`:** holding a row lock through an HTTP call is what 006 D6 avoids for every path except the one write. Re-asking is cheap, and a race is rare.
  - **Why not compare only the classes reconcile would touch:** the status, a cancel or a move of any class can change what the rules decide (criterion 14's "unmatched occurrence" test reads every class).
- **D17: A "gone" answer is double-checked with Zoom** (review round 1, S1; owner, 2026-11-02: "Double-check with Zoom", the reviewer's option (b); criterion 31).
  - **The danger:** Zoom answers 3001 ("no such meeting") for a meeting that belongs to **another** Zoom account. A mistyped `Zoom connection name`, or swapped credentials, would make the nightly run cancel every remaining class on that account and email every requester. Nothing could undo that.
  - **The check:** before treating 3001 as "gone", reconcile confirms the host user exists on that connection. A missing user, or a failed check, makes the booking "couldn't be checked", which changes nothing and is retried.
  - **Why this and not option (a)** (refusing a connection-name change while classes are booked): it also catches a wrong credentials file on the server, which no form can see. It costs one call, only on a 3001.
  - **The reason uses 006's existing `ZoomUserNotFound` phrase**, and its next step points to Check connection, so no new copy is needed. If the designer wants different words, they propose them through the main session.
- **D18: Review round 1's other findings are accepted** (main session, 2026-11-02):
  - **S2:** criterion 10's 400 also covers a missing or non-object `payload`, checked before the account.
  - **S3:** criterion 19's untested lines get tests.
  - **N1:** `sensitive_variables("event")`, and the `ADMINS` comment names webhook bodies (criterion 20).
  - **N2:** a `NOT_ASKED` outcome, so the button never says "matches Zoom" without having asked (criterion 18).
  - **N3:** the command checks each booking in isolation (criterion 19).
  - **N4:** the "still on" rule (which classes count as still to come, for the cancellation email's `remaining` and reconcile) is **one model method**, beside `remaining_classes`, and both callers use it (criterion 21's one-definition rule).
  - **N5:** `EventResult.reference` is removed, since nothing reads it.
  - **N6:** `settings.USE_HTTPS` is read directly, not through `getattr(…)`.
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
| R9 | A wrong connection name or credentials file makes every meeting look "gone", and the nightly run cancels a whole account's bookings (review round 1, S1) | Low / **High** (irreversible, mass emails) | Avoid: a 3001 is double-checked against the host user before anything is cancelled (criterion 31, D17) | `couldn't be checked: Zoom has no user …` lines in the nightly output | backend, IT desk |
| R10 | A stale Zoom answer undoes an app change made a moment earlier (review round 1, B1) | Low / Medium (a false email, a wrong time) | Avoid: the fingerprint re-check under the lock (criterion 30, D16) | a `LOCK_RACE` in the logs | backend |
| R8 | Sync silently stops (a secret missing, the proxy closed) and nobody notices | Medium / Medium | Mitigate: the account page's "Last heard from Zoom" and "no webhook secret" notice (criterion 29), `zoom.W002`, and the nightly command's exit code | a stale "Last heard" time | IT desk, owner |

**Follow-ups** (recorded, not in this brief):

- **P8, a `Needs a look` tab with its count** in the queue, between `Waiting` and `Link sent` (Design D.10). It needs a count in `tab_counts()` and a `for_tab` filter. It isn't needed for go-live; the tag, the notice and the IT email cover it for now.
- **Pruning old `ZoomEvent` rows** (Scope) must keep the newest row per slug, because criterion 29's "Last heard" reads it (D12).
- **A site-URL setting** (owner: `tmd-devops`; added 2026-11-02, D15).
  - **Today:** the nightly command has no request, so `services.absolute_url()` builds email links (the requester's `request_url`, IT's `detail_url`) from the first concrete `ALLOWED_HOSTS` entry, with `USE_HTTPS` for the scheme. The webhook and the button use the request, as before.
  - **Candidate:** an explicit setting, such as a site URL read in `base.py`, would be clearer, and wouldn't depend on the order of `ALLOWED_HOSTS`.
  - **No change in this brief.** Until then, the README tells whoever sets up production to put the public domain first in `ALLOWED_HOSTS`.

## MVT plan
<!-- owner: tmd-planner -->

### Models

Migration `0009_zoom_sync`, numbered after 012's `0008`.

- **`ZoomEvent`**: `slug` (`SlugField` 40), `event` (`CharField` 60), `body_sha256` (`CharField` 64), `event_ts` (`BigIntegerField`, null), `received_at` (auto), `outcome` (choices, criterion 11), `link_request` (FK, null, `SET_NULL`, `related_name="+"`).
  - Constraint: `UniqueConstraint(slug, body_sha256)`.
  - Docstring: why only a hash is kept.
- **`LinkRequest.zoom_attention`** (`TextField`, blank), plus a property `zoom_attention_lines` (a list of str).
- **`ZoomEventQuerySet.last_received_at(slug)`** → aware datetime or `None`, one aggregate (D12).
- **Properties** (G1, criterion 27): `Occurrence.moved_in_zoom`, `Occurrence.cancelled_in_zoom`, `LinkRequest.cancelled_in_zoom`.
- **A function beside `zoom_connection_state_for`:** `webhook_secret_set_for(credential_set) -> bool`. It reads settings only.
- **The cancel model operation** shared by 011's `cancel()` and reconcile clears `zoom_attention` when the booking becomes `cancelled` (criterion 28).
- **No other model change.** Cancelling and moving reuse 011's and 012's model operations, with `by=None`.

### Placement of the code

- **`apps/zoom/webhooks.py` (new):** `verify()`, `url_validation_reply()`, `MAX_AGE_SECONDS = 300`, `MAX_BODY_BYTES = 256 * 1024`. Pure functions over bytes and headers, so they're easy to unit-test. `hmac` and `hashlib` come from the standard library.
- **`services.py`:** `reconcile(link_request, *, provider=None) -> ReconcileResult(outcome, cancelled, moved, attention, emailed)`, and `send_attention_email(...)`. `emailed` (G6) is true only when a requester email was due and sent. The deadlock retry follows `approve()`'s. The flash texts of criterion 18 live here, beside 012's. It reuses `cancel`'s and `_move`'s locked-write helpers from 011 and 012, factored so reconcile calls them **without** making a second Zoom call (Zoom already changed).
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
- `can_sync` (bool: approved, remaining classes, `checks_zoom`, and the user holds the review permission);
- **`link_request.cancelled_in_zoom`** (bool, G1): picks criterion 27's cancelled-in-Zoom line.

**`zoom/partials/class_rows.html`:** each occurrence also exposes **`moved_in_zoom`** and **`cancelled_in_zoom`** (bool, G1), which pick criterion 27's notes. They're model properties with no query and no new `with` values.

**`zoom/queue.html`:** each row's `link_request.zoom_attention` is truthy for the `Needs a look` tag. There's no new query: it's a column on the row.

**`zoom/account_form.html`** (change page) adds (P7, criterion 29):

| Variable | Type | Notes |
|---|---|---|
| `webhook_secret_set` | `True`, `False` or `None` | From the **stored** connection name. `None` on the add page, when the stored connection isn't `ready`, or when the provider doesn't `checks_zoom`. Never the secret |
| `last_zoom_event_at` | aware datetime or `None` | `ZoomEvent.objects.last_received_at(stored slug)` (D12). `None` unless `webhook_secret_set` is `True` and an event was recorded |

**Emails:**
- `attention_subject.txt` / `attention_body.txt`: `link_request`, `lines` (list of str), `detail_url` (str, absolute). **G8:** reads `link_request.reference`, `class_name`, `requester_name` and `host_account.label`.
- `cancelled_body.txt` and `moved_body.txt` (011, 012): unchanged contexts, plus **`in_zoom`** (bool, default `False`; **G2**). Reconcile passes `True` (criterion 16).

**Messages:** criterion 18's flashes arrive through `messages` on `zoom:detail`, at the levels in its table.

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
**Port for every HTTP check in this plan: 8011** (main session, 2026-10-30; 8010 now belongs to another project). Pass it as a run-time override, `WEB_PORT=8011 …`, on each `docker compose up`, and never edit `.env`. This holds until the owner decides otherwise.

1. **`tmd-ui-designer`:**
   - **1a. Done (2026-10-30):** the Design section is written (D.1–D.12). G1–G8 and P1–P9 are folded in as D10 and D11 (criteria 9, 14, 16, 18, 19, 25, 26 and the new 27–29). The contract is fixed.
   - **1b. Before the frontend starts (G7):** amend `docs/design/class-rows.md` ("What a row shows": the two Zoom notes after the Moved and Cancelled note rows; "States": "or the Zoom note"; the Origin line) and `docs/design/busy-button.md` ("Used by": `zoom/detail.html`, `Check against Zoom`, `Checking with Zoom…`), as D.12's G7 words them. It's documentation only; it can run alongside step 2, and must finish before 3b.
2. **`tmd-devops`, alone first:**
   - Criterion 1, which is env plumbing only (D6): the optional fourth variable per credential set, `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`, read in `base.py`'s `read_zoom_credentials` into `ZoomCredentials.webhook_secret`; the empty line per set in `zoom-credentials.env.example`; and the settings tests (masking, the source scan, a set complete without the secret).
   - **Checked, and none needed:** a `compose.yaml` change (the existing `env_file` already carries `zoom-credentials.env`, and Zoom credentials stay out of `web.environment`, per CLAUDE.md's exception), and a `.env.example` change (no new `.env` variable; P7 needs no setting).
   - It runs `pytest` for its own tests **without `--create-db`**, then `ruff` and `docker compose config --quiet` for both stacks. It finishes before step 3.
3. **In parallel, after steps 1b and 2:**
   - **3a. `tmd-django-backend`:**
     - `webhooks.py`, the endpoint, `reconcile()` with `ReconcileResult.emailed` and the deadlock retry;
     - the model and migration `0009`, with G1's properties, `last_received_at`, `webhook_secret_set_for`, and the clearing of `zoom_attention` in the cancel operation;
     - `zoom.W002`, and the command with P9's lines and the sweep;
     - `zoom:sync` with criterion 18's messages (including G4 and G5);
     - the `account_form.html` context (`webhook_secret_set`, `last_zoom_event_at`);
     - `in_zoom` passed to the requester emails;
     - D13's `manual` handling;
     - the tests for criteria 2–23 and 27–29.

     It confirms D6's scope note and records it. **Only the backend runs `pytest --create-db`.** It reports "backend pytest run finished".
   - **3b. `tmd-frontend`:** Design D.11's build list:
     - the detail notice, the cancelled-in-Zoom line and the `Check against Zoom` box;
     - `class_rows.html`'s Zoom notes;
     - the queue tag and the Cancelled tab's empty-state sentence;
     - the new IT email;
     - `in_zoom` in `cancelled_body.txt` and `moved_body.txt` (P6);
     - the account page's P7 notices.

     It never uses `--create-db`. It runs `pytest` (reusing the database) only after the main session passes on the backend's signal.
4. **`tmd-test-verifier`:** criteria 1–25 and 27–29, including both `check --deploy` runs and the signed-request walkthrough, **on port 8011** (criterion 25). It's the next agent to run `pytest --create-db`, after 3a and 3b. Then the owner's live check (criterion 26, now with steps 7 and 8) through the main session, once the production domain's webhook path is reachable (D6, steps 0a–0c).
5. **`tmd-code-reviewer`:** security first (every item of D2, raw-body handling, no secret in logs or on the account page), then no HTTP under locks, then idempotency in the same transaction, then the echo-free design (D1). Then honesty: no message or email claims who made a change in Zoom (P6, criterion 27), every criterion 18 flash is true in its case, and no flag can outlive its booking (criterion 28).
   - **Done (2026-11-02): round 1, CHANGES REQUESTED** (B1, S1–S3, N1–N6). The rulings are D16–D18, with D1's dated note, criteria 10, 18, 19, 20 and 21 amended, and new criteria 30 and 31.

**Fix cycle 1** (2026-11-02, after review round 1). **Backend only**, and it starts now. There's no devops, designer or frontend step: no setting changes, and every message reuses an existing pinned text or an existing notice or flash, so no template changes.

- **1.1. `tmd-django-backend`:**
  - **B1:** criterion 30: `LinkRequest.sync_fingerprint()`, the re-check under the locks, the one re-ask, `LOCK_RACE` and its three mappings, and the three thread tests;
  - **S1:** criterion 31: the host-user check on a 3001, couldn't-be-checked with `ZoomUserNotFound` or the check's own error, and the four tests;
  - **S2:** criterion 10: the `payload` object check before the account check, and its test;
  - **S3:** criterion 19: tests for the lock-race line and the IT-email-failed line;
  - **N1–N6** (D18): `@sensitive_variables("event")` and the `ADMINS` comment; the `NOT_ASKED` outcome; per-booking isolation in the command; one "still on" model method; removing `EventResult.reference`; `settings.USE_HTTPS`.

  **Only the backend runs `pytest --create-db`.** It reports "backend pytest run finished".
- **1.2. `tmd-test-verifier`:** criteria 1–25 and 27–31 again (criterion 26 stays with the owner), with the thread tests (criterion 30's three, plus criteria 8 and 17) run 3 extra times. Also the full checklist, including the `check --deploy` runs. HTTP checks are on **8011**. It's the next agent to run `pytest --create-db`, after 1.1.
- **1.3. `tmd-code-reviewer`, round 2:** criteria 30 and 31 first (the fingerprint taken before the `GET` and compared under the lock, before any write; at most one re-ask; nothing changed on `LOCK_RACE`; the user check only on 3001; nothing cancelled or emailed when the user isn't found or the check fails). Then S2, S3 and N1–N6.
- Then step 6 below.

6. **`tmd-docs-writer`:**
   - **README:** "Keeping in step with Zoom", with D6's steps (including the proxy steps 0a–0c), the nightly command, rotating a webhook secret, the account page's "Last heard from Zoom" line as the way to see sync is working (criterion 29), and 006 D15's limit marked resolved.
   - **Dated amendment notes:** 011 and 012's requester emails gain the `in_zoom` form (criterion 16), and 011's `cancel()` now clears `zoom_attention` (criterion 28).
   - **README, production setup:** put the public domain **first** in `ALLOWED_HOSTS`, because the nightly command's email links are built from it (D15; the site-URL follow-up).
   - **README, "Keeping in step with Zoom":** a `couldn't be checked: Zoom has no user with this account's sign-in email` line in the nightly output means the account's connection name or the server's credentials are wrong. Nothing is cancelled until that's fixed; press Check connection to find which (D17).
   - **CLAUDE.md:** the `zoom` bullet (the webhook endpoint, `reconcile()` as the one sync path, and the one `csrf_exempt` view) and the env gotcha for the fourth variable.
   - **`docs/CHANGELOG.md`**, the 006 amendment notes (D7), and closes the brief.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

Written 2026-10-30. This is built inside the approved f-desk direction, and reuses briefs 011 and 012's patterns: the detail page's boxes, `class-rows`, `busy-button`, `flash-messages` and `status-tabs` (`docs/design/`). The webhook endpoint has no UI.

- Every **pinned** string in the criteria is used exactly as written. Where this section's wording differs from a criterion, **the criterion wins**.
- Wording marked *design copy* is new in this section.
- Proposed changes to pinned text are in D.10.
- **Refreshed 2026-10-30 after the main session's rulings:**
  - **Accepted:** P1–P7, P9, and the gaps G1–G8. **P8** (a `Needs a look` queue tab) is recorded as a follow-up only, and isn't built here.
  - The sections below now show the accepted wording. D.10 and D.12 keep the original proposals as the record of why each change was made.
  - P7 is now written out as D.4.1, the Zoom account change page.
  - G7 is done: `docs/design/class-rows.md` and `docs/design/busy-button.md` are amended.
  - The planner has pinned them: the proposals as **D11** (criteria 16, 18, 19 and 29) and the gaps as **D10** (criteria 14, 27 and 28, and the contract). This section was then checked against criteria 1–29. **Where this section differs from the criteria, the criteria win.**
  - One new proposal, **P10** (D.10), reviews the one criterion-18 text the planner wrote itself.
- **The honesty rule from 012 (D.2.6) applies throughout:** never claim what the app doesn't know. Here, that means three things:
  - the app doesn't know **who** changed a class in Zoom, so nothing says "the IT desk" or names a person for those changes;
  - it doesn't know **when** Zoom was changed, only when the change was copied here (by the webhook within seconds, or by the nightly run or the button up to a day later), so the page says "copied here on {when}";
  - "Nothing had changed" is avoided where Zoom *had* changed and was changed back (D.10, P5).

**Summary of what changes**

| Kind | What |
|---|---|
| New component | **none.** The notice, the tag, the button and the box all exist |
| New partials | `zoom/partials/attention_tag.html` (the `Needs a look` tag, used in the queue and on the detail page; D.3.1), `zoom/partials/sync_form.html` (the one `Check against Zoom` form, used in one of two places; D.1.4) |
| Changed templates | `zoom/detail.html` (D.1), `zoom/partials/class_rows.html` (D.1.5), `zoom/queue.html` (D.3), `zoom/account_form.html` (D.4.1, P7), `zoom/email/cancelled_body.txt` and `moved_body.txt` (D.5.1 and D.5.2, P6) |
| New emails | `zoom/email/attention_subject.txt`, `attention_body.txt` (D.5.3) |
| Unchanged | the timetable pages, the start page, the move and cancel forms, the Zoom accounts **list** (D.4) |
| Icons | **none new.** `alert-triangle`, `slash`, `calendar` and `check-circle` are in the sprite |
| Tokens and CSS | **none new.** Every class used exists (`.notice--warn`, `.notice ul`, `.tag--warn`, `.tags`, `.box`, `.box__lead`, `.form-actions`, `.button--secondary`) |
| JS | **none new.** The busy button and flash Close blocks cover everything |
| Component notes | `class-rows.md` (the two Zoom notes) and `busy-button.md` (the `Check against Zoom` row) are amended (G7, accepted and done 2026-10-30) |

**Information architecture** (D8, unchanged): no new page and no new navigation. Status shows where IT already looks, and one verb is added.

```
Link requests (zoom:queue)          ← "Needs a look" tag in the Status cell of affected rows
└── ZL-0042 (zoom:detail)           ← "Changed in Zoom: needs a look" notice, at the top
                                      Classes: "Cancelled directly in Zoom" / "Moved directly in Zoom" notes
                                      [Check against Zoom] → POST zoom:sync → back here with a flash
Zoom accounts › Change Zoom 02      ← in "Zoom connection": whether changes made in Zoom are seen here,
  (zoom:account_edit)                 and when Zoom was last heard from (D.4.1, P7)
IT's inbox                          ← "Needs a look: ZL-0042 was changed in Zoom" (with the detail link)
Requester's inbox                   ← 011's cancellation email / 012's moved email
[no screen] zoom:webhook (slug)     ← Zoom only
```

### D.1 Request detail: `zoom/detail.html`

#### D.1.1 Page structure (approved booking)

This extends 012's D.1.1. New items are in bold.

1. the flashes (`base.html`, unchanged);
2. **`Changed in Zoom: needs a look`** (new, D.1.3), when `zoom_attention_lines` isn't empty. It carries the `Check against Zoom` button when `can_sync`;
3. the decided line (`notice--ok`, unchanged);
4. **Request**: the `Status` row gains the `Needs a look` tag after `Link sent` (D.3.1), when `link_request.zoom_attention`;
5. **Classes**: a class cancelled or moved in Zoom gets its own note (D.1.5);
6. **`Check against Zoom`** (new box, D.1.4), when `can_sync` **and** `zoom_attention_lines` is empty;
7. `Change the time of the remaining classes` (012, unchanged);
8. `Cancel this booking` (011, unchanged). It stays last.

**Why the notice goes first.** It's the one thing on the page that asks IT to act, so it comes before the records. `approve_error` already sets this precedent: a problem notice sits above the decided line.

**Why there's exactly one `Check against Zoom` button, in one of two places:**

- **When something needs a look,** the button sits inside the notice, straight under the pinned next step (`… then press Check against Zoom.`). IT reads the problem, fixes it in a class row below or in Zoom, and comes back to the top. After a move or cancel in the app, the redirect lands at the top anyway, so the button is right there.
- **Otherwise** it sits in its own small box after Classes, with a lead that says what it's for. It's an occasional tool there: "I just changed this in Zoom; copy it now."
- Two buttons with the same name on one page would make IT wonder whether they differ, and would give a screen reader's button list two identical entries. So the box isn't rendered while the notice is.
- **Why the box goes before the move and cancel boxes:** 012 orders the boxes from the smallest change to the largest. A check changes nothing that IT asks for: it only copies what Zoom already has. So it comes first.

**Cancelled booking:** the page is 011's, with D.1.2's line when it was cancelled in Zoom. There's no notice and no button (G3 makes sure of the notice).

**Waiting and rejected requests:** unchanged. `can_sync` is false and `zoom_attention_lines` is empty.

#### D.1.2 The cancelled line, when the booking was cancelled in Zoom

When the last remaining class is cancelled in Zoom, `status_after_cancel` makes the booking `cancelled`. Today's line would then print `This booking was cancelled by None on …` (`cancelled_by` is empty). So the line gets a second form, chosen by `link_request.cancelled_in_zoom` (G1):

| Case | Notice | Text |
|---|---|---|
| cancelled in the app (011) | `notice--note`, `info` | unchanged: `This booking was cancelled by {cancelled_by} on {when}. It was approved by {decided_by} on {when}.` |
| cancelled in Zoom | `notice--note`, `info` | *design copy*: `This booking was cancelled directly in Zoom. The change was copied here on {when}. It was approved by {decided_by} on {when}.` Both times use `zoom/partials/when.html` |

- **"Directly in Zoom"** matches the pinned reason, `Cancelled directly in Zoom.` That reason is the one fact the app stores about a Zoom-made change, so the page repeats it word for word.
- **"The change was copied here on {when}"**, not "cancelled on {when}": `cancelled_at` is when the app found out, which can be up to a day after Zoom was changed (the nightly run).
- It stays `note`, not `warn`: a finished booking needs nothing from IT. The requester was emailed (criterion 16).

#### D.1.3 The notice: `Changed in Zoom: needs a look`

It shows when `zoom_attention_lines` isn't empty (criterion 15). It goes straight after `{% block content %}`, before the `approve_error` block (the two never show together: one is for an approved booking, the other for a waiting one).

```html
<div class="notice notice--warn" id="zoom-attention">
  <svg class="icon icon--xl" aria-hidden="true" focusable="false"><use href="#i-alert-triangle"></use></svg>
  <div class="notice__body">
    <p class="notice__title">Changed in Zoom: needs a look</p>
    <ul class="break-anywhere">
      {% for line in zoom_attention_lines %}<li>{{ line }}</li>
      {% endfor %}
    </ul>
    {% if can_sync %}
    <p>Move or cancel the class here, or change it back in Zoom, then press Check against Zoom.</p>
    {% include "zoom/partials/sync_form.html" with link_request_pk=link_request.pk csrf_token=csrf_token only %}
    {% else %}
    <p>Move or cancel the class here, or change it back in Zoom.</p>
    {% endif %}
  </div>
</div>
```

| Part | Text | Source |
|---|---|---|
| Icon | `alert-triangle` | the warn family, as in every warn notice |
| Title | `Changed in Zoom: needs a look` | pinned (criterion 15) |
| List | one `li` per line, printed as given (auto-escaped: a line can hold another booking's class name) | pinned sentences (criterion 15), built by the backend |
| Next step, with the button | `Move or cancel the class here, or change it back in Zoom, then press Check against Zoom.` | pinned (criterion 15) |
| Next step, without it | `Move or cancel the class here, or change it back in Zoom.` | *design copy*. Only for the edge where `can_sync` is false but lines remain (the provider was switched to `manual`). The pinned sentence would point at a button that isn't there |

**Rendered** (Zoom 02; ZL-0042's Mon 5 Oct class was moved in Zoom onto ZL-0051's time, and Zoom also has an extra class):

> **△ Changed in Zoom: needs a look**
> - The class on Mon 5 Oct 2026, 8:30 am was moved in Zoom to Tue 6 Oct 2026, 9:00 am to 12:00 pm, but Zoom 02 already has ZL-0051 Grade 10 Chemistry then, so it wasn't moved here.
> - Zoom has a class on Thu 8 Oct 2026, 9:00 am to 12:00 pm that isn't booked here.
>
> Move or cancel the class here, or change it back in Zoom, then press Check against Zoom.
> **[ Check against Zoom ]**

- **Why `warn` and not `bad`:** nothing failed in the app, and the booking still works for every class the notice doesn't name. `bad` is kept for "we couldn't do what you asked".
- **Why a list even for one line:** one shape for every case, and the lines are separate facts. A screen reader announces "list, 1 item", which is accurate.
- **Not `role="alert"` and not focused on load.** It's lasting state, not the result of what IT just did. Announcing it on every page load would be noise. The flash after a check carries the announcement (D.1.7).
- **The `id="zoom-attention"`** lets the IT email's link and any future link point at it. It's presentation only, and no JS uses it.
- **Dates in the lines are plain text,** not `<time>`, because the backend builds the whole sentence (pinned). This is the one exception to D.8's "every date in `<time>`" rule, and it's accepted: the text is still the readable date.
- **How IT clears it:** fix the booking (move or cancel the class here, or change Zoom back, or delete the extra class in Zoom), then press `Check against Zoom`. The next reconcile that finds nothing to flag clears it (criterion 15), and the flash says so (D.1.7). The webhook or the nightly run clears it too, with no flash.

#### D.1.4 `Check against Zoom`: the form, and its box

**The form** is one partial, `zoom/partials/sync_form.html`, so its markup lives in one place whichever spot it renders in:

```html
<form method="post" action="{% url 'zoom:sync' link_request_pk %}" data-busy-form>
  {% csrf_token %}
  <div class="form-actions">
    <button class="button button--secondary" type="submit" data-busy-text="Checking with Zoom…">Check against Zoom</button>
    <p class="visually-hidden" role="status" data-busy-status></p>
  </div>
</form>
```

- **`with link_request_pk=… csrf_token=csrf_token only`.** A partial included with `only` doesn't see `csrf_token` unless it's passed in, and `{% csrf_token %}` then prints nothing, so every POST would get a 403. `partials/user_menu.html` already passes it the same way.
- **`button--secondary`, not primary:** the check is a safe, repeatable lookup. It never needs a confirm page, because it only copies what Zoom already says, and emails the requester only when a class really was cancelled or moved. It's also `secondary` inside the warn notice, so the notice's action looks like every other entry action on the page.
- **`data-busy-text="Checking with Zoom…"`** is the same phrase as `Check connection` on the account page: both make one Zoom lookup and reload. It's *design copy*; criterion 18 pins only the button's name.
- The `div.form-actions` wrapper stops the button stretching to the notice's width (`.notice__body` is a flex column). Below 600px, `.form-actions` buttons go full width, as they already do everywhere.

**The box**, when `can_sync` and `zoom_attention_lines` is empty:

```html
<section class="box" aria-labelledby="sync-title">
  <div class="box__head"><h2 class="box__title" id="sync-title">Check against Zoom</h2></div>
  <div class="box__body">
    <p class="box__lead">…lead…</p>
    {% include "zoom/partials/sync_form.html" with link_request_pk=link_request.pk csrf_token=csrf_token only %}
  </div>
</section>
```

**The lead** (*design copy*): `Changes made directly in Zoom are usually copied here by themselves. If you've just changed this booking in Zoom, press the button to copy the change now. If a class was cancelled or moved, the requester gets an email.`

- **"Usually"** is deliberate. The automatic copy needs the account's webhook secret on the server (W002), and the nightly run needs the owner's scheduled task (D6, step 7). The page can't know either, so it doesn't promise "within a minute" or "every night".
- The last sentence answers the question IT will have before pressing: "will this email the teacher?" It names the only two cases that do.
- The box title repeats the button's words, as `Cancel this booking` does. It's a heading, so the page still has one button with that name.

**Where it doesn't show** (`can_sync` false; criterion 18): a waiting, rejected or cancelled request; an approved booking with no remaining classes (all held, or one in progress with none after it); and the `manual` provider. No "can't check" notice replaces it: in each case there's nothing to check, or the page already says why (011's `cancel_blocked_message`, the manual-provider flashes).

#### D.1.5 The Classes box: classes changed in Zoom

The tags don't change. A class cancelled in Zoom shows `Cancelled` (`slash`), and a class moved in Zoom shows `Moved` (`calendar`), exactly as when IT does it. Only the **note** under the row says where the change came from. Today's notes would print `Moved by None on …` and `Cancelled by None on …: Cancelled directly in Zoom.`, so each gets a Zoom form, chosen by the model properties in G1:

| Note | When | Text |
|---|---|---|
| Moved, in the app | `moved_at` and not `moved_in_zoom` | unchanged (012): `Moved by {moved_by} on {when}.` |
| **Moved, in Zoom** | `moved_in_zoom` | *design copy*: `Moved directly in Zoom. Copied here on {when}.` (`when` = `moved_at`) |
| Cancelled, in the app | `cancelled_at` and not `cancelled_in_zoom` | unchanged (011): `Cancelled by {cancelled_by} on {when}: {reason}` |
| **Cancelled, in Zoom** | `cancelled_in_zoom` | *design copy*: `Cancelled directly in Zoom. Copied here on {when}.` (`when` = `cancelled_at`). The stored reason isn't printed after it, because it's the same words (`Cancelled directly in Zoom.`) |

- **Why the source goes in the note, not the tag.** A row keeps one status word (class-rows.md's rule): `Cancelled` and `Moved` describe the class's state, which is the same whoever changed it. Tags like `Cancelled in Zoom` would be wider, would wrap on phones, and would add two more tag variants for IT to learn. The note sits directly under the date, so the source is still seen at a glance.
- **Why "copied here on {when}"** and not the caller's suggested "Moved in Zoom on {when}": `moved_at` and `cancelled_at` record when the app copied the change. The nightly run can copy a change made yesterday, so "moved on {when}" could be a day out. "Copied here" is always true (the honesty rule).
- **The order stays** "moved note, then cancelled note", so history still reads in the order it happened. A class moved by IT and later cancelled in Zoom reads `Moved by Anjali on …` then `Cancelled directly in Zoom. Copied here on …`.
- **A moved-in-Zoom class keeps its actions.** If it's still remaining, it's in `movable_ids` and `cancellable_ids` as usual, so IT can move or cancel it again here.
- **A class Zoom moved onto a busy time** isn't moved here (criterion 14), so its row is unchanged. The notice at the top names it by its old date, which is the date its row still shows. IT can find it.

The amended partial header comment names `cancelled_in_zoom` and `moved_in_zoom` as read from each occurrence.

#### D.1.6 Wireframes

**Desktop (1440). ZL-0042, approved, needs a look. Wed 7 Oct was cancelled in Zoom (copied by the webhook); `zoom` provider.**

```
ZL-0042: Grade 11 Physics                                         Home › Zoom link requests › ZL-0042
┌ △ Changed in Zoom: needs a look ───────────────────────────────────────────────────────────────┐  notice--warn
│   • The class on Mon 12 Oct 2026, 8:30 am was moved in Zoom to Tue 13 Oct 2026, 9:00 am to     │  ul, pinned lines
│     12:00 pm, but Zoom 02 already has ZL-0051 Grade 10 Chemistry then, so it wasn't moved here.│
│   Move or cancel the class here, or change it back in Zoom, then press Check against Zoom.     │  pinned next step
│   [ Check against Zoom ]                                                                       │  button--secondary
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ ✓ This request was approved by Anjali on Mon 28 Sep 2026, 9:40 am. ────────────────────────────┐  notice--ok
┌ Request ───────────────────────────────────────────────────────────────────────────────────────┐
│ Status     [✓ Link sent] [△ Needs a look] [● Recording]        Name   Nimal Perera             │  tags wrap
│ …unchanged                                                                                     │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Classes (8) ───────────────────────────────────────────────────────────────────────────────────┐
│ 1. Mon 5 Oct 2026, 8:30 am to 11:30 am                                                         │  held
│ 2. Wed 7 Oct 2026, 8:30 am to 11:30 am  [⊘ Cancelled]                                          │  muted date
│    Cancelled directly in Zoom. Copied here on Tue 6 Oct 2026, 4:12 pm.                         │  classrows__note
│ 3. Mon 12 Oct 2026, 8:30 am to 11:30 am                          Move this class  Cancel this class │  still its old time
│ 4. Wed 14 Oct 2026, 8:30 am to 11:30 am                          Move this class  Cancel this class │
│ …                                                                                              │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Change the time of the remaining classes ──────────────────────────────────────────────────────┐  012, unchanged
┌ Cancel this booking ───────────────────────────────────────────────────────────────────────────┐  011, unchanged
```

**Desktop (1440). A different case: Mon 12 Oct was moved in Zoom to a free time, so it was copied here and nothing needs a look.**

```
┌ Classes (8) ───────────────────────────────────────────────────────────────────────────────────┐
│ …                                                                                              │
│ 3. Tue 13 Oct 2026, 9:00 am to 12:00 pm  [▦ Moved]               Move this class  Cancel this class │
│    Moved directly in Zoom. Copied here on Tue 6 Oct 2026, 4:20 pm.                             │
│ …                                                                                              │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Check against Zoom ────────────────────────────────────────────────────────────────────────────┐  new box
│ Changes made directly in Zoom are usually copied here by themselves. If you've just changed    │  box__lead
│ this booking in Zoom, press the button to copy the change now. If a class was cancelled or     │
│ moved, the requester gets an email.                                                            │
│ [ Check against Zoom ]                                                                         │  button--secondary
└────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Change the time of the remaining classes ──────────────────────────────────────────────────────┐
┌ Cancel this booking ───────────────────────────────────────────────────────────────────────────┐
```

**Phone (400). Needs a look, after pressing the button while it still doesn't match:**

```
┌──────────────────────────────────────┐
│ ZL-0042: Grade 11 Physics            │
│ Home › Zoom link requests › ZL-0042  │
│ ┌ △ Checked with Zoom: some     (x) ┐│  flash, warn, role=status
│ │   changes need a look.           │ │
│ └──────────────────────────────────┘ │
│ ┌ △ Changed in Zoom: needs a look ─┐ │  notice--warn
│ │ • The class on Mon 12 Oct 2026,  │ │  the list wraps anywhere
│ │   8:30 am was moved in Zoom to   │ │
│ │   Tue 13 Oct 2026, 9:00 am to    │ │
│ │   12:00 pm, but Zoom 02 already  │ │
│ │   has ZL-0051 Grade 10 Chemistry │ │
│ │   then, so it wasn't moved here. │ │
│ │ Move or cancel the class here,   │ │
│ │ or change it back in Zoom, then  │ │
│ │ press Check against Zoom.        │ │
│ │ [     Check against Zoom       ] │ │  full width below 600px, 44px
│ └──────────────────────────────────┘ │
│ ┌ ✓ This request was approved by … ┐ │
│ ┌ Request ─────────────────────────┐ │
│ │ Status                           │ │  facts stack below 600px
│ │ [✓ Link sent] [△ Needs a look]   │ │
│ │ [● Recording]                    │ │  tags wrap
│ │ …                                │ │
│ ┌ Classes (8) ─────────────────────┐ │
│ │ 2. Wed 7 Oct 2026, 8:30 am to    │ │
│ │    11:30 am  [⊘ Cancelled]       │ │
│ │    Cancelled directly in Zoom.   │ │
│ │    Copied here on Tue 6 Oct      │ │
│ │    2026, 4:12 pm.                │ │
│ │ 3. Mon 12 Oct 2026, 8:30 am to   │ │
│ │    11:30 am                      │ │
│ │    Move this class               │ │
│ │    Cancel this class             │ │
│ └──────────────────────────────────┘ │
```

**Phone (400), cancelled in Zoom (top of the page):**

```
│ ┌ ⓘ This booking was cancelled     ┐ │  notice--note
│ │   directly in Zoom. The change   │ │
│ │   was copied here on Tue 6 Oct   │ │
│ │   2026, 4:12 pm. It was approved │ │
│ │   by Anjali on Mon 28 Sep 2026,  │ │
│ │   9:40 am.                       │ │
│ └──────────────────────────────────┘ │
│ ┌ Request ─────────────────────────┐ │
│ │ Status    [⊘ Cancelled]          │ │  no Needs a look tag (G3)
```

#### D.1.7 Outcomes of `Check against Zoom`

Every outcome arrives by redirect (302) to `zoom:detail` and shows in `partials/messages.html`, directly after the title row (`flash-messages.md`). After the redirect the page loads at the top: the flash, then the notice if one is still needed.

| Outcome (`ReconcileResult`) | Level → family | Icon | Role | Text |
|---|---|---|---|---|
| nothing to copy, nothing to flag (including when a notice was just cleared) | success → ok | `check-circle` | status | `Checked with Zoom: this booking matches Zoom.` (P5, accepted) |
| classes cancelled or moved, email sent | success → ok | `check-circle` | status | `Checked with Zoom: {n} change{n\|pluralize} copied here. We emailed {email}.` (P1, accepted) |
| copied, but the requester email didn't send | warning → warn | `alert-triangle` | status | `Checked with Zoom: {n} change{n\|pluralize} copied here, but the email to {email} didn't send. Tell them yourself.` (P2, accepted; needs G6) |
| something needs a look, nothing copied | warning → warn | `alert-triangle` | status | `Checked with Zoom: some changes need a look.` (pinned, unchanged) |
| copied **and** something needs a look | warning → warn | `alert-triangle` | status | `Checked with Zoom: {n} change{n\|pluralize} copied here, and some changes need a look. We emailed {email}.` (P3, accepted) |
| copied, the email failed, **and** something needs a look | warning → warn | `alert-triangle` | status | `Checked with Zoom: {n} change{n\|pluralize} copied here, and some changes need a look. The email to {email} didn't send. Tell them yourself.` (criterion 18; the planner's, joining P2 and P3) |
| Zoom couldn't be asked | error → bad | `alert-octagon` | alert | `We couldn't check with Zoom: {phrase}. {next step}` (pinned). The next step (P4, accepted): `Try again in a few minutes.` for a temporary error; `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.` for a lasting one; `daily_reset_sentence()` alone for the daily limit, checked before `lasting` |
| a lock race: a second deadlock, or a lock-wait timeout (the first deadlock is retried once) | error → bad | `alert-octagon` | alert | `Someone else was changing this booking at the same moment. Nothing was changed. Try again.` (012's `MOVING_AT_THE_SAME_MOMENT`, reused; G5, accepted) |
| nothing to check, with a provider that doesn't check Zoom (`manual`) | error → bad | `alert-octagon` | alert | `This system can't reach Zoom, so it can't check this booking.` (G4, accepted). The provider is tested first |
| nothing to check, no remaining classes (a stale page: the booking was cancelled, or its last class started) | error → bad | `alert-octagon` | alert | `There are no classes left to check in this booking.` (G4, accepted) |

Neither "nothing to check" case calls Zoom. A request that was never approved (unverified, waiting or rejected) is a **404** (criterion 18).

**Rendered** (ZL-0042, Zoom 02, at Mon 28 Sep 2026, 10:00):

- `Checked with Zoom: 1 change copied here. We emailed nimal@polymath.edu.lk.`
- `Checked with Zoom: 2 changes copied here, and some changes need a look. We emailed nimal@polymath.edu.lk.`
- `We couldn't check with Zoom: Zoom is busy right now. Try again in a few minutes.`
- `We couldn't check with Zoom: Zoom didn't accept this account's connection details. Ask whoever manages the Zoom accounts to press Check connection for Zoom 02, then try again.`
- `We couldn't check with Zoom: Zoom's daily limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.`

- **Exactly one flash per press** (criterion 18). Every combination of "copied", "the email failed" and "needs a look" has its own row above, so no flash hides another fact.
- **No focus jump** after the redirect. The flash is the first content after the h1, and that's where a screen reader and a sighted user both start.
- **What `{email}` is:** the requester's address, as in 011's and 012's flashes. The IT email to the desk isn't mentioned in the flash: the person pressing is in the desk and gets it.

### D.2 States

| State | What the user sees |
|---|---|
| Default, nothing flagged | the detail page with the `Check against Zoom` box (D.1.4) when `can_sync` |
| Needs a look | the warn notice at the top with its lines, the next step and the button (D.1.3); the `Needs a look` tag in the Status row and in the queue |
| Changed in Zoom and copied | the `Cancelled` or `Moved` tag with the `… directly in Zoom. Copied here on {when}.` note (D.1.5). A whole booking cancelled in Zoom gets D.1.2's line |
| Loading | the busy button: `Checking with Zoom…`, `aria-disabled`, and the text in `data-busy-status`. A second press does nothing (`busy-button.md`). With no JS, the browser's own indicator. The server is safe anyway: reconcile locks the request row (criterion 17) |
| Validation error | none. The form has no fields |
| Success | 302 to the detail with a success flash (D.1.7). If the notice was cleared, it's gone from the page that loads |
| Warning | 302 with a warning flash: needs a look, or the email didn't send |
| Server error (Zoom) | 302 with the error flash `We couldn't check with Zoom: …` and one next step. Nothing was changed, and the page still shows what it showed |
| Server error (anything else) | the site's normal 500 page. The booking's transaction rolled back (`non_atomic` view, reconcile's own transaction), so nothing was half-saved |
| Empty | doesn't exist: the box and the button only show when there are remaining classes |
| Not offered | `can_sync` false (D.1.4): no box and no button. A POST anyway (a stale page): G4's error flash |
| No permission | anonymous: sign-in, then back to the detail. A signed-in user without `zoom.review_linkrequest`: the existing `403.html`. The detail page is already gated the same way, so they never see the button |
| Not found | 404 for a request that doesn't exist, or one that was never approved (criterion 18). `GET` on `zoom:sync` is 405 |

### D.3 Queue: `zoom/queue.html`

#### D.3.1 The `Needs a look` tag: `zoom/partials/attention_tag.html` (new)

```html
<span class="tag tag--warn"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-alert-triangle"></use></svg>Needs a look</span>
```

- Word: `Needs a look` (pinned, criterion 15). Icon: `alert-triangle`. Tone: `tag--warn`.
- **Why `alert-triangle` and not `clock`:** `Waiting` is already `tag--warn` with `clock`. The two never share a row in practice (only approved bookings can need a look), but if they did they'd still differ by icon and word. `alert-triangle` is the warn family's icon on every notice, so "something to check" reads the same everywhere.
- **Why a partial with no `with` values:** the queue row and the detail page's Status row show the same tag. The tone, icon and word are chosen in one file, as `status_tag.html` does for statuses. The **condition** stays with the caller (`{% if link_request.zoom_attention %}`), because it's the caller's row.
- Its header comment names its purpose (criterion 15) and says it takes no context.

#### D.3.2 Where it goes in the queue

In the **Status** cell, after the status tag. The cell's wrapper changes from `<span>` to `<span class="tags">`, the same wrapper the detail page's Status row uses, so two tags wrap instead of overflowing:

```django
<td role="cell"><span class="datagrid__label" aria-hidden="true">Status</span><span class="tags">{% include "zoom/partials/status_tag.html" with status=link_request.status label=link_request.get_status_display only %}{% if link_request.zoom_attention %}{% include "zoom/partials/attention_tag.html" only %}{% endif %}</span></td>
```

- It shows in every tab where the row appears: `Link sent` and `All` (only approved bookings get it; G3 keeps it off cancelled ones).
- **Below 768px** (the card layout) the `Status` label sits above both tags, and they wrap side by side.
- **No new tab.** D8 and criterion 15 chose a tag and an email, with no new query. A `Needs a look` tab with a count would let IT find these bookings without the email. It's offered as a follow-up in D.10, P8, because it needs a count query and a filter.
- **No column, no sort change.** A flagged booking keeps its place in its tab's order. The email gives IT the direct link, so IT doesn't have to hunt for the row.

```
Desktop (1440), Link sent tab:
│ Reference │ Class              │ Requested by   │ First class     │ Classes │ Status                       │
│ ZL-0042   │ Grade 11 Physics   │ Nimal Perera … │ Mon 5 Oct 2026  │ 8       │ [✓ Link sent] [△ Needs a look] │
│ ZL-0043   │ Staff briefing     │ …              │ …               │ 1       │ [✓ Link sent]                │

Phone (400), one card:
┌ ZL-0042 ─────────────────────────────┐
│ Class         Grade 11 Physics       │
│ …                                    │
│ Status        [✓ Link sent]          │
│               [△ Needs a look]       │  wraps when it doesn't fit
└──────────────────────────────────────┘
```

#### D.3.3 The Cancelled tab's empty state (copy only)

011's empty state says `Bookings show here when the IT desk cancels them.` That's no longer the whole truth: a booking cancelled in Zoom lands here too. *Design copy*: `Bookings show here when they're cancelled, here or directly in Zoom.` The heading `No cancelled bookings.` is unchanged.

### D.4 How the rest of the app reflects a change made in Zoom (no template changes)

| Where | What changes | Why no template work |
|---|---|---|
| **Timetable, month and day** | a class moved in Zoom shows at its new time, and its old slot is free. A class cancelled in Zoom is gone and its slot is free. A class Zoom has but the app doesn't ("isn't booked here") is **not** on the timetable | `booked()` reads the stored classes. An entry means "this account is taken by an app booking then". 006's clash check still sees the extra Zoom class live at approve time, and the move form's help already says `Meetings made directly in Zoom aren't on the timetable.` |
| **Start page** (`zoom:start`) | follows the stored times, so a class moved in Zoom opens at its new time, and one cancelled in Zoom shows the `cancelled` state | `start_state()` reads the stored times and `cancelled_at`. The public page shows no history (011 criterion 22). Its cancelled text, `The IT desk emailed the reason to the person who booked it.`, stays true: criterion 16 sends the same IT desk email, with `Reason: Cancelled directly in Zoom.` |
| **Move and cancel forms** | none. A class moved in Zoom can be moved or cancelled again here, like any other | |
| **Zoom accounts list** | none. Seven columns are already tight at 1024px, and the state belongs with the connection it describes, on the change page | |
| **Zoom account change page** | **changed** (P7, accepted): D.4.1 | |
| **The webhook endpoint** | no UI. Its answers are JSON or empty, for Zoom only | |

#### D.4.1 The Zoom account change page: `zoom/account_form.html`, the `Zoom connection` section (P7)

**Why it's here.** Until now, the only sign of a missing webhook secret was `zoom.W002` in `check --database`, which IT never runs. Without the secret, changes made in Zoom to that account's meetings are never copied here by themselves. This section shows IT, in words, whether changes made in Zoom are seen, and when Zoom last spoke to the app. "Last heard" doubles as a health check, because every cancel and move made in the app echoes back from Zoom as an event.

**Context** (criterion 29, pinned; it wins over anything below):

- `webhook_secret_set`: **three values.** `True` or `False` when the stored connection is `ready` **and** the provider `checks_zoom`; `None` otherwise (the add page, a connection that isn't `ready`, or `manual`). It's never the secret itself, only whether there is one.
- `last_zoom_event_at` (aware datetime or `None`): the newest `ZoomEvent.received_at` for the stored connection name (D12: derived, not stored). It's `None` when `webhook_secret_set` isn't `True`, or when no event has been recorded.
- The view decides every "should this show" case through `None`, so the template needs no `checks_zoom` and no connection-state test. My first draft's G9 (`checks_zoom` on this page) is **not needed**: criterion 29's `None` covers it.

**Where it shows.** Inside the `Zoom connection` fieldset, only when `webhook_secret_set` isn't `None`. In practice that's the change page, with a `ready` connection, under the `zoom` provider. When the connection is `missing` or `none`, the connection itself has to be fixed first, and its existing notice already says how. A webhook line there would stack a second problem on the first. Under `manual`, `zoom.W002` is silent too, and a warning nobody can act on would be noise.

**The template's three branches:** `{% if webhook_secret_set %}` (the paragraph in `Set up`), `{% elif webhook_secret_set is False %}` (the warn notice), and nothing for `None`. Django's `is` operator tells `False` apart from `None`, so a missing value never shows the warning.

**Order inside the fieldset:**

1. the existing `Set up` notice (`notice--ok`, `check-circle`), which gains a paragraph when the secret is set (below);
2. **new, when the secret isn't set:** the `Changes made in Zoom aren't seen here` notice (below);
3. the `Zoom connection name` field (unchanged);
4. the `Check connection` button and its help (unchanged).

**Secret set**: a second `p` inside the `Set up` notice's `.notice__body`, after its existing sentence:

```html
<p>Changes made directly in Zoom are copied here. {% if last_zoom_event_at %}Last heard from Zoom on {% include "zoom/partials/when.html" with at=last_zoom_event_at only %}.{% else %}Nothing heard from Zoom yet.{% endif %}</p>
```

It's a plain `p`, with no new class. My first draft added a second sentence, `Zoom tells this system each time one of this account's meetings is changed or deleted, including changes made here.`, to explain why "last heard" matters. Criterion 29 pins the texts without it, and its tests render each state's exact text, so **it isn't built.** If IT finds "last heard" unclear in the owner's live check, it can come back as a follow-up.

**Secret not set**: a separate notice straight after `Set up`:

```html
<div class="notice notice--warn">
  <svg class="icon icon--xl" aria-hidden="true" focusable="false"><use href="#i-alert-triangle"></use></svg>
  <div class="notice__body">
    <p class="notice__title">Changes made in Zoom aren't seen here</p>
    <p>The server has no webhook secret for <span class="break-anywhere">{{ zoom_connection_name }}</span>. Until it has one, a class changed or deleted directly in Zoom stays as it was here until its booking is checked against Zoom. Ask whoever looks after the server to add it. The README explains how.</p>
  </div>
</div>
```

| Part | Text (pinned, criterion 29) |
|---|---|
| Secret set, heard | `Changes made directly in Zoom are copied here. Last heard from Zoom on {when}.` |
| Secret set, not yet | `Changes made directly in Zoom are copied here. Nothing heard from Zoom yet.` |
| No secret, title | `Changes made in Zoom aren't seen here` |
| No secret, body | `The server has no webhook secret for {name}. Until it has one, a class changed or deleted directly in Zoom stays as it was here until its booking is checked against Zoom. Ask whoever looks after the server to add it. The README explains how.` |

- **Why the "set" state goes inside `Set up` and isn't its own notice:** it's good news about the same connection. A second green notice would double the noise for the normal case. The warning gets its own notice because it's a separate problem with its own fix and its own reader (the server admin).
- **Why `warn`, not `bad`:** bookings still work. Only the automatic copy is missing, and the button and the nightly run still catch changes.
- **"Webhook secret"** appears only in the warning, because it's the words the server admin will look for in the README and in `zoom-credentials.env`. IT reads the title, which says what it means for them. This is the one screen exception to D.7's word list.
- **No "too long ago" judgement.** The page doesn't flag an old "last heard" time. An account with no changes for a week is normal, and the app can't tell that apart from a broken path. The time is shown, and IT judges it.
- **"Nothing heard from Zoom yet"** is normal right after setup. The first cancel or move made in the app on this account fills it in.
- `{when}` uses `zoom/partials/when.html`, so it's in `<time datetime>`.

**Wireframe, desktop (1440), secret set:**

```
┌ Zoom connection ───────────────────────────────────────────┐  formsection
│ ┌ ✓ Set up ────────────────────────────────────────────┐   │  notice--ok
│ │   The server has a Zoom connection called zoom-02.    │   │
│ │   Press Check connection to make sure Zoom accepts it.│   │
│ │   Changes made directly in Zoom are copied here. Last │   │  new p
│ │   heard from Zoom on Mon 28 Sep 2026, 10:12 am.       │   │
│ └───────────────────────────────────────────────────────┘   │
│ Zoom connection name  …unchanged…                          │
│ [ Check connection ]  …unchanged help…                     │
└────────────────────────────────────────────────────────────┘
```

**Wireframe, phone (400), no secret:**

```
│ Zoom connection                      │
│ ┌ ✓ Set up ────────────────────────┐ │
│ │   The server has a Zoom          │ │
│ │   connection called zoom-02. …   │ │
│ └──────────────────────────────────┘ │
│ ┌ △ Changes made in Zoom aren't  ──┐ │  notice--warn
│ │   seen here                      │ │
│ │   The server has no webhook      │ │
│ │   secret for zoom-02. Until it   │ │
│ │   has one, a class changed or    │ │
│ │   deleted directly in Zoom stays │ │
│ │   as it was here until its       │ │
│ │   booking is checked against     │ │
│ │   Zoom. Ask whoever looks after  │ │
│ │   the server to add it. The      │ │
│ │   README explains how.           │ │
│ └──────────────────────────────────┘ │
│ Zoom connection name                 │
│ …                                    │
│ [       Check connection         ]   │
```

**States**

| State | What shows |
|---|---|
| Add page | nothing new (`webhook_secret_set` is `None`) |
| Connection `none` or `missing` | the existing notice only; no webhook line (`None`) |
| `manual` provider | nothing new (`None`) |
| Ready, secret set, heard (`True`) | `Set up` + `Changes made directly in Zoom are copied here. Last heard from Zoom on {when}.` |
| Ready, secret set, never heard (`True`, no event) | `Set up` + `Changes made directly in Zoom are copied here. Nothing heard from Zoom yet.` |
| Ready, no secret (`False`) | `Set up`, then the warn notice |
| Two accounts sharing one connection | both show the same "last heard" time (criterion 29). That's true: Zoom calls once per connection, not per account |
| After `Check connection` | unchanged: that button checks the API connection, not the webhook. Its flash doesn't mention the secret |
| No permission | unchanged: the page needs `zoom.change_hostaccount` |

**Accessibility.** No new controls, so the tab order is unchanged. Both notices are read in page order, inside the fieldset whose legend (`Zoom connection`) names them. Neither is a live region. The warning has an icon, a title and a sentence, never colour alone. The connection name wraps anywhere.


### D.5 Emails (plain text)

All three are sent after the commit, and only when something changed (criterion 16). They're `{% autoescape off %}`, like the other bodies, and hold no join link, passcode, start link, host key or token.

#### D.5.1 To the requester, classes cancelled in Zoom: `cancelled_body.txt` (reused)

**Accepted (P6, G2) and pinned in criterion 16.** As first pinned, 011's email would have been sent unchanged, opening `The IT desk has cancelled …`. That broke the honesty rule: the app doesn't know who deleted the class in Zoom, and D5 itself only assumes it was IT.

One more context value, `in_zoom` (bool, default false), changes the opening sentence and adds one line. Reconcile sends `in_zoom=True`. 011's own cancel leaves it false, and its email is unchanged. Everything else, including the `Reason:` line, stays.

```
Hello {requester_name},

{% if in_zoom %}{% if remaining %}{n} class{n|pluralize:"es"} of your Zoom booking {reference} for {class_name} {n|pluralize:"was,were"} cancelled directly in Zoom.{% else %}Your Zoom booking {reference} for {class_name} was cancelled directly in Zoom.{% endif %}{% else %}…011's sentence, unchanged…{% endif %}

Classes cancelled ({n}):
- Wed 7 Oct 2026, 8:30 am to 11:30 am

Reason: Cancelled directly in Zoom.
{% if in_zoom %}
If you didn't expect this, reply to the IT desk.
{% endif %}
…011's "still on" line, the students line and the request line, unchanged…
```

**Rendered** (one class of ZL-0042 deleted in Zoom, `zoom` provider):

```
Hello Nimal Perera,

1 class of your Zoom booking ZL-0042 for Grade 11 Physics was cancelled directly in Zoom.

Classes cancelled (1):
- Wed 7 Oct 2026, 8:30 am to 11:30 am

Reason: Cancelled directly in Zoom.

If you didn't expect this, reply to the IT desk.

Your other classes are still on, with the same link and start link.

Zoom doesn't tell the people you shared the link with. Please let your students know.

To book again, send a new request: https://tmd.polymath.edu.lk/zoom/request/

Polymath College IT desk
```

- **Why passive voice here,** against the usual plain-language advice: the active form needs a subject, and the app doesn't know it. "Someone cancelled …" would alarm the reader, and "The IT desk cancelled …" may be false. The passive sentence is the true one.
- **Why the reply line:** a teacher whose class vanished with no reason they recognise needs one thing to do. If IT made the change on purpose, the reply costs them a minute. If it was a mistake, it's recoverable in Zoom within 7 days (D5, 011 D9), so speed matters.
- **Subject unchanged** (pinned): `Cancelled: {reference} {class_name}`. It's true either way.

#### D.5.2 To the requester, classes moved in Zoom: `moved_body.txt` (reused)

The same problem and the same fix (P6, accepted; pinned in criterion 16). With `in_zoom`, the opening sentence becomes `The time of {n} class{n|pluralize:"es"} in your Zoom booking {reference} for {class_name} was changed directly in Zoom.` Everything else is 012's, unchanged: the `Was:` / `Now:` pairs, the link sentence, the students line, and `If the new time doesn't work for you, reply to the IT desk.` That last line already gives the requester the step the cancel email needed to gain, so nothing is added.

- **`Was:` is still true:** it's the time stored here before reconcile copied the move, which is the time the requester was last told.
- **`The start link follows the new times.` is still true:** the start window reads the stored times, which reconcile just changed.

**Rendered** (a one-off ZL-0043 moved in Zoom):

```
Hello Nimal Perera,

The time of 1 class in your Zoom booking ZL-0043 for Staff briefing was changed directly in Zoom.

Was: Mon 5 Oct 2026, 8:30 am to 11:30 am
Now: Tue 6 Oct 2026, 9:00 am to 12:00 pm

Your Zoom link and start link stay the same. The start link follows the new times.

Zoom doesn't tell the people you shared the link with. Please let your students know the new time.

If the new time doesn't work for you, reply to the IT desk.

Polymath College IT desk
```

#### D.5.3 To the IT desk, needs a look: `attention_subject.txt` and `attention_body.txt` (new)

Sent to every IT recipient (005 D9) when the sentences are set or changed, never for the same sentences twice (criterion 16). Context (contract): `link_request`, `lines` (list of str), `detail_url` (str, absolute).

**Subject** (pinned): `Needs a look: {reference} was changed in Zoom`. One line, no trailing newline, like the other subjects.

**Body:**

```
{reference} was changed directly in Zoom, and this system couldn't copy the change safely. The booking here and the meeting in Zoom don't match.

Reference: {reference}
Class: {class_name}
Booked on: {host_account.label}
Requested by: {requester_name}

What doesn't match:
- {line}
- {line}

What to do:
Move or cancel the class here, or change it back in Zoom, then press Check against Zoom on the booking's page:
{detail_url}

The requester hasn't been told about these. If you move or cancel a class here, they get an email as usual.

You get these emails because you're in the IT desk group on the Technology Management Desk.
```

**Rendered:**

```
ZL-0042 was changed directly in Zoom, and this system couldn't copy the change safely. The booking here and the meeting in Zoom don't match.

Reference: ZL-0042
Class: Grade 11 Physics
Booked on: Zoom 02
Requested by: Nimal Perera

What doesn't match:
- The class on Mon 12 Oct 2026, 8:30 am was moved in Zoom to Tue 13 Oct 2026, 9:00 am to 12:00 pm, but Zoom 02 already has ZL-0051 Grade 10 Chemistry then, so it wasn't moved here.

What to do:
Move or cancel the class here, or change it back in Zoom, then press Check against Zoom on the booking's page:
https://tmd.polymath.edu.lk/zoom/requests/42/

The requester hasn't been told about these. If you move or cancel a class here, they get an email as usual.

You get these emails because you're in the IT desk group on the Technology Management Desk.
```

- **Pinned:** the subject, the lines (criterion 15), and the next step (criterion 15's notice sentence, reused so the email and the page give the same instruction). Everything else is *design copy*.
- **The facts block** copies the layout of `it_new_body.txt` (`Reference:`, `Class:`, `Requested by:`), so the desk's two kinds of email look alike. `Booked on` is added because every line names the account.
- **"Couldn't copy the change safely"** explains why IT is being asked at all: the app copies what it safely can, and stops at a clash rather than double-booking an account (criterion 14).
- **The requester line** tells IT what the requester already knows, so they don't assume Zoom or the app told them. It's true: criterion 16 emails the requester only about classes it cancelled or moved, never about a needs-a-look line.
- **The link** goes to the detail page, where the notice and the button are at the top. It doesn't add `#zoom-attention`, because the notice is already the first content after the flashes.
- **No reminder is sent** for the same sentences (criterion 16). The queue tag and the notice keep the reminder on screen.

### D.6 The nightly command's output (`sync_zoom_bookings`)

It's read by whoever looks after the server, in a terminal or a scheduled task's log. P9 is accepted: criterion 19 now prints a line for each booking that changed, needs a look **or couldn't be checked**, "in the forms of Design D.6". So the lines below are the forms to build and test. It pins the couldn't-be-checked line and the summary itself.

| Case | Line |
|---|---|
| copied, email sent | `{reference} ({label}): {c} class{c\|pluralize:"es"} cancelled, {m} moved. Emailed the requester.` Either part is left out when its count is 0: `ZL-0042 (Zoom 02): 1 class cancelled, 2 moved. Emailed the requester.` / `ZL-0043 (Zoom 03): 1 class moved. Emailed the requester.` |
| copied, email failed | `ZL-0042 (Zoom 02): 1 class cancelled. The email to the requester didn't send.` |
| needs a look, new or changed sentences (IT emailed) | `ZL-0042 (Zoom 02): needs a look. Emailed the IT desk.` |
| needs a look, the same sentences as before (no email, criterion 16) | `ZL-0042 (Zoom 02): still needs a look. No new email.` |
| copied and needs a look | `ZL-0042 (Zoom 02): 1 class moved, and needs a look. Emailed the requester and the IT desk.` With a failed requester email: `ZL-0042 (Zoom 02): 1 class moved, and needs a look. Emailed the IT desk. The email to the requester didn't send.` |
| couldn't be checked (pinned) | `{reference} ({label}): couldn't be checked: {reason sentence}`, e.g. `ZL-0042 (Zoom 02): couldn't be checked: Zoom is busy right now.` |
| summary (pinned) | `Checked {n} booking{n\|pluralize}: {c} changed, {a} need{a\|pluralize:"s,"} a look, {f} couldn't be checked.`, e.g. `Checked 1 booking: 0 changed, 1 needs a look, 0 couldn't be checked.` |

- **"Still needs a look" is printed, not skipped,** so the summary's `{a}` always matches the number of needs-a-look lines above it. Anyone reading the log can count.
- **The `cancelled` part always comes before `moved`,** so lines from different nights read alike.
- The class names, dates, emails and links are left out, so no line holds a link, a token, a class name or an email address (criterion 19).
- Criterion 28's sweep (G3) prints nothing.
- **Exit code 1** when any booking couldn't be checked (criterion 19), so a scheduled task can alert.

### D.7 Copy

**Pinned, used verbatim:** criterion 2 (`zoom.W002`'s sentence; server output, not a screen), 15 (the two attention sentences, the notice title `Changed in Zoom: needs a look`, its next step, and the tag `Needs a look`), 16 (the reason `Cancelled directly in Zoom.`, the IT subject, and since P6 the two `in_zoom` opening sentences and `If you didn't expect this, reply to the IT desk.`), 18 (the button `Check against Zoom` and every one of its messages, including P1–P5 and G4–G5), 19 (the couldn't-be-checked line, the pluralised summary, and D.6's line forms by reference), 27 (the three "directly in Zoom" texts on the detail page) and 29 (the account page's paragraph and warn notice).

**Design copy** (new here; the frontend owns it unless noted):

| Where | Text |
|---|---|
| Detail, cancelled line, cancelled in Zoom | `This booking was cancelled directly in Zoom. The change was copied here on {when}. It was approved by {decided_by} on {when}.` |
| Detail, notice next step without the button | `Move or cancel the class here, or change it back in Zoom.` |
| Detail, `Check against Zoom` box title | `Check against Zoom` (the pinned button name, reused) |
| Detail, box lead | `Changes made directly in Zoom are usually copied here by themselves. If you've just changed this booking in Zoom, press the button to copy the change now. If a class was cancelled or moved, the requester gets an email.` |
| Busy text | `Checking with Zoom…` |
| Class rows, Zoom notes | `Moved directly in Zoom. Copied here on {when}.` / `Cancelled directly in Zoom. Copied here on {when}.` |
| Queue, Cancelled tab's empty state | `Bookings show here when they're cancelled, here or directly in Zoom.` |
| IT email body | D.5.3, except the pinned lines and next step |

**Words that never appear on a screen or in an email:** "webhook", "reconcile", "sync", "event", "payload", "signature", "occurrence", "API", "secret" (except in the server-facing W002 text and D.4.1's warning, whose words the server admin looks up in the README), "token". IT reads "changed directly in Zoom", "copied here" and "Check against Zoom".

### D.8 Accessibility

- **Landmarks and headings.**
  - **Detail:** h1, then an h2 per box. The new box's h2 is `Check against Zoom`. No new levels. The notice's title is a `p.notice__title`, like every notice, not a heading: it's state, not a section.
  - **Queue:** unchanged. The tag is inside the Status cell.
  - Everything is inside the shell's `main`.
- **Labels and descriptions.**
  - The button's name, `Check against Zoom`, is its whole visible text, and it's the only control with that name on the page (D.1.1). In the notice, the sentence just before it says when to press it. In the box, the lead says what it does.
  - No fields, so no `aria-describedby`, `aria-invalid` or error summary is needed.
- **Status is never colour alone.**
  - `Needs a look`: `alert-triangle` + the word, in both places.
  - The notice: `alert-triangle` + a title + sentences.
  - `Cancelled` / `Moved`: unchanged icons and words, and the source is in words (`directly in Zoom`).
  - Every flash: an icon + words (`flash-messages.md`).
- **Announcements.**
  - After a press, the flash after the redirect: `role="status"` for success and warning, `role="alert"` for errors (existing).
  - While busy, the button's text changes and `data-busy-status` announces `Checking with Zoom…`.
  - The notice isn't a live region. It's read in page order, straight after the flashes.
- **Keyboard and focus order** (detail, needs a look): skip link → shell → breadcrumb links → flash Close (if any) → `Check against Zoom` (in the notice) → the Request box's links (`See it on the timetable`, Zoom link, start link, email, phone) → the class rows' `Move this class` / `Cancel this class` in date order → `Change the time of the remaining classes` → `Cancel this booking`. Without the notice, `Check against Zoom` comes after the class rows instead, before the series link. Both follow the visual order.
  - **After the redirect:** a normal page load. Focus starts at the top, and the flash is the first content after the h1. No focus is moved by script.
  - **Busy submit:** focus stays on the button (`aria-disabled`, not `disabled`).
  - **No dialogs,** so there's no focus to restore.
- **Touch targets.** `.button` is 44px tall at every width, and full width inside `.form-actions` below 600px. The class rows' actions keep their 44px (class-rows.md). Tags aren't interactive.
- **Reflow and contrast.** No sideways scroll at 320, 400, 1024 or 1440, in either colour mode. The notice's list wraps anywhere (it holds class names). The queue's two tags wrap inside `.tags`. **No new colour pairs:** `notice--warn`, `tag--warn`, `button--secondary` and `notice--note` are existing, checked AA pairs. `button--secondary` sits on `--c-warn-soft` inside the notice: its own `--c-primary-soft` fill carries its text contrast, so the warn background doesn't affect it.
- **Times.** The notes and the cancelled line print their times through `zoom/partials/when.html` (`<time datetime>`). The pinned attention lines are the one exception (D.1.3).

### D.9 Progressive enhancement

- **Works with plain HTML and full page loads:** everything here. The button is a real `<form method="post">` with a CSRF token. The result is a 302 and a flash. The notice, the tag and the notes are server-rendered. There's no `confirm()`: a check is safe to repeat, so it needs none.
- **What `app.js` adds (existing blocks only, no new JS):**
  - the busy button on the sync form (`data-busy-form`, `data-busy-text`, `data-busy-status`);
  - flash Close.
- **No polling and no live update.** A webhook can change the booking while IT has the page open. The page doesn't refresh itself: the next load, or a press of the button, shows the current state. A booking changed under an open move or cancel form is already caught by 011's and 012's checks (012 D17's `shown` fingerprint).

### D.10 Copy proposals

**Status (2026-10-30): accepted.** The main session accepted P1–P7 and P9, and the planner recorded them as **D11**. P1–P5 are pinned in criterion 18, P6 in 16, P7 in 29 (written out as D.4.1), and P9 in 19. **P8 is recorded as a follow-up only** and isn't built in 013. The criteria are the source of truth. The table below keeps the proposals as written, as the record of why each change was made. **P10** (below the table) is new: a review of the one criterion-18 text the planner wrote itself.

| # | Where | Pinned now | Proposal | Why |
|---|---|---|---|---|
| P1 | criterion 18, success flash | `Checked with Zoom: {n} change(s) copied here. We emailed {email}.` | `Checked with Zoom: {n} change{n\|pluralize} copied here. We emailed {email}.` | A literal `(s)` reads as a form, not a sentence. 012's P2 did the same for `class{n\|pluralize:"es"}` |
| P2 | criterion 18, a new warning | none | `Checked with Zoom: {n} change{n\|pluralize} copied here, but the email to {email} didn't send. Tell them yourself.` (warning) | Without it, an email failure either shows a success that claims `We emailed …` (untrue), or no flash at all. The words follow 011's `Cancelled, but the email to {email} didn't send. Tell them yourself.` Needs G6 |
| P3 | criterion 18, copied **and** needs a look | `Checked with Zoom: some changes need a look.` only | `Checked with Zoom: {n} change{n\|pluralize} copied here, and some changes need a look. We emailed {email}.` (warning) | The pinned warning hides that the requester was just emailed. IT then can't tell whether to contact them. Both facts in one flash keeps "one message" (criterion 18) |
| P4 | criterion 18, error's next step | "006's temporary or lasting next step" | temporary: `Try again in a few minutes.` (006). Lasting: `Ask whoever manages the Zoom accounts to press Check connection for {label}, then try again.` (011's, as 012's P6 chose). Daily limit: `services.daily_reset_sentence()` alone (012 D22) | 006's lasting step starts `Choose another free account`, which means nothing here: a check is about one booking on one account. 012 hit the same problem (P6, D.14) |
| P5 | criterion 18, no-change flash | `Checked with Zoom: nothing had changed.` | `Checked with Zoom: this booking matches Zoom.` | The press that clears a notice is usually made **after** IT changed Zoom back, or moved the class here. Zoom *had* changed, and IT knows it. "Nothing had changed" would contradict what IT just did, and wouldn't confirm the notice is gone. "Matches" is true in every no-change case, including the plain one |
| P6 | criterion 16, requester emails | 011's and 012's emails unchanged: `The IT desk has cancelled …` / `The IT desk has changed the time …` | an `in_zoom` flag changes the opening sentence (D.5.1, D.5.2), and the cancel email gains `If you didn't expect this, reply to the IT desk.` Needs G2 | The honesty rule: the app doesn't know who changed Zoom. If it wasn't IT, the email tells the teacher something false, from IT's own address |
| P7 | the Zoom account change page (optional, needs a contract addition) | nothing | in the `Zoom connection` section, `ready` state. **Secret set:** the `Set up` notice gains a sentence: `Changes made directly in Zoom are copied here. Last heard from Zoom on {when}.` (or `Nothing heard from Zoom yet.`). **No secret:** a second notice, `notice--warn` + `alert-triangle`, title `Changes made in Zoom aren't seen here`, body `The server has no webhook secret for {name}. Until it has one, a class changed or deleted directly in Zoom stays as it was here until its booking is checked against Zoom. Ask whoever looks after the server to add it. The README explains how.` The accounts list is unchanged (seven columns are already tight at 1024px) | Today only `check --database` shows W002, which IT never runs. "Last heard" doubles as a health check, because every cancel and move made in the app echoes back as an event. Needs `webhook_secret_set` (bool, never the secret) and `last_zoom_event_at` (the newest `ZoomEvent.received_at` for the set's slug, one query) on `zoom/account_form.html`. The planner decides whether it's in 013 or a follow-up |
| P8 | queue (follow-up) | a tag only (D8) | a `Needs a look` tab between `Waiting` and `Link sent`, with its count, through `status-tabs.md` unchanged. Result line `{n} booking{n\|pluralize} that need{n\|pluralize:"s,"} a look`; empty state with a `check-circle` disc, `Nothing needs a look.`, `Bookings show here when a change made directly in Zoom couldn't be copied here.` | A flagged booking can sit on page 3 of `Link sent`. The email is the only way to find it. Needs a count in `tab_counts()` and a `for_tab` filter, so it's a contract change. Not needed for go-live |
| P9 | criterion 19, the command | lines only for changed or needs-a-look bookings; `Checked {n} bookings: {c} changed, {a} need a look, {f} couldn't be checked.` | also one line per booking that couldn't be checked (D.6); and plurals: `Checked {n} booking{n\|pluralize}: {c} changed, {a} need{a\|pluralize:"s,"} a look, {f} couldn't be checked.` | Exit code 1 says *that* something failed, but not *which* booking or why. `1 bookings` and `1 need a look` read as mistakes |

#### P10: the planner's combined flash (criterion 18). A small proposal, for the main session

**Status: a proposal.** Until it's accepted, criterion 18's text stands, and D.1.7 shows it.

**The pinned text** (copied, the requester email failed, and something needs a look):

`Checked with Zoom: {n} change{n|pluralize} copied here, and some changes need a look. The email to {email} didn't send. Tell them yourself.`

**Checked against P2 and P3:**

- **Honest: yes.** Each sentence is true in this case: changes were copied, some changes weren't, and the requester's email didn't go. Nothing is claimed that the app doesn't know.
- **Consistent: yes.** The first sentence is P3's, word for word, without its `We emailed {email}.` The last two are P2's and 011's wording, split into two sentences.
- **Clear: one gap.** In P2, `Tell them yourself.` can only mean "tell them about the copied changes", because that's all the flash mentions. Here it follows a sentence about changes that **need a look**. A reader can take it as "tell the requester about those too". The requester is never told about a needs-a-look line (criterion 16, D.5.3's "The requester hasn't been told about these"), and those changes aren't settled yet. Telling the teacher about them now could send them to the wrong time.

**Proposal:** name what to tell them.

`Checked with Zoom: {n} change{n|pluralize} copied here, and some changes need a look. The email to {email} didn't send, so tell them about the copied change{n|pluralize} yourself.`

Rendered, for 2 changes: `Checked with Zoom: 2 changes copied here, and some changes need a look. The email to nimal@polymath.edu.lk didn't send, so tell them about the copied changes yourself.`

- It keeps the level (warning), the one-message rule, and P3's first sentence unchanged, so the two warnings still open alike.
- **Not proposed:** changing P2's own `Tell them yourself.` There, nothing else is in the flash for "them" to be told about, so it's already clear.
- **If it's accepted:** criterion 18's row and its test text change. D.1.7's row, which shows the pinned text, then takes the new one. No template or icon changes: it's a backend message constant.

### D.11 Build list for `tmd-frontend`

- **Templates** (each new or changed one starts with the `{# … #}` header naming its purpose and context; every include ends with `only`):
  - **New** `zoom/partials/attention_tag.html` (D.3.1).
  - **New** `zoom/partials/sync_form.html` (D.1.4), included `with link_request_pk=… csrf_token=csrf_token only`.
  - `zoom/detail.html`: the notice (D.1.3), the cancelled line's Zoom form (D.1.2), the tag in the Status row (D.1.1 item 4), the `Check against Zoom` box (D.1.4). The header comment gains `zoom_attention_lines`, `can_sync` and `cancelled_in_zoom`.
  - `zoom/partials/class_rows.html`: the two Zoom notes (D.1.5). The header comment gains `cancelled_in_zoom` and `moved_in_zoom`.
  - `zoom/queue.html`: the Status cell's `span.tags` wrapper and the tag (D.3.2); the Cancelled tab's empty-state sentence (D.3.3). The header comment gains `zoom_attention`.
  - **New** `zoom/email/attention_subject.txt` and `attention_body.txt` (D.5.3).
  - `zoom/email/cancelled_body.txt` and `moved_body.txt`: the `in_zoom` branches (D.5.1, D.5.2; P6, criterion 16). Each header comment gains `in_zoom` (bool, default false).
  - `zoom/account_form.html`: the `Zoom connection` section's added paragraphs and the warn notice (D.4.1; P7). The header comment gains `webhook_secret_set` (`True`, `False` or `None`) and `last_zoom_event_at` (criterion 29).
  - **Not built:** P8's queue tab (a follow-up).
- **CSS:** none.
- **Icons:** none new.
- **JS:** none.
- **Component notes:** build from `class-rows.md` and `busy-button.md` as they are now (G7's amendments were applied 2026-10-30).

### D.12 Gaps in the context contract (backend to add or confirm)

**Status (2026-10-30): G1–G8 accepted** by the main session and pinned by the planner (D10): G1 in criteria 14 and 27, G2 in 16, G3 in 28, G4–G6 in 18, and G8 in the contract. G7 is done: both component notes are amended. G9 was settled by criterion 29 with no further change. The entries below keep the gaps as first written, as the record.

- **G1. Where a change came from, decided once, on the model.** Today's notes print `Moved by None` and `Cancelled by None`. The rule "an empty `*_by` with its timestamp set means it was done in Zoom" is true because the user keys are `PROTECT` (nobody is deleted). It's a business rule, so it belongs on the model, not in a template `{% if not occurrence.moved_by %}`:
  - `Occurrence.moved_in_zoom` (bool: `moved_at` set and `moved_by_id` is `None`);
  - `Occurrence.cancelled_in_zoom` (bool: `cancelled_at` set and `cancelled_by_id` is `None`);
  - `LinkRequest.cancelled_in_zoom` (bool: the same, on the booking).

  **Please also confirm** that reconcile sets `LinkRequest.cancelled_at` (with `cancelled_by` left empty) when `status_after_cancel` makes the booking `cancelled`, as 011's `cancel()` does. D.1.2's line reads it.
- **G2. `in_zoom` (bool)** on `cancelled_body.txt` and `moved_body.txt`: true when reconcile sends them. Only if P6 is accepted.
- **G3. A needs-a-look flag must not outlive the booking.** `can_sync` is false once a booking has no remaining classes, and the nightly command skips it. So a flag left on it could never be cleared, and its tag would sit in `Link sent` and `All` for good. **Recommendation:** clear `zoom_attention` whenever a booking stops having remaining classes: in the model operation that makes it `cancelled` (011's cancel, and reconcile), and in `sync_zoom_bookings`, which also clears it on approved bookings with no remaining classes (one `UPDATE`). The template then needs no extra condition.
- **G4. `zoom:sync` when there's nothing to check** (`can_sync` false: a stale page, or a hand-made POST). Criterion 18 doesn't say. **Recommendation:** redirect to the detail with an error flash, as 012 criterion 4 does for a move that's no longer possible. *Design copy*: `There are no classes left to check in this booking.`, or for the `manual` provider, `This system can't reach Zoom, so it can't check this booking.` The detail page then shows why.
- **G5. A lock wait or deadlock** during a button-pressed reconcile. **Recommendation:** reuse 012's `MOVING_AT_THE_SAME_MOMENT` text, `Someone else was changing this booking at the same moment. Nothing was changed. Try again.`, as an error flash. It's true: the transaction rolled back. The webhook path has its own answer (criterion 10: 500, and Zoom retries).
- **G6. `ReconcileResult` needs to say whether the requester email was sent** (`emailed`, bool), so the view can choose P2's warning. Its `cancelled` and `moved` lists give `{n}` (`n = len(cancelled) + len(moved)`). The requester's address for `{email}` is `link_request.requester_email`.
- **G7. Component note amendments** (for the main session to accept; not edited here, because this task may only add new `docs/design/` files):
  - `docs/design/class-rows.md`, "What a row shows": after the "Moved note" row, add `Moved note, in Zoom (brief 013) | moved_in_zoom | p.classrows__note: Moved directly in Zoom. Copied here on {when}.`; after the "Cancelled note" row, add `Cancelled note, in Zoom (brief 013) | cancelled_in_zoom | p.classrows__note: Cancelled directly in Zoom. Copied here on {when}. The stored reason isn't printed: it's the same words.` In "States", the `Moved` and `Cancelled` rows gain "or the Zoom note". In the Origin line, add "Amended by brief 013: the notes say when a change was made directly in Zoom."
  - `docs/design/busy-button.md`, "Used by": add `zoom/detail.html` (brief 013) | `Check against Zoom` (`.button--secondary`, in the needs-a-look notice or its own box; `zoom/partials/sync_form.html`) | `Checking with Zoom…`.
- **G8. Fields read from `link_request`** in the IT email: `reference`, `class_name`, `requester_name` and `host_account.label`. They're on the object already. Please list them in the contract.
- **G9 (raised 2026-10-30; settled by criterion 29, no action).** I first asked for `checks_zoom` on `zoom/account_form.html`, so the `manual` fallback wouldn't show a warning nobody can act on. Criterion 29 does it better: `webhook_secret_set` is `None` under `manual`, on the add page, and for a connection that isn't `ready`, and the template shows nothing for `None`. No extra value is needed.
- **Confirmed, no gap:** `zoom_attention_lines` and `can_sync` on the detail page, and `link_request.zoom_attention` on each queue row, are as the contract says. `csrf_token` is in every request context already.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops (agent plan step 2, criterion 1), 2026-10-30
*Amended by 015 (2026-11-02):* the notes below are left as the historical record. Brief 015 moved the webhook secret from `zoom-credentials.env` into the database, so `ZOOM_S2S_*`, `webhook_secret_set_for` and the `read_zoom_credentials` block they describe are gone.

**The planner's "env only" is confirmed against the code.**
- `compose.yaml` passes the whole of `zoom-credentials.env` to `web` through `env_file: [{path: ./zoom-credentials.env, required: false}]`, so a fourth variable per set arrives with no compose change. `compose.dev.yaml` doesn't touch `env_file`. Listing it under `web.environment` would be wrong: it would override the file (CLAUDE.md's Zoom-credentials exception, which `test_compose_loads_the_optional_credentials_file` enforces).
- `.env.example` already says, generically, that `ZOOM_S2S_*` doesn't go in `.env`. Nothing to add there.
- `.gitignore` and `.dockerignore` already keep `zoom-credentials.env` out of git and the image.

**Files changed**
- `config/settings/base.py`:
  - `ZoomCredentials` gains `webhook_secret: str = field(default="", repr=False)`. Its docstring says why it's optional.
  - New `ZOOM_CREDENTIAL_OPTIONAL_PARTS = (("webhook_secret", "WEBHOOK_SECRET"),)`, beside the three required `ZOOM_CREDENTIAL_PARTS`.
  - `read_zoom_credentials` reads the optional parts under the same naming rule (`zoom_credential_env_prefix(slug) + "_WEBHOOK_SECRET"`) and strips them. A blank or absent value becomes `""` and never makes a set incomplete, so it's never listed in `ZOOM_CREDENTIAL_MISSING` and `zoom.E005` doesn't change. A webhook secret on its own also never completes an incomplete set.
  - The `ZOOM_S2S_SECRETS` comment now says that webhook secrets are inside it too. They're masked because the setting name contains `SECRET`.
- `zoom-credentials.env.example`:
  - The header now says "copy the four variables below", and that the fourth is optional.
  - New line `ZOOM_S2S_ZOOM_01_WEBHOOK_SECRET=` (empty), with a comment that says where Marketplace shows the Secret Token, what it's for, and that it's a secret.
- `apps/core/test_zoom_settings.py` (platform tests):
  - `FAKE` now carries a dummy `webhook_secret`, and the repr, error-report masking and debug-page tests check all four values.
  - The masking test also asserts that no value appears in `repr(get_safe_settings())`.
  - New tests:
    - the secret is read and stripped;
    - a set is complete without it (absent, empty, or blank);
    - a webhook secret doesn't complete an incomplete set;
    - the field defaults to `""`, so the zoom app's `zoommock.credentials()` still works unchanged.
  - The example-file test now expects the fourth name.
  - The source scan (`test_zoom_s2s_env_is_read_only_in_base_settings`) is unchanged and still passes.

**Masking (criterion 1)**
- The value lives only inside `ZOOM_S2S_SECRETS`, which Django's `SafeExceptionReporterFilter` masks.
- `repr=False` keeps it out of `repr()` and `str()`. Under prod, `repr(settings.ZOOM_S2S_SECRETS["zoom-01"])` prints `ZoomCredentials(slug='zoom-01')`.
- Nothing logs it: `base.py` doesn't log, and the variable is read only there.

**Is `/zoom/webhooks/<slug>/` a secret-bearing path? No.** `config/log_filters.py` is unchanged.
- The slug is the credential-set name (`zoom-01`). IT can see it on the Zoom accounts page as "Zoom connection name", and D2 says outright that slugs aren't secrets.
- The secret travels only as a key. It never travels in the request: the request carries a per-request HMAC in the `x-zm-signature` header, which the 300-second window and D3 bound.
- Gunicorn's access log uses its default format (the Dockerfile `CMD` sets no `access_log_format`), so it records the request line and Referer, never request headers or the body.
- So a logged webhook path gives away nothing usable.
- If 014 adds a recording download path to the app that carries a token, that one *would* need a `log_filters.py` rule.

**For the backend (`tmd-django-backend`): one thing that affects criteria 4 and 5.**
- Django's handler logs every 4xx response at `WARNING` on `django.request` (`django/utils/log.py` `log_response`, called from `BaseHandler.get_response`): `Not Found: /zoom/webhooks/zoom-99/`, `Unauthorized: /zoom/webhooks/zoom-01/`, `Method Not Allowed …`, `Payload Too Large …`. It does this unless the response is already marked as logged.
- Criterion 4 says an unknown slug gets "no log above `INFO`", and criterion 5 says "**one** `WARNING`". Taken across all loggers, Django's own line breaks both.
- These lines contain only the path and slug, so they aren't a secret leak.
- The planner or main session should decide whether the criteria mean the app's own logger, or whether the view should suppress Django's line. I didn't change `LOGGING`, because silencing `django.request` for one path would be a hidden rule that nobody asked for.
- Two smaller notes:
  - `DATA_UPLOAD_MAX_MEMORY_SIZE` stays at Django's default 2.5 MB. That's above the 256 KB cap, so the view's own `Content-Length` check (413) is what refuses large bodies, as criterion 4 intends.
  - `zoommock.credentials()` doesn't need changing for existing tests. To get the "test secret", pass `webhook_secret=` to `ZoomCredentials` yourself.

**New env vars**
- `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`, one per credential set. It's optional and defaults to `""`.
- It goes in `zoom-credentials.env` only, not in `.env` or `web.environment`, by design (CLAUDE.md's exception).

**Dependency changes:** none. The backend's verifier uses stdlib `hmac`/`hashlib`.

**Operational steps for the user**
- No rebuild is needed for this change by itself, since settings are read at start-up.
- Per account, after D6 step 4 (adding the secret to `zoom-credentials.env`), **recreate** `web` so `env_file` is re-read: `docker compose up -d`. A `restart` isn't enough.
- No migration from this step.

**For `tmd-docs-writer`: README and CLAUDE.md wording that's now out of date.** I didn't change these.
- `README.md` line 178: "the three `ZOOM_S2S_<NAME>_*` variables per account" should become three required plus an optional fourth, the webhook secret.
- `README.md` lines 419–422, "Connecting an account to Zoom" step 8: mention `ZOOM_S2S_ZOOM_01_WEBHOOK_SECRET` (optional, D6 step 4).
- CLAUDE.md "Environment gotchas", the Zoom-credentials exception: "the three `ZOOM_S2S_<NAME>_*` variables per account" needs the same change. The agent plan's step 6 already covers this.

**Self-check output**
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `115 files already formatted`.
- `docker compose config --quiet` (prod, `WEB_PORT=8011`) and `docker compose -f compose.yaml -f compose.dev.yaml config --quiet`: both exit 0.
- `pytest apps/core/test_zoom_settings.py` (dev container, reusing the test DB, no `--create-db`): 21 dots, exit 0.
- `pytest` full suite (dev container, no `--create-db`): 1320 tests collected, exit 0. The project's `-q` addopts suppress the summary line.
- `manage.py makemigrations --check --dry-run`: `No changes detected`.
- `manage.py check` (dev): `System check identified no issues (0 silenced).`
- Dev, dummy env via `exec -e`, with two sets, `zoom-01` with a webhook secret and `zoom-02` without:
  - `ZOOM_S2S_SECRETS` printed as `{'zoom-01': ZoomCredentials(slug='zoom-01'), 'zoom-02': ZoomCredentials(slug='zoom-02')}`;
  - `{'zoom-01': True, 'zoom-02': False}` for "has a webhook secret";
  - `ZOOM_CREDENTIAL_MISSING == {}`.
- Prod stack, rebuilt with `WEB_PORT=8011 ZOOM_PROVIDER=manual docker compose up -d --build`: `web` reached `healthy` (`polymath-tmd:latest`, `0.0.0.0:8011->8000`).
- `check --deploy` on the prod stack, with `USE_HTTPS=True`, `ZOOM_PROVIDER=zoom` and a dummy set that includes a dummy webhook secret (all through `exec -e`): only `security.W021`, `System check identified 1 issue (0 silenced).`, exit 0.
- Plain `check` on prod: no issues.
- Under prod settings, `repr` of the dummy set is `ZoomCredentials(slug='zoom-01')`, with webhook secret present `True` and `ZOOM_CREDENTIAL_MISSING == {}`.
- Not run here: `check --database default` for `zoom.W002`. The backend builds that check (criterion 2), and the verifier runs it (criterion 24).
- The dev stack was restored afterwards: `WEB_PORT=8011 docker compose -f compose.yaml -f compose.dev.yaml up -d`, image `polymath-tmd:dev`, `ZOOM_PROVIDER=fake`, `config.settings.dev`, `/healthz/` 200 on 8011. `talentlink-web-1` on 8010 wasn't touched. `.env` wasn't edited.

### tmd-django-backend (agent plan step 3a), 2026-11-02

**Files changed**
- `apps/zoom/models.py`:
  - `LinkRequest.zoom_attention` (+ `zoom_attention_lines`) and the G1 properties `cancelled_in_zoom` on `LinkRequest` and `Occurrence`, and `moved_in_zoom` on `Occurrence` (no query).
  - The shared locked writes `LinkRequest.record_cancel()` (it clears `zoom_attention` when the booking becomes `cancelled`, criterion 28) and `record_moves()`. 011's `cancel()`, 012's moves and reconcile all use them.
  - New QuerySet methods: `with_remaining_classes()`, and `clear_stale_attention()`, the one-`UPDATE` sweep.
  - `webhook_secret_set_for()`, the `ZoomEvent` model and `ZoomEventQuerySet.last_received_at()`.
  - The pinned sentences `CANCELLED_IN_ZOOM_REASON`, `ZOOM_MOVE_CLASHES` and `ZOOM_CLASS_NOT_BOOKED`, and the helpers `class_span` / `class_moment`.
  - Help texts on the cancel and move fields now cover changes copied from Zoom.
- `apps/zoom/migrations/0009_zoom_sync.py` (new, schema only).
- `apps/zoom/sync.py` (new): `compare()`, the pure rules of criterion 14, with no DB and no HTTP, like `timetable.py`.
- `apps/zoom/webhooks.py` (new):
  - `verify(request, slug) -> ZoomCredentials | Refusal`, `read_event()`, `url_validation_reply()`, `is_from_account()`, `body_sha256()`;
  - `MAX_AGE_SECONDS = 300` and `MAX_BODY_BYTES = 256 * 1024`.
- `apps/zoom/providers.py`:
  - `MeetingState` (times, occurrence IDs and deleted IDs only);
  - `meeting_state()` on the live provider (one `GET /meetings/{id}`; 3001 means `None`), with `read_meeting_state()` to read the answer;
  - a steerable fake: `meeting_states` and `state_calls`, plus a registry of the meetings the fake made itself, so the app's own changes read back as no change.
- `apps/zoom/services.py`:
  - `reconcile()`, `ReconcileResult` (with `emailed`, G6), `handle_event()`, `sync_blocked_message()` (G4), `sync_message()` and `sync_failed_message()` (P4);
  - criterion 18's message constants, plus `SYNC_MESSAGES` for the word scan;
  - `send_attention_email()`, `in_zoom` on the two requester emails, and `absolute_url()`;
  - `cancel()` and `_move_once()` now write through the model operations.
- `apps/zoom/views.py`:
  - `ZoomWebhookView`, the one view without CSRF protection, plus `WEBHOOK_STATUS`;
  - `SyncBookingView`;
  - `zoom_attention_lines` and `can_sync` on the detail page;
  - `webhook_secret_set` and `last_zoom_event_at` on the account form.
- `apps/zoom/urls.py`: `zoom:sync` and `zoom:webhook`.
- `apps/zoom/checks.py` and `apps.py`: `zoom.W002`, tagged `database`.
- `apps/zoom/management/commands/sync_zoom_bookings.py` (new).
- Tests:
  - New: `synckit.py` (helpers), `test_sync_models.py`, `test_reconcile.py`, `test_webhook.py`, `test_sync_views.py`, `test_sync_command.py` and `test_sync_race.py` (committed-data thread tests).
  - Changed: `test_zoom_accounts_connection.py`'s `test_there_is_no_webhook_url` (006 criterion 39) is now `test_the_only_webhook_url_is_brief_013s`, per D7.

**Context contract, as implemented: no deviation.**
- `zoom/detail.html`: `zoom_attention_lines` and `can_sync`. `link_request.cancelled_in_zoom` is the model property.
- `class_rows.html`: `occurrence.moved_in_zoom` and `occurrence.cancelled_in_zoom`, both model properties.
- `queue.html`: `link_request.zoom_attention`, a column on the row; the test shows no extra query.
- `account_form.html`: `webhook_secret_set` (`True`, `False` or `None`) and `last_zoom_event_at`.
- The emails:
  - `attention_*`: `link_request`, `lines` and `detail_url`;
  - `cancelled_body.txt` and `moved_body.txt`: `in_zoom`.
- Messages: criterion 18's flashes, as pinned, with P10's text.

**Decisions and additions to review** (none changes a pinned text):
1. **"Missing" vs "series rebuilt"** (criterion 14):
   - Zoom lists the class as deleted: it's cancelled here.
   - Zoom doesn't have it at all: it's cancelled only when Zoom has no unmatched class from now on.
   - Otherwise the series was probably rebuilt in Zoom (new IDs at new times), so nothing is cancelled and Zoom's unmatched classes get the pinned "isn't booked here" sentence.
   - Why: cancelling would wrongly email the teacher that every class was cancelled after IT changed the series' time in Zoom.
   - Classes with no stored occurrence ID are matched by their start.
2. **One unpinned needs-a-look sentence**, `ZOOM_MOVE_NOT_BOOKABLE`: `The class on {old} was moved in Zoom to {new}, but that time can't be booked here, so it wasn't moved here.`
   - When it applies: Zoom moved a class to a time 012's rules refuse (off the 5-minute step, across midnight, already passed, or more than a year ahead).
   - Why: copying it would break the slot grid.
   - It needs the planner's or designer's pin.
3. **Meetings with no fixed dates are "couldn't be checked"** (`ZoomUnavailable`): a Zoom type other than 2 (scheduled) or 8 (weekly), or an answer the code can't read.
   - Nothing is cancelled for a meeting the app simply couldn't read.
   - The phrase shown is 006's `no answer from Zoom`.
4. **What the webhook looks up:** `approved` **and** `cancelled` bookings.
   - Why: criterion 17 needs the echo of a whole cancel made here to be `no_change`; with approved-only (criterion 12) it would be `not_ours`.
   - A cancelled booking is never sent to Zoom and never changed.
5. **The nightly run's absolute URLs** (the requester's `request_url` and IT's `detail_url`): the command has no request, so `services.absolute_url()` uses the first concrete `ALLOWED_HOSTS` entry, with `USE_HTTPS` for the scheme.
   - The webhook and the button use the request, as every email did before.
   - **For `tmd-devops` / the planner:** an explicit site-URL setting would be clearer. It's not added here (settings belong to devops).
6. **Extra command lines** (D.6 doesn't cover these cases):
   - copied with a known flag: `…, and still needs a look. Emailed the requester.`;
   - the IT email failed: `The email to the IT desk didn't send.`;
   - a lock race: `couldn't be checked: Someone else was changing this booking at the same moment.`;
   - under `manual`: `This system can't reach Zoom, so no bookings were checked.` (exit 0).
   - Bookings on unconnected accounts are skipped, not counted.
7. **Webhook answers beyond the table:** a lock race after the retry is 500 with one `ERROR` line (G5's "the webhook has its own answer").
   - A verified body that isn't an event is 400, and so is a bad validation token.
   - 413 logs one `WARNING` (`too large`).
   - An unknown name logs at `INFO` only (criterion 4).
8. **Not asking Zoom never clears a flag.** Only G3 does that, when no class is left.
   - "Not asking" means a booking with nothing left, or a provider that can't reach Zoom.
   - "Cleared by the next reconcile that finds nothing to flag" applies only when Zoom was actually asked.
9. **D14 is followed:** every log assertion filters to `apps.*` records, and `LOGGING` is unchanged.
10. **D6's scope note isn't confirmed against Marketplace**, because there's no network access from here.
    - By code: the only new Zoom call is `GET /meetings/{id}`, the endpoint that 011's start link and `occurrence_id_for` already use. So no new REST scope is needed.
    - The owner's live check, step 1, confirms the event subscription.

**Migrations:** `0009_zoom_sync`:
- adds `LinkRequest.zoom_attention`;
- creates `ZoomEvent`, with the unique `(slug, body_sha256)` key and an index on `(slug, received_at)`;
- changes six help texts.

It's reversible.

**Dependencies and settings:**
- No new dependency: `hmac`, `hashlib` and `json` come from the standard library.
- No settings change, and `LOGGING` is untouched.

**Self-check output** (dev container, 2026-11-02):
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `125 files already formatted`.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `python manage.py check`: `System check identified no issues (0 silenced).`
- `python manage.py check --database default`:
  - With dev settings (`fake`): `System check identified no issues (0 silenced).`
  - With `exec -e ZOOM_PROVIDER=zoom` and a dummy set `polymathlesson-account` with no secret: `(zoom.W002) polymathlesson Paid's Zoom connection has no webhook secret, so changes made directly in Zoom to its meetings aren't seen here.`, plus the expected `zoom.E004` for the dev accounts Zoom 01–03, which have no connection name.
  - The same with a dummy `…_WEBHOOK_SECRET`: W002 is gone, and only those three E004s remain.

backend pytest run finished: `pytest --create-db -p no:randomly -rN` → `1483 passed in 103.25s (0:01:43)`, exit 0.

#### Fix cycle 1 (review round 1), 2026-11-02

Built to D16–D18 and criteria 10, 18–21, 30 and 31 as the planner pinned them. The provisional S1 phrase from the main session's hand-off was **not** used: criterion 31 pins 006's `ZoomUserNotFound` phrase instead, so no new wording was added.

**Files changed**
- `apps/zoom/models.py`:
  - `LinkRequest.sync_fingerprint(occurrences=None)` (B1, criterion 30): `(status, ((pk, starts_at, ends_at, cancelled_at), …))`, with the classes sorted by pk. It makes no query when the classes are passed in.
  - `LinkRequest.classes_still_on(now, *, occurrences)` (N4), placed beside `remaining_classes`. It's now the only place the "not cancelled and not ended" rule is written. `status_after_cancel`, 011's `cancel()` and reconcile all use it.
- `apps/zoom/services.py`:
  - **B1:** `reconcile()` now runs in at most two rounds (`RECONCILE_LOOKS = 2`). Each round reads the booking, takes its fingerprint, asks Zoom with no transaction open, then calls `_reconcile_locked()`.
    - `_reconcile_locked()` holds the one deadlock retry. Inside it, `_reconcile_once()` locks the request, the account and the classes, then recomputes the fingerprint from the locked rows **before** comparing or writing anything.
    - On a mismatch it raises `BookingChangedMeanwhile`. That rolls back the transaction, the `ZoomEvent` row included, and reconcile starts again with a fresh fingerprint and a fresh `GET`.
    - A second mismatch returns `LOCK_RACE`, with nothing changed. No HTTP runs under the locks.
    - `ReconcileResult.cause` names the exception class, for the webhook's one `ERROR` line. That's `BookingChangedMeanwhile` or `OperationalError`.
    - For a booking that isn't approved, the classes are read without `FOR UPDATE`, only for the fingerprint. Every change takes the request lock first.
  - **N2:** a `NOT_ASKED` outcome (`"not_asked"`).
    - `sync_message()` maps it to the error `NOTHING_LEFT_TO_CHECK`.
    - `handle_event()` answers it, and records it, as `no_change`. That's the echo of a cancelled booking, as before.
    - The `ZoomEvent` row's outcome is still `no_change`.
  - **N1:** `@sensitive_variables("event")` on `handle_event`, and `("event", "payload", "item")` on `_event_meeting_id`.
  - **N5:** `EventResult.reference` is removed.
  - **N6:** `absolute_url()` reads `settings.USE_HTTPS`.
  - **N4:** `cancel()` and reconcile call `classes_still_on()`.
- `apps/zoom/providers.py` (**S1**, criterion 31): when the live `meeting_state()` gets a 3001, it makes `GET /users/{host_account.email}` on the same client (006's Check connection call) before returning `None`.
  - A 1001 raises `ZoomUserNotFound`; any other failure raises its own `ProviderError`. Either way the booking is "couldn't be checked": the webhook answers 503, the button shows criterion 18's error row, and the command prints its couldn't-be-checked line.
  - A normal answer makes no user call.
- `apps/zoom/webhooks.py` (**S2**): `read_event()` also requires `payload` to be an object, so a bad shape gets 400 `UNREADABLE` before the account check runs. It's now `@sensitive_variables("body", "event")`.
- `apps/zoom/management/commands/sync_zoom_bookings.py`:
  - **N3:** each booking is checked inside its own `try`. An unexpected exception logs one `ERROR` (the reference and the exception class), prints `{reference} ({label}): couldn't be checked: {ExceptionClass}.`, counts towards `{f}`, and the run carries on.
  - `NOT_ASKED` prints no line and counts as nothing.
- `config/settings/base.py` (**N1**, that one comment only): the `ADMINS` warning now also names Zoom webhook bodies.
- Tests:
  - `synckit.py`: `add_user()`, `user_gets()` and `USER_URL`. `add_meeting(status=404)` now also registers a found host user by default (`user_found=False` turns that off).
  - `test_sync_race.py`: criterion 30's three thread tests on committed data:
    - an app move between the webhook's `GET` and its lock;
    - an app cancel in the same gap;
    - two app moves in a row, giving a 500 and no row.
    - **All three were seen to fail with the re-check turned off** (`sync_fingerprint` temporarily returned a constant, which matches the pre-fix code): a false `… directly in Zoom` email, a false `isn't booked here` flag, and 200 instead of 500. They pass with it on, and three runs in a row were stable.
    - The cancel-echo test registers the host-user answer.
  - `test_sync_double_check.py` (new, criterion 31):
    - a wrong-account 3001, through reconcile, the webhook (503, no row), the button (the pinned flash) and the command (its line, exit 1);
    - the user check timing out (`no answer from Zoom`), through all four;
    - a real deletion;
    - a normal answer making no user `GET`.
  - `test_webhook.py`:
    - **S2:** the four bad `payload` shapes (missing, a string, a list, `null`) each get 400, with no `wrong account` record and no row;
    - **N1:** an `ExceptionReporter` test shows `event` masked in `handle_event`'s frame, and no join link anywhere in the report.
  - `test_sync_command.py`:
    - **S3:** the lock-race line, counted in `{f}`, with exit 1. That's tested both mocked and from two real fingerprint mismatches, which make two `GET`s.
    - **S3:** `The email to the IT desk didn't send.`, using a failing email backend.
    - **N3:** a `RuntimeError` in one booking of three gives one line, `{f}` = 1, exit 1, one `ERROR` record, and no exception text in the log.
    - `NOT_ASKED`.
  - `test_sync_views.py`:
    - **N2:** the booking's class begins between the view's check and `reconcile()`, giving the `There are no classes left…` flash with no Zoom call;
    - two fingerprint mismatches give `MOVING_AT_THE_SAME_MOMENT`.
  - `test_sync_models.py`: `classes_still_on`; the source scan (criterion 21: the rule appears once, in `models.py`, and `services.py` calls the method twice); and `sync_fingerprint`, including no query, ignoring order, and differing on a move, a cancel, a length change or a status change.
  - `test_reconcile.py`: the two "asks Zoom nothing" tests now expect `not_asked`, and the `NOT_ASKED` flash is added to the pinned-message test.

**Context contract: unchanged.** No template, context key or URL changed, and every message reuses an existing pinned text.

**Migrations:** none. `sync_fingerprint` and `classes_still_on` are methods, not columns.

**Dependencies and settings:** no new dependency. The only settings change is N1's comment in `base.py`.

**Decisions to review**
1. **The S1 check lives in the provider**, inside `ZoomProvider.meeting_state()`. All three triggers reach Zoom only through it, so a 3001 can't skip the check. It reuses the call's own client, and runs before any lock. The fake provider isn't changed; tests steer it directly.
2. **On the second run, the deadlock retry and the fingerprint re-ask are separate**, as criterion 30 says. So a reconcile makes at most two meeting `GET`s, plus the user check on a 3001.
3. **The webhook's lock-race `ERROR` line** now names `BookingChangedMeanwhile` or `OperationalError`, using `ReconcileResult.cause`, where it used to always say `OperationalError`.

**Self-check output** (dev container on 8011, 2026-11-02):
- `ruff format .`: `1 file reformatted, 125 files left unchanged`. Then `ruff check .`: `All checks passed!`, and `ruff format --check .`: `126 files already formatted`.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `python manage.py check`: `System check identified no issues (0 silenced).`
- `python manage.py check --database default`: `System check identified no issues (0 silenced).`
- The thread tests (`test_sync_race.py`, `test_cancel_race.py`, `test_move_race.py`), run twice more: `19 passed` each time.

backend pytest run finished: `pytest --create-db -p no:randomly -rN` → `1504 passed in 88.74s (0:01:28)`, exit 0.

### tmd-frontend (agent plan step 3b, Design D.11), 2026-10-30

Built from Design D.1–D.12, the amended `docs/design/class-rows.md` and `busy-button.md`, and the context contract. Every pinned string is used verbatim; every message from the backend is printed as given (no message text was written here). No Python was touched.

**Files changed**
- **New** `templates/zoom/partials/attention_tag.html` (D.3.1): `span.tag.tag--warn`, `alert-triangle`, `Needs a look`. Takes no context; the caller keeps the condition (`{% if link_request.zoom_attention %}`).
- **New** `templates/zoom/partials/sync_form.html` (D.1.4): the one `Check against Zoom` POST form to `zoom:sync`, `button--secondary`, busy-button hooks with `Checking with Zoom…`. Both callers include it `with link_request_pk=link_request.pk csrf_token=csrf_token only`, so `{% csrf_token %}` prints a token (checked: the rendered form carries `csrfmiddlewaretoken`).
- `templates/zoom/detail.html`:
  - the `Changed in Zoom: needs a look` notice (`notice--warn`, `id="zoom-attention"`) straight after `{% block content %}`, before `approve_error`, when `zoom_attention_lines`. The lines are a `ul.break-anywhere`, auto-escaped. With `can_sync` it shows criterion 15's pinned next step and the sync form; otherwise D.1.3's design-copy step without the button;
  - the cancelled line's Zoom form, chosen by `link_request.cancelled_in_zoom` (criterion 27): `This booking was cancelled directly in Zoom. The change was copied here on {when}. It was approved by {decided_by} on {when}.` 011's form is unchanged in the `else`;
  - the `Needs a look` tag in the Status row, after the status tag and before `Recording`, when `link_request.zoom_attention`;
  - the `Check against Zoom` box (h2 `sync-title`, D.1.4's lead, the sync form) straight after Classes, when `can_sync and not zoom_attention_lines`. So exactly one button per page, before the move-series and cancel boxes;
  - header comment gains `zoom_attention_lines`, `can_sync`, `cancelled_in_zoom`, `zoom_attention`, `moved_in_zoom`, `csrf_token` and the two new partials.
- `templates/zoom/partials/class_rows.html` (D.1.5): `{% if occurrence.moved_in_zoom %}Moved directly in Zoom. Copied here on {when}.{% elif occurrence.moved_at %}`012's note`{% endif %}`, and the same shape for `cancelled_in_zoom` / `Cancelled directly in Zoom. Copied here on {when}.` (no reason after it). No template test on `*_by`. Order kept: moved note, then cancelled note. Header comment updated.
- `templates/zoom/queue.html` (D.3.2, D.3.3): the Status cell's wrapper is now `span.tags`, with the tag after the status tag; the Cancelled tab's empty state reads `Bookings show here when they're cancelled, here or directly in Zoom.` Header comment updated.
- `templates/zoom/account_form.html` (D.4.1, criterion 29): inside the `ready` branch of `Zoom connection`, `{% if webhook_secret_set %}` adds the second `p` to `Set up` (`Last heard from Zoom on {when}` through `zoom/partials/when.html`, or `Nothing heard from Zoom yet.`), and `{% if webhook_secret_set is False %}` adds the `Changes made in Zoom aren't seen here` warn notice after `Set up`, with `{{ zoom_connection_name }}` (the stored name) in `span.break-anywhere`. `None` (or the variable missing) shows nothing new. Header comment updated.
- `templates/zoom/email/cancelled_body.txt` and `moved_body.txt` (D.5.1, D.5.2, criterion 16): `in_zoom` branches for the opening sentence; the cancel email adds `If you didn't expect this, reply to the IT desk.` plus a blank line after `Reason:` only with `in_zoom`. Header comments gain `in_zoom`.
- **New** `templates/zoom/email/attention_subject.txt` and `attention_body.txt` (D.5.3), reading `link_request.reference`, `class_name`, `requester_name`, `host_account.label`, `lines` and `detail_url` (G8).
- **CSS, JS, icons, static files:** none (D.11). Every class used already exists; `alert-triangle` is in the sprite.

**Spec deviations:** none.
- One placement note: the Check against Zoom box sits directly after the Classes `section`, outside the `{% if link_request.status == "approved" %}` block that holds the move and cancel boxes. `can_sync` already implies approved, and `can_decide` is false for an approved request, so the rendered order is D.1.1's (Classes, Check against Zoom, Change the time…, Cancel this booking).

**Context contract gaps:** none found. Two notes for the backend and verifier:
- Until the backend's `Occurrence.moved_in_zoom` / `cancelled_in_zoom` and `LinkRequest.cancelled_in_zoom` exist, a missing property reads as false, so a row would fall back to 011/012's `… by None …` form. Criterion 27's "no `by None`" test therefore depends on those properties, not on any template guard.
- `account_form.html`'s new markup is nested inside the existing `zoom_connection_state == "ready"` branch. That matches the contract (`webhook_secret_set` is `None` unless the stored connection is `ready`), so a `False` with any other state would show nothing.

**Self-check output**
- Stub-context render script (dev container, `config.settings.dev`, a stub URLconf adding `zoom:sync` while the backend's route didn't exist yet): **55 checks, 0 failures.** They cover:
  - the notice (title, two escaped `li`s, pinned step, button inside it, exactly one `Check against Zoom</button>` on the page, notice before the approved line), the no-`can_sync` variant (design-copy step, no button);
  - the sync form (action `/zoom/requests/42/sync/`, a CSRF token inside it, the busy hooks);
  - the Status-row tag order (`Link sent`, `Needs a look`, `Recording`), and no tag without `zoom_attention`;
  - the box (lead, one button, after Classes and before `Cancel this booking`), and no box or button without `can_sync`;
  - class rows: both Zoom notes in `<time datetime>`, no reason repeated, 012's and 011's app-made notes unchanged, a class moved by IT then cancelled in Zoom keeps the note order, and no `by None` anywhere;
  - the cancelled-in-Zoom line, and 011's cancelled line unchanged;
  - the queue's `span.tags` on every row, the tag on the flagged row only, and the Cancelled empty state;
  - the account page in all three states plus a missing variable (exact pinned texts, the warn notice after `Set up` and before the connection-name field, nothing new for `None`);
  - emails: `cancelled_body.txt` and `moved_body.txt` rendered **byte-identical** to their `HEAD` versions with `in_zoom` absent and `False`, across `remaining` × `can_start` (cancel) and `can_start` (move); with `in_zoom=True`, D.5.1's and D.5.2's rendered examples match exactly, the plural (`2 classes … were`) and whole-booking forms are right, and neither contains `The IT desk has`; the IT subject renders `Needs a look: ZL-0042 was changed in Zoom` and the body matches D.5.3's rendered example exactly, with autoescape off.
- First HTTP pass on **8011**, before the backend's context existed (dev stack, signed in as a dev superuser through a temporary session, deleted afterwards): `200` for `/zoom/requests/`, `?status=cancelled` (new empty-state sentence present), `?status=approved`, `/zoom/requests/26/` (approved), `/zoom/requests/42/` (waiting), `/zoom/accounts/153/edit/` and `/zoom/accounts/13/edit/`. No page contains `by None`; no new markup appears without the backend's context, as intended.
- **`pytest --reuse-db apps/zoom apps/core -rN`** (dev container, run once, after the backend's "backend pytest run finished"; no `--create-db`): **`1296 passed in 90.53s`, exit 0.**
- **Second HTTP pass on 8011, against the backend's real views** (2026-11-02):
  - **Setup, all throwaway:**
    - The dev `web` was recreated on 8011 with a compose override file kept in the agent's scratchpad, never in the repo. It added two dummy credential sets through `environment`: `tmdfe-with` (with a dummy webhook secret) and `tmdfe-without` (none). `.env` and `zoom-credentials.env` weren't touched.
    - Rows, all named `TMDFE…`: three accounts (`tmdfe-with`, `tmdfe-without`, and one with no connection).
    - Three bookings, made with the tests' `make_request`/`booked_on` helpers:
      - a weekly booking with two `zoom_attention` lines, one holding `<Grade 10>`;
      - a weekly booking with one class moved in Zoom, one cancelled in Zoom, and one moved by a user;
      - a one-off cancelled in Zoom.
    - `booked_on(by=None)` leaves `decided_by` empty. That printed `approved by None` on the first run, which is a data artefact, since a real approval always has a decider. It was fixed in the data, not the template.
  - **Results: 35 checks, 0 failures**, all `200`.
    - **Detail, needs a look:**
      - the notice has its title, two escaped `li`s, the pinned step, and the button inside it;
      - there is exactly one `Check against Zoom` button, and no box;
      - the sync form carries a `csrfmiddlewaretoken`;
      - the Status row shows `Link sent`, then `Needs a look`.
    - **Detail, nothing flagged:**
      - no notice and no tag;
      - one button, in the box between Classes and `Cancel this booking`;
      - both Zoom notes, plus the app-made `Moved by … on …` note.
    - **Detail, cancelled in Zoom:**
      - the `This booking was cancelled directly in Zoom. The change was copied here on …` line;
      - no button and no tag.
    - **Queue** (`?status=approved` and `?status=all`):
      - the flagged row has `Link sent` and then `Needs a look` inside `span.tags`;
      - the unflagged row has no tag;
      - `?status=cancelled` returns `200`.
    - **Account change page:**
      - `True`: the `Set up` notice gains `Changes made directly in Zoom are copied here. Nothing heard from Zoom yet.`. There is no warn notice, and the dummy secret doesn't appear in the page;
      - `False`: the exact warn title and body naming `tmdfe-without`, and no copied-here paragraph;
      - `None`: an account with no connection, and also the add page, shows nothing new.
      - The `Last heard from Zoom on {when}` variant wasn't produced over HTTP, because no `ZoomEvent` row was made. It's covered by the stub render above and by the backend's criterion 29 tests.
    - `No rendered page contains by None` holds on all three detail pages.
  - **Pressing `Check against Zoom`** (a real POST using the page's token and a cookie jar): `302` to the detail page, then the backend's flash, printed as given: `We couldn't check with Zoom: no answer from Zoom. Try again in a few minutes.` The fake provider has no meeting under the dummy ID. This proves the `csrf_token=csrf_token` pass-through works: the press isn't a 403.
  - **Cleanup:**
    - Deleted: 3 requests, 7 classes, 252 slots, 3 accounts, 0 `ZoomEvent` rows and the session. A recount found 0 `TMDFE` rows left.
    - The dev `web` was recreated without the override, so it's back to `polymath-tmd:dev`, `fake`, `config.settings.dev`, with no credential sets. `/healthz/` returns 200 on 8011.
  - **For the main session:** `talentlink-web-1` and `talentlink-db-1` (port 8010, the other project) were found `Exited (255)`, with their worker and scheduler restarted at the same moment. That looks like a Docker restart. This agent only ran compose commands for the `polymath-tmd` project and didn't start or stop them.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS** (2026-11-02; criterion 26, the owner's live check, is still pending by design)

**Checklist:** ruff ✅ | format ✅ (125 files) | `pytest --create-db` ✅ twice, 1483 passed each (70 s, 68 s) | sync, webhook, reconcile, race, command and model modules, 3 more runs ✅ (161 passed each) | makemigrations ✅ none | check ✅ | `check --database default` ✅ (dev, fake: no issues) | `check --deploy` (prod, `USE_HTTPS=True`) ✅ | prod HTTP ✅

**Not exercised live:** Zoom itself (dummy credentials only; no network). On the dev stack the fake provider's real bookings sit on accounts with no connection name, so `sync_zoom_bookings` there printed only `Checked 0 bookings: 0 changed, 0 need a look, 0 couldn't be checked.` (exit 0). The button, notice and every command line are proven by the committed tests plus the frontend's 35 HTTP checks.

**`check --deploy` and `zoom.W002`** (prod container, `USE_HTTPS=True`, dummy sets via `exec -e`):
- `ZOOM_PROVIDER=zoom`, with and without a webhook secret: only `security.W021` (W002 is database-tagged).
- `manual`: `security.W021` and `zoom.W001`.
- `check --database default`, a set named for an account, **without** a secret: `zoom.W002 polymathlesson Paid's Zoom connection has no webhook secret, so changes made directly in Zoom to its meetings aren't seen here.` With a secret: W002 is gone. Under `manual`: no issues.

**Live webhook, prod image on 8011** (`ZOOM_PROVIDER=manual`; dummy set `tmdv-01` passed through an override file in the scratchpad that holds only `${VAR}` references, with the values exported inline; nothing was written to disk):
- GET → 405.
- Unsigned POST → 401, empty body.
- Wrong signature → 401.
- Timestamp 301 s old → 401; 301 s ahead → 401.
- Wrong `account_id` → 401.
- Unknown slug → 404 (Django's standard page; the project has no custom 404 template).
- Signed `meeting.deleted` → 200, then a repeat → 200, with one `ZoomEvent` row (`ignored`, as D13 says for `manual`).
- Validation challenge → 200, and `{"plainToken": p, "encryptedToken": hex(HMAC-SHA256(secret, p))}` was checked to be exactly equal.
- Validation token `v0:1:{}` → 400.
- Body over 256 KB → 413.
- Log counts: the app's own loggers gave one `WARNING` per refusal with only the slug and the reason word (`missing`, `bad signature`, `stale`, `wrong account`, `too large`), and `INFO` only for the unknown slug. `django.request` lines carry the path only.
- **Grep of the prod container logs for the webhook secret, client secret, any `v0=<hex>` signature, the validation token and the test password: 0 hits.**

**Prod UI under `manual`** (throwaway superuser, deleted afterwards along with the `tmdv-01` event row):
- Anonymous detail → 302 to sign-in; anonymous POST to `zoom:sync` without a CSRF token → 403.
- Queue, Cancelled tab, approved detail and both account change pages → 200; no `Check against Zoom`, no `Needs a look`, no webhook text and no `by None` anywhere.
- `zoom:sync`: GET → 405; POST on an unapproved request → 404; POST without a CSRF token → 403; POST on an approved booking under `manual` → 302 with the pinned error `This system can't reach Zoom, so it can't check this booking.`
- Saved HTML audit (detail, queue, account page): one `h1`, skip link, one `main`, nav landmarks, no `<img>` without `alt`, every visible input has a `<label for>`.

**Criteria → tests** (all passing in the 1483):
- 1: `apps/core/test_zoom_settings.py`.
- 2: `test_zoom_accounts_connection.py` and `test_sync_models.py` (W002), plus the live runs above.
- 3: `test_webhook.py::test_the_address_is_one_per_connection`, `test_get_is_405`, `test_the_webhook_is_the_only_view_without_csrf_protection`, `test_other_posts_still_need_a_csrf_token`.
- 4: `test_a_name_with_no_webhook_secret_is_404_and_logs_nothing_above_info`, `test_over_256_kb_is_413_before_the_body_is_read`, `test_a_real_body_over_256_kb_is_413`.
- 5: `test_every_refusal_is_401_empty_with_one_warning` (each header missing, one character off, one byte changed), `test_the_window_is_300_seconds_either_way`, `test_a_body_signed_with_another_sets_secret_is_refused`.
- 6: `test_url_validation_answers_exactly_with_no_query_and_no_http`, `test_a_validation_token_outside_the_safe_characters_is_400`, `test_an_unsigned_validation_is_refused`.
- 7: `test_an_event_from_another_zoom_account_is_401`.
- 8: `test_a_repeat_is_200_with_no_zoom_call_no_change_and_no_email`, and `test_sync_race.py::test_two_deliveries_at_once_reconcile_once_and_email_once`.
- 9: `test_other_events_are_recorded_ignored`, `test_the_manual_provider_records_meeting_events_ignored_and_asks_zoom_nothing`.
- 10: `test_a_handled_event_is_200_and_its_row_holds_the_outcome`, `test_zoom_unreachable_is_503_and_keeps_no_row`, `test_any_other_failure_is_500_with_one_error_line_and_no_row`, `test_a_lock_race_is_500`, `test_a_signed_body_that_isn_t_an_event_is_400`.
- 11: the `ZoomEvent` field list and the secret-name test (005 c46).
- 12: `test_a_meeting_with_no_booking_here_is_not_ours_with_no_zoom_call`, `test_a_booking_on_another_connection_is_never_touched`, `test_a_waiting_or_rejected_request_is_never_matched`, `test_the_echo_of_a_whole_cancel_made_here_changes_nothing`.
- 13: `test_sync_race.py::test_zoom_is_asked_with_no_transaction_open_from_the_webhook_and_the_button`.
- 14, 15, 16: `test_reconcile.py` (table, held classes, rebuilt series, type-3, flag survival, `in_zoom` renders).
- 17: the three `test_the_echo_of_…` tests, and `test_sync_race.py::test_a_webhook_during_a_cancel_waits_then_finds_nothing_to_do`.
- 18: `test_sync_views.py` (one test per row, the forced double 1213, both G4 cases, 404, 405, permissions).
- 19: `test_sync_command.py` (every pinned line, both summaries, exit 1, `manual`, skipped accounts).
- 20: `test_no_log_record_holds_a_secret_a_signature_the_body_or_a_link` (all loggers), `test_the_view_and_the_verifier_mask_what_they_hold`, and the live log grep.
- 21: `verify()` is one function; the view only maps results.
- 22: `test_sync_views.py` rendering tests, plus the frontend's HTTP pass.
- 23: the root `conftest.py` network block.
- 24: the runs above.
- 25: the walkthrough above. The three-state account page (`webhook_secret_set` true, false and `None`) is `test_the_three_states_of_the_account_page`; it could not be shown over HTTP on prod, because that needs a `ready` connection to a live Zoom. The frontend showed it on dev. **Screenshots done (2026-11-02, dev stack on 8011, fake provider, dummy sets `tmdfe-with` / `tmdfe-without` via a scratchpad override of `${VAR}` references; Edge headless via playwright-core, full page, 1440 and 400 wide, no cropping at 400, no horizontal overflow, `scrollWidth` = viewport on all 14):** `scratchpad/crit25/` holds `detail_needs_a_look`, `detail_check_box_and_zoom_notes` (class rows with `Moved directly in Zoom` and `Cancelled directly in Zoom`, plus the Check against Zoom box), `detail_cancelled_in_zoom`, `queue_tag`, `account_secret_true`, `account_secret_false` and `account_none`, each `_1440.png` and `_400.png`. Viewed: needs-a-look notice with button, tag in the Status row, both Zoom notes, the warn notice with the pinned text on the account page. Seeded-data artefacts, not product faults: `approved by None` (the test helper approves with no decider) and `Every , 8:30 am` (weekday code in the seeded booking). Throwaway data deleted (3 accounts, 3 bookings, session), dev stack restored.
- 26: **pending** (the owner's live check).
- 27: `test_sync_models.py` (the three properties in all four combinations) and `test_no_detail_page_says_by_none_after_changes_copied_from_zoom`.
- 28: `test_the_sweep_clears_a_flag_whose_classes_have_all_been_held_in_one_update`, `test_the_sweep_keeps_the_flag_of_a_booking_with_classes_left`, and the cancel tests in `test_sync_models.py`.
- 29: `test_the_three_states_of_the_account_page`, `test_none_where_there_is_nothing_to_say`, `test_two_accounts_on_one_connection_show_the_same_last_heard`, `test_the_account_page_costs_at_most_one_query_more`, `test_no_page_shows_the_webhook_secret`.

**Tests added by the verifier:** none. The existing tests already pin every webhook-security item in the request, and I found no gap.

**Observations, not failures:**
- Unauthenticated POST to `zoom:sync` gets 403 (CSRF) before the sign-in redirect. That is Django's normal order.

**Stack:** restored to dev on 8011 (`polymath-tmd:dev`, `fake`, no credential sets, `/healthz/` 200). Prod web restart used scratchpad override only; `.env` untouched; the talentlink containers were not touched.

### Re-verification (fix cycle 1), 2026-11-02

**Verdict: PASS** for criteria 1–25, 27–29 and the new 30 and 31, and for the amended 10 and 18–21. Criterion 26 (the owner's live check) stays pending.

**Checklist:** ruff ✅ | format ✅ (126 files) | `pytest --create-db` ✅ twice, 1504 passed each (88 s, 94 s) | race and thread modules (`test_sync_race`, `test_sync_double_check`, `test_cancel_race`, `test_move_race`, `test_race`, `test_zoom_race`), 3 more runs ✅ (35 passed each) | makemigrations ✅ none | check ✅ | `check --database default` ✅ | `check --deploy` not re-run (only a comment in `base.py` changed; prior run stands) | prod HTTP ✅.

**Mutation spot-checks** (product code temporarily edited, then restored from a copy):
- **B1** (criterion 30): `sync_fingerprint` made to return a constant → the three thread tests failed: `test_a_move_made_here_between_the_get_and_the_lock_is_kept`, `test_a_cancel_made_here_between_the_get_and_the_lock_is_kept`, `test_two_changes_in_a_row_are_a_lock_race_that_changes_nothing` (3 failed, 4 passed).
- **S1** (criterion 31): the user `GET` removed on a 3001 → 6 of 7 tests in `test_sync_double_check.py` failed, including `test_a_3001_from_the_wrong_account_cancels_nothing`, the 503-with-no-row, pinned-flash and command-line tests, and the failed-user-check test.
- **Restored:** an md5 of every `apps/zoom/*.py` taken before the mutations matches after (`RESTORED_IDENTICAL`, and again `CODE_UNCHANGED` at the end). `git diff` can't show this alone because the work isn't committed. Both modules pass again (14 passed).

**Live on the prod image, 8011** (`ZOOM_PROVIDER=manual`, dummy set `tmdv-01`, values through exported variables and a scratchpad override of `${VAR}` references only):
- Signed body with no `payload` → 400, empty. Also `payload` as a string, `payload` as `null`, and no `event` → 400, empty.
- Signed `meeting.updated` with a good `account_id` → 200, one `ZoomEvent` row (`ignored`, as D13 says for `manual`); row deleted afterwards.
- Signed body with a wrong `account_id` → 401, one app `WARNING` (`refused: wrong account`).
- **Grep of the prod logs for the webhook secret, client secret, account id and any `v0=<hex>` signature: 0 hits.**
- **S1 over HTTP not exercised:** a 3001 needs the `zoom` provider talking to Zoom's real hosts (fixed in `zoom_api.py`), and there is no network. It rests on the mutation check and the four-trigger tests above.

**Cleanup:** throwaway row deleted; dev stack restored on 8011 (`polymath-tmd:dev`, `fake`, no `ZOOM_S2S_*`, `/healthz/` 200). `.env` untouched; talentlink untouched.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-11-02 (verifier PASS on 28 of 29; criterion 26 pending the owner)

**Verdict: CHANGES REQUESTED.**

**Blocker**

**B1. A stale Zoom answer can undo a change the app just committed.**

Where: `services.py:2239` (the GET, made with no lock) and `services.py:2299` (the lock, taken afterwards). Nothing checks whether the booking changed between the GET and the lock.

How it happens:
1. A webhook or a button press does its GET.
2. IT's `move_class()` locks, PATCHes and commits.
3. The reconcile takes the lock and copies the old Zoom time back, with `moved_by=None`.
4. The requester gets an email saying the class was "changed directly in Zoom".

A class cancelled in the app at that moment gets a false flag and an IT email instead. Criterion 17's thread test only covers the opposite order.

Fix:
- Fingerprint the booking before the GET: status, plus each class's `(pk, starts_at, ends_at, cancelled_at)`.
- Recompute the fingerprint under the locks. If it differs, roll back, ask Zoom again once and retry. If it differs a second time, return `LOCK_RACE`: the button shows 012's message, the webhook answers 500, and the command prints a couldn't-be-checked line.
- Add a thread test with a move landing between the GET and the lock.
- Owner: backend. The planner adds a dated note to D1.

**Should fix**

**S1. A "gone" answer from the wrong Zoom account would cancel a whole account's bookings.**

Where: `providers.py:803` and `sync.py:89`.

Zoom answers 3001 for a meeting that belongs to another Zoom account. If `credential_set` is edited, or the credentials are swapped, the nightly run would cancel every remaining class on that account and email every requester. Nothing can undo that.

Options:
- (a) Refuse a `credential_set` change while the account still has booked classes.
- (b) On a 3001, confirm the host user exists on that connection before treating the meeting as gone. If the host user isn't found, count the booking as couldn't-be-checked.

Owner: planner rules, backend builds.

**S2. Criterion 10's 400 is only half built.**

Where: `webhooks.py:133-141`.

A body with `event` but no `payload` object gets a 401 and a misleading `wrong account` WARNING.

Fix: also require `isinstance(event.get("payload"), dict)`, and add the test case. Owner: backend.

**S3. Two of criterion 19's pinned command lines have no test.**

The lock-race line (and its count and exit code) and `The email to the IT desk didn't send.` are untested. Owner: backend.

**Nits**
- **N1.** `services.py:2447`: `handle_event`'s parsed body holds join links in an unmasked local. Add `@sensitive_variables("event")`, and mention webhook bodies in the ADMINS warning comment in `base.py`.
- **N2.** `services.py:2195` and `services.py:2302`: if the booking has nothing left to check by the time `reconcile()` runs, the button can claim "matches Zoom" without having asked Zoom. Return a distinct "not asked" outcome, mapped to `NOTHING_LEFT_TO_CHECK`.
- **N3.** `sync_zoom_bookings.py:98-99`: one unexpected exception stops the whole nightly run. Catch it per booking and count that booking as couldn't-be-checked.
- **N4.** `services.py:1081` and `services.py:2354`: the "still on" rule is written twice. Make it one model method, next to `remaining_classes`.
- **N5.** `services.py:2146`: `EventResult.reference` is never read. Remove it.
- **N6.** `services.py:2952`: use `settings.USE_HTTPS` directly instead of `getattr(...)`.

**Sound**
- **Webhook verifier:**
  - It's built from pure functions, and the HMAC is computed over the raw body and compared in constant time.
  - The 413 check runs before the body is read, and the body is read only once the slug is known.
  - The timestamp must be digits only, and the validation token's characters are restricted, so a validation reply can't be turned into a signed forged event.
  - Each refusal is logged as a single word.
  - This is the only `csrf_exempt` view in the app.
- **Idempotency:** the `ZoomEvent` insert happens in the same transaction as the booking changes, and its unique key serialises duplicate deliveries without adding a lock cycle.
- **Model properties and shared helpers:** the G1 properties are correct, and so are the helpers shared with 011 and 012.
- **Settings, migration and command:** settings masking, the migration 0009 reversal, the one-`UPDATE` sweep and the absence of N+1 queries all check out.
- **Templates:** they decide nothing, and the `in_zoom` variants leave 011's and 012's text unchanged.
- **Dependencies:** only the standard library.

### Round 2 — 2026-11-02 (after fix cycle 1; verifier re-verification PASS, criterion 26 pending the owner)

**Verdict: APPROVE.**

Every round-1 finding (B1, S1–S3, N1–N6) is fixed in the code, and each has a test that fails without its fix. The fix cycle adds no blockers and nothing that must be fixed. `ruff check .` and `ruff format --check .` (127 files) are clean.

**How round 1 was fixed**
- **B1:**
  - **Fingerprint:** `LinkRequest.sync_fingerprint()` (`models.py:1202-1219`) is taken before the `GET` (`services.py:2259-2261`).
  - **Compared under the lock:** `_reconcile_once` recomputes the fingerprint under 011's lock order (2373-2374), before `sync.compare` and before any write.
  - **Re-ask once:** a mismatch asks Zoom one more time (`RECONCILE_LOOKS = 2`). A second mismatch returns `LOCK_RACE` / `BookingChangedMeanwhile` with nothing changed. This stays separate from the 1213 deadlock retry.
  - **Tests:** three committed-data thread tests in `test_sync_race.py:243-326`. The verifier's mutation check showed they catch the race.
- **S1:**
  - **Where the check runs:** `meeting_state()` (`providers.py:810-816`) makes `GET /users/{email}` on a 3001, before it returns `None`.
  - **When the check fails:** a 1001 or any other failure surfaces as `PROVIDER_FAILED` before any lock is taken.
  - **Coverage:** all three triggers go through this one method. `test_sync_double_check.py` covers every case in criterion 31.
- **S2:**
  - **Fix:** `read_event()` requires `payload` to be a dict (`webhooks.py:146-151`), and this check runs before `is_from_account`.
  - **Tests:** missing, string, list and `null` payloads are all tested.
- **S3:** the lock-race line (its count and exit code 1) and the failed-IT-email line are both tested (`test_sync_command.py:138-182`).
- **N1:** `@sensitive_variables("event")` is on `handle_event` and `_event_meeting_id`, and the `ADMINS` comment is updated. An `ExceptionReporter` test is added.
- **N2:**
  - **Outcome:** `NOT_ASKED` is a distinct outcome, mapped to `NOTHING_LEFT_TO_CHECK`.
  - **Webhook:** it records `NOT_ASKED` as `no_change`.
  - **Test:** a view test moves the clock and asserts no Zoom call is made.
- **N3:** each booking in the command is checked in its own `try`. A failure logs one `ERROR` naming only the class, with no exception text, and is tested.
- **N4:** `classes_still_on()` is shared by `status_after_cancel`, `cancel()` and reconcile, and a source-scan test checks this.
- **N5:** `EventResult` holds only `outcome`.
- **N6:** `settings.USE_HTTPS` is read directly.

**Nits** (optional; none blocks; not taken up in 013):
1. **Unreachable checks:** `webhooks.py:163-164` and `:179-180`. The `isinstance(payload, dict)` checks can no longer fail now that `read_event` guarantees a dict. Owner: backend.
2. **Unused fixture:** `test_sync_command.py:216`. `monkeypatch` is requested but never used. Owner: backend.
3. **A third copy of the "still on" rule:** `models.py:1416-1417`.
   - 011's `start_state` builds `to_come` with the same rule as `classes_still_on()`.
   - The N4 scan's regex misses it.
   - Optional fix: `to_come = self.classes_still_on(now, occurrences=booked)`.
   - Owner: backend.
4. **Repeated wording:** `sync_zoom_bookings.py:39`. `LOCK_RACE_REASON` repeats the first sentence of `services.MOVING_AT_THE_SAME_MOMENT`. It's pinned as built (D15), so this matters only if that text changes.

**Sound:**
- **The fingerprint check:** it runs under the lock and before any compare or write, with one re-ask and no HTTP under a lock.
- **The thread tests:** they commit the app's change inside the mocked `GET` callback, so the race is real, not simulated.
- **The S1 double-check:** it lives in the single live `meeting_state()`, so every trigger is covered by construction.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Status stays `Verifying`.** Verification is PASS (including the fix-cycle re-verification of 2026-11-02) and Review is APPROVE (round 2), so everything that can be checked here is done. The one thing open is criterion 26, the owner's live check against real Zoom: Marketplace validates the endpoint (and asks for no new scope), a class deleted and a one-off moved in Zoom are copied here, a clash gives `Needs a look` and the IT email, a cancel in the app sends exactly one email, `Last heard from Zoom` shows on the account page, and the requester emails say `directly in Zoom`. This follows 006, 011 and 012, which stay `Verifying` until their owner live checks, and the README's go-live gate, which lists 013 as "waiting on the owner's live check". It becomes `Done` once the owner reports criterion 26's results.

**Files updated**
- `README.md`:
  - new section "Keeping in step with Zoom": how the three triggers work, the server steps (D6, 0a–0c) and per-account Marketplace steps, the `endpoint.url_validation` handshake, how the endpoint is protected, "Last heard from Zoom", rotating a webhook secret, the `Check against Zoom` button, and the nightly command (how to schedule it, its output, exit codes 0 and 1, the `Zoom has no user …` line);
  - "three" `ZOOM_S2S_<NAME>_*` variables per account is now four (the fourth, `ZOOM_S2S_<NAME>_WEBHOOK_SECRET`, is optional), also in "Connecting an account to Zoom" step 8;
  - `ALLOWED_HOSTS`: the domain must be in it before Zoom can validate, and first (the nightly command's email links use it, D15);
  - the "changes made directly in Zoom aren't seen" known limit is marked resolved with its conditions, and the go-live gate's item 4 now reads "built, waiting on the owner's live check".
- `CLAUDE.md`: the `zoom` bullet (webhook, `reconcile()` as the one path with the fingerprint check D16 and the 3001 double-check D17, `ZoomEvent` idempotency, the one `csrf_exempt` view, where a change came from, `zoom_attention` clearing, `classes_still_on()`), and the Zoom-credentials gotcha (four variables, plus a note that brief 015 will later move them into the database, marked planned, not built). No section was deleted.
- `docs/CHANGELOG.md`: the 013 entry.
- Dated "Amended by 013" notes in earlier briefs: `docs/tasks/006-live-zoom-connection.md` (criterion 39, D13 and the "Webhooks" out-of-scope line), `docs/tasks/011-cancel-and-start-link.md` (criterion 17: the `in_zoom` email form, and `cancel()` clearing `zoom_attention`), and `docs/tasks/012-move-a-class.md` (criterion 18: the `in_zoom` email form).

**Not done on purpose:** the review's four optional nits are left alone, as instructed. The README's scope-name note stays "to be confirmed" until criterion 26 step 1 reports whether Marketplace asks for a scope; if it does, add its name to the README then.
