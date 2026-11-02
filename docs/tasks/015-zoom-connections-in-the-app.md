# 015 — Zoom connections in the app: credentials typed on a screen and stored encrypted, replacing `zoom-credentials.env`

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Verifying <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

**Starts once brief 013 is committed and approved, with only its owner live check (013 criterion 26) still pending.** 013 is committed as `ddb1719`, so the gate is met (D20). 013 can't be Done before that live check, and the owner has ordered the check to run after this brief is built. The owner's live checks (006 criterion 48, 013 criterion 26) then run through the new screen (criterion 50).

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

The owner's words (2026-11-02):

> shall we have a UI and the save credential for zoom in \encrepted in the database than .env file

The owner's answers (2026-11-02, relayed by the main session):

- **Who can edit:** the IT desk, meaning the same people who manage Zoom accounts and host keys (the `zoom.change_hostaccount` permission).
- **The env file:** remove it. Credentials live only in the database, with no env fallback.
- **When:** now, before the owner's live Zoom check. It's built after brief 013 closes, and the owner then tests a real account through the new screen.
- **Oversight:** the owner counts this as a correction of brief 006's D2 ("Zoom credentials never touch the database; env only").

**Reading.** Today each paid Zoom subscription's Server-to-Server app credentials (Account ID, Client ID, Client Secret and, from brief 013, the webhook Secret Token) can only be given to the app by someone with shell access. They write them into a git-ignored `zoom-credentials.env` and recreate the `web` container. On the account page, IT types a connection *name* that has to match that file. The owner wants the IT desk to type the credentials into the app instead. The two secrets are stored Fernet-encrypted with the same keys as host keys. The env file, and every line of code that reads it, goes away. The new values must take effect at once: Check connection, booking and the webhook all use them on the next request, with no restart. The secrets are write-only. They're never shown back and never revealed. The page shows only whether each one is saved, and who saved it and when. The planner's choices (one `ZoomConnection` row per Zoom app, chosen on each account; Account ID and Client ID kept as plain identifiers) are recorded as D1–D3.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**In scope**

- **Model** (migration `0010`):
  - a new `ZoomConnection` (one row per Zoom Server-to-Server app);
  - `HostAccount.credential_set` (a free-text name) is replaced by a `HostAccount.zoom_connection` foreign key;
  - the secrets are encrypted through `apps/zoom/crypto.py`, and its exception is renamed `SecretUnreadable`.
- **Screens:**
  - new `Zoom connections` list, add and change pages;
  - the Zoom account add and change pages pick a connection from a list instead of typing a name;
  - the accounts list's `Zoom connection` column gains a `Can't be read` state in place of `Missing on the server`.
- **Using the credentials:**
  - `ZoomProvider`, `zoom_api` (its token cache), the preview cache key, `services.check_connection` and the webhook (`webhooks.verify`, `services.handle_event`) all read the database;
  - nothing reads settings for credentials any more.
- **Checks:**
  - `zoom.E005` is retired;
  - `zoom.E004` and `zoom.W002` read the database;
  - the other checks are unchanged (D10).
- **Command:** `rotate_host_keys` becomes `rotate_encryption_keys`, which re-encrypts every stored secret (D4).
- **Removed (`tmd-devops`):**
  - the credential-reading code in `config/settings/base.py`;
  - `zoom-credentials.env.example`;
  - `compose.yaml`'s `env_file` entry;
  - the env-credential settings tests;
  - the `.env.example` wording.

  The `.gitignore` and `.dockerignore` lines stay, with a new comment (D12). `LOGGING` pins `django.db.backends` (D15).
- **Docs (`tmd-docs-writer`):** the amendments to briefs 005, 006, 008, 011, 013 and 014 and to `CLAUDE.md` listed under "Amendments to earlier briefs", the README's setup, rotation and backup advice, and `docs/CHANGELOG.md`.

**Out of scope**

- **Deleting a Zoom connection** (D14; a follow-up).
- **A connection-level "Check connection".** The account's existing button proves the connection and the user together (D6).
- **Revealing a client secret or a webhook secret** (D7).
- **Moving other settings into the database:** `ZOOM_PROVIDER`, `HOST_KEY_ENCRYPTION_KEYS`, `IT_DESK_PHONE` and email settings stay in env.
- **Renaming `HOST_KEY_ENCRYPTION_KEYS`** (D3).
- **A key-management service, or a per-secret key.**
- **Storing access tokens anywhere but process memory** (006 D4 stands).
- **Detecting a leftover `zoom-credentials.env` or `ZOOM_S2S_*` variables.** The file was never created (D11).
- **A history of connection changes** beyond the "last changed at / by" fields, which mirror host keys.
- **Brief 014's recording work.** 014 only picks up criterion 28's connection matching (see "Amendments").

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- **Carried over from 005, 006, 008, 011 and 013:**
  - the frozen now;
  - "IT user" (the `IT desk` group: `view_`, `add_` and `change_hostaccount`, plus `review_linkrequest`);
  - "plain user" (signed in, no Zoom permissions);
  - "key-less viewer" (only `zoom.view_hostaccount`);
  - "mocked Zoom" and the network block;
  - "signed POST" (013's terms);
  - the pinned-copy rule: the designer may propose changes through the main session, and they're made here first.
- **"Test connection":** a `ZoomConnection` made by the test helpers with obviously fake values:
  - `slug="zoom-test"`;
  - `account_id="test-account-id"`;
  - `client_id="test-client-id"`;
  - client secret `test-client-secret-value`;
  - webhook secret `test-webhook-secret-value` (when a test needs one).
- **"Ciphertext":** the stored Fernet token of a secret.
- **"Secret values":** the test client secret, the test webhook secret and their ciphertexts.

### The model (`tmd-django-backend`)

1. **`ZoomConnection` exists, with these fields and nothing else** (D1, D3):
   - `slug`:
     - `SlugField(max_length=40, unique=True)`;
     - `validators=[validate_credential_set]` (006's rule, `^[a-z0-9]+(-[a-z0-9]+)*$`);
     - verbose name `Zoom connection name`.
   - `account_id`: `CharField(100)`, verbose `Account ID`. Stored **plain**.
   - `client_id`: `CharField(100, unique=True)`, verbose `Client ID`. Stored **plain**.
   - `client_secret_encrypted`: `TextField(editable=False)`.
   - `webhook_secret_encrypted`: `TextField(blank=True, editable=False)`.
   - `credentials_version`: `PositiveIntegerField(default=1, editable=False)`.
   - `credentials_changed_at` (`DateTimeField`, null) and `credentials_changed_by` (FK user, `SET_NULL`, null, `related_name="+"`). Both are `editable=False`.
   - `webhook_secret_changed_at` and `webhook_secret_changed_by`, the same shapes.
   - **`Meta`:**
     - `ordering = ["slug"]`;
     - `default_permissions = ()` (D5);
     - verbose names `Zoom connection` / `Zoom connections`.
   - **`CheckConstraint`s** (MySQL 8.4 enforces them), so a stored connection is always complete. Each of these must not be `""`:
     - `account_id`;
     - `client_id`;
     - `client_secret_encrypted`.

     A test writes each one empty with `QuerySet.update()` and gets `IntegrityError`.
   - **`str()` and `repr()`:** `str()` is the slug, and `repr()` is `<ZoomConnection: zoom-test>`. Neither contains an ID, a secret or ciphertext (test).
2. **Secrets are only reachable through methods** (`@sensitive_variables` on every one that holds a plaintext). An *Unreadable* secret means one that fails to decrypt.
   - **`set_credentials(*, account_id, client_id, client_secret, by)`:**
     - An empty `client_secret` keeps the saved one.
     - When **any** of the three differs from what's stored, it adds 1 to `credentials_version` and sets `credentials_changed_at` (now) and `credentials_changed_by` (`by`). Comparing the secret means decrypting the stored one. If the stored secret is unreadable, any typed secret counts as a change.
     - When nothing differs, it changes nothing at all: no version bump and no change record.
   - **`set_webhook_secret(plain, *, by)`** stores it and records the webhook change fields. It doesn't touch `credentials_version` (a webhook secret isn't part of the token).
   - **`remove_webhook_secret(*, by)`** clears a stored secret, readable or not, and records the change (D20 G3). It does nothing when no secret is stored.
   - **`get_client_secret()`, `get_webhook_secret()`** return the plaintext (`""` when no webhook secret is saved), or raise `crypto.SecretUnreadable`.
   - **`credentials()`** returns a `zoom_api.ZoomCredentials`, a frozen dataclass that **moves** from `config/settings/base.py` to `apps/zoom/zoom_api.py`:
     - fields `slug`, `version`, `account_id`, `client_id`, `client_secret`;
     - every field except `slug` is `repr=False`;
     - no webhook secret.
   - **State properties.** Each decrypts only to test readability, and keeps nothing:
     - `credentials_state`: `"saved"` or `"unreadable"`;
     - `webhook_secret_state`: `"none"`, `"saved"` or `"unreadable"`;
     - `has_webhook_secret`: `webhook_secret_state == "saved"`.
   - **`rotate_secrets()`** re-encrypts both stored secrets with the first key. It returns how many it rotated, and raises `SecretUnreadable` naming which one failed. It changes neither the version nor the change record.
3. **`HostAccount` links to a connection** (D1).
   - `credential_set` is removed. In its place:

     ```python
     zoom_connection = ForeignKey(
         ZoomConnection,
         on_delete=PROTECT,
         null=True,
         blank=True,
         related_name="host_accounts",
         verbose_name="Zoom connection",
     )
     ```
   - **`zoom_connection_state`** is:
     - `"none"` when no connection is chosen;
     - `"unreadable"` when the connection's `credentials_state` is `"unreadable"`;
     - `"ready"` otherwise.
   - `is_zoom_connected()` is still `== "ready"`, the one definition.
   - **No query when the related row is already loaded.** `HostAccountQuerySet.bookable()`, `for_management()` and the account change view load the connection with `select_related("zoom_connection")`.
   - **Locking reads lock only `HostAccount` rows.** `availability_for(lock=True)` and the change view's `select_for_update` use `of=("self",)`, so no booking path ever locks a `ZoomConnection` row (D8).
   - The module functions `zoom_connection_state_for` and `webhook_secret_set_for` are removed. Their callers read the connection object (criteria 20, 32, 33).
4. **Migration `0010_zoom_connections`, schema only** (D11). It's numbered after 013's `0009`; if 014 lands first, the later one renumbers.
   - It creates `ZoomConnection`, removes `HostAccount.credential_set` and adds `HostAccount.zoom_connection`.
   - There's **no data migration from env**: `zoom-credentials.env` was never created, so there are no credentials anywhere to carry over. Any connection *name* typed on an account is dropped, because no such account could have been `ready` without credentials.
   - It's reversible. Reversing restores an empty `credential_set` column.
   - `makemigrations --check --dry-run` is clean.
   - `ZoomEvent.slug` is unchanged (a plain slug; 013's history keeps working).
5. **The secret-name test (005 criterion 46, extended by 008)** now scans `ZoomConnection` as well. Its allowed list becomes exactly these, and any other field matching the pattern still fails:
   - `HostAccount.host_key_encrypted`, `HostAccount.host_key_changed_at`, `HostAccount.host_key_changed_by`;
   - `ZoomConnection.client_secret_encrypted`, `ZoomConnection.webhook_secret_encrypted`, `ZoomConnection.webhook_secret_changed_at`, `ZoomConnection.webhook_secret_changed_by`.
6. **At rest, secrets are ciphertext only.**
   - A raw SQL read of a saved test connection shows `client_secret_encrypted` and `webhook_secret_encrypted` starting with `gAAAAA`, and containing neither plaintext.
   - Two connections saved with the same secret store different ciphertexts.
   - Encryption is `crypto.encrypt()` with the first `HOST_KEY_ENCRYPTION_KEYS` key; no second encryption module.
   - With `HOST_KEY_ENCRYPTION_KEYS` swapped for a different valid key (`override_settings`), `credentials_state` and `webhook_secret_state` read `"unreadable"`, and the account reads `"unreadable"`.
7. **`crypto.py` only names the error differently** (D13).
   - `HostKeyUnreadable` is renamed `SecretUnreadable`, with no alias. Every caller is updated: `models`, `views`, `services` and the command.
   - The module docstring no longer says host keys are the only secret the database holds.
   - `cryptography` is still imported only in `crypto.py` (source scan).

### Zoom connection screens

8. **Permission** (owner: "IT desk"; D5).
   - `zoom:connections`, `zoom:connection_add` and `zoom:connection_edit` each need `zoom.change_hostaccount`:
     - anonymous → the sign-in redirect;
     - plain user and key-less viewer → 403 with `templates/403.html`.
   - `Permission.objects.filter(content_type=<ZoomConnection>)` is empty, so the Staff and access page can never grant a connection permission of its own.
   - All three views are `never_cache` (`Cache-Control` includes `no-store`).
9. **Navigation** (D6, Information architecture).
   - There's **no new sidebar item**. The sidebar's `Zoom accounts` link is `aria-current="page"` on all three connection pages.
   - The Zoom accounts list shows a `Zoom connections` link when `can_manage_connections` is true. It's absent for a key-less viewer.
   - The account add and change pages' `Zoom connection` section shows the same link, under the same condition.
   - Breadcrumbs:
     - `Zoom accounts › Zoom connections`;
     - `Zoom accounts › Zoom connections › Add a Zoom connection`;
     - `Zoom accounts › Zoom connections › {slug}`.
10. **The list (`zoom:connections`).**
    - One row per connection, by slug. Each row shows:
      - the name, linking to its change page;
      - **Used by:** the labels of the accounts that use it, in `sort_order` then `label` order, each linking to `zoom:account_edit`, or `No account yet`;
      - **Connection details:** `Saved` or `Can't be read`;
      - **Webhook secret:** `Saved`, `Not saved` or `Can't be read`.
    - Each state is shown with an icon plus a word.
    - The page contains **no** Account ID, Client ID, secret value or ciphertext.
    - **Queries:** the same number with 1 and with 5 connections, each used by 2 accounts (a test compares the two counts).
    - **The add button** (D20 P2) is the box head's `+ Add a Zoom connection` link: the `plus` icon (`aria-hidden`) plus the words `Add a Zoom connection`, pointing to `zoom:connection_add`. It shows whether or not there are connections. It's the page's only link to `zoom:connection_add` (a test counts exactly one, and finds it inside the box head, not inside the empty state).
    - **Empty state:** `No Zoom connections yet. Add one for each paid Zoom subscription.` There's no second add button inside the empty state; the head's button serves it (P2).
    - **Status tags** (D20 G5, D.9): both state columns render through `zoom/partials/connection_tag.html`:
      - `saved`: `tag--plain`, the `lock` icon and `Saved`;
      - `none`: `tag--warn`, the `alert-triangle` icon and `Not saved`;
      - `unreadable`: the new `tag--bad`, the `alert-octagon` icon and `Can't be read`.
11. **Add (`zoom:connection_add`).**
    - The fields, in order: `slug` (`Connection name`), `account_id`, `client_id`, `client_secret`, `webhook_secret`. The first four are required; the webhook secret is optional.
    - **`client_secret` is marked `required` whenever it is required** (amended 2026-11-02, D21, review round 1 SF2). It's required on the add page, and on the change page when `credentials_state == "unreadable"`; on the change page with a readable saved secret it isn't. `ZoomConnectionForm.__init__` sets `fields["client_secret"].required` from exactly that rule, so the input renders the `required` attribute in both required cases and not otherwise, like `account_id` and `client_id` (test: the rendered HTML on the add page, on the change page with an unreadable secret, and on the change page with a readable one). The empty-value error is the field's own `required` message (`error_messages["required"]`), which keeps criterion 13's pinned text; `clean_client_secret` no longer has an empty-value branch of its own. P3's behaviour (D20) is unchanged.
    - A valid POST:
      - creates the row through `set_credentials` and (if typed) `set_webhook_secret`, with `by` the IT user;
      - sets `credentials_version` to 1, `credentials_changed_at` to now and `credentials_changed_by` to the user;
      - redirects 302 to `zoom:connections` with the success message `Added the Zoom connection {slug}. Next, choose it on the Zoom account that uses it, then press Check connection there.`
    - **Labels and help, add and change pages** (D20 G1). `ZoomConnectionForm.__init__` sets each label and help text from the page (add or change) and the stored state, the way `HostAccountForm` switches the host key's. Nothing is set in the template. Each help renders with `id="<name>-help"`. A test checks every row.

      **One definition of the name and ID help** (amended 2026-11-02, D21, review round 1 SF3). The help for `slug`, `account_id` and `client_id` is defined once, as the `help_text` of `ZoomConnection.slug`, `.account_id` and `.client_id`, worded exactly as the add-page rows below. The form borrows it with `ZoomConnection._meta.get_field(name).help_text` and holds no copy of its own; the per-state switching stays only for the two secrets and `remove_webhook_secret`. Migration `0010_zoom_connections` is still uncommitted, so it's edited in place, and `makemigrations --check --dry-run` stays clean. Tests: each of the three model fields' `help_text` equals its pinned text below, and the rendered help on both pages equals the model's.

      | Field | Page and state | Label | Help |
      |---|---|---|---|
      | `slug` | add | `Connection name` | `A short name for this Zoom app, like zoom-01. Use lower-case letters, numbers and hyphens. It can't be changed later, because it's part of the address Zoom sends changes to.` |
      | `account_id` | both | `Account ID` | `Copy the Account ID from App Credentials and paste it here.` |
      | `client_id` | both | `Client ID` | `Copy the Client ID from App Credentials and paste it here.` |
      | `client_secret` | add | `Client secret` | `Copy the Client Secret from App Credentials and paste it here. For safety, it's never shown again once saved.` |
      | `client_secret` | change, `credentials_state == "saved"` | `New client secret` | `Leave it empty to keep the saved one. If the Client Secret was regenerated in Zoom, paste the new one here.` |
      | `client_secret` | change, `"unreadable"` | `New client secret` | `Paste the Client Secret from App Credentials. The saved one can't be used.` |
      | `webhook_secret` | add | `Webhook secret` | `Optional. The Secret Token from the Event Subscriptions part of the Zoom app. You can add it later, on this connection's page, which also shows the address Zoom needs.` |
      | `webhook_secret` | change, `webhook_secret_state == "none"` | `New webhook secret` | `Paste the Secret Token from the Event Subscriptions part of the Zoom app, and save. Then press Validate in Zoom.` |
      | `webhook_secret` | change, `"saved"` | `New webhook secret` | `Leave it empty to keep the saved one. If the Secret Token was regenerated in Zoom, paste the new one here.` |
      | `webhook_secret` | change, `"unreadable"` | `New webhook secret` | `Paste the Secret Token from the Event Subscriptions part of the Zoom app. The saved one can't be used.` |
      | `remove_webhook_secret` | change, when present (criterion 12) | `Remove the saved webhook secret` | `Tick this if the saved secret is wrong and you don't have the new one yet. Changes made in Zoom then stop being seen here.` |

    - **Widgets, add and change pages** (D20 G2). The rendered HTML is checked by a test:
      - `account_id`, `client_id`, `client_secret` and `webhook_secret` are `forms.TextInput`, so they render `type="text"`, never `PasswordInput`. Each one has `autocomplete="off"`, `autocapitalize="none"`, `autocorrect="off"` and `spellcheck="false"`.
      - Those four render **no `maxlength` attribute**. Their 100- and 200-character limits are checked in `clean_*` (criterion 13), so a paste that's too long is refused, not silently cut short by the browser.
      - `slug` keeps `maxlength="40"`.
12. **Change (`zoom:connection_edit`).**
    - **The name is shown, not editable** (D2). The form has no `slug` field, and a POSTed `slug` changes nothing (test).
    - `account_id` and `client_id` are prefilled with the stored values (D3).
    - **Both secret inputs always render with no value.** Their labels are `New client secret` and `New webhook secret`. Leaving them empty keeps what's saved, with one exception. When `credentials_state` is `"unreadable"`, an empty `New client secret` is refused (criterion 13, D20 P3).
    - **`Remove the saved webhook secret`** (a checkbox) is present whenever a webhook secret is **stored** (`webhook_secret_encrypted != ""`), that is, when `webhook_secret_state` is `"saved"` **or** `"unreadable"`. It's absent when the state is `"none"` (D20 G3, following `remove_host_key`). A test ticks it on an unreadable secret: the save clears the secret, records the change, and the state then reads `"none"`.
    - The POST locks the row (`select_for_update()` inside the request's transaction) before validating.
    - A valid POST redirects 302 to `zoom:connections` with a message:
      - no account uses the connection: `Saved the Zoom connection {slug}. Next, choose it on the Zoom account that uses it, then press Check connection there.`
      - one or more do: `Saved the Zoom connection {slug}. To make sure Zoom accepts it, press Check connection on {labels}.` `{labels}` is the accounts' labels joined as `Zoom 01`, `Zoom 01 and Zoom 02`, or `Zoom 01, Zoom 02 and Zoom 03`, using the existing word-joining rule in `models.py`.
    - A POST that changes nothing records nothing (criterion 2) and shows the same message.
13. **Errors keep what was typed** (except secrets, criterion 14) and use these pinned texts. Values are trimmed first. An ID or secret must then be non-empty, contain no whitespace, be printable ASCII, and be at most 100 characters (IDs) or 200 (secrets). Otherwise:
    - `slug`:
      - empty: `Type a name for this connection, like zoom-01.`
      - bad form: `Use lower-case letters, numbers and hyphens only, like zoom-01.` (006's text, reused);
      - taken: `Another Zoom connection already has this name. Choose a different one.`
    - `account_id`: `Paste the Account ID from the App Credentials page of the Zoom app. It has no spaces.`
    - `client_id`:
      - bad: `Paste the Client ID from the App Credentials page of the Zoom app. It has no spaces.`
      - taken: `The Zoom connection {slug} already uses this Client ID. Each Zoom app needs only one connection.`
    - `client_secret`: `Paste the Client Secret from the App Credentials page of the Zoom app. It has no spaces.` This also covers an empty value in two cases:
      - on the add page;
      - on the change page when the saved client secret can't be read (`credentials_state == "unreadable"`, D20 P3). The form decides this from the instance's `credentials_state`. Nothing is saved, so the Account ID and Client ID stay as they were (test).

      In both cases the empty-value error is the field's `required` message, with this same text (amended 2026-11-02, D21, SF2; criterion 11).
    - `webhook_secret`, when typed: `Paste the Secret Token from the Event Subscriptions part of the Zoom app. It has no spaces.`
    - A new webhook secret **and** Remove ticked: `Type a new webhook secret or tick Remove, not both.`

    The page's error summary leads with `We couldn't save this Zoom connection yet.` Each error is tested, and so is the kept value of every non-secret field.

    **The length limits are the server's, not the browser's** (D20 G2). A test POSTs a 101-character Account ID, a 101-character Client ID and a 201-character secret, and each gets its field's error above.
14. **A typed secret is never sent back.**
    - After any invalid POST, the HTML contains neither typed secret anywhere, and neither secret input has a `value` attribute.
    - For each secret that was typed, a note shows above its field, and is added to the field's `aria-describedby`:
      - `For your safety, the client secret you typed wasn't kept. Type it again.`
      - `For your safety, the webhook secret you typed wasn't kept. Type it again.`

      The form exposes this as `client_secret_was_typed` and `webhook_secret_was_typed` (008's host-key pattern, D7).
    - **The secret boxes show what's typed** (owner's answer to O1, D20). Each is a plain `type="text"` input with no `value` attribute, exactly like the host key, so IT can spot a wrong paste. `docs/design/password-field.md` doesn't apply to them: no `type="password"`, no Show/Hide button.
    - **One partial renders all three secret inputs** (D20). `client_secret`, `webhook_secret` and the account page's existing `host_key` render through `zoom/partials/secret_field.html`. The host key's rendered output doesn't change: the same ids, `aria-describedby` tokens, note and attributes. The existing 008 and 011 host-key template tests pass unchanged.
    - No page, before or after any POST, contains a saved secret's plaintext or ciphertext (tested on the list, the add page, the change page, both account pages and the accounts list).
15. **The change page shows each secret's state, never the secret.**
    - **Connection details:**
      - `saved`: `Connection details saved on {date} by {name}.` The ` by {name}` part is dropped when `credentials_changed_by` is empty.
      - `unreadable`: a `notice--bad`: `The client secret is saved, but it can't be read with the server's current encryption keys. Type it again.`
    - **Webhook secret:**
      - `saved`: `Webhook secret saved on {date} by {name}.`, followed by `Last heard from Zoom on {when}.`, or `Nothing heard from Zoom yet.` when no event is recorded. `last_zoom_event_at` is 013's `ZoomEvent.objects.last_received_at(slug)`, one aggregate.
      - `none`: titled `No webhook secret saved`, with `Without it, changes made directly in Zoom aren't seen here. Add it when you set up the Zoom app's Event Subscription, using the address below.` (D20 P1: Zoom's Validate only passes once the app already has the secret).
      - `unreadable`: `A webhook secret is saved, but it can't be read with the server's current encryption keys. Type it again.`
    - **Undated fallbacks** (amended 2026-11-02, D21, review round 1 N2). When a state is `saved` but has no saved-on date, the sentence has no date and no name:
      - `credentials_changed_at` empty: `Connection details saved.`
      - `webhook_secret_changed_at` empty: `Webhook secret saved.`, still followed by the `Last heard from Zoom on {when}.` or `Nothing heard from Zoom yet.` line.

      This happens only for a row made outside the screens (a shell or a test helper), because every save through the screens records the date (criterion 2). It mirrors the host key's `saved_legacy`. No code change: the frontend already renders both (test: each sentence, for a row with the date cleared by `QuerySet.update()`).
    - **`Address for Zoom's Event Subscriptions`:** the absolute URL of `zoom:webhook` for this slug, built from the request with `build_absolute_uri` (D6). It's plain text that a person can select, and isn't a link. It renders in the new `.copy-value` component (D20, Design D.9.1).
    - **An address Zoom can't use** (D20 G4). The view sets `webhook_address_secure` to `webhook_address.startswith("https://")`. When it's false, a `notice--warn` with the `alert-triangle` icon follows the address, titled `Zoom can't use this address`, with `Zoom only sends changes to an address that starts with https://. Open this page through the site's public https:// address, or ask whoever looks after the server for it.` The template makes no URL decision of its own. Test: a plain `Client` GET shows the notice, and a `secure=True` GET doesn't.
    - **`Used by`:** the same account links as the list.
16. **No reveal** (D7).
    - No URL, view, button or form shows a client secret or a webhook secret.
    - A source scan of `apps/zoom/urls.py` finds exactly one reveal route, `zoom:account_host_key`, which is 011's.
    - A test decrypts nothing for display: `get_client_secret` and `get_webhook_secret` are called only by `credentials()`, `rotate_secrets()`, the state properties and the webhook (source scan of their callers).
17. **Forms are protected.**
    - The add and change views are wrapped in `sensitive_post_parameters("client_secret", "webhook_secret")`.
    - Every form and model method that holds a typed or decrypted secret is `@sensitive_variables` naming it.
    - An `ExceptionReporter` test on an error raised inside the form's `save()` shows neither typed secret in the HTML.
    - A POST without a CSRF token through `Client(enforce_csrf_checks=True)` gets 403 on both views.

### The Zoom account pages (amend 006 criteria 34–36 and 013 criterion 29)

18. **The account form picks a connection.**
    - `HostAccountForm`'s `credential_set` is replaced by `zoom_connection`, a `ModelChoiceField` in the same place (after `sort_order`).
    - Label `Zoom connection`. Empty label `No Zoom connection yet`.
    - Help: `The Zoom app this account books through. If it isn't in the list, add it on the Zoom connections page first.`
    - An invalid choice gives `Choose a Zoom connection from the list.`
    - Its queryset reads only `pk` and `slug` (`.only("pk", "slug")`), so no secret column is selected (captured SQL).
    - The field is on both the add and the change pages. Its widget is a `<select>` rendered through the new shared partial `partials/select_field.html` (Design D.7.1, D20), never `field.html`'s text-input path (CLAUDE.md's rule for choice widgets). The select has a `<label for>`, its help as `id="zoom_connection-help"` in its `aria-describedby`, and, after an invalid POST, the person's choice still selected (test).
19. **What the change page says about the connection,** from the **stored** link (an invalid POST doesn't change it, as with 006 criterion 35):
    - `ready`: `Set up` (`notice--ok`), with `This account uses the Zoom connection {name}. Press Check connection to make sure Zoom accepts it.`
    - `unreadable`: `Can't be read` (`notice--bad`), with `The details of the Zoom connection {name} can't be read with the server's current encryption keys. Type its client secret again on the Zoom connection's page.`
    - `none`: unchanged (`Not set up`, 006's text).
    - `{name}` links to that connection's change page when `can_manage_connections` is true. Otherwise it's plain text.
20. **013's webhook lines read the connection.**
    - `webhook_secret_set` keeps 013 criterion 29's meaning (`True`, `False` or `None`, with `None` on the add page, when the stored connection isn't `ready`, or when the provider doesn't `checks_zoom`). It's now the stored connection's `has_webhook_secret`.
    - `last_zoom_event_at` is read by the stored connection's slug.
    - The `False` notice keeps its title. Its body becomes: `The Zoom connection {name} has no webhook secret. Until it has one, a class changed or deleted directly in Zoom stays as it was here until its booking is checked against Zoom. Add it on the Zoom connection's page.`
    - 013's tests for the three states, the shared-connection case and "query count rises by at most one" pass against the new source.
21. **The accounts list's `Zoom connection` column** shows `Set up`, `Not set up` or `Can't be read` (replacing `Missing on the server`), each with an icon and a word, through `zoom/partials/account_tag.html`. 006's "a missing connection matters only on a bookable account" styling rule is kept for `Not set up`. For `"unreadable"`, `account_tag.html` includes `zoom/partials/connection_tag.html`, so `Can't be read` is always `tag--bad` with `alert-octagon`, whether the account is bookable or not, and has one definition across both lists (D20 G5). The list's query count is the same with 1 and with 5 accounts, each linked to a connection.
22. **Check connection's messages** (006 criterion 36's table, amended rows; every other row is unchanged):

    | Result | Level | Message |
    |---|---|---|
    | no connection chosen | error | `{label} has no Zoom connection yet. Choose one, save, then check again.` |
    | connection unreadable | error | `The details of the Zoom connection {slug} can't be read with the server's current encryption keys. Type its client secret again on the Zoom connection's page, then check again.` |
    | `ZoomAuthFailed` | error | `Zoom didn't accept the details of the Zoom connection {slug}. Check its Account ID, Client ID and Client Secret on the Zoom connection's page, and that the Zoom app is activated.` |

    In the first two rows nothing is sent anywhere (an empty mocked-Zoom registry, no error). The `name not on the server` row is retired.

### Using the stored credentials

23. **Read per operation, effective at once** (D8).
    - Every Zoom call builds its client from the connection row as read in that operation. No module keeps credentials between operations: no module-level dict, no settings, no `lru_cache`.
    - **Test, no restart:**
      1. An account on the test connection is checked (`POST zoom:account_check`), so a token for version 1 is cached.
      2. The IT user saves a new client secret on `zoom:connection_edit`.
      3. The next `POST zoom:account_check` makes a **new** token request whose HTTP Basic credentials carry the **new** secret.
      4. The success message shows.
24. **The token cache follows the version** (amends 006 criterion 9's "per credential set").
    - `zoom_api`'s cache key is `(slug, credentials_version, client_id)` (amended 2026-11-02, D21, review round 1 SF1; it was `(slug, credentials_version)`).
      - **Why the Client ID is in the key:** a connection deleted and re-added under the same name starts again at version 1, so a version alone can't tell the old Zoom app from the new one. Without the Client ID, a worker still holding the old app's token for `(slug, 1)` would use it for the new app for up to an hour, and create meetings on the wrong Zoom account. Today that needs a shell delete; D14's follow-up "Remove" would make it reachable from a screen.
    - **Only lower versions are dropped** (amended 2026-11-02, D21, review round 1 N4). Building a client for `(slug, v, client_id)` drops every cached token for the same slug whose version is **lower** than `v`, whatever its Client ID, so a replaced secret's token isn't kept in that process. A token for the same slug at the same or a higher version is kept: a client built from an older (stale) read must never evict a newer version's token. Tests:
      - **newer evicts older:** with a token cached for `(zoom-test, 1, test-client-id)`, building a client for version 2 drops it;
      - **stale doesn't evict newer:** with a token cached for version 2, building a client for version 1 leaves it, and the next version-2 call reuses it (no new token request, by call count);
      - **same name, new app:** with a token cached for `(zoom-test, 1, test-client-id)`, the test connection is deleted and re-added as `zoom-test` with Client ID `other-client-id` (version 1 again). The next Zoom call makes a **new** token request whose Basic auth header carries `other-client-id` (a `responses` matcher), and the old token is never sent as a `Bearer`.
    - **Another worker's save:** bumping `credentials_version` with `QuerySet.update()` makes the next call in this process fetch a new token. Process memory needs no message from the saving process.
    - **Changing only the webhook secret** doesn't bump the version, so the cached token is reused (call count).
    - 006's other token rules (the 300-second margin, the one retry on `401`, never stored, never logged) are unchanged and their tests pass.
25. **Preview cache and threads.**
    - `services._preview_key` uses `zoom_connection_id` and `credentials_version` in place of `credential_set`.
    - Changing the account's connection, or the connection's credentials, makes the next preview ask Zoom again (test).
    - The preview's worker threads still run **no** query: the accounts are loaded with their connection before the threads start. 006's fixed-query-count test for the detail page passes, and a test asserts no query happens inside `provider.busy_times` under the preview.
26. **Every Zoom path works from the database.** Approve, cancel, move, reconcile, the start link and `check_zoom_connections` pass their existing test suites. The test helpers (`zoommock.py`, `synckit.py`) now create `ZoomConnection` rows instead of setting `settings.ZOOM_S2S_SECRETS`. A source scan finds no `ZOOM_S2S` and no `ZOOM_CREDENTIAL` anywhere under `apps/` or `config/` (the scanning test builds its needles from parts, so it doesn't match itself).

### The webhook (amends 013 criteria 4, 6, 12 and 29)

27. **One lookup per call.**
    - `webhooks.verify(request, slug)` reads the connection by slug with **exactly one query**. It loads only `pk`, `slug`, `account_id` and `webhook_secret_encrypted`.
    - **A URL validation** makes exactly one query and no HTTP call (amends 013 criterion 6's "no database query").
    - **An unknown slug, or a connection with no webhook secret** → 404, and nothing above `INFO` from `apps.zoom` (013 criterion 4, unchanged).
    - **A connection whose webhook secret can't be read** → 404, plus exactly one `WARNING` from `apps.zoom`: `Zoom webhook call to {slug} refused: unreadable secret` (D9).
    - 013 criteria 5 and 7's signature, replay and account checks use the decrypted secret and the stored `account_id`, and their tests pass unchanged apart from setup.
28. **Bookings are matched by connection.**
    - `handle_event` keeps only bookings whose `host_account.zoom_connection_id` is the verified connection's pk, replacing `credential_set == slug`.
    - Compared with 013, a handled event costs at most the one lookup query more (a captured-query test on a `meeting.deleted` that reconciles).
    - 013 criterion 12's "booked on another connection's account is `not_ours`, with a `WARNING`" still holds.
29. **A saved webhook secret works on the next call.**
    1. On a connection with no webhook secret, a signed URL validation gets 404.
    2. The IT user saves the webhook secret on `zoom:connection_edit`.
    3. The very next signed validation gets 200 with the exact JSON.
    4. After the secret is **changed**, a call signed with the old secret gets 401 `bad signature`.
    5. After it's **removed**, the next call gets 404.

    No restart, settings change or cache reset happens between the steps.

### Checks, commands and rotation

30. **`zoom.E005` is retired** (D10).
    - `check_credential_sets` is removed and no longer registered (a registry test).
    - No check anywhere produces the id `zoom.E005`, and the id isn't reused.
    - `config/settings/base.py` is no longer imported by `apps/zoom/checks.py`.
31. **Unchanged checks.**
    - `zoom.E001`, `E002`, `E003`, `E006` and `W001` keep their behaviour, tags and texts: they read `ZOOM_PROVIDER`, `HOST_KEY_ENCRYPTION_KEYS` and `IT_DESK_PHONE`, which aren't credentials.
    - Their existing tests pass.
    - No new untagged or deploy check queries the database.
32. **`zoom.E004`** (still tagged `database`, `zoom` provider only, silent before `migrate`).
    - There's one error per bookable account whose `zoom_connection_state` isn't `ready`:
      - `{label} has no working Zoom connection: no Zoom connection is chosen.`
      - `{label} has no working Zoom connection: the details of {slug} can't be read with the current encryption keys.`
    - Hint: `Choose the connection on the Zoom accounts page, or type its client secret again on the Zoom connections page.`
    - It runs one query, whatever the number of accounts.
33. **`zoom.W002`** (still tagged `database`, `zoom` provider only, connected bookable accounts).
    - `webhook_secret_state == "none"` keeps 013's message, with the new hint: `Add the webhook secret on the Zoom connection's page. The README says where Zoom shows it.`
    - `"unreadable"` gets: `{label}'s Zoom connection has a webhook secret that can't be read with the current encryption keys, so changes made directly in Zoom to its meetings aren't seen here.` The hint is the same.
    - It runs one query.
34. **`rotate_encryption_keys` replaces `rotate_host_keys`** (D4).
    - `apps/zoom/management/commands/rotate_host_keys.py` is removed.
    - The new command re-encrypts, with the first `HOST_KEY_ENCRYPTION_KEYS` key, **in one transaction** with the rows locked:
      - every saved host key;
      - every client secret;
      - every webhook secret.
    - It changes no `*_changed_at`, `*_changed_by` or `credentials_version`.
    - It prints `Re-encrypted {n} host key{s} and {m} Zoom connection secret{s}.`, with correct plurals.
    - For values it can't read, it writes to stderr `Couldn't read: {items}. Type those again on the Zoom accounts and Zoom connections pages.` Each item is `the host key of {label}`, `the client secret of {slug}` or `the webhook secret of {slug}`, joined with `; `. The command then **exits 1**.
    - **Tests:**
      - with keys `[new, old]`, after the command, keys `[new]` alone read every value;
      - one unreadable value gives the stderr line and exit 1;
      - no output contains a secret value.
35. **`check_zoom_connections`** works from the database with its existing line formats. Criterion 22's new texts appear in its lines where the check would show them.

### Removing the env path (`tmd-devops`)

36. **`config/settings/base.py`** no longer contains any of these:
    - `ZoomCredentials`;
    - `ZOOM_CREDENTIAL_PARTS`;
    - `ZOOM_CREDENTIAL_OPTIONAL_PARTS`;
    - `zoom_credential_env_prefix`;
    - `read_zoom_credentials`;
    - `ZOOM_CREDENTIAL_SETS`;
    - `ZOOM_S2S_SECRETS`;
    - `ZOOM_CREDENTIAL_MISSING`;
    - the now-unused `dataclass` import.

    The `HOST_KEY_ENCRYPTION_KEYS` comment says it also encrypts Zoom connection secrets, and that a database backup plus these keys gives access to Zoom (D16, R1).

    **The `mail_admins` comment** (amended 2026-11-02, D21, review round 1 N5). The "Don't set ADMINS without first revisiting …" comment above the `mail_admins` handler also names Zoom connection values: a 500 email's frame locals can hold an Account ID, a Client ID or a secret's ciphertext from a database error (brief 015, review round 1, N5). The reviewer checks the comment; no code changes.

    A source scan finds no `ZOOM_S2S` and no `ZOOM_CREDENTIAL` in:
    - `apps/` and `config/`;
    - `compose.yaml` and `compose.dev.yaml`;
    - `Dockerfile` and `docker/`;
    - `.env.example`.
37. **Files.**
    - `zoom-credentials.env.example` is deleted.
    - `compose.yaml`'s `web` has no `env_file` key and no mention of `zoom-credentials`.
    - `docker compose config --quiet` passes for both the prod stack and the dev overlay.
    - `.gitignore` and `.dockerignore` **keep** their `zoom-credentials.env` line (D12), with the comment changed to `# Retired by brief 015 (Zoom credentials are typed in the app). Kept so a stray copy is never committed or copied into the image.`
    - `apps/core/tests.py::test_dockerignore_keeps_private_data_out_of_the_image` still passes.
38. **`.env.example`.**
    - The `ZOOM_PROVIDER` comment no longer mentions `zoom-credentials.env` or `ZOOM_S2S_*`. It says each Zoom app's details are typed on the app's Zoom connections page.
    - The `HOST_KEY_ENCRYPTION_KEYS` comment says it encrypts host keys **and** Zoom connection secrets. It adds that the keys must be backed up apart from the database: losing them means retyping every secret, and a backup holding both gives access to Zoom.
    - `compose.yaml`'s comment on `HOST_KEY_ENCRYPTION_KEYS` says the same in one line.
39. **Platform tests (`apps/core/test_zoom_settings.py`).**
    - **Removed:** the tests of env-credential reading, naming, masking of `ZOOM_S2S_SECRETS`, the compose `env_file` and the example file.
    - **Kept:**
      - the `urllib3` pin;
      - the network-block tests (006 criterion 45);
      - the prod fake-provider refusal;
      - the `.env.example` provider line.
    - **Added:**
      - criteria 36–37's absence scans;
      - **`django.db.backends` logs nothing below `INFO`** (D15). `LOGGING` pins `"django.db.backends": {"level": "INFO"}`, with a comment saying SQL parameters now carry connection values. A test asserts its effective level is at least `INFO` under the project's `LOGGING`.

### Security

40. **Nothing secret is logged.** Records are captured at `DEBUG` for `apps.zoom`, `django`, `requests` and `urllib3` through:
    - adding a connection;
    - changing it (both secrets);
    - an invalid POST with typed secrets;
    - Check connection (mocked Zoom);
    - a signed webhook validation;
    - a `meeting.deleted` reconcile;
    - `rotate_encryption_keys`.

    No record contains:
    - a secret value or its ciphertext;
    - the test Account ID or Client ID;
    - `Basic ` or `Bearer `;
    - an access token.

    Django's `django.db.backends` records are left at their pinned level for this test, not lowered.
41. **Where values may appear.**
    - Secret values and ciphertexts never appear in any rendered page, message, email or `repr()`.
    - The Account ID and Client ID appear **only** on the connection change page, inside their own inputs (D3). They aren't on the list, either account page, any message, any email or any log.

    This amends 006 criterion 40 for those two values on that one page. A test renders every page named in criterion 14 and searches for each value.
42. **`repr()` stays safe.** `repr()` and `str()` of `ZoomConnection`, `zoom_api.ZoomCredentials`, `ZoomClient` and `HostAccount` show only the slug or the label (test).
43. **Tokens stay out of storage.** 006 criterion 9's check that the token is in no `zoom_*` table and not in Django's cache passes, and its table dump now includes `zoom_zoomconnection`.

### Tests, templates, verification

44. **No test reaches the network.** The project-wide `responses` block stands. Token requests are registered with a matcher on the Basic auth header where a test depends on which secret was sent (criteria 23 and 24).
45. **Template rules.** For `zoom/connections.html`, `zoom/connection_form.html` and every changed template:
    - a header comment naming the purpose and the context;
    - every include ends with `only`;
    - no inline styles;
    - no hard-coded paths;
    - the sprite holds exactly the symbols in use;
    - status is an icon plus a word.

    The pages work without JavaScript. They meet WCAG AA, with touch targets of 44–56 px, at 320, 400, 1024 and 1440 px in light and dark.

    **New components and partials** (D20):
    - `.copy-value` (CSS section 5n) and `.tag--bad` (section 5g, the line after `.tag--brand`) are built as `docs/design/copy-value.md` and `docs/design/tag-bad.md` describe. They use existing tokens only: no new token and no colour literal (the existing token test passes).
    - **The verifier measures `.tag--bad`'s contrast** at the 10.5px semibold tag size, in light (`--c-bad-text` on `--c-bad-soft`, expected about 5.4:1) and dark (expected about 6.2:1). Each must be at least 4.5:1. It also confirms `.copy-value`'s text and help pairs on `--c-surface-2` in both modes.
    - The three new partials, `zoom/partials/connection_tag.html`, `zoom/partials/secret_field.html` and `partials/select_field.html`, follow the same template rules (a header comment naming their `with` variables, `only` on every include of them).
46. **Automated checks** (CLAUDE.md "Verify a change", all five), all passing:
    - `ruff check .` and `ruff format --check .`;
    - `pytest --create-db`;
    - `makemigrations --check --dry-run`;
    - `manage.py check`;
    - `manage.py check --database default`.

    Settings change, so **`check --deploy` runs on the prod stack** with `USE_HTTPS=True`, twice:
    - with `ZOOM_PROVIDER=zoom` and **no credential variable at all**: only `security.W021` may appear;
    - with `ZOOM_PROVIDER=manual`: only W021 and `zoom.W001`.
47. **Prod walkthrough on port 8011** (no real Zoom; never press Check connection on a connected account, which would call Zoom).
    - Start it with `WEB_PORT=8011 ZOOM_PROVIDER=manual docker compose up -d --build`, never by editing `.env`, and wait for `web` to be `healthy`.
    - **The container:**
      - `docker compose exec web env` lists no `ZOOM_S2S_` or `ZOOM_CREDENTIAL` variable;
      - `ls /app` shows no `zoom-credentials.env.example`.
    - **Over HTTP:**
      1. Add a connection `zoom-verify` with obviously fake values. The list shows `Saved` and `Not saved`.
      2. An invalid add with a typed secret shows the "wasn't kept" note, and the page source has no typed secret.
      3. Add a dummy webhook secret on the change page. A signed URL validation `POST` to `/zoom/webhooks/zoom-verify/`, signed with it, returns the exact JSON **without restarting `web`**.
      4. Choose `zoom-verify` on a test account. The change page shows `Set up`, and the list shows `Set up`.
      5. `Check connection` on an account with **no** connection shows criterion 22's first row, with no outbound call.
      6. Static files come from hashed paths.
    - **Screenshots, in the scratchpad:**
      - the connection list, empty and filled, at 1440 and 400;
      - the add page with errors at 1440 and 400;
      - the change page in its secret states at 1440;
      - the account change page's three connection states at 1440.
    - **Clean-up:** unlink and delete `zoom-verify` with a short `manage.py shell` script (there's no delete screen, D14), say so in Verification, and restore the stack that was running before.
48. **Parallel-run safety.** In step 3 only the backend runs `pytest --create-db` (CLAUDE.md, tasks 008 and 010). The verifier is the next agent to do so.
49. **Docs are complete.** The docs writer makes every amendment listed under "Amendments to earlier briefs" below, the README changes, `CLAUDE.md`'s three places (the `zoom` bullet, the environment gotchas, and the shared form partials list, D20), and `docs/CHANGELOG.md`. The reviewer checks the list is fully covered.
50. **The owner's live check** (after this brief passes verification and review, and after agent plan step 7 has taken the dev test accounts Zoom 01–03 out of use (D19); the main session gives the owner these steps, and the verifier records the reported results).
    1. On `Zoom connections`, add the real account's connection (Account ID, Client ID, Client Secret). Choose it on that Zoom account, and press `Check connection`. It shows `The Zoom connection works for {label}.` **with no restart.**
    2. Type a deliberately wrong client secret and save. `Check connection` at once shows criterion 22's `ZoomAuthFailed` text. Type the real one back and save. `Check connection` works again at once.
    3. Then run 006 criterion 48, steps 2, 3 and 5. Step 4's "wrong secret (restart)" is replaced by step 2 above, and no `zoom-credentials.env` step remains.
    4. Then, once the webhook path is reachable from Zoom, run 013 criterion 26 (013's only pending item, D20) with the webhook Secret Token typed on the connection page (013 D6, step 4 amended). Marketplace's **Validate** passes as soon as the page is saved.

### Added after review round 1 (2026-11-02)

51. **Two people saving the same Client ID, or adding the same connection name, at the same moment** (review round 1, N5; D21; the change-page coverage and the name race were settled by the main session, 2026-11-02).
    - **The races:** the form checks before `save()` that the Client ID (criterion 13, `client_id_taken_by`) and, on the add page, the connection name (the `slug` field's `unique` check, run by `ModelForm.validate_unique`) are free. A second person saving at the same moment passes those checks and then hits the `client_id` or `slug` unique constraint as an `IntegrityError`. Two cases are covered:
      - **the same Client ID,** on the add page and on the change page (when an edited Client ID collides the same way; it's the same race);
      - **the same connection name,** on the add page only (the change page has no `slug` field, criterion 12).
    - **What the second person sees:** not a 500. The page re-renders (200) with the field's pinned error, as criterion 13 already words it:
      - `client_id`: `CLIENT_ID_TAKEN`, `The Zoom connection {slug} already uses this Client ID. Each Zoom app needs only one connection.`, where `{slug}` names the connection that won;
      - `slug`: the existing "taken" text, `Another Zoom connection already has this name. Choose a different one.`

      It follows criterion 13 (the error summary's lead, every non-secret value kept) and criterion 14 (neither typed secret sent back, the "wasn't kept" notes shown).
    - **Nothing is half-saved:** no second connection exists, the winning connection is unchanged, and on the change page the edited row keeps its stored values and `credentials_version`.
    - **How:** the save runs inside its own `transaction.atomic()` savepoint, so the request's transaction (`ATOMIC_REQUESTS`) stays usable for the re-render and the lookups. After an `IntegrityError` the view asks the database again which of the two values is now taken (the same `client_id_taken_by` and slug checks the form uses) and adds the pinned error to each field that is. When it collides on both, both errors show. If neither is taken, the error wasn't one of these races, and it is re-raised, not swallowed. The view never reads or shows the database's error text.
    - **Nothing leaks:** no log record, at any level from `apps.zoom`, `django`, `django.db.backends`, `requests` or `urllib3` captured at `DEBUG` as in criterion 40, contains `Duplicate entry`, `IntegrityError`, the Client ID, the Account ID, a secret value or a ciphertext. No `ERROR` record from `django.request` is written, so no error report (500 page or `mail_admins` email) is built.
    - **Tests**, each simulating the race by letting the pre-check pass while another committed connection already holds the value:
      - **Client ID, add:** patch `ZoomConnection.client_id_taken_by` to return nothing for the form's check, then POST to `zoom:connection_add`;
      - **Client ID, change:** the same patch, then POST to `zoom:connection_edit` for a second connection;
      - **connection name, add:** patch `ZoomConnectionForm.validate_unique` to do nothing, then POST to `zoom:connection_add` with the taken slug and a free Client ID.

      Each asserts the status, the field error, the kept values, the row counts and the captured logs above.
    - **Devops part:** the `mail_admins` comment in `config/settings/base.py` names Zoom connection values (criterion 36).

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner's four answers settle who edits, the env file, the timing and the oversight framing. The planner has decided the points the main session asked it to settle (D1–D17). The one point flagged for the owner, C1, is now **closed** by the owner's answer (D18). The designer's proposals, contract gaps and owner question (Design D.13) are settled by the main session and the owner, and recorded as D20. Review round 1's accepted items are recorded as D21.

| # | Point | Planner's recommendation | Owner's answer | Recorded as |
|---|---|---|---|---|
| C1 | The owner said "save credential … encrypted". Should the **Account ID** and **Client ID** be encrypted too, or kept plain and shown back on the connection's change page, with only the two secrets (Client Secret, webhook Secret Token) encrypted? | Keep them plain and show them. They grant nothing without the secret: the Client ID is public by OAuth design, and the Account ID is in every webhook Zoom sends. Showing them lets IT check, by eye, which Zoom app a connection is. | **"Keep IDs readable"** (2026-11-02, relayed by the main session) | **Closed.** D18 (confirms D3; criteria 1, 12, 13 and 41 stand as written) |

**Decisions (the planner's)**

- **D1: A `ZoomConnection` row per Zoom app, chosen on each account. Not fields on `HostAccount`.**
  - **Why a separate row:**
    - 006 D2 lets several accounts share one subscription's app, because the Zoom user is chosen by `HostAccount.email`. Fields on the account would copy the secret into each, and every rotation would mean editing every copy.
    - 013's webhook has **one address and one secret per app** (`/zoom/webhooks/zoom-01/`). On a shared subscription, Zoom sends every user's events to that one address, so the secret belongs to the app, not to an account.
    - `zoom_api`'s token cache is already per app.
    - It keeps 006's "connection name" and 013's slug, `ZoomEvent.slug` and `last_received_at(slug)` exactly as they are.
  - **Cost:** setting up a 1:1 account takes one more step (add the connection, then choose it on the account). The setup is a one-off per paid account (11 in all), and the add page's success message says what to do next.
  - **Rejected:** fields on `HostAccount`. It's simpler for 1:1, but wrong for a shared app and for 013's per-app webhook.
- **D2: A connection's name can't be changed once saved.** It's the path Zoom's Marketplace calls (`/zoom/webhooks/{name}/`), and `ZoomEvent` history and `last_received_at` are keyed by it. Renaming would silently break the webhook and split the "Last heard" history. A wrong name is fixed by adding a new connection and choosing it on the account (D14 explains why the old row isn't deleted yet).
- **D3: Account ID and Client ID are stored plain. The Client Secret and webhook secret are Fernet-encrypted with `HOST_KEY_ENCRYPTION_KEYS`, through `crypto.py`.** Confirmed by the owner (C1, D18).
  - **Why plain IDs:** see C1 and D18. They stay out of logs, lists, messages and emails all the same (criteria 40–41), because 006 criterion 11 already treated them as not-for-logs.
  - **Same keys as host keys:** the owner's choice, relayed. It means one key list, one rotation and one backup rule.
  - **The variable keeps its name.** Renaming it would make every deployment's `.env` and compose file change for no protective gain. Its comments say what it now covers (criteria 36 and 38).
- **D4: One rotation command, renamed `rotate_encryption_keys`. No sibling.**
  - **The danger it removes:** rotation ends by **removing the old key**. If host keys and connection secrets were rotated by two commands, forgetting the second would leave every Zoom connection unreadable. Every booking would then stop at once, and the 11 secrets would have to be fetched from Marketplace again.
  - **One transaction, exit 1 on any unreadable value,** so a script stops before the old key is removed.
  - **No alias for the old name.** The app isn't live, and the README is rewritten in the same brief.
- **D5: Gate every connection screen on `zoom.change_hostaccount`, and give `ZoomConnection` no permissions of its own (`default_permissions = ()`).** The owner named exactly this permission. Separate model permissions would need a migration to grant them to `IT desk`, and would create grantable permissions on the Staff and access page that mean nothing. The key-less viewer, who may see accounts, sees only the connection *state* on the accounts list.
- **D6: Information architecture** (`ux-strategy:information-architecture`). This is a rare task (setup, rotation), so it lives one level under Zoom accounts, not in the sidebar:

  ```
  Zoom links (sidebar group)
  ├── Link requests            zoom:queue
  ├── Timetable                zoom:timetable
  └── Zoom accounts            zoom:accounts            ← [Zoom connections] link (change_hostaccount)
      ├── Add / Change {name}  zoom:account_add / _edit ← "Zoom connection" select; link to the chosen
      │                                                   connection; [Check connection] (unchanged)
      └── Zoom connections     zoom:connections         ← name · used by · details · webhook secret
          ├── Add a Zoom connection   zoom:connection_add
          └── {name}                  zoom:connection_edit ← states, "Address for Zoom's Event
                                                              Subscriptions", used-by links
  ```

  - **Findability:** at most three clicks from anywhere. The Zoom accounts item stays highlighted, so IT always knows where they are.
  - **Labels:** "Zoom connection" is the word already on the account page since 006. The field labels copy Marketplace's own words (`Account ID`, `Client ID`, `Client Secret`, `Secret Token`), so a non-technical IT member can match what they paste to what they see.
  - **Where the link is set:** the **account** chooses its connection (where 006 put the name, and where Check connection lives), and the connection page only lists its users. One place edits the link (DRY).
  - **No connection-level check:** Check connection on the account already proves the token, the user and the licence. A second, token-only check would be a second definition of "works". The save message names the accounts to check.
  - **The webhook address is shown** so IT copies it into Marketplace rather than building it by hand (013 D6, step 2).
- **D7: The secrets are write-only, with no reveal. This is confirmed, unlike the host key (011 D11).**
  - **Why the host key has a reveal:** a teacher stuck in a class needs it read out over the phone, now.
  - **Why these don't:** nobody ever needs to read them out of this app. Whoever administers the Zoom subscription can see or regenerate them in Marketplace at any time. A reveal would only make this app a second place to steal them from.
  - **The rules are 008's host-key rules:** never echoed, dropped from the bound data after an error, `sensitive_*` everywhere, and only the state and "who and when" shown.
- **D8: The token cache follows a `credentials_version` read from the row. No signal and no reset call.**
  - **Why not a reset call on save:** Gunicorn runs several workers, each with its own in-memory token cache (006 D4). A reset in the saving worker can't reach the others.
  - **How the version works:** every operation already reads the connection row, so a version in the cache key makes every worker fetch a fresh token on its next call. No signal is used (CLAUDE.md: no signals for business logic), and nothing is shared between processes.
  - **Only the three token parts bump it.** A webhook-secret change doesn't invalidate a working token.
  - **No locks on connection rows from booking paths** (`of=("self",)`). A connection edit locks only its own row, so it can't deadlock with `approve()`'s request-then-account order.
- **D9: The webhook does one indexed lookup.** 013's 404 for an unknown name or no secret is kept, so the endpoint tells a stranger nothing. An **unreadable** secret is also 404, so it reveals no more to the caller, but it logs one `WARNING`, because unlike a stranger's guess it's a fault the server's operator must fix. `zoom.W002` reports it too (criterion 33).
- **D10: Checks.**
  - **`zoom.E005` existed to validate env variables** (an empty list, missing values, bad names, colliding names). The database makes each of those impossible: required fields with constraints, the slug validator, and a unique slug. It's retired, and its id isn't reused.
  - **`zoom.E004` and `W002` stay database-tagged,** for 006 D11's reason: one unconnected account mustn't stop the site, and the public form, from starting.
  - **`E001`, `E002`, `E003`, `E006` and `W001` are unchanged.** They read `ZOOM_PROVIDER`, the encryption keys and the phone number, none of which is a credential. The main session's list named `E001` and `E002` among the env-reading checks, but neither reads credentials, so neither changes.
  - **`zoom.E003`** (keys missing or invalid) now protects connections as well as host keys, with no change.
- **D11: A schema migration only, with no data migration.** No credentials exist anywhere: `zoom-credentials.env` was never created (owner, relayed), and the dev stack runs `fake`. Any connection *name* typed on an account is dropped, since without credentials it never made an account `ready`. No leftover-env detector is added, because there's nothing to detect.
- **D12: The `.gitignore` and `.dockerignore` lines are kept, with a "retired" comment.**
  - **Why:** old README copies or a habit could still produce a `zoom-credentials.env` holding real secrets. Keeping both lines means that file is never committed and never copied into the image. It costs two lines.
  - **Rejected:** removing them as dead config. The protection is worth more than the tidiness.
- **D13: `HostKeyUnreadable` becomes `SecretUnreadable`, with no alias.** It will be raised for client and webhook secrets too, and `except HostKeyUnreadable` around a client secret would mislead the next reader. It's a mechanical rename inside `apps/zoom`.
- **D14: No delete in this brief (a follow-up).**
  - `HostAccount.zoom_connection` is `PROTECT`, as accounts are never deleted.
  - An unused connection just stays in the list as `No account yet`. If one is abandoned, the README tells the subscription admin to **regenerate its secret in Marketplace**, which makes the stored copy useless.
  - A "Remove an unused connection" action can follow if the owner asks.
- **D15: `django.db.backends` is pinned to `INFO`.** At `DEBUG`, Django logs every SQL statement **with its parameters**. From this brief those include Account IDs, Client IDs and ciphertexts. The `django` logger is already `INFO`, but an explicit pin (like `urllib3`'s, 006 R3) keeps a future `LOG_LEVEL=DEBUG` or a logger tweak from writing them.
- **D16: Accepted by the owner: a database backup plus `HOST_KEY_ENCRYPTION_KEYS` now gives Zoom API access**, not only host keys. Anyone holding both can create, change and delete meetings on every connected account until the secrets are regenerated. It's in the risk register (R1), and the README's backup advice says to keep the keys apart from database backups, and what to do if both leak (criterion 38, docs).
- **D17: The port is 8011 for every HTTP check,** passed inline (`WEB_PORT=8011 …`) and never written to `.env` (another project holds 8010; main session, 2026-10-30).
- **D18: The IDs stay readable** (owner, C1: "Keep IDs readable", 2026-11-02, relayed by the main session).
  - Only the two secrets, the Client Secret and the webhook Secret Token, are encrypted.
  - The Account ID and Client ID are stored plain and shown in their own inputs on the connection's change page only. Criterion 41 still keeps them off the list, the account pages, messages, emails and logs.
  - This confirms D3 as written. Criteria 1, 12, 13 (including the "Client ID already used" check) and 41 stand unchanged.
- **D19: The dev test accounts Zoom 01–03 are switched out of use before the owner's live check** (owner-approved dev-data housekeeping, relayed by the main session, 2026-11-02; agent plan step 7).
  - **Why:** with `ZOOM_PROVIDER=zoom`, `zoom.E004` and `zoom.W002` (criteria 32–33) flag every bookable account with no working connection. In the dev database the test accounts Zoom 01–03 are paid and in use, so they would bury the one real account's results.
  - **It's data, not code.** No migration, fixture or code change; it touches only the dev database.
  - **The model's rule still applies.** `HostAccount.stop_booking_errors()` (brief 008, criterion 17) refuses to take an account out of use while it still has upcoming booked classes, so those test bookings may have to be cancelled first.
- **D20: The Design section's proposals are settled** (main session, 2026-11-02; O1 answered by the owner). Each is pinned in the criteria and the context contract named below. That fixes the contract.
  - **Accepted proposals to pinned copy:**
    - **P1:** the webhook `none` notice's body ends `Add it when you set up the Zoom app's Event Subscription, using the address below.` Zoom's Validate only passes once the app already has the secret, so "once it is set up" sent IT round in a circle (criterion 15).
    - **P2:** "with the add button" means the box head's `+ Add a Zoom connection`. There's no second button inside the empty state, and tests look for it in the head (criterion 10).
    - **P3:** when the saved client secret can't be read, an empty `New client secret` is refused with criterion 13's existing `client_secret` text. Otherwise someone who corrects only an ID is told "Saved" while the connection still can't be used (criteria 12–13).
  - **Accepted contract gaps:**
    - **G1:** `ZoomConnectionForm` sets labels and help per page and state from the Design's D.3 table, the way `HostAccountForm` does for the host key. The texts are pinned in criterion 11.
    - **G2:** the two IDs and the two secrets are `TextInput`s with `autocomplete="off"`, `autocapitalize="none"`, `autocorrect="off"` and `spellcheck="false"`. They render **no `maxlength`**, and the 100/200 limits are checked in `clean_*`, so a paste that's too long is refused, not cut short. The slug keeps `maxlength="40"` (criteria 11 and 13).
    - **G3:** `remove_webhook_secret` also shows when the stored webhook secret can't be read, as long as one is stored, following `remove_host_key` (criteria 2 and 12).
    - **G4:** the new context bool `webhook_address_secure` (the webhook address starts with `https://`) drives the `Zoom can't use this address` warning, so the template makes no URL decision (criterion 15, contract).
    - **G5:** a note only. `account_tag.html` includes `connection_tag.html` for the unreadable state (criterion 21, contract).
  - **Components (D.9):** `.copy-value` and `.tag--bad` are accepted. Their notes, `docs/design/copy-value.md` and `docs/design/tag-bad.md`, are written (G6). The verifier confirms `.tag--bad`'s contrast (criterion 45).
  - **New shared partials:**
    - `zoom/partials/secret_field.html` serves `client_secret`, `webhook_secret` and the existing `host_key`. The host key's rendered output must not change (criterion 14).
    - `partials/select_field.html` renders the account form's `Zoom connection` select (criterion 18).
    - Both are in "Placement and reuse", and `tmd-docs-writer` adds both to CLAUDE.md's shared form partials (agent plan step 6).
  - **O1, the owner's answer:** the secret boxes show what's typed. Each is a plain `type="text"` input with no value, like the host key. `docs/design/password-field.md` doesn't apply to them (criterion 14).
  - **Follow-up, not in 015:** F1, a `Copy address` button (see "Follow-ups").
  - **The gate (agent plan step 0):** it said 013 must be **Done**. 013 can't be Done until the owner's live check (013 criterion 26), and the owner has ordered that check after 015 is built. The gate is now: 013 committed and approved, with only that live check pending. 013 is committed as `ddb1719`, so the gate is met. Criterion 50 step 4 is reworded to match.
- **D21: Review round 1's items are accepted** (main session, 2026-11-02; the review is recorded unchanged under "Review", Round 1). Every item is taken up except N1.
  - **SF1 and N4, the token cache key** (criterion 24). The key becomes `(slug, credentials_version, client_id)`. A connection deleted and re-added under the same name starts again at version 1, so a version alone can't tell the old Zoom app from the new one; the Client ID can. A client built from an older version must not evict a newer version's token, so only **lower** versions of the same slug are dropped. D8 stands: the version, read per operation, is still what makes every worker fetch a fresh token after a save.
  - **SF2, `required` on the client secret** (criteria 11 and 13). `client_secret` renders `required` whenever it is required: on the add page, or on the change page when the saved secret is unreadable. The empty-value error is the field's `required` message and keeps the pinned text. P3 (D20) is unchanged.
  - **SF3, one definition of the help text** (criterion 11). The connection name, Account ID and Client ID help is the model fields' `help_text`, using the pinned add-page text, and the form borrows it. The same rule as 008's SF3: the model's copy had drifted from the pinned one because nothing showed it.
  - **N2, the undated fallbacks** (criterion 15). `Connection details saved.` and `Webhook secret saved.` are pinned. They show only when a connection has no saved-on date, which happens only for rows made outside the screens. No code change.
  - **N5, a simultaneous duplicate Client ID** (new criterion 51; criterion 36). The second person gets the pinned `CLIENT_ID_TAKEN` field error instead of a 500, and no duplicate-entry text or ciphertext reaches a log or an error report. Devops adds Zoom connection values to the `mail_admins` warning comment in `config/settings/base.py`. Two settlements by the main session (2026-11-02), both in criterion 51:
    - **The change page is covered too.** An edited Client ID that collides at the same moment is the same race and gets the same handling.
    - **The connection-name race is folded in.** On the add page, if two people save the same connection name at once, the second gets the `slug` field's existing pinned "already taken" error (`Another Zoom connection already has this name. Choose a different one.`) instead of a 500. The same no-log and no-half-save rules apply, and its test simulates the race the same way, by letting the pre-check pass.
  - **N3, a backend tidy-up** in `rotate_encryption_keys.py` (drop the `CLIENT_SECRET_NAME` conditional and its import). Criterion 34's output is unchanged, so no criterion changes.
  - **N1, not taken up.** The repeated `{name}` link-or-span in `account_form.html` stays as it is.

**Oversight note (for the main session, not an agent task).** The owner counts this brief as a correction of 006 D2. Per CLAUDE.md "Oversight capture", the main session runs `/oversight` when the owner asks for the commit. The `CLAUDE.md` changes that make it durable are authored first by `tmd-docs-writer` (step 6).

**Risk register** (`delivery-execution:risk-register`)

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | A database backup and `HOST_KEY_ENCRYPTION_KEYS` leak together, giving full Zoom API access to every connected account (D16, accepted by the owner) | Low / **High** | **Accept with mitigation.** The README's backup advice says to store the keys apart from database backups. If both leak: regenerate every Client Secret and webhook Secret Token in Marketplace, type them on the connection pages, and rotate the keys (`rotate_encryption_keys`) | a lost or exposed backup | owner, devops |
| R2 | The old key is removed after rotating only some secrets, so every connection becomes unreadable and all booking stops | Low / **High** | **Avoid:** one command, one transaction, exit 1 on any unreadable value (D4). E004 names each affected account | `zoom.E004 … can't be read`, or Check connection's unreadable message | owner, devops |
| R3 | A secret leaks through the HTML (an echoed value), logs (SQL parameters at `DEBUG`), an error page or a `repr()` | Low / **High** | **Avoid:** write-only fields, `sensitive_*`, the `django.db.backends` pin, and a test per channel (criteria 14, 17, 40–42) | a test failure, or the reviewer's sweep | backend, devops, reviewer |
| R4 | A worker keeps using a token from replaced credentials, so a "fixed" secret seems not to work, or a revoked one seems to | Medium / Medium | **Avoid:** a cache keyed by version and Client ID, read per operation (D8, D21; criteria 23–24) | Check connection disagrees with a fresh save | backend |
| R5 | IT mixes up connections (picks the wrong one on an account), so bookings hit the wrong Zoom account | Low / **High** | **Mitigate:** Check connection proves the user exists on that app (006 criterion 36). 013 criterion 31's "gone" double-check stops mass cancels. The Client ID is unique across connections | a `ZoomUserNotFound` on Check connection | IT desk |
| R6 | Dropping `credential_set` loses names someone typed | Low / Low | **Accept:** no credentials existed, so no name ever made an account `ready` (D11) | none | backend |
| R7 | Parallel agents break the test database | Medium / Medium | **Avoid:** only the backend runs `--create-db` in step 3 (criterion 48) | false failures | main session |
| R8 | A credential is mistyped (a stray space, the wrong field) | Medium / Low | **Mitigate:** no-whitespace validation, Marketplace's own labels, and Check connection straight after (criteria 13 and 23) | auth failure on Check connection | IT desk |

**Follow-ups** (recorded, not in this brief)

- **"Remove an unused Zoom connection"** (D14).
- **014's README step "Restart `web` so the next token carries the new scope".** It stays correct, because tokens live in process memory. A later brief could add a version bump on demand (for example a "Get a new token" action) if restarting proves awkward.
- **F1: a `Copy address` button** beside the webhook address (Design D.13, D20). It would be an `app.js` enhancement on a `data-copy` hook: hidden without JS, announcing "Copied" in a `role="status"` line, and needing a secure context for `navigator.clipboard`.

### Amendments to earlier briefs (for `tmd-docs-writer`; each gets a dated note pointing at this brief)

**005**
- **D17** ("host keys are the one secret the database holds"): connection secrets are now stored too, under the same keys.
- **Criterion 46** (the secret-name test): the allowed list grows (criterion 5).
- **The rotation steps:** `rotate_host_keys` becomes `rotate_encryption_keys` (D4).

**006**
- **Requirement, last paragraph, and Scope:**
  - "Credentials come only from the server's environment, never from the database": superseded.
  - The out-of-scope "storing … any Zoom credential in the database": credentials are now stored (tokens still aren't).
- **Terms:** "Zoom-connected account" now means an account whose chosen connection is readable.
- **Criteria:**
  - **2:** env-only, superseded by criteria 1–6 here. The source scan is inverted (criterion 36).
  - **3:** masking of `ZOOM_S2S_SECRETS` is retired; masking is now by `sensitive_*` (criterion 17).
  - **4:** `zoom.E005` is retired (criterion 30).
  - **6:** E004's reasons (criterion 32).
  - **7:** env plumbing is removed (criteria 37–38). The `urllib3` pin stays.
  - **9:** the token cache key (criterion 24).
  - **34:** the connection name field becomes a select (criterion 18).
  - **35:** the states (`missing` becomes `unreadable`; criteria 19, 21).
  - **36:** three message rows (criterion 22).
  - **40:** the Account ID and Client ID appear on the connection change page (criterion 41).
  - **44:** `zoom-credentials.env` no longer exists; the ignore line stays (D12).
  - **46.1:** `check --deploy` needs no dummy credential variables.
  - **47.3:** choose a connection instead of typing `zoom-test`.
  - **48:** the setup step and step 4 (criterion 50).
- **Decisions and risks:**
  - **D2:** superseded by D1–D3 here. This is the owner's correction.
  - **D11:** E005 is gone.
  - **D13:** "credentials … never the database".
  - **D16:** steps 8–11 and "Rotating a secret": type on the connection page, with no recreate.
  - **R3:** the mitigation list.

**008**
- **Criterion 4:** the list column's states, as already amended by 006.
- **The form's field order:** `zoom_connection` replaces `credential_set`.
- **The `HostAccount` docstring:** "the one secret stored".

**011**
- **D11:** a note that no other secret gets a reveal (D7 here).
- **MVT and Placement:** `HostKeyUnreadable` becomes `SecretUnreadable` (D13).

**013**
- **Scope's settings bullet and criterion 1:** the webhook secret is now a field on the connection.
- **Terms:** the "test secret" is set on a test connection.
- **Criteria:**
  - **2:** W002's hint, and its unreadable form (criterion 33).
  - **4:** the lookup (criterion 27).
  - **6:** "no database query" becomes one query.
  - **12:** matching by connection (criterion 28).
  - **24:** the dummy webhook secret is set on a connection, not passed as env.
  - **25:** the walkthrough's dummy secret is typed on the page.
  - **26:** the secret is typed on the page.
  - **29:** the source of `webhook_secret_set`, and the `False` notice's body (criterion 20).
- **Decisions and risks:**
  - **D6, steps 4–5:** type the Secret Token in `Webhook secret` on the connection page and save. Validate passes at once, with no recreate.
  - **D12, first bullet:** "env-only, with no database row" is now a row, but `last_zoom_event_at` stays derived from `ZoomEvent`, as decided.
  - **R7:** rotate by regenerating in Marketplace, then typing the new value on the page.
- **MVT:** `webhook_secret_set_for` is removed.
- **The devops Implementation notes:** left as the historical record, with a one-line note.

**014**
- **Criterion 3:** `credential_set` becomes `zoom_connection` (criterion 28's matching rule).
- **The MVT's `handle_recording_completed(credentials, …)`:** it takes the verified connection.
- **D5 step 4** ("restart `web`" for a new scope) stays, with the reason (tokens live in process memory).

**CLAUDE.md**
- **The `zoom` architecture bullet:**
  - Replace "Zoom credentials never touch the database at all (env only, task 006 D2)" with: credentials live in `ZoomConnection` rows (task 015), typed on the in-app Zoom connections screens by `zoom.change_hostaccount` holders. The Client Secret and webhook secret are Fernet-encrypted with `HOST_KEY_ENCRYPTION_KEYS`, are write-only and are never revealed. Each operation reads them fresh, and the token cache is keyed by `credentials_version`.
  - Name `rotate_encryption_keys`.
  - The webhook does one lookup by connection name.
- **"Environment gotchas":**
  - Remove the "Exception: Zoom credentials" gotcha and replace it with a one-line note that there are no Zoom credential variables, and why.
  - In the `ZOOM_PROVIDER` gotcha, "a working credential set" becomes "a working connection saved on the Zoom connections page".
  - Add the backup rule (D16).
- **"Shared form partials" (Architecture → Templates):** add `partials/select_field.html` (the one way to render a `<select>` inside a form, since `field.html` must never get a choice widget) and note `zoom/partials/secret_field.html` (the write-only secret input for the host key, client secret and webhook secret; `zoom`-only, so it stays under `templates/zoom/partials/`) (D20).

**README**
- **The env table:** the line about `ZOOM_CREDENTIAL_SETS` and `ZOOM_S2S_*`.
- **The dev note** about putting credentials in `zoom-credentials.env`.
- **"Connecting an account to Zoom":** steps 8–10, and rotating a secret.
- **013's "Keeping in step with Zoom":** the webhook-secret step.
- **The `HOST_KEY_ENCRYPTION_KEYS` setup paragraph and rotation paragraph:** the new command, and that it covers connection secrets.
- **Backup advice (D16):** keep the keys apart from database backups, and what to do if both leak.
- **D14's note:** regenerate an abandoned connection's secret in Marketplace.

## MVT plan
<!-- owner: tmd-planner -->

### Models

In `apps/zoom/models.py`, with migration `0010_zoom_connections` (criterion 4).

- **`ZoomConnection`** (criterion 1):
  - **Fields, constraints and `Meta`** as listed there.
  - **Methods** (criterion 2):
    - `set_credentials`;
    - `set_webhook_secret`;
    - `remove_webhook_secret`;
    - `get_client_secret`;
    - `get_webhook_secret`;
    - `credentials()`;
    - `rotate_secrets()`.
  - **Properties:** `credentials_state`, `webhook_secret_state` and `has_webhook_secret`.
  - **Rules on the model:** the version bump and the change record are model rules, so no view decides them.
  - **Docstring:** why a row per app (D1), why the name is fixed (D2), why the IDs are plain (D3), and why there's no reveal (D7).
- **`ZoomConnectionQuerySet.for_management()`:** the list's rows, with the accounts that use each one in display order. It uses `Prefetch("host_accounts", queryset=HostAccount.objects.only("pk", "label", "sort_order", "zoom_connection_id").order_by("sort_order", "label"), to_attr="accounts_in_use")`, so the query count is fixed (criterion 10).
- **`HostAccount`** (criterion 3):
  - `zoom_connection` FK, and `credential_set` removed;
  - `zoom_connection_state` (`none` / `unreadable` / `ready`) and `is_zoom_connected()`;
  - `select_related("zoom_connection")` in `bookable()` and `for_management()`;
  - `of=("self",)` on locking reads;
  - `with_timetable_flag`'s `only()` is unchanged; 009's deferred-fields test swaps `credential_set` for `zoom_connection`.
- **Module functions removed:** `zoom_connection_state_for` and `webhook_secret_set_for`.
- **`crypto.py`:** `HostKeyUnreadable` becomes `SecretUnreadable`, and the docstring is updated (criterion 7).

### Code placement

- **`zoom_api.py`:**
  - `ZoomCredentials` moves here (fields `slug`, `version`, `account_id`, `client_id`, `client_secret`);
  - the cache key is `(slug, version, client_id)`, dropping only lower versions of the same slug (criterion 24, amended by D21);
  - `ZoomClient` is otherwise unchanged.
- **`providers.ZoomProvider._client`:** `host_account.zoom_connection.credentials()`, raising `ZoomNotConnected` when no connection is chosen or it's unreadable.
- **`services.py`:**
  - `_preview_key` (criterion 25);
  - `check_connection`'s states and the three new texts (criterion 22);
  - `handle_event`'s matching by connection (criterion 28);
  - the connection screens' flash texts, beside the account ones (criteria 11–12).
- **`webhooks.py`:** `verify()` does one lookup, returns the verified connection with its decrypted secret, and logs the unreadable case (criterion 27). `url_validation_reply` and `is_from_account` take what `verify` returns. The exact signatures are the backend's choice, and are recorded in its notes.
- **`forms.py`:**
  - `ZoomConnectionForm`, one class for add and change like `HostAccountForm` (D6 of 008). It has the secret-dropping `full_clean`, `*_was_typed`, `remove_webhook_secret` only when a webhook secret is stored (readable or not, D20 G3), labels and help per page and state (G1), the G2 widgets with limits checked in `clean_*`, and P3's refusal of an empty client secret when the saved one is unreadable;
  - `HostAccountForm.zoom_connection` (criterion 18).
- **`checks.py`:**
  - remove `check_credential_sets` and the `config.settings.base` import;
  - E004 and W002 from the database (criteria 30–33).
- **`apps.py`:** unregister E005.
- **Management commands:** `rotate_encryption_keys.py` (new); `rotate_host_keys.py` is removed (criterion 34).
- **`validators.py`:**
  - `validate_credential_set`'s comment no longer mentions env names;
  - new `validate_zoom_value` (trimmed, no whitespace, printable ASCII) is used by the form for the IDs and secrets, with per-field messages (criterion 13).
- **Settings (`tmd-devops`):** criteria 36–39.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| **`zoom:connections`** | `zoom/connections/` | `ZoomConnectionListView(SignedInPermissionMixin, ListView)`; queryset `for_management()`; `never_cache` | `zoom/connections.html` | `zoom.change_hostaccount` |
| **`zoom:connection_add`** | `zoom/connections/add/` | `ZoomConnectionCreateView(…FormViewMixin, CreateView)`; `sensitive_post_parameters("client_secret", "webhook_secret")`, `never_cache` | `zoom/connection_form.html` | `zoom.change_hostaccount` |
| **`zoom:connection_edit`** | `zoom/connections/<int:pk>/edit/` | `ZoomConnectionUpdateView(…FormViewMixin, UpdateView)`; `select_for_update()` on POST; the same decorators | `zoom/connection_form.html` | `zoom.change_hostaccount` |
| `zoom:accounts` (context changes) | as today | as today | `zoom/accounts.html` | as today |
| `zoom:account_add`, `zoom:account_edit` (form and context change) | as today | as today; the change view captures the **stored** connection in `get_object()` (as 006 does the stored name) | `zoom/account_form.html` | as today |
| `zoom:account_check` | as today | as today (texts change) | none (302) | as today |
| `zoom:webhook` | as today | as today (the one lookup) | none | Zoom's signature |

- **Success URL:** `zoom:connections` for both add and change.
- **Shared mixin:** `ZoomConnectionFormViewMixin` holds the shared context. Views never build HTML.
- **No new sidebar entry:** `partials/sidebar.html`'s `Zoom accounts` `aria-current` test adds the three connection URL names. That's a frontend edit, with no new `perms` check beyond the existing `view_hostaccount` gate.

### Context contract

**`zoom/connections.html`** (new)

| Variable | Type | Notes |
|---|---|---|
| `connections` | list of `ZoomConnection` | From `for_management()`. Each exposes: `pk`; `slug`; `accounts_in_use` (list of `HostAccount`: `pk`, `label`; may be empty); `credentials_state` (`"saved"` or `"unreadable"`); `webhook_secret_state` (`"none"`, `"saved"` or `"unreadable"`). Templates read nothing else from a connection. |

**`zoom/connection_form.html`** (new; add and change)

| Variable | Type | Notes |
|---|---|---|
| `form` | `ZoomConnectionForm` | Fields: `slug` (**add only**), `account_id`, `client_id`, `client_secret`, `webhook_secret`, `remove_webhook_secret` (**change only, and only when a webhook secret is stored**: `webhook_secret_state` `"saved"` or `"unreadable"`, D20 G3). Attributes: `client_secret_was_typed` and `webhook_secret_was_typed` (bool). **Labels and help** come from the form, set in `__init__` per page and state, exactly as criterion 11's table (D20 G1). **Widgets** (D20 G2): the IDs and secrets are `TextInput` (`type="text"`) with `autocomplete="off"`, `autocapitalize="none"`, `autocorrect="off"`, `spellcheck="false"` and no `maxlength`; `slug` keeps `maxlength="40"`. The secret widgets never render a value. The template renders `slug`, `account_id` and `client_id` through `partials/field.html`, `client_secret` and `webhook_secret` through `zoom/partials/secret_field.html`, and `remove_webhook_secret` through `partials/check_field.html`. |
| `is_add` | bool | Picks the h1, title, breadcrumb and button (`Add the connection` / `Save changes`). |
| `connection` | `ZoomConnection` or `None` | `None` on add. On change the template reads only: `credentials_changed_at`, `credentials_changed_by` (User or None), `webhook_secret_changed_at` and `webhook_secret_changed_by`. |
| `saved_slug` | str | Change only: the stored name, for the heading, the breadcrumb and the read-only name line. `""` on add. |
| `credentials_state` | str | `"saved"` or `"unreadable"` on change; `"none"` on add. |
| `webhook_secret_state` | str | `"none"`, `"saved"` or `"unreadable"`; `"none"` on add. |
| `last_zoom_event_at` | aware datetime or `None` | Only when `webhook_secret_state == "saved"`; otherwise `None`. |
| `webhook_address` | str | Change only: the absolute `zoom:webhook` URL for `saved_slug`. `""` on add. Rendered in `.copy-value`. |
| `webhook_address_secure` | bool, **new (D20 G4)** | Change only: `webhook_address.startswith("https://")`, worked out in the view. `False` drives the `Zoom can't use this address` notice (criterion 15). `False` on add, where nothing reads it. |
| `accounts_in_use` | list of `HostAccount` (`pk`, `label`) | Change only; empty on add. |

Flash messages: criteria 11–12, at the `success` level, on `zoom:connections`.

**`zoom/account_form.html`** (changed; replaces the 006 and 013 connection variables)

| Variable | Type | Notes |
|---|---|---|
| `form.zoom_connection` | bound `ModelChoiceField` (select) | Replaces `form.credential_set`. Rendered through the new shared `partials/select_field.html` with `narrow=True` (Design D.7.1, D20), never `field.html` (CLAUDE.md). |
| `form.host_key`, `form.key_was_typed` | (unchanged) | Now rendered through `zoom/partials/secret_field.html` with `was_typed=form.key_was_typed`, the pinned host-key note and `narrow=True`. The rendered output is unchanged (criterion 14, D20). |
| `zoom_connection_state` | str | `"ready"`, `"unreadable"` or `"none"`, from the **stored** link; `"none"` on add. |
| `zoom_connection_name` | str | The stored connection's slug, or `""`. |
| `zoom_connection_url` | str | The stored connection's `zoom:connection_edit` URL when there is one **and** `can_manage_connections` is true; otherwise `""`. |
| `can_manage_connections` | bool | `zoom.change_hostaccount`. It shows the `Zoom connections` link and turns the name into a link. |
| `webhook_secret_set` | `True`, `False` or `None` | As in 013 criterion 29, now from the stored connection (criterion 20). |
| `last_zoom_event_at` | aware datetime or `None` | As in 013, by the stored connection's slug. |
| (unchanged) | | `account`, `is_add`, `host_key_state`, `saved_label`, `can_check_connection`, `upcoming_count`, `next_class_start`, `can_reveal_host_key`, `last_key_reveal`, `key_reveal_count`. |

**`zoom/accounts.html`** (changed)

| Variable | Type | Notes |
|---|---|---|
| `accounts` | list of `HostAccount` | `account.zoom_connection_state` is now `"ready"`, `"unreadable"` or `"none"`. `needs_zoom_connection` is unchanged. |
| `can_manage_connections` | bool, **new** | `zoom.change_hostaccount`; shows the `Zoom connections` link. |
| (unchanged) | | `can_add`, `can_change`, `can_review`. |

**`zoom/partials/account_tag.html`** (changed): for `kind="zoom"`, `state` takes `"ready"`, `"unreadable"` or `"none"` (`"missing"` is retired). The words are `Set up`, `Can't be read` and `Not set up` (criterion 21). For `"unreadable"` it includes `zoom/partials/connection_tag.html` with `state="unreadable" only` (D20 G5).

**New partials** (D20; each is included with `… only`)

| Partial | `with` variables | Notes |
|---|---|---|
| `zoom/partials/connection_tag.html` | `state`: `"saved"`, `"none"` or `"unreadable"` | The one definition of these tags: `Saved` (`tag--plain`, `lock`), `Not saved` (`tag--warn`, `alert-triangle`), `Can't be read` (`tag--bad`, `alert-octagon`). Used by `zoom/connections.html` for both state columns, and by `account_tag.html` (criteria 10 and 21). |
| `zoom/partials/secret_field.html` | `field` (BoundField), `was_typed` (bool), `note` (str, the pinned "wasn't kept" sentence), `narrow` (bool, optional) | Writes a `type="text"` input with **no `value` attribute**. The note shows above the field as `id="<name>-note"` when `was_typed`. `aria-describedby` lists `<name>-error`, `<name>-note` and `<name>-help`, only those that exist, in that order. Used for `client_secret` and `webhook_secret` (notes from criterion 14, not narrow) and `host_key` (008's note, narrow) (criterion 14). |
| `partials/select_field.html` | `field` (BoundField of a select or `ModelChoiceField`), `narrow` (bool, optional) | Shared: `.field` with a `<label for>`, help as `id="<name>-help"`, `aria-describedby` `<name>-error` then `<name>-help`, `aria-invalid` only with errors, and options from iterating the bound field (the empty label, order and selected choice all come from the form). Used by `account_form.html`'s `zoom_connection` (criterion 18). |

**Command output** (`rotate_encryption_keys`): criterion 34's lines. **Check messages:** criterion 22.

### Placement and reuse

- **`apps/zoom` only.** No new app: connections exist only to serve Zoom accounts. `config/` and the compose files are changed by `tmd-devops` only.
- **Reused:**
  - 008's write-only key pattern (`full_clean` dropping a typed value, `*_was_typed`, `sensitive_*`);
  - 008's `stop_booking_errors`-style row lock on POST;
  - `crypto.py`'s `encrypt`, `decrypt` and `rotate`;
  - 006's `validate_credential_set` and its error text, and its check messages;
  - 013's `ZoomEvent.objects.last_received_at`;
  - 010's `SignedInPermissionMixin` and `templates/403.html`;
  - the shared form partials (`partials/error_summary`, `field`, `field_error`, `check_field`);
  - `zoom/partials/account_tag.html` and `zoom/partials/when.html`;
  - `docs/design/form-section.md` and `flash-messages.md`. `password-field.md` does **not** apply: the secret boxes are plain text inputs (owner, O1; D20).
- **New, built once and reused (D20):**
  - **`zoom/partials/secret_field.html`:** the write-only secret input, used three times: the new `client_secret` and `webhook_secret`, and the account page's existing `host_key`, which today is written out by hand in `account_form.html`. Moving the host key onto it puts one rule in one place. Its rendered output must not change (criterion 14). It lives under `zoom/partials/` because only `zoom` has secrets.
  - **`partials/select_field.html`:** shared, beside `field.html`. No shared partial renders a `<select>` inside a form today, and `field.html` must never get a choice widget (CLAUDE.md). It's first used by the account form's `Zoom connection` select.
  - **`zoom/partials/connection_tag.html`:** the one definition of a connection state's tag, used by the connection list and, for `Can't be read`, by `account_tag.html`.
  - **CSS components `.copy-value` and `.tag--bad`** (`static/css/style.css` sections 5n and 5g), as specified in `docs/design/copy-value.md` and `docs/design/tag-bad.md`. They use existing tokens only.
- **Django ships:** `CreateView`, `UpdateView`, `ListView`, `ModelForm`, `ModelChoiceField`, `Prefetch`, `CheckConstraint`, `sensitive_post_parameters`, `sensitive_variables`, `never_cache`, `build_absolute_uri` and `messages`.
- **No new dependency.**

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Gate:** brief 013 is committed and approved, with only its owner live check (013 criterion 26) pending (D20). 013 can't be Done before that check, and the owner has ordered it after 015 is built. 013 is committed as `ddb1719`, so the gate is **met**. **Port 8011** for every HTTP check, passed inline (`WEB_PORT=8011 …`), never written to `.env` (D17).
1. **`tmd-ui-designer`:**
   - writes the Design section for `zoom/connections.html`, `zoom/connection_form.html`, the account form's `Zoom connection` section (criteria 18–20), the accounts list's link and tag (21) and the sidebar highlighting (9);
   - the states in criteria 10, 14, 15 and 19, at 320, 400, 1024 and 1440 px in both modes;
   - accessibility (the "wasn't kept" notes in `aria-describedby`, select labelling, the selectable webhook address);
   - no-JS behaviour;
   - whether the secret inputs follow `docs/design/password-field.md`.

   Copy changes go to the main session as proposals (pinned-copy rule). Gaps in the context contract are listed as G-items. **The contract is fixed when the main session accepts them.**
2. **In parallel, once step 1's contract is fixed:**
   - **2a. `tmd-django-backend`:**
     - criteria 1–8, 10–35, 40–44 and 48 (the model, migration `0010`, `crypto` rename, forms, views, URLs, `zoom_api`, providers, services, webhooks, checks, the command, the test-helper rewrite);
     - every `apps/zoom` test change, and the tests for criteria 1–35, 40–43.

     It **stops reading** every `ZOOM_S2S_*` and `ZOOM_CREDENTIAL_*` setting and the `config.settings.base` import, but **does not edit `config/`**. **Only the backend runs `pytest --create-db`.** It reports "backend pytest run finished".
   - **2b. `tmd-frontend`:**
     - the two new templates;
     - the three new partials (D20): `zoom/partials/connection_tag.html`, `zoom/partials/secret_field.html` and the shared `partials/select_field.html`;
     - `account_form.html`'s connection section (the select through `select_field.html`) and its host key moved onto `secret_field.html` with unchanged output, `accounts.html`'s link, `account_tag.html`'s states;
     - the CSS components `.copy-value` and `.tag--bad`, from `docs/design/copy-value.md` and `docs/design/tag-bad.md` (both written, G6);
     - the sidebar's `aria-current` names;
     - the header comments, following the Design and the contract.

     It **never uses `--create-db`**, and runs `pytest` only after the main session passes on the backend's signal.
3. **`tmd-devops`, after 2a** (it can overlap 2b's tail).
   - **Its work:** criteria 36–39:
     - remove the credential block from `base.py`;
     - delete `zoom-credentials.env.example`;
     - remove `compose.yaml`'s `env_file`;
     - recomment the ignore lines;
     - `.env.example` and the compose comments;
     - the `django.db.backends` pin;
     - rewrite `apps/core/test_zoom_settings.py`.
   - **Why after the backend, not alongside it:** `apps/zoom/checks.py` imports `zoom_credential_env_prefix` from `base.py` when the app loads. Removing the block first would stop Django from starting, so every other agent's tests would fail until the backend caught up.
   - **Its checks:** it runs `pytest apps/core` (no `--create-db`), `ruff`, and `docker compose config --quiet` for both stacks.
4. **`tmd-test-verifier`:**
   - criteria 1–48, with the automated checks (46), both `check --deploy` runs, and the prod walkthrough on **8011** (47);
   - it's the next agent to run `pytest --create-db`, after steps 2 and 3 finish;
   - FAIL returns to the owning agent.
5. **`tmd-code-reviewer`** (read-only), security first:
   - no secret or ciphertext in HTML, logs (including SQL parameters), messages, emails, `repr` or error pages;
   - write-only fields, and no reveal path;
   - `sensitive_*` coverage and CSRF;
   - the version-keyed token cache, with no stale credentials in any worker;
   - one webhook lookup, and 013's 404s kept;
   - no locks on connection rows from booking paths;
   - one rotation command that can't leave a secret behind;
   - no env read or `ZOOM_S2S_` remnant;
   - then DRY, thin views and pinned copy.

   CHANGES REQUESTED returns to step 2 or 3, then step 4 again.

   **Round 1 fix cycle** (D21, 2026-11-02):
   - **5a. `tmd-django-backend`:** SF1 and N4 (criterion 24), SF2 (criteria 11 and 13), SF3 (criterion 11, editing migration `0010` in place), N3, and criterion 51's view handling, with their tests. It's the only agent running `pytest --create-db` in this cycle.
   - **5b. `tmd-devops`,** in parallel with 5a (comment only, no `pytest --create-db`): criterion 36's `mail_admins` comment.
   - **5c. `tmd-test-verifier`:** criteria 1–48 again, plus criterion 51, after 5a and 5b finish.
   - **5d. `tmd-code-reviewer`:** round 2.
6. **`tmd-docs-writer`:**
   - criterion 49: every item under "Amendments to earlier briefs";
   - the README (setup, rotation, backup advice D16, D14's note);
   - `CLAUDE.md` (the zoom bullet and the environment gotchas, written before the main session's `/oversight` commit, since it makes the episode durable);
   - `CLAUDE.md`'s shared form partials: add `partials/select_field.html` and `zoom/partials/secret_field.html` (D20);
   - `docs/CHANGELOG.md`;
   - then closes the brief. Status stays `Verifying` until criterion 50's owner check is reported, as 006 and 011 did.
7. **Dev-data housekeeping, before the owner's live check** (D19; owner-approved; data, not code). In the **dev** database only, take the dev test accounts **Zoom 01, Zoom 02 and Zoom 03** out of use (untick `In use`), so the `zoom` provider's `E004` and `W002` don't flag them.
   - Do it on the in-app `Change {name}` page, as an IT user. That path runs `stop_booking_errors()` and leaves a normal record.
   - **If the page refuses** with criterion 17's "still has … booked classes" error, first cancel those test bookings with `Cancel this booking` (brief 011). Under `fake` this makes no Zoom call. Then untick `In use` again.
   - **Afterwards:** `manage.py check --database default` with `ZOOM_PROVIDER=zoom`, passed inline, names none of the three accounts.
   - **Report:** which accounts were switched off, and which test bookings, if any, were cancelled.
   - **Who does it:** whichever agent the main session chooses, for example `tmd-test-verifier` straight after step 4, or the main session through an agent. It doesn't change the production database or any repo file.
8. **Main session:** gives the owner criterion 50's steps, then the 006 and 013 live checks through the new screen. It runs `/oversight` for the 006 D2 correction when the owner asks for the commit.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

Written 2026-11-02, inside the approved f-desk direction. It reuses brief 008's account screens, 011's write-only and secret patterns, and 013's account-page notices.

- Every **pinned** string in the criteria is used exactly as written. Where this section's wording differs from a criterion, **the criterion wins**.
- Wording marked *design copy* is new in this section. The form owns every label and help text (contract: "Labels, help and widget attributes come from the form"), so the backend copies the help texts in D.3 onto `ZoomConnectionForm`.
- Proposals to change pinned text (P), contract gaps (G), owner questions (O) and follow-ups (F) are in D.13.

**Summary of what changes**

| Kind | What |
|---|---|
| New templates | `zoom/connections.html` (D.2), `zoom/connection_form.html` (D.3, D.4) |
| New partials | `zoom/partials/connection_tag.html` (D.6), `zoom/partials/secret_field.html` (D.5), `partials/select_field.html` (D.7.1, shared) |
| Changed templates | `zoom/account_form.html` (D.7), `zoom/accounts.html` (D.8), `zoom/partials/account_tag.html` (D.6), `partials/sidebar.html` (D.1) |
| New components | `.copy-value` (D.9.1) and the `.tag--bad` modifier (D.9.2). Nothing else in the kit fits either one. Both use only existing tokens |
| Tokens | **none new** |
| Icons | **none new.** `lock`, `link`, `alert-octagon`, `alert-triangle`, `check-circle`, `info` and `plus` are all in the sprite already |
| JS | **none new.** The error-summary focus, the flash Close button and the busy button already cover everything |

### D.1 Information architecture and navigation

This follows the planner's D6. There's no new sidebar item. The connection pages sit one level under Zoom accounts.

```
Zoom links (sidebar)
└── Zoom accounts  ▌ (aria-current on all six pages below)
    ├── [Zoom connections] secondary button in the list's box head (can_manage_connections)
    ├── Add / Change {label}  ← "Zoom connection" select, "Zoom connections" link, notice name links to the connection
    └── Zoom connections                      zoom:connections
        ├── [+ Add a Zoom connection]         zoom:connection_add
        └── {slug} (row link)                 zoom:connection_edit  ← "Used by" links back to each account
```

- **Sidebar (criterion 9).** In `partials/sidebar.html`, the `Zoom accounts` link's `aria-current="page"` test adds `zoom:connections`, `zoom:connection_add` and `zoom:connection_edit`. Its gate stays `perms.zoom.view_hostaccount`. Update the header comment to name the three new view names.
- **Titles, h1s and breadcrumbs.** The breadcrumbs are pinned. Every crumb before the last one is a link (`partials/crumb.html`, `current=False`).

| Page | `<title>` and h1 | Crumbs |
|---|---|---|
| List | `Zoom connections` | `Zoom accounts` → `zoom:accounts` › `Zoom connections` (current) |
| Add | `Add a Zoom connection` | `Zoom accounts` › `Zoom connections` → `zoom:connections` › `Add a Zoom connection` (current) |
| Change | *design copy* `Change the Zoom connection {saved_slug}` | `Zoom accounts` › `Zoom connections` › `{saved_slug}` (current) |

- **Why the change h1 says "the Zoom connection".** Connection names usually match account names (`zoom-01` and `Zoom 01`). `Change zoom-01` would read like the account page's `Change Zoom 01`. Wrap the h1 in `span.break-anywhere`, as `account_form.html` does.

### D.2 The list: `zoom/connections.html`

**Structure, top to bottom, inside `<main>`:**

1. `.titlebar` (h1 and crumbs, D.1), then `partials/messages.html` from `base.html`. The success flashes from add and change land here.
2. `section.box[aria-labelledby="connections-title"]`:
   - `.box__head`:
     - `h2.box__title#connections-title` `Connections ({n})`, where `{n}` is `connections|length`;
     - `a.button.button--primary` → `zoom:connection_add`, with the `plus` icon (`aria-hidden`) and `Add a Zoom connection`. Everyone who can see this page may add, so there's no condition on the button.
   - `.box__body`:
     - with connections:
       - `p.box__lead` *design copy*: `Each Zoom connection holds one Zoom app's details, so this site can book classes through it. For safety, saved secrets are never shown.`
       - then `.datagrid-wrap` > `table.datagrid.datagrid--wrap-tags[role="table"]`, with the explicit roles copied from `accounts.html`.
     - with none: the `.empty` state (below).

**Table, column by column**

| # | `<th scope="col">` | Cell | Phone label (`span.datagrid__label`, `aria-hidden`) |
|---|---|---|---|
| 1 | `Name` | `<th scope="row" role="rowheader">` holding `a.datagrid__ref.tap-link.break-anywhere[translate="no"]` → `zoom:connection_edit connection.pk`. Its content is `<span class="visually-hidden">Change </span>{{ connection.slug }}`, so the link list reads "Change zoom-01" | `Name` |
| 2 | `Used by` | When `accounts_in_use` has items: `span.datagrid__stack` with one `a.tap-link.break-anywhere` per account → `zoom:account_edit account.pk`. Each link's content is `<span class="visually-hidden">Change </span>{{ account.label }}`. Otherwise: `span.text-muted` `No account yet` (pinned) | `Used by` |
| 3 | `Connection details` | `zoom/partials/connection_tag.html` with `state=connection.credentials_state` | `Connection details` |
| 4 | `Webhook secret` | `connection_tag.html` with `state=connection.webhook_secret_state` | `Webhook secret` |

- `<caption class="visually-hidden">`: `Zoom connections, by name`.
- **`datagrid--wrap-tags`:** at 320px a phone card's value column is only about 76px wide, so a tag must be able to wrap. The class's CSS comment still names "Missing on the server". The frontend may refresh that comment to `"Can't be read"`. This is a comment-only change.
- **Nothing else from a connection is printed.** The template reads only `pk`, `slug`, `accounts_in_use`, `credentials_state` and `webhook_secret_state` (criterion 10).

**Desktop (1440, after a save):**

```
┌────────────┬──────────────────────────────────────────────────────────────────────────────┐
│ ZOOM LINKS │ Zoom connections                    Home › Zoom accounts › Zoom connections │
│  Link req. │ ┌──────────────────────────────────────────────────────────────────────────┐ │
│  Timetable │ │ ✓ Saved the Zoom connection zoom-02. To make sure Zoom accepts it, press  │ │ flash (ok)
│ ▌Zoom acc. │ │   Check connection on Zoom 02 and Zoom 05.                           (x) │ │
│            │ └──────────────────────────────────────────────────────────────────────────┘ │
│            │ ┌──────────────────────────────────────────────────────────────────────────┐ │
│            │ │ Connections (3)                              [ + Add a Zoom connection ] │ │
│            │ ├──────────────────────────────────────────────────────────────────────────┤ │
│            │ │ Each Zoom connection holds one Zoom app's details, so this site can book │ │ lead (muted)
│            │ │ classes through it. For safety, saved secrets are never shown.           │ │
│            │ │ Name      Used by          Connection details    Webhook secret          │ │
│            │ │ ──────────────────────────────────────────────────────────────────────── │ │
│            │ │ zoom-01   Zoom 01          [🔒 Saved]            [🔒 Saved]               │ │
│            │ │ zoom-02   Zoom 02          [🔒 Saved]            [△ Not saved]            │ │
│            │ │           Zoom 05                                                        │ │
│            │ │ zoom-09   No account yet   [⬣ Can't be read]     [⬣ Can't be read]        │ │
│            │ └──────────────────────────────────────────────────────────────────────────┘ │
└────────────┴──────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400).** This is the ported card pattern. The Add button wraps under `Connections (3)` at its natural width.

```
┌──────────────────────────────────────┐
│ ☰  (top bar)                         │
│ Zoom connections                     │
│ Home › Zoom accounts › Zoom conn…    │
│ ┌──────────────────────────────────┐ │
│ │ Connections (3)                  │ │
│ │ [ + Add a Zoom connection ]      │ │
│ ├──────────────────────────────────┤ │
│ │ Each Zoom connection holds one … │ │
│ │ ┌──────────────────────────────┐ │ │
│ │ │ Name        zoom-02 (link)   │ │ │  44px tap rows
│ │ │ Used by     Zoom 02 (link)   │ │ │
│ │ │             Zoom 05 (link)   │ │ │
│ │ │ Connection  [🔒 Saved]       │ │ │
│ │ │ details                      │ │ │
│ │ │ Webhook     [△ Not saved]    │ │ │
│ │ │ secret                       │ │ │
│ │ └──────────────────────────────┘ │ │
└──────────────────────────────────────┘
```

**States (list)**

| State | What shows |
|---|---|
| Default | The box, with the lead and the table |
| Empty | The head still shows `Connections (0)` and the Add button. In place of the lead and the table: `.empty` > `span.disc.disc--64` (the `link` icon) + `<h3>No Zoom connections yet.</h3>` + `<p>Add one for each paid Zoom subscription.</p>`. Together these are criterion 10's pinned text, split as on the accounts list. There's no second Add button: the head's button is the page's only Add action (008 D.1; see P2) |
| After add or change | The redirect lands here with the pinned `success` flash (criteria 11–12) above the box |
| Loading | None. It's a full page load with nothing async |
| Signed out / no permission | Handled by the view: a redirect to sign in, or `templates/403.html` (criterion 8) |
| Server error | Django's own 500 page. There's nothing page-specific |

### D.3 Add and change: `zoom/connection_form.html` (one template; `is_add` picks the words)

**Structure, top to bottom, inside `<main>`:**

1. `.titlebar` (D.1).
2. `partials/error_summary.html` with `form=form lead="We couldn't save this Zoom connection yet." only` (pinned lead). It renders only after a failed POST.
3. One `.box` with no head (the h1 already names the page) > `.box__body` > `.box__form` (640px) > `<form method="post" novalidate>`. The form holds `{% csrf_token %}`, three `fieldset.formsection` blocks (the same three on both pages) and `.form-actions`.

**On-screen order = the form's field order = the error summary's order** (criterion 11, plus `remove_webhook_secret` last):

| Section (`legend.formsection__title`) | Add | Change |
|---|---|---|
| **The connection** | `slug` through `partials/field.html` with `narrow=True` | No input (criterion 12). `div.stack` > `dl.facts` with `Connection name` → `{saved_slug}` (`dd[translate="no"]`) and `Used by` → the account links (`span.tags` > one `a.tap-link.break-anywhere` per account, the same link content as D.2), or `span.text-muted` `No account yet`. Then `p.text-muted` *design copy*: `The name can't be changed, because it's part of the address Zoom sends changes to.` |
| **App credentials** | `p.box__lead` (intro, below), then `account_id` and `client_id` through `field.html` (full width), then `client_secret` through `zoom/partials/secret_field.html` (D.5) | The credentials state notice (D.4.1), then the same intro and fields. `account_id` and `client_id` are prefilled (criterion 12) |
| **Changes made in Zoom** | `p.box__lead` (intro, below), then `webhook_secret` through `secret_field.html` | The webhook state notice (D.4.2), the intro, the address block (D.4.3), `webhook_secret` through `secret_field.html`, then `remove_webhook_secret` through `partials/check_field.html` when the form has it |

**Why these section names.** `App credentials` is Marketplace's own page name, so IT sees the same words on both screens. The pinned errors already say "the App Credentials page". `Changes made in Zoom` matches the account page's `Changes made in Zoom aren't seen here` notice, so the cause and the fix share words. It avoids "webhook" in a heading; the word stays only in the pinned field label.

**Section intros** (*design copy*, `p.box__lead`, the first child after the legend; it's muted body text):

| Section | Add | Change |
|---|---|---|
| App credentials | `In Zoom's App Marketplace (marketplace.zoom.us), open this subscription's Polymath TMD app, then App Credentials. Copy each value from there and paste it here.` | the same |
| Changes made in Zoom | `Zoom can tell this site when a class is changed or deleted directly in Zoom. You can set this up later, on this connection's page.` | `Zoom can tell this site when a class is changed or deleted directly in Zoom. That needs the address below and the Zoom app's Secret Token.` |

"Polymath TMD" is the app name the README tells admins to use (README "Connecting an account to Zoom", step 2).

**Labels and help text** (labels are pinned where marked; the rest is *design copy* for the form, G1):

| Field | Label | Help (`id="<name>-help"`) |
|---|---|---|
| `slug` (add only) | `Connection name` (pinned) | `A short name for this Zoom app, like zoom-01. Use lower-case letters, numbers and hyphens. It can't be changed later, because it's part of the address Zoom sends changes to.` |
| `account_id` | `Account ID` | `Copy the Account ID from App Credentials and paste it here.` |
| `client_id` | `Client ID` | `Copy the Client ID from App Credentials and paste it here.` |
| `client_secret`, add | `Client secret` | `Copy the Client Secret from App Credentials and paste it here. For safety, it's never shown again once saved.` |
| `client_secret`, change, `credentials_state == "saved"` | `New client secret` (pinned) | `Leave it empty to keep the saved one. If the Client Secret was regenerated in Zoom, paste the new one here.` |
| `client_secret`, change, `"unreadable"` | `New client secret` (pinned) | `Paste the Client Secret from App Credentials. The saved one can't be used.` |
| `webhook_secret`, add | `Webhook secret` | `Optional. The Secret Token from the Event Subscriptions part of the Zoom app. You can add it later, on this connection's page, which also shows the address Zoom needs.` |
| `webhook_secret`, change, `"none"` | `New webhook secret` (pinned) | `Paste the Secret Token from the Event Subscriptions part of the Zoom app, and save. Then press Validate in Zoom.` |
| `webhook_secret`, change, `"saved"` | `New webhook secret` (pinned) | `Leave it empty to keep the saved one. If the Secret Token was regenerated in Zoom, paste the new one here.` |
| `webhook_secret`, change, `"unreadable"` | `New webhook secret` (pinned) | `Paste the Secret Token from the Event Subscriptions part of the Zoom app. The saved one can't be used.` |
| `remove_webhook_secret` | `Remove the saved webhook secret` (pinned) | `Tick this if the saved secret is wrong and you don't have the new one yet. Changes made in Zoom then stop being seen here.` |

- The add labels say `Client secret` and `Webhook secret` in sentence case, to match the pinned change labels. The help names Zoom's own terms (`Client Secret`, `Secret Token`), so IT can match what they paste to what Marketplace shows (D6).
- **Errors** are criterion 13's pinned texts, each under its control as `.field__error` (the `alert-circle` icon plus the words) and linked from the summary. Every non-secret value is kept. Both secret inputs are always empty, with the "wasn't kept" note (D.5).

**`.form-actions`:** `button.button.button--primary[type=submit]` reading `Add the connection` (add) or `Save changes` (change), then `a.button.button--quiet` → `zoom:connections` reading `Cancel`. Below 600px both are full width (the existing rule). There's no busy state, because saving doesn't call Zoom.

**Add, desktop (1440), after an invalid POST with both secrets typed:**

```
Add a Zoom connection                   Home › Zoom accounts › Zoom connections › Add a Zoom connection
┌ ⬣ We couldn't save this Zoom connection yet. 2 things need your attention. ┐  error summary (focused by JS)
│   • Another Zoom connection already has this name. Choose a different one.   │  link → #id_slug
│   • Paste the Client ID from the App Credentials page of the Zoom app. It    │  link → #id_client_id
│     has no spaces.                                                           │
└──────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────┐
│ ┌──── .box__form, 640px ──────────────────────────┐                          │
│ │ The connection                                   │                          │
│ │ Connection name                                  │                          │
│ │ A short name for this Zoom app, like zoom-01. …  │                          │
│ │ [zoom-01         ]  ← 2px error border            │                          │
│ │ (!) Another Zoom connection already has this …   │                          │
│ │ ──────────────────────────────────────────────── │                          │
│ │ App credentials                                  │                          │
│ │ In Zoom's App Marketplace (marketplace.zoom.us), │                          │
│ │ open this subscription's Polymath TMD app, …     │                          │
│ │ Account ID                                       │                          │
│ │ Copy the Account ID from App Credentials and …   │                          │
│ │ [AbC1dEf2GhI3jKl4MnO5pQ                       ]  │  kept                    │
│ │ Client ID                                        │                          │
│ │ Copy the Client ID from App Credentials and …    │                          │
│ │ [xYz 123                                      ]  │  kept, as typed          │
│ │ (!) Paste the Client ID from the App Credentials │                          │
│ │     page of the Zoom app. It has no spaces.      │                          │
│ │ ┌ △ For your safety, the client secret you ────┐ │  notice--warn, #client_secret-note
│ │ │   typed wasn't kept. Type it again.          │ │                          │
│ │ └──────────────────────────────────────────────┘ │                          │
│ │ Client secret                                    │                          │
│ │ Copy the Client Secret from App Credentials …    │                          │
│ │ [                                             ]  │  always empty            │
│ │ ──────────────────────────────────────────────── │                          │
│ │ Changes made in Zoom                             │                          │
│ │ Zoom can tell this site when a class is changed  │                          │
│ │ or deleted directly in Zoom. You can set this …  │                          │
│ │ ┌ △ For your safety, the webhook secret you ───┐ │                          │
│ │ │   typed wasn't kept. Type it again.          │ │                          │
│ │ └──────────────────────────────────────────────┘ │                          │
│ │ Webhook secret                                   │                          │
│ │ Optional. The Secret Token from the Event …      │                          │
│ │ [                                             ]  │                          │
│ │                                                  │                          │
│ │ [ Add the connection ]  Cancel                   │                          │
│ └──────────────────────────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Add, phone (400), the same errors:** this is one column. The summary is at the top, the inputs are full width (`.input--narrow` lifts below 600px), and the notes and errors sit in the same order as on desktop. The two buttons are full width and stacked: `[ Add the connection ]`, then `[ Cancel ]`.

### D.4 The change page's state blocks (criterion 15)

None of these blocks has a `role` or a `tabindex`. They're lasting page content, not alerts, and they never take focus. Dates are `{{ value|class_date }}`, and the person is `{{ user }}`, as on the host key's line. The `{when}` value is `zoom/partials/when.html`.

#### D.4.1 Connection details (the first child of **App credentials** after the legend, before the intro)

| `credentials_state` | Notice | Icon | Text |
|---|---|---|---|
| `"saved"` | `notice--ok` | `check-circle` | `<p>`: `Connection details saved on {connection.credentials_changed_at\|class_date} by {connection.credentials_changed_by}.` (pinned). When `credentials_changed_by` is empty, drop ` by {name}` |
| `"unreadable"` | `notice--bad` | `alert-octagon` | `<p>`: `The client secret is saved, but it can't be read with the server's current encryption keys. Type it again.` (pinned) |

#### D.4.2 Webhook secret (the first child of **Changes made in Zoom** after the legend)

| `webhook_secret_state` | Notice | Icon | Content (`div.notice__body`) |
|---|---|---|---|
| `"saved"` | `notice--ok` | `check-circle` | `p`: `Webhook secret saved on {date} by {name}.` (pinned; ` by {name}` is dropped when empty). Then `p`: `Last heard from Zoom on {when}.` when `last_zoom_event_at`, otherwise `Nothing heard from Zoom yet.` (pinned) |
| `"none"` | `notice--warn` | `alert-triangle` | `p.notice__title` `No webhook secret saved`, then `p` with the pinned body. P1 proposes rewording its last sentence |
| `"unreadable"` | `notice--bad` | `alert-octagon` | `p`: `A webhook secret is saved, but it can't be read with the server's current encryption keys. Type it again.` (pinned) |

- **Why `none` is `warn`, not `note`.** The account page already shows this same fact as a `warn` notice (`Changes made in Zoom aren't seen here`). The same fact gets the same tone on both pages.

#### D.4.3 `Address for Zoom's Event Subscriptions` (change only; after the intro, before the webhook secret field)

It uses the new `.copy-value` component (D.9.1):

```html
<dl class="copy-value">
  <dt class="copy-value__label">Address for Zoom's Event Subscriptions</dt>
  <dd class="copy-value__value" translate="no">{{ webhook_address }}</dd>
  <dd class="copy-value__help">In the Zoom app, open Features, then Event Subscriptions, and paste this into Event notification endpoint URL. Tap or click it once to select it all.</dd>
</dl>
```

- The label is pinned (criterion 15). The help is *design copy*, and it follows the README's Marketplace path (Features → General Features → Event Subscriptions).
- It's plain text, not a link and not an input (criterion 15). One click or tap selects the whole address and nothing around it (`user-select: all`), which is the hard part of copying a long URL on a phone.
- **When the address isn't `https://`** (G4: `webhook_address_secure` is false), a `notice--warn` with `alert-triangle` follows the block. *Design copy*: title `Zoom can't use this address`, then `p`: `Zoom only sends changes to an address that starts with https://. Open this page through the site's public https:// address, or ask whoever looks after the server for it.` Otherwise, IT on an internal hostname would copy an address that Marketplace's Validate can never reach, and wouldn't know why.

**Change, desktop (1440), connection used by two accounts, everything saved:**

```
Change the Zoom connection zoom-02            Home › Zoom accounts › Zoom connections › zoom-02
┌──────────────────────────────────────────────────────────────────────────────┐
│ ┌──── .box__form, 640px ──────────────────────────┐                          │
│ │ The connection                                   │                          │
│ │ Connection name   zoom-02                        │  .facts                  │
│ │ Used by           Zoom 02   Zoom 05   (links)    │                          │
│ │ The name can't be changed, because it's part of  │  muted                   │
│ │ the address Zoom sends changes to.               │                          │
│ │ ──────────────────────────────────────────────── │                          │
│ │ App credentials                                  │                          │
│ │ ┌ ✓ Connection details saved on Mon 2 Nov 2026 ┐ │  notice--ok              │
│ │ │   by Nimal Perera.                           │ │                          │
│ │ └──────────────────────────────────────────────┘ │                          │
│ │ In Zoom's App Marketplace (marketplace.zoom.us), │                          │
│ │ open this subscription's Polymath TMD app, …     │                          │
│ │ Account ID                                       │                          │
│ │ [AbC1dEf2GhI3jKl4MnO5pQ                       ]  │  prefilled (D3)          │
│ │ Client ID                                        │                          │
│ │ [q1W2e3R4t5Y6u7I8o9P0                         ]  │  prefilled               │
│ │ New client secret                                │                          │
│ │ Leave it empty to keep the saved one. If the …   │                          │
│ │ [                                             ]  │  always empty            │
│ │ ──────────────────────────────────────────────── │                          │
│ │ Changes made in Zoom                             │                          │
│ │ ┌ ✓ Webhook secret saved on Mon 2 Nov 2026 by ─┐ │  notice--ok              │
│ │ │   Nimal Perera.                              │ │                          │
│ │ │   Last heard from Zoom on Mon 2 Nov 2026,    │ │                          │
│ │ │   10:42 am.                                  │ │                          │
│ │ └──────────────────────────────────────────────┘ │                          │
│ │ Zoom can tell this site when a class is changed  │                          │
│ │ or deleted directly in Zoom. That needs …        │                          │
│ │ ┌ Address for Zoom's Event Subscriptions ──────┐ │  .copy-value             │
│ │ │ https://tmd.polymath.edu.lk/zoom/webhooks/   │ │  mono, select-all        │
│ │ │ zoom-02/                                     │ │                          │
│ │ │ In the Zoom app, open Features, then Event … │ │                          │
│ │ └──────────────────────────────────────────────┘ │                          │
│ │ New webhook secret                               │                          │
│ │ Leave it empty to keep the saved one. If the …   │                          │
│ │ [                                             ]  │                          │
│ │ [ ] Remove the saved webhook secret              │                          │
│ │     Tick this if the saved secret is wrong and … │                          │
│ │                                                  │                          │
│ │ [ Save changes ]  Cancel                         │                          │
│ └──────────────────────────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**The other secret states, desktop (only the blocks that differ):**

```
Details unreadable, no webhook secret, not used by any account:
│ │ Used by           No account yet                 │
│ │ App credentials                                  │
│ │ ┌ ⬣ The client secret is saved, but it can't ──┐ │  notice--bad
│ │ │   be read with the server's current          │ │
│ │ │   encryption keys. Type it again.            │ │
│ │ └──────────────────────────────────────────────┘ │
│ │ New client secret                                │
│ │ Paste the Client Secret from App Credentials.    │
│ │ The saved one can't be used.                     │
│ │ Changes made in Zoom                             │
│ │ ┌ △ No webhook secret saved ───────────────────┐ │  notice--warn
│ │ │   Without it, changes made directly in Zoom  │ │
│ │ │   aren't seen here. …                        │ │
│ │ └──────────────────────────────────────────────┘ │
│ │ (intro) (address block)                          │
│ │ New webhook secret                               │
│ │ Paste the Secret Token from the Event …          │  no Remove checkbox
Webhook secret unreadable:
│ │ ┌ ⬣ A webhook secret is saved, but it can't be ┐ │  notice--bad
│ │ │   read with the server's current encryption  │ │
│ │ │   keys. Type it again.                       │ │
│ │ └──────────────────────────────────────────────┘ │
│ │ … New webhook secret … [ ] Remove the saved webhook secret (G3)
```

**Change, phone (400):** this is one column. `.facts` stacks each label above its value (the existing rule below 600px). The `Used by` links wrap as 44px tap targets. The address wraps anywhere inside its box. The buttons are full width.

### D.5 The secret inputs: `zoom/partials/secret_field.html` (new partial, not a new component)

**Do they follow `docs/design/password-field.md`? No.** That spec is **superseded** (2026-09-24, owner: "Match the concept exactly"). Using its Show/Hide button would mean reopening it with the owner first. The secrets follow the **host key's** write-only pattern instead (008 D.2/D.3, 011):

- **A plain `type="text"` input, not `type="password"`.**
  - IT pastes a 22- to 32-character value copied from Marketplace. Seeing it is the only way to spot a wrong paste, such as the Client ID pasted into the secret box (R8).
  - `type="password"` would bring in the browser's password manager. It would offer to "save the password" for this site, and could later fill the site's own sign-in password into these boxes, or Client values into the sign-in form. For non-technical staff that's both confusing and unsafe.
  - The owner may prefer dots (O1).
- **Never a value.** The partial has no `value` attribute at all. It doesn't depend on `field.html`'s password rule, because this isn't a password widget.
- **Widget attributes** come from the form (G2): `autocomplete="off"` (no form history holding a secret), `autocapitalize="none"`, `autocorrect="off"`, `spellcheck="false"` (browser spell-check services must never receive the value) and **no `maxlength`**.

**Why a partial.** Three inputs now share this exact markup: `host_key`, `client_secret` and `webhook_secret`. Today the host key is written out by hand in `account_form.html` (008 D.3.2), and copying it twice more would put one rule in three places. `account_form.html`'s host key moves to this partial too. Its output must stay the same: the same ids, the same `aria-describedby` tokens and the same notice. Its existing tests are the check.

```
{# with: field (BoundField), was_typed (bool), note (str, the pinned "wasn't kept" sentence), narrow (bool, optional) #}
[when was_typed]
<div class="notice notice--warn" id="{name}-note">
  <svg class="icon icon--xl" aria-hidden="true" focusable="false"><use href="#i-alert-triangle"></use></svg>
  <p>{note}</p>
</div>
[end]
<div class="field">
  <label class="field__label" for="{id}">{label}</label>
  [help] <p class="field__help" id="{name}-help">{help}</p>
  <input class="input[ input--narrow]" type="text" id="{id}" name="{name}"
         {widget attrs except type and value} [required when field.field.required]
         [aria-invalid="true" when errors]
         aria-describedby="[{name}-error ][{name}-note ][{name}-help]">   ← only the ids that exist, in this order
  {% include "partials/field_error.html" with field=field only %}
</div>
```

| Use | `was_typed` | `note` (pinned, criterion 14 / 008) | `narrow` |
|---|---|---|---|
| `client_secret` | `form.client_secret_was_typed` | `For your safety, the client secret you typed wasn't kept. Type it again.` | no (full width; 32 characters) |
| `webhook_secret` | `form.webhook_secret_was_typed` | `For your safety, the webhook secret you typed wasn't kept. Type it again.` | no |
| `host_key` | `form.key_was_typed` | `For your safety, the host key you typed wasn't kept. Type it again.` | yes |

- The note sits **above** its field, outside `.field`, as the host key's does. It isn't in the error summary, because it isn't an error. The summary still lists any real error, and the note is the first thing above the box the person must fill again.
- **Width.** IDs and secrets are full width (`.box__form`, 640px). At 16rem a 32-character secret would scroll inside the box, and the person couldn't check the end of what they pasted. Only `slug` is narrow.

### D.6 Tags: `zoom/partials/connection_tag.html` (new) and `account_tag.html` (changed)

Both columns on the list use the same three states, so one partial with one parameter covers both. The tone, icon and word for each state are chosen **here and nowhere else**.

| `state` | Class | Icon | Word |
|---|---|---|---|
| `"saved"` | `tag tag--plain` | `lock` | `Saved` |
| `"none"` | `tag tag--warn` | `alert-triangle` | `Not saved` |
| `"unreadable"` | `tag tag--bad` (new, D.9.2) | `alert-octagon` | `Can't be read` |

- `Saved` is plain, like the host key's `Saved`: the normal state shouldn't draw the eye. The `lock` icon says it's kept locked away.

**`zoom/partials/account_tag.html`, `kind="zoom"`** (criterion 21; `missing` is removed):

| `state` | `needs_zoom_connection` | Output |
|---|---|---|
| `"ready"` | any | unchanged: `tag--plain`, `link`, `Set up` |
| `"unreadable"` | any | `{% include "zoom/partials/connection_tag.html" with state="unreadable" only %}`, so `Can't be read` has one definition across both pages |
| `"none"` | true | unchanged: `tag--warn`, `alert-triangle`, `Not set up` |
| `"none"` | false | unchanged: `tag--plain`, `slash`, `Not set up` |

- **006's styling rule is kept** for the one state it was written for: whether `Not set up` matters depends on whether the account is bookable.
- `Can't be read` is **always** `bad`, whatever the account. It isn't a choice someone made, the way "no connection on a free account" is. It's a server fault that affects every account on that connection, and it's fixed in one place.
- Update the partial's header comment: the states, the include, and that `connection_tag.html` is now one of its partials.

### D.7 The account form's **Zoom connection** section (criteria 18–20)

DOM order inside the `fieldset.formsection` with the `Zoom connection` legend:

1. **Change only:** the state notice from the **stored** link (criterion 19), then 013's `False` notice when `webhook_secret_set is False`.
2. `{% include "partials/select_field.html" with field=form.zoom_connection narrow=True only %}` (D.7.1). This replaces the `credential_set` text input.
3. When `can_manage_connections`: `div.field` > `a.tap-link` → `zoom:connections`, reading `Zoom connections` (criterion 9). It's a text link, not a button: `Check connection` is the section's one button.
4. `Check connection` (unchanged).

**The `{name}` element**, used in every notice below: when `zoom_connection_url` isn't empty, `<a class="break-anywhere" href="{{ zoom_connection_url }}" translate="no">{{ zoom_connection_name }}</a>`; otherwise `<span class="break-anywhere" translate="no">…</span>`. `.notice a` already inherits the notice's colour and keeps its underline.

| `zoom_connection_state` | Notice | Icon | Title | Body (pinned) |
|---|---|---|---|---|
| `"ready"` | `notice--ok` | `check-circle` | `Set up` | `This account uses the Zoom connection {name}. Press Check connection to make sure Zoom accepts it.` Then, unchanged from 013, when `webhook_secret_set`: `Changes made directly in Zoom are copied here.` followed by `Last heard from Zoom on {when}.` or `Nothing heard from Zoom yet.` |
| `"unreadable"` | `notice--bad` | `alert-octagon` | `Can't be read` | `The details of the Zoom connection {name} can't be read with the server's current encryption keys. Type its client secret again on the Zoom connection's page.` |
| `"none"` | `notice--note` | `info` | `Not set up` | unchanged (006): `Paid accounts in use need a Zoom connection before classes can be booked on them.` |

- **013's `False` notice** (`notice--warn`, `alert-triangle`): its title stays `Changes made in Zoom aren't seen here`. Its body becomes criterion 20's pinned text, with `{name}` as above: `The Zoom connection {name} has no webhook secret. Until it has one, a class changed or deleted directly in Zoom stays as it was here until its booking is checked against Zoom. Add it on the Zoom connection's page.`
- On **add**, no notice shows (nothing is stored), but the select and the link do.
- **Select help** (pinned, criterion 18): `The Zoom app this account books through. If it isn't in the list, add it on the Zoom connections page first.`
- **Select error:** `Choose a Zoom connection from the list.`
- **Following the link loses unsaved changes**, as following any link does. The help's word "first" and `Check connection`'s existing "Save your changes first" set that expectation. No JS guard is added.

**Account change, desktop (1440), the section in its three states:**

```
│ Zoom connection                                    │
│ ┌ ✓ Set up ────────────────────────────────────┐   │  ready
│ │   This account uses the Zoom connection       │   │
│ │   zoom-02 (link). Press Check connection to … │   │
│ │   Changes made directly in Zoom are copied    │   │
│ │   here. Last heard from Zoom on …             │   │
│ └───────────────────────────────────────────────┘   │
│ Zoom connection                                    │  (field label)
│ The Zoom app this account books through. If it …  │
│ [ zoom-02            ▾]                            │  select, 16rem
│ Zoom connections (link)                            │
│ [ Check connection ]                               │
│ Asks Zoom whether this account's saved connection …│

│ ┌ ⬣ Can't be read ─────────────────────────────┐   │  unreadable
│ │   The details of the Zoom connection zoom-09  │   │
│ │   (link) can't be read with the server's …    │   │
│ └───────────────────────────────────────────────┘   │

│ ┌ i Not set up ────────────────────────────────┐   │  none
│ │   Paid accounts in use need a Zoom connection │   │
│ │   before classes can be booked on them.       │   │
│ └───────────────────────────────────────────────┘   │
│ [ No Zoom connection yet ▾]                        │
```

#### D.7.1 `partials/select_field.html` (new shared partial)

CLAUDE.md forbids passing a choice widget to `field.html`. No shared partial renders a `<select>` today: the timetable filter writes its own GET-only one. So a select inside a form gets its own small partial, beside `field.html`, in the same f-desk field pattern. It's a partial, not a component: it uses only `.field`, `.field__label`, `.field__help`, `.input` (already used on a `<select>` by the timetable filter) and `field_error.html`.

```
{# with: field (BoundField of a Select / ModelChoiceField), narrow (bool, optional) #}
<div class="field">
  <label class="field__label" for="{id}">{label}</label>
  [help] <div class="field__help" id="{name}-help">{help}</div>
  <select class="input[ input--narrow]" id="{id}" name="{name}"
          [required when field.field.required] [aria-invalid="true" when errors]
          aria-describedby="[{name}-error ][{name}-help]">
    {% for option in field %}<option value="{{ option.data.value }}"{% if option.data.selected %} selected{% endif %}>{{ option.choice_label }}</option>{% endfor %}
  </select>
  {% include "partials/field_error.html" with field=field only %}
</div>
```

- The options come from iterating the bound field, so the empty label (`No Zoom connection yet`), the order and the selected option all come from the form. After an invalid POST, the person's choice stays selected.
- It's labelled with a real `<label for>`, and its help and error are wired the same way as `field.html`'s. There's no `aria-label` and no placeholder option text standing in for the label.
- `tmd-docs-writer` adds it to CLAUDE.md's list of shared form partials (step 6).

### D.8 The accounts list (criteria 9 and 21)

- **The link.** The box head's right side becomes `div.form-actions` (the existing flex-wrap group with a 12px gap). It holds, in this order:
  - when `can_manage_connections`: `a.button.button--secondary` → `zoom:connections`, with the `link` icon (`aria-hidden`) and `Zoom connections`;
  - when `can_add`: the existing `+ Add a Zoom account` primary button.

  Render the group only when at least one of them shows. The key-less viewer sees neither.
- **Layout.** At 1440 and 1024 both buttons sit at the right of `Accounts ({n})`. Below 600px the group wraps under the title, and each button is full width (the existing `.form-actions .button` rule).
- **Empty state.** The head is still rendered, so the link shows when there are no accounts yet. That's the natural moment to set up connections.
- **The column.** It's unchanged apart from the tag (D.6). The header comment's `zoom_connection_state` values become `"ready"`, `"unreadable"` and `"none"`, and it adds `can_manage_connections`.

```
│ Accounts (5)                    [ ⛓ Zoom connections ] [ + Add a Zoom account ] │   1440
│ Accounts (5)                     │   400
│ [      ⛓ Zoom connections      ] │
│ [     + Add a Zoom account     ] │
```

### D.9 New components

#### D.9.1 `.copy-value`: a value to copy exactly into another system

- **Why it's new.** `.facts dd` is body-size proportional text, and on a phone a long-press selects a URL one word at a time. `.secret` is the nearest thing in the kit, but it's built for something else: it's 28px with wide letter-spacing, so a host key can be read aloud; it's hidden when printed; and its name says "secret". A 50-character URL at that size wraps into four or more lines at 400px, and it isn't a secret.
- **Anatomy.** `dl.copy-value` > `dt.copy-value__label` + `dd.copy-value__value[translate="no"]` + an optional `dd.copy-value__help`.

| Part | Spec (existing tokens only) |
|---|---|
| `.copy-value` | `margin: 0 0 var(--space-5); padding: var(--space-4); border: var(--rule) solid var(--c-border); border-radius: var(--radius); background: var(--c-surface-2);` |
| `.copy-value__label` | `margin: 0 0 var(--space-2); color: var(--c-heading); font-weight: var(--fw-medium);` (it reads like a field label) |
| `.copy-value__value` | `margin: 0; color: var(--c-heading); font-family: var(--font-mono); font-size: var(--fs-body); line-height: var(--lh-body); overflow-wrap: anywhere; -webkit-user-select: all; user-select: all; cursor: text;` |
| `.copy-value__help` | `margin: var(--space-2) 0 0; color: var(--c-muted); font-size: var(--fs-help); line-height: var(--lh-body);` |

- **Contrast.** These are the same pairs `secret-value.md` measured: `--c-heading` on `--c-surface-2` is about 12:1 (light) and 8.5:1 (dark), and `--c-muted` on `--c-surface-2` is about 5.3:1 and 4.9:1. The verifier confirms them.
- **States.** Shown only. There's no hover, focus or copied state, and no JS.
- **Print.** It prints, unlike `.secret`, because it isn't a secret.
- **Reflow.** It wraps anywhere, so there's no sideways scroll at 320px or at 400% zoom.
- **Where it goes.** CSS section 5n, beside `.secret`.
- **Used by:** `zoom/connection_form.html` (the webhook address).

#### D.9.2 `.tag--bad`: the danger tone for a tag

- **Why it's new.** The ported tags have `ok`, `warn`, `note`, `plain` and `brand`, but no danger tone. `Can't be read` is the one tag state where something is broken and booking stops. The change pages show the same state as `notice--bad` (pinned, criteria 15 and 19), and the list must not look calmer than the page it links to.
- **Spec.** `.tag--bad { background: var(--c-bad-soft); color: var(--c-bad-text); }`, on the line after `.tag--brand` in section 5g. It always carries the `alert-octagon` icon and a word.
- **Contrast at the 10.5px semibold tag size** (AA needs 4.5:1):
  - light: `--red-700` `#B42318` on `--red-50` `#FFE3E2` is about **5.4:1**;
  - dark: `--red-300` `#F59A94` on `--red-900` `#432A2A` is about **6.2:1**.

  The verifier confirms them.
- **Used by:** `zoom/partials/connection_tag.html`, and through it, `account_tag.html`.

**Component notes.** The main session limited this step to the brief, so `docs/design/copy-value.md` and `docs/design/tag-bad.md` aren't written yet. Once the main session accepts D.9, the designer writes them from D.9.1 and D.9.2 word for word, so each component is defined in one place before the frontend builds it (G6).

### D.10 States, all pages

| State | List | Add | Change | Account add / change |
|---|---|---|---|---|
| Default | D.2 | D.3 | D.3, D.4 | D.7 |
| Empty | No connections (D.2) | n/a | `Used by`: `No account yet` | The select holds only `No Zoom connection yet`. The help points to the Zoom connections page, and the link is right below it |
| Loading | none (full page loads) | none | none | `Check connection` keeps its busy state (unchanged) |
| Validation errors | n/a | the summary (pinned lead) plus a pinned error under each field. Typed values are kept, except secrets | the same, plus `Type a new webhook secret or tick Remove, not both.` | `Choose a Zoom connection from the list.` |
| Secret typed, then an invalid POST | n/a | the "wasn't kept" note above each typed secret's field (D.5) | the same | the host key's note (unchanged, now through the partial) |
| Unreadable | `Can't be read` tags | n/a | the `notice--bad` notices (D.4) | `Can't be read` notice (D.7); `Can't be read` tag on the list |
| Success | the flash after the redirect (criteria 11–12) | redirects to the list | redirects to the list | unchanged |
| Server error / CSRF | Django's 500, or `403.html` | the same | the same | the same |
| No permission | anonymous: sign in; plain user and key-less viewer: `403.html` (criterion 8) | the same | the same | the key-less viewer sees no link and no tag change beyond the words |

### D.11 Accessibility

- **Headings and landmarks.**
  - The list: h1 (the page), then h2 `Connections ({n})`, then h3 for the empty state.
  - The form pages have only the h1. The sections are `<fieldset>`/`<legend>`, as on every form in the app (`form-section.md`), so the outline stays h1 → content.
  - The change page's `The connection` fieldset holds no control, only a `dl`. That's valid, and it keeps the same three sections on add and change.
  - The landmarks are `base.html`'s: the `Main` navigation and `<main>`.
- **Labels, help and errors.**
  - Every input and the select has a `<label for>`.
  - `aria-describedby` lists, in order: `<name>-error` (when there's an error), `<name>-note` (for a secret typed before an invalid POST, criterion 14), then `<name>-help`.
  - `aria-invalid="true"` is set only when there's an error.
  - The error summary has `role="alert"` and `tabindex="-1"`. `app.js` focuses it on load, and each item links to the field's `id`.
  - The checkbox uses `check_field.html`'s wiring.
- **The note is announced with its field.** When focus reaches `New client secret`, a screen reader reads the label, then the error (if any), then "For your safety, the client secret you typed wasn't kept. Type it again.", then the help.
- **Select labelling.** It has a visible label and help, and the native `<select>` with no custom widget, so every platform's own picker works. The empty option's words (`No Zoom connection yet`) are real text, not a stand-in for the label.
- **The webhook address.**
  - It's a `dt`/`dd` pair, so a screen reader reads "Address for Zoom's Event Subscriptions" with the value. `translate="no"` stops browser translation from mangling it.
  - One tap or click selects it all.
  - Keyboard-only users can copy it with caret browsing (F7), or read and type it. A Copy button is F1.
- **Links.** Link names stay unique in a links list: the hidden `Change ` prefix gives "Change zoom-01" and "Change Zoom 01", and the visible text sits inside the accessible name (WCAG 2.5.3). The `{name}` links inside notices are inline in a sentence, which WCAG 2.5.8 exempts. Every link that stands alone is a `.tap-link`, at 44px on phones.
- **Keyboard and focus order.**
  - **List:** sidebar, then the Add button, then each row's name link, then its `Used by` links.
  - **Add / change:** the error summary (focused) and its links, then `Used by` links (change), then Account ID, Client ID, the client secret, the webhook secret, Remove, `Save changes` / `Add the connection`, and `Cancel`.
  - **Account section:** the `{name}` link, then the select, then the `Zoom connections` link, then `Check connection`.
  - **After a redirect** (a successful save), focus starts at the top of the new page, and the flash is the first content after the h1.
- **Touch targets.** Inputs, the select, buttons and checkbox rows are 44px (`--target`). Tap links are 44px below 768px. Nothing is under 44px.
- **Status is never colour alone.** Every tag is an icon plus a word. Every notice is an icon plus words, and has a title where the state has a name. The error border is backed by the `alert-circle` error line.
- **Contrast.** Only existing pairs are used, plus D.9's two new ones, measured above. Light and dark both hold AA.

### D.12 Progressive enhancement and responsive checks

- **No JS.** Every page is a plain GET or a POST with a full page load.
  - The error summary isn't focused, but it's the first thing after the title.
  - Flashes have no Close button (it's `hidden` until `app.js` shows it).
  - `Check connection` submits without its busy text.
  - The address is selected with a normal drag or long-press. `user-select: all` is CSS, not JS.
  - Nothing on these pages needs JS.
- **With `app.js`.** The existing hooks run: `data-error-summary`, `data-flash` / `data-flash-close`, and `data-busy-form` on `#zoom-check`. **No new hook.**

| Width | List | Add / change | Account section |
|---|---|---|---|
| 1440 | the table, four columns | 640px form column | 640px |
| 1024 | the sidebar plus the table. Four columns fit with no sideways scroll | the same | the same |
| 400 | one card per row. The labels sit at `--row-label-w`. The Add button wraps under the title | one column, inputs full width, `.facts` stacked, buttons full width | the select full width, the head buttons stacked |
| 320 | the same, with tags wrapping (`--wrap-tags`). Long names wrap with `.break-anywhere` | the address wraps anywhere, with no sideways scroll | the same |
| Dark | tokens only. `tag--bad` and `.copy-value` have measured dark pairs (D.9) | the same | the same |

### D.13 Proposals, gaps, questions and follow-ups

**Proposals to pinned copy or criteria (P), for the main session:**

- **P1 (criterion 15, the webhook `none` notice).**
  - **Change:** replace the body's last sentence, `Add it once the Zoom app's Event Subscription is set up.`, with `Add it when you set up the Zoom app's Event Subscription, using the address below.`
  - **Why:** Marketplace's **Validate** passes only after this site has the secret (README, "Setting up the webhook", step 5). So "once it is set up" sends IT round in a circle. The address they need is on this page, right under the notice.
  - The full body becomes: `Without it, changes made directly in Zoom aren't seen here. Add it when you set up the Zoom app's Event Subscription, using the address below.`
- **P2 (criterion 10, "with the add button").** Read this as the box head's `Add a Zoom connection` button, which is the page's only Add action and shows in the empty state too (008 D.1's precedent). Any test should look for the button in the head, not inside `.empty`. No copy changes.
- **P3 (criteria 12–13, recommended).**
  - **Change:** when `credentials_state == "unreadable"`, an empty `New client secret` is refused with criterion 13's existing `client_secret` text.
  - **Why:** otherwise someone who only corrects the Account ID gets `Saved the Zoom connection …`, while the connection still can't be used.
  - No new copy is needed. If it isn't accepted, the design stands as written: the `notice--bad` and the help (`The saved one can't be used.`) still say what to do.

**Gaps in the context contract (G), for the backend:**

- **G1: Help text by page and state.** `ZoomConnectionForm` sets each label and help in D.3's table, in `__init__`. The choice depends on whether it's add or change and on `credentials_state` / `webhook_secret_state`, the same way `HostAccountForm` switches its host-key help.
- **G2: Widget attributes.**
  - `account_id`, `client_id`, `client_secret` and `webhook_secret` are `forms.TextInput` (not `PasswordInput`), with `autocomplete="off"`, `autocapitalize="none"`, `autocorrect="off"` and `spellcheck="false"`.
  - They have **no `maxlength` attribute.** Django's `CharField(max_length=…)` adds one automatically, so check the 100- and 200-character limits in `clean_*` instead. A too-long paste must reach criterion 13's error. It must never be cut short silently in the browser, saved, and then fail at Zoom.
  - `slug` keeps `maxlength="40"`. It's typed by hand, so a cut there is visible as you type.
- **G3: Remove for an unreadable secret.** Criterion 12's "present only when a webhook secret is saved" means a secret is **stored**, so `webhook_secret_state` is `"saved"` **or** `"unreadable"` (`webhook_secret_encrypted != ""`), as `remove_host_key` does for an unreadable host key (008 D.3.4). Removing it is the way out when the Token isn't to hand.
- **G4: `webhook_address_secure`** (bool, change only; `False` on add): `webhook_address.startswith("https://")`, worked out in the view. It drives D.4.3's `Zoom can't use this address` notice, so the template makes no URL decision.
- **G5: The `zoom/partials/account_tag.html` contract** gains `"unreadable"` and drops `"missing"`. It's already listed. G5 only records that the partial now includes `connection_tag.html`.
- **G6: Component notes.** On acceptance, the designer writes `docs/design/copy-value.md` and `docs/design/tag-bad.md` from D.9 (this step was limited to the brief).

**Open question for the owner (O), not blocking:**

- **O1: Should the secret boxes show what's typed, or dots?**
  - **The design:** a plain text box, like the host key (D.5). IT can then see a wrong paste, and the browser's password manager stays out of it.
  - **The alternative:** dots (`type="password"`). It hides the value from someone looking over IT's shoulder, but browsers will offer to save it as this site's password, and may fill the sign-in password into it.
  - Either way the value is never sent back or shown after saving.
  - **Recommendation:** plain text. The build goes ahead with text unless the owner says otherwise.

**Follow-ups (F), not in this brief:**

- **F1: A `Copy address` button** beside the webhook address. It would be an `app.js` enhancement on a `data-copy` hook, hidden without JS, announcing "Copied" through a `role="status"` line. It helps keyboard-only users most. Note that `navigator.clipboard` needs a secure context (`https://`).

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops (agent plan step 3, 2026-11-02)

**Files changed**

- **`config/settings/base.py`** (criterion 36):
  - The whole "Zoom connection" block is removed: `ZoomCredentials`, the two `*_PARTS` tuples, `zoom_credential_env_prefix`, `read_zoom_credentials`, the credential-set list and the secrets/missing settings. The now-unused `from dataclasses import dataclass, field` is removed too.
  - The `HOST_KEY_ENCRYPTION_KEYS` comment now says it encrypts host keys **and** each Zoom connection's Client Secret and webhook Secret Token, that `rotate_encryption_keys` re-encrypts them, and that the keys must be backed up apart from the database, because a backup plus the keys gives Zoom access (D16, R1).
  - The `ZOOM_PROVIDER` comment's "needs the credential sets below" now says each account needs a connection saved on the Zoom connections page, with no Zoom credential variables.
  - `LOGGING` pins `"django.db.backends": {"level": "INFO"}`, with a comment saying SQL parameters now carry connection values (D15, criterion 39).
- **`zoom-credentials.env.example`:** deleted (`git rm`, so the deletion is staged) (criterion 37).
- **`compose.yaml`** (criteria 37–38):
  - `web` has no `env_file` key and no mention of `zoom-credentials`. In its place is a two-line comment inside `web.environment`: no Zoom credential variables, because the details are typed in the app (brief 015).
  - The one-line comment on `HOST_KEY_ENCRYPTION_KEYS`: `Required: encrypts host keys and Zoom connection secrets. Back it up apart from the DB: both together give Zoom access.`
- **`.env.example`** (criterion 38):
  - The `ZOOM_PROVIDER` `zoom` line says each Zoom app's details are typed on the app's Zoom connections page, not in any env file. The two lines pointing at `zoom-credentials.env` are removed.
  - The `HOST_KEY_ENCRYPTION_KEYS` comment covers host keys **and** Zoom connection secrets. It says to back up the keys and store them apart from database backups, what losing them means (retyping every secret), and that a backup holding both gives Zoom access.
  - Its rotation line now names `rotate_encryption_keys` (it said `rotate_host_keys`, which the backend removed), and says the command must end without an error before the old key is removed (D4).
- **`.gitignore`, `.dockerignore`:** the `zoom-credentials.env` line is **kept**. Its comment is now exactly criterion 37's `# Retired by brief 015 (Zoom credentials are typed in the app). Kept so a stray copy is never committed or copied into the image.` (D12).
- **`apps/core/test_zoom_settings.py`, rewritten** (criterion 39):
  - **Removed:** env-credential reading and naming, the webhook-secret env tests, the `ZoomCredentials` repr test, masking the old secrets setting in error reports and the debug page, the compose `env_file` test and the example-file test.
  - **Kept:** the `urllib3` logging pin, the three network-block tests (006 criterion 45), the prod fake-provider refusal, and the `.env.example` provider line (extended).
  - **Added:**
    - `base.py` holds none of criterion 36's names, nor `dataclass`;
    - no `settings` attribute is named after the old variables;
    - criterion 36's source scan of `apps/`, `config/`, `docker/`, both compose files, `Dockerfile` and `.env.example` (`__pycache__` skipped; the needles are built from parts, so the file doesn't match itself);
    - the example file is gone, compose has no `env_file` and no `zoom-credentials`, and both ignore files keep the line under the exact retired comment (criterion 37);
    - the `ZOOM_PROVIDER` and `HOST_KEY_ENCRYPTION_KEYS` comments in `.env.example`, `base.py` and `compose.yaml` say what criterion 38 asks (the compose one is checked to be one line);
    - the `django.db.backends` pin, checked both in `LOGGING` and as the logger's effective level, which must be at least `INFO`.
  - `apps/core/tests.py::test_dockerignore_keeps_private_data_out_of_the_image` is unchanged and passes.

**New env vars:** none. **Removed env vars:** the Zoom credential list and the per-connection credential variables (they were only ever read from the git-ignored file, which was never created; D11).

**Dependency changes:** none.

**Operational steps for the user**

- **Recreate `web` once** on whichever stack is used, so the container drops compose's old `env_file` entry: `docker compose up -d --build` (prod) or the dev overlay equivalent. The dev stack has already been rebuilt and recreated (below).
- **Nothing to migrate in config:** the file was never created. A stray `zoom-credentials.env` would be ignored by the app and kept out of git and the image.

**Not mine; for `tmd-docs-writer`:** `README.md`, `CLAUDE.md` and `docs/CHANGELOG.md` still mention `zoom-credentials.env`, the old variables and/or `rotate_host_keys` (criterion 49's list covers them). README facts that changed: there's no credentials file to copy, compose has no `env_file`, the rotation command is `rotate_encryption_keys`, and the encryption keys now protect connection secrets too (backup advice, D16).

**Self-check output** (2026-11-02)

- **Stacks:** the dev stack was running (on 8011) before and after. It was rebuilt and recreated with `WEB_PORT=8011 docker compose -f compose.yaml -f compose.dev.yaml up -d --build`: `db` kept running, `web` was recreated, and `GET http://127.0.0.1:8011/healthz/` returned 200. The dev overlay has no Docker healthcheck. Inside it, `env` shows **0** credential variables, and `ls /app` shows no `zoom-credentials*` file. `.env` was not touched.
- `docker compose config --quiet`: `prod config OK`. `docker compose -f compose.yaml -f compose.dev.yaml config --quiet`: `dev config OK`. The rendered prod config has no `env_file` and no `zoom-credentials`.
- `pytest apps/core` (dev container, **no `--create-db`**): **`149 passed in 18.20s`**. `apps/core/test_zoom_settings.py` alone: **17 passed**.
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `128 files already formatted`.
- `python manage.py check`: `System check identified no issues (0 silenced).` `check --database default` (dev `.env`, `fake`): the same.
- `makemigrations --check --dry-run`: `No changes detected`.
- `check --deploy` under prod settings, run in the dev container with `-e DJANGO_SETTINGS_MODULE=config.settings.prod -e USE_HTTPS=True -e DEBUG=False` and **no credential variable at all**:
  - `ZOOM_PROVIDER=zoom`: only `security.W021` (1 issue);
  - `ZOOM_PROVIDER=manual`: only `security.W021` and `zoom.W001` (2 issues).

  This is a pre-check only. Criterion 46's runs on the real prod stack remain the verifier's.

**Fix cycle 1** (agent plan step 5b, review round 1 N5, amended criterion 36, D21; 2026-11-02): `config/settings/base.py`'s `mail_admins` comment ("Don't set ADMINS without first revisiting …") now also names Zoom connection values: a database error's frame locals can hold an Account ID, a Client ID or a stored secret's ciphertext. Comment only; no setting, env var, dependency or compose change. `apps/core/test_zoom_settings.py` doesn't check that comment (criterion 36 leaves it to the reviewer), so no test changed. Self-check in the dev container, no `--create-db`: `pytest apps/core/test_zoom_settings.py` **17 passed in 4.65s**; `ruff check .` `All checks passed!`; `ruff format --check .` `129 files already formatted`; `python manage.py check` `System check identified no issues (0 silenced).` No rebuild needed (the dev stack bind-mounts the source; the prod image picks it up on its next build).

### tmd-frontend (agent plan step 2b, 2026-11-02)

**Files changed**

- **New templates:**
  - `templates/zoom/connections.html` (D.2, criterion 10). The box head's `+ Add a Zoom connection` is the page's only link to `zoom:connection_add` (P2). The table has the four columns, with both state columns through `connection_tag.html`. The empty state is `No Zoom connections yet.` (h3) plus `Add one for each paid Zoom subscription.`, split as on the accounts list, with no second button. It reads only `pk`, `slug`, `accounts_in_use`, `credentials_state` and `webhook_secret_state`.
  - `templates/zoom/connection_form.html` (D.3, D.4, criteria 11–15). One template for add and change, in three `fieldset.formsection`s. The change page shows the name and `Used by` as a `.facts` list. It has the credentials and webhook state notices, the `.copy-value` address, and the `Zoom can't use this address` warning when `webhook_address_secure` is false. Both secrets render through `secret_field.html`, and `remove_webhook_secret` through `check_field.html` when the form has it.
- **New partials:**
  - `templates/zoom/partials/connection_tag.html`: `saved` (plain, `lock`), `none` (warn, `alert-triangle`) and `unreadable` (bad, `alert-octagon`).
  - `templates/zoom/partials/secret_field.html`: `field`, `was_typed`, `note` and `narrow`. It never writes a `value`. `aria-describedby` lists `-error`, `-note` and `-help`, only those that exist, in that order.
  - `templates/partials/select_field.html`: `field` and `narrow`. It has a `<label for>`, its help as `div#<name>-help`, `aria-describedby` with error then help, and `aria-invalid` only with errors. Its options come from iterating the bound field.
- **Changed templates:**
  - `templates/zoom/account_form.html`:
    - the Zoom connection section's three states from the stored link (`ready`, `unreadable`, `none`), with criterion 19's and 20's pinned text;
    - `{name}` as a link when `zoom_connection_url` isn't empty, otherwise a span, both `translate="no"`;
    - the select through `select_field.html`, then the `Zoom connections` `tap-link` for `can_manage_connections`;
    - the host key moved onto `secret_field.html`;
    - the header comment rewritten for the new context.
  - `templates/zoom/accounts.html`: the head's right side is a `.form-actions` group. It holds `Zoom connections` (secondary, `link` icon) for `can_manage_connections`, then the existing Add button, and is rendered only when one of them shows. The header comment now names `can_manage_connections` and the new states.
  - `templates/zoom/partials/account_tag.html`: `missing` is removed. `unreadable` includes `connection_tag.html` with `state="unreadable" only`. The header comment is updated.
  - `templates/partials/sidebar.html`: `Zoom accounts` is `aria-current="page"` on `zoom:connections`, `zoom:connection_add` and `zoom:connection_edit` too. The header comment is updated.
- **CSS (`static/css/style.css`):**
  - 5g: `.tag--bad` on the line after `.tag--brand`.
  - 5j: the `datagrid--wrap-tags` comment is refreshed (comment only).
  - 5n: `.copy-value`, `__label`, `__value` and `__help`, after `.secret`, exactly as `docs/design/copy-value.md`.
  - 8 (Responsive, the card block): `.datagrid__ref.break-anywhere { white-space: normal; }`, so a long name wraps in a 320px card (see the self-check).
  - Existing tokens only: no new token and no colour literal.
- **JS:** none. No new hook.

**Spec deviations**

- **Undated "saved" lines (flagged for review).** When `credentials_changed_at` or `webhook_secret_changed_at` is empty, the change page says `Connection details saved.` or `Webhook secret saved.` instead of printing `class_date` of `None`. That can happen when a row is made outside the screens, for example by the verifier's shell clean-up. The dated, pinned sentences are used whenever a date exists. This mirrors the host key's `saved_legacy` line. If the main session prefers no fallback, it's a two-line removal.
- **The `{name}` markup is repeated three times** inside `account_form.html` (the ready notice, the `False` notice and the unreadable notice). It's on one page only, so it isn't a partial.
- **`secret_field.html` is written to the same rules as `field.html`.** A `True` widget attribute is written bare, a `False` one is dropped, and `required` is added when `field.field.required`. The host key has neither, so its output is unchanged (self-check below).

**Context contract gaps:** none. Every variable used is in the contract, under its exact name.

**Not mine; for the backend's test updates.** These existing strings are gone from the templates:

- `Missing on the server`;
- `The server has a Zoom connection called …`;
- `The server has no webhook secret for …`.

Any 006 or 013 template test asserting them needs the criterion 19–21 texts. `apps/zoom/services.py:205` still carries 006's `name not on the server` message, which criterion 22 retires.

**Self-check**

- **Host key output is unchanged.** A scratch script rendered the old inline host-key block and the new `secret_field.html` include for the same field, with whitespace between tags collapsed. It covered five cases (unbound; error plus typed; typed only; error without help; no help). Result: `ALL SAME`. Rendered: `…<input class="input input--narrow" type="text" id="id_host_key" name="host_key" autocomplete="off" inputmode="numeric" spellcheck="false" maxlength="10" aria-invalid="true" aria-describedby="host_key-error host_key-note host_key-help">…`
- **`select_field.html` rendered standalone.** The posted choice is `selected`. With an invalid choice it shows `aria-invalid="true" aria-describedby="zoom_connection-error zoom_connection-help"` and the error line.
- **The tags rendered standalone.** `connection_tag.html` gives all three tags. `account_tag.html` with `state="unreadable"` gives the `tag--bad` / `alert-octagon` / `Can't be read` tag.
- **Template tests needing no database.** In the dev container (no `--create-db`): `pytest apps/core/tests.py -k "include_ends or inline_style or hardcoded or icon_use or icons_partial or colour_literals or purpose_comment or static_reference or admin_or_reads or colliding_site or old_fonts or old_search"` gave **73 passed**. That covers header comments, `only` on every include, no inline style, no hard-coded paths, the sprite matching exactly the icons in use, colour literals only in 1a, and every `{% static %}` file existing.
- **Full `pytest` (after the backend's "pytest run finished" signal).** Run in the dev container with plain `pytest`, no `--create-db`: **`1610 passed in 103.95s`**, no failures.
- **HTTP render on the dev stack (port 8011, already published; `.env` not touched).**
  - **Setup:**
    - Temporary dev-database rows: connections `fe-check-01` (saved, no webhook secret, used by two accounts), `fe-check-02` (both saved), `fe-check-09` (both secrets replaced by an unreadable token through `QuerySet.update`) and a 40-character name.
    - Four `FE check …` accounts, free and not in use, so none is bookable.
    - A shell-made session for the dev superuser.
  - **Pages:** the list (empty and filled), the add page (clean, and after an invalid POST), the change page in its states, the account change page in its three states, the account add page and the accounts list.
  - **Coverage:** 320 and 1440 px, light and dark, Edge headless through Playwright. Every page returned **200**.
  - **Findings:**
    - Every state shows its pinned text, icon and tone.
    - `Zoom accounts` is current in the sidebar on the connection pages.
    - The `Zoom can't use this address` warning shows over plain http.
    - The add page after an invalid POST:
      - neither typed secret is in the HTML;
      - the Account ID is kept;
      - both "wasn't kept" notes show;
      - `#id_client_secret` has no `value` and `aria-describedby="client_secret-note client_secret-help"`;
      - the error summary takes focus.
    - The account IDs appear only on the connection change page, inside their inputs. No secret or `gAAAAA` text appears on the list, the accounts list, either account page or the change page.
  - **Clean-up:** the rows, the session and the scratch scripts were removed afterwards. The connection count is 0 again and no `FE check` account is left.
- **One fix from that run (mine, CSS only).** At 320px the accounts list scrolled sideways by 6px (`scrollWidth=326`). In the phone cards, a long name link such as `polymathlesson Paid` or `FE check unreadable` kept `.datagrid__ref`'s `white-space: nowrap`. A 40-character connection name had the same problem. This predates brief 015, but it would have hit the new list too. The fix is one rule in the Responsive section's card block: `.datagrid__ref.break-anywhere { white-space: normal; }`. Short references like `ZL-0001`, which have no `break-anywhere`, keep their no-wrap.
  - **After the fix:** every page is `scrollWidth=320` at 320, including the 40-character name on the list and on its change page.
  - The guard tests were re-run after it (`colour_literals`, `static_reference`, `purpose_comment`, `include_ends`): **65 passed**.
- **Screenshots:** `C:\Users\ASUS\AppData\Local\Temp\claude\d--My-work-PolymathTMD\c2317be1-7dfa-485a-8134-215a52759cb9\scratchpad\shots\` (`list-empty-*`, `list-*`, `add-*`, `add-errors-*`, `change-nowebhook-*`, `change-saved-*`, `change-unreadable-*`, `change-long-*`, `acct-ready-*`, `acct-unreadable-*`, `acct-none-*`, `acct-add-*`, `accounts-*`, each `-{light|dark}-{320|1440}.png`).
- **Note for the verifier, not a deviation.** On the dev stack, the ready account shows 013's `Changes made in Zoom aren't seen here` notice. That's because the `fake` provider reports `checks_zoom = True`, so `webhook_secret_set` is `False`, not `None`.

### tmd-django-backend (agent plan step 2a, 2026-11-02)

**Files changed**

- **`apps/zoom/models.py`:**
  - New `ZoomConnectionQuerySet` (`for_management()`, which prefetches `accounts_in_use` in `sort_order`, `label` order; `for_webhook(slug)`, the webhook's one lookup of four columns).
  - New `ZoomConnection` (criterion 1), with its three `CheckConstraint`s and `default_permissions = ()`. Its methods (criterion 2): `set_credentials`, `set_webhook_secret`, `remove_webhook_secret`, `get_client_secret`, `get_webhook_secret`, `credentials()`, the three state properties, `rotate_secrets()` and `client_id_taken_by()`.
  - `HostAccount.credential_set` is replaced by the `zoom_connection` FK (criterion 3). `zoom_connection_state` is now `none`/`unreadable`/`ready`, with one definition in the static method `HostAccount.connection_state(connection)`, which the change page uses for the stored link.
  - `HostAccountQuerySet`: `bookable()` and `for_management()` `select_related("zoom_connection")`; new `locked()` (`select_related("zoom_connection").select_for_update(of=("self",))`); `availability_for(lock=True)` uses `of=("self",)`.
  - `zoom_connection_state_for` and `webhook_secret_set_for` are removed. `_join_words` is renamed `join_words`, because `services` now uses it for the save message.
- **`apps/zoom/migrations/0010_zoom_connections.py`:** schema only (criterion 4, D11), with a docstring. See "Migrations".
- **`apps/zoom/crypto.py`:** `HostKeyUnreadable` is renamed `SecretUnreadable`, with no alias. The docstring now covers both kinds of secret and names `rotate_encryption_keys` (criterion 7).
- **`apps/zoom/zoom_api.py`:** `ZoomCredentials` moved here (`slug`, `version`, `account_id`, `client_id`, `client_secret`, everything but `slug` `repr=False`, no webhook secret). The token cache key is `(slug, version)`. `_forget_other_versions()` runs when a client is built, dropping that slug's other versions (criterion 24).
- **`apps/zoom/providers.py`:** `ZoomProvider._client` reads `host_account.zoom_connection.credentials()`. No connection, or an unreadable one, raises `ZoomNotConnected` (no HTTP).
- **`apps/zoom/services.py`:**
  - `_preview_key` keys on `zoom_connection_id` and `credentials_version` (criterion 25).
  - `check_connection` has criterion 22's three texts (`CHECK_NO_CONNECTION`, `CHECK_UNREADABLE`, the new `CHECK_AUTH_FAILED`); `CHECK_NOT_ON_SERVER` is removed.
  - `handle_event(connection, …)` takes `webhooks.verify`'s `VerifiedConnection` and matches on `host_account.zoom_connection_id` (criterion 28).
  - `reconcile()`'s first read is `select_related("host_account__zoom_connection")`, so asking Zoom costs no extra query.
  - Every locking read of an account in `approve()`, `cancel()`, both moves and `_reconcile_once` uses `HostAccount.objects.locked()` (D8).
  - New `connection_saved_message()` and the three flash texts (criteria 11–12). The plan placed them in `services`; the account flashes stay in `views`.
  - The move pre-check and the start-token read join `host_account__zoom_connection`.
- **`apps/zoom/webhooks.py`:** `verify()` makes one `for_webhook` query and returns a frozen `VerifiedConnection(pk, slug, account_id, webhook_secret)`, with the last two `repr=False`.
  - No row, or no secret: `UNKNOWN` (404, INFO).
  - An unreadable secret: the new `UNREADABLE_SECRET` (404), with one WARNING, `Zoom webhook call to {slug} refused: unreadable secret` (criterion 27, D9).
  - New signatures: `url_validation_reply(verified, event)` and `is_from_account(verified, event)`. The slug argument is gone; it's on `verified`.
- **`apps/zoom/checks.py`, `apps/zoom/apps.py`:** `check_credential_sets` (E005) and the `config.settings.base` import are removed, and E005 is unregistered. E004 and W002 read the database, one query each, with criterion 32's and 33's texts and hints (`WEBHOOK_SECRET_UNREADABLE`, `WEBHOOK_SECRET_HINT`).
- **`apps/zoom/validators.py`:** new `validate_zoom_value(value, *, max_length, message)` (trimmed, non-empty, printable ASCII with no whitespace, length limit). The connection-name comment no longer talks about env names.
- **`apps/zoom/forms.py`:**
  - `HostAccountForm.zoom_connection` is a `ModelChoiceField` over `ZoomConnection.objects.only("pk", "slug")`, with criterion 18's label, empty label, help (borrowed from the model field) and error.
  - New `ZoomConnectionForm` (criteria 11–14, D20 G1–G3, P3):
    - only `slug` is a model field, and only on add;
    - the IDs and secrets are form-only `TextInput`s with `PASTE_ATTRS` and no `maxlength`, and reach the row only through the model's methods in `save()`;
    - per-page and per-state labels and help are set in `__init__`;
    - `full_clean` drops both typed secrets after errors and sets `client_secret_was_typed` and `webhook_secret_was_typed`;
    - the `clean_*` methods enforce the 100 and 200 limits;
    - `clean_client_secret` refuses an empty value on add, or on change when the stored secret is unreadable (P3);
    - `clean()` refuses a new webhook secret together with Remove;
    - `@sensitive_variables` is on every method that holds a secret.
- **`apps/zoom/views.py`:**
  - New `ZoomConnectionListView`, `ZoomConnectionFormViewMixin`, `ZoomConnectionCreateView` and `ZoomConnectionUpdateView`. The add and change views are `never_cache` plus `sensitive_post_parameters("client_secret", "webhook_secret")`, and the list is `never_cache`. The change view's POST uses `select_for_update(of=("self",))`.
  - The account views supply the new contract variables. The change view captures the stored connection in `get_object()` and locks with `of=("self",)`.
  - The check view reads with `select_related("zoom_connection")`.
  - The webhook view passes `VerifiedConnection` through.
  - The cancel and sync views join `host_account__zoom_connection`.
- **`apps/zoom/urls.py`:** `connections/`, `connections/add/` and `connections/<int:pk>/edit/` (`zoom:connections`, `connection_add`, `connection_edit`). There's no reveal route.
- **`apps/zoom/management/commands/rotate_encryption_keys.py`:** new (criterion 34). **`rotate_host_keys.py` is removed** (`git rm`, so the deletion is staged).
- **`apps/zoom/management/commands/sync_zoom_bookings.py`:** joins `host_account__zoom_connection`, so `is_connected` costs no query per booking.
- **Tests:**
  - `zoommock.py`: the brief's test values. New helpers: `connection()`, `connect(*accounts, slug=…, webhook_secret=…)` (no `settings` argument), `credentials(version=…)`, `basic_auth()`, `add_token(secret=…)` (a Basic-auth header matcher, criterion 44), `foreign_token()` and `make_unreadable()` (via `override_settings` with a second fake key, so no test imports `cryptography` for it).
  - `synckit.py`: `connect()` makes rows, and brings an existing row to the given webhook secret. New `verified()`.
  - `conftest.py`: stubs for the two new templates.
  - `test_race.py`'s `committed` fixture deletes the race tests' now-unused connections.
  - New `test_connections.py` (criteria 1–3, 5–8, 10–17, 23–29, 33, 34, 40–43).
  - `test_zoom_accounts_connection.py` is rewritten for criteria 18, 19, 21, 22, 30–32 and 35.
  - Mechanical updates in the other zoom test files: `zm.connect(settings, …)` became `zm.connect(…)`, `HostKeyUnreadable` became `SecretUnreadable`, and `rotate_host_keys` became `rotate_encryption_keys`. Also: the account lock regex, the deferred-field name, the 013 webhook query count (0 → 1) and the 013 account-page `missing` state (now `unreadable`).

**Context contract, as implemented:** every variable is as written, under its exact name, including D20's `webhook_address_secure`.

- `zoom/connections.html`: `connections`.
- `zoom/connection_form.html`: `form` (with `client_secret_was_typed` and `webhook_secret_was_typed`), `is_add`, `connection`, `saved_slug`, `credentials_state`, `webhook_secret_state`, `last_zoom_event_at`, `webhook_address`, `webhook_address_secure` and `accounts_in_use`.
- `zoom/account_form.html`: `zoom_connection_state`, `zoom_connection_name`, `zoom_connection_url`, `can_manage_connections`, `webhook_secret_set` and `last_zoom_event_at`, plus the unchanged ones.
- `zoom/accounts.html`: `can_manage_connections`.

No deviations. Choices the brief left to the backend:

- **The webhook signatures** (MVT plan, "the exact signatures are the backend's choice"):
  - `verify(request, slug) -> VerifiedConnection | Refusal`;
  - `url_validation_reply(verified, event)`;
  - `is_from_account(verified, event)`;
  - `services.handle_event(verified, event, body_sha256, …)`.
- **`set_credentials` returns a bool**, and so do `set_webhook_secret` and `remove_webhook_secret`. A connection's first details are version 1: the version is only bumped when a client secret was already stored. `set_webhook_secret` with the secret already stored records nothing.
- **`rotate_secrets()` on a partly unreadable row** re-encrypts the readable secret on the instance. It then raises `SecretUnreadable` with the unreadable names as `args` (`"client secret"`, `"webhook secret"`) and the count as `.rotated`, so the command can name every item. **The command commits the readable values and still exits 1.** The unreadable ones are lost either way, and the exit status stops a rotation script before the old key is removed (D4).
- **An unreadable connection counts as "not connected"** for `ZoomProvider._client` (`ZoomNotConnected`, no HTTP), as it does for `is_connected()`.
- **The `{labels}` join** uses the existing `models.join_words` (renamed from `_join_words`).

**Migrations:** `0010_zoom_connections`. It removes `HostAccount.credential_set`, creates `ZoomConnection` with its three check constraints, and adds `HostAccount.zoom_connection` (`PROTECT`, nullable).

- **Reversibility:** checked in the dev container with `migrate zoom` → `migrate zoom 0009` → `migrate zoom`, all OK.
- **Data dropped:** applying it drops any connection name typed on a dev account (D11).

**Dependencies and settings:** no new dependency, and `config/` isn't touched. Nothing in `apps/` reads `ZOOM_S2S_*`, `ZOOM_CREDENTIAL_*` or `config.settings.base` any more; `test_connections.py::test_no_module_reads_credentials_from_settings` scans `apps/zoom`. `tmd-devops` (step 3) can now remove the `base.py` block, the example file, compose's `env_file` and `apps/core/test_zoom_settings.py`'s env tests. Until then, those settings tests still pass against the untouched `base.py`.

**For the verifier and reviewer**

- **Criterion 26's scan** covers `apps/zoom` here. Scanning `apps/` and `config/` as a whole is criterion 36's devops test: `config/settings/base.py` and `apps/core/test_zoom_settings.py` still hold the names until step 3.
- **Criterion 9's sidebar `aria-current`**, and the rendered markup in general, are the frontend's. Two backend tests do render the real templates, both in `test_connections.py`: `test_values_appear_only_where_allowed` (criteria 14 and 41) and `test_typed_secrets_are_never_sent_back[True]` (the two "wasn't kept" notes).
- **Criterion 43:** no existing test dumped the `zoom_*` tables, so `test_tokens_are_in_no_table_and_not_in_djangos_cache` is new. It dumps every `zoom_*` table, `zoom_zoomconnection` included.

**Self-check output** (dev container, 2026-11-02, after the frontend's step 2b templates were in place):

- `pytest --create-db -p no:cacheprovider -rfE`: **1610 passed in 113.44s**, 0 failed, 0 errors. This was the only `--create-db` run in step 3 (criterion 48). **Backend pytest run finished.**
- `ruff check .`: All checks passed. `ruff format --check .`: 128 files already formatted.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check` and `check --database default` (the dev `.env`, `fake`): no issues.
- `check --database default` with `ZOOM_PROVIDER=zoom` passed inline: four `zoom.E004` errors in criterion 32's new wording (`Zoom 01`, `Zoom 02`, `Zoom 03` and `polymathlesson Paid`: `no Zoom connection is chosen`). These are the dev accounts that step 7 (D19) takes out of use. It shows E004 reads the database, with no E005.
- Migration `0010` applied, reversed to `0009` and re-applied on the dev database.

#### Fix cycle 1 (agent plan step 5a, D21, 2026-11-02)

**Files changed**

- **`apps/zoom/zoom_api.py`** (SF1, N4; criterion 24): the token cache key is `(slug, credentials_version, client_id)`. `_forget_other_versions` became `_forget_lower_versions`, which drops only that slug's entries (tokens and fetch locks) with a **lower** version, whatever their Client ID. A same-version entry with another Client ID (a re-added connection's old app) is left alone; it's simply never looked up again. The module docstring says why the Client ID is in the key.
- **`apps/zoom/forms.py`:**
  - **SF2** (criteria 11 and 13): `__init__` sets `fields["client_secret"].required = self.is_add or self.credentials_state == "unreadable"`. `credentials_state` is now set on both pages (`None` on add). `clean_client_secret` has no empty-value branch: an empty or whitespace-only value is the field's `required` error, which is `CLIENT_SECRET_ERROR`.
  - **SF3** (criterion 11): `CONNECTION_NAME_HELP`, `ACCOUNT_ID_HELP` and `CLIENT_ID_HELP` are borrowed from `ZoomConnection._meta.get_field(...).help_text`. The form holds no copy of its own.
  - **Criterion 51:** new `ZoomConnectionForm.add_taken_errors()`. It asks the database again with the form's own lookups: `client_id_taken_by`, and on add the slug lookup that `validate_unique` makes. It adds the pinned `CLIENT_ID_TAKEN` and/or `CONNECTION_NAME_TAKEN` error to each field that is taken, and then forgets the typed secrets. It returns `False` when neither value is taken, so the view re-raises. It never reads the database's error text.
  - `full_clean`'s secret-dropping step moved into `_forget_typed_secrets()`, shared with `add_taken_errors()`, so the race path gets the same no-echo behaviour and the same "wasn't kept" notes.
- **`apps/zoom/views.py`** (criterion 51):
  - `ZoomConnectionFormViewMixin.form_valid` runs `form.save()` inside its own `transaction.atomic()` savepoint and catches only `IntegrityError`.
  - It then calls `form.add_taken_errors()`, re-raising when that returns `False`. On the change page it re-reads the row with `get_object()`, because `set_credentials` had already changed the in-memory instance. Then it returns `form_invalid` (200).
  - The success flash moved into a `saved_message()` hook on each view, so the race path can't add a success message.
- **`apps/zoom/models.py`** (SF3): the `help_text` of `slug`, `account_id` and `client_id` is now criterion 11's pinned add-page text.
- **`apps/zoom/migrations/0010_zoom_connections.py`** (SF3): edited in place (uncommitted). Only those three `help_text` strings changed.
- **`apps/zoom/management/commands/rotate_encryption_keys.py`** (N3): `f"the {name} of {connection.slug}"`. The `CLIENT_SECRET_NAME` conditional and import are gone, and the output is unchanged (the criterion 34 tests pass as they are).
- **`apps/zoom/tests/zoommock.py`:** `add_token(..., client_id=...)` can now match a token request on its Client ID as well as its secret.
- **`apps/zoom/tests/test_connections.py`:**
  - **Criterion 24:**
    - the key-shape assertion in `test_another_workers_save_makes_the_next_call_fetch_a_new_token` is updated;
    - new `test_the_cache_key_is_the_name_the_version_and_the_client_id`;
    - `test_a_new_version_drops_the_old_versions_token`, rewritten: newer evicts older, whatever the Client ID, and another slug is kept;
    - new `test_a_stale_read_doesnt_drop_a_newer_versions_token`: version 2's token survives a version-1 client and is reused, with one token request;
    - new `test_a_connection_re_added_under_the_same_name_gets_its_own_token`: the Basic header carries `other-client-id`, and every later call is `Bearer` with the new token, never the old one.
  - **SF2:** `test_the_add_form_labels_and_help` now expects `client_secret` to be required. New `test_the_client_secret_is_marked_required_only_when_it_is[add|unreadable|saved]` checks the rendered `required` attribute and the `required` message. A whitespace-only client secret case is added to the criterion 13 table.
  - **SF3:** new `test_the_name_and_id_help_is_the_models_and_is_the_pinned_text`, and `test_the_rendered_name_and_id_help_on_both_pages_is_the_models` (real templates, `id="<name>-help"`).
  - **Criterion 51:**
    - `test_a_client_id_added_at_the_same_moment_gets_the_taken_error[False|True]`;
    - `test_a_client_id_changed_at_the_same_moment_gets_the_taken_error[False|True]`;
    - `test_a_name_added_at_the_same_moment_gets_the_taken_error[False|True]`, which patches `ZoomConnectionForm.validate_unique` and not `client_id_taken_by`, as pinned;
    - `test_a_name_and_a_client_id_both_lost_show_both_errors`;
    - `test_any_other_integrity_error_is_not_swallowed`.

    The Client ID tests patch `client_id_taken_by` so that only the form's first call misses, and every later call asks the database for real. They assert two calls: the form's check, then the re-check after the error.

**Context contract:** unchanged. The change page's race re-render supplies the same variables, read from the stored row.

**Migrations:** none added. `0010_zoom_connections` is edited in place (help text only).

**Dependencies and settings:** none. `config/` isn't touched.

**For the verifier and reviewer**

- **A DEBUG-only channel, outside this cycle's scope** (found while writing criterion 51's log sweep).
  - **What happens:** with `django` forced to DEBUG *and* the real templates, `django.template` logs each missing optional variable (`narrow`, `min` and `max` in `partials/field.html`) with a traceback. That traceback's text, formatted when it's emitted, includes the field's widget context, so it contains a typed **Account ID or Client ID**. It never contains a secret, because the typed secrets are dropped from the bound data before the re-render.
  - **Why it's never written outside a test:** `base.py:218` pins `django` at `INFO`, so these records are never made.
  - **How the tests handle it:** criterion 40's sweep uses the stub templates for the same reason. Criterion 51's tests do too: they check IDs on the stub-template run, and secrets, ciphertexts, `Duplicate entry` and `IntegrityError` on both runs.
  - **Who could close it:** the frontend could give `field.html` defaults for those variables, or devops could pin `django.template` explicitly. I left it alone, because both are outside my ownership.
- **Reading log text:** read a captured record's text from `record.exc_text`, which is set when the record is emitted. `VariableDoesNotExist` formats its live context lazily, so calling `formatException` after the response sees a popped context and misses the value.

**Self-check output** (dev container, 2026-11-02):

- `pytest --create-db -p no:cacheprovider -rfE`: **1641 passed in 122.48s**, 0 failed, 0 errors (exit 0; step 2a had 1610). This was the only `--create-db` run in this cycle. **Backend pytest run finished.**
- `apps/zoom/tests/test_connections.py` on its own, before the full run: 124 passed.
- `ruff check .`: All checks passed. `ruff format --check .`: 129 files already formatted.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `python manage.py check`: System check identified no issues (0 silenced).

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS** (2026-11-02, criteria 1-48; 49 and 50 are not the verifier's)

**Checklist:** ruff ✅ · format ✅ (129 files) · `pytest --create-db` ✅ **1624 passed** (1606 before my 18 new tests; the 1610 in the notes was before devops rewrote `test_zoom_settings.py`) · `makemigrations --check --dry-run` ✅ · `check` ✅ · `check --database default` ✅ (dev, `fake`; with `ZOOM_PROVIDER=zoom` it gives E004 for the 4 dev accounts with no connection, as D19 expects) · `check --deploy` on the real prod stack, `USE_HTTPS=True`, no credential variable: `zoom` → only `security.W021`; `manual` → only W021 + `zoom.W001` ✅ · prod HTTP ✅.

**Criteria → evidence**
- 1-3, 5-7: `test_connections.py` (fields, constraints, repr, set_credentials/webhook/remove, states, rotate_secrets, bookable/locking, ciphertext, other key, crypto rename + single `cryptography` import).
- 4: `makemigrations --check` clean; backend reversed 0010 → 0009 → 0010.
- 8: `test_each_page_needs_the_change_permission`, `test_a_connection_has_no_permissions_of_its_own`; prod: anonymous → 302 login on all three; `no-store` seen.
- 9: **added** `test_connections_html.py` (sidebar `aria-current`, breadcrumbs, link shown/hidden by permission).
- 10: **added** (exactly one add link, in the head, before the empty state; row order, `No account yet`, tags with icon + word); query count by `test_the_list_query_count_is_fixed`.
- 11-14: existing label/help/widget/error/limit/note tests, plus **added** rendered-input tests (text type, autocapitalize etc., no `maxlength`, no `value`, notes in `aria-describedby`, `aria-invalid`). Prod: the invalid add shows both notes, with no typed secret in the source.
- 15: context tests + **added** rendered states, copy-value address (not a link), https warning on plain GET but not `secure=True`.
- 16-17: `test_the_only_reveal_route_is_the_host_keys`, `test_secrets_are_decrypted_only_by_the_allowed_callers`, `test_an_error_inside_save_masks_both_typed_secrets`, `test_both_pages_need_a_csrf_token`.
- 18-22: `test_zoom_accounts_connection.py` + **added** (select, label, help id, selected after an invalid POST, the three states, tags).
- 23-25, 26: `test_a_saved_client_secret_is_used_at_once_with_no_restart`, the token-cache and preview tests, `test_no_module_reads_credentials_from_settings`; full zoom suite passes.
- 27-29: webhook tests (one lookup of four columns, unreadable → 404 + one WARNING, matching by connection, a saved secret works on the next call). Prod: the signed validation was 404 before the secret was saved and 200 with the exact JSON after, with no restart.
- 30-35: checks and rotation tests (`test_zoom_accounts_connection.py`, `test_w002_*`, `test_rotation_*`, `test_the_old_command_is_gone`). E004 seen on the prod stack with the new wording.
- 36-39: `apps/core/test_zoom_settings.py` (16 tests) + `test_dockerignore_*`. Prod container: 0 `ZOOM_S2S_`/`ZOOM_CREDENTIAL` variables, `/app` has no `zoom-credentials*` file. `docker compose config --quiet` passes for prod and the dev overlay (re-run by the verifier, nothing printed).
- 40-43: `test_nothing_secret_is_logged_anywhere`, `test_values_appear_only_where_allowed`, `test_reprs_*`, `test_tokens_are_in_no_table_*`; **added** rendered-page leak test across the list, add, accounts and both account pages (secrets, ciphertext, `gAAAAA` and the two IDs absent; the IDs appear once, inside their inputs, on the change page). Prod gunicorn log after the walkthrough: 0 hits for any secret, ID or typed value. The `django.db.backends` pin is tested by devops.
- 44: the global `responses` block is unchanged.
- 45: template-rule tests in `apps/core` pass. **Contrast measured** from the real tokens: `.tag--bad` light `#B42318` on `#FFE3E2` = **5.43:1**, dark `#F59A94` on `#432A2A` = **6.20:1** (both at least 4.5). `.copy-value` on `--c-surface-2`: text 11.80 (light) / 7.73 (dark); help text 5.32 (light) / **4.54** (dark, passes by 0.04).
- 46: above. 48: I ran `--create-db` alone.

**Prod walkthrough (port 8011, `ZOOM_PROVIDER=manual`, throwaway user `verif015`):** all 38 scripted checks OK: empty list, invalid add, valid add, `Saved`/`Not saved`, webhook secret added, signed validation, account choosing the connection (`Set up` on the change page and the list), Check connection with no connection (message shown), hashed static files, 100/200-character limits. The `Check connection` call went to a connection-less account only. Logged-in HTML audit (list, add with errors, change pages, account pages): one `h1`, headings in order, skip link, landmarks present, every form input has a label, `aria-describedby` targets all exist, `aria-invalid` on errors, no `value` on any secret input. The only unlabelled inputs are the settings-dialog radios in the shell (pre-existing). Screenshots: `...\scratchpad\walk\shots\` (list empty/filled at 1440 and 400, add-errors at 1440 and 400, change nowebhook/saved/unreadable, account ready/unreadable/none at 1440).

**Clean-up:** the `zoom-verify*` connections and the three `Verify 015*` accounts were deleted with a `manage.py shell` script (there's no delete screen, D14), and the user `verif015` was deleted. The dev DB has no leftovers. The stack was restored to dev on 8011, and `/healthz/` returns 200.

**Tests added:** `apps/zoom/tests/test_connections_html.py` (18 tests, real templates).

**Observations (not failures):**
- On the add page the client secret input has no HTML `required` (the server refuses empty); criterion 11 doesn't ask for the attribute.
- The dev DB still holds the `Zoom 01-03` accounts with no connection (D19 step 7, as planned).
- The 400px full-page screenshot shows the page heading above the sticky top bar. This is a full-page capture artifact of the sticky header and wasn't investigated further.

### Re-verification (fix cycle 1) — 2026-11-02

**Verdict: PASS** (criteria 1-48 and 51)

**Checklist:** ruff ✅ · format ✅ (129 files) · `pytest --create-db -rA` ✅ **1641 passed** in 120.68s (the only `--create-db` run; output kept in the verifier's scratchpad) · `makemigrations --check --dry-run` ✅ · `check` ✅ · `check --deploy` n/a (no settings changed; the devops change is a comment) · prod HTTP ✅.

**Criteria:** 11, 13, 15, 24, 36 and 51 are covered by the tests the backend names in Fix cycle 1, and all pass in the full run. 1-10, 12, 14, 16-23, 25-35, 37-48 pass unchanged in the same run.

**Mutation checks** (dev container, bind-mounted source; each restored with `cp` from a copy, and `sha1sum` of `zoom_api.py` and `views.py` equals the "before" hashes, so the code is unchanged):
- Cache key without `client_id`: 7 tests fail, including `test_a_connection_re_added_under_the_same_name_gets_its_own_token`, `test_the_cache_key_is_the_name_the_version_and_the_client_id`, `test_a_new_version_drops_the_old_versions_token` and `test_a_stale_read_doesnt_drop_a_newer_versions_token`.
- `except IntegrityError` removed: 7 criterion-51 tests fail (the add/change Client ID cases, the name cases and `test_a_name_and_a_client_id_both_lost_show_both_errors`).
- `transaction.atomic()` savepoint removed: the same 7 fail.

**Prod image HTTP (port 8011, `ZOOM_PROVIDER=manual`, throwaway user `verif015b`):** the first build failed at `apt-get` (a network error, exit 100) and passed on retry. `web` became healthy. Add page: the `client_secret` input carries `required`. The rendered help for `slug`, `account_id` and `client_id` equals the pinned text (apostrophes are HTML-escaped). An empty secret on add returns 200 with `Paste the Client Secret from the App Credentials page of the Zoom app. It has no spaces.` in the error summary and at the field, `aria-invalid="true"`, `aria-describedby="client_secret-error client_secret-help"`, and the typed name, Account ID and Client ID kept. Nothing was saved. The user was deleted and no `verif-x` connection exists. The dev stack was restored on 8011 and `/healthz/` returns 200.

**For the reviewer: does the `django` INFO pin stop the `django.template` DEBUG records?** Yes. Measured under `dev`, `prod` and `test` settings, each with `LOG_LEVEL=DEBUG`: `django`, `django.template`, `django.db.backends` and `django.request` all have an effective level of INFO, and `isEnabledFor(DEBUG)` is False. `django.template` has no level of its own and inherits the `django` pin (`base.py:218`). `LOG_LEVEL` only sets the root logger, so it can't lower it. No such record is created in the real settings. It would appear only if someone sets `django` or `django.template` to DEBUG in code. Pinning `django.template` explicitly, or giving `field.html` defaults for `narrow`, `min` and `max`, would be a defence in depth. It isn't needed, and I changed no product code.

**Tests added this cycle:** none (the backend's tests already pin the fixes, and the mutations show they fail when the behaviour breaks).

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-11-02 (verifier PASS on criteria 1–48)

**Verdict: CHANGES REQUESTED.** There are no blockers, and the security sweep in agent plan step 5 passes on every item. Three should-fix items remain, all owned by the backend.

**Security sweep:** every item passes.

- **Write-only fields.** Inputs are write-only twice over: `full_clean` drops the typed secrets, and `secret_field.html` never writes a `value`. The reprs show only the slug.
- **Request and query hygiene.** `sensitive_post_parameters` and `sensitive_variables` cover every path, `django.db.backends` is pinned (`base.py:225`), there is one reveal route only (`account_host_key`), and there is no new `csrf_exempt`.
- **Token cache.** The cache is keyed by version and the version is read on every operation. SF1 covers the one gap.
- **Webhook.** The webhook does one four-column lookup and keeps 013's 404s.
- **Locking.** Booking paths lock accounts only, through `HostAccount.objects.locked()`.
- **Key rotation.** `rotate_encryption_keys` runs in one transaction and exits 1 on an unreadable value.
- **Environment.** No env reads and no `ZOOM_S2S_` / `ZOOM_CREDENTIAL` remnants are left in `apps/`, `config/` or compose. The README still mentions them; step 6 updates it.

**Should fix**

1. **SF1: token cache key no longer includes the Client ID.**
   - **Where:** `apps/zoom/zoom_api.py:224`.
   - **Problem:** 006's key was `(slug, client_id)`. A connection deleted and re-added under the same name starts again at version 1. A worker still holding a token for `(slug, 1)` would then use the *old* app's token for up to an hour, and create meetings on the wrong Zoom account. Today this can happen only after a shell delete. D14's planned "Remove" would make it reachable from a screen.
   - **Fix:** key on `(slug, version, client_id)`, keep `_forget_other_versions` matching on slug, and update the cache-key tests (`test_connections.py:991`, `:1007-1011`).
   - **Owner:** backend. The planner amends criterion 24's pinned key.
2. **SF2: client secret is not marked `required` on the add page.**
   - **Where:** `apps/zoom/forms.py:781` and `:865-872`.
   - **Problem:** criterion 11 says the first four fields are required, and Design D.5 says the partial writes `required`. Screen readers announce Account ID and Client ID as required, but not Client secret.
   - **Fix:** set `fields["client_secret"].required = self.is_add or self.credentials_state == "unreadable"` in `__init__`, and delete the empty-value branch of `clean_client_secret`. The pinned text is the `required` message, and P3's behaviour is unchanged.
   - **Owner:** backend.
3. **SF3: connection help text is duplicated, in different words.**
   - **Where:** `models.py:353` against `forms.py:682`, and the ID help at `models.py:359` / `:365` against `forms.py:686-687`.
   - **Problem:** this is the same pattern as 008's SF3. The model's text is never shown and has already drifted from the pinned copy.
   - **Fix:** make the model `help_text` the pinned add-page text, and have the form borrow it with `_meta.get_field(...).help_text`. Migration 0010 is uncommitted, so edit it in place.
   - **Owner:** backend.

**Nits**

- **N1:** `account_form.html:46`, `:55` and `:64` repeat the same `{name}` link-or-span. This is acceptable as is; if the template is touched again, `zoom/partials/connection_name.html` could hold it once. Owner: frontend.
- **N2:** keep the frontend's undated fallback, `Connection details saved.` / `Webhook secret saved.` (`connection_form.html:46`, `:63`). It mirrors the host key's `saved_legacy` and is reachable only for rows made outside the screens. **Pin both sentences in criterion 15** as a dated amendment; no code change. Owner: planner.
- **N3:** `rotate_encryption_keys.py:64`. `exc.args` already names the secret, so `f"the {name} of {connection.slug}"` gives the same output. Drop the `CLIENT_SECRET_NAME` conditional and its import. Owner: backend.
- **N4:** `zoom_api.py:125`. A client built from a stale read evicts the *newer* version's token. Evict only lower versions; fold this into SF1. Owner: backend.
- **N5:** `forms.py:859` checks that the Client ID is free before `save()`, so two people adding the same Client ID at once would raise an `IntegrityError`.
  - **Risk:** MySQL's "Duplicate entry" text would reach the log, against criterion 41, and the 500 report's SQL frame locals would hold ciphertext.
  - **Fix:** catch the error in the views and show the pinned `CLIENT_ID_TAKEN` message (backend). Name Zoom connection values in the `mail_admins` comment at `base.py:205` (devops).

**Judged as asked**

- **Undated fallback:** accept and pin it (N2).
- **Repeated `{name}`:** a nit only (N1).
- **The 320px wrapping rule** (`style.css:3020`): accept. It is needed for criterion 45's reflow and also fixes an existing 6px sideways scroll.
- **The `.env.example` rotation line** (`:67`): accept. It is necessary and matches D4.
- **Missing `required`:** should-fix (SF2).

**Good**

- `HostAccount.objects.locked()` holds D8's "lock the account rows only" rule in one place.
- `webhooks.verify`'s frozen `VerifiedConnection` with `repr=False` fields, together with the two-layer write-only inputs, is a pattern to reuse for any future secret.

### Round 2 — 2026-11-02 (after fix cycle 1; re-verification PASS, 1641 tests)

**Verdict: APPROVE.** No blockers, no should-fix items.

**How round 1 was fixed**

- **SF1 / N4: token cache key.**
  - **The key:** `zoom_api.py:231` keys on `(slug, version, client_id)`.
  - **Eviction:** `_forget_lower_versions` (`:122-135`) evicts only lower versions of the same slug.
  - **Docs and safety:** the docstrings (`:19-28`, `:125-129`) explain why. The preview cache is unaffected, because a re-added connection gets a new pk.
  - **Proof:** the verifier's mutation check made 7 tests fail.
- **SF2: client secret `required`.**
  - **The flag:** `forms.py:816` sets `required = is_add or credentials_state == "unreadable"`.
  - **Empty and whitespace values:** the empty-value branch is gone (`:874-882`), so whitespace-only input also gets the pinned `required` error.
  - **Rendering:** `secret_field.html:9` writes the attribute, and the verifier confirmed it on the prod image.
- **SF3: help text written once.** The model (`models.py:354-356`, `:361`, `:367`) holds criterion 11's pinned text verbatim. The form borrows it (`forms.py:684-687`), and migration `0010` matches.
- **N2: undated sentences.** They are pinned in criterion 15 and rendered exactly (`connection_form.html:46`, `:63`).
- **N3: rotation tidy-up.** Done (`rotate_encryption_keys.py:58-59`).
- **N5: save race.**
  - **Backend:** criterion 51 is handled; see the next section.
  - **Devops:** the `mail_admins` comment names the connection values (`base.py:205-206`).
- **N1:** declined in D21.

**New code, security first**

- **`form_valid`** (`views.py:1429-1442`):
  - **Savepoint and catch:** it saves in its own savepoint, catches only `IntegrityError`, and re-raises when `add_taken_errors()` finds nothing taken. A test covers the re-raise.
  - **Error text:** it never reads the database's error text.
  - **Flash:** there is no success message on the race path.
- **Change-page `get_object()` re-read** (`:1436-1439`):
  - **Why it's needed:** `form.instance` was changed in memory before the save failed.
  - **Locking:** the lock is already held, so the re-read adds no new lock.
  - **What the template sees:** it never reads `form.instance`, and the test asserts the stored values.
- **`add_taken_errors()`** (`forms.py:902-931`):
  - **Lookups:** it uses the same lookups as the form, and checks the slug only when the field exists.
  - **Errors:** it raises the pinned errors with `code="unique"`, and both if both values collide.
  - **Secrets:** it carries `@sensitive_variables`, then calls `_forget_typed_secrets()`.
- **`_forget_typed_secrets()`** (`:841-858`): a straight extraction, shared with `full_clean`. The race re-render never echoes a typed secret and still shows the "wasn't kept" notes.
- **`saved_message()` hook:** fine.
- **Criterion 51's tests** (`test_connections.py:1485-1683`):
  - **Simulation:** they follow the pinned simulation.
  - **Assertions:** they check call counts, field errors, kept values, row counts and the unchanged winner.
  - **Log sweep:** the logs hold no `Duplicate entry`, `IntegrityError`, secret or ciphertext, and there is no `django.request` ERROR.

**Nits** (optional; none blocks; not taken up in 015):

1. **The re-check silently relies on READ COMMITTED** (`forms.py:903-931`).
   - **Why:** the re-check is a plain read inside the request's transaction. It sees the winning row only because MySQL's Django default, READ COMMITTED, is in force; `base.py` sets no `isolation_level`.
   - **What breaks:** under REPEATABLE READ it would read the snapshot, return False, and re-raise: the 500 that criterion 51 forbids. 008 hardened `stop_booking_errors()` for the same reason.
   - **Fix:** name the dependency in the docstring, or make the two lookups locking reads.
   - **Owner:** backend.
2. **The `django.template` DEBUG channel** (the main session's open point).
   - **Judgement:** acceptable as is.
     - The verifier measured `django.template` at an effective INFO under the dev, prod and test settings, even with `LOG_LEVEL=DEBUG`.
     - Only IDs could ever appear, never secrets.
     - The channel has existed since 005 and isn't new here.
   - **If closed later:** prefer an explicit `"django.template": {"level": "INFO"}` pin next to the `django.db.backends` pin (`base.py:224-227`) over defaults in `field.html`. The pin covers every form; the defaults would fix one partial.
   - **Owner:** devops.

**Good**

- **Savepoint, ask again, re-raise.** This turns a unique-constraint race into the pinned field error without reading the database's error text. It's the pattern to reuse for any future check-then-save form.
- **Re-reading the stored row.** The page never describes a change that wasn't saved.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Status stays `Verifying`.** Verification is PASS (including the fix-cycle re-verification of 2026-11-02, 1641 tests) and Review is APPROVE (round 2), so everything that can be checked here is done. The one thing open is criterion 50, the owner's live check: add the real account's connection on the Zoom connections screen and press `Check connection` with no restart, type a wrong client secret and then the right one, run 006 criterion 48's steps 2, 3 and 5, and (once the webhook path is reachable) 013 criterion 26 with the Secret Token typed on the connection page. This follows 006, 011, 012 and 013, which stay `Verifying` until their owner live checks. It becomes `Done` once the owner reports criterion 50's results. Agent plan step 7 (taking the dev accounts Zoom 01-03 out of use, D19) is not a docs task and is not in the README.

**Files updated** (criterion 49)
- `README.md`:
  - removed the `zoom-credentials.env` setup, the `ZOOM_CREDENTIAL_SETS` / `ZOOM_S2S_<NAME>_*` paragraph, the dev-stack `env_file` note and every `rotate_host_keys` mention;
  - "Connecting an account to Zoom" steps 8-10 are now adding the connection on the Zoom connections screen (where each value comes from in Marketplace) and choosing it on the account; "Rotating a secret" is typing the new value there; the D14 note (an abandoned connection: regenerate its secret in Marketplace);
  - "Setting up the webhook": the address comes from the connection page, and the Secret Token is typed there (Validate passes at once);
  - rotation paragraph: `rotate_encryption_keys`, which must succeed before the old key is removed;
  - the `HOST_KEY_ENCRYPTION_KEYS` setup paragraph and table row: also protects connection secrets, back it up apart from the database, and what to do if both leak (D16);
  - the redeploy step: recreate `web` once to drop the old `env_file`.
- `CLAUDE.md` (no section deleted; changed in place):
  - the `zoom` bullet: the "env only, task 006 D2" sentence is replaced by the `ZoomConnection` reality (IDs readable, secrets Fernet-encrypted under the same keys, `IT desk` on `zoom:connections`, write-only, no reveal), the `(slug, credentials_version, client_id)` token cache, `rotate_encryption_keys`, the one-lookup webhook, and criterion 51's savepoint, ask-again and re-raise pattern;
  - Environment gotchas: the "Exception: Zoom credentials" bullet is rewritten (no env file, no `env_file`, the "Planned, not built" sentence is gone; backup rule added), and the `ZOOM_PROVIDER` gotcha's "working credential set" is reworded;
  - Shared form partials: `partials/select_field.html` and `zoom/partials/secret_field.html` added;
  - the `config/log_filters.py` bullet: `django.db.backends` pinned at `INFO` (D15).
- `docs/CHANGELOG.md`: the 015 entry ("awaiting the owner's live check"), and a one-line pointer in 013's entry that its "planned, not built" note is now built.
- Dated "Amended by 015 (2026-11-02)" notes in earlier briefs, covering every item under "Amendments to earlier briefs":
  - `docs/tasks/005-zoom-link-requests.md`: D17, criterion 46 and the rotation steps;
  - `docs/tasks/006-live-zoom-connection.md`: the requirement paragraph and out-of-scope line, Terms, criteria 2, 3, 4, 6, 7, 9, 34, 35, 36, 40, 44, 46, 47, 48, and D2 (reversed), D11, D13, D16 and R3;
  - `docs/tasks/008-zoom-accounts.md`: criterion 4, the form's field order and the `HostAccount` docstring;
  - `docs/tasks/011-cancel-and-start-link.md`: D11 and the `SecretUnreadable` rename;
  - `docs/tasks/013-zoom-webhook-sync.md`: Scope's settings bullet, Terms, criteria 1, 2, 4, 6, 12, 24, 25, 26 and 29, D6, D12, R7, the MVT and the devops notes;
  - `docs/tasks/014-recording-links.md`: criterion 3, the MVT's `handle_recording_completed` and D5.

**Not done on purpose:** the round-2 nits (the re-check's reliance on READ COMMITTED, and pinning `django.template` at `INFO`) are not taken up; they are listed as follow-ups in the CHANGELOG entry. Review N1 (the repeated `{name}` link-or-span) was declined in D21. The README's go-live gate list is unchanged: the brief does not ask for 015 there.
