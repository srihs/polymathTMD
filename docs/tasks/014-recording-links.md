# 014 — Email the recording link when Zoom finishes a class recording

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Planned <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

The owner's words (2026-09-26):

> so what we need is zoom to linked via api or anyither means and create/cancel meetings via the app without user has to login to zoom app. This application will be the interface for zoom. Research on how to do this and ask questions if you have to.

The owner's scope answer (2026-09-26, relayed): "email recording links to the requester when `recording.completed` fires". Brief 011 has the full answers and the split.

**Reading.** Requesters can ask for a class to be recorded to the Zoom cloud (005 D18), and 006 switches automatic cloud recording on for those meetings. Today nobody sends the recording on: IT would have to sign in to Zoom, find it and share it.

With this brief, each account's Zoom app also sends `recording.completed` to 013's verified endpoint. The app then:

- works out which booking and which class the recording belongs to;
- asks Zoom for the recording's share link and passcode;
- emails them to the requester.

It keeps a small record that a recording was sent, never the link itself. IT sees it on the request's page and can send it again.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**Place in the split** (brief 011, Scope): last. It depends on 013's endpoint (signature, replay window, account check, idempotency).

**In scope**

- **Model** (migration `0010`): `RecordingNotice`.
- **`recording.completed` handling** inside 013's endpoint.
- **Provider:** `recording_share(*, host_account, meeting_uuid)` (`GET /meetings/{uuid}/recordings`).
- **Emails:** the requester's "recording ready" email, and an IT email when it couldn't be sent.
- **The request detail:** a `Recordings` box with `Email the link again`.
- **The Zoom scope** `cloud_recording:read:list_recording_files:admin`, and the event subscription (setup in D5).

**Out of scope**

- Changing recording sharing settings through the API (owner, Q7: "Each Zoom account's settings"; D7).
- Downloading, storing or re-hosting recordings. Transcripts and summaries.
- Recordings of meetings the app didn't book.
- Emailing anyone but the requester.
- Tracking whether the requester watched it.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- These carry over from 005, 006, 011 and 013: the frozen now, ZL-0042 (weekly, Zoom 02, meeting `81234567890`), mocked Zoom and the network block, **signed POST**, and the pinned-copy rule.
- **The example event:** `recording.completed` for meeting `81234567890`, `uuid` `aBc/12+==`, instance `start_time` Mon 5 Oct 2026 03:02 UTC (8:32 am Colombo). Mocked `GET /meetings/{uuid}/recordings` returns `share_url` `https://us02web.zoom.us/rec/share/SHARETOKEN`, `password` `Rp9#x2`, and a `download_access_token` `DLTOKEN`. The event payload carries `download_token` `PAYLOADTOKEN`.

### Model

1. **`RecordingNotice`** (migration `0010`, reversible):
   - `link_request` (FK, `PROTECT`);
   - `occurrence` (FK, null, `SET_NULL`);
   - `zoom_uuid` (`CharField` 100, **unique**);
   - `recorded_at` (the instance start, aware);
   - `created_at` (auto);
   - `emailed_at` (null: the last successful send);
   - `last_failed_at` (null).

   It stores **no** link, passcode or token. The 005 criterion 46 secret-name test passes.

### Receiving the event

2. **Subscribed and verified.** `recording.completed` goes through all of 013's checks (criteria 4–8): the signature, the window, the account, and the body-hash idempotency. It's no longer answered `ignored`.
3. **Which booking.** `payload.object.id` is matched among requests with status `approved` **or `cancelled`** (a held class's recording still matters after the rest was cancelled), on an account whose `credential_set` is the URL's slug.
   - No match → outcome `not_ours`, 200, no Zoom call.
4. **Which class.** The instance's `start_time` is matched to the booking's non-cancelled class whose `[starts_at − 30 minutes, ends_at)` contains it (011's window idea). The nearest `starts_at` wins if two match.
   - No match (the meeting was started outside any class) → `occurrence` is null, and the email names the recording's own date and time.
   - Tests: 8:32 am → the Mon 5 Oct class; 8:05 am → the same class; 11:40 am → none.
5. **One email per recording.** `zoom_uuid` is unique. A second `recording.completed` with a **different** body for the same `uuid` (Zoom can re-send after processing) creates no second notice and no second email, and its outcome is `no_change`.
6. **Ask Zoom, fresh.** The app calls `GET /meetings/{uuid}/recordings` with no transaction open.
   - The `uuid` is **double URL-encoded** when it starts with `/` or contains `//`, as Zoom's docs require (https://developers.zoom.us/docs/api/meetings/). The backend confirms and records it. The test's `aBc/12+==` is encoded as the docs say, and asserted in the recorded URL.
   - Only `share_url` and `password` are read.
   - `share_url` must be `https` on `zoom.us` or a subdomain, or it's treated as `ZoomUnavailable`.
   - Any 006 error → **503**, and no `ZoomEvent` row is kept (013 criterion 10), so Zoom's retry sends it.
7. **Then, in one transaction:** the `ZoomEvent` row and the `RecordingNotice` are written, and committed. **After the commit**, the email is sent and `emailed_at` or `last_failed_at` is set.

### The emails

8. **To the requester only**, plain text, no cc or bcc.
   - **Subject:** `Recording ready: {reference} {class_name}`
   - **Body:**
     ```
     Hello {requester_name},

     The recording of your class on {Mon 5 Oct 2026, 8:30 am to 11:30 am} is ready.

     Watch it here: {share_url}
     Passcode: {password}

     Share the link and passcode only with your students. The IT desk's Zoom settings decide how long the recording stays available.

     Polymath College IT desk
     ```
   - With no class matched, the date line reads `of your meeting on {Mon 5 Oct 2026} at {8:32 am}`.
   - With no passcode from Zoom, the passcode line is left out, and the next line starts `Anyone with the link can watch it. Share it only with your students.`
   - It **never** contains a download URL, `download_token`, `download_access_token`, `play_url`, or the join link. A test searches for `DLTOKEN`, `PAYLOADTOKEN` and `/download`.
9. **When the email fails:** `last_failed_at` is set. One email goes to every IT recipient (005 D9), subject `Recording link didn't send: {reference}`, body `The recording of {class} is ready, but the email to {email} didn't send. Open {detail URL} and press Email the link again.` It contains **no** share link or passcode.
10. **Nothing is kept.** Across a received event and a resend, with `DEBUG` logging captured: `SHARETOKEN`, `Rp9#x2`, `DLTOKEN` and `PAYLOADTOKEN` appear in no log record, no `zoom_*` table dump, no cache entry and no message. `SHARETOKEN` and `Rp9#x2` appear only in the requester's email. The provider method and the handler are `@sensitive_variables` for the answer and the payload.

### The request detail

11. **A `Recordings` box** on an approved or cancelled booking with at least one notice (for review-permission users). One row per notice, soonest first:
    - the class (`Occurrence.__str__`), or `Meeting on {date} at {time}`;
    - `Link emailed on {when}` (ok tag), or `The email didn't send` (warn tag, icon plus word);
    - a POST button `Email the link again` (with the busy button, `Getting the link from Zoom…`).
12. **`POST zoom:recording_resend`** (pk, notice pk):
    - It needs `zoom.review_linkrequest`, is `non_atomic`, and is POST only. It's 404 when the notice isn't the request's.
    - It asks Zoom fresh (criterion 6), sends criterion 8's email, updates `emailed_at`/`last_failed_at`, and redirects to the detail with:
      - `Emailed the recording link to {email}.` (success)
      - `The email to {email} didn't send. Try again later.` (warning)
      - `We couldn't get the recording from Zoom: {phrase}. {next step}` (error, 006's temporary or lasting next step)
      - `Zoom no longer has this recording. It may have been deleted.` (error, for a `404`; the backend confirms Zoom's code for a missing recording and records it)

### Scope, rules, verification

13. **Scopes.** The README's list gains `cloud_recording:read:list_recording_files:admin` (https://developers.zoom.us/docs/integrations/oauth-scopes-granular/). A `ZoomMissingScope` on the recordings call gives the resend message `The Zoom app for {label} is missing the permission to read recordings. Ask whoever looks after the server to add the scopes listed in the README.`, and 503 on the webhook (Zoom retries after the scope is added).
14. **Thin views; template rules, no-JS, layout and accessibility** as in 011 criterion 35.
15. **No test reaches the network.** `FakeProvider` gains a steerable `recording_share` answer and error.
16. **Automated checks** as in 011 criterion 37. No settings change is planned.
17. **Prod walkthrough** (dummy signing, as in 013 criterion 25):
    - a signed `recording.completed` for a test booking in `fake`-steered dev renders the `Recordings` box;
    - on prod with `manual`, an unsigned post is refused.

    Screenshots at 1440 and 400: the box with both tag states.
18. **The owner's live check:**
    1. Record 2 minutes of a live test class.
    2. Within about an hour of it ending, the requester email arrives.
    3. The link opens in a private browser window, and asks for the passcode if Q7's account setting is on.
    4. `Email the link again` works.
    5. Note each account's recording sharing settings for the record (Q7).

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q7 on 2026-09-26 (there is no Q3 in briefs 011–014; see 011's note).

| Q | Question (short) | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| Q7 | Who controls how private a recording link is? | Each Zoom account's settings; the app sets nothing | **"Each Zoom account's settings"** | D7 |

The public address is 013's (owner, Q6: "Production domain"; 013 D9).

**Decisions (the planner's)**

- **D1: Email every recording of an app booking**, not only those whose requester ticked "Record this class". A recording exists either way, and it's the requester's class. Holding it back would leave IT to share it by hand in Zoom.
- **D2: The link is fetched, not taken from the payload, and never stored.**
  - Fetching uses the same code path as `Email the link again`, so there's one definition of what's sent.
  - Only the fact of sending is stored. A stored share link plus passcode would be a table of working recording links.
  - The payload's `download_token` and the API's `download_access_token` are ignored and never logged.
- **D3: `share_url` plus the passcode, never a download or play URL.** The share page applies the account's sharing rules (passcode, expiry, downloads). Download URLs with tokens bypass them.
- **D4: A recording is matched to a class by its start time within 011's start window** (criterion 4). With the start link, the meeting normally starts inside that window.
- **D5: Owner setup, per paid account** (for the README):
  1. On marketplace.zoom.us, open the account's `Polymath TMD` app, then **Scopes → Add Scopes**, and add `cloud_recording:read:list_recording_files:admin`.
  2. **Features → Event Subscriptions**, edit `Polymath TMD sync` (013), and add Recording → **All Recordings have completed** (`recording.completed`). Save. The endpoint URL and secret are unchanged.
  3. In the account's web settings, **Settings → Recording**: cloud recording on, "Require passcode to access shared cloud recordings" on, and sharing allowed to anyone with the link. Choose downloads and an auto-delete period (Q7).
  4. Restart `web`, so the next token carries the new scope.
- **D7: Recording privacy is each Zoom account's setting** (owner, Q7: "Each Zoom account's settings").
  - The app never calls the recording-settings endpoint and asks for no scope to do so.
  - The owner sets passcode, sharing, downloads and auto-delete once per account (D5, step 3). The owner's live check records them (criterion 18, step 5).
  - This is why criterion 8's email says "The IT desk's Zoom settings decide how long the recording stays available", and why it covers the no-passcode case truthfully.
- **D6: Information architecture.** One box on the page IT already uses:

  ```
  ZL-0042 (zoom:detail)
  └── Recordings (box)  ← one row per recording; [Email the link again] → POST zoom:recording_resend
  ```

**Risk register**

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | Recording links leak beyond the class | Medium / Medium | Mitigate: account passcodes and expiry (Q7), requester only, email wording, nothing stored | a complaint | owner |
| R2 | An account setting restricts sharing to signed-in users, so students can't open it | Medium / Medium | Mitigate: D5 step 3, and the owner's live check step 3 | a requester reports it | owner |
| R3 | A recording is matched to the wrong class | Low / Low | Mitigate: the window match, and a fallback that names the recording's own date (criterion 4) | the requester reports the wrong date | backend |
| R4 | A whole-booking cancel deletes recordings not yet sent (011 R4) | Unknown / Medium | Confirm in 011's live check. If true, the README says to cancel after the recordings arrive | 011's step 7 | owner |

## MVT plan
<!-- owner: tmd-planner -->

### Models

- `RecordingNotice` (criterion 1), migration `0010_recording_notice`, numbered after 013's `0009`.
- A manager method `for_detail(link_request)`, soonest first, with the occurrence joined.

### Code

- **`providers.py`:** `recording_share(*, host_account, meeting_uuid) -> RecordingShare(share_url, passcode)`. It's a frozen dataclass with both fields `repr=False`, and it lives only in memory. There's also `zoom_api.meeting_uuid_path()` for the double encoding.
- **`services.py`:** `handle_recording_completed(credentials, payload) -> outcome` (called from 013's `handle_event`), `resend_recording(notice, *, provider=None)`, `send_recording_email(...)`, `send_recording_failed_it_email(...)`.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `zoom:webhook` (handles one more event) | as in 013 | `ZoomWebhookView` | none | Zoom's signature |
| **`zoom:recording_resend`** | `zoom/requests/<int:pk>/recordings/<int:notice_pk>/send/` | `RecordingResendView(ReviewerRequiredMixin, SingleObjectMixin, View)`, POST, `non_atomic` | none (302) | `zoom.review_linkrequest` |
| `zoom:detail` (changed context) | as today | as today | `zoom/detail.html` | as today |

### Context contract

**`zoom/detail.html`** adds `recordings` (a list of `RecordingNotice`: `occurrence` (Occurrence or `None`), `recorded_at`, `emailed_at`, `last_failed_at`, `pk`). It's empty when there are none, and then the box is left out.

**Emails:**
- `recording_subject.txt` / `recording_body.txt`: `link_request`, `occurrence` (or `None`), `recorded_at`, `share_url` (str), `passcode` (str, may be `""`).
- `recording_failed_subject.txt` / `recording_failed_body.txt`: `link_request`, `occurrence`, `recorded_at`, `detail_url`.

### Placement and reuse

- **`apps/zoom` only.**
- **Reused:** 013's endpoint, verification, `ZoomEvent` and 503-retry rule; 006's `zoom_api`, error kinds and `lasting`; 011's window; 005's `_send` and IT recipients; the busy button.
- **No new dependency.**

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Done (2026-09-26):** the owner answered Q7 (D7). **Start only after 013 is Done** and its endpoint has passed the owner's live check.
1. **`tmd-ui-designer`:** the `Recordings` box, both emails, and the resend messages.
2. **In parallel, after the Design:**
   - **2a. `tmd-django-backend`:** the model and migration, the provider method, the handler, the resend view, and the tests for criteria 1–15. It records the uuid encoding and the missing-recording code. It signals after `pytest --create-db`.
   - **2b. `tmd-frontend`:** the box and the email layouts. It runs `pytest` after the signal.
3. **`tmd-test-verifier`:** criteria 1–17, then the owner's live check (criterion 18).
4. **`tmd-code-reviewer`:** nothing stored or logged (criterion 10), the https-on-zoom.us check, idempotency by uuid, and thin views.
5. **`tmd-docs-writer`:** the README (recording links, D5's setup, Q7's settings, the scope), `docs/CHANGELOG.md`, and closes the brief.
