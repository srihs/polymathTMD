# 015 — Zoom connections in the app: credentials typed on a screen and stored encrypted, replacing `zoom-credentials.env`

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Planned <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

**Starts only after brief 013 is Done.** The owner's live checks (006 criterion 48, 013 criterion 26) then run through the new screen (criterion 50).

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
   - **`remove_webhook_secret(*, by)`** clears it and records the change. It does nothing when no secret is saved.
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
    - **Empty state:** `No Zoom connections yet. Add one for each paid Zoom subscription.`, with the add button.
11. **Add (`zoom:connection_add`).**
    - The fields, in order: `slug` (`Connection name`), `account_id`, `client_id`, `client_secret`, `webhook_secret`. The first four are required; the webhook secret is optional.
    - A valid POST:
      - creates the row through `set_credentials` and (if typed) `set_webhook_secret`, with `by` the IT user;
      - sets `credentials_version` to 1, `credentials_changed_at` to now and `credentials_changed_by` to the user;
      - redirects 302 to `zoom:connections` with the success message `Added the Zoom connection {slug}. Next, choose it on the Zoom account that uses it, then press Check connection there.`
12. **Change (`zoom:connection_edit`).**
    - **The name is shown, not editable** (D2). The form has no `slug` field, and a POSTed `slug` changes nothing (test).
    - `account_id` and `client_id` are prefilled with the stored values (D3).
    - **Both secret inputs always render with no value.** Their labels are `New client secret` and `New webhook secret`. Leaving them empty keeps what's saved.
    - `Remove the saved webhook secret` (a checkbox) is present only when a webhook secret is saved.
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
    - `client_secret`: `Paste the Client Secret from the App Credentials page of the Zoom app. It has no spaces.` This also covers empty on the add page.
    - `webhook_secret`, when typed: `Paste the Secret Token from the Event Subscriptions part of the Zoom app. It has no spaces.`
    - A new webhook secret **and** Remove ticked: `Type a new webhook secret or tick Remove, not both.`

    The page's error summary leads with `We couldn't save this Zoom connection yet.` Each error is tested, and so is the kept value of every non-secret field.
14. **A typed secret is never sent back.**
    - After any invalid POST, the HTML contains neither typed secret anywhere, and neither secret input has a `value` attribute.
    - For each secret that was typed, a note shows above its field, and is added to the field's `aria-describedby`:
      - `For your safety, the client secret you typed wasn't kept. Type it again.`
      - `For your safety, the webhook secret you typed wasn't kept. Type it again.`

      The form exposes this as `client_secret_was_typed` and `webhook_secret_was_typed` (008's host-key pattern, D7).
    - No page, before or after any POST, contains a saved secret's plaintext or ciphertext (tested on the list, the add page, the change page, both account pages and the accounts list).
15. **The change page shows each secret's state, never the secret.**
    - **Connection details:**
      - `saved`: `Connection details saved on {date} by {name}.` The ` by {name}` part is dropped when `credentials_changed_by` is empty.
      - `unreadable`: a `notice--bad`: `The client secret is saved, but it can't be read with the server's current encryption keys. Type it again.`
    - **Webhook secret:**
      - `saved`: `Webhook secret saved on {date} by {name}.`, followed by `Last heard from Zoom on {when}.`, or `Nothing heard from Zoom yet.` when no event is recorded. `last_zoom_event_at` is 013's `ZoomEvent.objects.last_received_at(slug)`, one aggregate.
      - `none`: titled `No webhook secret saved`, with `Without it, changes made directly in Zoom aren't seen here. Add it once the Zoom app's Event Subscription is set up.`
      - `unreadable`: `A webhook secret is saved, but it can't be read with the server's current encryption keys. Type it again.`
    - **`Address for Zoom's Event Subscriptions`:** the absolute URL of `zoom:webhook` for this slug, built from the request with `build_absolute_uri` (D6). It's plain text that a person can select, and isn't a link.
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
    - The field is on both the add and the change pages. Its widget is a `<select>` rendered through the existing form partials, never `field.html`'s text-input path (CLAUDE.md's rule for choice widgets).
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
21. **The accounts list's `Zoom connection` column** shows `Set up`, `Not set up` or `Can't be read` (replacing `Missing on the server`), each with an icon and a word, through `zoom/partials/account_tag.html`. 006's "a missing connection matters only on a bookable account" styling rule is kept. The list's query count is the same with 1 and with 5 accounts, each linked to a connection.
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
    - `zoom_api`'s cache key is `(slug, credentials_version)`.
    - Building a client for `(slug, v)` drops any cached token for the same slug with another version, so a replaced secret's token isn't kept in that process.
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

    The `HOST_KEY_ENCRYPTION_KEYS` comment says it also encrypts Zoom connection secrets, and that a database backup plus these keys gives access to Zoom (D16, R1). A source scan finds no `ZOOM_S2S` and no `ZOOM_CREDENTIAL` in:
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
49. **Docs are complete.** The docs writer makes every amendment listed under "Amendments to earlier briefs" below, the README changes, `CLAUDE.md`'s two places, and `docs/CHANGELOG.md`. The reviewer checks the list is fully covered.
50. **The owner's live check** (after this brief passes verification and review, and after agent plan step 7 has taken the dev test accounts Zoom 01–03 out of use (D19); the main session gives the owner these steps, and the verifier records the reported results).
    1. On `Zoom connections`, add the real account's connection (Account ID, Client ID, Client Secret). Choose it on that Zoom account, and press `Check connection`. It shows `The Zoom connection works for {label}.` **with no restart.**
    2. Type a deliberately wrong client secret and save. `Check connection` at once shows criterion 22's `ZoomAuthFailed` text. Type the real one back and save. `Check connection` works again at once.
    3. Then run 006 criterion 48, steps 2, 3 and 5. Step 4's "wrong secret (restart)" is replaced by step 2 above, and no `zoom-credentials.env` step remains.
    4. Then, once 013 is Done and the webhook path is reachable, run 013 criterion 26 with the webhook Secret Token typed on the connection page (013 D6, step 4 amended). Marketplace's **Validate** passes as soon as the page is saved.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner's four answers settle who edits, the env file, the timing and the oversight framing. The planner has decided the points the main session asked it to settle (D1–D17). The one point flagged for the owner, C1, is now **closed** by the owner's answer (D18).

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

**Oversight note (for the main session, not an agent task).** The owner counts this brief as a correction of 006 D2. Per CLAUDE.md "Oversight capture", the main session runs `/oversight` when the owner asks for the commit. The `CLAUDE.md` changes that make it durable are authored first by `tmd-docs-writer` (step 6).

**Risk register** (`delivery-execution:risk-register`)

| # | Risk | Likelihood / impact | Response | Trigger | Owner |
|---|---|---|---|---|---|
| R1 | A database backup and `HOST_KEY_ENCRYPTION_KEYS` leak together, giving full Zoom API access to every connected account (D16, accepted by the owner) | Low / **High** | **Accept with mitigation.** The README's backup advice says to store the keys apart from database backups. If both leak: regenerate every Client Secret and webhook Secret Token in Marketplace, type them on the connection pages, and rotate the keys (`rotate_encryption_keys`) | a lost or exposed backup | owner, devops |
| R2 | The old key is removed after rotating only some secrets, so every connection becomes unreadable and all booking stops | Low / **High** | **Avoid:** one command, one transaction, exit 1 on any unreadable value (D4). E004 names each affected account | `zoom.E004 … can't be read`, or Check connection's unreadable message | owner, devops |
| R3 | A secret leaks through the HTML (an echoed value), logs (SQL parameters at `DEBUG`), an error page or a `repr()` | Low / **High** | **Avoid:** write-only fields, `sensitive_*`, the `django.db.backends` pin, and a test per channel (criteria 14, 17, 40–42) | a test failure, or the reviewer's sweep | backend, devops, reviewer |
| R4 | A worker keeps using a token from replaced credentials, so a "fixed" secret seems not to work, or a revoked one seems to | Medium / Medium | **Avoid:** a version-keyed cache read per operation (D8; criteria 23–24) | Check connection disagrees with a fresh save | backend |
| R5 | IT mixes up connections (picks the wrong one on an account), so bookings hit the wrong Zoom account | Low / **High** | **Mitigate:** Check connection proves the user exists on that app (006 criterion 36). 013 criterion 31's "gone" double-check stops mass cancels. The Client ID is unique across connections | a `ZoomUserNotFound` on Check connection | IT desk |
| R6 | Dropping `credential_set` loses names someone typed | Low / Low | **Accept:** no credentials existed, so no name ever made an account `ready` (D11) | none | backend |
| R7 | Parallel agents break the test database | Medium / Medium | **Avoid:** only the backend runs `--create-db` in step 3 (criterion 48) | false failures | main session |
| R8 | A credential is mistyped (a stray space, the wrong field) | Medium / Low | **Mitigate:** no-whitespace validation, Marketplace's own labels, and Check connection straight after (criteria 13 and 23) | auth failure on Check connection | IT desk |

**Follow-ups** (recorded, not in this brief)

- **"Remove an unused Zoom connection"** (D14).
- **014's README step "Restart `web` so the next token carries the new scope".** It stays correct, because tokens live in process memory. A later brief could add a version bump on demand (for example a "Get a new token" action) if restarting proves awkward.

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
  - the cache key is `(slug, version)`, dropping other versions of the same slug (criterion 24);
  - `ZoomClient` is otherwise unchanged.
- **`providers.ZoomProvider._client`:** `host_account.zoom_connection.credentials()`, raising `ZoomNotConnected` when no connection is chosen or it's unreadable.
- **`services.py`:**
  - `_preview_key` (criterion 25);
  - `check_connection`'s states and the three new texts (criterion 22);
  - `handle_event`'s matching by connection (criterion 28);
  - the connection screens' flash texts, beside the account ones (criteria 11–12).
- **`webhooks.py`:** `verify()` does one lookup, returns the verified connection with its decrypted secret, and logs the unreadable case (criterion 27). `url_validation_reply` and `is_from_account` take what `verify` returns. The exact signatures are the backend's choice, and are recorded in its notes.
- **`forms.py`:**
  - `ZoomConnectionForm`, one class for add and change like `HostAccountForm` (D6 of 008). It has the secret-dropping `full_clean`, `*_was_typed`, and `remove_webhook_secret` only when one is saved;
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
| `form` | `ZoomConnectionForm` | Fields: `slug` (**add only**), `account_id`, `client_id`, `client_secret`, `webhook_secret`, `remove_webhook_secret` (**change only, and only when one is saved**). Attributes: `client_secret_was_typed` and `webhook_secret_was_typed` (bool). Labels, help and widget attributes come from the form. The secret widgets never render a value. |
| `is_add` | bool | Picks the h1, title, breadcrumb and button (`Add the connection` / `Save changes`). |
| `connection` | `ZoomConnection` or `None` | `None` on add. On change the template reads only: `credentials_changed_at`, `credentials_changed_by` (User or None), `webhook_secret_changed_at` and `webhook_secret_changed_by`. |
| `saved_slug` | str | Change only: the stored name, for the heading, the breadcrumb and the read-only name line. `""` on add. |
| `credentials_state` | str | `"saved"` or `"unreadable"` on change; `"none"` on add. |
| `webhook_secret_state` | str | `"none"`, `"saved"` or `"unreadable"`; `"none"` on add. |
| `last_zoom_event_at` | aware datetime or `None` | Only when `webhook_secret_state == "saved"`; otherwise `None`. |
| `webhook_address` | str | Change only: the absolute `zoom:webhook` URL for `saved_slug`. `""` on add. |
| `accounts_in_use` | list of `HostAccount` (`pk`, `label`) | Change only; empty on add. |

Flash messages: criteria 11–12, at the `success` level, on `zoom:connections`.

**`zoom/account_form.html`** (changed; replaces the 006 and 013 connection variables)

| Variable | Type | Notes |
|---|---|---|
| `form.zoom_connection` | bound `ModelChoiceField` (select) | Replaces `form.credential_set`. Rendered through the existing choice partials, never `field.html` (CLAUDE.md). |
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

**`zoom/partials/account_tag.html`** (changed): for `kind="zoom"`, `state` takes `"ready"`, `"unreadable"` or `"none"` (`"missing"` is retired). The words are `Set up`, `Can't be read` and `Not set up` (criterion 21).

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
  - `docs/design/form-section.md`, `flash-messages.md` and `password-field.md` (the designer decides whether the secret inputs follow it).
- **Django ships:** `CreateView`, `UpdateView`, `ListView`, `ModelForm`, `ModelChoiceField`, `Prefetch`, `CheckConstraint`, `sensitive_post_parameters`, `sensitive_variables`, `never_cache`, `build_absolute_uri` and `messages`.
- **No new dependency.**

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

0. **Gate:** start only after brief 013 is **Done**. **Port 8011** for every HTTP check, passed inline (`WEB_PORT=8011 …`), never written to `.env` (D17).
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
     - `account_form.html`'s connection section, `accounts.html`'s link, `account_tag.html`'s states;
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
6. **`tmd-docs-writer`:**
   - criterion 49: every item under "Amendments to earlier briefs";
   - the README (setup, rotation, backup advice D16, D14's note);
   - `CLAUDE.md` (the zoom bullet and the environment gotchas, written before the main session's `/oversight` commit, since it makes the episode durable);
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

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->
