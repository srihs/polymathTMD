# 004 — Make f-desk the app's design theme

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> so now make f-desk as the design theme for the project.

**Reading:** The client approved the `design/f-desk/` look-alike (brief 003, D13) in one configuration: light mode, purple sidebar, standard 250px sidebar, full width. That look now becomes the real app's theme. This is a **port, not a copy**. The prototype's tokens, shell and components move into `static/` and `templates/`, following the MVT/DRY rules the prototype did not have to follow: template partials, `{# #}` headers, URLs by name, one icon sprite, and no fake data. The port also takes up the porting follow-ups that brief 003's review recorded (role-named tokens, type in `rem`, one visually-hidden utility, the "Icons only" sync nit, a 320px reflow check). It amends brief 003's criteria that the owner's post-close changes invalidated (always light on first visit, purple sidebar by default). Only two pages exist today: sign-in and home. Both move into the new look. Home becomes the dashboard shell with honest placeholder content, and the sidebar lists only destinations that really exist. Everything the prototype showed that the app cannot do yet (requests, devices, design kit) waits until its feature arrives. The search field and the notifications bell stay in the top bar to match the approved look, but as honest placeholders that say they aren't available yet (owner's answer, D12). The first is brief 005 (Zoom link requests), and this brief leaves the shell ready for it.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**In scope**

- `static/css/style.css`: replaced by the f-desk system, ported from `design/f-desk/style.css` and `docs/design/directions/f.md`:
  - role-named tokens (no value-named ones);
  - type sizes in `rem`;
  - one visually-hidden utility;
  - only the components the app's templates use now, plus the shell. Dead prototype-only rules (requests table, device page, chart, `kit-*`, `?demo=` states) are **not** ported. Brief 005 and later bring over what they need from `design/f-desk/`.
- `static/js/theme-init.js` (new) and `static/js/app.js`, replaced by the f-desk enhancements. What stays:
  - blocks 1–8 as they apply to the app;
  - the sign-in page's existing behaviours (below);
  - the "Icons only" sync fix.

  What does not come across: the `?demo=` block, and the old inventory-prototype code (modals, stock forms, chart, filters, `window.showToast` / `openModal`).
- `templates/base.html` becomes the f-desk document and shell. It is split into partials under `templates/partials/` and included with `{% include … with … only %}`. The Feather sprite becomes **one** partial. `partials/icon_templates.html` is deleted, because its only consumer, the old toast code, is gone.
- `templates/registration/login.html` is ported to the f-desk split sign-in, keeping every brief 001 behaviour and test.
- `templates/core/home.html` is ported to the shell, with honest placeholder content.
- Fonts: IBM Plex Sans 300/400/500/600 from Google Fonts, `display=swap`, replacing Cinzel, Nunito and Nunito Sans.
- Django `messages` rendered through one partial, in f-desk's flash component, placed in the page flow under the title row (D16). The messages context processor is already on, and brief 005 needs it for "request sent" confirmations.
- `User.initials` (a model property, no migration) for the avatar in the user menu.
- Tests: existing tests updated deliberately where the markup changes (listed in the MVT plan), and new shell and guard tests.
- Docs at the end: `CLAUDE.md` (Front end, Icons, UI conventions → tokens), `README.md` (third-party notices), `docs/CHANGELOG.md`, and a note in `design/README.md` that `f-desk/` is now a frozen record.

**Out of scope**

- The Zoom link-request feature and any requests, devices, search, notifications or design-kit screens (brief 005 onward).
- Django admin styling. The admin keeps Django's own look.
- Custom 404/500 templates.
- Changing `design/f-desk/` itself, or re-capturing its 39 screenshots. It is frozen as the approved reference (D1).
- Any settings, env, Docker or dependency change. Google Fonts was already loaded from the same hosts. No `tmd-devops` work.
- Raising the D9 text sizes (such as the 10.5px tags). The client's choice stands. `rem` only makes the browser's font-size preference work.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

"Shell page" means any page that extends `base.html` without overriding `{% block body %}`. Today that is only `core:home`. "Both modes" means `data-theme="light"` and `data-theme="dark"`. Pixel values are at the browser's default 16px root size unless stated. f.md means `docs/design/directions/f.md` (the source of every value), and 003/n means brief 003's criterion n.

**Document head and first paint**

1. Every page's `<html>` is rendered by the server as `<html lang="en-LK" data-theme="light" data-width="full" data-nav-size="standard" data-nav-tone="purple">`. That is the approved configuration, so the page is correct with JS off.
2. In `<head>`, in this order: `<script src="{% static 'js/theme-init.js' %}">` with neither `defer` nor `async`, then the IBM Plex Sans stylesheet link from `fonts.googleapis.com` (weights 300;400;500;600, `display=swap`), then `css/style.css`. `js/app.js` is loaded once with `defer`. No page references `Cinzel`, `Nunito` or `Nunito+Sans`. This is a pytest check on the rendered HTML of login and home.
3. **First visit (amends 003/19, 003/23, 003/24).** With empty `localStorage` and the browser emulating `prefers-color-scheme: dark`, `<html>` carries `data-theme="light"` and `data-nav-tone="purple"` at `DOMContentLoaded` on login and home, and the computed page background is the light token. The page never follows the device's colour scheme.
4. **Saved choice wins (003/24 kept).** With `tmd-layout` seeded to `{"theme":"dark","width":"boxed","navSize":"compact","navTone":"light"}`, all four attributes are already on `<html>` at `DOMContentLoaded` on both pages. `theme-init.js` does nothing but read `tmd-layout` and set those four attributes.
5. **One source for the allowed values and defaults.** The four settings' allowed values and defaults are defined once in JS, and the other file reads them from there. Neither file carries its own copy. The reviewer confirms this by reading `theme-init.js` and `app.js`.

**The shell (shell pages)**

6. **Sidebar, standard size, purple tone.**
   - The crest chip (`static/img/crest-chip.png`, `alt=""`) and the wordmark `Technology Management Desk`, linked to `core:home`.
   - Inside `<nav aria-label="Main">`: group `Menu` → `Home` (`core:home`).
   - For users with `is_staff` only, a second group `Administration` → `Admin` (`admin:index`).
   - Every `href` in the nav equals `reverse()` of one of those URL names. There are no other links, no `#` links and no disabled "coming soon" items.
   - On `core:home`, the `Home` link has `aria-current="page"`, and nothing else in the nav does.
   - Rendered width at 1440×900 is 250px (±2px).
7. **Active marker on purple (amends 003/29).**
   - The current item's marker (the 3px bar, and its row background if any) uses the colour the Design section records. It is **not** `#722A82`.
   - It reaches ≥3:1 against the purple `--nav-bg` **and** against the active row background.
   - The active item's text reaches ≥4.5:1 against the active row background.
   - The verifier recomputes all three ratios from the token values.
8. **Top bar**, 70px (±2px) at 1440×900, in the prototype's order (003/12, owner's Q1 answer, D12). Left: the menu toggle (`Show the menu` / `Hide the menu`, `aria-expanded`, `hidden` in the HTML, revealed by JS), the no-JS `Menu` link to the sidebar's id, then the **search placeholder** (criterion 37). Right: the colour-mode button (`Switch to dark mode` / `Switch to light mode`, `hidden` in the HTML), the **notifications bell** (criterion 38), the `Layout settings` button (`hidden` in the HTML), and the user menu. Nothing in the top bar leads to a URL that does not exist.
9. **User menu** is a `<details>` that opens with JS off. Its summary shows the avatar with `user.initials` and the name `user.get_full_name`, falling back to `user.username`. Its panel contains `Layout settings` (JS only, `hidden` in the HTML) and `Sign out`. `Sign out` is a `<button type="submit">` inside a `<form method="post" action="{% url 'accounts:logout' %}">` with a CSRF token. No `<a>` on any page points at `accounts:logout`. With JS on, `Escape` and a click outside close the menu and return focus to its summary.
10. **Title row.** Directly under the top bar sit the `<h1>` and a `<nav aria-label="Breadcrumb">` with an `<ol>` whose last item has `aria-current="page"`. On home the h1 is `Home` and the trail is `Home`. At 1440 wide they share a row, and at 400 wide they stack.
11. **Footer** on shell pages: left `{current year} © Polymath College`, with the year from `{% now "Y" %}`; right `Technology Management Desk`.
12. **Settings dialog** (003/21 and 003/22 carried over).
    - A `<dialog>` headed `Layout settings`, with the line `Your choices are saved in this browser only.`
    - Four fieldsets with the legends and options of 003/21: `Colour mode`, `Page width`, `Sidebar size`, `Sidebar colour`. `Reset to default` and `Close` buttons.
    - Present once on shell pages and absent on login.
    - Changing a radio applies immediately and saves `tmd-layout`, a JSON object with exactly the keys `theme`, `width`, `navSize` and `navTone`.
    - `Reset to default` removes the key and returns to criterion 1's values: light, full, standard, purple (amends 003/23).
    - `Escape` and `Close` return focus to the opener.
13. **"Icons only" sync (003 review nit).** Choose `Compact` in the panel, close it, then collapse the sidebar with the menu toggle. Reopening the panel shows `Compact` checked (the saved size, not the page-only collapse). Choosing `Icons only` then applies and saves `navSize: "icons"`, so a reload shows the icons size. The menu toggle alone never writes `tmd-layout`.
14. **Phone drawer (003/18 carried over).** At 400×844 the sidebar is off-screen.
    - **With JS:** the toggle opens it as a drawer with a scrim, and the rest of the page is `inert`. `Escape`, the scrim and `Close the menu` close it and return focus to the toggle.
    - **With JS off:** the `Menu` link opens it through `:target`, and every nav destination is reachable.
15. **Messages.** A Django message added before rendering a shell page appears once, in the flash component, **in the page flow directly under the title row inside `<main>`**, not as a floating box (D16), with `role="status"`. For the `error` level it uses `role="alert"`. Its text is escaped, and its close button (JS) dismisses it. This is a pytest check using `messages.success` in a test view or through the message storage on the request.

**Sign-in page (brief 001 kept)**

16. Every test in `apps/accounts/tests.py` passes **unchanged**. This covers:
    - the `Sign in · {SITE_NAME}` title;
    - `id="login-error"` with `role="alert"`, `hidden` before any attempt and visible after a wrong password, with the text `We couldn&rsquo;t sign you in`;
    - `aria-describedby` exactly `username-help` / `password-help` before an attempt and `login-error <id>-help` after one;
    - `aria-invalid`;
    - the kept username value;
    - the CSRF field;
    - POST-only logout.
17. The page uses f-desk's split sign-in: the form column and the purple brand panel with the crest (`img/crest.png`, `alt="Polymath College crest"`) and `Vivere Disce ~ Learn to Live`. It has the colour-mode button (hidden without JS). It has no sidebar, top bar, settings dialog or footer, and exactly one `<h1>` (`Welcome back`).
18. **Sign-in form column matches the concept (amended by D18); the empty-field check is kept.**
    - **The form column is `design/f-desk/login.html`'s:**
      - the username help `The name the school gave you, like nimali.p` (`id="username-help"`);
      - the password help `Passwords are case sensitive.` (`id="password-help"`);
      - a full-width password field.

      There is **no** Show/Hide button (no `data-toggle-password`), and **no** "Forgot your password, or new here? …" line. The ids, `aria-*` wiring and alert of criterion 16 are unchanged.
    - *Why this was amended:* the earlier wording required keeping the Show/Hide button and brief 001's help text. That preserved brief 001's **visible copy** over the client-approved concept, but brief 001 only fixed non-visual behaviour (title, error wiring, admin link). The owner corrected it: "login page design is different than the concept", resolved as "Match the concept exactly".
    - **Empty-field check:** on submit with an empty box, the page shows `Please fill in both boxes` / `Type your username and password, then press Sign in.` in `#login-error` and focuses the first empty field. It now also sets `aria-invalid="true"` and `aria-describedby="login-error <id>-help"` on the empty field(s), which closes the gap brief 001 left out of scope.

**Home page**

19. As a signed-in user, home shows, inside a card, a heading `Hello, {first_name, or username if that is empty}` and `{SITE_NAME} is set up and running. Screens will be added here as requirements come in.` It shows no invented figures, requests, devices, chart or notifications. `test_home_title_and_body_use_site_name` passes unchanged.
20. **Admin stays staff-only (brief 001 kept).** A non-staff user's home page contains no link to `admin:index` and no link whose text is `Admin`. Staff and superusers see exactly one `Admin` link, in the sidebar. The sign-out form is present for both.

**Templates, partials, DRY**

21. Every file under `templates/` starts with a `{# … #}` comment on line 1, naming its purpose and the context variables or `with` parameters it expects. The existing parametrized test is widened to every template (`rglob`).
22. Every `{% include %}` in `templates/` ends with `only`. There are no `style="…"` attributes in `templates/`. Every URL is `{% url %}`. Checked by pytest over the template sources.
23. **One sprite.**
    - `templates/partials/icons.html` holds the only `<symbol>` elements in `templates/`.
    - It is included once, by `base.html`, and appears exactly once in the rendered login and home pages.
    - Every `<use href="#i-…">` in any template names a symbol defined there, and every symbol is used by at least one template. The sprite carries only what the app uses. Brief 005 adds more from `design/f-desk/`.
    - Paths are Feather's (MIT). No other `<svg>` path data remains in templates: the Solar icons inlined in `login.html` are gone.
24. `test_every_static_reference_in_templates_exists` passes, and `theme-init.js` is covered by it.

**CSS rules for the port**

25. **Tokens.**
    - Every colour literal in `style.css` (hex, `rgb(`, `hsl(`) sits inside the palette block in `:root`. The dark-mode block and the three `[data-nav-tone]` blocks only map tokens to `var(--…)`.
    - No custom-property name encodes its value: none matches `px`, `rem`, or a digits-dash-digits size such as `--fs-10-5`. Numeric steps on a colour scale (`--crest-600`) are allowed.
    - Checked by pytest over `static/css/style.css`.
26. **Type in `rem`.**
    - No `font-size` in `style.css` uses `px`, and the root font size is never set in `px`.
    - At the default 16px root, the computed sizes on home and login equal f.md §8 within ±0.5px: body 14px, sidebar item 14.4px, h1 18px, card title 15.4px, group title 12px. Status tags are left out of this check until brief 005 (D14): no tag renders on home or login, and criterion 28 forbids porting unused rules.
    - With the browser's default font size raised (the verifier sets Chromium's `webkit.webprefs.default_font_size` to 20, or equivalent), body text computes to 17.5px (±0.5).
27. **One visually-hidden utility.**
    - The utility is `.visually-hidden`, used for always-hidden text.
    - The declaration set (the 1px box and the clip) is written once for it.
    - Any width-scoped hiding (at most two media contexts) is a single grouped selector list per media query, commented as the scoped form of the utility.
    - `style.css` contains at most three occurrences of the clip declaration. The reviewer checks this.
28. `style.css` keeps 003/29's section order (tokens, base, icons, shell, components, layout-setting variants, page-specific, responsive, reduced motion and print). Every rule in it is used by at least one template or by `app.js`. The reviewer spot-checks for dead prototype rules.

**Responsive and accessibility**

29. No horizontal scroll (`scrollWidth ≤ clientWidth`) and no clipped or overlapping text on login and home. Checked:
    - at 320×640 (new, WCAG 1.4.10), 400×844, 1024×768 and 1440×900;
    - in both modes;
    - for home, with each sidebar size.
30. At 400×844 and 1440×900, every link, button and summary on both pages is at least 44×44px. Breadcrumb links are exempt, as in 003.
31. **Contrast (003/20 carried over).** AA in both modes and on all three sidebar tones, with the port's token values recomputed by the verifier: text 4.5:1, non-text 3:1. This includes criterion 7's marker. Status is always an icon plus a word, and reduced motion is respected.
32. **JS off.**
    - Both pages render in full, in light mode, with the purple sidebar.
    - The user menu, the notifications bell and the phone search panel open, sign-out works, sign-in submits, and the `Menu` link opens the sidebar.
    - Every JS-only control carries `hidden`: menu toggle, colour-mode buttons, `Layout settings` openers, flash close. There is no password show/hide button (D18).
    - No console errors with JS on.

**Top-bar placeholders (owner's Q1 answer, D12)**

These are numbered 37 and 38 so that the other criteria keep their numbers. They belong with criterion 8.

37. **Search placeholder: visible, honest, never submits.**
    - At ≥992px the top bar shows f-desk's search field at 304×44px. **There is no search button** while search is a placeholder (owner: "Remove button for now", D15). The search icon sits at the **start** of the field, decorative and `aria-hidden`. This is a deliberate difference from the client-approved screenshot, and the purple button returns in brief 005. Below 992px it collapses to f-desk's search icon button, which opens the same field in a `<details data-pop>` panel. That is the prototype's pattern, and it works without JS.
    - **It is not a form.** There is no `<form>` around it, and no `action`, `name` or submit button, so nothing can submit it and pressing Enter does nothing. The rendered home page contains no `<form>` other than the sign-out form, which pytest checks.
    - The field is `<input type="search" id="top-search" readonly aria-disabled="true">` with:
      - a visually hidden `<label for="top-search">Search</label>`;
      - the placeholder `Search is coming soon`;
      - `aria-describedby="top-search-note"`, pointing at a visually hidden `<span id="top-search-note">Search is coming soon.</span>`.
    - The string `Search arrives with the first section` appears nowhere in `templates/`, which pytest checks (D17).

      It stays focusable, so keyboard and screen-reader users hear why it does nothing. It is not `disabled`, because a disabled field is skipped and never explained.
    - Visually the field reads as unavailable but still legible. The placeholder text reaches ≥4.5:1 against the field background in both modes and on the phone panel, because here it carries the message and is not decoration. The cursor is `not-allowed`. Any focus ring meets 003/20.
    - The field is identical with JS on and off, because no script is involved.
38. **Notifications bell: present, no count, says there are none.**
    - A `<details data-pop>` whose summary is the bell icon with the accessible name `Notifications, none yet`. It has **no** count badge or dot.
    - The panel has the heading line `Notifications`, then `No notifications yet.`. It has no list items, no footer link and no other links.
    - It opens with JS off. With JS on, `Escape` and a click outside close it and return focus to its summary, as 003/13 describes.
    - Its target is at least 44×44px at 400 and at 1440.

**Model**

33. `User.initials` returns the upper-cased first letters of `first_name` and `last_name` when both are set (`Nimali Perera` → `NP`). When only one is set, it returns that name's first letter. When neither is set, it returns the first letter of `username`. It never returns an empty string for a saved user. It is unit-tested, and `makemigrations --check` shows no migration.

**Verification (CLAUDE.md "Verify a change", all five)**

34. `ruff check .`, `ruff format --check .`, `pytest --create-db`, `makemigrations --check --dry-run` and `manage.py check` all pass. `check --deploy` is not needed, because settings are unchanged.
35. **Prod stack.** `docker compose up -d --build`, then wait for `web` to be `healthy`. Over HTTP on port 8010:
    - `GET` login returns 200.
    - A wrong password re-renders with the error.
    - A real sign-in lands on home (200) for a staff user and for a non-staff user.
    - `theme-init.js`, `style.css`, `app.js` and every image are served from hashed WhiteNoise paths (200).
    - Sign-out by POST lands on login.
    - The browser network log shows only the app's origin, `fonts.googleapis.com` and `fonts.gstatic.com`.
    - Afterwards the verifier restores whichever stack was running before.
36. **Screenshots** (in the verifier's scratchpad; attach the paths, do not commit): sign-in and home at 1440×900 and 400×844, in light and dark (8 files). Also `home--first-visit.png` at 1440×900 with empty storage and the device set to dark, showing the light page and the purple sidebar. Also `home--drawer-open.png` at 400×844, `home--notifications-open.png` at 1440×900, `home--search-focused.png` at 1440×900 (the placeholder field focused), and `home--320.png` / `login--320.png`. All are captured with fonts loaded. The verifier states that home's purple sidebar matches `design/f-desk/screenshots/desktop-dashboard--nav-purple.png` in shell geometry (sidebar, top bar and title row within ±2px). The removed search button and the search icon's new position are excluded from that comparison, because they are the recorded deliberate difference (D15).

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

None open. The owner answered the planner's Q1 and Q2, which are now D12 and D13.

- **D12: The search field and notifications bell stay in the top bar, as honest placeholders** (owner's answer to Q1, verbatim in substance: keep them visually to match what the client approved; they must not be dead or misleading; they are wired up in brief 005).
  - **Search.** Of the two options the owner offered, the planner chose the **non-submitting, focusable, `aria-disabled` field with a plain note** (criterion 37). It is not a form with no action, for three reasons:
    - a form with no action submits to the current page with `?q=…` and then silently ignores it, which is exactly the misleading behaviour the owner ruled out;
    - showing a "nothing to search yet" state after submitting would need view code for a feature that doesn't exist;
    - a `disabled` field would be skipped by the keyboard and never explained.

    The note `Search is coming soon` is the only new copy (owner's wording, D17).
  - **Bell.** No badge. The accessible name is `Notifications, none yet`, and the panel reads `No notifications yet.` (criterion 38).
  - **Brief 005** turns the field into a real `<form method="get">` to its list view, and gives the bell real content, or else records why not.
- **D13: The sidebar help card stays out** (owner's answer to Q2; the planner's default stands). It returns when a "raise a request" route exists, probably in 005.

**Rulings on the designer's four open points (Design section → points 1–4)**

- **D14: Tags are out of the size check until 005** (main-session ruling on point 1). No tag renders on home or login, and criterion 28 forbids porting the unused `.tag` rules. So criterion 26 no longer measures tags. Brief 005 ports `.tag` and checks it at 10.5px (f.md §8, D9).
- **D15: No search button while search is a placeholder** (owner, verbatim: *"Remove button for now"*, on point 2).
  - The purple search button is removed, and the search icon moves to the start of the field.
  - This is a **deliberate difference from the client-approved screenshot**. The reviewer should list it in "What the client will notice", and the fidelity comparison in criterion 36 excludes that button.
  - The button returns in brief 005, when the field becomes a real form.
- **D16: Flash messages sit in the page flow, under the title row** (main-session ruling on point 3, accepting the designer's reasoning). They are not a floating, fixed toast, because an in-flow message works with JS off and on phones without covering content or the drawer. This deviates from f-desk's toast, and 005's "request sent" confirmation inherits it.
- **D17: The search note reads `Search is coming soon`** (owner, verbatim, on point 4). It replaces `Search arrives with the first section` everywhere: D12, criterion 37, and the placeholder, the visually hidden note and the content. The designer updates the Design section and `docs/design/placeholder-controls.md` to match.

**Owner correction on sign-in**

- **D18: The sign-in form column matches the concept exactly** (owner, verbatim: *"login page design is different than the concept"*; resolved as *"Match the concept exactly"*).
  - `registration/login.html`'s form column follows `design/f-desk/login.html`:
    - the concept's help texts (`The name the school gave you, like nimali.p`; `Passwords are case sensitive.`);
    - a full-width password field with **no** Show/Hide button;
    - **no** "Forgot your password, or new here? Ask the office to set up or reset your account." line.
  - This **supersedes** the parts of D8, criterion 18 and the step-1 designer bullet that said to keep brief 001's visible copy and the Show/Hide button.
  - **Why the earlier wording was wrong:** it treated the app's pre-theme sign-in copy as something brief 001 protected. Brief 001 fixed only non-visual behaviour: the `tmd_site_name` title, the `login-error` / `aria-describedby` / `aria-invalid` wiring, and the staff-only admin link. So preserving the old visible copy over the client-approved concept was not required, and it contradicted the owner's instruction to make f-desk the theme.
  - **What stays** (brief 001's non-visible behaviours and pinned strings):
    - every criterion-16 item, including `id="login-error"`, `role="alert"`, the `hidden` toggle, the error-first `aria-describedby` order, the kept username and the `We couldn&rsquo;t sign you in` alert text;
    - the JS empty-field check (criterion 18's second bullet).
  - **Follow-ups for other owners:**
    - `docs/design/password-field.md` and the Design section's show/hide rows no longer describe the app. The designer marks them superseded.
    - `tmd-docs-writer` records the correction in `docs/CHANGELOG.md`.
    - Status stays **Done**.
  - **Deliberate, owner-approved differences from the concept.** These are kept on purpose and are not defects.
    - **Three remaining sign-in differences, kept** (owner, verbatim: *"Keep them (Recommended)"*):
      - the curly apostrophe in the error title (`We couldn&rsquo;t sign you in`, as criterion 16 pins it);
      - focus goes to the password box after a wrong password, not to the error notice;
      - the username box gets autofocus on first load.
    - **The empty-field check, kept** (owner, verbatim: *"Keep it (Recommended)"*): `Please fill in both boxes` / `Type your username and password, then press Sign in.` (criterion 18, second bullet), which the concept doesn't show.

**Decisions** (the planner's, recorded so later briefs don't reopen them):

- **D1: The prototype is frozen, and f.md is the spec.** `design/f-desk/` and f.md stay as the approved reference. The app is not a copy of the prototype folder: values come from f.md, and structure follows CLAUDE.md. The prototype's screenshots predate the light/purple default, and they are not recaptured, because the app's criteria (3, 12, 36) now carry what 003/19, 003/23, 003/24, 003/25, 003/27 and 003/29 required. `tmd-docs-writer` notes in `design/README.md` that `f-desk/` is a record and the app is the living theme.
- **D2: Approved defaults, light only on first visit.** `light` / `full` / `standard` / `purple`. There is no `prefers-color-scheme` following (this reverses 003's D6 and D10, per the owner's "make it a light version"). Dark mode stays available through the button and the panel, and a saved choice is kept.
- **D3: The settings panel ships in the app with all four settings,** exactly as approved. It is JS-only and is described as such in the Needs-JS list.
- **D4: Icons: Feather replaces Solar Bold Duotone app-wide** (this settles 003's D4 for the app). One sprite partial holds only the symbols in use. The MIT notice goes in the partial's header comment and in `README.md`. CLAUDE.md's Icons bullet and the "`login.html` still inlines its icons" note are updated by `tmd-docs-writer`.
- **D5: No in-app design-kit page.** The kit stays in `design/f-desk/ui-kit.html`. Reasons:
  - Less code: a staff-only kit page would add a view, a URL, a permission and a template full of specimen data.
  - Nobody on staff needs it to do their work.
  - Its specimens are made-up content, which the app must not show.

  The cost is that the kit can drift from `static/css/style.css`. That is accepted, because f.md stays the spec and each feature brief verifies its own components.
- **D6: Navigation shows only real destinations, and grows by editing one partial.**
  - Today: `Menu` → `Home`, plus `Administration` → `Admin` for staff.
  - The active item is set from `request.resolver_match.view_name`, passed into `partials/sidebar.html` as `current`. A group's `<details>` parent is set `open` when `request.resolver_match.namespace` equals that group's namespace, passed as `current_ns`.
  - **How 005 extends it:** add its group and items to `partials/sidebar.html` (with `{% url %}` names), and, if needed, one symbol to `partials/icons.html`. Nothing else in the shell changes, and there is no context processor and no nav registry. That is less code at this size. Revisit when there are more than about 4 sections.
- **D7: Sign-out lives in the user menu only.** It is a POST form, and the `<details>` menu works without JS. Home no longer carries its own sign-out button, so one concept lives in one place. The two tests that pinned the old markup are updated (see MVT plan).
- **D8: The sign-in page keeps the app's own copy and behaviours.** *Partly superseded by D18:* the help text, show/hide and the forgot line now follow the concept. The following still stand: the `We couldn&rsquo;t sign you in` alert (criterion 16 pins it), the empty-field check, and `id="login-error"` (the prototype's `signin-error` is not used). Originally it read: "That covers the help text, the `We couldn&rsquo;t sign you in` alert, password show/hide and the empty-field check, re-dressed in f-desk. Where the prototype's contract copy differs, the app's live copy wins."
- **D9: Messages via Django's framework.** There is one `partials/messages.html` in the flash style, and no JS toast API. This replaces the old `#toasts` container, the `window.showToast` API and `icon_templates.html`, all of which are deleted.
- **D10: `User.initials` is a model property.** The fallback order is a rule, so under CLAUDE.md it belongs on the model, not in a template filter chain. 005 reuses it for "who is on it". There is no migration. The avatar's display name uses Django's own `get_full_name`, with `default:user.username` in the template.
- **D11: The home view is unchanged** (`login_required` function view). The port changes no route or context, so converting it to a generic CBV now would be churn with no benefit. 005's views will be CBVs.

## MVT plan
<!-- owner: tmd-planner -->

### Models

- `apps/accounts/models.py` → `User`: add the read-only property `initials` (criterion 33), with a docstring saying why it lives on the model. No fields change, and there is no migration.

### URLs and views

No new or changed routes. These are the routes the shell links to:

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `accounts:login` | existing | `LoginView` (`redirect_authenticated_user=True`), unchanged | `registration/login.html` | Anonymous |
| `accounts:logout` | existing | `LogoutView`, POST only, unchanged | — | Signed in |
| `core:home` | existing | `apps.core.views.home`, unchanged | `core/home.html` | `login_required` |
| `admin:index` | existing | Django admin | Django's | `is_staff` (link shown only to staff) |

**Information architecture** (from `ux-strategy:information-architecture`):

```
Sign in                                   (no shell)
└── Home                                  [Menu]            ← only destination for everyone today
    ├── Admin                             [Administration]  staff only; Django admin, own look
    └── Utility (top bar)
        ├── Search                        placeholder, no destination yet (D12)
        ├── Colour mode                   (JS)
        ├── Notifications ▾               "No notifications yet." (D12)
        ├── Layout settings               (dialog, JS)
        └── {initials} {name} ▾  → Layout settings · Sign out (POST)
Brief 005 adds:  [<its group>] → <its list> / <its form>; wires search → its list; the help card returns (D13)
```

Wayfinding: the active sidebar item, the breadcrumb's current item and the `<h1>` must agree on every shell page. Utility navigation holds nothing that exists only there, except `Sign out` and the settings. The search field and the bell have no destination yet and say so (D12).

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Everywhere (existing context processors):**

| Variable | Type | Source |
|---|---|---|
| `tmd_site_name` | `str` | `apps.core.context_processors.site` |
| `user` | `User` / `AnonymousUser` | auth context processor. `user.initials` is new (`str`), `user.get_full_name()` is Django's, and `user.username` and `user.is_staff` are existing. |
| `request` | `HttpRequest` | request context processor. Only `request.resolver_match.view_name` / `.namespace` are read, and only in `base.html` to pass into the sidebar. |
| `messages` | message storage | messages context processor. Each message has `.message`, `.level_tag` and `.tags`. |
| `csrf_token` | token | CSRF. It must be passed explicitly into any `only` include that contains a POST form. |

**`templates/base.html`.** The document: `<html>` attributes (criterion 1), the head order (criterion 2), the skip link, and the sprite include.

- **Blocks:**
  - `title` (required on every page);
  - `head`;
  - `body`, whose **default content is the shell**. Login overrides `body` to drop the shell. The page chrome therefore stays defined only in `base.html`.
  - Inside the shell: `heading` (the `<h1>` text), `breadcrumb` (extra `<li>`s after `Home`; empty on home), and `content`;
  - `scripts`.
- **Includes, with exact parameters:**

| Partial | `with … only` parameters | Notes |
|---|---|---|
| `partials/icons.html` | none | The Feather sprite (criterion 23). The header comment carries the MIT notice. |
| `partials/sidebar.html` | `current` (str, view name or `""`), `current_ns` (str or `""`), `user` | Nav per D6; the no-JS close link `Close the menu`. |
| `partials/topbar.html` | `user`, `csrf_token` | Includes `partials/top_search.html`, `partials/colour_mode_button.html`, `partials/notifications.html` and `partials/user_menu.html`. |
| `partials/top_search.html` | none | The search placeholder (criterion 37). There is no form. 005 replaces it with a real form and passes its URL name. |
| `partials/notifications.html` | none | The bell with no badge and the empty panel (criterion 38). 005 passes it real items. |
| `partials/user_menu.html` | `user`, `csrf_token` | `<details>`, the sign-out POST form. |
| `partials/colour_mode_button.html` | none | Also used by login (DRY). |
| `partials/messages.html` | `messages` | Flash per criterion 15. It renders nothing when empty. |
| `partials/footer.html` | none | Uses `{% now "Y" %}`. |
| `partials/settings_dialog.html` | none | Criterion 12. |
| `partials/icon.html` (optional, the builder decides) | `name` (str), `size` (str, optional) | One `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-{{ name }}"></use></svg>`, if it removes enough repetition. |

**`templates/registration/login.html`:** `form` (`AuthenticationForm`), `next` (str), and `tmd_site_name`. It overrides `body` and includes `partials/colour_mode_button.html`. It ignores LoginView's `site` / `site_name` (existing guard test).

**`templates/core/home.html`:** `user` and `tmd_site_name`. It fills `title` = `Home`, `heading` = `Home`, an empty `breadcrumb`, and a `content` card (criterion 19).

**Settings contract** (003's, with new defaults):

- `<html data-theme data-width data-nav-size data-nav-tone>`;
- `localStorage` key `tmd-layout`, holding exactly four keys;
- defaults per criterion 1;
- only `theme-init.js` sets the attributes before first paint, and only `app.js` changes them afterwards;
- CSS switches token blocks by attribute selector.

**JS hooks** (003's `data-*` vocabulary carried over):

- the prototype's hooks: `data-nav`, `data-nav-toggle`, `data-nav-toggle-label`, `data-nav-link`, `data-nav-close`, `data-scrim`, `data-drawer-inert`, `data-pop`, `data-theme-toggle`, `data-theme-label`, `data-settings`, `data-settings-open`, `data-settings-close`, `data-settings-reset`, `data-setting`, `data-flash`, `data-flash-close`;
- the existing sign-in hooks: `data-login-form`, and `data-field` if still needed. `data-toggle-password` is removed (D18).

JS never binds to classes or tags.

### Placement and reuse

- **All front-end work** is in the project-level `templates/` and `static/`, as today. No new app.
- **`apps/accounts`:** `User.initials` only.
- **Reused:**
  - f.md's tokens, geometry and type scale;
  - `design/f-desk/style.css`'s rules, ported and renamed, for the pieces in scope;
  - `design/f-desk/app.js` blocks 1–8;
  - `design/f-desk/theme-init.js`;
  - the crest images already in `static/img/`;
  - Django's `messages`, `LogoutView`, `LoginView` and `get_full_name`.
- **Not built:** a nav registry or context processor (D6), a JS toast API (D9), a design-kit view (D5).

**Tests deliberately updated** (the verifier owns them):

- `apps/core/tests.py::test_home_shows_sign_out_button_that_posts_to_logout`. It now looks for the POST form to `accounts:logout` anywhere on the page, and matches the button by its text content with tags stripped, because the button now carries an icon.
- `apps/core/tests.py::_admin_links` / `test_home_shows_admin_link_to_staff` / `test_home_shows_admin_link_to_superuser`. These now match `<a href="{admin}">` by text content with tags stripped, so `Admin` inside a `<span>` beside an icon counts. The non-staff test still finds none, and the staff tests expect exactly one.
- `apps/core/tests.py::test_template_starts_with_purpose_comment`. It is parametrized over every template under `templates/` (criterion 21).

**Tests kept unchanged:** everything in `apps/accounts/tests.py`, plus `test_every_static_reference_in_templates_exists`, `test_healthz_ignores_host_header`, `test_home_requires_login`, `test_home_renders_for_signed_in_user`, the site-name and title tests, and `test_no_template_reads_the_colliding_site_name_variable`.

**New tests:** criteria 1, 2, 6 (nav `href`s resolve by name, `aria-current`, staff-only group), 9 (sign-out form, no GET logout link), 12 (dialog present on home and absent on login), 15, 17, 21, 22, 23, 25, 26's `px` guard, 33, 37's markup (no `<form>` other than sign-out; `readonly`, `aria-disabled`, label, `aria-describedby` target exists) and 38's markup (accessible name, no badge, the empty text, no links in the panel). The browser-only criteria (3, 4, 7, 13, 14, 18, 26 rendering, 29–32, 35, 36, 37's contrast and focus, 38's `Escape`/outside click) are checked with Playwright from the scratchpad, as in 003, and are not added to the repo.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

**Step 1 — `tmd-ui-designer`** (a short Design section in this brief; no HTML/CSS/JS, and f.md is untouched unless a value is wrong). It fills in:

- the component map, from prototype pieces to the app's partials and classes, marking what is ported now and what waits for 005;
- the home placeholder layout: one card, with its title and body per criterion 19;
- the sidebar content per D6;
- the placeholder treatment for the search field (the unavailable-but-legible look, placeholder contrast, focus, the phone panel) and the empty notifications panel (criteria 37 and 38, D12);
- the **active-marker colour on the purple tone**, with ratios (criterion 7);
- the old-token → role-named-token rename table (criterion 25) and the `rem` values for f.md §8's sizes (criterion 26);
- the visually-hidden plan (criterion 27);
- the sign-in re-dress. *Amended by D18:* the form column matches `design/f-desk/login.html` exactly, with no show/hide. It originally read "keeping the app's copy (D8), and where show/hide sits";
- the flash component for `messages`;
- the Needs-JS list for the app.

Skills: `design-systems:design-token`, `design-systems:naming-convention`, `ui-design:typography-scale`, `inclusive-interaction:keyboard-navigation`, `adaptive-interfaces:flexible-typography`.

**Step 2 — in parallel, once step 1 is in:**

- **2a `tmd-frontend`** owns `templates/**` and `static/css/style.css`, `static/js/theme-init.js` and `static/js/app.js`. It:
  - builds everything in Scope;
  - deletes `templates/partials/icon_templates.html`;
  - self-checks criteria 1, 2, 16, 21–25, 32, 37 and 38, and renders both pages in both modes;
  - writes its Implementation notes.

  Suggested skills: `inclusive-interaction:keyboard-navigation`, `ui-design:dark-mode-design`, `design-systems:accessibility-audit`.
- **2b `tmd-django-backend`** owns `apps/accounts/models.py`. It adds `User.initials` with a docstring, confirms there is no migration, and writes its Implementation notes. This is a small step, and it is independent because the contract fixes the property name and behaviour.

**Step 3 — `tmd-test-verifier`.**

- Updates the three tests listed under "Tests deliberately updated" and adds the new pytest tests.
- Runs all five "Verify a change" checks, including the prod-stack HTTP check (criterion 35), and restores the previous stack afterwards.
- Runs the Playwright checks from the scratchpad: criteria 3, 4, 7, 13, 14, 18, 26, 29–32, 37 and 38.
- Captures the screenshots in criterion 36.
- A FAIL goes back to step 2 (a or b).

**Step 4 — `tmd-code-reviewer`** (read-only). It reviews:

- MVT and DRY: `only` includes, chrome only in `base.html`, one sprite, one source for the JS defaults (criterion 5);
- token discipline and naming (criteria 25, 27, 28), and dead-rule removal;
- the `data-*`-only binding;
- accessibility in both modes;
- fidelity of the purple-default shell to the approved screenshot.

Suggested skills: `visual-critique:critique-brand-consistency`, `design-systems:accessibility-audit`. CHANGES REQUESTED goes back to step 2, then step 3.

**Step 5 — `tmd-docs-writer`.**

- `CLAUDE.md`:
  - **Front end → Origin:** the app's CSS and JS now come from `design/f-desk/`, and `design/v5-tasks` is no longer the origin.
  - **Front end → JavaScript:** add `theme-init.js` and the settings contract.
  - **Front end → Icons:** Feather, one sprite partial `partials/icons.html`; remove the `login.html` duplication note.
  - **UI conventions → tokens:** say the f-desk tokens in `:root` are the app's tokens, and remove the "provisional until a design direction is chosen" wording and the task-002 caveat.
- `README.md`: third-party notices (IBM Plex Sans, SIL OFL 1.1; Feather, MIT).
- `design/README.md`: `f-desk/` is now a frozen record (D1).
- `docs/CHANGELOG.md` entry.
- Closes this brief.

`tmd-devops` is not used: there is no settings, env, Docker or dependency change.

**Order:** 1 → (2a ∥ 2b) → 3 → 4 → 5.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

**Sources.** Every value comes from `docs/design/directions/f.md` (f.md) and `design/f-desk/` in its approved configuration (light, purple sidebar, standard, full width). Where this section is silent, f.md and the prototype govern. This section records only where the app **differs** from f-desk, plus the port rules. Two app-specific pieces are specified once in `docs/design/`: `placeholder-controls.md` (search placeholder and empty bell) and `flash-messages.md`. `password-field.md` is superseded (D-7).

### D-1. Port rules

**1a. Type in `rem`.** The root stays at the browser default (never set `html { font-size }` in px; leave it unset). Every `font-size` is f.md's px value ÷ 16. Every line height becomes **unitless** (f.md's px line heights are all 1.5×, 1.2× or 1× their font size), so lines grow with the text. At the default 16px root, everything renders identically to f-desk. Everything else stays in px: shell geometry (250/160/70px sidebar, 70px top bar), spacing, borders, radii, icons and the 44px targets. That keeps the approved geometry exact (criteria 6, 8 and 36). There is one exception: `--search-w` becomes `19rem` (304px at default), because the field has to hold a one-line placeholder that must not clip (criterion 37). Where a text box must grow, use `min-height`, never `height`.

**1b. Role-named tokens (criterion 25).** Only the tokens the app uses are ported. The rest arrive with 005, and the names to use then are given here.

| f-desk token | App token | Value | Used by (now) |
|---|---|---|---|
| `--fs-12` | `--fs-caption` | `0.75rem` | sidebar group titles |
| `--fs-13` | `--fs-help` | `0.8125rem` | `.field__help` |
| `--fs-14` | `--fs-body` | `0.875rem` | body, buttons, crumbs, footer, pop items, inputs |
| `--fs-14-4` | `--fs-nav` | `0.9rem` | sidebar items, wordmark |
| `--fs-15-4` | `--fs-card-title` | `0.9625rem` | `.box__title` |
| `--fs-17-5` | `--fs-title` | `1.09375rem` | sign-in h1, settings title, phone motto |
| `--fs-18` | `--fs-page-title` | `1.125rem` | shell h1 |
| `--fs-21` | `--fs-motto` | `1.3125rem` | sign-in motto |
| `--fs-10-5` / `--fs-12-25` / `--fs-13-6` / `--fs-20-4` / `--fs-21` (stat) | 005: `--fs-tag`, `--fs-error`, `--fs-nav-child`, `--fs-stat-phone`, `--fs-stat` | `0.65625` / `0.765625` / `0.85` / `1.275` / `1.3125rem` | not ported |
| `--fs-16`, `--fs-chart-*` | dropped | | |
| `--lh-16-8`, `--lh-18-48`, `--lh-21-6`, `--lh-25-2`, `--lh-tight` | `--lh-tight` | `1.2` | headings, legends, pop head, wordmark |
| `--lh-18`, `--lh-18-4`, `--lh-19-5`, `--lh-20-4`, `--lh-21` | `--lh-body` | `1.5` | everything else (12.25px error: 18.375 vs 18.4, −0.03px) |
| `--lh-1` | `--lh-flat` | `1` | 005 (tags) |
| `--space-10px` | `--nav-item-gap` and `--nav-list-top` | `10px` | icon–label gap in a nav row; first group's top offset |
| `--space-52px` | retired; `--search-pad-start` | `36px` | search placeholder (icon moves to the start, see D-4) |
| `--space-32px` | `--fieldset-gap` and `--signin-band-pad` | `32px` | settings fieldsets; phone sign-in band |
| `--space-5px` | `--flyout-pad-y` | `5px` | icons-size flyout |
| `--space-2px` / `-3px` / `-6px` / `-28px` / `-36px` / `-40px` | 005: `--tag-pad-y`, `--error-gap`, `--history-indent`, `--select-pad-end`, … | | not ported |
| `--rule-2` | `--focus-width` (outlines and offsets) and `--rule-strong` (the invalid-input border) | `2px` | |
| `--icon-12` … `--icon-28` | `--icon-xs` 12, `--icon-sm` 14, `--icon-md` 16, `--icon-lg` 18, `--icon-xl` 20, `--icon-2xl` 24, `--icon-3xl` 28 (the `.icon--20` modifiers become `.icon--xl` etc.) | px | |
| `.offscreen` (class) | `.visually-hidden` | | |

Colour scale steps (`--grey-850`, `--crest-600` and so on) stay, as criterion 25 allows. The dark block has one selector, `:root[data-theme="dark"]`. The `prefers-color-scheme` copy is removed (D2), which also removes 003's duplicated 56-line mapping.

**1c. Visually hidden (criterion 27).** `.visually-hidden` is written once in section 2 (base). There are two scoped forms, each a single grouped selector list with the comment `/* .visually-hidden, scoped to <width> */`:
- `@media (min-width: 992px)`: the compact and icons-size wordmark, group titles and item labels.
- `@media (max-width: 991.98px)`: `.whoami__name` and the whoami chevron.

f-desk's `<768px` table-head copy is not ported. That makes three clip declarations in total.

### D-2. Active marker on the purple sidebar (criterion 7)

The recorded colour is **white `#FFFFFF`** (`--white`, through `--tone-purple-bar` → `--nav-active-bar`). The active row background is `--tone-purple-active-bg` = `--crest-700` `#5C1F6A`. The active text is `--tone-purple-active` = white. WCAG 2.x ratios, truncated:

| Pair | Ratio | Needs |
|---|---|---|
| Bar `#FFFFFF` on sidebar `--nav-bg` `#722A82` | **8.86:1** | ≥3 |
| Bar `#FFFFFF` on active row `#5C1F6A` | **11.29:1** | ≥3 |
| Active text `#FFFFFF` on active row `#5C1F6A` | **11.29:1** | ≥4.5 |

(Luminance: `#722A82` 0.0685, `#5C1F6A` 0.0430, white 1.) Idle items stay `#D5BFDA` (5.19:1), so "current" is shown by the bar, the row shade and brighter text together, never by colour alone. The other tones keep f.md §9.4 (light tone bar `#722A82` on `#FCFAFD` 8.54:1; dark tones `#CFA3DA` 6.31:1).

### D-3. Sidebar (`partials/sidebar.html`)

```
┌─────────────────────────┐
│ [crest] Technology      │  ← one <a> to core:home (crest alt="", name = wordmark)
│         Management Desk │
│ ✕ Close the menu        │  ← phone only, href="#main", outside <nav>
│ Menu                    │  ← <p class="sidenav__group-title" id="nav-menu">
│▌⌂ Home                  │  ← aria-current="page" on core:home
│ Administration          │  ← staff only (user.is_staff)
│  ⛉ Admin                │  ← admin:index, icon `shield`
│                         │  (no help card, D13)
└─────────────────────────┘
```

- The markup is f-desk's (`.sidenav`, `__brand`, `__close`, `__group-title`, `__list`, `__link`, `__icon`, `__label`). The brand `<div>` becomes `<a class="sidenav__brand" href="{% url 'core:home' %}">`. It carries the only focus ring in the brand row: `--nav-focus`, inset.
- Group ids are `nav-menu` and `nav-admin`.
- **How 005 slots in:** insert its group **between** `Menu` and `Administration`, which always stays last. Use `<p class="sidenav__group-title" id="nav-<ns>">` plus a `<ul aria-labelledby>`. If it has more than one page, use f-desk's `<details class="sidenav__parent"{% if current_ns == '<ns>' %} open{% endif %}>`, with the chevron and children. The help card returns after `</nav>` (D13). 005 adds `chevron-right` and its item icon to the sprite, and ports the `__parent` / `__children` / flyout rules.

### D-4. Top bar (`partials/topbar.html`)

Desktop (≥992px), differences from f-desk marked `*`:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│[≡]  ┆⌕ Search is coming soon              ┆*   [☾] [🔔]* [⚙] ┃(NP) Nimali Perera ▾┃*│
│ 52  └ 304×44, dashed border, no button ──────┘   52   52   52  ┃ name only, no role  ┃│
└──────────────────────────────────────────────────────────────────────────────┘
```

**Search placeholder (`partials/top_search.html`; criterion 37).**
- Keep f-desk's `<details class="pop topfind" data-pop>` wrapper, so the ≥992px field and the <992px icon panel stay one element with one `id`. Inside, drop the `<form>` and the submit button. What remains is the label, the input, a decorative icon and the note, exactly as in criterion 37.
- **Look:**
  - The search icon moves to the **start** of the field: 16px, `--c-muted`, 12px from the left, `aria-hidden`. The input has `padding-inline: var(--search-pad-start) 12px`.
  - No purple fill and no shadow. A purple square reads as a button, and there is nothing to press. This is a recorded deviation from the approved screenshot, and the reviewer should note it. The field's size and position are unchanged: 304×44 at the same x.
  - Border `1px dashed var(--c-control)`: f.md §7.5's read-only treatment (3.25:1 on `--c-surface-2`, 3.43:1 on the top bar).
  - Background `--c-surface-2`, placeholder `--c-muted` with `opacity: 1`, `cursor: not-allowed`. No hover change.
- **Placeholder contrast** (criterion 37): light `#636779` on `#F8F9FA` **5.32:1**; dark `#9CA3AD` on `#363A38` **4.53:1**. The phone panel uses the same field on the same token, so the same figures apply.
- **Focus:** the border turns `--c-focus` (staying dashed), plus the 2px `--c-focus` outline at 1px offset (8.86:1 light, 6.31:1 dark on the top bar).
- **Copy (D17):** the placeholder is `Search is coming soon`, and the visually hidden note `#top-search-note` is `Search is coming soon.` Everything else in criterion 37 stands.
- **Fit:** the placeholder is about 142px at 14px IBM Plex Sans. Desktop has 304 − 48 = 256px free. The phone panel at 320px wide has 230px free, once the rule below 360px (next list) is applied.
- **Phone summary:** the `search` icon with visually hidden `Search, not available yet`. The panel is f-desk's `.topfind__panel` (fixed, 12px from each side, under the top bar).

**Notifications (`partials/notifications.html`; criterion 38).**
- f-desk's `<details class="pop" data-pop>`, with the `.icon-button` summary: the bell plus visually hidden `Notifications, none yet`. No `.count`.
- Panel `.pop__panel` (320px): `<p class="pop__head">Notifications</p>`, then `<p class="pop__note">No notifications yet.</p>`. The note is 14px `--c-muted` (5.61:1 light, 5.26:1 dark), with padding `0 16px 16px`. There is no list, no `.pop__foot` and no link.

```
        ┌────────────────────────────┐
        │ Notifications              │
        │ No notifications yet.      │
        └────────────────────────────┘
```

**User menu (`partials/user_menu.html`; criterion 9).**
- Summary `.whoami`: `.initials` (`{{ user.initials }}`, `aria-hidden`), then `.whoami__name` with the visually hidden prefix `Your account: ` and the name `{{ user.get_full_name|default:user.username }}`, then `chevron-down`.
- **No role line.** The contract has no role, so the name is centred vertically in the 70px block.
- Panel `.pop__panel--menu`:
  1. The head (below 992px only, `aria-hidden`): initials and name.
  2. `Layout settings` (`<button class="pop__link" data-settings-open hidden>`, icon `sliders`).
  3. `.pop__rule`.
  4. `<form method="post" action="{% url 'accounts:logout' %}">`, then `{% csrf_token %}`, then `<button class="pop__link" type="submit">`, icon `log-out`, text `Sign out`.
- No `Design kit` item.

**Phone (<992px):** f-desk's layout, which puts the brand box first (`<a class="topbar__brand">` to `core:home`, visually hidden `Home`). **New rule below 360px, for the 320px check:**
- `.whoami` becomes 44px wide;
- the top bar's `padding-right` becomes 8px;
- `.topfind__panel` sits 8px from each side.

The widths then total 301px with JS (brand box 73, then toggle, search, colour mode, bell and avatar at 44 each) and 301px without JS (brand box 73, `Menu` link about 88, then search, bell and avatar at 44 each).

### D-5. Title row, footer, home

- **Title row:** f-desk `.titlebar`, `.page-heading`, `.crumbs`.
  - `base.html` renders the first crumb: `<span aria-current="page">Home</span>` when the view name is `core:home`, otherwise `<a href="{% url 'core:home' %}">Home</a>` followed by `{% block breadcrumb %}`.
  - Pages that add crumbs supply each `<li>` with its separator SVG. 005 adds `chevron-right` then.
- **Footer:** `partials/footer.html`, `.page-foot`: `<p>{% now "Y" %} © Polymath College</p><p>Technology Management Desk</p>`.
- **Home content:** one `.box` at full content width (no `.cards` grid):

```
Home                                                               Home
┌────────────────────────────────────────────────────────────────────────┐
│ Hello, Nimali                                               (.box__head)│  h2.box__title
├────────────────────────────────────────────────────────────────────────┤
│ Polymath TMD is set up and running. Screens will be added here as     │  p, --c-text
│ requirements come in.                                                  │
└────────────────────────────────────────────────────────────────────────┘
```

  The heading is `Hello, {{ user.first_name|default:user.username }}`. The body is `{{ tmd_site_name }} is set up and running. Screens will be added here as requirements come in.` There is no button, figure or icon. At 400px it is the same box at full width, under the stacked title row.

### D-6. Messages (`partials/messages.html`; criterion 15)

This is a deliberate deviation from f-desk's fixed toast, specified in `docs/design/flash-messages.md`. Messages sit **in the page flow**, directly under `.titlebar` inside `<main>`, in a `<div class="flashes">` (a column with a 12px gap and 24px margin below). Reasons:
- a fixed toast can't be dismissed without JS, and would cover content on phones;
- in the flow it is read right after the `<h1>`.

Each message is f-desk's `.flash` anatomy (surface, border, radius, `--shadow-pop`, 20px icon, text, close) with `position: static` and `width: auto`. The level sets the icon and its colour: `success` `check-circle` `--c-ok-text`; `info` / `debug` `info` `--c-note-text`; `warning` `alert-triangle` `--c-warn-text`; `error` `alert-octagon` `--c-bad-text`. `role="status"`, or `role="alert"` for `error`. The close button is `button--quiet button--icon`, `data-flash-close`, `hidden` in HTML, with visually hidden `Close this message`. On close, focus goes to `<main>`. Messages never time out. Write message text that states the outcome in words (`Request sent.`), because the icon is only a second cue. Nothing renders when there are no messages.

### D-7. Sign-in (`registration/login.html`)

**Superseded by the owner's correction (2026-09-24).** The owner said "login page design is different than the concept" and chose "Match the concept exactly". The form column now follows f-desk's `login.html` **exactly**, and this reverses D8's "app copy wins":
- The help texts are the concept's: `The name the school gave you, like nimali.p` and `Passwords are case sensitive.`
- There is **no** Show/Hide password button, so there is no `.field__row` and no `eye` symbol, and the Needs-JS row for it in D-12 falls away.
- There is **no** "Forgot your password" line, so there is no `.signin__help` and no `info` symbol on this page.

Rows below that conflict with this are struck in spirit and kept as the record. What remains from brief 001:
- the `login-error` id, text (`&rsquo;`) and role;
- the `aria-describedby` / `aria-invalid` wiring;
- the kept username;
- the autofocus rules;
- the empty-field check.

The original mapping follows.

| Current app | Becomes (f-desk class) | Notes |
|---|---|---|
| `main.login-page` | `<main class="signin" id="main" tabindex="-1">` | The split sign-in: `.signin__form`, then `.signin__brand` |
| `.login-brand` (crest, names, motto) | `.signin__brandline`: crest-chip 28px, `alt=""`, and `Technology Management Desk` (a `<p>`) | The full crest and the motto move to the brand panel |
| — | `<div class="signin__mode">{% include "partials/colour_mode_button.html" only %}</div>` | The wrapper positions it, so the partial needs no parameter |
| `h1` / `p.lead` | `.signin__middle` → `<h1>Welcome back</h1>`, `<p class="signin__sub">Sign in to the Technology Management Desk.</p>` | Centred, as f-desk |
| `div.alert#login-error` | `<div class="notice notice--bad" id="login-error" role="alert" tabindex="-1"{% if not form.errors %} hidden{% endif %}>` + `alert-octagon` 20px + `<p class="notice__title" data-login-error-title>` + `<p data-login-error-text>` | The text is unchanged: `We couldn&rsquo;t sign you in` / `That username or password didn&rsquo;t match. Try again, or ask the office to reset it.` No class value may contain ` hidden` (the tests match that substring) |
| form, CSRF, `next`, the `aria-*`, `autofocus`, kept username | unchanged, re-classed: `.field`, `.field__label`, `.field__help`, `.input` | Username help unchanged. The password help **moves above** the control (f.md §7.5): `Passwords are case sensitive. Check that Caps Lock is off.` |
| `.input-affix` + show/hide | `<div class="field__row">` (input `flex: 1`, then the button), see `docs/design/password-field.md` | `button button--secondary`, `eye` icon 16px, then the `Show` / `Hide` word, `data-toggle-password="password"`, `aria-pressed="false"`, **`hidden`** |
| `btn-primary btn-lg` with an arrow | `button button--primary button--block signin__submit` `Sign in` | No icon |
| `.login-help` | `<p class="signin__help">`: `info` 16px + `Forgot your password, or new here? Ask the office to set up or reset your account.` | 14px `--c-muted`, 24px under `Sign in`, left-aligned |
| — | `<p class="signin__foot">Polymath College · Technology Management Desk</p>` | |
| `.login-art` | `.signin__brand` → `.signin__disc` (`img/crest.png`, `alt="Polymath College crest"`) + `<p class="signin__motto">Vivere Disce ~ Learn to Live</p>` | `One place to look after…` is dropped (not in the approved look) |

- **The empty-field check (JS):** it swaps in `Please fill in both boxes` / `Type your username and password, then press Sign in.` through the two `data-login-error-*` hooks and unhides the notice. It sets `aria-invalid="true"` and `aria-describedby="login-error <id>-help"` on each empty field and focuses the first empty one. The first input event on a field removes that field's `aria-invalid` (the message stays until the next submit).
- **Focus:** before an attempt, `autofocus` stays on the username. After a failed attempt it goes to the password (today's behaviour; the notice is **not** focused, unlike f-desk).

### D-8. Settings panel and "Icons only" (criteria 12, 13)

f-desk's `.sheet` markup and copy are unchanged. The only change is the defaults (light, full, standard, purple).

**The fix:** the `Sidebar size` radios always show the **chosen** size (the one `app.js` keeps as `chosenNavSize`), never the page-only collapsed `data-nav-size`. Choosing a size applies it and saves it on `change`, and also on a `click` of the radio that is already checked. So picking the checked size ends a page-only collapse. The menu toggle only ever changes the page attribute and `aria-expanded`.

### D-9. Component → partial map

| f-desk piece | App template | Now / 005 |
|---|---|---|
| `<html>`, `<head>`, `.skip`, `.shell` grid, `<main>` + `.titlebar`, `.scrim` | `base.html` (`{% block body %}` defaults to the shell) | now |
| Feather `<svg class="sprite">` | `partials/icons.html`. Symbols: `menu`, `x`, `search`, `moon`, `sun`, `bell`, `settings`, `sliders`, `chevron-down`, `home`, `shield`, `log-out`, `info`, `check-circle`, `alert-triangle`, `alert-octagon` (16; `eye` removed with the show/hide button, D-7 / D18) | now; 005 adds its own |
| `.sidenav` (brand, close, nav) | `partials/sidebar.html` | now; `__parent` / children / helpcard in 005 |
| `.topbar` (`__start`, `__end`, brand box, toggle, `Menu` link, settings gear) | `partials/topbar.html` | now |
| `.topfind` + `.topsearch` | `partials/top_search.html` (placeholder) | now; the real form in 005 |
| `.pop` notifications | `partials/notifications.html` (empty) | now; `.pop__list` / `__item` / `__foot` / `.count` / `.tag` in 005 |
| `.pop` + `.whoami` + `.initials` | `partials/user_menu.html` | now |
| `[data-theme-toggle]` `.icon-button` | `partials/colour_mode_button.html` (topbar and login) | now |
| `.page-foot` | `partials/footer.html` | now |
| `.sheet` + `.choice` | `partials/settings_dialog.html` | now |
| `.flash` | `partials/messages.html` (in the flow, D-6) | now |
| `.box` (`__head`, `__title`, `__body`) | used in `core/home.html` | now |
| `.button` (`--primary`, `--secondary`, `--quiet`, `--icon`), `.field`, `.input`, `.notice--bad` | `registration/login.html`, dialog, flash | now (only these variants) |
| `.signin*` | `registration/login.html` | now |
| `.cards`, `.stat`, `.tag`, `.datagrid`, `.facts`, `.history`, `.empty`, `.pager`, `.chart`, `.disc`, `.options`, `.field__error`, the other `.notice` families, `kit-*` | — | 005 or later |
| `<svg class="icon"><use>` | inline, or the optional `partials/icon.html` (`name`, `size` = `sm` / `md` / `xl`) | builder's choice |

### D-10. States

| State | What the user sees |
|---|---|
| Default | As above |
| Empty | Home is the placeholder card. The bell panel shows `No notifications yet.` |
| Loading | None (no async) |
| Validation | Sign-in only (D-7): after a server attempt, or from the JS empty-field check |
| Server error | Django's default 500 (custom pages out of scope) |
| Success | Sign-in redirects to Home. A Django message shows as a flash under the title row. Sign-out lands on the sign-in page |
| No permission | Signed out: `core:home` redirects to sign-in with `next`. Not staff: no `Administration` group, no `Admin` link anywhere |
| Unavailable feature | Search placeholder and bell (D-4) |

### D-11. Accessibility and focus

- **Landmarks:** skip link `Skip to main content` (the first focusable, `#main`), then `<aside>` › `<nav aria-label="Main">`, `<header>`, `<main id="main" tabindex="-1">`, `<nav aria-label="Breadcrumb">`, `<footer>`. No `role="search"`, because there is no search form yet.
- **Headings:** one `h1` per page. `h2` for the home card title and the settings title. Group titles, `.pop__head` and the brand line are `<p>`.
- **Tab order at 1440:**
  1. skip link;
  2. brand link, `Home`, (`Admin`);
  3. menu toggle, search field, colour mode, bell, gear, user menu;
  4. page content.

  The footer has no links. At <992px, `Close the menu` comes first in the open drawer, and the brand box, toggle or `Menu` link, and search summary lead the top bar.
- **Focus after actions:**
  - drawer → the toggle;
  - pop `Escape` / outside click → its summary;
  - settings `Escape` / `Close` → the opener, or the user summary when opened from the menu;
  - flash close → `<main>`;
  - sign-in, sign-out, full page loads → the top of the page (username autofocus on sign-in).
- **Targets:** f-desk's 44–52px everywhere, including the flash close.
- **Status:** always an icon plus a word. Reduced motion as f.md §12.

### D-12. Needs JavaScript (exactly these; each is `hidden` in the HTML)

| Control | Without JS |
|---|---|
| Menu toggle | Desktop: the full sidebar. Phone: the `Menu` link opens it by `:target`, and `Close the menu` closes it |
| Colour-mode buttons (top bar, sign-in) | The page stays light (it does not follow the device, D2) |
| `Layout settings` (gear, user-menu item) | The approved defaults |
| ~~Password `Show` / `Hide`~~ | ~~The password stays masked~~. Removed: the sign-in page has no show/hide button (D-7, D18) |
| Flash close | The message stays in the flow and covers nothing |

**Enhanced, nothing hidden:**
- `Escape`, outside click and one-open-at-a-time on the three `data-pop` menus;
- the drawer's scrim, `inert` and focus return;
- the sign-in empty-field check (without JS, an empty submit gets the server's `We couldn't sign you in`);
- saving `tmd-layout`.

The allowed values and defaults live once in `theme-init.js`, for example `window.tmdLayout = {key, settings}`, and `app.js` reads them (criterion 5).

### D-13. Ruled (was: left open)

All four were ruled by the owner or the planner and are recorded in the decisions: (1) tags dropped from criterion 26's size check until brief 005; (2) the search button is removed for now, so D-4 stands; (3) messages go in the page flow, so D-6 stands; (4) the wording is `Search is coming soon` (D-4). The original notes follow.

1. **Criterion 26 lists "tags 10.5px"**, but no tag renders on home or login, and `.tag` isn't ported (criterion 28: no unused rules). The suggestion is to drop it from the render check until 005.
2. **The search icon moves to the start of the field and loses its purple fill** (D-4). That is a visible difference from the approved screenshot, chosen for honesty and the 320px fit. The reviewer should confirm, or the owner should overrule.
3. **The flash moves from a fixed toast into the page flow** (D-6). 005's "request sent" inherits this.
4. **The copy:** D12's original wording used "section", which may not mean much to staff. Ruled: `Search is coming soon`.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-django-backend (step 2b)

**Files changed**

- `apps/accounts/models.py`: added the read-only property `User.initials` (criterion 33, D10), with a docstring saying why the rule lives on the model. Also added a module docstring.
- `apps/accounts/tests.py`: **appended** 7 tests (one parametrized over 6 cases, plus the saved-user case). No existing test was touched, so criterion 16 still holds.

**The rule as implemented:** first letters of `first_name` and `last_name`, upper-cased (`Nimali Perera` → `NP`). If only one is set, that one's letter. If neither is set, the username's first letter. Names are stripped first, so a name made only of spaces counts as unset. A saved user always has a username, so the result is never empty for one.

**Context contract:** `user.initials` (`str`) is provided as the contract says. There are no deviations. `get_full_name`, `is_staff`, `request.resolver_match`, `messages` and `csrf_token` come from Django and the existing context processors, so the backend changed none of them. No view, URL or settings change.

**Tests left to others:** the three rewritten tests in `apps/core/tests.py` (the sign-out button test, `_admin_links` plus the two admin-link tests) and the widened header test are assigned to `tmd-test-verifier` under "Tests deliberately updated". I did not touch them. None of my tests depend on markup, so none of them wait for the frontend.

**Migrations:** none. `makemigrations --check --dry-run` says `No changes detected`.

**Dependencies and settings:** none.

**Self-check** (dev container, run against whatever templates and static files were in the working tree at the time):

- `ruff check .`: All checks passed.
- `ruff format --check .`: 42 files already formatted.
- `manage.py check`: no issues.
- `pytest --create-db`: 36 passed.
- `makemigrations --check --dry-run`: No changes detected.

The dev stack was started for these checks and then brought down again, so nothing from this project is running, which is how I found it.

### tmd-frontend (step 2a)

**Files changed**

- **`templates/base.html`** is rewritten as the f-desk document and shell.
  - `<html>` carries the approved defaults. The head order is `theme-init.js` (blocking), the Plex stylesheet, `style.css`, then `app.js` (`defer`).
  - The skip link comes next, then the sprite include.
  - `{% block body %}` defaults to the shell: sidebar, scrim, top bar, `<main>` with the title row, messages and `content`, then the footer and the settings dialog.
  - Blocks: `title`, `head`, `body`, `heading`, `breadcrumb`, `content`, `scripts`. `body_class` is gone because nothing uses it.
  - The first breadcrumb is `<span aria-current="page">Home</span>` on `core:home`, otherwise a link followed by `{% block breadcrumb %}`.
- **New partials in `templates/partials/`.** All are included with `… only`, and each has a `{# #}` header on line 1:
  - `icons.html`: the Feather sprite. It has 17 symbols, exactly D-9's list, including `shield` and `eye` from Feather. The MIT notice is in its header.
  - `sidebar.html`, `topbar.html`, `top_search.html`, `notifications.html`, `user_menu.html`.
  - `colour_mode_button.html`, used by the top bar and by login.
  - `messages.html`, `footer.html`, `settings_dialog.html`.
- **Deleted:** `templates/partials/icon_templates.html`. The deletion is not staged.
- **`templates/registration/login.html`** is ported to f-desk's split sign-in (D-7).
  - It overrides `body`. All brief 001 attributes and copy are unchanged: `id="login-error"`, `role="alert"`, the `hidden` rule, the `aria-describedby` / `aria-invalid` / `autofocus` logic and the kept username.
  - The password help now sits above the control.
  - The show/hide button is `hidden` and sits in a `.field__row`.
  - The Solar icons are gone.
- **`templates/core/home.html`** is now one `.box` card per D-5. Its sign-out form and Admin link moved to the shell (D7).
- **`static/css/style.css`** is replaced. It uses the nine f-desk sections in 003/29's order.
  - Tokens follow D-1b: role names and `rem` type with unitless line heights. The value-named `--dk-*` layer is folded into the single dark block.
  - Only the pieces in D-9's "now" column are ported.
  - `.visually-hidden` is written once in section 2. It also has two scoped copies, one in section 6 (`≥992px`) and one in section 8 (`<992px`), so there are 3 clip declarations in total.
  - The white active bar on purple is in the tone set.
  - The new `<360px` block implements D-4's 320px fixes.
- **`static/js/theme-init.js`** (new) publishes `window.tmdLayout = {key, settings}`, then applies the saved values.
- **`static/js/app.js`** is replaced. Its blocks are:
  1. helpers;
  2. settings, reading `window.tmdLayout` with no second copy (criterion 5);
  3. colour mode;
  4. settings dialog, including the "Icons only" fix;
  5. menu toggle and drawer;
  6. `data-pop`;
  7. flash close, which removes the message and focuses `<main>`;
  8. sign-in show/hide and the empty-field check, now also setting `aria-invalid` and `aria-describedby`.

  The old toast, modal, chart and inventory code is gone.

**Spec deviations and choices (all small)**

1. **Colour-mode icon.** The button renders both the moon and the sun, and CSS shows the one that matches `data-theme`. The prototype swapped `<use href>` from JS. This way `#i-sun` is used by a template (criterion 23 needs every symbol used), and the right icon is there from first paint. JS only updates the spoken label.
2. **Show/hide accessible name.** The button reads "Show password" / "Hide password": the visible word `Show`/`Hide` comes from `data-toggle-password-label`, and a visually hidden " password" follows it. On its own, "Show" does not say what it shows.
3. **New JS hooks** beyond the contract's list:
   - `data-login-error`, `data-login-error-title` and `data-login-error-text` (D-7 named the last two);
   - `data-login-field` (`="trim"` on the username, so spaces alone count as empty; the password is taken as typed);
   - `data-toggle-password-label`.

   Every hook is a `data-*` attribute, and the old `data-field` is not needed.
4. **Phone user-menu head.** At `<992px` the prototype's scoped hide (`.whoami__text`) also hid the name inside the panel head. The app scopes the hide to `.whoami > .whoami__name` and `.whoami > .whoami__chevron`, so the panel head shows the name, as D-4 intends.
5. **Sign-in column widths.** f-desk's three sign-in column rules are collapsed into one equivalent `max-width: 1399.98px` rule: 420px below 1400, 360px at 1400 and up. The prototype's dead phone rules (`.shell > main` padding repeated at `<768px`) and the flash's fixed-position rules are dropped.
6. **Test ownership.** No test was edited. The brief assigns the three rewrites in `apps/core/tests.py` to `tmd-test-verifier` ("Tests deliberately updated (the verifier owns them)"), and they fail until the verifier rewrites them (see below).

**Context contract gaps:** none. Every template reads only contract variables. `request.resolver_match` is read only in `base.html`, and `csrf_token` is passed explicitly into the `only` includes. `current_ns` is passed into the sidebar as the contract says, but nothing reads it yet; 005 will.

**Self-check.** The dev overlay was started for this and brought down afterwards, because it was down when I began. Two throwaway users were created for the HTTP renders and then deleted.

- `pytest --create-db` in the dev container: **33 passed, 3 failed.** The 3 failures are exactly the tests listed under "Tests deliberately updated":
  - `test_home_shows_sign_out_button_that_posts_to_logout`: the button now starts with an SVG;
  - `test_home_shows_admin_link_to_staff` and `test_home_shows_admin_link_to_superuser`: `Admin` is now inside a `<span>` beside an icon.

  Every test in `apps/accounts/tests.py` passes unchanged, and so does `test_every_static_reference_in_templates_exists`, which now covers `theme-init.js`.
- **Static guard script** (scratchpad `static_004.py`): all pass.
  - Criterion 21: all 13 templates have a header on line 1.
  - Criterion 22: every include has `only`, there are no `style=` attributes and no hard-coded hrefs.
  - Criterion 23: 17 symbols, all used, no undefined `use`, no path data outside the sprite.
  - Criterion 25: no colour literal outside the palette and no value-named token.
  - Criterion 26: no `px` font-size and no root size.
  - Criterion 27: 3 clip declarations.
  - Criterion 37: the old string is gone. No Cinzel or Nunito.
  - Also checked: every class in the CSS is used by a template or `app.js`, and every template class has a rule.
- **Playwright over HTTP on :8010, dev stack** (scratchpad `fe004.mjs`): **90 PASS / 0 FAIL, no console errors.**
  - **Renders:** login and home return 200 at 1440×900, 400×844 and 320×640, light and dark. There is no horizontal scroll, and every link, button and summary is at least 44px (crumbs exempt).
  - **Shell at 1440:** sidebar 250px, top bar 70px plus its 1px rule, search 304×44. Computed sizes: body 14px, item 14.4px, h1 18px, card 15.4px, group 12px. The h1 and breadcrumb share a row at 1440 and stack at 400 and 320.
  - **First visit:** with the device dark, both pages open light with the purple sidebar and a white background. A saved choice is present at `DOMContentLoaded`.
  - **"Icons only" sync:** Compact, then the toggle, then reopening the panel shows Compact. Choosing Icons only saves `navSize: "icons"`, which survives a reload. The toggle never writes storage. Reset returns light, full, standard and purple and removes the key.
  - **Menus:** the bell and user menu close on `Escape` or an outside click, with focus back on their summary. The search field ignores typing and Enter. The drawer makes the page inert, focuses `Close the menu`, and `Escape` returns focus to the toggle.
  - **JS off:** every JS-only control is hidden. Sign-in submits. The `Menu` link opens the sidebar through `:target`, the phone search panel opens, and sign-out by POST lands on login. A non-staff user has no Admin link.
  - **Sign-in:** the empty-field check sets the copy, `aria-invalid` and `aria-describedby="login-error password-help"`, and focus. Show/hide switches the type, `aria-pressed` and the word. A wrong password shows the notice with focus on the password.
- **Messages** (home view rendered with `messages.success` and `messages.error` on the request): they appear once, between `.titlebar` and the card inside `<main>`, as `flash--ok` with `role="status"` and `flash--bad` with `role="alert"`. The text is escaped. The page's only `<form>` is sign-out.
- **Screenshots**, not committed, in the scratchpad `shots004/`:
  - `login--{1440,400,320}--{light,dark}.png` and `home--{1440,400,320}--{light,dark}.png`;
  - `home--first-visit.png`, `home--notifications-open.png`, `home--search-focused.png`, `home--drawer-open.png`;
  - `home--400--nojs-search.png`, `home--1440--saved-dark-boxed-compact-light.png`, `login--1440--error.png`.
- **Review round 1 fixes (`static/js/app.js`):** `chosenNavSize` now reads only `data-nav-size`, so there is no second copy of the default (criterion 5). The Sidebar size click handler now applies only when `input.value === chosenNavSize`, so a newly picked size is saved once, by `change`. `node --check static/js/app.js` passes; the full suite is left to the verifier.

**Owner correction: sign-in matches the concept.** The owner said "login page design is different than the concept" and chose "Match the concept exactly". This reverses D-7's "app copy wins" (D8) for the form column.

- **What changed in `templates/registration/login.html`:**
  - The username help is now the concept's `The name the school gave you, like nimali.p`.
  - The password help is `Passwords are case sensitive.`
  - The password field is full width, with no Show/Hide button.
  - The "Forgot your password, or new here?" line is gone.
  - The `{# #}` header is updated.
- **What was removed because nothing else used it:**
  - the show/hide JS block in `static/js/app.js` (block 8 is now only the empty-field check);
  - `.field__row` and `.signin__help` in `static/css/style.css`;
  - the `eye` symbol in `partials/icons.html`, leaving 16 symbols, all used.

  `docs/design/password-field.md` and criterion 18's show/hide bullet no longer describe the app. That is for the designer, planner and docs writer to settle.
- **Kept, because each one is behaviour rather than visible copy:**
  - `#login-error`: `role="alert"`, `hidden` unless `form.errors`, and its title and text;
  - the `aria-describedby` order (`login-error` before the help id), `aria-invalid`, the kept username and the `username-help` / `password-help` ids;
  - the autofocus rules (username first; password after a failed attempt);
  - the POST with CSRF, `next`, and the `tmd_site_name` title;
  - the JS empty-field check.
- **Remaining differences from `desktop-login--error.png`:**
  - The concept draws the apostrophe as a straight `'`. The app keeps `&rsquo;`, because `test_login_with_wrong_password_shows_error` pins `We couldn&rsquo;t sign you in`. The words are identical.
  - After a failed attempt the concept focuses the notice. The app focuses the password, per brief 001's kept autofocus rule.
  - Before any attempt, the username shows its autofocus ring. The concept screenshot has none.
- **Self-check** on the running dev stack (left running as found), rendered at 1440 and 400:
  - The form-column geometry equals the concept.
    - At 1440: h1 at y 233; username 401; password 521; Sign in 609; all 264px wide.
    - Error state: notice 279–389; username 466; password 586; Sign in 674.
    - At 400 it matches `mobile-login--light.png` pixel for pixel, apart from the autofocus ring.
  - No horizontal scroll and no console errors. The empty-field check still works.
  - The static guard script passes.
  - `pytest apps/accounts/tests.py apps/core/tests.py`: **76 passed, 0 failed.** No existing test asserted the old help copy, the Show button or the forgot line, so none fails because of this correction.
  - Screenshots are in the scratchpad: `shots004/login--{1440,400}--concept-match.png` and `login--1440--error--concept-match.png`.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

### Tests added / rewritten

`apps/core/tests.py` was rewritten: the three tests the brief assigns to the verifier
(`test_home_shows_sign_out_button_that_posts_to_logout`, `_admin_links` plus
`test_home_shows_admin_link_to_staff` / `_to_superuser`) now match text content with
tags stripped, so the icon-plus-word markup passes; `test_template_starts_with_purpose_comment`
is parametrized over every template found under `templates/` (`rglob`), not the old
hard-coded list of three. `apps/accounts/tests.py` was **not** touched (confirmed via
`git diff --stat`: 0 changes from the verifier; only the backend's own 26-line addition
of the `initials` tests is present, matching its Implementation notes). ~40 new pytest
tests were added to `apps/core/tests.py` covering the shell/CSS/placeholder criteria
listed below. All were run and shown to fail against the wrong behaviour while writing
them (e.g. the redirect-away-from-login bug, the `2. Base and reset` header/divider
collision, the tautological form assertion — each caught and fixed before the final run).

### Acceptance criteria

| # | Result | Evidence |
|---|---|---|
| 1 | ✅ | `test_home_html_tag_carries_approved_defaults`, `test_login_html_tag_carries_approved_defaults` |
| 2 | ✅ | `test_home_head_loads_theme_init_before_fonts_before_style`, `test_login_head_loads_theme_init_before_fonts_before_style`, `test_no_template_references_the_old_fonts` |
| 3 | ✅ | Playwright `g1_defaults.mjs`: device `prefers-color-scheme: dark`, empty storage → `data-theme="light" data-nav-tone="purple"` at DOMContentLoaded on login and home |
| 4 | ✅ | Playwright `g1_defaults.mjs`: seeded `tmd-layout` → all four attrs correct at DOMContentLoaded |
| 5 | ✅ | Playwright `g1_defaults.mjs`: `window.tmdLayout` published by theme-init.js; read `static/js/app.js` — no second copy of the values/defaults |
| 6 | ✅ | `test_sidebar_home_link_has_aria_current_only_on_home`, `test_sidebar_links_resolve_to_named_urls_only`, `test_sidebar_shows_administration_group_only_for_staff`; Playwright `g6_misc.mjs` sidebar width 250px (±2) at 1440 |
| 7 | ✅ | `contrast.mjs` recomputed from the actual CSS token hex values: white bar on `--nav-bg` `#722A82` = 8.86:1, on active row `#5C1F6A` = 11.30:1, active text on active row = 11.30:1 — all ≥ required, marker is white not `#722A82` |
| 8 | ✅ | Playwright `g6_misc.mjs` top bar 71px (70±2) at 1440; template order confirmed by reading `partials/topbar.html` (toggle → Menu link → search; colour mode → bell → gear → user menu); no dead links |
| 9 | ✅ | `test_no_anchor_link_points_at_logout`, `test_home_shows_sign_out_button_that_posts_to_logout`, `test_user_menu_layout_settings_button_is_hidden_in_html`; Playwright `g6_misc.mjs` Escape returns focus to the user-menu summary |
| 10 | ✅ | Playwright `g6_misc.mjs`: h1/breadcrumb share a row at 1440, stack at 400; home h1 = "Home", trail = "Home" (template read) |
| 11 | ✅ | `partials/footer.html` read: `{% now "Y" %} © Polymath College` / `Technology Management Desk`, no links; visible in all screenshots |
| 12 | ✅ | `test_settings_dialog_present_on_home`, `test_settings_dialog_absent_on_login`; Playwright `g2_settings.mjs` opens/closes/Escape-focus-return |
| 13 | ✅ | Playwright `g2_settings.mjs`: Compact → toggle collapse → reopen shows Compact checked (not "icons") → choosing Icons only applies+saves → survives reload; toggle alone never wrote storage |
| 14 | ✅ | Playwright `g3_responsive.mjs` (JS: drawer+scrim+inert+focus, Escape returns focus to toggle); Playwright `g5…mjs` (no-JS: `Menu` link opens via `:target`) |
| 15 | ✅ | `test_success_message_renders_once_in_flow_under_title_row_with_role_status` (escaping, placement between titlebar and content, `data-flash-close hidden`), `test_error_message_uses_role_alert`, `test_no_message_renders_no_flash_container` |
| 16 | ✅ | `pytest apps/accounts/tests.py`: all 15 tests pass, file byte-for-byte untouched by this task |
| 17 | ✅ | `test_login_page_has_exactly_one_h1_reading_welcome_back`, `test_login_page_has_no_shell_chrome` |
| 18 | ✅ | Playwright `g6_misc.mjs`: empty-field check sets copy/`aria-invalid`/`aria-describedby`/focus; show/hide toggles type/`aria-pressed`/word; screenshot `login--1440--error.png` |
| 19 | ✅ | `test_home_title_and_body_use_site_name` (kept, passes unchanged) |
| 20 | ✅ | `test_home_hides_admin_link_from_non_staff`, `test_home_shows_admin_link_to_staff`, `test_home_shows_admin_link_to_superuser` |
| 21 | ✅ | `test_template_starts_with_purpose_comment` parametrized over all 13 templates via `rglob` |
| 22 | ✅ | `test_every_include_ends_with_only`, `test_no_inline_style_attributes_in_templates`; manual grep confirmed every `href` is either `{% url %}`-derived, a font-provider link, or an in-page `#i-…`/`#nav`/`#main` anchor |
| 23 | ✅ | `test_icons_partial_holds_the_only_symbol_elements`, `test_every_icon_use_references_a_defined_symbol_and_every_symbol_is_used` (17/17 used), `test_icon_sprite_appears_exactly_once_on_rendered_pages` |
| 24 | ✅ | `test_every_static_reference_in_templates_exists` passes (kept unchanged), covers `theme-init.js` via `base.html`'s `{% static %}` reference |
| 25 | ✅ | `test_css_colour_literals_live_only_in_the_root_palette_block` (renamed/narrowed in re-verification, see below), `test_css_custom_property_names_do_not_encode_their_value`; manual grep confirmed no hex/rgb/hsl outside the token block |
| 26 | ✅ | `test_css_font_sizes_are_rem_and_the_root_size_is_never_set`; Playwright `g5…mjs`: 16px root → body 14/nav 14.4/h1 18/card 15.4/group 12px (all within ±0.5px); 20px root → body 17.5px, sidebar geometry unchanged (250px) |
| 27 | ✅ | Manual grep: exactly 3 `clip-path: inset(50%)` declarations (base + two width-scoped groups) |
| 28 | ✅ | Manual review: section order 1–9 matches 003/29; grep found no `.tag`/`.stat`/`.cards`/`.chart`/`.kit-`/`.datagrid`/etc. dead prototype rules |
| 29 | ✅ | Playwright `g4…mjs` (22 checks) + `g10_navsizes_scroll.mjs` (12 checks, all 3 sidebar sizes): `scrollWidth - clientWidth` ≤ 0 at 320/400/1024/1440, light+dark, home+login |
| 30 | ✅ | Playwright `g4…mjs`: no element under 44×44 at 400 or 1440 (crumbs exempt) |
| 31 | ✅ | `contrast.mjs`: body/muted text, purple/light/dark sidebar bars, search placeholder in both modes — all ≥ AA from actual token values |
| 32 | ✅ | Playwright `g5…mjs` (JS off: sign-in, sign-out, phone search panel, `:target` menu, all JS-only controls `hidden`) + `g6_misc.mjs` (0 console errors with JS on) |
| 33 | ✅ | `test_initials_follow_name_then_username_rule` (6 cases), `test_initials_never_empty_for_saved_user`; `makemigrations --check --dry-run` → "No changes detected" |
| 34 | ✅ | see Checklist below |
| 35 | ✅ | see Checklist below (prod HTTP) |
| 36 | ✅ | 19 screenshots captured in the scratchpad (paths below); purple shell geometry compared side-by-side against `design/f-desk/screenshots/desktop-dashboard--nav-purple.png` — sidebar width, top bar height and title-row position match within ±2px; the search button/icon position is the recorded deliberate difference (D15) |
| 37 | ✅ | `test_search_placeholder_field_is_readonly_and_described`, `test_home_page_has_no_form_other_than_sign_out`, `test_old_search_copy_appears_nowhere_in_templates`; Playwright: field 304×44, `cursor: not-allowed`, typing/Enter no-ops, placeholder contrast recomputed (5.32:1 light / 4.54:1 dark) |
| 38 | ✅ | `test_notifications_bell_has_no_badge_and_says_none_yet`; Playwright: accessible name "Notifications, none yet", Escape/outside-click close with focus return, target ≥44×44 at 400 and 1440, screenshot `home--notifications-open.png` |

### Checklist (CLAUDE.md "Verify a change")

- `ruff check .` ✅ All checks passed
- `ruff format --check .` ✅ 42 files already formatted
- `pytest --create-db -rA` ✅ **75 passed** (dev container; includes 15 in `apps/accounts/tests.py` unchanged, 60 in `apps/core/tests.py`)
- `makemigrations --check --dry-run` ✅ No changes detected
- `manage.py check` ✅ System check identified no issues (0 silenced)
- `check --deploy` — n/a, confirmed no settings/config/Docker files changed (`git diff --stat config/` empty)
- **Prod stack** (`docker compose up -d --build`, waited for `web` healthy):
  - `GET /accounts/login/` → 200, CSRF token present
  - Wrong password → 200, re-renders with `We couldn't sign you in`
  - Real sign-in → 302 → home 200, for a staff/superuser (`verify004`) and a non-staff user (`verify004staffno`, first/last name set)
  - `theme-init.js`, `style.css`, `app.js`, `crest-chip.png`, `crest.png`, `favicon-32.png` all served from hashed WhiteNoise paths, all 200
  - Non-staff home: no "Admin" text anywhere; staff home: exactly one Admin link to `/admin/`
  - Sign-out by POST → 302 → `/accounts/login/`
  - Only origins referenced: the app itself, `fonts.googleapis.com`, `fonts.gstatic.com` (the one `http://www.w3.org` string is the SVG namespace URI in the sprite, not a fetched resource)
  - Throwaway superuser and non-staff user created via `manage.py createsuperuser --noinput` / shell, logged-in HTML of home (staff + non-staff) and login saved to the scratchpad **before** deletion, then both deleted
  - Docker restored: stopped after use; nothing from `polymath-tmd` was running before this session and nothing is running now

### Accessibility audit (saved HTML, `docs/tasks` checklist)

- Every input has a `<label for>` (username, password, `#top-search`) — confirmed in templates and rendered HTML
- Errors linked with `aria-describedby`; `aria-invalid` set on error — accounts tests + `g6_misc.mjs`
- Exactly one `h1` per page, confirmed on both home and login renders; headings run h1→h2 (card title, settings title)
- Landmarks present: skip link, `<aside><nav aria-label="Main">`, `<header>`, `<main id="main" tabindex="-1">`, `<nav aria-label="Breadcrumb">`, `<footer>` — grepped from saved `home-staff.html`
- Images have `alt`: crest chips `alt=""` (decorative), sign-in crest `alt="Polymath College crest"`
- Status always icon + word: flash messages, bell accessible name, search note
- Buttons have accessible names: settings gear "Layout settings", colour mode "Switch to … mode", bell "Notifications, none yet", menu toggle "Show/Hide the menu"
- Targets ≥44×44: confirmed via Playwright at 400 and 1440 (0 undersized elements outside the exempt breadcrumbs)

### Screenshots (verifier's scratchpad, not committed)

`C:\Users\ASUS\AppData\Local\Temp\claude\d--My-work-PolymathTMD\c2317be1-7dfa-485a-8134-215a52759cb9\scratchpad\verify004\`:
`login--1440--light.png`, `login--1440--dark.png`, `login--1440--error.png`, `login--400--light.png`, `login--400--dark.png`,
`login--320--light.png`, `login--320--dark.png`, `home--1440--light.png`, `home--1440--dark.png`, `home--400--light.png`,
`home--400--dark.png`, `home--320--light.png`, `home--320--dark.png`, `home--first-visit.png`, `home--drawer-open.png`,
`home--notifications-open.png`, `home--search-focused.png`, `home--400--nojs-search.png`, `home--1440--saved-dark-boxed-compact-light.png`.

### Playwright scripts (verifier's scratchpad, for re-run)

`...\scratchpad\verify004\g1_defaults.mjs`, `g2_settings.mjs`, `g3_responsive.mjs`, `g4_search_scroll_targets.mjs`,
`g5_jsoff_rem_navsizes.mjs`, `g6_misc.mjs`, `g7_screenshots.mjs`, `g8_drawer_shot.mjs`, `g9_bell_shot.mjs`,
`g10_navsizes_scroll.mjs`, `contrast.mjs` — run against the dev stack on port 8010.

### Failures

None. No agent action required.

### Re-verification (after review round 1)

**Verdict: PASS**

Addressed the should-fix and both test nits from Review round 1, owned by `tmd-test-verifier`, in `apps/core/tests.py`:

1. **`test_css_colour_literals_live_only_in_the_root_palette_block`** (renamed from `..._root_token_section`). The allowed zone is now the first `:root { … }` block only (the 1a palette, ~lines 37–91), found by regex rather than a line-number slice, so the dark-mode block and the three `[data-nav-tone]` blocks are checked too. Pattern widened to `#[0-9A-Fa-f]{3,8}\b|rgba?\(|hsla?\(` so the `rgba(...)` shadow/scrim/line values in the palette no longer slip past the "expect a literal in here" sanity check being satisfied by hex alone. **Proved it bites**: in a scratch copy (`scratchpad/verify004/prove/style.css`, never the real file), added `--c-page: #111111;` inside `:root[data-theme="dark"]` and confirmed the check now fails (`['#111111']`); the unmutated file still passes.
2. **`test_css_custom_property_names_do_not_encode_their_value`**. Added an explicit allow-list (`ALLOWED_DIGIT_SUFFIX_PREFIXES`) of the only prefixes permitted to end in a bare `-<digits>`: the colour scales (`white`, `clear`, `grey`, `crest`, `green`, `amber`, `red`, `blue`) and the two ordinal non-colour scales already in the shipped CSS (`--space-1`..`8`, `--c-surface-2`). Any other name ending in `-<digits>` is now rejected. **Proved it bites**: mutated a scratch copy to rename `--fs-body` → `--fs-14` and `--icon-md` → `--icon-16`; both are now caught (`['fs-14']`, `['icon-16']`); confirmed `--space-3`, `--crest-600`, `--c-surface-2` still pass on the real file.
3. **New test `test_no_hardcoded_paths_in_href_or_action_attributes`** (criterion 22): scans every template's raw source for `href="…"` / `action="…"` starting with `/`; `{% url %}`/`{% static %}` tags read as literal tag text in source (never a leading `/`) so they never trip it, and in-page `#…` anchors are unaffected. **Proved it bites**: mutated a scratch copy of `home.html` to add `<a href="/students/">x</a>`; the check now fails (`['href="/students/"']`); the real templates pass with zero offenders.

Proof script: `scratchpad/verify004/prove/prove_review_fixes.py`, run against scratch copies in `scratchpad/verify004/prove/` (`style.css`, `home.html`) — no product file was ever mutated.

**tmd-frontend's `static/js/app.js` fix** (parallel, should-fix #2) confirmed landed: line 47 is now `var chosenNavSize = root.getAttribute('data-nav-size');` (no second copy of the `navSize` default — `<html>` always carries the attribute, so the old `? … : 'standard'` fallback was dead code per criterion 5), and the sidebar-size click handler at ~168–171 now guards with `input.value === chosenNavSize` so a newly-chosen size isn't double-fired through both the `click` and `change` handlers.

**Checklist re-run** (dev stack, `docker compose -f compose.yaml -f compose.dev.yaml up -d`, brought down again afterwards):
- `ruff check .` ✅ All checks passed
- `ruff format --check .` ✅ 42 files already formatted
- `pytest --create-db -rA` ✅ **76 passed** (75 + the new criterion-22 guard test)
- No prod rebuild: only `apps/core/tests.py` (tests) and `static/js/app.js` (no new/renamed/removed static file, no template reference change) changed, so `test_every_static_reference_in_templates_exists` already covers it and prod hashing is unaffected

**Playwright re-run against the dev stack** (`verify004/g1_defaults.mjs`, `g2_settings.mjs`, plus a new `g11_doublefire_guard.mjs` targeting the click/change double-fire fix specifically):
- Criterion 3 (first visit light/purple despite dark device scheme) ✅ 4/4 in `g1_defaults.mjs`
- Criterion 4 (saved choice wins at DOMContentLoaded) ✅
- Criterion 5 (`window.tmdLayout` the one source, `app.js` reads it) ✅
- Criterion 12/13 (settings dialog, Icons-only sync, reset) ✅ 11/11 in `g2_settings.mjs` — Compact → page-only collapse → reopen still shows Compact checked → Icons only applies+saves → survives reload → Reset returns to light/full/standard/purple and clears storage → Escape closes and returns focus
- Double-fire guard specifically: `g11_doublefire_guard.mjs` instruments `localStorage.setItem` — choosing a **new** sidebar size writes `tmd-layout` exactly once (not twice via click+change), and clicking the **already-checked** size (the page-only-collapse-undo path) also writes exactly once, confirming the `input.value === chosenNavSize` guard neither double-writes nor breaks the already-checked case

A superseded throwaway user (`pwverify`) was created for these Playwright runs and deleted afterwards. Docker was stopped after use; nothing from `polymath-tmd` is running, matching the state before this round.

**Failures:** none. No agent action required.

### Re-verification (owner correction: sign-in)

**Verdict: PASS**

Owner correction, verbatim: "login page design is different than the concept"; chosen resolution "Match the concept exactly". Verified `tmd-frontend`'s change to `templates/registration/login.html` (concept help copy, full-width password, no Show/Hide button, no forgot-password line) plus the removal of the show/hide JS block from `static/js/app.js`, `.field__row`/`.signin__help` from `static/css/style.css`, and the `eye` symbol from `partials/icons.html`.

**(1) Checklist**, dev stack (already running, left running throughout):
- `ruff check .` ✅ All checks passed
- `ruff format --check .` ✅ 42 files already formatted
- `pytest --create-db -rA` ✅ **76 passed**, matching tmd-frontend's self-check exactly

**(2) New pinning tests**, appended to `apps/accounts/tests.py` (existing tests untouched):
- `test_login_username_help_matches_the_concept_copy` — exact text `The name the school gave you, like nimali.p`
- `test_login_password_help_matches_the_concept_copy` — exact text `Passwords are case sensitive.`, and confirms the old `Check that Caps Lock is off` sentence is gone
- `test_login_page_has_no_password_show_hide_control` — no `data-toggle-password` hook, no `>Show<` / `>Hide<` text
- `test_login_page_has_no_forgot_password_help_line` — no `Forgot your password` text, no `signin__help` class
- `test_login_password_field_is_not_wrapped_in_a_toggle_row` — no `field__row` anywhere, and no `<button` between the password input and its field wrapper's closing `</div>`
- `test_login_autofocus_on_username_before_any_attempt` / `test_login_autofocus_moves_to_password_after_wrong_password` — pin D8's kept autofocus rule across the structural change around the password field

All 7 pass against the live template (`pytest apps/accounts/tests.py apps/core/tests.py --create-db -rA` → **83 passed**). **Proved each fails against the old markup**: `scratchpad/verify004/prove/prove_signin_correction.py` reconstructs the pre-correction fragment (old help copy with a nested `<strong>`, `.field__row` + `data-toggle-password` + `eye` icon + `Show` label, the `signin__help` "Forgot your password…" line) in a scratch string — never the real template — and runs the identical regex assertions: **9/9 correctly reject the old markup** (the two help-copy assertions correctly fail because the old copy doesn't match verbatim, including the old username help's nested `<strong>` tag truncating the captured text).

**(3) Brief-001 sign-in behaviours**: the full existing `apps/accounts/tests.py` suite (15 original tests, now 22 with the additions) passes unchanged — error alert `id`/`role="alert"`/`hidden`, `aria-describedby` order (`login-error` before the help id), `aria-invalid`, kept username, title. Added explicit autofocus pinning (see above) since the password field's DOM structure changed (no more `.field__row` wrapper) and autofocus wasn't previously covered by a dedicated test. `next` and the POST+CSRF plumbing are unchanged Django/LoginView behaviour, not touched by this correction, and continue to render (`test_login_page_renders` still checks the CSRF field; the `next` hidden input's template line is untouched).

**(4) Static/sprite guards**: `test_every_static_reference_in_templates_exists` ✅ and `test_every_icon_use_references_a_defined_symbol_and_every_symbol_is_used` ✅ both still pass post-`eye`-removal — 16 symbols remain, all used, confirmed by direct read of `partials/icons.html` (`eye` absent, symbol count 16) and `static/js/app.js` (no `toggle-password` or `eye` reference left). No `{% static %}` reference changed (`img/crest-chip.png` and `img/crest.png` are the same two images used before and after this correction) — confirmed no prod rebuild needed.

**(5) Playwright visual comparison**, dev stack, port 8010 (`scratchpad/verify004/g12_signin_concept_shots.mjs`, 12/12 checks passed, 0 console errors):
- `login--1440--light--concept-match.png` vs `design/f-desk/screenshots/desktop-login--light.png`: layout, copy, spacing and the full-width password field match. Geometry independently recomputed (not just read from the frontend's notes): h1 y=233, username y=401, password y=521, Sign in y=609, both fields 264px wide — all exactly as tmd-frontend reported.
- `login--1440--error--concept-match.png` vs `desktop-login--error.png`: notice box, red-bordered invalid fields and kept username (`pwverify`) all match.
- `login--400--light--concept-match.png` vs `mobile-login--light.png`: matches, including the stacked layout and full-width controls.
- `login--1440--dark--concept-match.png` viewed for extra confidence against `desktop-login--dark.png` (not required by the brief but checked): same match quality in dark mode.
- **Remaining differences, all as tmd-frontend recorded and all deliberately kept for brief-001 reasons — confirmed by direct observation, not just reading the notes:**
  1. Curly apostrophe (`We couldn’t sign you in`) vs the concept's straight `'` — confirmed via `errorTitle === "We couldn’t sign you in"` (pinned by the existing `test_login_with_wrong_password_shows_error`).
  2. After a failed attempt, focus lands on the **password** field (visible focus ring in the screenshot), not the notice, as the concept shows — confirmed via `document.activeElement.id === "password"`.
  3. On first load the **username** field shows a focus ring (autofocus) that the concept screenshot doesn't have — visible in `login--1440--light--concept-match.png` and `login--400--light--concept-match.png`.
  No other differences found.

**Cleanup**: throwaway user `pwverify` created for the Playwright runs and deleted afterwards. Dev stack left running (as found and as instructed) — no prod rebuild performed since no `{% static %}` reference changed.

**Failures:** none. No agent action required.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-24 (verifier PASS)

**Verdict: CHANGES REQUESTED** (no blockers)

**Should fix**
1. `apps/core/tests.py:493–495` — `test_css_colour_literals_live_only_in_the_root_token_section` misses `rgba(`/`hsla(` (every translucent palette value is rgba) and treats all of section 1 as allowed, so a hex in the dark block (`style.css:288`) or a `[data-nav-tone]` block (`:329`, `:343`) passes, against criterion 25. Fix: pattern `#[0-9A-Fa-f]{3,8}\b|rgba?\(|hsla?\(`, allowed zone = the palette block only (first `:root {…}`, lines 37–91). Owner: tmd-test-verifier.
2. `static/js/app.js:47` — `(SETTINGS.navSize ? SETTINGS.navSize.fallback : 'standard')` is a second copy of a default (criterion 5) and dead because `<html>` always carries `data-nav-size`. Fix: `var chosenNavSize = root.getAttribute('data-nav-size');`. Owner: tmd-frontend.

**Nits:** token-name test accepts value-style names like `--fs-14` (reject non-colour tokens ending `-<digits>`); add a pytest guard for criterion 22 (no `href="/"` / `action="/"` in templates); `user_menu.html:3,5` repeats the display-name rule that `User.__str__` already owns (D10 — accept unless the planner agrees to change); `current_ns` passed to the sidebar but unused until 005; sidebar-size radio fires `setSetting` twice (guard with `input.value === chosenNavSize`); boxed-width shadow uses the light `--shadow-pop` in dark mode (faithful to the prototype); the `.gitignore` change is outside this task — commit it separately.

**Checklist:** all 13 templates have `{# #}` headers; every include uses `only` with `csrf_token` passed explicitly; one sprite; URLs by name; no `|safe`, messages autoescaped; sign-out POST with CSRF, no `<a>` to logout; Admin staff-only; JS binds via `data-*` only; colour literals only in the palette; brief-001 login behaviours intact; `User.initials` on the model, no migration.

**Brief 003 porting follow-ups:** all five done (rem type, role-named tokens, one visually-hidden utility, Icons-only fix, 320px block).

**Fidelity:** geometry, type and colour match the approved `desktop-dashboard--nav-purple.png`. What the client will notice: no purple search button (dashed placeholder field, D15); no bell count; no job title under the user's name; sidebar shows only Home (+ Admin for staff); Home is one greeting card.

**For brief 005:** the shell assumes a signed-in user (user menu, sidebar Home link). The public Zoom request form must either override `{% block body %}` like `login.html` or add `{% if user.is_authenticated %}` branches in `topbar.html` and `sidebar.html` — the 005 planner must record which.

**Good:** `theme-init.js` publishes `window.tmdLayout` and `app.js` reads it (one source of values and defaults); the colour-mode button renders both icons and CSS picks one, so the right icon shows from first paint.

### Round 2 — 2026-09-24 (after round-1 fixes; verifier PASS, 76 tests)

**Verdict: APPROVE.** Blockers: none. Should fix: none.

- `static/js/app.js:47` reads `data-nav-size` only; defaults live solely in `theme-init.js:20–26` (criterion 5).
- `apps/core/tests.py:504–534` colour-literal test catches `rgba(`/`hsla(` and allows literals only in the first `:root { … }` palette block; a literal in the dark or `[data-nav-tone]` blocks fails (verifier proved it with a planted literal).
- Nits taken: size-radio double save removed (one `tmd-layout` write per choice); token-name test rejects value-style names (`--fs-14`, `--icon-16`); criterion-22 guard fails on literal `href="/…"`/`action="/…"`.
- Nit: `"white"` and `"clear"` in `ALLOWED_DIGIT_SUFFIX_PREFIXES` (`tests.py:547–548`) are unnecessary — drop when next touched.
- Agreed as left: display name in `user_menu.html` (D10), `current_ns` (for 005), dark boxed shadow (faithful port), `.gitignore` committed separately.
- Still open for brief 005: the public request form must override `{% block body %}` or add `is_authenticated` branches in `topbar.html`/`sidebar.html` — the 005 planner records which.

**Review (owner correction): APPROVE.** Blockers: none. Tidy-ups: the changelog line, and three lines in the Design section that still describe the old sign-in.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

- `CLAUDE.md`: **Architecture → Front end** rewritten — Origin now points at `design/f-desk/` (task 003/004) instead of the removed `design/v5-tasks/`; JavaScript describes `theme-init.js` owning the four layout settings as `window.tmdLayout`, with `app.js` reading them (no second copy) and the `tmd-layout` storage key; Icons now says Feather/MIT, one sprite partial, and the old Solar/`login.html` duplication note is removed (it's resolved). **Architecture → Templates** now describes `base.html` as the shell split into partials under `templates/partials/`, included with `only`, pages filling `heading`/`breadcrumb`/`content`, the shell assuming a signed-in user (public pages override `{% block body %}` as `login.html` does), and how a new sidebar section adds itself between `Menu` and `Administration`. **UI conventions** replaces the "provisional until a design direction is chosen" tokens note with the real rule: tokens live only in `style.css`'s first `:root` palette block, type in `rem`/geometry in `px`, the client-approved defaults (light, purple, standard, full), status as icon+word, and text sizes matching the approved reference (10.5px tags, arriving with 005) at AA.
- `README.md`: **Tech stack** table's Front end and Fonts rows updated (IBM Plex Sans, `theme-init.js`, ported from `design/f-desk/`; Nunito/Nunito Sans/Cinzel removed). New **Third-party notices** section: IBM Plex Sans (SIL OFL 1.1) and Feather icons (MIT).
- `docs/CHANGELOG.md`: new newest-first entry, **2026-09-24 — 004: The approved design becomes the app's theme**, with user-visible changes (new look, honest search/notifications placeholders, sidebar scoped to real destinations, sign-in behaviour kept) and technical notes (files, `User.initials`, `rem` tokens, role-named tokens, flash-in-flow messages, 76 tests, follow-ups for 005).
- `design/README.md`: the `f — a look-alike…` section's "Not yet ported" paragraph, now false, is replaced with "Ported, and now frozen," recording that task 004 ported the approved configuration and `f-desk/` stays as the frozen reference (D1). This file isn't one of `tmd-docs-writer`'s three owned homes, but the brief's own scope and D1 call for it, and the old wording was no longer true.

`.gitignore` was left untouched, as instructed (it is tracked as a separate, pre-existing change).

**Status:** Done — Verification is PASS (76 tests, dev and prod stacks) and Review is APPROVE (round 2), so both gates required to close are met.

**Post-close correction (D18).** `docs/CHANGELOG.md`'s 004 entry wrongly said sign-in kept "password show/hide" after D18 removed that button to match the concept exactly. Fixed: the user-visible line now says sign-in matches the concept exactly (concept help text, full-width password field, no show/hide button, no forgot-password line) and lists the three kept differences the owner approved (curly apostrophe in the error title, focus on the password box after a wrong password, username autofocus) plus the kept empty-field check. The technical notes now record the D18 file removals (the show/hide JS block, `.field__row`/`.signin__help` CSS, the `eye` sprite symbol, `docs/design/password-field.md` superseded) and the updated count, 83 tests (PASS) / APPROVE. Checked `README.md` and `CLAUDE.md` for any show/hide mention — neither one has any, so neither needed a change.
