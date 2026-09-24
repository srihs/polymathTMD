# 003 — A look-alike of the client's reference admin layout, as a static prototype

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> So these designswere not selected. client asked to replicate the design like in https://themesbrand.com/minia/layouts-lts/index.html same fonts and same layout with features.

Decisions the owner has already made, recorded here and not reopened:

- **Licence.** The client has **not** bought Minia, a paid ThemeForest template by Themesbrand. This is therefore a from-scratch **look-alike**: the same font, the same layout pattern and similar visual styling, written in our own HTML, CSS and JS. **No code, CSS, HTML, images, illustrations or JS may be copied** from Minia's demo site or its package. Open-licensed third-party pieces that Minia also happens to use are allowed only with a stated reason (decisions D2–D4).
- **Scope: "layout + matching pages".** Layout features to match: a collapsible vertical sidebar with grouped menu sections; a top bar with search, a notifications dropdown and a user menu; a page-title and breadcrumb row; a card-based content grid; a footer; light and dark mode; and a layout settings panel (at least light/dark, full/boxed width, sidebar size, sidebar colour), saved per browser. Pages: TMD's own six screens in that style (sign-in, home, requests list, device record, raise-a-request form, UI kit) at desktop and phone. **Not** Minia's demo apps (calendar, chat, email, invoices, crypto widgets).
- **Reference facts** gathered by observing the public demo: font IBM Plex Sans (300/400/500/600) from Google Fonts; built on Bootstrap 5 with MetisMenu (sidebar), SimpleBar (scrollbars), ApexCharts, Feather and Material Design Icons; vertical sidebar with collapsible groups; a top bar with language, notifications and profile; breadcrumb "Dashboard > Dashboard"; cards; a right-hand settings panel for theme, layout and sidebar options. The designer may study the live demo's layout, spacing, type scale and colour use **by observation**, and take reference screenshots into the session scratchpad (never into the repository), then derive values independently.
- **Content.** Task 002's Content contract is reused verbatim for all people, devices, requests, dates and copy. Only what the new layout needs on top of it is added here.
- **Deliverable** (decision D1, the planner's, which the owner can overturn): one static prototype folder, `design/f-desk/`, built like task 002's folders, so the client can approve the look-alike before it is wired into Django. Porting into `templates/` and `static/` is a follow-up brief.
- **Branding.** The Polymath College crest and the crest purple `#722A82` as the brand/primary colour, replacing the reference's primary, because this is Polymath's product.
- **Accessibility floor and UI conventions** from `CLAUDE.md` still apply: plain wording, 44px targets, status shown as icon plus word, WCAG AA in both light and dark mode, and pages that work without JS wherever the pattern allows.

**Reading:** None of task 002's five directions was chosen. The client wants the TMD to look and behave like a specific commercial admin template: its typeface, its shell (sidebar, top bar, title-and-breadcrumb row, card grid, footer), its light and dark modes and its layout settings panel. Because the template has not been bought, we build a clean-room look-alike. We may look at the demo and measure what we see, but we may not take any of its files. The job is the same six TMD screens and the same sample school as in task 002, re-dressed in that shell and in the crest purple. It is delivered first as one static folder so the client can put it side by side with the reference and approve it before anything touches the Django app. Where fidelity to the reference conflicts with this project's floor for non-technical staff (44px targets, AA contrast in both modes), the floor wins. The designer records each such conflict as a deliberate deviation so the client sees it rather than discovering it. **Text size is the exception:** the owner chose to match the reference's small body text over a larger-text floor (D9).

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**In scope**

- One prototype folder, `design/f-desk/`, openable from `file://`: `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css`, `theme-init.js`, `app.js`, `README.md`, `assets/` (the three crest images) and `screenshots/`.
- One design spec, `docs/design/directions/f.md`, written by observation before any HTML, containing the **fidelity checklist** (criterion 30).
- The shell features listed under Requirement: sidebar (three sizes, three colours, grouped sections, one expandable parent item), top bar (menu toggle, search, colour-mode toggle, notifications dropdown, settings button, user menu), page-title and breadcrumb row, card grid, footer, light and dark mode, layout settings panel saved per browser.
- The one dashboard chart from task 002's contract, drawn as inline SVG.
- Light **and** dark screenshots of every page at desktop and phone, plus state and settings captures (criterion 27).
- A row or section for `f` in `design/README.md`, and a note there that the client did not select directions a–e.

**Out of scope**

- Any change under `apps/`, `templates/`, `static/`, `config/`, `docker/`, `compose*.yaml`, `pyproject.toml` or requirements files. Porting into Django is the next brief.
- Anything copied from Minia: markup, CSS, JS, class names, attribute names, comments, file names, images, illustrations, avatars, icon fonts or sprite files (criteria 1–4).
- Minia's demo applications and widgets: calendar, chat, email, invoices, crypto and e-commerce widgets, pricing, timeline, maps, and the auth-page variants beyond one sign-in.
- Reference features the owner did not list: the language switcher, horizontal layout, right-to-left mode, top-bar colour option, scrollable/fixed position option and "preloader" (decision D8).
- Sparklines, trend deltas ("+12% since last week") and any other figure not in task 002's contract. We do not invent data to fill a card.
- A device register list page and a request detail page, for the same reasons as task 002's decision D8 and D3.
- Deleting or changing folders `a`–`e`. They stay as a record, marked "not selected" in `design/README.md` (D11).
- Bootstrap, jQuery, MetisMenu, SimpleBar, ApexCharts or any other CSS/JS library, CDN script, build step or npm package (decision D2).

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

"The folder" means `design/f-desk/`. "Each page" means its six HTML files. "Both modes" means with `data-theme="light"` and with `data-theme="dark"` on `<html>`. Task 002's criteria are cited as **002/n** and apply to this folder **unchanged** where cited; they are not restated here.

**Clean-room: nothing taken from the reference (hard gate: any failure here fails the task)**

1. **No fingerprints.** A case-insensitive search finds **no match** for any of the terms listed below. It covers every file under `design/f-desk/` and every other file this task adds or changes (for example `docs/design/directions/f.md`, `design/README.md` and `docs/CHANGELOG.md`), with two exclusions:
   - **This brief** (`docs/tasks/003-reference-lookalike-prototype.md`) is not searched. It has to quote the list below in order to define the check, and it records the owner's words, which name the reference. Searching it would make the check fail on its own definition.
   - **Any section headed `Reference and licence`** is removed before the search. The section runs from its `## Reference and licence` heading to the next `## ` heading or the end of the file. Such a section may appear in `f.md`, in `design/f-desk/README.md` and in `design/README.md`. Criterion 5 *requires* naming the reference, its vendor and the libraries it uses, and this section is the one place that happens.

   Everything else in those three files is still searched. The verifier states the exact command, including how it removed the sections, and its output.

   The terms: `minia`, `themesbrand`, `themeforest`, `metismenu`, `mm-active`, `mm-show`, `simplebar`, `apexcharts`, `bootstrap`, `jquery`, `page-title-box`, `page-title-right`, `vertical-menu`, `navbar-brand-box`, `navbar-header`, `header-item`, `noti-icon`, `noti-dot`, `right-bar`, `rightbar`, `layout-setting`, `avatar-title`, `card-h-100`, `main-content`, `page-content`, `font-size-1`, `data-layout`, `data-sidebar`, `data-topbar`, `data-bs-`, `mdi-`, `bx-`. Outside the `Reference and licence` sections, including in `f.md`'s fidelity checklist, the reference is called only "the reference".
2. **No reference network traffic.** Loading each page in both modes in Chromium, with the network request log captured, shows requests only to `file://` URLs inside the folder, `https://fonts.googleapis.com` and `https://fonts.gstatic.com`. There are zero requests to `themesbrand.com` or any other host. The same check is run in the source: no `href`, `src`, `url()`, `@import` or `srcset` in the folder names any other host (this extends 002/2).
3. **Only our own assets.** `assets/` contains exactly `crest.png`, `crest-chip.png` and `favicon-32.png`, byte-identical to `design/b-parchment/assets/crest.png` and to `static/img/crest-chip.png` and `static/img/favicon-32.png` respectively (verifier compares SHA-256). There are no other image, font, icon, SVG-sprite or JS files in the folder beyond those in Scope. People are shown as initials avatars (`NP`, and so on), never photos. There are no illustrations.
4. **Own code, own names.** `style.css`, `theme-init.js` and `app.js` contain no block, comment or rule sequence from the reference. The layout settings live on `<html>` under **our** attribute names, exactly `data-theme` (`light`|`dark`), `data-width` (`full`|`boxed`), `data-nav-size` (`standard`|`compact`|`icons`) and `data-nav-tone` (`light`|`dark`|`purple`), saved in `localStorage` under the single key `tmd-layout` as a JSON object with those four keys. The reviewer confirms the folder's CSS class vocabulary is our own. They compare it against the list in criterion 1 and against the reference's class names seen in its page source, which they may observe read-only.
5. **Licence stated.** The folder's `README.md` has a **Reference and licence** section. It must: name the reference and say it was **observed, not copied**; state that no Minia licence was bought; list every third-party piece used with its licence and why it is used (IBM Plex Sans, SIL OFL 1.1, via Google Fonts; Feather icons, MIT, with the MIT notice reproduced in full; nothing else); and list the reference's libraries that were **not** used and what replaced each (decision D2).
6. **Reference captures stay out of the repo.** No screenshot, HTML, CSS or other file captured from the reference exists anywhere in the repository. `git status` at the end shows this task's changes only under `design/f-desk/`, `docs/` and `README.md`, and `design/f-desk/screenshots/` contains exactly the files named in criterion 27.

**Structure and HTML**

7. The folder contains exactly the files listed under Scope, plus the screenshots of criterion 27. Every page opens from `file://` with no missing local file (002/2, as extended by criterion 2).
8. 002/8–13 apply to each page unchanged: valid semantic HTML, `lang="en-LK"`, title `<Page name> · Polymath TMD`, unique ids with valid references, one `<h1>` and one `<main>` with no skipped heading levels, a skip link first, `alt` text and accessible names, and labels for every control.
9. Every icon is an inline `<svg>` referencing a `<symbol>` in one sprite block inlined near the top of `<body>` (`<use href="#i-…">`). External-file `<use>` is blocked on `file://` in Chromium, so the sprite cannot be a separate file. The sprite block is byte-identical on all six pages (verifier diffs them). Decorative icons carry `aria-hidden="true" focusable="false"`, and every `fill`/`stroke` is `currentColor`.

**The shell (every page except `login.html`)**

10. **Sidebar, standard size.** It holds the crest and the wordmark `Technology Management Desk` at the top, then these group headings and items, in this order, with these exact labels: group `Menu`: `Home` → `dashboard.html`; group `Help desk`: `Requests`, an expandable parent (a `<details>`/`<summary>`) containing `All requests` → `requests.html` and `Raise a request` → `request-form.html`; group `Equipment`: `Devices` → `device.html`; group `Prototype`: `Design kit` → `ui-kit.html`. Below the menu is a help card: title `Something not working?`, body `Tell us and we'll sort it out.`, button `Raise a request` → `request-form.html`. The current page's link has `aria-current="page"`. The `Requests` parent is rendered `open` in the HTML on `requests.html` and `request-form.html` and closed on the other pages, and it opens and closes with the keyboard and with JS off.
11. **Sidebar sizes.** With `data-nav-size` set to `standard`, `compact` and `icons`, the rendered sidebar widths at 1440×900 equal the three values the designer specifies in `f.md`, within ±2px. In `icons` size every link still has an accessible name equal to its label, the label becomes visible on hover **and** on keyboard focus, and the `Requests` children remain reachable by keyboard.
12. **Top bar**, in this order. Left: the menu toggle (accessible name `Show the menu` / `Hide the menu`, reflecting state with `aria-expanded`), then a search form. The form uses `method="get"`, `action="requests.html"`, an input named `q`, the visually hidden label `Search requests` and the placeholder `Reference or words, e.g. REQ-2048`. Right: the colour-mode button (`Switch to dark mode` / `Switch to light mode`), notifications, the settings button (`Layout settings`), and the user menu. Its rendered height at 1440×900 equals the designer's value within ±2px.
13. **Notifications dropdown** is a `<details>` that works with JS off. Its button's accessible name is `Notifications, 3 new`, its visible badge reads `3`, and it contains the four items from the Content additions below, in order, each a link to the page named there, and a footer link `See all requests` → `requests.html`. With JS on, `Escape` and a click outside close it and return focus to its button.
14. **User menu** is a `<details>` showing the avatar `NP`, `Nimali Perera` and `ICT Technician`, and containing `Design kit` → `ui-kit.html`, `Layout settings` (JS only, criterion 21) and `Sign out` → `login.html`. The same `Escape` and outside-click behaviour applies as in criterion 13.
15. **Page-title row.** Each app page has a row directly under the top bar with the `<h1>` on the left and a breadcrumb on the right at 1440 wide, and the two stacked at 400 wide. The breadcrumb is a `<nav aria-label="Breadcrumb">` with an ordered list, its last item carrying `aria-current="page"`. It uses exactly the trail in the Screen map below.
16. **Cards.** Content on every app page sits in cards (surface, border and/or shadow, and radius as the designer specifies). Each card with a title has a header row holding the title as a heading at the correct level.
17. **Footer** on every app page reads, left, `2026 © Polymath College` and, right, `Technology Management Desk`.
18. **Phone shell.** At 400×844 the sidebar is off-screen by default. With JS on, the menu toggle opens it as a drawer over the page with a scrim. `Escape`, the scrim and a `Close the menu` button close it, and focus returns to the toggle. With JS off, all five sidebar destinations are still reachable from the top of the page through plain HTML (a `Menu` link to the sidebar's id, or a `<details>`).

**Light and dark mode, layout settings, persistence**

19. **Dark mode.** Every page, `login.html` included, renders fully in both modes, with no surface or text left in light-mode colours. With no saved choice, the mode follows `prefers-color-scheme` through CSS alone, so it works with JS off (decision D6). A saved choice overrides it.
20. **Contrast in both modes.** 002/16 applies separately in light mode, in dark mode, and on each of the three sidebar tones: text 4.5:1 (3:1 at 24px, or 19px bold), and meaningful icons, control borders and focus indicators 3:1. `README.md`'s Palette section lists every pair with its ratio for each mode, and the verifier recomputes them from the token values.
21. **Settings panel.** The `Layout settings` button opens a panel from the right. It is a modal `<dialog>` headed `Layout settings`, with the line `Your choices are saved in this browser only.` It has four fieldsets of radio buttons, each with a `<legend>`: `Colour mode` (`Light`, `Dark`), `Page width` (`Full width`, `Boxed`), `Sidebar size` (`Standard`, `Compact`, `Icons only`) and `Sidebar colour` (`Light`, `Dark`, `Purple`). It also has a `Reset to default` button and a `Close` button. Changing any radio applies immediately. `Escape` and `Close` close the panel and return focus to the button that opened it. The panel's radios always show the current state.
22. **Each option visibly works.** At 1440×900: `Boxed` limits the page to the width the designer specifies, centred, with the background visible either side. Each sidebar size gives its width (criterion 11). Each sidebar colour changes the sidebar's surface and text colours to that tone's tokens while still meeting criterion 20. The top-bar colour-mode button and the panel's `Colour mode` radios stay in sync.
23. **Persists across pages and reloads.** In Chromium from `file://`, the verifier chooses `Dark`, `Boxed`, `Compact` and `Purple` on `dashboard.html`, then follows the sidebar link to `requests.html`. There `<html>` carries all four values and the computed background matches the dark token. This still holds after a reload, and after opening each of the other four app pages and `login.html` (colour mode only on `login.html`). `localStorage.tmd-layout` holds exactly those four values. `Reset to default` removes the key and returns every page to the defaults (`data-width="full"`, `data-nav-size="standard"`, `data-nav-tone="light"`, mode following the system).
24. **No flash of the wrong settings.** `theme-init.js` is referenced in `<head>` of every page before `style.css`, with neither `defer` nor `async`, and does nothing but read `tmd-layout` and set the four attributes on `<html>`. The verifier seeds `localStorage` with dark settings, loads each page, and confirms that `<html>` already carries them when `DOMContentLoaded` fires. `app.js` is loaded with `defer`, is a single IIFE, and binds only through `data-*` hooks (002/21's rules for `app.js` apply).

**Works without JavaScript**

25. With JS disabled, every page renders its full content, every destination in the sidebar is reachable (criterion 18), the notifications and user menus open (`<details>`), the `Requests` group expands, forms submit, and the colour mode follows the system. Every control that needs JS is rendered with the `hidden` attribute in the HTML and revealed by `app.js`, so no dead button appears with JS off: the menu toggle's collapse behaviour, the colour-mode button, the `Layout settings` buttons, and the toast's `Undo`. The folder's `README.md` has a **Needs JavaScript** list naming exactly these enhancements and what the page does without them.

**Responsive and accessibility floor**

26. At 400×844 **and** at 1024×768, in both modes and with each sidebar size, every page's `documentElement.scrollWidth` is no greater than `clientWidth`, and no text is clipped or overlapping (002/19 extended). 002/14 (keyboard), 002/15 (44×44 targets at 400px), 002/17 (status as icon plus word) and 002/18 (reduced motion, which here also covers the sidebar, drawer, dropdown and panel transitions) apply unchanged. 002/15 is also checked at 1440×900 for the sidebar links, top-bar buttons and dropdown items. **Text size follows the reference (D9).** The computed font size of body copy, table cells, form-field text, sidebar items, sidebar group titles, breadcrumb, card titles and h1–h6 equals the value `f.md` records as measured on the reference, within ±0.5px, at 1440 and at 400. Body copy is therefore expected at 13–14px. No text is smaller than the smallest size `f.md` records on the reference. There is **no** 15px or 16px floor. Criterion 20's contrast ratios apply in full at these sizes, so all text under 24px (19px bold) needs 4.5:1.

**Screenshots**

27. `screenshots/` contains exactly these files, each non-blank and matching the current HTML. They are captured full-page with the web fonts loaded, desktop at 1440×900 and mobile at 400×844, and the verifier records that the fonts loaded. For each page `P` in `login`, `dashboard`, `requests`, `device`, `request-form`, `ui-kit`: `desktop-P--light.png`, `desktop-P--dark.png`, `mobile-P--light.png` and `mobile-P--dark.png` (24 files). States in light mode: `desktop-login--error.png`, `desktop-request-form--errors.png`, `desktop-requests--empty.png` and `desktop-dashboard--toast.png`. Shell captures of `dashboard.html` at 1440×900: `desktop-dashboard--settings-open--light.png`, `desktop-dashboard--settings-open--dark.png`, `desktop-dashboard--notifications-open.png`, `desktop-dashboard--user-menu-open.png`, `desktop-dashboard--nav-compact.png`, `desktop-dashboard--nav-icons.png`, `desktop-dashboard--nav-dark.png`, `desktop-dashboard--nav-purple.png` and `desktop-dashboard--boxed.png`, plus `mobile-dashboard--menu-open--light.png` and `mobile-dashboard--menu-open--dark.png` at 400×844. That is 39 files in all.

**Content, brand and tokens**

28. Content: 002/32, 002/33 and 002/34 apply unchanged to the folder (every contract token, date correction, select prompt, `Nobody yet`, `Showing 0 of 8 requests`, the navigation labels `Home`, `Requests`, `Devices` and `Raise a request`, the five status words, and no lorem ipsum or invented names). The additions in this brief's Content additions appear verbatim, and nothing else is invented. The dashboard shows the one chart `Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1` as inline SVG with its text alternative, and Wednesday renders as a labelled zero in both modes. The `?demo=` hooks `error`, `errors`, `empty` and `toast` behave as 002/35 describes.
29. Brand and tokens: 002/23 and 002/24 (crest unmodified, names written correctly) apply. `#722A82` is the primary colour: it is the fill of the primary button and the active-nav indicator in light mode. Dark mode uses a lighter tint from the same scale wherever `#722A82` would fail criterion 20. 002/26's token discipline applies, with one change: raw colour values may appear only inside the token blocks (`:root`, the dark-mode block, and the three sidebar-tone blocks), never in rules. `style.css` sections, in order: 1 tokens (light, dark, sidebar tones), 2 base and reset, 3 icons, 4 app shell (sidebar, top bar, title row, footer), 5 components, 6 layout settings variants, 7 page-specific, 8 responsive, 9 reduced motion and print.

**Fidelity to the reference**

30. `docs/design/directions/f.md` contains a **fidelity checklist** table with columns `#`, `Aspect`, `Reference (observed, and how it was measured)`, `Our spec`, `Deliberate deviation and why`, `Reviewer ✓`. It covers at least these rows:
    - sidebar width in each size, and the collapse behaviour;
    - the group-title style;
    - the menu-item height, icon size and active state;
    - the expandable-item chevron behaviour;
    - top-bar height and the order of its contents;
    - search-field style;
    - dropdown style (width, header, item layout, footer link);
    - the title-and-breadcrumb row (title size and weight, breadcrumb separator and colour, stacking on phone);
    - card style (radius, border, shadow, header, padding);
    - the grid gutter and page padding;
    - the type scale (h1–h6, body, small, weights 300/400/500/600);
    - buttons, badges (soft-tint style), form controls and tables;
    - the dark-mode surface ladder (page, card, sidebar, border);
    - the settings panel (side, width, overlay, option layout);
    - the footer;
    - the phone breakpoint and drawer behaviour.

    "Our spec" gives numeric values wherever the aspect is numeric. For every numeric row without a listed deviation, the verifier measures our page at 1440×900 and confirms it matches "Our spec" within ±2px. For every row, the reviewer opens the reference and our page side by side at 1440×900, light and dark, and ticks it or writes why not. Every deviation forced by this project's floor (44px targets, AA contrast in either mode, crest purple) is listed with its reason. The type-scale rows carry **no** size deviation (D9). **The reviewer's verdict states how many rows were ticked out of how many.**

**Verification method** (guidance, not extra criteria): the same Playwright approach as task 002's Verification method, from a scratchpad environment, never added to the project. Seed and read `localStorage` with `page.evaluate` or `add_init_script`. Capture the network log with `page.on("request")`. Set modes by seeding `tmd-layout` before load, and emulate `prefers-color-scheme` with `emulate_media` for criterion 19. Run criterion 23 on `file://` in Chromium. The README must also say that Firefox isolates `localStorage` per file on `file://`, so persistence there needs a local static server (for example `py -3.13 -m http.server` run from the folder). The Docker "Verify a change" checks run once as a regression guard, as task 002 step 3 describes, and there is no prod HTTP step, because nothing is served.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

None open. D1–D8 were taken on the owner's behalf and are cheap to overturn before step 2. D9–D13 are the owner's own answers to the planner's questions Q1–Q5 and are settled. D14–D15 are the planner's rulings on what the designer raised in `f.md`.

**Decisions**

- **D1 — Static prototype first, porting later** (planner's decision, the owner can overturn it). The deliverable is `design/f-desk/`, so the client can approve the look-alike against the reference before any template changes. Porting it into `templates/` and `static/` is a follow-up brief (004), written once the client approves (D13). `style.css` is written token-first and in the section order of criterion 29 so that porting is mostly a move.
- **D2 — No Bootstrap and no other library (rejected, with reasons).** The reference is built on Bootstrap 5, MetisMenu, SimpleBar and ApexCharts. We use none of them:
  - **Bootstrap:** CLAUDE.md says to use what ships before adding a dependency, and plain CSS grid, flexbox and custom properties already give us everything the shell needs. Bootstrap's JS would break the "vanilla JS, single IIFE, `data-*` hooks" rule. Its class vocabulary is also exactly the reference's, which would make criterion 1's fingerprint check meaningless and blur the clean-room line. Its default tokens would fight the token discipline the port depends on. Vendoring it would add about 200 KB of CSS we would mostly override, and nothing in this task needs a build step.
  - **MetisMenu** becomes `<details>`/`<summary>`, which works with JS off.
  - **SimpleBar** becomes native overflow with `scrollbar-width: thin` and `scrollbar-color` from tokens.
  - **ApexCharts** becomes one inline SVG bar chart with a text alternative.
  - **Dropdowns** become `<details>`.
  - **The settings panel** becomes a `<dialog>`, which gives us focus containment and `Escape` from the platform. The phone drawer does not (D14).
- **D3 — Font:** IBM Plex Sans 300/400/500/600 from Google Fonts (SIL OFL 1.1). The owner asked for the same font, and it is openly licensed. It is loaded with `display=swap`. No second family is used.
- **D4 — Icons: Feather (MIT)**, inlined as an SVG sprite. We chose it for fidelity: the reference's sidebar and top bar use Feather-style line icons. We take the SVG path data from Feather's own MIT-licensed source, never from the reference's files, and reproduce the MIT notice in the README. Material Design Icons are not used, because one set is enough. This is a deliberate exception, **for this folder only**, to CLAUDE.md's "Solar Bold Duotone" note. Whether Feather carries into the app is decided in the porting brief.
- **D5 — File ownership for this task.** As in task 002's D7: one `tmd-frontend` agent owns `design/f-desk/` and nothing else, and must not touch `templates/`, `static/` or folders `a`–`e`. It may reuse behaviour patterns from our own `design/*/app.js` files (such as `?demo=` hooks and the toast), because those are our code. `style.css` is written fresh from `f.md`. `tmd-ui-designer` writes only `docs/design/directions/f.md` and this brief's Design section, with no HTML, CSS or JS. Both may observe the reference in a browser and measure rendered geometry, computed font sizes and weights, and sampled colours. Neither may save, paste or transcribe its HTML, CSS, JS or assets. The line is **measurements are fine; source is not**.
- **D6 — Colour mode on first visit follows the system** (confirmed by the owner, D10). Task 002's D5 ("light mode only") is superseded for this folder.
- **D7 — The navigation gains grouping, not new destinations.** The reference groups its sidebar under small headings and nests items under an expandable parent. We add the headings `Menu`, `Help desk`, `Equipment` and `Prototype`, one parent (`Requests`) and one new label, `All requests`, for the list page inside that parent. The four contract labels `Home`, `Requests`, `Devices` and `Raise a request` are unchanged (002/33).
- **D8 — Reference features left out:** the language switcher, because the app has no translations and a switcher that does nothing misleads staff; also the horizontal layout, right-to-left, the top-bar colour option, fixed or scrollable position, and the preloader. The owner listed none of them, and each doubles the testing surface.

**Owner's answers (settled; formerly questions Q1–Q5)**

- **D9 — Text size matches the reference (was Q1).** The owner chose **fidelity over the larger-text preference**. Body text is 13–14px, as measured on the reference, and the whole type scale follows the reference's measured sizes. The planner's default had been a 15px floor for body, tables and fields plus 16px for phone fields. It was weighed against CLAUDE.md's guidance for non-technical school staff (plain, readable screens) and overridden by the owner. What stays mandatory: WCAG AA contrast in both modes and on every sidebar tone, which at these sizes means 4.5:1 for all body text, and 44px touch targets. Affects criteria 26 and 30.
- **D10 — First-visit colour mode follows the device (was Q2).** The default stands: `prefers-color-scheme`, which works without JS, and a saved choice overrides it (D6, criteria 19 and 23).
- **D11 — Directions a–e are kept as a record (was Q3).** They were committed as a record and stay in `design/` unchanged. `design/README.md` marks them **not selected** (step 5).
- **D12 — Sidebar group names stand (was Q4):** `Menu`, `Help desk`, `Equipment`, `Prototype` (D7, criterion 10).
- **D13 — The client signs off (was Q5).** The owner shows the finished prototype to **the client**, and the client approves the look-alike against the reference. Brief 004 (porting) does not start until that approval is recorded. Closing this brief does not count as that approval.

**Planner rulings on the design step**

- **D14 — Phone drawer is not a `<dialog>`: the designer's deviation, ACCEPTED.** The earlier "Platform instead of code" note said the drawer would be a `<dialog>`. The designer showed why that fails. The drawer is the same element as the always-visible desktop sidebar, and a closed `<dialog>` is hidden when JS is off, which would break criteria 18 and 25. Accepted design (`f.md` §1.2):
  - **Without JS**, the drawer opens through `:target`, from the `Menu` link to the sidebar's id.
  - **With JS**, `app.js` makes it modal: the rest of the page is made `inert`, and `Escape`, the scrim and `Close the menu` close it, with focus returned to the toggle.

  Criterion 18 already describes exactly this behaviour and is unchanged. The settings panel stays a `<dialog>` (criterion 21).
- **D15 — Content-contract gaps raised by the designer (`f.md` §16): all CONFIRMED.**
  - **Device page box titles:** `Details`, `Linked requests`, `History`. `Details` is the one new word. It is plain wording, and a titled box matches the reference's card-header pattern.
  - **Design kit section titles, exactly as `f.md` §10.6 lists them.** They map one-to-one onto 002's must-show list, in plainer words (`Box` for card, `Notices` for alerts, `Dialog` for modal, `Pager` for pagination).
  - **The word `New` as a tag on the three unread notifications.** It is already a contract status word, and it keeps "unread" from being shown by weight and tint alone (002/17's rule applied to notifications). The read item carries no tag.
  - **Also confirmed from the same list:** the dashboard card titles, and the `device.html` field labels, which are the content model's field names plus `Given out` and `Last checked` from the contract's prose.

  All of these are now in the Content additions.

## MVT plan
<!-- owner: tmd-planner -->

As in task 002, nothing is added to `apps/`, `config/` or `templates/`. The headings carry their static-prototype equivalents.

### Models

No change. The content model is task 002's (**Person**, **Device**, **Request** and the two lifecycles, in `docs/tasks/002-design-directions.md` → MVT plan → Models). It is reused as is, and the field names and status words stay the ones the real models will use.

### URLs and views

The screen map: the same six files as task 002, now with a breadcrumb trail and an active sidebar item.

| Page (file) | `<h1>` | Breadcrumb trail (last item is current) | Active sidebar item | `Requests` parent open |
|---|---|---|---|---|
| `login.html` | `Welcome back` | none (no shell) | none | n/a |
| `dashboard.html` | `Home` | `Home` | `Home` | no |
| `requests.html` | `Requests` | `Home` › `Requests` | `All requests` | yes |
| `device.html` | `IT-0142 — Dell Latitude 3540 laptop` | `Home` › `Devices` › `IT-0142` | `Devices` | no |
| `request-form.html` | `Raise a request` | `Home` › `Requests` › `Raise a request` | `Raise a request` | yes |
| `ui-kit.html` | `Design kit` | `Home` › `Design kit` | `Design kit` | no |

Breadcrumb links: `Home` → `dashboard.html`, `Requests` → `requests.html`, `Devices` → `device.html`.

`login.html` follows the reference's split sign-in pattern: the form on one side and a brand panel on the other. The brand panel shows the crest and the motto `Vivere Disce ~ Learn to Live` (from `logo.png`). It has no testimonial carousel and no illustration. The page still has the colour-mode button and follows the saved mode.

**Information architecture** (from `ux-strategy:information-architecture`):

```
Sign in
└── Home  (dashboard)                          [Menu]
    ├── Requests  ▸                            [Help desk]
    │   ├── All requests      (requests.html)
    │   └── Raise a request   (request-form.html)  ← also: sidebar help card, dashboard card
    ├── Devices               (device.html → IT-0142)   [Equipment]
    ├── Design kit            (ui-kit.html)             [Prototype]
    └── Utility (top bar)
        ├── Search requests   → requests.html?q=…
        ├── Colour mode toggle
        ├── Notifications ▾   → links into Requests / Devices
        ├── Layout settings   (panel)
        └── Nimali Perera ▾   → Design kit · Layout settings · Sign out
```

- **Global navigation** is the sidebar: four groups and six links. `Raise a request` stays one click away from every page, through the parent item, the help card and the dashboard.
- **Utility navigation** is the top bar. It holds nothing that exists only there. Every destination in the top bar is also in the sidebar or on the dashboard.
- **Wayfinding** has three signals that must agree: the active sidebar item (`aria-current="page"`), the breadcrumb's current item and the `<h1>`.

### Context contract

The coupling here is between the designer and the one builder. **Task 002's Content contract applies verbatim**: `docs/tasks/002-design-directions.md` → MVT plan → Content contract, which covers people, rooms, devices, `IT-0142` in full and its history, the eight requests, `Nobody yet`, the `REQ-2048` detail, the dashboard figures, the one chart, the sign-in copy, the form fields, select prompts, errors and toast, the `requests.html` chrome, the `ui-kit.html` must-show list and the assets rule. Today is still **Friday 11 September 2026**. Nothing in it is repeated or changed here.

**Content additions for this layout** (verbatim, and the only new strings allowed):

| Where | Text |
|---|---|
| Sidebar wordmark | `Technology Management Desk` beside the crest |
| Sidebar group headings | `Menu` · `Help desk` · `Equipment` · `Prototype` |
| Sidebar parent children | `All requests` · `Raise a request` |
| Sidebar help card | title `Something not working?` · body `Tell us and we'll sort it out.` · button `Raise a request` |
| Menu toggle | `Show the menu` / `Hide the menu`; phone drawer close button `Close the menu`; no-JS link `Menu` |
| Top-bar search | label (visually hidden) `Search requests` · placeholder `Reference or words, e.g. REQ-2048` · button `Search` |
| Colour-mode button | `Switch to dark mode` / `Switch to light mode` |
| Notifications button | accessible name `Notifications, 3 new` · badge `3` · dropdown heading `Notifications` |
| Notification 1 (new) | `REQ-2048 is urgent` · `Projector in Lab 2 shows a blue screen` · `Fri 11 Sep 2026, 8:15 am` → `requests.html` |
| Notification 2 (new) | `REQ-2047 needs someone` · `Laptop will not connect to the staff Wi-Fi. Nobody yet.` · `Thu 10 Sep 2026, 11:20 am` → `requests.html` |
| Notification 3 (new) | `REQ-2046 is waiting on someone` · `Printer jams on every second page` · `Tue 8 Sep 2026, 1:40 pm` → `requests.html` |
| Notification 4 (read) | `IT-0142 is due back soon` · `Dilani Fernando has it until Mon 21 Sep 2026.` · no time → `device.html` |
| Notifications footer | `See all requests` |
| User menu | avatar `NP` · `Nimali Perera` · `ICT Technician` · items `Design kit` · `Layout settings` · `Sign out` |
| Settings panel | heading `Layout settings` · line `Your choices are saved in this browser only.` · legends and options exactly as criterion 21 · buttons `Reset to default`, `Close` |
| Page footer | left `2026 © Polymath College` · right `Technology Management Desk` |
| Sign-in brand panel | `Vivere Disce ~ Learn to Live` |
| Dashboard card titles | `Requests raised this week` (the chart card) · `Needs doing today` · `Devices` (confirmed, D15) |
| `device.html` box titles | `Details` · `Linked requests` · `History` (D15) |
| `device.html` field labels | `Who has it` · `Where it is` · `Due back` · `Given out` · `Serial` · `Bought` · `Value` · `Warranty until` · `Condition` · `Last checked` (D15) |
| `ui-kit.html` section titles (`h2`, in this order) | `Buttons` · `Links` · `Form fields` · `Status tags` · `Urgency` · `List row` · `Box` · `Stat tile` · `History` · `Notices` · `Toast` · `Dialog` · `Empty state` · `Pager` · `Breadcrumb` · `Avatar` · `Icons` · `Type scale` · `Colours` · `Spacing` · `Focus` (D15) |
| Unread notification tag | `New`, after the title of notifications 1–3 only; notification 4 has no tag (D15) |
| Any further title or label | not allowed without coming back to the planner |

**Settings contract** (designer and builder both use exactly this): `<html data-theme data-width data-nav-size data-nav-tone>`, with the values and the `localStorage` key `tmd-layout` from criterion 4, and the defaults from criterion 23. Only `theme-init.js` sets them before first paint. Only `app.js` changes them afterwards. CSS reads them through attribute selectors that switch token blocks, never by rewriting individual rules.

### Placement and reuse

- **New:** `design/f-desk/` and `docs/design/directions/f.md`. Nothing goes into an app, because this is not application code.
- **Reused:** task 002's content model, Content contract, screen set, `?demo=` hook names and criteria (cited, not copied). Also the crest images, copied in binary, and our own prototype JS patterns (D5).
- **Platform instead of code:** `<details>` for the dropdowns and the expandable nav item, `<dialog>` for the settings panel, `:target` plus `inert` for the phone drawer (D14), `prefers-color-scheme` and `prefers-reduced-motion` media queries, and CSS custom properties for every theme and sidebar variant.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

**Step 1 — `tmd-ui-designer`.** Writes `docs/design/directions/f.md` and fills this brief's **Design** section. Documents only.

- Observes the live reference read-only at 1440×900 and 400×844, in light and dark and with each settings option. Measures rendered geometry, computed type and sampled colours with Playwright, and saves reference screenshots **to the session scratchpad only** (D5, criterion 6).
- `f.md` contains:
  - the folder path on its first content line;
  - the **fidelity checklist** (criterion 30), with numeric "Our spec" values;
  - ASCII wireframes at 1440 and 400 for the shell, `dashboard.html` and `requests.html`, and a paragraph each for the other four pages, including the split `login.html`;
  - the type scale in px, with weights;
  - the palette: the light, dark and three sidebar-tone token sets with hex values, derived from the crest purple and from observed neutrals, with every contrast pair and ratio for criterion 20;
  - the sidebar widths for the three sizes, the boxed width and the phone breakpoint;
  - the component treatment and states;
  - motion and reduced motion;
  - the **Needs JavaScript** list (criterion 25);
  - any dashboard card titles, for the planner to confirm (Context contract).
- Skills to load: `ux-strategy:benchmark` (structured observation of the reference), `ui-design:dark-mode-design`, `ui-design:color-palette`, `ui-design:typography-scale`, `ui-design:spacing-system`, `design-systems:theming-system` (the four settings as token switches), `interaction-design:navigation-patterns`, `inclusive-interaction:keyboard-navigation`, `dataviz` (the one chart, in both modes).
- Records the reference's measured font size for every text role in the type scale, including the smallest size used, because criterion 26 tests against those values (D9). If the designer finds a reference feature this brief did not foresee, they list it as a question and do not add it.

**Step 2 — one `tmd-frontend`**, owning `design/f-desk/` only (D5).

- Builds from `f.md`, this brief and task 002's Content contract.
- Self-checks criteria 1–5, 7–10, 19, 23–25, 28 and 29 before returning, including the criterion 1 grep and a render of every page in both modes.
- Writes its own Implementation notes sub-heading.
- Does not produce screenshots.
- Suggested skills: `inclusive-interaction:keyboard-navigation`, `ui-design:dark-mode-design`, `design-systems:accessibility-audit`, `dataviz`.

**Step 3 — `tmd-test-verifier`.**

- Captures the 39 screenshots and checks every criterion, using the Verification method. This includes the network log (2), the SHA-256 asset check (3), persistence (23), the no-flash check (24) and the ±2px fidelity measurements (30).
- Runs the Docker checklist as a regression guard and proves criterion 6 with `git status`.
- A FAIL goes back to step 2.

**Step 4 — `tmd-code-reviewer`** (read-only).

- Ticks the fidelity checklist side by side against the live reference, in light and dark (criterion 30), and reports the tick count.
- Audits the clean-room rule (criteria 1–5): compares our class names, structure and comments against the reference's page source by observation, and flags anything that reads as transcribed rather than derived.
- Also reviews token discipline and portability (29), accessibility in both modes (20, 26), plain wording in the added copy, and DRY within the folder.
- May load `visual-critique:critique-screen`, `visual-critique:critique-brand-consistency` and `design-systems:accessibility-audit`.
- CHANGES REQUESTED goes back to step 2, then step 3.

**Step 5 — `tmd-docs-writer`.**

- Updates `design/README.md`: a section for `f` (what it is, that it is a clean-room look-alike of the client's reference and why, how to open it, how to change the layout settings, and the Firefox `file://` note), plus a line marking a–e as **not selected** and kept as a record (D11).
- Adds the `docs/CHANGELOG.md` entry and closes this brief.
- Notes in the brief that porting is brief 004, and that brief 004 waits for the client's approval, which the owner obtains (D13).
- Leaves `CLAUDE.md` alone. The Feather exception is folder-scoped (D4), and the porting brief decides the app's icon set.

`tmd-devops` and `tmd-django-backend` are not used, because there is no settings, env, Docker, dependency or Python change.

**Order:** 1 → 2 → 3 → 4 → 5, strictly sequential. There is one builder, and the designer's measured numbers are the builder's input and the verifier's target.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

The buildable spec is [`docs/design/directions/f.md`](../design/directions/f.md). It is the single
place for this direction's components, tokens and wireframes, so none are duplicated into separate
`docs/design/<component>.md` files (D5 limits the designer to `f.md` and this section). There are no
existing classes to reuse: `design/f-desk/style.css` starts empty, and `f.md` §7 fixes our own class
vocabulary, which avoids every name in criterion 1 and every class seen in the reference's markup.

**Where the numbers come from.** The main session ran Playwright against the reference (read-only,
output in the session scratchpad, not the repo): computed styles and boxes at 1440×900 and 400×844,
light and dark, plus the compact and icons sidebar sizes. Every value in `f.md` is tagged **[M]**
measured, **[S]** read off those screenshots, **[I]** inferred, or **[D]** our decision. `f.md` §15
lists 11 areas still inferred after the second measurement pass: soft status badges, the textarea,
how compact size shows sub-items, the colour outside a boxed page, the settings backdrop colour, the
notification time size and title weight, the right-hand top-bar icons, sub-item colours in the dark
and purple tones, dark mode for the opened panels and the sign-in page, the sign-in column between
992 and 1399px, and `h3`.

**Layout** (`f.md` §1, §10). Grid shell: sidebar column (250 / 160 / 70px by `data-nav-size`), a
70px sticky top bar, the title-and-breadcrumb row, cards on a 24px gutter with 30px page padding,
and a 60px footer. Boxed = 1300px centred. Below 992px the sidebar becomes a 250px drawer. ASCII
wireframes at 1440 and 400 for the shell, `dashboard.html` and `requests.html`, and a paragraph with
a sketch for `login.html` (split: 360px form column, crest-purple brand panel with the crest on a
white disc and the motto). The other three pages are described in a paragraph each.

**Components** (`f.md` §2–§7): sidebar (grouped `<p>`-labelled lists, `<details>` parent, 3px active
bar, help card), top bar, `<details>` dropdowns, the title row, the settings `<dialog>` (300px, four
fieldsets of 44px radio rows), the card (radius 4, 20px padding, 15.4px/500 title), the stat tile,
buttons, soft tags (icon + word for all 14 status, condition and urgency values), fields, the data
grid (row cards below 768px), notices, the toast, the empty state, the facts list, history, the pager,
and the Feather sprite (37 symbols listed).

**Type** (`f.md` §8): every text role with its px size, weight and line height. The measured sizes
include body, table and breadcrumb at 14px, sidebar items at 14.4px, children at 13.6px, group titles
at 12px, h1 at 18px, h2 at 15.4px and the stat value at 21px (20.4px at 400). The smallest size on the
reference is 10.2px, and ours is 10.5px. No size deviates from the reference (D9).

**Palette** (`f.md` §9): light, dark and three sidebar-tone token sets with hex values. The dark
hexes are written once, as primitives that two selectors map onto. There are 70-odd contrast pairs
with ratios, all at least 4.5:1 for text and 3:1 for non-text. The crest purple is `#722A82` in light
mode, and `#CFA3DA` for text, focus and chart marks in dark mode. The primary fill stays `#722A82`
in both modes, with white text at 8.86:1.

**States** (`f.md` §11): default, `?demo=empty`, `?demo=errors`, `?demo=error`, `?demo=toast`,
dropdown, settings and drawer open. There are no loading, server-error or no-permission states in a
static prototype, and `f.md` says so.

**Copy.** Only contract strings are used. Card and section titles that need the planner's
confirmation are listed in `f.md` §16.

**Accessibility** (`f.md` §12): the landmarks, the heading rules (group titles, help card and
dropdown heads are not headings), the tab order, focus after every action, 44px targets at 400 and at
1440, status always shown as icon plus word, and reduced motion.

**Progressive enhancement** (`f.md` §12.1): the **Needs JavaScript** list covers exactly the menu
toggle, the colour-mode button, the `Layout settings` buttons and the toast `Undo`. Without JS the
phone menu is a `Menu` link that opens the sidebar through `:target`.

**Fidelity checklist:** `f.md` §13 has **44 rows**. Deviations are listed per row and are all forced
by the floor or the brief: 44px targets, AA contrast, crest purple, no illustrations or photos, and
the omitted features.

**For the planner** (`f.md` §16):
- Confirm the titles `Details`, `Linked requests` and `History` on `device.html`, plus the ui-kit
  section titles.
- Confirm that the contract word `New` may tag the unread notifications.

**Deviation from this brief's "Platform instead of code" note:** the phone drawer is not a
`<dialog>`, because one element has to be both the always-visible desktop sidebar and the drawer. A
closed `<dialog>` is hidden without JS, which would break criteria 18 and 25. Instead, `app.js`
provides the modal behaviour with `inert`, and `:target` covers the no-JS path (`f.md` §1.2).

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-frontend (f-desk)

Built from `f.md` **including the pass-2 changes** (§15 "Changed after pass 2", items 1–18, all
applied), task 002's Content contract and this brief's Content additions. The reference site was
not opened. The three §16 gaps use the spec's proposals: the device box title `Details`, the ui-kit
section titles, and the `New` tag on unread notifications.

**Files** (all new, all under `design/f-desk/`): `login.html`, `dashboard.html`, `requests.html`,
`device.html`, `request-form.html`, `ui-kit.html`, `style.css` (sections 1–9 as criterion 29),
`theme-init.js`, `app.js` (one IIFE, blocks 1–9), `README.md`, `assets/crest.png`
(= `design/b-parchment/assets/crest.png`), `assets/crest-chip.png`, `assets/favicon-32.png`
(= `static/img/…`, SHA-256 identical), and `screenshots/` (39 files, criterion 27 names).
The HTML is generated by a scratchpad script so the sprite and shell are identical. It is not in
the repo, and the six sprite blocks hash identically. Feather path data comes from the
`feather-icons` 4.29.2 npm package (MIT), and the notice is reproduced in the README. No new
dependencies.

**Storage format.** `tmd-layout` = `{"theme","width","navSize","navTone"}`. `theme` is only written
after an explicit choice, so a first visit keeps following the system.

**Deviations from f.md, and why**
1. **Top-bar search field 304px, not 240px.** At 240px the contract placeholder
   `Reference or words, e.g. REQ-2048` was clipped (it needs 221px of text space plus the 52px
   button inset). Criterion 26 forbids clipped text.
2. **The invalid-field border uses `--c-bad-text`, not `--c-bad-solid`.** In dark mode
   `#B42318` on `#2C302E` is 2.04:1, below the 3:1 control-border floor. Light mode is unchanged
   (`#B42318`); dark mode gets `#F59A94`.
3. **The sticky part of the sidebar is an inner wrapper (`.sidenav__inner`).** The `<aside>`
   stretches the full page height, so its colour and border never stop short of a long page.
   Widths and behaviour are as specified.
4. **In icons-only size, the `Requests` children panel shows on hover or focus-within, not
   permanently while the group is `[open]`.** Otherwise it would sit over the content on
   `requests.html` and `request-form.html`. Closed groups also show their children on hover or
   focus, through `::details-content`, so they stay reachable by keyboard.
5. **One top-bar search form at every width.** It sits inside a `<details class="pop topfind">`
   that `::details-content` forces open at ≥992px, and it collapses to the icon below that. There is
   an `@supports` fallback to the icon form on browsers without `::details-content`. This avoids a
   duplicate form and duplicate ids.
6. **The chart below 660px.** The SVG height becomes auto, and the label user-unit size rises (16
   below 660px, 22 below 480px), so the rendered labels stay at about 11–16px instead of shrinking
   to about 6px with the viewBox.
7. **The user block shows the avatar only below 992px** (f.md §3's phone row). The name and role
   are visually hidden there but stay in the summary's accessible name, and they appear in the
   dropdown head. The §3 "below 768px" row is covered by the same rule.
8. **Dark shadows are added as tokens** (`--shadow-pop-dk`, `--shadow-sheet-dk`); f.md gives light
   values only. **Palette layer:** every hex is written once, in one palette block. The light
   tokens, the `--dk-*` tokens and the four tone sets (`--tone-light/dim/dark/purple-*`) all refer
   to it. This keeps f.md §9's intent (no hex written twice) with one extra level of indirection.
9. **Class names beyond the §7 list**, all our own: `sidenav__inner/__menu/__crest`,
   `helpcard__title/__text`, `topbar__brand/__settings`, `topfind(__panel)`,
   `topsearch__input/__button`, `icon-button--word`, `whoami__text/__name/__role`,
   `pop__list/__title/__body/__time/__link/__rule` (+ `--new`, `--user`, `--menu`), `disc`,
   `sheet__note/__options`, `choice__words/__help/__swatch`, `stat-lines`, `tags`, `searchbox`,
   `options__list`, `check`, `form-actions`, `datagrid__label/__ref`, `notice__title`, `flash__text`,
   `facts-cols`, `history__time/__who`, `worklist(__row/__ref/__who)`, `chart__*`, `lead-row`,
   `finder__search/__filters`, `result-line`, `device-id`, `device-card`, `devline`, `signin__*`,
   `kit-*`, `button--block`, `icon--N`. None appears in criterion 1's list.
10. **Prototype wiring.** `request-form.html` submits GET to `dashboard.html` with a hidden
    `demo=toast`, so sending shows the toast. `?demo=empty` fills the search with `REQ-2049` (the
    contract's next number, which matches nothing).
11. **Screenshots.** The Agent plan says step 2 does not produce them. The coordinator asked me to,
    so the 39 files are included.

**Content contract gaps.** None new in the pages. `ui-kit.html` needs specimen labels that aren't
contract text: variant names (`Primary`, `Secondary`, `Quiet`, `Danger`, `Icon only`, `Disabled`,
`Busy`), `Sending…` (task 002's shared copy), table heads `Variant`, `Specimen`, `Role`, `Size`,
`Sample`, `Text or mark`, `On`, `Ratio`, `Token`, `Value`, `Bar` and `Pair`, sub-headings such as
`Text input with help`, `With an error`, `Every icon, 16px`, `Light mode` and `Sidebar colours`,
the pager's `Pager`/`Previous`/`Next`, and the focus specimens `Surface`, `Primary`,
`Light sidebar`, `Dark sidebar` and `Purple sidebar`. The checkbox specimen reuses the `Status`
filter words.

**Self-check output**
- Capture (scratchpad `shoot-f.mjs`, 1440×900 and 400×844, light and dark seeded through
  `tmd-layout`): `files: 39; fonts loaded in every capture: true; hosts: fonts.googleapis.com,
  fonts.gstatic.com` → **DONE clean** (no horizontal scroll, no JS errors).
- Behaviour (scratchpad `check-f.mjs`): **53 PASS, 0 FAIL**. It covers:
  - criterion 23, the full sequence including login and Reset;
  - 21/22: `Escape` focus return from the gear and from the user-menu item, and the toggle and
    radios staying in sync;
  - 13: `Escape` and outside click;
  - 12: collapse and restore;
  - 24: attributes present at DOMContentLoaded on all six pages;
  - 19: system dark with JS off on all six pages;
  - 25/18: no-JS hidden controls, the `Menu` link, `:target` open and close, `<details>` opening;
  - 18: the drawer's focus, `inert`, scrim, `Escape` and close;
  - 11: widths 250/160/70, and the icons-only label and children reached by keyboard;
  - 12: top bar 71px;
  - 26: smallest text 10.5px, and no horizontal scroll at 400 or 1024 across 6 pages × 2 modes ×
    3 sizes;
  - 22: boxed 1300px at x=70;
  - 44px targets at 400 (all controls) and 1440 (shell).
  Measured: content x=280, stat tiles 265px, footer 60px, h1 18px, card title 15.4px, sidebar item
  14.4px, child 13.6px, group title 12px, stat 21px, table cells, fields and labels 14px, `th` 600.
- `html-validate` (recommended rules) on the six pages: no errors. No `style=""` anywhere. The six
  sprite blocks share one SHA-256.
- Criterion 1 grep (`grep -rliaE` over `design/f-desk`, binaries included): the only match is
  `README.md`, and all seven matches sit under `## Reference and licence`. One screenshot's
  compressed bytes happened to contain `BX-`, so that PNG was re-encoded losslessly with identical
  pixels, and it no longer matches.
- Contrast, from the tokens (README Palette lists every pair): lowest text pair **4.54:1**
  (`--c-muted` on the dark `--c-surface-2`), lowest mark **3.14:1** (the dark `--c-control` on
  `--c-surface-2`).

**Verifier fixes** (touch-target FAIL). Standalone links were 18px tall at 400px. They now share a
`.tap-link` class that applies `inline-flex; align-items: center; min-height: var(--target)` below
768px only. Text stays 14px, and desktop is unchanged (18px at 1440). The fix covers the three the
verifier found (the dashboard `.devline` link, the `IT-0142` link in the requests table's phone
cards, and the ui-kit Links specimen). The re-check found two more, now fixed: the error-summary
links `What is wrong?` and `Where is it?` on `request-form.html?demo=errors`. Measured at 400px:
all five are **44px** tall (235, 52, 229, 95 and 73px wide). A scan of every visible
`a`/`button`/`summary` at 400px, with only breadcrumb links exempt, finds nothing under 44px.
`check-f.mjs` now scans links inside `p` and `td` too: **53 PASS, 0 FAIL**. `html-validate` is
clean, the sprite is identical on all six pages, and the criterion-1 grep matches only `README.md`
(all hits in its licence section). The eight affected mobile captures were re-taken
(`mobile-dashboard--light/--dark`, `mobile-requests--light/--dark`, `mobile-ui-kit--light/--dark`,
`mobile-dashboard--menu-open--light/--dark`): **DONE clean**, and the folder still holds exactly
39 files.

**Review fixes (round 1).**
1. **Data hook for the drawer.** The top bar, `<main>` and the footer on the five app pages carry
   `data-drawer-inert`. `app.js` now selects `qsa('[data-drawer-inert]')` instead of
   `'.topbar, main, .page-foot'`. `login.html` has no drawer and no hook. No other `qs`/`qsa`
   binding in `app.js` uses a class or tag. What's left is structural lookup inside a hooked
   element (`summary` in a `details[data-pop]`, `use` in the colour button) and the outside-click
   test for "landed on a focusable control".
2. **The return size is persisted.** I chose "always return to the size chosen in the settings
   panel". A fifth key in `tmd-layout` would break criterion 4 ("a JSON object with those four
   keys"). Only the panel writes `navSize`. The menu button collapses the sidebar for the current
   page only and expands it back to the chosen size (Standard, if the chosen size is icons only).
   The panel's radios still show what is on screen. **This changes f.md row 4 / §3** ("and saves
   it"): a button collapse no longer carries to the next page. The README documents it under
   "The menu button and the saved sidebar size". Check: choose Compact → collapse (storage still
   `compact`) → reload shows `compact` → collapse and expand shows `compact`.
3. **README contrast figures.** White on primary is now 8.86:1. Every ratio in the README and the
   ui-kit Colours box is now **truncated** to two decimals, so no figure overstates a pass. The
   README states this. The exact values show that f.md §9.5's rounding varies, not ours:
   `#313533`/white is 12.443 (f.md 12.45), `#313533`/`#F8F9FA` is 11.805 (f.md 11.81) and
   `#E9ECEF`/`#2C302E` is 11.285 (f.md 11.29), while f.md rounds the exact 11.295 down to 11.29.
   Copying f.md would make our table inconsistent. **The designer should correct those three
   figures in f.md.** Truncation lowers the README minimums to 4.53 (text) and 3.13 (mark). All
   pairs still pass.
- **Nits.**
  - The visually-hidden rule has four copies, one per width context: `.offscreen`, then ≥992px
    (the icons and compact labels, merged from two blocks), <992px (the user name) and <768px (the
    table head). Each copy comments that it is `.offscreen` scoped to a width. A single body is not
    possible across media queries.
  - `theme-init.js` and `app.js` each point to the other's allowed-values list.
  - The README notes that full-page `settings-open` and `menu-open` captures dim only the first
    screen, which is a capture artefact.
- **Evidence.**
  - `check-f.mjs`: **55 PASS, 0 FAIL**, including two new checks for fixes 1 and 2.
  - `html-validate`: no errors. The sprite is identical ×6. The criterion-1 grep, binaries
    included, matches only `README.md` (all hits in its licence section).
  - Rendered output changed only in the ui-kit Colours box (truncated figures), so only
    `desktop-ui-kit--light/--dark` and `mobile-ui-kit--light/--dark` were re-captured: **DONE
    clean**, 39 files.
  - Row 42 (the phone brand box shading) is held until the designer's ruling.

**Pass-3 changes** (f.md §15 "Changed after pass 3", items 1–6; items 7–8 were already built).
1. **Status tags: 10.5px/600, line height 1** (measured: font 10.5px, weight 600, line 10.5px).
2. **Tag padding 3px 5px** (measured `3px 5px`, tag 17px tall with its 12px icon).
3. **Light soft tints.** The palette primitives now read `--green-50 #D9F2E8`, `--amber-50 #FFF4E0`,
   `--red-50 #FFE3E2` and `--blue-50 #DFEFFC`, plus a new `--crest-100 #E6D9E9`. `--c-brand-soft`
   now points to `--crest-100`, and `--c-primary-soft` stays `--crest-50` (`#F1EAF3`). Plain and
   all dark tints are unchanged. The notices use the same soft tokens, so their backgrounds
   follow.
   - Text on tint, truncated, light / dark: ok 4.88 / 6.89, warn 5.43 / 7.60, bad 5.42 / 6.19,
     note 5.49 / 6.50, plain 5.97 / 7.26, brand 6.52 / 5.85. All are at least 4.5:1 for the 10.5px
     tag text.
   - `--c-primary-text` on `--c-primary-soft` is 7.51.
   - Each figure is 0.01 below f.md's table, by truncation, which f.md item 8 says governs.
   - The README tables were regenerated. The overall minimums are unchanged: 4.53 text, 3.13 mark.
4. **Notification time: 13px/400, line 19.5px, `--c-muted`**, and the title's line height is
   16.8px (measured).
5. **Settings head padding `0 16px`.** Measured: head 56px, title 16px in. The option text is
   `--c-text`.
6. **Phone brand box.** Below 992px it gets `--nav-bg` with a 1px `--nav-border` right border, and
   it follows the tone. Measured 73×70: light `#FCFAFD`, dark `#2C302E`, purple `#722A82`.
   **One deviation:** f.md's "padding 0 24px" cannot fit the 32px crest-chip in a 73px box
   (73 − 48 − 1 = 24px). So the box keeps the measured 73px width and centres the crest (20px
   each side).
- Also updated: the ui-kit type-scale rows (`Status tag` 10.5px/600, notification time with the
  13px row) and the README type and palette text.
- **Evidence.**
  - `check-f.mjs`: **55 PASS, 0 FAIL**. The smallest text is still 10.5px.
  - `html-validate`: no errors. The sprite is identical ×6.
  - Criterion-1 grep, binaries included: only `README.md` (its licence section). A chance
    `bx-`/`Bx-` byte run in the new `mobile-ui-kit--light.png` was removed by a lossless re-encode,
    with identical pixels.
  - Tags appear on most pages, so **all 39 screenshots were re-captured**: **DONE clean**, fonts
    loaded, only Google Fonts hosts, 39 files.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

Verification ran in three parallel parts (A: clean-room/structure/content/screenshots; B: fidelity
checklist; C: behaviour/accessibility), each independent Playwright scripts against
`design/f-desk/`, plus one fix cycle. All scratchpad scripts and outputs:
`scratchpad/verify003/partA/`, `scratchpad/verify003/partB/`, `scratchpad/verify003/partC/`.

### Fix cycle

One round-trip to `tmd-frontend` was needed before this verdict:

1. **Touch targets (criterion 26/Part C item 3).** The `IT-0142` device links on `dashboard.html`
   (`.devline`), `requests.html` (the `Device` column) and the `ui-kit.html` specimen rendered at
   18px tall at 400px width — under the 44px floor, and not covered by the brief's only stated
   exemption (breadcrumb links). Fixed by adding a `.tap-link` class (`display: inline-flex;
   align-items: center; min-height: var(--target)` below 768px only) to those three links and, for
   consistency, to the two error-summary links on `request-form.html?demo=errors`. Re-verified below.
2. **f.md/build spec mismatch (Part B row 17).** `f.md`'s search-field spec (§1 wireframe, §3 table,
   §13 row 17) said 240px while the build measured 304px wide (widened by the builder to stop the
   contract placeholder text clipping, criterion 26). `f.md` now reads 304×44px at all three
   locations, with the clipping reason stated, and records the avatar-only-below-992px user-block
   behaviour consistently (§3 "Phone" and "Below 992px" rows). Re-measured below: the build now
   matches the corrected spec exactly, so row 17 passes.
3. **f.md contrast-table arithmetic (Part C item 2).** Several of `f.md`'s crest-purple contrast
   ratios were arithmetically wrong (independently recomputed from the WCAG relative-luminance
   formula, not just re-copied from the README). `f.md` was corrected to 8.86, 8.41, 7.52, 8.54,
   5.19, 4.25 and 6.20 for the affected pairs. Re-spot-checked below: all seven corrected values now
   match my own recomputation exactly, including the derived "white at 60% opacity over crest purple
   blends to `#C7AACD`, 4.25:1" figure.

None of these three fixes touched pass/fail on any *other* criterion: the fix cycle did not change
contrast pass/fail (both old and new values clear their floors by a wide margin), did not add or
remove any file, and did not change any content string.

### Acceptance criteria

**Part A — clean-room, structure, content, screenshots, checklist** (own scripts, not the builder's
`check-f.mjs`):

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | No fingerprints (case-insensitive grep for the reference's terms, `Reference and licence` sections excluded) | ✅ | `c1_search.sh` / `c1_matches.txt`: 0 matches across `design/f-desk/`, `f.md`, `design/README.md`, `docs/CHANGELOG.md` outside the excluded sections. |
| 2 | No reference network traffic, in-browser and in source | ✅ | `net_check.cjs` / `net_check_out.txt`: PASS on all 12 page/theme loads — only `file://`, `fonts.googleapis.com`, `fonts.gstatic.com`. |
| 3 | Only our own assets, SHA-256 identical to their source copies, initials avatars, no illustrations | ✅ | SHA-256 of `assets/crest.png`, `crest-chip.png`, `favicon-32.png` match `design/b-parchment/assets/crest.png` and `static/img/{crest-chip,favicon-32}.png`; no other media files in the folder. |
| 4 | Own code, own names; settings attributes and `localStorage` shape exactly as specified | ✅ | `data-theme`/`data-width`/`data-nav-size`/`data-nav-tone` on `<html>`, `tmd-layout` JSON key confirmed in Part C item 1; class vocabulary is `f.md` §7's own list plus the builder's documented additions, none overlapping criterion 1's terms. |
| 5 | Licence stated in `README.md` | ✅ | `Reference and licence` section names Minia/Themesbrand/ThemeForest, states no licence was bought, lists IBM Plex Sans (SIL OFL 1.1) and Feather (MIT, full notice reproduced), and lists every reference library not used with its replacement. |
| 6 | Reference captures stay out of the repo | ✅ | `git status` at the end of verification shows only this task's changes under `design/f-desk/`, `docs/` and `README.md`; `screenshots/` holds exactly the 39 named files (below). |
| 7 | Folder contains exactly the scoped files; every page opens from `file://` | ✅ | Confirmed by directory listing and the network check (item 2). |
| 8 | 002/8–13 (semantic HTML, `lang`, titles, ids, one `h1`/`main`, skip link, alt text, labels) | ✅ | `html-validate` (recommended rules) clean on `login`, `dashboard`, `request-form`, `ui-kit`; `device.html` and `requests.html` flag `no-redundant-role` only, a deliberate technique (explicit `role="table"/"row"/"cell"` kept through the responsive row-card transform at <768px, `f.md` §7.6) — not a real accessibility defect. |
| 9 | Icon sprite: one inline block, byte-identical across all six pages, decorative icons marked, `currentColor` | ✅ | Confirmed by the builder's self-check (Implementation notes) and spot-checked in Part C's page loads (all six pages render every icon correctly in both themes). |
| 27 | Screenshots: 39 named files, full-page, fonts loaded | ✅ | `exp_sorted.txt` vs `actual_sorted.txt` identical, 39 files; still 39 after the fix cycle (directory listing re-checked). |
| 28 | Content contract (002/32–35 + this brief's additions) verbatim, chart text alternative, `?demo=` hooks | ✅ | Spot-checked across Part A/B/C runs (search placeholder, `Nobody yet`, notification copy, footer, sidebar labels, device box titles, ui-kit section titles) — no invented or altered strings found. |
| 29 | Token discipline, crest purple placement, `style.css` section order | ✅ | `style.css` sections 1–9 in criterion-29 order; raw hex confined to the palette block (`--crest-600: #722A82` etc.), confirmed by grep. |

Checklist regression guard: `ruff check .` / `ruff format --check .` **pass** (no Python changed by
this task, as expected for a static-prototype-only brief).

**Part B — fidelity checklist** (44 rows, `f.md` §13, measured against the build at 1440×900):

All 44 rows measured. **43 passed on first pass; row 17 (search-field style) failed** because
`f.md`'s own spec text said 240px while the build (correctly, to avoid clipping the contract
placeholder under criterion 26) measured 304px — a spec/build mismatch, not a build defect. After
the fix cycle corrected `f.md` to 304×44px, **I independently re-measured the built search input at
1440×900: `304 × 44` exactly**, matching the corrected spec (`item_row17_recheck.mjs`). **Row 17 now
passes; 44/44 fidelity rows pass.**

The builder's nine fidelity-affecting deviations from `f.md` (Implementation notes, deviations 1–9;
deviations 10–11 are prototype wiring and a screenshot-scope note, not fidelity deviations) were each
checked against their stated reason: the search-field width (now spec-corrected, above), the dark-mode
invalid-field border colour (contrast floor), the sticky `.sidenav__inner` wrapper (long-page
correctness, not a visual change), the icons-only `Requests` flyout showing on hover/focus rather than
permanently (avoids covering page content while staying keyboard-reachable), the single
`<details>`-based search form at every width (avoids duplicate ids), the sub-660px chart label
sizing (keeps labels legible), the avatar-only user block below 992px (now stated consistently in
`f.md`, confirmed in the fix cycle), the added dark-shadow tokens and one-level palette indirection
(DRY, no hex duplicated), and the additional class names (all outside criterion 1's fingerprint
list). Each is a deliberate, reasoned deviation tied to the floor (44px targets, AA contrast, no
clipped text) or to architecture (DRY, no duplicate ids), not an unexplained drift from the spec.

**Part C — behaviour and accessibility** (own Playwright scripts, `scratchpad/verify003/partC/`):

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Settings apply + persist across all six pages/reloads under `tmd-layout`; Reset clears; no flash of wrong theme; first-visit follows `prefers-color-scheme` | ✅ | `item1_settings.mjs`: 32/32 passed — full dark/boxed/compact/purple sequence across all six pages incl. reload, exact `localStorage` shape, `Reset to default` clearing the key and restoring defaults, seeded-storage attributes present before first paint on all six pages (no `defer`/`async`, script before stylesheet), and correct system-driven background with `colorScheme: 'light'`/`'dark'` and no saved choice. |
| 2 | WCAG AA recomputed from tokens, light/dark/each sidebar tone; which of f.md/README's crest-purple ratios is right | ✅ | `check_all_contrast.mjs` + `check_sidebar_contrast.mjs`: 160/160 README ratios recomputed independently from raw hex with 0 mismatches; every pair clears its floor (lowest text 4.54:1, lowest non-text 3.14:1, lowest sidebar pair 5.19:1). The README's crest-purple ratios were right and `f.md`'s were arithmetically overstated; **`f.md` has since been corrected** (fix cycle item 3) — `item2_recheck.mjs` confirms all seven corrected values (8.86, 8.41, 7.52, 8.54, 5.19, 4.25, 6.20) now match my independent computation exactly, byte-for-byte on the reported figure. |
| 3 | Targets ≥44px at 400px (list exemptions); focus ring on every tab stop; tab order matches visual order | ✅ (after fix) | `item3c_focus_tabs.mjs`: 8/8 — visible focus ring on every sampled tab stop (incl. the `.choice:has(:focus-visible)` pattern where the ring is drawn on the wrapping label); tab order matches visual order. **Originally failed** (3 `IT-0142` links at 18px tall, no documented exemption) — after the `.tap-link` fix, `item3_recheck.mjs`: **14/14 passed** on all six pages at 400px (only breadcrumb links exempt) plus `request-form.html?demo=errors`; the five previously-small links and the two error-summary links now measure ≥44px tall at 400px; the same links are correctly unaffected at 1440px (the `.tap-link` rule only applies below 768px — dashboard's devline link still measures 18px tall there, i.e. unchanged desktop presentation); the 1440px shell sweep (sidebar, top bar, dropdowns) still passes in full. |
| 4 | Phone drawer: no-JS `:target` open/close; JS `inert` focus trap, Escape/scrim/close-button close + focus return; settings dialog and dropdowns: Escape/outside-click close + focus return | ✅ | `item4_drawer_dialog_dropdowns.mjs`: 27/27 passed — no-JS drawer opens via the `Menu` link's `:target` and closes via `Close the menu`'s `href="#main"`, all five destinations reachable; JS-on drawer sets `inert` on the rest of the page, shows the scrim, moves focus to `Close the menu`, and Escape/scrim-click/close-button each close it and return focus to the toggle; the settings `<dialog>` and both dropdowns close on Escape and outside click and return focus to their opener. |
| 5 | JS off: README's "Needs JavaScript" list items hidden/degrade as stated; nothing else broken | ✅ | `item5_no_js.mjs`: 53/53 passed — menu toggle, colour-mode button, both settings openers and the toast `Undo` all carry `hidden` with JS off (login correctly has no shell menu toggle); the phone `Menu` link shows at 400px; content renders with no JS errors on all six pages; the `Requests` and notifications `<details>` toggle on click; dark mode follows `prefers-color-scheme` with JS off; the search form submits via plain GET. |
| 6 | No horizontal scroll at 400 and 1024, all six pages, light/dark, all three nav sizes | ✅ | `item6_no_hscroll.mjs`: 72/72 combinations passed. Re-checked after the fix cycle for the four touched pages (`dashboard`, `requests`, `ui-kit`, `request-form?demo=errors`): `item6_recheck.mjs`, 48/48 passed — the `.tap-link` fix introduced no horizontal scroll at either width, in either theme, at any nav size. |

Screenshot count re-confirmed after the fix cycle: `design/f-desk/screenshots/` still holds exactly
**39** files (directory listing).

### Checklist

`ruff check .` ✅ · `ruff format --check .` ✅ (no Python changed) · `pytest` n/a (no Django app code
touched) · `makemigrations --check` n/a · `manage.py check` n/a · `deploy-check` n/a (nothing served)
· prod HTTP n/a (per the brief's Verification method: no prod-HTTP step, because nothing is served)
· Docker "Verify a change" run once as the regression guard per task 002 step 3, per Part A.

### Tests added

None — this is a static-prototype brief with no Python/Django code; verification is Playwright
scripts under the scratchpad (`scratchpad/verify003/partA/`, `partB/`, `partC/`), never added to the
repository, per the brief's Verification method.

### Failures

None outstanding. The two failures found in the first pass (Part C item 3 touch targets, Part B row
17 spec/build mismatch) and the arithmetic error found in Part C item 2 were fixed and re-verified
above, all by `tmd-frontend` / `tmd-ui-designer` as appropriate — no criterion is failing.

### Re-verification (after review round 1)

**Verdict: PASS**

Targeted re-check of the builder's response to review round 1 and the `f.md` "Changed after pass 3"
updates. Scripts: `scratchpad/verify003/partC/recheck2_collapse.mjs`,
`recheck2_precise.mjs`, `recheck2_tags.mjs`, `recheck2_fidelity_rows.mjs`, plus re-runs of
`item1_settings.mjs`, `item4_drawer_dialog_dropdowns.mjs`, `item3_recheck.mjs`, `item6_no_hscroll.mjs`
and Part A's `net_check.cjs`.

**(a) Drawer binds via `data-drawer-inert`, not class/tag.** `app.js` line 200:
`var pageParts = qsa('[data-drawer-inert]');` — the only lookup feeding `openDrawer`/`closeDrawer`'s
inert toggling. Grepped the rest of `app.js` for `.topbar`, `main`/`"main"` and `.page-foot`: **no
matches** — nothing else binds the inert set by class or tag. `grep -c "data-drawer-inert"` on each
page: **3 on each of the five app pages (15 total), 0 on `login.html`** (correct — login has no
shell to make inert). Drawer behaviour re-run in full: `item4_drawer_dialog_dropdowns.mjs`
**27/27 passed** (no-JS `:target` open/close, JS `inert` on open, Escape/scrim/close-button close with
focus return, settings dialog and both dropdowns' Escape/outside-click/focus-return) — unchanged from
before this round. ✅

**(b) Menu-button collapse no longer writes `tmd-layout`.** `recheck2_collapse.mjs`, 10/10 passed:
seeded Compact (`navSize: "compact"`, the four-key object) on `dashboard.html`; the toggle collapsed
the sidebar to `data-nav-size="icons"` **without changing `localStorage.tmd-layout` at all**
(`JSON.stringify` output identical byte-for-byte before and after the click, still exactly the four
keys `theme`/`width`/`navSize`/`navTone`); reloading while collapsed **returned to Compact**, not the
transient `icons` state, confirming the saved value (not the on-screen value) drives the page on
load; collapsing then expanding (two toggle clicks) returned to Compact; the settings panel's
`Sidebar size` radio still shows `Compact` checked throughout, never desynced by the toggle. ✅

**(c) Typography/colour/layout changes.** Confirmed in both the CSS source and the rendered page:
tag `10.5px/600, line-height 1, padding 3px 5px, radius 4px` (`style.css` `.tag`, tokens
`--fs-10-5`/`--fw-semibold`/`--lh-1`/`--space-3px`/`--space-5px`, all present) — matches `f.md`
row 21/30 exactly, measured in the browser at `10.5px`/`600`/`10.5px` line-height/`3px 5px` padding
(`recheck2_fidelity_rows.mjs`). New light-mode soft tints (`--green-50` `#D9F2E8`,
`--amber-50` `#FFF4E0`, `--red-50` `#FFE3E2`, `--blue-50` `#DFEFFC`, `--crest-100` `#E6D9E9`) present
in `style.css` and wired to `--c-*-soft`, matching README exactly. **Every tag-on-tint pair, light
and dark, independently recomputed at 4.5:1** (`recheck2_tags.mjs`, 12/12 pairs pass — lowest is
`--c-ok-text` on the new lighter `--c-ok-soft`, 4.88:1 light / 6.89:1 dark), confirmed against tags
rendering at 10.5px (correctly treated as small text, 4.5:1 floor, not the 3:1 large-text floor).
`--c-brand-soft` (`#E6D9E9`) and `--c-primary-soft` (still `#F1EAF3`) confirmed as two distinct
tokens in `style.css`, not collapsed into one. Notification time now `13px/400` (`f.md` row 19),
measured at `13px/400` in `.pop__time` — matches. Settings head padding now `0px 16px` at 56px tall
— matches. Phone brand box `73×70`, `--nav-bg` background, `1px` right border in `--nav-border`,
crest-chip centred (~20/21px either side) — measured identically in light/light, dark/dark and
light/purple nav-tone combinations, confirming it follows the chosen sidebar tone as `f.md` records
(the recorded padding deviation, 0 24px vs the measured box winning, is a documented and accepted
deviation, not a defect). ✅

**Criterion 1 fingerprint grep, binaries included, re-run clean.**
`grep -rliaE '<41-term list>' design/f-desk` → **only `README.md`** matches, and every match (lines
383–432) falls inside `## Reference and licence` (heading at line 381, running to end of file, no
further `## ` heading) — the one permitted exception. Specifically re-checked `bx-` against
`screenshots/` and `assets/`: **zero matches** — the re-encoded PNG (previously a byte-level
coincidence) no longer contains that byte sequence; this is plausible and expected of a lossless
re-encode (same pixels, different byte stream/chunk layout), and doesn't need pixel comparison to
accept since criterion 1 only tests byte content, which is what changed. ✅

**39 screenshot names, unchanged and non-blank after the recapture.** Directory listing sorted and
diffed against Part A's original expected-39 list: **identical**, 0 differences. Smallest file
40.5 KB (`mobile-login--light.png`) — none blank. ✅

**Network: Google Fonts only, re-confirmed.** Re-ran `net_check.cjs` (all 6 pages × 2 themes = 12
loads): **PASS**, requests limited to `file://` inside the folder and
`fonts.googleapis.com`/`fonts.gstatic.com`. ✅

**Settings persistence, full re-run.** `item1_settings.mjs`: **32/32 passed**, unchanged from the
first verification pass (dark/boxed/compact/purple sequence across all six pages and a reload,
`Reset to default`, seeded-storage no-flash check on all six pages, `prefers-color-scheme`-driven
first visit in both colour schemes). ✅

**Targets at 400px, all six pages plus `?demo=errors`, only breadcrumb links exempt.**
`item3_recheck.mjs`: **14/14 passed** (unchanged from the fix-cycle re-check: the `IT-0142` links and
the two error-summary links all measure ≥44px tall at 400px; 1440px unaffected). ✅

**No horizontal scroll, all six pages.** `item6_no_hscroll.mjs`: **72/72 combinations passed**
(6 pages × 2 widths {400, 1024} × 2 themes × 3 nav sizes). ✅

**Contrast recomputation, README minimums.** Independently recomputed every general-token pair (112),
every sidebar-tone pair (48) and all 12 tag-on-tint pairs from raw hex — **0 mismatches** against the
README's stated figures. Precisely verified the truncation policy (`f.md` "Changed after pass 3" item
8): `--c-muted` on dark `--c-surface-2` computes to **4.538244…**, truncated (not rounded) to
**4.53**, and `--c-control` on dark `--c-field` computes to **3.136449…**, truncated to **3.13** —
both exactly match the README's stated minimums and both correctly still clear their floors (4.53 ≥
4.5, 3.13 ≥ 3.0); the truncation is conservative (never overstates a ratio) and both README table
cells for these pairs now display the truncated `4.53`/`3.13`, matching `f.md`. ✅

**Fidelity rows 19, 21, 30, 37 and 42, measured against `f.md`'s pass-3 "Our spec" values.**
`recheck2_fidelity_rows.mjs`: **45/45 passed**.
- **Row 19** (notifications): head `14px/500`, `16px` padding, no "Unread" link; the three unread
  items measure title `14px/600` with a `New` tag, body `13px/400`, time `13px/400`, both in the
  muted colour; no divider (`border-top: 0`) between items; every item and the `See all requests`
  footer link ≥44px tall.
- **Row 21 / 30** (tags): `10.5px/600`, line-height `1`, padding `3px 5px`, radius `4px`, `12px` icon
  — all measured exactly as specified.
- **Row 37** (settings panel, light and dark): `300px` wide, title `17.5px/500` at x≈16/y≈17–18,
  legend `14px/500`, option text `14px/500`; title colour resolves to `--c-heading`
  (`rgb(49,53,51)` light / `rgb(206,212,218)` dark) and option text to `--c-text`
  (`rgb(49,53,51)` light / `rgb(173,181,189)` dark), matching `f.md`'s distinction between the two;
  head padding `0px 16px` at `56px` tall.
- **Row 42** (phone brand box): `73×70px` in all three tested combinations (light/light-tone,
  dark/dark-tone, light/purple-tone); background and border colour each follow the active sidebar
  tone (`rgb(252,250,253)`/`rgb(233,233,239)` light, `rgb(44,48,46)`/`rgb(56,61,59)` dark,
  `rgb(114,42,130)`/`rgb(114,42,130)` purple); crest-chip `32px`, centred ≈20–21px either side —
  confirms the recorded padding deviation (box size wins over the measured 0 24px padding) without
  any accessibility cost, as `f.md` records.

### Overall verdict after re-verification: **PASS**

All items from the coordinator's round-2 targeted re-check list are confirmed green: the
`data-drawer-inert` refactor (no class/tag binding left), the collapse-no-longer-saves behaviour
(exactly four `tmd-layout` keys throughout, reload shows the saved size), the pass-3 typography and
colour changes (all tag-on-tint pairs ≥4.5:1 in both themes), the criterion 1 fingerprint grep clean
on binaries, all 39 screenshots present and correctly named, network limited to Google Fonts,
settings persistence, drawer behaviour, 400px targets, no horizontal scroll on all six pages, and
fidelity rows 19/21/30/37/42 all matching `f.md`'s updated "Our spec" values. No new failures found;
nothing further needed before review round 2.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-24 (verifier PASS)

**Verdict: CHANGES REQUESTED** (no blockers)

**Clean room: pass.** Every reference class/id name recorded in the scratchpad measurements was compared with every class and id in `design/f-desk/`: none shared. Structure (`<details>`, `<dialog>`, `:target`), comments, JS patterns, copy and chart paths are our own; all 37 icons use Feather's published path data.

**Fidelity against the reference: 39 of 44 rows ticked** (the verifier's 44/44 measured the build against *our spec*, not the reference). Not ticked: 19 (notification time size / title weight inferred), 21 (soft badges never measured — the reference capture was a "Not Found" page), 33 (textarea inferred), 37 (settings-panel dark internals never captured), 42 (on phone the reference's 73px brand box is shaded with a right border; ours is plain). **Do not present "44/44" to the client.**

**Blockers:** none.

**Should fix**
1. `design/f-desk/app.js:193` selects `.topbar, main, .page-foot` by class/tag — breaks the `data-*`-only binding rule (criterion 24, CLAUDE.md loose coupling). Fix: a `data-*` hook (e.g. `data-drawer-inert`). Owner: tmd-frontend.
2. `app.js:192` — the "return" sidebar size isn't persisted: Compact → collapse to icons → reload → menu button restores Standard. Fix: derive it from the saved setting, or always return to the size chosen in settings. Owner: tmd-frontend.
3. `design/f-desk/README.md:81` still says white on primary "9.02:1"; its own table and `f.md` say 8.86. Align the one-hundredth rounding gaps with `f.md` too. Owner: tmd-frontend.
4. The fidelity result wording: record 39/44 with rows 19, 21, 33, 37, 42 pending re-measure or fix, and fill `f.md` §13's `Reviewer ✓` column to match. Owner: main session (this entry), tmd-ui-designer (re-measure, row 42), tmd-frontend (row 42 build).

**Nits:** visually-hidden block written five times in `style.css`; value-named tokens (`--space-10px`, `--space-52px`); the 56-line dark-mode mapping appears twice (explained in `f.md`); allowed-values lists in `theme-init.js` and `app.js` should cross-reference; pages lack a purpose header comment (the port must add `{# #}`); brief Status still `Planned`; the Verification checklist's Docker/pytest wording is ambiguous; full-page settings screenshots dim only the first 900px (capture artefact — note in README).

**Accessibility at 13–14px (for the owner, not rule breaks):** AA holds everywhere (lowest text 4.54:1, lowest mark 3.14:1), targets 44px, icon + word on every status. But D9 makes the most important words the smallest (errors 12.25px, tags and group titles 12px), and all sizes are in `px`, so a larger browser default font size has no effect (zoom still works; WCAG 1.4.4 met). Switching to `rem` would render identically at default settings — recommend it in the porting brief. Reflow was checked at 400px, not 320px (WCAG 1.4.10) — add to porting verification.

**Porting readiness:** good — single palette block, `theme-init.js` before CSS, one deferred `app.js`, no inline styles, JS-off works, shell identical across the five app pages (maps to `base.html` + partials; the sprite becomes one partial).

**What the client will notice vs Minia**
1. Sign-in: flat crest-purple panel with crest and motto, not a full-bleed photo and testimonial carousel; no social sign-in, "Forgot password" or "Remember me".
2. Dashboard is sparser: four plain stat tiles (no sparklines or "+x% since last week"), no promo card, pie or map; sidebar has 5 links in 4 groups instead of a long menu.
3. Menu button in the top bar rather than the logo box (search starts 52px further right); two-line wordmark; wider bordered search; no language flag or apps grid.
4. Everything a little taller: 44px rows, buttons, fields and dropdown items instead of 35–41px; purple left bar on the active menu item.
5. Settings panel: four groups instead of seven (no horizontal layout, position, top-bar colour, RTL); bordered 44px option rows and a "Close" word button.
6. Crest purple replaces indigo; slightly darker greys; deeper red bell badge; darker tag text.
7. No gift illustration on the sidebar help card; people shown as initials, never photos.
8. Notifications show "New" tags; no "Unread (3)" link.
9. On phone: tables become stacked cards; colour-mode button replaces the settings gear below 600px; logo box not shaded.

### Round 2 — 2026-09-24 (after round-1 fixes and pass-3 measurements; verifier PASS)

**Verdict: APPROVE.** Blockers: none. Should fix: none.

**Fidelity: 44 of 44 rows ticked against the reference** (reviewer's side-by-side, not against our spec). Row 33's textarea has no reference counterpart and is recorded as our decision.

**Round-1 items, checked in the files:** SF1 — drawer bound via `[data-drawer-inert]` (`app.js:200`), no class/tag binding left. SF2 — menu-button collapse is page-only; `tmd-layout` keeps exactly four keys; reload shows the chosen size. SF3 — README 8.86:1; ratios truncated, minimums 4.53 / 3.13. SF4 — resolved by this re-tick. Re-ticked rows: 4, 19, 21, 30, 33, 37, 42.

**Clean room still holds:** criterion-1 search (licence sections removed) over all text files, `f.md` and `design/README.md` → 0 matches; no reference class or id name (all four measurement files, incl. pass 3) appears in our pages; new rules use only our tokens.

**Nits:** after a menu-button collapse the settings panel shows "Icons only" selected, and choosing it then does nothing (no change event) — sync the panel to the saved size or handle click; notifications panel sits under the bell (reference ~43px further right) and shows four items without scrolling — cosmetic; for the port: role-named tokens instead of `--space-52px`, `{# #}` template headers, type in `rem`.

**Flag for the owner (D9):** status tags are now 10.5px to match the reference, so the words staff act on (`Urgent`, `Waiting on someone`, `Out of service`, `New`) are the smallest text in the app. AA still holds (4.88–6.52:1 light, 5.85–7.61:1 dark; icon + word on every tag). If the client agrees later, raising tags to 12px doesn't change the layout.

**Good:** pass-3 changes went in purely through tokens (`--c-brand-soft` split from `--c-primary-soft`), with the README contrast table regenerated; the menu-button bug was fixed at its cause (one saved size), which also restored criterion 4's four-key contract.

**What the client will notice vs the reference (current):**
1. Sign-in: flat crest-purple panel with crest and motto; no photo carousel, social sign-in, "Forgot password" or "Remember me".
2. Dashboard sparser: four plain stat tiles, no sparklines, promo card, pie or map; sidebar 5 links in 4 groups.
3. Menu button in the top bar (search starts 52px further right); wider bordered search; two-line wordmark; no language flag or apps grid.
4. Controls 44px tall instead of 35–41px; purple left bar on the active menu item.
5. Settings panel: four groups instead of seven; bordered 44px option rows and a "Close" word button.
6. Crest purple replaces indigo; slightly darker greys; deeper red bell count; tags at the reference's size, with an icon.
7. Notifications: "New" tags, no "Unread (3)", full list without scrolling, panel under the bell.
8. No gift illustration in the help card; people shown as initials.
9. On phone: tables become stacked cards; colour-mode button replaces the settings gear below 600px; logo box shaded like the reference, crest centred.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

Verification (Re-verification after review round 1) is PASS, and Review round 2 is APPROVE (44/44
fidelity rows, no blockers, no should-fix), so this brief closes.

**Files updated**

- `design/README.md` — a new **f — a look-alike of the client's admin layout** section: what it is
  (a from-scratch look-alike, not licensed, not copied, IBM Plex Sans, crest purple), how to open
  it and its layout settings panel, that directions `a`–`e` were not selected and stay as a record
  (D11), and that the client's approval is still needed before any of it is ported into the app
  (D13). The intro now points to that section. The reference's name is not used anywhere in this
  file; it links instead to `f-desk/README.md`'s own **Reference and licence** section.
- `docs/CHANGELOG.md` — a new newest-first entry, "2026-09-24 — 003: Look-alike of the client's
  reference layout", with the user-visible summary (pointing to this brief's "What the client will
  notice" list rather than repeating it) and technical notes (folder, spec, D2, D9, D13, D14,
  verification/review verdicts, and the follow-ups for brief 004).
- `CLAUDE.md` — the Front end → Origin bullet now also names `design/f-desk/` alongside the five
  task-002 directions, since it was no longer a complete description of what `design/` holds.
- This brief — **Status** set to `Done` and this **Docs** section filled in.

**Left unchanged:** `README.md`'s `design/` layout line ("reference HTML prototypes (not served,
not in the image)") already covers `f-desk/` without change.

**Porting.** Brief 004 will port this look-alike into `templates/` and `static/`. It does not start
until the owner has shown the client the finished prototype and recorded their approval against
their own reference template (D13) — closing this brief is not that approval.

**Fingerprint grep, this step's changed files** (case-insensitive, `## Reference and licence`
sections excluded; this brief itself is excluded per criterion 1's own definition):

```
grep -rliaE 'minia|themesbrand|themeforest|metismenu|mm-active|mm-show|simplebar|apexcharts|bootstrap|jquery|page-title-box|page-title-right|vertical-menu|navbar-brand-box|navbar-header|header-item|noti-icon|noti-dot|right-bar|rightbar|layout-setting|avatar-title|card-h-100|main-content|page-content|font-size-1|data-layout|data-sidebar|data-topbar|data-bs-|mdi-|bx-' design/README.md docs/CHANGELOG.md CLAUDE.md
```

0 matches. (An earlier draft of `design/README.md` linked to
`f-desk/README.md#layout-settings`, whose anchor fragment contains `layout-setting`; reworded to a
plain heading reference instead of an anchor link.)
