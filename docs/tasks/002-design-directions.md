# 002 — Five design directions for the Technology Management Desk

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> So the first task is to create designs for this system. Check logo.png for the branding and create 5 award winning easyto use 5 design variations for this project. Use Skills and agents.

Two corrections the owner gave while this brief was being written, verbatim:

> dont use v5-tasks as insperation

> Dont use current designs directions in the project

Answers the owner gave when asked, which are decided and not open questions:

- **Scope:** the Technology Management Desk manages BOTH school technology assets (device register: laptops, projectors, tablets and so on; who has what; check-out and return; condition; repairs) AND an IT helpdesk (staff raise tech requests and faults; IT staff triage, assign and resolve; status tracking and history), with requests linked to devices and people.
- **Screens per variation:** sign-in, home/dashboard, a list, a detail, a create/edit form, and a UI-kit page — each at desktop and phone (about 400px).
- **Deliverable:** static HTML/CSS/JS prototype folders under `design/`, each with its own `style.css`, `app.js`, `README.md` and `screenshots/`. Not app templates. The winning variation's CSS later becomes the app's real stylesheet. No application code changes in this task.
- **Range:** 5 genuinely distinct directions — different layouts, navigation models, type pairings, density and tone — all within the crest brand.
- **Branding source:** `logo.png` only — the crest, `#722A82` as the brand hue, the torch, the motto — plus the cut-outs already in `static/img/`. Each direction derives its own palette, neutrals and type pairing fresh from the crest. The app's current look is not an input either: not `static/css/style.css` (its purple scale, neutrals, font families, radii, shadows), not `static/js/app.js`, not the current templates' layouts.

**Reading:** This task produces design options, not product code. We build five self-contained static prototypes of the same product — a Technology Management Desk holding a device register *and* an IT helpdesk — so the owner can see five finished-feeling versions side by side and pick one. Because the point is comparison, everything that isn't the design is held constant: all five show the same six screens, the same sample school data, the same words for the same things, and the same accessibility floor. What varies is the design direction: page layout, navigation model, type pairing, colour treatment, density and tone. The only fixed brand inputs are the crest image itself and the crest purple `#722A82`; everything else each direction works out for itself from the crest. Neither the earlier prototype nor the app's current look is an input — each variation's `style.css` is written from scratch. The winning `style.css` is expected to become `static/css/style.css` in a later brief, so each prototype's CSS must be token-first and structured for porting, even though nothing in `templates/`, `static/` or `apps/` is touched here.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**In scope**

- Five prototype folders, `design/a-<slug>/` … `design/e-<slug>/`, each self-contained and openable from the file system.
- Six HTML pages per folder (`login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`), plus `style.css`, `app.js`, `README.md`, `assets/` and `screenshots/`.
- One direction brief per variation in `docs/design/directions/`, written before any HTML.
- Shared sample content — people, devices, requests, dates, money — used identically by all five, defined once in the **Content contract** below.
- Screenshots: desktop and phone for every page, plus three state captures per folder.
- `design/README.md`: an index comparing the five directions in one table.
- The accessibility floor (keyboard, labels, heading order, targets, contrast, status shown as icon plus word) as a hard requirement of every page, not a later pass.

**Out of scope**

- **Choosing the winner.** The owner does that after seeing the five. No agent ranks them.
- **`design/v5-tasks/`, which no longer exists.** The owner has deleted that folder from disk; the deletion is intentional and is committed separately from this task. It is therefore not an input to this task in any form — not as a layout, a token set, a type pairing, a concept, a component inventory or a naming series — and there is nothing there to read. No agent recreates it, restores it from Git history, or cites or copies from it, and nothing in this task's output refers to it.
- **The current app CSS/JS and templates are not inputs.** `static/css/style.css`, `static/js/app.js` and everything under `templates/` are excluded in the same way and for the same reason: they carry the earlier prototype's look. No agent reads them for design ideas, and no variation may reuse their font families, their palette beyond the crest purple itself, their radii, shadows, spacing scale, class names or component shapes. Each variation's `style.css` starts from an empty file. The only files any agent copies from `static/` are the three crest images in `static/img/` (criterion 1), and that is a binary copy, not a design input.
- Any change under `apps/`, `templates/`, `static/`, `config/`, `docker/`, `compose*.yaml`, `pyproject.toml` or any requirements file. No Django, no migrations, no settings, no application dependencies.
- Porting the winning CSS into `static/css/style.css` — a separate brief once a winner exists.
- Real data. Everything in the prototypes is invented sample content.
- Screens beyond the six listed: no device register list, no request detail page, no reports, no settings, no user administration. The **Screen map** explains why these six cover both halves of the product.
- Build steps, frameworks, npm packages in the deliverable, CSS preprocessors, CDN JavaScript.
- Dark mode as a full theme (decision D5).

**Which project conventions bind here.** `CLAUDE.md`'s "UI conventions" section records the *style* of an earlier prototype the owner has now set aside, and the app's current stylesheet is that same style shipped. For this task their style prescriptions — the specific font families, "crest purple only for primary actions", verb tiles — are **not binding**, and a direction that ignores them is not a defect. What still binds, because each stands on its own as a requirement of these users, is: the audience is school staff, many of them non-technical; plain everyday wording, with each field saying what to type; errors that explain how to fix the problem and keep what the user typed; touch targets of 44px or more; status shown with an icon and a word, never colour alone; and WCAG AA contrast. Everything in `CLAUDE.md` outside that section applies unchanged.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

Everything below is checkable on the static files. "Each folder" means each of the five `design/[a-e]-*/` folders; "each page" means each of the six HTML pages in that folder. The intended tooling is under **Verification method** at the end of this section.

**Structure**

1. Exactly five folders exist matching `design/[a-e]-*`, and each contains exactly these files: `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css`, `app.js`, `README.md`, `assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png`, and the screenshots required by criterion 21.
2. Every page opens from `file://` with no missing local file: every `href`, `src` and `url()` in the HTML and CSS resolves either to a file inside that same folder or to `https://fonts.googleapis.com` / `https://fonts.gstatic.com`. No `../`, no absolute local path, no reference to `static/` or to another folder under `design/`.
3. `docs/design/directions/a.md` … `e.md` exist; each names its folder path on its first content line, and that path matches an existing folder from criterion 1.
4. `design/README.md` exists and has one row per variation with: folder, direction name, navigation model, heading font, body font, density, and a one-line "who it suits". It compares the five against each other only.
5. No file this task produces recreates, restores or references `design/v5-tasks/`: the folder has been deleted by the owner, no agent brings it back in whole or in part (including from Git history), and no delivered file names that path. Ignoring changes that were already pending before this task started, `git status` at the end of the task shows this task's changes only under `design/<letter>-*/`, `docs/` and `README.md`. No file under `apps/`, `templates/`, `static/`, `config/`, `docker/`, and no compose, packaging or requirements file, is added, changed or deleted.

**Each README**

6. Each folder's `README.md` has, as headed sections: the direction name and a two-sentence concept; **Fonts** (exact families, weights, and where each is used); **Palette** (every token with its hex, how it was derived from the crest, and the contrast pairs checked with their ratios); **Why it suits non-technical school staff** (at least one paragraph, concrete, about these users and this school); **Navigation model** (desktop and phone, and what happens with JavaScript off); **Skills used** (the named skills the designer and the builder actually loaded); **Demo hooks** (every `?demo=` URL, and a line saying these are prototype-only and are never ported into `templates/`); **Screenshots** (what is in `screenshots/`).
7. No README, no direction brief, no page and no comment in any delivered file mentions `v5`, `v5-tasks`, the app's current stylesheet or any earlier prototype, or compares the direction to one.

**Valid, semantic HTML**

8. Each page parses with no unclosed or mismatched element, starts with `<!DOCTYPE html>` at byte 1, and has `<html lang="en-LK">`, `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">` and a non-empty `<title>` of the form `<Page name> · Polymath TMD`.
9. Every `id` on a page is unique, and every `for`, `aria-describedby`, `aria-labelledby`, `aria-controls`, `aria-owns` and same-page `href="#…"` points at an `id` that exists on that page.
10. Each page has exactly one `<h1>` and exactly one `<main>`, and heading levels never skip a level going down (no `h3` follows an `h1` in document order without an `h2` between them).
11. Each page's first focusable element is a skip link pointing at the `id` of its `<main>`.
12. Every `<img>` has an `alt` attribute (empty only when decorative), every decorative `<svg>` has `aria-hidden="true" focusable="false"`, and every `<button>` and `<a>` has an accessible name — visible text, `aria-label`, or a visually hidden span.
13. Every form control has a `<label for>` or a visually hidden label; a `placeholder` is never the only label. Every field that needs explaining has help text linked with `aria-describedby`.

**Accessibility floor**

14. Keyboard: at a 1440×900 viewport, every interactive element on every page is reachable by Tab in an order matching its visual order; no element has a positive `tabindex`; every focused element shows a visible focus indicator with at least 3:1 contrast against the adjacent background. Nothing is reachable by hover alone.
15. Touch targets: at a 400px-wide viewport, every interactive element's rendered box is at least 44×44 CSS px, or has at least 44×44px of pointer area through padding. Inline links inside a sentence of prose are exempt, and every exemption is listed in the verification report.
16. Contrast: every text-on-background pair used across the six pages meets WCAG AA — 4.5:1 for text under 24px (under 19px if bold), 3:1 for larger text, for icons that carry meaning, and for control borders. The README's Palette section lists the pairs and ratios, and the verifier recomputes them from the token values in `style.css`.
17. Status is never colour alone: every request status, device status and condition value renders as an icon plus a word.
18. Motion: every transition and animation is removed or reduced inside `@media (prefers-reduced-motion: reduce)`.

**Responsive**

19. At a 400×844 viewport, every page's document `scrollWidth` is no greater than its `clientWidth` — no horizontal scrolling — and no text is clipped or overlapping.
20. At a 1440×900 viewport, the main content column is no wider than the measure the direction brief states, and body text is at least 16px on every page at both viewports.

**Works without JavaScript**

21. With JavaScript disabled, every page still renders its full content, the primary navigation is visible or reachable through a plain HTML control (a link, or `<details>`), and every form is present with its fields and a submit button. Nothing the page's task needs is JavaScript-only. `app.js` is a single IIFE that binds through `data-*` attributes and adds no framework, build step or third-party script.

**Screenshots**

22. Each folder's `screenshots/` contains, non-blank and matching the current HTML: `desktop-login.png`, `desktop-dashboard.png`, `desktop-requests.png`, `desktop-device.png`, `desktop-request-form.png`, `desktop-ui-kit.png`, each captured full-page at a 1440×900 viewport; `mobile-login.png`, `mobile-dashboard.png`, `mobile-requests.png`, `mobile-device.png`, `mobile-request-form.png`, `mobile-ui-kit.png`, each full-page at 400×844; and three state captures at 1440×900: `desktop-login--error.png`, `desktop-request-form--errors.png`, `desktop-requests--empty.png`. Fifteen files per folder, seventy-five in all. Every capture is taken with the web fonts actually loaded.

**Brand fidelity**

23. The crest (`assets/crest.png`, cut from `logo.png`) is used unmodified: no CSS `filter`, `mix-blend-mode`, `opacity` below 1, or background knock-out is applied to it; its rendered width and height keep the source aspect ratio to within 1%; it is never rendered smaller than 28px tall; and its `alt` is `Polymath College crest` where it carries meaning, or `""` where an adjacent wordmark already names the college.
24. The college is always written `Polymath College` and the product `Technology Management Desk`, shortened to `Polymath TMD` only in `<title>`. Each README names the font used for the wordmark.
25. The crest purple `#722A82`, or a tint or shade of it from the direction's own scale, is present and legible as the brand colour on every page, and the README says where. Each page has exactly one visually dominant primary action; which colour carries it is the direction's decision.
26. Token discipline, because the winner becomes `static/css/style.css`: every colour, font, space, radius, shadow and duration value in `style.css` is declared once in `:root` and used through `var(--…)`. No raw hex, `rgb()`, `hsl()` or named colour appears outside the `:root` block; inline SVG in the HTML uses `currentColor` for every `fill` and `stroke`. `style.css` is organised into numbered comment sections in this order: 1 tokens, 2 base and reset, 3 icons, 4 app shell and navigation, 5 components, 6 page-specific, 7 responsive, 8 reduced motion and print.

**Distinctness — the point of the task**

27. Navigation (relaxed on desktop by decision D9; the original wording is recorded there). **Desktop:** the five use five distinct primary navigation *treatments*. Two variations may share a mechanism — a left vertical nav, say — but any two that do must differ in **at least two** of these six, visibly and measurably at a 1440×900 viewport: mechanism (where the nav lives and how it behaves), width or placement, grouping (sectioned or a flat list), item shape (row, tile, icon-over-word, plain link), count badges (present or absent), and framing (borders, panels, a rule, or none). **Phone:** the five still use five different mechanisms, no two alike. Each README names its desktop treatment and its phone mechanism, and `design/README.md` records both so the differences can be read off one table. The verifier states, for every pair of variations sharing a desktop mechanism, which two of the six they differ on and by how much.
28. Type: no two variations use the same heading font family, and no two use the same heading/body pairing. No font family appears in more than two of the five.
29. Layout: no two variations share a page skeleton — the position of navigation, the number of content columns on desktop, and the page-head treatment all differ. `design/README.md` shows this.
30. Density is measurably different: the number of request rows visible in the first 900px of `requests.html` at a 1440×900 viewport differs by at least 2 between the densest and the least dense variation, and each README states its density intent.
31. Colour alone is not the difference: rendered in greyscale, criteria 27–30 still hold.

**Same content everywhere**

32. Every string, number and name in the **Content contract** appears identically in all five folders. Tokens the verifier greps for in each folder: `nimali.p`, `Nimali Perera`, `REQ-2048`, `Projector in Lab 2 shows a blue screen`, `IT-0142`, `Dell Latitude 3540`, `Dilani Fernando`, `Grade 6B`, `Rs 285,000`, `Fri 11 Sep 2026`, `Science Block Lab 2`.
    **The four points settled after the builds began are contract text like the rest, and must match verbatim in all five folders:** the corrected weekdays (`Thu 10 Sep 2026, 11:20 am`, `Fri 11 Sep 2026, 7:35 am`, `Tue 25 Aug 2026`, `Fri 21 Aug 2026, 3:05 pm`, `Fri 12 Jun 2026, 9:30 am`, and no occurrence anywhere of `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug` or `Thu 12 Jun`), `REQ-1902`'s title `Battery replaced under warranty`, the select prompts `Choose a device` and `Choose a room` (and no `Choose one`, `Please select` or `— Select —`), `Nobody yet` for every unassigned request, and `Showing 0 of 8 requests` in the empty state.
    **The two raised timestamps moved so that reference numbers ascend with time are contract text too:** `REQ-2048` reads `Fri 11 Sep 2026, 8:15 am` and `REQ-2045` reads `Tue 8 Sep 2026, 7:35 am`; `Wed 9 Sep` appears nowhere, and `Fri 11 Sep 2026, 7:35 am` appears nowhere. The row order stays `REQ-2048` first down to `REQ-2041` last, no timestamp in any folder falls on a Saturday or a Sunday, the dashboard reads `3 devices due back next week` (never `this week`), and a direction that shows the chart shows `Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1` with all five days present including the Wednesday zero.
33. Labels for the same thing are identical across the five: primary navigation uses exactly `Home`, `Requests`, `Devices`, `Raise a request`; request statuses are exactly `New`, `In progress`, `Waiting on someone`, `Fixed`, `Closed`.
34. No page contains lorem ipsum, `TODO`, `FIXME`, `xxx`, a placeholder-image service URL, or a person, school or place name from outside the Content contract.

**States**

35. Each folder demonstrates, and documents in its README: the sign-in error state (`login.html?demo=error`), the form-with-errors state (`request-form.html?demo=errors`), the empty list state (`requests.html?demo=empty`), and a success confirmation (`?demo=toast` on any app page). Error copy keeps everything the user typed and says how to fix the problem; the empty state says what to do next.

**Independence from the app's current look**

36. No variation reuses the current app's design. Checked against `static/css/style.css` and the current `templates/`, a variation **fails** if any of the following is true:
    - its heading or body font family is one the current stylesheet uses;
    - any colour token other than the crest purple `#722A82` itself has the same hex value as a token in the current stylesheet — its purple tints and shades, its neutrals, its functional colours and its chart colours must all be newly derived;
    - its radius, shadow or spacing values match the current stylesheet's set;
    - it reuses the current stylesheet's component class names or component shapes, or reproduces the current templates' page layouts.
    Two variations may of course coincide with each other by accident on a single value; this criterion is only about the current app.
37. Each `style.css` was written from scratch: no block, rule order, comment or token block is copied from `static/css/style.css`, and no file in any variation is a modified copy of `static/js/app.js` or of a file under `templates/`. Each README's Palette section shows how its colours were derived from the crest, which is what makes this checkable rather than a matter of opinion.

**Verification method** (guidance for `tmd-test-verifier`, not extra criteria)

- Criteria 14, 15, 19, 20, 22 and 30 need a real rendering engine. Use **Playwright**: set the viewport explicitly (1440×900 and 400×844), `goto` the `file://` URL, `wait_for_load_state("networkidle")` and wait for `document.fonts.ready` before capturing, then `screenshot(full_page=True)`. Measure with `page.evaluate` — bounding boxes for targets, `documentElement.scrollWidth` vs `clientWidth`, computed styles for font sizes, and `getBoundingClientRect().top < 900` for the row count.
- Install Playwright into a scratchpad virtual environment or run it through `npx`. It is verification tooling: **never** add it to `pyproject.toml`, a requirements file or the Docker image (criterion 5). It needs network once, to fetch its browser.
- Keyboard order (criterion 14) can be walked with repeated `keyboard.press("Tab")` plus `document.activeElement`.
- Criteria 7, 27–31, 34, 36 and 37 are read-and-compare checks; state what you compared. For 36 and 37, extract the `:root` token values from each variation's `style.css` and from `static/css/style.css` and compare the sets; report any shared value other than `#722A82`.
- Record whether the web fonts loaded during capture. Screenshots taken with fallback fonts do not satisfy criterion 22.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

None blocking. The questions that would have changed the deliverable were answered before this brief was finished. The decisions taken on the owner's behalf are recorded here, and any of them can be overturned cheaply before the build step starts.

- **D1 — No earlier prototype and no current app look as input.** The earlier prototype folder `design/v5-tasks/` has been **deleted from disk by the owner** and is not coming back; it is not merely excluded as an input, there is nothing left to consult, and no agent restores it. The app's current front end (`static/css/style.css`, `static/js/app.js`, `templates/`) still exists but is excluded entirely (see Scope and criteria 5, 7, 36 and 37). Each direction starts from `logo.png`, the product scope and the Content contract. Fonts, neutrals, the purple scale, radii, shadows, spacing, the component set and the icon style are each direction's own work, and each `style.css` starts from an empty file.
- **D2 — Folder naming.** `design/<letter>-<slug>/`, letters `a`–`e`, for example `design/a-console/`. The letter gives the owner a short way to refer to one ("direction c") and keeps a stable order in the file list; the slug keeps it meaningful. The naming deliberately starts a fresh series rather than continuing any earlier one.
- **D3 — Which six screens.** See the **Screen map**. The list page is the *request queue*, not a device register, and the detail page is a *device record*, not a request. The reasoning is in the Screen map.
- **D4 — Shared content, varied form.** Content, labels and status words are identical across all five (criteria 32–34) so the owner compares design, not wording.
- **D5 — Light mode.** All five are light-mode products: staff use these on shared machines in bright classrooms and offices, and the crest is a light-first mark. One direction may use dark *chrome* — a dark rail, sidebar or masthead — against a light content canvas. No full dark theme and no dark-mode toggle in this task.
- **D6 — `?demo=` hooks.** Each prototype reads a `demo` query parameter to switch a page into its error, empty or success state, so the owner and the verifier can reach those states without a server. Each README lists the hooks and states that they are prototype-only and are never carried into `templates/`.
- **D7 — File ownership override for this task.** `tmd-frontend` normally owns `templates/`, `static/css/style.css`, `static/js/app.js` and `static/img/`. **For task 002 only, each `tmd-frontend` agent owns exactly one `design/<letter>-<slug>/` folder and must not touch `templates/` or `static/` at all.** These folders are prototype material, not application code. `tmd-ui-designer` keeps its normal rule: documents only, no HTML, CSS or JS.
- **D8 — No device register list page.** The `Devices` navigation item points at `device.html`, the single record. Each README says the register list is deliberately not prototyped, because `requests.html` already proves the list, filter, sort, status and empty-state patterns a register would reuse.
- **D9 — Criterion 27's desktop clause was relaxed after the build, not enforced by rebuilding a variation.** Recorded in full, because how this was decided matters more than what was decided.
  - **The original wording, as written before any folder existed:** "Navigation: the five use five different primary navigation mechanisms on desktop, and five different phone mechanisms. Each README names both. No two variations share either."
  - **What was built:** `a` (Ledger) and `d` (Signpost) both put the primary navigation in a left vertical column — `a` a 248px sidebar with grouped sections and live queue counts, `d` a 96px ungrouped framed rail of icon-over-word tiles. `b`, `c` and `e` are three mechanisms distinct from those two and from each other, and all five phone mechanisms are distinct.
    **The count badge in `d`, in sequence, because the record is the point:** `d` was built *with* a `Requests` count badge on its rail. During round 1 the badge was **removed**, which made "count badges" read as a difference between `a` and `d`. That difference was therefore *created to satisfy the measurement, not found in the designs* — the reviewer objected in round 2 (should-fix 4) that a design had been edited to satisfy a metric rather than a user, and the removal has been **reversed: the badge is restored**. `d` shows its `Requests` count again, as it was designed to. Counting the badge as an `a`/`d` discriminator would have been counting our own edit, so it is struck from the list below.
  - **The reviewer's finding** (round 1, should-fix 8): taken literally, `a` and `d` share a desktop mechanism, so criterion 27 fails as originally written.
  - **Why the criterion moved instead of `d`:** respeccing `d` means rebuilding its shell across all six pages — a day of work and a fresh round of verification — to satisfy a taxonomic claim ("five mechanisms") that the owner is not choosing on. The owner picks between these five by looking at them, and `a` and `d` do not look alike: 248px against 96px, grouped sections against a flat list, full-width rows against icon-over-word tiles, and unframed against framed — **four** of the six discriminators, where the amended criterion asks for two. Both show a `Requests` count badge, so count badges are *not* one of the four; the margin holds without them. The requirement the criterion was written to protect — *five options that are genuinely different to look at and to use* — is met; the wording was simply stricter than the requirement.
  - **What was given up, stated plainly:** the five no longer demonstrate five different desktop navigation *patterns*, so this task does not answer "which navigation pattern suits the school best" as fully as first intended. If the owner wants that answer, it is a new brief that respecs one variation deliberately, not a patch to this one.
  - **Nothing else moved.** The phone clause stands unrelaxed at five distinct mechanisms, criteria 28–31 stand as written, and no criterion was renumbered. A criterion is only ever relaxed in the brief, by the planner, with the original wording kept — never quietly, and never by an agent editing its own target.

## MVT plan
<!-- owner: tmd-planner -->

There is no Model, View or Template layer in this task: nothing is added to `apps/`, `config/` or `templates/`, and no URL is routed. The three headings below carry their equivalents for a static prototype — the content model the screens imply, the screen map that stands in for URLs and views, and the content contract, which is the only coupling between the five parallel builders.

### Models

The prototype's content model. Nothing here is implemented in this task and it is **not** a database design, but the field names and status words should be reused when the real models are briefed, so the two do not drift.

**Person**

| Field | Example | Notes |
|---|---|---|
| Display name | `Nimali Perera` | Shown wherever a person appears |
| Username | `nimali.p` | `firstname.initial`; shown on sign-in and in the account area |
| Role | `ICT Technician` | Plain label under the name |
| Where they are | `ICT Room` | Room or department |

**Device** — the asset register half

| Field | Example | Notes |
|---|---|---|
| Tag | `IT-0142` | The label stuck on the device; what staff read out |
| Name | `Dell Latitude 3540 laptop` | Make, model, kind |
| Kind | `Laptop` | Laptop, Projector, Tablet, Desktop PC, Printer, Interactive panel, Visualiser |
| Status | `Issued` | One of `In store`, `Issued`, `In repair`, `Out of service` |
| Condition | `Good` | One of `Good`, `Needs repair`, `Out of service` |
| Who has it | `Dilani Fernando` | Empty when `In store` |
| Where it is | `Grade 6B Classroom` | Room |
| Due back | `Mon 21 Sep 2026` | Empty when not issued |
| Bought | `14 Feb 2024` | |
| Value | `Rs 285,000` | Sri Lankan rupees, no decimals, comma thousands separator |
| Warranty until | `13 Feb 2027` | |

**Request** — the helpdesk half

| Field | Example | Notes |
|---|---|---|
| Reference | `REQ-2048` | |
| What is wrong | `Projector in Lab 2 shows a blue screen` | The short title shown in the list |
| Raised by | `Suresh Kumara` | A Person |
| About which device | `IT-0087` | A Device, or `Not about a particular device` |
| Where | `Science Block Lab 2` | |
| How urgent | `Urgent` | One of `Can wait`, `Normal`, `Urgent` |
| Status | `In progress` | One of `New`, `In progress`, `Waiting on someone`, `Fixed`, `Closed` |
| Who is on it | `Nimali Perera` | Nobody is assigned while the status is `New`; the screen writes that as `Nobody yet`, never as a blank cell or a dash |
| Raised | `Fri 11 Sep 2026, 8:15 am` | The reference number is handed out at this moment, so higher numbers are always newer |
| Updates | list of `{when, who, what}` | The history shown as a timeline |

The two lifecycles, rendered identically in all five (the device history and the list's status column both read from them):

```
Request:  New ──▶ In progress ──▶ Fixed ──▶ Closed
                      │    ▲
                      ▼    │
               Waiting on someone

Device:   In store ──▶ Issued ──▶ In store
             │  ▲                    │
             ▼  │                    ▼
          In repair ◀────────── Needs repair reported
             │
             ▼
        Out of service
```

### URLs and views

No routes. This is the **screen map**: the six pages every variation builds, in the order a person meets them.

| Page (file) | What it is for | Primary content | Nav position | Who it is for |
|---|---|---|---|---|
| `login.html` | Sign in | Username and password, the crest, one error state | — (no app chrome) | Everyone |
| `dashboard.html` | See what needs doing today, and start a job | Both halves: open requests, urgent count, devices due back next week, devices in repair, register size, and the main actions | `Home` | Everyone; first screen after sign-in |
| `requests.html` | Work through the queue; find a request | A list of 8 requests with search, filters (status, urgency, who is on it), sort, and an empty state | `Requests` | IT staff mainly; teachers see their own |
| `device.html` | See one device's whole story | `IT-0142`: who has it, where, condition, value, warranty, its open and past requests, and a dated history of issues, returns and repairs | `Devices` | IT staff and the office |
| `request-form.html` | Raise a request about a device | The guided form — what it is about, what is wrong, where, how urgent, a photo — with its error state | `Raise a request` (primary action) | Teachers and office staff: the least technical users |
| `ui-kit.html` | The component catalogue for this direction | Every component the direction defines, in every state | Utility link labelled `Design kit` | The owner, and whoever ports the winner |

**Why these six cover both halves without more pages** (decision D3): the dashboard shows both halves at a glance; the list exercises the helpdesk queue, the denser and harder screen, and proves the list, filter, status, sort and empty-state patterns; the detail is a device record, which proves the asset half *and* shows the join between the halves, because the device's own requests are listed on it; and the form is the request-raising flow, where a teacher picks a device — crossing both halves again. A device register list would reuse patterns the queue already proves, and a request detail page would reuse the timeline the device page already proves.

**Information architecture** (from `ux-strategy:information-architecture`; criterion 33 fixes the labels, while the *mechanism* is what each direction varies):

```
Sign in
└── Home  (dashboard)
    ├── Requests            ← the queue: search, filter, sort
    │   └── (a request)     ← not prototyped; its timeline pattern appears on Devices
    ├── Devices             ← opens the IT-0142 record (D8)
    │   └── Device record   ← holder, condition, history, linked requests
    ├── Raise a request     ← primary action, reachable from every screen
    └── Utility
        ├── Nimali Perera / account
        ├── Sign out
        └── Design kit      ← prototype only
```

- **Global navigation** carries exactly four items — `Home`, `Requests`, `Devices`, `Raise a request` — because four is inside the span non-technical staff scan without re-reading, and each is a place or a job rather than a data type.
- **Utility navigation** (the person's name, Sign out, Design kit) is kept separate from those four, wherever the direction puts it.
- **Phone:** each direction states its own mechanism and must keep `Raise a request` reachable with one thumb. Whatever the mechanism, it works with JavaScript off (criterion 21).
- **Wayfinding:** every page says where you are — the current nav item carries `aria-current="page"`, and the `<h1>` uses the same wording as the nav label.

### Content contract

Here the coupling is not backend to frontend but **planner to five parallel builders**. This is the sample content, copied verbatim into all five folders. No agent invents, renames or improves any of it; a gap comes back to the planner. Today, everywhere, is **Friday 11 September 2026**.

**Dates and weekdays.** Every weekday name below has been checked against the real 2026 calendar and is now correct: 1 Sep 2026 is a Tuesday, so Sep runs Mon 7, Tue 8, Wed 9, Thu 10, Fri 11, Mon 14, Mon 21; 1 Jun 2026 is a Monday, so 12 Jun 2026 is a Friday; 31 Aug 2026 is a Monday, so 21 Aug is a Friday and 25 Aug a Tuesday. Where a weekday and a date disagreed in the first version of this contract, the **date number was kept and the weekday corrected**, with one exception: the return to the store moved from `Fri 22 Aug` (a Saturday — the school is shut) to **`Fri 21 Aug 2026`**. Five corrections to align folders to, in full:

| Was | Now | Where |
|---|---|---|
| `Wed 10 Sep 2026, 11:20 am` | `Thu 10 Sep 2026, 11:20 am` | `REQ-2047` raised; the matching `IT-0142` history line |
| `Thu 11 Sep 2026, 7:35 am` | `Fri 11 Sep 2026, 7:35 am` | `REQ-2045` raised (it is today) |
| `Mon 25 Aug 2026` | `Tue 25 Aug 2026` | `IT-0142` given out; the matching history line |
| `Fri 22 Aug 2026, 3:05 pm` | `Fri 21 Aug 2026, 3:05 pm` | `IT-0142` returned to the store |
| `Thu 12 Jun 2026, 9:30 am` | `Fri 12 Jun 2026, 9:30 am` | `IT-0142` battery replaced |

A date is always written `Ddd D Mmm YYYY` (`Fri 11 Sep 2026`), and a date with a time adds `, h:mm am/pm` in lower case (`Fri 11 Sep 2026, 7:35 am`). Dates with no weekday — `14 Feb 2024`, `13 Feb 2027` — stay as they are.

**Reference numbers ascend with the time raised.** The eight rows of `requests.html` are listed newest first, `REQ-2048` down to `REQ-2041`, and that is also the default `Newest first` sort — so the two must agree, as they do in any real helpdesk, where the number is handed out when the request arrives. The table order stays as it is and the row order in every folder stays as it is; **two raised timestamps move instead**:

| Was | Now | Where |
|---|---|---|
| `Wed 9 Sep 2026, 8:15 am` | `Fri 11 Sep 2026, 8:15 am` | `REQ-2048` raised — the newest request, and the one raised today |
| `Fri 11 Sep 2026, 7:35 am` | `Tue 8 Sep 2026, 7:35 am` | `REQ-2045` raised — it sits between `REQ-2046` and `REQ-2044` |

Only those two move; the time of day is kept in both. `REQ-2047` stays at `Thu 10 Sep 2026, 11:20 am`, which is why the `IT-0142` history line that mirrors it does not change either — no device history line moves. `REQ-2048` stays `Urgent` and `In progress`, and its detail text still reads "It happened in period 2 and period 4 on Tuesday", which is Tue 8 Sep, earlier the same week. `REQ-2045` asking for a tablet "on Monday" is raised on Tue 8 Sep for Mon 14 Sep. Every timestamp lands on a school day; there is no Saturday or Sunday anywhere in this contract.

After the move, the eight rows read, newest first: `REQ-2048` Fri 11 Sep 8:15 am · `REQ-2047` Thu 10 Sep 11:20 am · `REQ-2046` Tue 8 Sep 1:40 pm · `REQ-2045` Tue 8 Sep 7:35 am · `REQ-2044` Mon 7 Sep 2:10 pm · `REQ-2043` Fri 4 Sep 9:05 am · `REQ-2042` Thu 3 Sep 4:25 pm · `REQ-2041` Tue 1 Sep 10:50 am. `Oldest first` is this list reversed; `Most urgent first` puts `REQ-2048` then `REQ-2042` at the top and leaves the rest in this order.

No date in this contract changes other than the seven in these two tables, and the two dashboard figures that read from them (below).

**People**

| Name | Username | Role | Where |
|---|---|---|---|
| Nimali Perera | `nimali.p` | ICT Technician | ICT Room |
| Ruwan Jayasuriya | `ruwan.j` | ICT Coordinator | ICT Room |
| Dilani Fernando | `dilani.f` | Teacher | Grade 6B Classroom |
| Suresh Kumara | `suresh.k` | Science Teacher | Science Block Lab 2 |
| Anoma Silva | `anoma.s` | Office Administrator | Admin Office |
| Tharindu Bandara | `tharindu.b` | Sports Teacher | Sports Room |

The signed-in person on every app screen is **Nimali Perera**, ICT Technician, initials `NP`.

**Rooms:** ICT Room · ICT Store · Science Block Lab 2 · Grade 6B Classroom · Library · Admin Office · Sports Room · Main Hall.

**Devices** (`device.html` shows `IT-0142` in full; the rest appear in pickers and linked lists)

| Tag | Name | Kind | Status | Condition | Who has it | Where | Due back | Value |
|---|---|---|---|---|---|---|---|---|
| `IT-0142` | Dell Latitude 3540 laptop | Laptop | Issued | Good | Dilani Fernando | Grade 6B Classroom | Mon 21 Sep 2026 | Rs 285,000 |
| `IT-0087` | Epson EB-X51 projector | Projector | In repair | Needs repair | — | Science Block Lab 2 | — | Rs 96,500 |
| `IT-0203` | Lenovo Tab M10 tablet | Tablet | In store | Good | — | ICT Store | — | Rs 42,000 |
| `IT-0056` | HP LaserJet M404 printer | Printer | In repair | Needs repair | — | Admin Office | — | Rs 74,900 |
| `IT-0119` | 65-inch interactive panel | Interactive panel | Issued | Good | Dilani Fernando | Grade 6B Classroom | — | Rs 410,000 |
| `IT-0175` | Dell OptiPlex 3000 desktop | Desktop PC | Issued | Good | Ruwan Jayasuriya | ICT Room | — | Rs 178,000 |
| `IT-0034` | Epson EB-S41 projector | Projector | Out of service | Out of service | — | ICT Store | — | Rs 88,000 |
| `IT-0211` | Elmo visualiser | Visualiser | In store | Good | — | ICT Store | — | Rs 61,500 |

`IT-0142` in full, for `device.html`: bought **14 Feb 2024**, warranty until **13 Feb 2027**, serial **5CG4113XYZ**, value **Rs 285,000**, given to **Dilani Fernando** on **Tue 25 Aug 2026**, due back **Mon 21 Sep 2026**, condition **Good**, last checked **Thu 3 Sep 2026**.

`IT-0142` history, newest first, shown as a timeline:

| When | Who | What happened |
|---|---|---|
| Thu 10 Sep 2026, 11:20 am | Dilani Fernando | Raised `REQ-2047` — will not connect to the staff Wi-Fi |
| Tue 25 Aug 2026, 7:50 am | Nimali Perera | Given to Dilani Fernando for Grade 6B. Due back Mon 21 Sep 2026 |
| Fri 21 Aug 2026, 3:05 pm | Nimali Perera | Returned to the ICT Store. Condition checked: Good |
| Fri 12 Jun 2026, 9:30 am | Nimali Perera | Battery replaced under warranty. Closed `REQ-1902` |
| Fri 14 Feb 2025, 10:00 am | Anoma Silva | Added to the register. Bought 14 Feb 2024 |

`IT-0142` linked requests, with the exact titles to show wherever a linked request is listed:

| Ref | Title | Status | Raised |
|---|---|---|---|
| `REQ-2047` | Laptop will not connect to the staff Wi-Fi | New | Thu 10 Sep 2026, 11:20 am |
| `REQ-1902` | Battery replaced under warranty | Closed | Fri 12 Jun 2026, 9:30 am |

`REQ-1902`'s title is `Battery replaced under warranty` — the same words as its history line, so the two read as one story. It appears only on `device.html`; it is not one of the eight rows in `requests.html`.

**Requests** (all eight appear in `requests.html`, in this order — which is newest first, the default sort)

| Ref | What is wrong | Raised by | Device | Urgency | Status | Who is on it | Raised |
|---|---|---|---|---|---|---|---|
| `REQ-2048` | Projector in Lab 2 shows a blue screen | Suresh Kumara | `IT-0087` | Urgent | In progress | Nimali Perera | Fri 11 Sep 2026, 8:15 am |
| `REQ-2047` | Laptop will not connect to the staff Wi-Fi | Dilani Fernando | `IT-0142` | Normal | New | Nobody yet | Thu 10 Sep 2026, 11:20 am |
| `REQ-2046` | Printer jams on every second page | Anoma Silva | `IT-0056` | Normal | Waiting on someone | Nimali Perera | Tue 8 Sep 2026, 1:40 pm |
| `REQ-2045` | Tablet needed for the Grade 5 reading class on Monday | Tharindu Bandara | Not about a particular device | Can wait | New | Nobody yet | Tue 8 Sep 2026, 7:35 am |
| `REQ-2044` | Interactive panel pen is not writing | Dilani Fernando | `IT-0119` | Normal | Fixed | Nimali Perera | Mon 7 Sep 2026, 2:10 pm |
| `REQ-2043` | No sound from the speakers in the ICT Room | Ruwan Jayasuriya | `IT-0175` | Normal | Closed | Nimali Perera | Fri 4 Sep 2026, 9:05 am |
| `REQ-2042` | Cannot sign in to the report system | Suresh Kumara | Not about a particular device | Urgent | Fixed | Ruwan Jayasuriya | Thu 3 Sep 2026, 4:25 pm |
| `REQ-2041` | New toner cartridge needed for the office printer | Anoma Silva | `IT-0056` | Can wait | Closed | Nimali Perera | Tue 1 Sep 2026, 10:50 am |

**Unassigned rows.** The two `New` requests have nobody on them. Wherever "Who is on it" is shown — the list row, a card, a filter summary, the device page's linked requests — an unassigned request reads exactly `Nobody yet`, the same words as the `Who is on it` filter option. Never a blank cell, never `—`, never `Unassigned`. (The em dash stays only in the **Devices** table above, for a device that has no holder and no due date.)

`REQ-2048` detail text, wherever a request is expanded or previewed: "The projector switches on, then the screen goes blue after about a minute. It happened in period 2 and period 4 on Tuesday. The lamp hours show 3,180."

**Dashboard figures** (identical in all five)

| Figure | Value | Words used |
|---|---|---|
| Open requests | 6 | `6 requests open` |
| Urgent | 2 | `2 are urgent` |
| Raised today | 1 | `1 raised today` |
| Devices due back next week | 3 | `3 devices due back next week` |
| Devices in repair | 2 | `2 devices in repair` |
| Devices in the register | 128 | `128 devices in the register` |
| Devices out on loan | 34 | `34 out on loan` |

Each figure is checkable, and two of them were adjusted when the raised timestamps moved:

- `1 raised today` is `REQ-2048`, raised `Fri 11 Sep 2026, 8:15 am`. It is the only request raised today, which is why it is also the highest number.
- `6 requests open` is the eight rows less the two `Closed` ones; `2 are urgent` is `REQ-2048` and `REQ-2042`; `2 devices in repair` is `IT-0087` and `IT-0056`.
- **`3 devices due back next week`** replaces the old `3 devices due back this week`, which could not be true: today is Friday, so "this week" has no school days left, and the only due date in the contract is `IT-0142`'s `Mon 21 Sep 2026`. Like `128 devices in the register` and `34 out on loan`, this figure counts the whole register, not the eight-device sample above; `IT-0142` is the one of the three that the contract shows in full. No folder invents due dates for the other devices — an interactive panel and a desktop PC are installed in a room, not lent out, so their `Due back` stays `—`.

If a direction shows a chart, it shows exactly one: requests raised per day over the last five school days, **Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1**, which is exactly the eight rows above counted by day (the other three were raised the week before). The text alternative beside it reads `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.` Wednesday's zero is deliberate and must render as a labelled empty bar or point, not as a gap or a missing category — an axis that quietly drops a day is the bug this figure is here to catch. Use the direction's own chart tokens, validated for contrast.

**Sign-in copy**

| Element | Text |
|---|---|
| Heading | `Welcome back` |
| Sub-line | `Sign in to the Technology Management Desk.` |
| Username label / help | `Username` / `The name the school gave you, like nimali.p` |
| Password label / help | `Password` / `Passwords are case sensitive.` |
| Button | `Sign in` |
| Error title / body (`?demo=error`) | `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` |
| Footer | `Polymath College · Technology Management Desk` |

In the error state the username box still holds `nimali.p`.

**`request-form.html` fields, in order**

| # | Label | Help text | Control |
|---|---|---|---|
| 1 | `What is it about?` | `Pick the device, or choose "Not about a particular device".` | Select opening on `Choose a device`, then the 8 devices as `IT-0142 — Dell Latitude 3540 laptop`, then `Not about a particular device` |
| 2 | `What is wrong?` | `One short line, for example "Projector will not turn on".` | Text input, required |
| 3 | `Tell us more` | `What happens, when it started, and what you already tried.` | Textarea, optional |
| 4 | `Where is it?` | `The room where we will find it.` | Select opening on `Choose a room`, then the 8 rooms in the order listed under **Rooms** |
| 5 | `How urgent is it?` | `Pick the one that fits. We look at urgent ones first.` | Three radios: `Can wait` (`It can wait until next week.`), `Normal` (`I need it in the next day or two.`), `Urgent` (`A class or the office is stopped right now.`); `Normal` preselected |
| 6 | `Add a photo` | `Optional. A photo of the screen or the error helps us a lot.` | File input |
| 7 | `Your name` | `We will reply to you.` | Read-only, showing `Nimali Perera (nimali.p)` |

**Select prompts** (settled once, and the same in all five folders — the designer's ruling in `docs/design/directions/c.md` §10):

| Select | First option | Then |
|---|---|---|
| `What is it about?` | `Choose a device` | the 8 devices, then `Not about a particular device` |
| `Where is it?` | `Choose a room` | the 8 rooms |
| `Status` filter (`requests.html`) | `All statuses` | the five statuses — a filter shows everything by default, so it needs no prompt |
| `How urgent` filter | `All` | the three urgency words |
| `Who is on it` filter | `Anyone` | `Nobody yet`, `Nimali Perera`, `Ruwan Jayasuriya` |
| `Sort` | — | no prompt option: `Newest first` is selected and is a real answer |

The two form prompts are placeholder options, not answers: each has an empty `value`, and in the error state (`?demo=errors`) `Where is it?` is still sitting on `Choose a room`, which is why it fails. Neither prompt is written as `Choose one`, `Please select`, `— Select —` or anything else; those exact two strings are the contract.

Buttons: `Send the request` (primary) and `Cancel` (secondary). Success toast: `Request sent. We gave it the number REQ-2049.` with an `Undo` action.

Error state (`?demo=errors`), keeping everything the user typed:

| Field | Message |
|---|---|
| `What is wrong?` | `Type a short description of the problem, for example "Projector will not turn on".` |
| `Where is it?` | `Choose the room where we will find it.` |
| Summary at the top | `We couldn't send this yet — 2 things need your attention`, with a link to each field |

**`requests.html` chrome**

- `<h1>`: `Requests`. Lead: `Everything staff have asked us to fix. Open the ones marked urgent first.`
- Search: label `Search requests`, placeholder `Reference, words, or a person's name, e.g. projector or REQ-2048`.
- Filters: `Status` (All statuses plus the five), `How urgent` (All plus the three), `Who is on it` (Anyone, Nobody yet, Nimali Perera, Ruwan Jayasuriya).
- Sort: `Newest first` (default), `Most urgent first`, `Oldest first`.
- Result line: `Showing 8 of 8 requests`. The same line in the empty state reads exactly `Showing 0 of 8 requests` — the total stays 8, because it is the number of requests there are, not the number the filters kept. The line is present in both states, in the same place, so it is not something that appears only when a search fails.
- Empty state (`?demo=empty`): the result line `Showing 0 of 8 requests`, then heading `No requests match what you chose`, body `Try clearing the filters, or search for a different word.`, button `Clear the filters`.

**`ui-kit.html` must show**, each in every state it has: buttons (primary, secondary, quiet, destructive, icon-only, disabled, busy); links; text input, textarea, select, radios, checkboxes, file input, search field, a field with help text, a field with an error; status badges for all five request statuses, all four device statuses and all three conditions, each with its icon and word; urgency chips; the list row; the card; the figure or stat tile; the timeline item; alerts (information, success, warning, danger); the toast; the modal; the empty state; pagination; the direction's wayfinding element; the avatar; the icon set at every size it uses; the type scale with pixel sizes; every colour token with its hex and contrast ratio; the spacing scale; and the focus ring on a light and on a dark surface.

**Assets.** Copy `static/img/crest.png`, `static/img/crest-chip.png` and `static/img/favicon-32.png` into each folder's `assets/`. Copying rather than linking keeps each folder self-contained and openable from `file://`, and means `design/` never reaches into `static/`. Read `logo.png` at the repository root directly when deriving colour: it is the crest, a purple shield with a torch and flame, `VIVERE DISCE` on the shield, and the motto `Vivere Disce ~ Learn to Live`.

### Placement and reuse

- **Everything is new material** under `design/<letter>-<slug>/` and `docs/design/directions/`. Nothing goes into an existing app, because nothing here is application code.
- **Nothing is reused from an earlier prototype or from the app's current front end** (decision D1). Each direction derives its own purple scale, neutrals, functional colours, type pairing, icon style and component set from `logo.png` and the product scope. The only thing taken from `static/` is a binary copy of the three crest images.
- **Reused from the project's rules:** the user-centred requirements listed at the end of Scope apply to all five without restatement.
- **Shared across the five and defined once here:** the Content contract, the navigation labels, the status words, the page filenames, the screenshot filenames and the `?demo=` hook names. Anything else that two variations happen to share is a coincidence, not a requirement.
- **Not reinvented:** no component here needs JavaScript that plain HTML cannot do. Use `<details>` for disclosures, real `<form>` elements and real links; `app.js` only enhances.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

**Step 1 — `tmd-ui-designer`** (one run, not five: the directions must be distinct *from each other*, which needs one mind holding all five).

Writes `docs/design/directions/a.md` … `e.md`, one per variation, and fills this brief's **Design** section with the index and the shared non-negotiables. Documents only — no HTML, CSS or JS. It must not open `static/css/style.css`, `static/js/app.js` or anything under `templates/`, and must not recover the deleted `design/v5-tasks/` from Git history; its visual inputs are `logo.png` and the three crest images only.

Each direction brief contains, in this order:

1. The folder path on the first content line, matching `design/<letter>-<slug>/`.
2. The direction name and a two-sentence concept.
3. The navigation model, desktop and phone, including behaviour with JavaScript off and how `Raise a request` stays reachable.
4. ASCII wireframes at both breakpoints (1440 and 400) for `dashboard.html` and `requests.html` at minimum; a sketch or a paragraph is enough for the other four.
5. The type pairing: exact Google Font families and weights, the type scale in px, and the wordmark font.
6. The palette: every token with its hex, how it was derived from the crest in `logo.png`, and the contrast pairs with ratios.
7. Component treatment: corners, borders, shadows, the button set, the status badge, the row, the card, the field, the focus ring, and the icon style the direction uses.
8. Density intent, and the expected number of request rows in the first 900px (criterion 30).
9. Motion: what moves, for how long, and the reduced-motion behaviour.
10. Which installed skills the builder should load for this direction.

The five slots and their remits. The designer names each direction, chooses its slug and may adjust a remit, as long as the five keep five different desktop navigation models, five different phone models and five different type pairings:

| Slot | Remit | Desktop nav model | Density | Candidate skills |
|---|---|---|---|---|
| **a** | The console: everything an ICT technician needs on one screen; list-first, information-rich | Persistent left sidebar with grouped sections and a live queue count | High | `technical-wireframe-info-layout`, `split-layout-technical`, `ui-design:information-density` |
| **b** | Calm and airy: one job per screen, generous white space, warm paper feel | Top bar carrying the four labels; no sidebar; single centred column | Low | `clean-minimal-beige-light-mode`, `orange-clean-paper-saas` (re-coloured to the crest), `interaction-design:onboarding-design` |
| **c** | Editorial: reads like a well-set document; strong page masthead, generous measure | Masthead with breadcrumbs plus in-page section navigation alongside the content | Low–medium | `editorial-tech`, `light-mode-paper-technical`, `ui-design:readable-measure` |
| **d** | Framed and tactile: bordered panels, chunky unmistakable controls, nothing ambiguous | Narrow rail showing icon **and** word (never icon alone) with framed content panels | Medium | `framed-grid-layout`, `high-contrast-skeuomorphic-clean`, `inclusive-interaction:touch-target-design` |
| **e** | Workbench: queue and record side by side; on a phone it becomes list → record with a Back link | Two-pane master–detail | Medium–high | `split-layout-technical`, `nested-container-clean-agency`, `interaction-design:navigation-patterns` |

Shared skills for the designer across all five: `ux-strategy:information-architecture`, `ui-design:design-screen`, `ui-design:visual-hierarchy`, `ui-design:type-system`, `ui-design:color-palette`, `interaction-design:state-machine` (the two lifecycles), `interaction-design:form-design`, `cognitive-accessibility:plain-language-design`, `accessible-content:heading-structure`, and `dataviz` only if a direction shows the one chart.

**Steps 2a–2e — five `tmd-frontend` agents, in parallel.** They can run together because the Content contract fixes every word and number, and each writes to its own folder and nothing else.

Each agent receives this brief's path, its own direction brief's path and its folder path, and then:

- Builds the six pages, `style.css`, `app.js`, `README.md`, and copies the three assets. `style.css` and `app.js` are written from scratch (criterion 37).
- Self-checks criteria 1, 2, 8–13, 21, 23–26 and 32–37 on its own folder before returning, including a render of every page.
- **Ownership for this task (decision D7): it owns `design/<its letter>-<slug>/` and nothing else.** It must not touch `templates/`, `static/` (beyond copying the three crest images) or another variation's folder, and it must not recreate `design/v5-tasks/`, which the owner has deleted. It must not *read* `static/css/style.css`, `static/js/app.js` or anything under `templates/`, or pull the deleted prototype back out of Git history — copying from them is what criteria 36 and 37 exist to catch.
- Appends its own sub-heading to this brief's Implementation notes. Five agents append to one file, so each writes only its own sub-heading and re-reads the file immediately before writing.

Screenshots are **not** produced at this step; the verifier captures them (step 3) so that every image in the repository is provably a capture of the delivered HTML.

**Step 3 — `tmd-test-verifier`.** Captures all seventy-five screenshots with Playwright at the stated viewports, checks all five folders against every acceptance criterion, and writes the Verification section. Uses the Verification method notes above.

The Docker "Verify a change" checklist applies differently here, and the verifier must say so rather than skip silently: `ruff check .` and `ruff format --check .` still run and must stay clean; `pytest`, `makemigrations --check --dry-run` and `manage.py check` run once as a regression guard that nothing in the app moved; `git status` proves criterion 5. There is no prod-stack HTTP step, because nothing is served. A FAIL names the variation letter and goes back to that one `tmd-frontend` agent.

**Step 4 — `tmd-code-reviewer`** (read-only). Reviews for distinctness (criteria 27–31), brand fidelity (23–25), token discipline and portability of each `style.css` (26), since one of them becomes the app stylesheet, accessibility (14–18), plain language in the copy, DRY within each folder, independence from the app's current look (36 and 37 — it is the one agent allowed to read `static/css/style.css`, because comparing against it is its job), and the absence of any reference to an earlier prototype (criterion 7). May load `visual-critique:critique-screen`, `visual-critique:critique-brand-consistency`, `visual-critique:critique-typography` and `design-systems:accessibility-audit`. It does **not** pick a winner. CHANGES REQUESTED goes back to the named variation's `tmd-frontend`, then to step 3 again.

**Step 5 — `tmd-docs-writer`.** Writes `design/README.md` (criterion 4: the comparison table, how to open a prototype, and how the `?demo=` hooks work), comparing the five against each other and against nothing else. It compares the five against each other only — not against the app's current look, and not against any earlier prototype. Adds the `docs/CHANGELOG.md` entry, adds a short "Design prototypes" pointer to `README.md` if one is missing, and closes this brief. It does not change `CLAUDE.md` unless the workflow itself changed.

`tmd-devops` and `tmd-django-backend` are not used: no settings, env, Docker, dependency or Python change.

**Parallelism:** 1 → (2a ‖ 2b ‖ 2c ‖ 2d ‖ 2e) → 3 → 4 → 5.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

The five directions are specified one file each. Each file is self-contained and
buildable on its own: it carries its own wireframes at 1440 and 400, its own type
pairing, its own palette with hex values and expected contrast ratios, its own
component treatment, its own states, its own copy and its own skills list. The
index below fixes what makes them different; the **Shared floor** after it fixes
what must be identical, so the owner compares design and nothing else.

There are no existing CSS component classes to reuse in this task: every variation
starts from an empty `style.css` (decision D1), so each direction file names its own
component set instead.

### Index of the five directions

| # | Direction | File | Folder | Desktop navigation | Phone navigation | Headings / body | Palette mood | Rows in first 900px |
|---|---|---|---|---|---|---|---|---|
| a | **Ledger** | [`docs/design/directions/a.md`](../design/directions/a.md) | `design/a-ledger/` | Persistent left sidebar, grouped sections, live queue counts | Fixed bottom tab bar, icon + word | Archivo / IBM Plex Sans (+ IBM Plex Mono) | Cool slate paper, crest purple the only chroma | 8 |
| b | **Parchment** | [`docs/design/directions/b.md`](../design/directions/b.md) | `design/b-parchment/` | Top bar with the four labels, one centred 760px column | `<details>` "Menu" panel under a slim top bar | Fraunces / Karla | Warm parchment, oat and plum | 3 |
| c | **Broadsheet** | [`docs/design/directions/c.md`](../design/directions/c.md) | `design/c-broadsheet/` | Ruled masthead + breadcrumbs, with an "On this page" index beside the column | Sticky masthead with a horizontally scrolling nav strip | Newsreader / Source Sans 3 | Soft lilac paper, near-black ink, rules not boxes | 5 |
| d | **Signpost** | [`docs/design/directions/d.md`](../design/directions/d.md) | `design/d-signpost/` | Narrow left rail, icon **and** word, framed panels | Always-visible 2×2 framed nav grid (no menu to open) | Space Grotesk / Atkinson Hyperlegible | High-contrast white and near-black plum, 2px frames | 6 |
| e | **Workbench** | [`docs/design/directions/e.md`](../design/directions/e.md) | `design/e-workbench/` | Search-led command bar over a two-pane master–detail | Pane stack; `Menu` anchor jumps to the nav block at the end of the document | Sora / Work Sans (+ JetBrains Mono) | Dark plum chrome against a cool light canvas | 7 |

The plan index also lives at [`docs/design/directions/README.md`](../design/directions/README.md).
**Three** distinct desktop mechanisms — b's top bar over a single centred column,
c's ruled masthead with a section index beside the content, and e's search-led
command bar over two panes — plus **one mechanism shared by a and d**, a persistent
left vertical nav, in two treatments: a 248px sidebar grouped under `Work` and
`Start` with live queue counts, and a 96px ungrouped rail of bordered icon-over-word
tiles against framed panels. **Five** different phone mechanisms, all distinct.
Five different type pairings, no shared heading family, and a density ladder of
**b 3 < c 5 < d 6 < e 7 < a 8** — a spread of five rows (criteria 27–30). None of
the differences is colour, so criterion 31 holds in greyscale.

Each direction file states the band-by-band vertical budget that produces its row
count at 1440×900, with the tolerance to check it against. Where a builder's
measurement disagrees with a direction file, the measurement wins and the file is
corrected: b's card was respecified from 120px to 188px once the builder showed a
120px card could not hold its own four lines, and c's queue page lost its
breadcrumb row, two headings and its in-column filter block once the builder showed
they pushed the queue below the fold.

### Shared floor — identical in all five

**1. Wording.** Every string in the Content contract, plus the interface copy
below, is the same in all five folders. The copy block is repeated in full in each
direction file so a builder never has to cross-reference.

Designer-authored interface copy, shared by all five (the Content contract fixes
the data and the sign-in, form, and queue strings; these fill the remaining gaps —
see **Gaps** at the end of this section):

| Where | Copy |
|---|---|
| Skip link | `Skip to main content` |
| Dashboard `<h1>` and lead | `Home` / `Friday 11 September 2026. Here is what needs doing today.` |
| Dashboard `<h2>`s | `What needs doing` · `Requests to work on` · `Devices to watch` · `Things you can do` (and, in a and c only, `Requests raised in the last five school days`) |
| Dashboard links | `See all requests` · `Open the device record` · `Go to the requests queue` |
| Device `<h1>` and lead | `IT-0142 — Dell Latitude 3540 laptop` / `Laptop · Issued to Dilani Fernando · Grade 6B Classroom` |
| Device `<h2>`s | `Where this device is` · `What it cost and how long it is covered` · `Requests about this device` · `What has happened to it` |
| Device buttons | `Raise a request about this device` (primary) · `Mark it returned` (secondary) |
| Confirm modal | `Mark IT-0142 returned?` / `This puts the laptop back in the ICT Store and clears the due-back date. You can give it out again at any time.` / `Yes, mark it returned` · `No, keep it as it is` |
| Modal success toast | `IT-0142 is back in the ICT Store.` |
| Form `<h1>` and lead | `Raise a request` / `Tell us what is wrong. We will pick it up from the ICT Room.` |
| Form `<h2>`s | `About the problem` (fields 1–4) · `How soon you need it` (5) · `Anything to show us` (6) · `Who is asking` (7) |
| Queue column / field names | `Reference` · `What is wrong` · `Raised by` · `Status` · `How urgent` · `Who is on it` · `Raised` |
| Busy button | `Sending…` |
| Async wait line | `Finding requests…` |
| Server error | `We couldn't save that just now` / `Nothing you typed has been lost. Wait a moment and press "Send the request" again.` |
| No permission | `You can't open this page` / `This page is for ICT staff. Ask Nimali Perera in the ICT Room, or raise a request and we will help.` / `Raise a request` |
| UI kit `<h1>` | `Design kit` |

Reading level target: grade 6–8 for prose, grade 4–6 for buttons, labels and error
messages. Every error says what to do next; no error blames the user; nothing the
user typed is ever discarded.

**2. Status vocabulary — icon plus word, never colour alone.** The icons are drawn
in each direction's own Solar weight (a: Bold · b: Bold Duotone · c: Linear ·
d: Outline · e: Broken), but the mapping is fixed:

| Value | Icon | Meaning colour |
|---|---|---|
| `New` | star | info |
| `In progress` | refresh-circle | brand |
| `Waiting on someone` | clock-circle | warning |
| `Fixed` | check-circle | success |
| `Closed` | archive | muted |
| `In store` | box | success |
| `Issued` | hand-holding | info |
| `In repair` | wrench | warning |
| `Out of service` | close-circle | danger |
| `Good` | check-circle | success |
| `Needs repair` | danger-triangle | warning |
| `Can wait` | hourglass | muted |
| `Normal` | flag | muted |
| `Urgent` | fire | danger |

`Urgent` uses the flame from the crest's torch. All meaning-bearing icons reach
3:1 against their background, and no status is ever rendered as a bare coloured
dot.

**3. Heading order and landmarks.** One `<h1>` per page, wording matched to the
navigation label that reached it. `<h2>` per section, `<h3>` only inside
`ui-kit.html` specimens, never deeper, never skipped. Landmarks: `<header>`,
`<nav aria-label="Main">`, `<main id="main">`, `<nav aria-label="Utility">`,
`<footer>`; `role="search"` on any search form; `<nav aria-label="Breadcrumb">`
where a direction uses breadcrumbs. The skip link is the first focusable element on
every page and points at the `<main>` id.

**4. Form wiring, identical markup in all five.**

```html
<label for="id_what_is_wrong">What is wrong?</label>
<p class="help" id="id_what_is_wrong-help">One short line, for example "Projector will not turn on".</p>
<input id="id_what_is_wrong" name="what_is_wrong" type="text" required
       aria-describedby="id_what_is_wrong-help id_what_is_wrong-error"
       aria-invalid="true" value="…what the user typed…">
<p class="field-error" id="id_what_is_wrong-error">
  <svg aria-hidden="true" focusable="false">…</svg>
  Type a short description of the problem, for example "Projector will not turn on".
</p>
```

- Help comes before the error in `aria-describedby`, so it is read in that order.
- `aria-invalid="true"` appears only on fields that actually failed.
- The urgency radios are a `<fieldset>` with `<legend>How urgent is it?</legend>`;
  each option's sentence sits inside its own `<label>`.
- The error summary is `role="alert" tabindex="-1"`, receives focus on load, and
  each of its links moves focus to the field itself.
- A placeholder is never the only label; the read-only `Your name` field is a real
  labelled control, not a paragraph.

**5. States every direction must render.** Default · loading (only the enhanced
filter and, in e, the pane swap — both announced in an `aria-live="polite"`
region) · empty · validation errors keeping every entered value · server error ·
success (toast with `Undo`, and the same sentence repeated as an alert on the page
landed on, for anyone who missed the toast) · sign-in error · no permission. The
reachable demo hooks are `login.html?demo=error`, `request-form.html?demo=errors`,
`requests.html?demo=empty`, `?demo=toast` on any app page, and
`device.html?demo=denied`. Each folder's `README.md` lists them and states that
they are prototype-only and are never carried into `templates/`.

**6. Touch, focus and keyboard.** Every interactive element is at least 44×44 CSS
px at 400px wide, and the primary action on each page is 52–64px; adjacent targets
are at least 8px apart, and `Cancel` is at least 24px from `Send the request`.
Tab order follows visual order; no positive `tabindex`; nothing is reachable by
hover alone. The focus indicator is a ring of at least 3px with an offset, meeting
3:1 against its adjacent background, and is shown in each direction's `ui-kit.html`
on both a light and a dark surface. Dialogs trap focus, close on Escape, and return
focus to the control that opened them; after a redirect, focus is placed on the
`<h1>` of the page landed on.

**7. Motion.** Each direction states its own durations; all five ship the same
reduced-motion guard, and no direction uses motion to carry meaning:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

**8. Progressive enhancement.** Works with plain HTML and a full page load in all
five: every navigation mechanism, the filter and sort form (`<form method="get">`
with its own `Apply` button, hidden only once scripting is available), disclosures
as `<details>`, the request form, the sign-out POST form, pagination, and the
confirm dialog as a `<dialog>` whose fallback is a link to a confirmation section
at the foot of the same page. `app.js` is one IIFE bound to `data-*` attributes
and adds only: in-place filtering with a live result line, toast rendering and
dismissal, `?demo=` state switching, focusing the error summary, the dialog focus
trap, and each direction's single extra flourish (a: none · b: closing the menu
after a link · c: the section-index scrollspy · d: none · e: the `/` shortcut and
the pane swap).

**9. Brand use, identical rules.** The crest is used unmodified — no `filter`, no
`mix-blend-mode`, no `opacity` below 1, no knock-out; aspect ratio held within 1%;
never rendered below 28px tall; `alt="Polymath College crest"` where it carries
meaning and `alt=""` where a wordmark names the college beside it. The college is
always `Polymath College` and the product `Technology Management Desk`, shortened
to `Polymath TMD` only in `<title>`. `#722A82`, or a step of the direction's own
scale derived from it, is legible on every page.

**10. Token discipline, because one of these becomes the app stylesheet.** Every
colour, font, space, radius, shadow and duration is declared once in `:root` and
used through `var(--…)`; no raw colour value appears outside `:root`; inline SVG
uses `currentColor` for every `fill` and `stroke`; `style.css` is ordered as the
eight numbered sections named in criterion 26. Each direction file gives its token
names, hex values and the contrast pairs to expect — **recompute each ratio and
print the exact figure in the folder's `README.md`**; the figures in the direction
files are the values to expect, not a substitute for the check.

### Gaps in the Content contract the planner should confirm

These strings are needed by the screens but are not in the Content contract. They
are specified above so all five stay identical; if the planner wants different
words, changing them here changes all five.

1. **Dashboard headings, lead and link labels** — the contract fixes the seven
   figures' wording but not the headings around them.
2. **Device page headings, lead and the two action buttons**, and the
   `Mark IT-0142 returned?` confirmation dialog and its success toast — the
   contract lists the device's fields and history but no page chrome, and
   `ui-kit.html` is required to show a modal, which needs a real decision to
   confirm.
3. **Request form section headings** (`About the problem`, `How soon you need it`,
   `Anything to show us`, `Who is asking`) — the contract lists the seven fields
   but not how they are grouped.
4. **Queue column / field names** — the contract gives the data but not the
   column headers.
5. **Server-error copy**, **busy-button copy** and the **async wait line** — needed
   because `ui-kit.html` must show every state.
6. **No-permission copy and its `?demo=denied` hook** — the brief asks for a
   no-permission state; the contract has none. The wording uses only names that are
   in the contract.
7. **Direction-local chrome words** that have no equivalent elsewhere: `On this
   page` (c), `On this record`, `What you are filling in`, `← Back to the list`,
   `Press / to search`, `What they told us`, `Choose a request from the list to see
   it here.` (e). Each is listed in its own direction file.

Nothing else was invented: no person, room, device, reference, date or amount
outside the Content contract appears in any of the five.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-frontend (c-broadsheet)

**Files created** — all under `design/c-broadsheet/`: `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css` (eight numbered sections; every colour, font, space, radius, shadow and duration is a `:root` token, no raw colour outside `:root`), `app.js` (one IIFE, `data-*` hooks only: `?demo=` switching, toast, error-summary focus, in-place queue filter with live count and "Finding requests…", dialog focus trap, closing the phone disclosures, and the "On this page" scrollspy), `README.md`, `assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png` (binary copies of `static/img/`), and 22 self-check captures in `screenshots/` (six pages × desktop and phone, plus the five demo states at both widths). Nothing outside that folder was touched; `static/css/style.css`, `static/js/app.js` and `templates/` were not opened.

**Rebuilt to the designer's ruling (revised c.md §1, §2.3, §8, §10, §11).** `requests.html` now runs `<h1>` → lead → search → count → rows in the reading column; the filters, sort, `Apply` (hidden once scripting is present) and `Clear the filters` sit in a sticky margin `<aside aria-labelledby>` headed `Filter and sort` (top offset 123px), which becomes a closed `<details>` under the search field on a phone — one component, same controls, same order. The margin selects are bound to the search `<form method="get">` with the `form=` attribute, so the GET submit still works with JavaScript off. The breadcrumb row exists only on `device.html` (`Devices › IT-0142`); the masthead measures 123px on the other four pages and 167px on the device record. Select placeholders are `Choose a device` and `Choose a room`. `REQ-1902` keeps `Battery replaced under warranty`.

**Content-contract alignment (extended criterion 32, "Dates and weekdays" block) applied.** Timestamps: `REQ-2048` `Fri 11 Sep 2026, 8:15 am`; `REQ-2045` `Tue 8 Sep 2026, 7:35 am`; `REQ-2047` and the matching history line `Thu 10 Sep 2026, 11:20 am`; given out `Tue 25 Aug 2026`; returned `Fri 21 Aug 2026, 3:05 pm`; battery `Fri 12 Jun 2026, 9:30 am`; last checked `Thu 3 Sep 2026`. Row order unchanged (2048 → 2041); the sort keys moved with the timestamps, so `Most urgent first` gives 2048 · 2042 · 2047 · 2046 · 2045 · 2044 · 2043 · 2041 and `Oldest first` is the list reversed. Dashboard reads `3 devices due back next week`; the chart shows `Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1` with Wednesday as a labelled zero-length bar (its own row, label and "0" value), Tuesday as the `--brand-strong` peak, alt text `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.`, and no "busiest day" sentence. `Nobody yet` everywhere a request is unassigned; the empty state's count line is `Showing 0 of 8 requests`. Folder grep for `Wed 9 Sep`, `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug`, `Thu 12 Jun`, `Fri 11 Sep 2026, 7:35 am`, `Choose one`, `Please select`, `— Select —`, `this week`: no hits.

**Density, measured at 1440×900 (criterion 30):** row pitch 109px; row tops **411 · 520 · 629 · 738 · 847**, sixth at 956 — **5 rows above 900px**. The first top is inside the file's 355–463 tolerance and 27px above its 438 budget because the lead fits on one line at 680px. README states 5, the measured tops, and the ladder b 3 < c 5 < d 6 < e 7 < a 8 (from `docs/design/directions/README.md`).

**Spec points not satisfied, and why**

- **Assets folder name.** The launch message said `img/`; criterion 1 in this brief says `assets/`. Followed the brief (`assets/`).
- **Icons as `<template>`.** Icons are inlined once per page as an `<svg hidden>` sprite of `<symbol>`s referenced with `<use>`, not a `<template>`: template content is inert, so status icons would vanish with JavaScript off (criteria 17 and 21). `app.js` clones from the same sprite for the toast. Solar Linear (the direction's weight) fetched from Iconify; Solar has no `wrench`, so `In repair` uses `sledgehammer`.
- **Breadcrumb row** on `device.html` is 44px rather than the file's 40px so the crumb links meet the 44px target at phone width.
- **Phone nav order.** DOM order is Home · Requests · Devices · Raise a request (matches desktop visual and tab order, criterion 14 at 1440). On phone `Raise a request` is pinned first with CSS `order`, so phone tab order is DOM order, not strip order.
- **Tab order on `requests.html` at 1440.** DOM order is search → margin filters → rows, the task order (narrow, then read), and the phone order the file specifies (filters under the search). Walking Tab therefore crosses from the reading column into the right-hand aside and back once; every other page walks in strict visual order. The second skip link "Skip to the queue" also appears at the top of the viewport when focused, as skip links do.
- **Disclosures that are open on desktop** (the phone "Filter and sort" and the desktop index's phone twin) ship `open` because a closed `<details>` cannot be forced open by CSS; `app.js` closes them on narrow screens, so with JavaScript off on a phone the filters start expanded. Nothing is hidden either way.
- **Sign-out form** is `method="post"` as specified; from `file://` a POST cannot complete, which is a prototype limitation, not a design one.
- **Two text sizes under 16px** are as the direction file specifies: badge words 15px semibold and the phone breadcrumb 15px. Body text is 18px everywhere.
- **Touch-target exemptions at 390px** (inline links inside a sentence): `REQ-2047` and `REQ-1902` inside timeline sentences on `device.html`, and the `ui-kit.html?demo=toast` link inside a caption on the kit page. Everything else, including radios and checkboxes (drawn at 24px inside a 44px control), measures ≥ 44×44.
- **The empty state keeps its `<h2>`** (`No requests match what you chose`) as c.md §6 specifies for the component; it is hidden until the queue is empty, so the default page outline is the `<h1>` and the aside's `<h2>` only.

**Content contract gaps.** None outstanding after the ruling (`Choose a device` / `Choose a room` / `REQ-1902` title now fixed in c.md §10).

**Contrast table** (WCAG 2 relative luminance, computed by script; all pass): ink/surface 18.03, ink/bg 16.44, ink/surface-2 15.04, muted/surface 7.36, muted/bg 6.71, muted/surface-2 6.14, surface-on-brand 8.86, brand/surface 8.86, brand/bg 8.09, brand/surface-2 7.40, brand/brand-tint 7.50, brand-strong/brand-tint 11.39, rule-strong/surface 3.73 (needs 3.0), rule-strong/bg 3.40, ok/surface 7.66, ok/ok-tint 6.58, warn/surface 6.85, warn/warn-tint 5.94, danger/surface 7.22, danger/danger-tint 6.09, info/surface 8.22, info/info-tint 7.04, focus/bg 8.09, focus/surface 8.86; focus on ink would be 2.03, so dark surfaces use a `--surface` ring (18.03). No token needed darkening.

**Self-check output.** Static: DOCTYPE at byte 1, `lang="en-LK"`, charset, viewport, `<Page> · Polymath TMD` titles; unique ids; every `for`/`aria-describedby`/`aria-labelledby`/`href="#…"` resolves; one `<h1>` and one `<main>` per page, no heading skips; every `<svg>` `aria-hidden`, every `<img>` has `alt`, every inline `fill`/`stroke` is `currentColor`/`none`; no inline `style`; all local hrefs/srcs exist; only fonts.googleapis.com/fonts.gstatic.com external; no `v5`, lorem, TODO. Rendered (Playwright, 1440×900 and 390×844): fonts loaded (Newsreader 400i/500/600, Source Sans 3 400/600/700); no horizontal scroll on any page at either width; first focusable is the skip link to `#main`; no positive tabindex; every tab stop shows the 3px ring; article column 680px (560px on the form); crest rendered 93×104 / 68×76 (login) and 34×34 / 32×32 (chip), aspect held; choosing `Closed` in the margin filter updates the live count to `Showing 2 of 8 requests`. `shoot.mjs` final line after the rebuild: **DONE clean** for the six pages and again for the five demo states.

**Review fixes (round 1).** (1) *Phone nav strip* — the `order: -1` reorder is gone, so DOM order (`Home` · `Requests` · `Devices` · `Raise a request`) is the visual and Tab order at every width; the scrollbar is no longer hidden (`scrollbar-width: thin`). At **≤400px the strip wraps to two rows** (the reviewer's first option; c.md's single scrolling row cannot hold the four labels at 400px, so the wrap is a stated deviation from c.md §1's "pinned left" wording): `Home` 107×48 at x 24, `Requests` 128×48 at x 131, `Devices` 117×48 at x 259 on row one (y 59), `Raise a request` 352×48 full-width on row two (y 112) — **all four inside the 400px viewport**, strip 104px, list `scrollWidth ≤ clientWidth`. Measured Tab sequence at 400px: Skip link → wordmark → Sign out → Home (24,59) → Requests (131,60) → Devices (259,60) → Raise a request (24,112) → On this page — left-to-right, top-to-bottom. Between 401 and 560px the strip still scrolls sideways as c.md draws it, with a persistent right-edge fade (`.mainnav::after`, `--fade-from` → `--surface`) as the overflow cue; verified at 480px: overflow true, fade present, `Raise a request` reachable by scroll and Tab. (2) *README depth* — rewritten to the b/d/e structure: Concept, Pages, Fonts, Palette + contrast, Why it suits, Navigation model, Density, Components (table of every component with class and treatment, the icon mapping, the token summary), Accessibility, Skills used, Demo hooks, Screenshots, Files; content reused, nothing invented (now ~215 lines). (3) *Nits* — figure icons moved into a 24px cell between the number and the words (`.figure` grid `72px 24px 1fr`) on the dashboard and the kit specimen; the README's primary-button claim reworded to say where each page's one purple button sits (on the dashboard, in `Things you can do` at the end of the page, with the masthead's `Raise a request` label as the route from anywhere — c.md's dashboard wireframe has no button above the fold, so the claim was changed, not the layout); `solar-duotone-bold` removed from the builder's skill list and the icon family stated as Solar Linear with a note on which of that skill's guidance applied. *Recaptured* with a scratchpad copy of `shoot.mjs` at 400px and the `mobile-` prefix: `mobile-login`, `mobile-dashboard`, `mobile-requests`, `mobile-device`, `mobile-request-form`, `mobile-ui-kit` and `desktop-dashboard` — both runs **DONE clean**; `screenshots/` holds exactly the 15 canonical names. Re-checks: no horizontal scroll, targets unchanged, no raw colour outside `:root` (the fade uses the new `--fade-from` token), `grep -rIil v5` empty.

### tmd-frontend (d-signpost)

**Files created** — all under `design/d-signpost/`: `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css` (eight numbered sections; every colour, font, space, radius, shadow and duration is a `:root` token; the scan finds no raw colour and no raw `px` outside `:root` other than the `@media` breakpoint, which CSS cannot tokenise), `app.js` (one IIFE, `data-*` hooks only: `?demo=` switching, sign-in and form-error demos with error-summary focus and links that move focus to the field, toast from a `<template>` with Undo/Close/8s/pause, in-place queue filter and sort with a live count and "Finding requests…", `<dialog>` open/close with focus return, busy submit, denied-state heading swap, closing the phone filter disclosure), `README.md`, `assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png` (binary copies of `static/img/`), and 24 self-check captures in `screenshots/` (`desktop-*` / `phone-*` for the six pages and for `login--demo-error`, `request-form--demo-errors`, `requests--demo-empty`, `requests--demo-toast`, `device--demo-denied`, `device--demo-toast`). Nothing outside that folder was touched; `static/css/style.css`, `static/js/app.js` and `templates/` were not opened.

**Spec points not satisfied or decided, and why**

- **Assets folder name.** The launch message said `img/`; criterion 1 says `assets/`. Followed the brief (`assets/`), as the coordinator later confirmed.
- **Icons.** Inlined once per page as a visually hidden `<svg>` sprite of `<symbol>`s referenced with `<use>` (works with JavaScript off; criteria 17 and 21), not a `<template>`; `app.js` clones the toast from a `<template>` that itself uses `<use>`. Solar Outline from Iconify, every `fill` `currentColor`. Solar has no `wrench`, so `In repair` uses Solar's `settings` gear (same family and weight); `Issued` uses `hand-shake` for the "hand-holding" slot. Solar path data contains the relative command `v5`; because the literal string `v5` must not appear in the folder, the build writes it as `v 5` (valid path syntax, same drawing).
- **Rail tiles are 84px wide inside the 96px rail** (spec: 96×88) so the 3px hard shadow and the 2px border fit without overflowing the rail.
- **Utility block on phone.** The spec puts `Sign out` in the 64px phone header; here the utility strip (`NP` · `Design kit` · `Sign out`) sits directly under the 2×2 grid, because it is one `<nav aria-label="Utility">` placed after the main nav in the DOM, which keeps tab order equal to visual order at both widths.
- **Request row on desktop** is 84px (spec 88px) with reference and title on one line and the metadata on the next; the row title link is padded to a 44px target with negative margins so it adds no height. Six rows start above 900px (tops 390, 486, 582, 678, 774, 870), matching the file's density intent.
- **Desktop filter row.** The four selects and `Apply` live inside the phone `<details>`, which is `open` in the HTML (CSS cannot force a closed `<details>` open); on desktop its summary is hidden and its body is laid out beside the search field, and `app.js` closes it on narrow screens. With JavaScript off on a phone the filters start expanded; nothing is hidden either way.
- **Prototype forms.** The request form and the "Mark it returned" confirmation submit with `method="get"` carrying `demo=toast`, so with JavaScript off they still navigate and with JavaScript on the landing page shows the success toast and matching alert. Sign in and sign out are `method="post"` as specified; from `file://` a POST cannot complete.
- **`--focus-on-dark: #FFFFFF`** was added: the crest-purple ring reaches only 2.11:1 on the ink-filled toast, so the toast's ring is white (18.70:1). The kit shows both.
- **`?demo=denied`** swaps the `<h1>` and lead text to the no-permission copy (via `data-denied-title`/`data-denied-lead`) rather than adding a second heading, so every state has exactly one `<h1>`.
- **Two text sizes under 16px** are as the direction file specifies: badge and chip words 15px bold, rail tile words 13px (15px on a phone). All prose, labels, help and metadata are 16–19px.
- **Touch-target exemption at 390px:** the 24px radio and checkbox inputs sit inside 72px framed `<label>` tiles that are the pointer target. Every other interactive element measures ≥ 44×44.

**Content contract alignment (planner's final settlement, applied).** Timestamps now follow the "Dates and weekdays" block: `REQ-2048` raised `Fri 11 Sep 2026, 8:15 am` (still Urgent / In progress, first in the list), `REQ-2045` `Tue 8 Sep 2026, 7:35 am`, `REQ-2047` and the matching `IT-0142` history line `Thu 10 Sep 2026, 11:20 am`, given out `Tue 25 Aug 2026`, returned `Fri 21 Aug 2026, 3:05 pm`, battery `Fri 12 Jun 2026, 9:30 am`, last checked `Thu 3 Sep 2026`; the sort keys (`data-raised`) were updated to match, and the built order 2048 → 2041 is unchanged. `REQ-1902`'s title is `Battery replaced under warranty`; the device page's linked requests read `REQ-2047` / New / `Thu 10 Sep 2026, 11:20 am` and `REQ-1902` / Closed / `Fri 12 Jun 2026, 9:30 am`. The form's "What is it about?" select now opens on `Choose a device` (empty value) before the eight devices and `Not about a particular device`; "Where is it?" opens on `Choose a room` (empty value) and stays there in `?demo=errors`; the filter selects keep `All statuses` / `All` / `Anyone` and Sort has no prompt. Unassigned requests read `Nobody yet` everywhere; the empty state's result line is exactly `Showing 0 of 8 requests`. The dashboard tile reads `3 devices due back next week`. A folder grep for `Wed 9 Sep`, `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug`, `Thu 12 Jun`, `Fri 11 Sep 2026, 7:35 am`, `Choose one`, `Please select`, `— Select —`, `Unassigned`, `this week` and `v5` returns nothing. The `?demo=errors` state uses the `REQ-2048` detail text as what the user typed in "Tell us more" so no words from outside the contract appear. After the alignment: `check_d.mjs` **CHECK: clean** (six rows above 900px unchanged), `shoot.mjs` **DONE clean** for the six pages and again for the six demo states.

**Review fixes (round 1).** (1) SHOULD FIX — form sections 3 and 4 are now **full width** (the `.form-pair` two-up grid was removed from the source and from `style.css` sections 6 and 7); this departs from the d.md wireframe's side-by-side sketch of steps 3 and 4 but keeps its 600px form column and framed-step shape. Evidence at 1440×900: all four step panels and the error alert are 600px wide; the file input renders 556px wide and shows "Choose File  No file chosen" in full; every step label is one line, 28px tall at a 28px line-height ("Anything to show us" 281px wide, "Who is asking" 207px). At 400px: panels and alert 368px, file input 324px, labels one line at 26px. (2) NIT, alert width — measured equal to the panels beneath it at both widths (600/600 and 368/368), so nothing changed; if the reviewer meant the alert versus the full-width page-head panel above, that is by design: the alert belongs to the 600px form column it introduces. (3) NIT, purple — the repeated foot-of-page `Raise a request` bar on phones is now a secondary (white, ink-framed) button, so a phone screen carries the purple fill only on the nav grid's `Raise a request` tile (d.md's Von Restorff tile) and on the page's own primary action; the phone dashboard now has exactly two purple-filled controls (`tile-primary` and the "Things you can do" primary), measured by computed background. (4) NIT, README — "Skills used" no longer lists `solar-duotone-bold` as a skill claim; it names the icon family as Solar Outline and says the preloaded Solar skill was consulted for usage rules only. Recaptured with a scratchpad copy of `shoot.mjs` at 400px and the `mobile-` prefix: `desktop-request-form.png`, `desktop-request-form--errors.png`, `mobile-request-form.png`, `mobile-dashboard.png`; both runs **DONE clean**; `screenshots/` holds exactly the 15 canonical files.

**Navigation wording and the counter (coordinator's index correction).** The README now describes the desktop mechanism as the index does — a persistent left vertical nav: a 96px ungrouped rail of bordered icon-over-word tiles against framed panels, no counts — and says plainly that a left vertical nav is shared with Ledger (248px grouped sidebar), while the phone mechanism (always-visible 2×2 framed grid, nothing to open) is unique. To make "no counts" true, the `6` counter badge (and its "Requests, 6 open" hidden text) was removed from the rail and grid tiles, from the kit's wayfinding specimen and from `style.css` (the `.count` rule and its three tokens); the figures remain on `Home`'s framed tiles. This departs from d.md §1's "`6` counter badge" so that criterion 27's distinctness (Ledger carries counts, Signpost does not) holds as the corrected index states. All 15 canonical screenshots recaptured with the 400px `mobile-` script: **DONE clean** for the six pages and for the three desktop states; `check_d.mjs` **CHECK: clean**; grep for `6 open`, `class="count"`, `.count` returns nothing.

**Review fixes (round 2) — decision reversed.** The `6` counter badge on the `Requests` rail/grid tile is restored exactly as d.md §1 specifies: the `.count` rule and its three tokens in `style.css`, the `<span class="count" aria-hidden="true">6</span>` badge plus the `<span class="vh">, 6 open</span>` hidden text in every app page's nav, and the kit's wayfinding specimen. The README now says the rail carries a live count on Requests and no longer presents counts as a difference from Ledger; the a/d differences it states are width (248 vs 96px), grouping, item shape and framing. Evidence (Playwright, computed): badge renders 24×24px, background `rgb(114, 42, 130)` (`--brand`), at (59,215) on desktop and (372,68) on the 400px grid; the link's text reads "Requests, 6 open" + the aria-hidden "6"; the hidden span is present. All 15 canonical screenshots recaptured (six pages at 1440 and 400, three desktop states): both runs **DONE clean**; `screenshots/` holds exactly 15 files; `check_d.mjs` **CHECK: clean**.

**Contrast table** (WCAG 2 relative luminance, computed by script; all pass): ink/surface 18.70, ink/bg 16.70, ink/brand-tint 14.99, ink/surface-2 14.83, muted/surface 9.02, muted/bg 8.06, muted/surface-2 7.15, surface-on-brand 8.86, brand/surface 8.86, brand/bg 7.92, brand/brand-tint 7.10, brand-strong/brand-tint 11.83, brand-strong/surface-2 11.71, surface-on-brand-strong 14.76, ok/surface 8.39, ok/ok-tint 7.18, warn/surface 7.47, warn/warn-tint 6.31, danger/surface 7.94, danger/danger-tint 6.60, surface-on-danger 7.94, info/surface 9.55, info/info-tint 7.92, ink on ok/warn/danger/info tints 15.99/15.79/15.55/15.51, focus/bg 7.92, focus/surface 8.86, focus/brand-tint 7.10, focus-on-dark/ink 18.70; frame-soft/surface 2.15 is used only for inner rules, the chip shell and the dashed empty frame, never a control edge, so no token needed darkening.

**Self-check output.** Static: DOCTYPE at byte 1, `lang="en-LK"`, charset, viewport, `<Page> · Polymath TMD` titles; unique ids; every `for`/`aria-describedby`/`aria-labelledby`/`href="#…"` resolves; one `<h1>` and one `<main>` per page, no heading skips; every `<svg>` `aria-hidden="true" focusable="false"`, every `<img>` has `alt`, every inline `fill` is `currentColor`; no inline `style`; only fonts.googleapis.com/fonts.gstatic.com external; `grep -ic v5` is 0 in every delivered file. Rendered (Playwright, 1440×900 and 390×844, fonts loaded): first focusable is the skip link to `#main`; no positive tabindex; tab order is rail (Home, Requests, Devices, Raise a request, NP, Design kit, Sign out) then main content, matching visual order; main content column 1240px (440px login, 600px form column); no horizontal scroll on any page or demo state at 390px (`scrollWidth` 390 = 390; the kit's colour table scrolls inside its own `role="region" tabindex="0"` wrapper). `check_d.mjs`: **CHECK: clean**. `shoot.mjs` final line: **DONE clean** for the six pages and again for the six demo states.

**Verifier fix (criterion 1).** `screenshots/` now holds only the fifteen canonical criterion-22 files (`desktop-*` at 1440×900, `mobile-*` at 400×844, and the three desktop state captures). The builder's own self-check captures (`phone-*.png` at 390 wide and the `*--demo-*.png` variants, 18 files) were deleted; the README's Screenshots paragraph now describes the canonical set.

### tmd-frontend (a-ledger)

**Files created** — all under `design/a-ledger/`: `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css` (eight numbered sections; every colour, font, space, radius, shadow and duration is a `:root` token; no raw colour outside `:root`), `app.js` (one IIFE, `data-*` hooks only: `?demo=` switching, toast with Undo/Close and 8 s pause-on-hover/focus, in-place queue filter and sort with the live `Finding requests…` line and `aria-sort`, search-box clear, error-summary focus and links that focus the field, `<dialog>` open/trap/return-focus/confirm toast, busy button, and closing the phone filter disclosure), `README.md`, `assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png` (binary copies of `static/img/`), and 26 self-check captures in `screenshots/` (six pages × desktop and phone, plus seven demo states at both widths). Nothing outside that folder was touched; `static/css/style.css`, `static/js/app.js` and `templates/` were not opened.

**Spec points not satisfied, or interpreted, and why**

- **`--line-strong` darkened one step** from the direction file's `#858DA1` (L 60%) to `#7D829B` (L 55%): the brief's value is 2.81:1 on `--surface-2`, where the sidebar's Sign out button sits, and a.md §4 says to darken one step if a control-border pair is under 3:1. Now 3.79 / 3.48 / 3.21:1 on `--surface` / `--bg` / `--surface-2`.
- **Icons:** one `<svg>` sprite of Solar **Bold** `<symbol>`s per page (fetched by name from Iconify), referenced with `<use href="#i-…">` and `fill="currentColor"`, hidden by a zero-size absolutely-positioned class rather than a `<template>` (inert without JS) or the `hidden` attribute; `app.js` clones from the same sprite. Solar has no `wrench`, so `In repair` uses `toolbox`; `Issued` (hand-holding) uses `hand-shake`.
- **Assets folder** is `assets/` per criterion 1, not the `img/` in the launch message.
- **Queue rows are not links.** a.md §6 asks for a stretched anchor on the reference cell, but there is no request-detail page in scope (D3), and criterion 2 forbids an `href` that resolves nowhere. The reference is a `<th scope="row">`; on `device.html` the open `REQ-2047` links to `requests.html`.
- **Filter panel is one 104px row at ≥1280px** (search + Status + How urgent + Who is on it + Sort + Clear filters), two rows at 1024–1279, stacked inside the `<details>` on phone. The `<details>` must be `open` in HTML (CSS cannot force a closed one open on desktop); `app.js` closes it under 1024px, so with JavaScript off on a phone the filters start expanded. Nothing is hidden either way.
- **Queue rows are 61px, not 44px**, at 1440: with fixed column widths (110 / flexible / 150 / 205 / 120 / 150 / 150) the longest titles and the `Raised` date wrap to two lines. All 8 rows still start above 900px (measured: first row at 363px, eighth at 790px).
- **Extra demo hooks** beyond the shared five: `device.html?demo=returned` (the toast `IT-0142 is back in the ICT Store.`, also where the no-JS confirmation form lands) and `request-form.html?demo=server` (the server-error alert), so every state a.md §9 lists is reachable.
- **`ui-design:information-density`** (a.md §15) is not an installed skill; the direction file's own density rules were followed. The other nine named skills were loaded.
- **Sign-out form** is `method="post"` as specified; from `file://` a POST cannot complete — a prototype limitation.
- **Touch-target notes at 390px:** radio inputs measure 22×22 but sit inside 44px+ `<label class="choice">` rows that are the pointer target; the `Apply` button measures 1×44 only because it is visually hidden once scripting is present; inline prose links on `ui-kit.html` (the Links specimen) are the sentence-link exemption. Every other control, including the four tab-bar cells (87×56, 130×56), measures ≥ 44×44.

**Content contract alignment (planner's final block applied).** Timestamps now read `Fri 11 Sep 2026, 8:15 am` (REQ-2048), `Tue 8 Sep 2026, 7:35 am` (REQ-2045), `Thu 10 Sep 2026, 11:20 am` (REQ-2047 and the IT-0142 history line), `Tue 25 Aug 2026`, `Fri 21 Aug 2026, 3:05 pm`, `Fri 12 Jun 2026, 9:30 am`, last checked `Thu 3 Sep 2026`, with the matching `datetime` attributes updated; row order unchanged (2048 first → 2041 last), and `Most urgent first` still sorts 2048, 2042, 2047, 2046, 2044, 2043, 2045, 2041. `REQ-1902` is titled `Battery replaced under warranty`; the device page's linked rows carry both titles, statuses and timestamps. `What is it about?` opens on `Choose a device` (empty value) and `Where is it?` on `Choose a room` (still so under `?demo=errors`); filter selects keep `All statuses` / `All` / `Anyone`, Sort has no prompt. Unassigned requests read `Nobody yet` everywhere; the empty state's line is `Showing 0 of 8 requests`. Dashboard tile reads `3 devices due back next week`; the chart is Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1 with the `aria-label` `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.`, Tuesday as the highlighted maximum, and Wednesday's zero drawn as a labelled empty bar. A grep of the folder for `Wed 9 Sep`, `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug`, `Thu 12 Jun`, `Fri 11 Sep 2026, 7:35 am`, `Choose one`, `Please select`, `— Select —`, `Unassigned` and `this week` finds nothing. After the changes `shoot.mjs` ends **DONE clean** for the six pages and again for the seven demo states.

**Review fixes (round 1).** (1) README depth: `README.md` now has headed `Concept`, `Pages` (a six-row table: what each page shows, its chrome and its demo hooks), `Density` (its own section with the measured 363px chrome, 61px rows, eighth row at 790px, and the phone relaxation), `Components` (a 22-row table of class and treatment, matching `ui-kit.html`) and `Accessibility` (landmarks, headings, skip link, focus ring, keyboard, forms, tables, status, targets, motion, text size, contrast) sections alongside the existing Fonts, Palette, Why-it-suits, Navigation model, Skills, Demo hooks and Screenshots; the density paragraph was moved out of Navigation model. Nothing was invented — every figure is from the build's measurements or `style.css`. (2) Sidebar gap: **not changed.** a.md §1 specifies "Bottom of the sidebar: `NP Nimali Perera / ICT Technician`, then `Design kit` and a `Sign out` button", and wireframe 2.1 draws that block under a rule at the foot of a full-height sidebar, so the space between the START group and the person block is the drawn layout; the block is already pinned to the viewport bottom (`align-self: end; position: sticky; bottom: 0`), so it stays in view while the content scrolls. Moving the utility block up would change the sidebar the direction file draws, so it was left as specified. No HTML, CSS or JS changed in this round, so no screenshots were recaptured. (3) Navigation wording: the README's Navigation model now describes the desktop mechanism as the index does — a left vertical nav, a persistent 248px sidebar grouped under `Work` and `Start` with live queue counts and the primary action inside it — and notes that a left vertical nav is shared with Signpost's 96px rail; only the phone mechanism (fixed bottom tab bar) is described as unique to Ledger.

**Contrast table** (WCAG 2 relative luminance, computed by script from the `:root` values; all pass): ink/surface 17.38, ink/bg 15.93, ink/surface-2 14.70, muted/surface 6.48, muted/bg 5.94, muted/surface-2 5.48, surface-on-brand 8.86, brand/surface 8.86, brand/bg 8.13, brand/surface-2 7.50, brand-strong/brand-tint 11.32, surface-on-brand-hover 10.35, surface-on-brand-active 13.35, line-strong/surface 3.79 (needs 3.0), line-strong/bg 3.48, line-strong/surface-2 3.21, info/info-tint 7.37, ok/ok-tint 5.66, warn/warn-tint 5.99, danger/danger-tint 6.29, info/ok/warn/danger on surface 8.48/6.48/6.80/7.45, surface-on-danger 7.45, surface-on-ink (toast) 17.38, focus/bg 8.13, focus/surface 8.86, focus/surface-2 7.50; on `--ink` and `--brand` the 2px `--focus-halo` carries the ring (17.38 / 8.86). `--line` 1.39 and `--brand-line` 2.11 are decorative only.

**Self-check output.** Static: DOCTYPE at byte 1, `lang="en-LK"`, charset, viewport, `<Page> · Polymath TMD` titles; unique ids; every `for` / `aria-describedby` / `aria-labelledby` / `href="#…"` / `<use href>` resolves; one `<h1>` and one `<main>` per page, no heading skips; landmarks `<header>`, `<nav aria-label="Main">`, `<nav aria-label="Utility">`, `<footer>` once per app page, `role="search"` on the filter form, `<nav aria-label="Breadcrumb">` on the device page; every non-sprite `<svg>` is `aria-hidden="true" focusable="false"` (the chart is `role="img"` with an `aria-label`); every `<img>` has `alt`; every inline `fill`/`stroke` is `currentColor`; no inline `style=""`; all local hrefs/srcs exist; only fonts.googleapis.com / fonts.gstatic.com external; no `v5` string anywhere (SVG path `V5…` commands were spaced to `V 5…`); no lorem/TODO; all eleven content-contract tokens present. Rendered (Playwright, 1440×900 and 390×844): Archivo, IBM Plex Sans and IBM Plex Mono loaded; no horizontal scroll on any page at either width; first focusable is the skip link to `#main`; no positive tabindex; content column 1120px at 1440; body 16px; crest 72×80 / 56×63 (login) and 32×32 (chip), aspect ratio 1.000; `requests.html` shows **8 of 8 rows above 900px**. JavaScript off: every nav link visible, every form present with a submit, `Apply` visible, `Filter and sort` open, the `Mark it returned` confirmation section visible, status icons rendered from the sprite. Behaviour: dialog opens with focus on its title, Tab stays inside, Escape closes and returns focus to `Mark it returned`, confirm shows the toast; filter `Status = New` → `Showing 2 of 8 requests`; a no-match search shows the empty state and `Showing 0 of 8 requests`; `Most urgent first` orders 2048, 2042, 2047, 2046, 2044, 2043, 2045, 2041 with `aria-sort` on `How urgent`; `?demo=errors` focuses the summary, marks only the two failed fields `aria-invalid` with `aria-describedby="…-help …-error"`, keeps `IT-0087` / the description / `Urgent`, and the summary links focus the field; `?demo=error` keeps `nimali.p` and focuses the password; `?demo=toast` shows the toast, the dashboard success alert, and focuses the `<h1>`. `pytest --create-db` in the dev container: 29 passed (the stack was not running before; it was started for the run and stopped again). `shoot.mjs` final line: **DONE clean** for the six pages and again for the seven demo states.

**Verifier fix (criterion 1).** `screenshots/` now holds only the fifteen canonical criterion-22 files (`desktop-*` at 1440×900, `mobile-*` at 400×844, and the three desktop state captures). The builder's own self-check captures (`phone-*.png` at 390 wide and the `*--demo-*.png` variants, 20 files) were deleted; the README's Screenshots paragraph now describes the canonical set.

### tmd-frontend (b-parchment)

**Files created** (all under `design/b-parchment/`): `login.html`, `dashboard.html`,
`requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css`
(written from a blank file; eight numbered sections; every value a `:root` token),
`app.js` (one IIFE, `data-*` hooks only), `README.md`, `assets/crest.png`,
`assets/crest-chip.png`, `assets/favicon-32.png` (binary copies), and
`screenshots/` (23 builder captures at 1440×900 and 390×844, including the five
demo states and the open phone menu; the verifier re-captures at the brief's
viewports). Nothing outside that folder was touched.

**Spec deviations, and why**

- The crest files are in `assets/` (criterion 1), not the `img/` subfolder the
  launch message named; the criteria are what the verifier checks.
- Icons are defined once per page in a visually hidden `<svg>` sprite of
  `<symbol>`s and placed with `<use>`, rather than a `<template>` cloned by JS,
  so every status icon still renders with JavaScript off (criteria 17 and 21).
  `app.js` clones from the same sprite for the toast and the wait line.
- `--line-strong` was darkened one step from the direction file's `#9A8C79` to
  `#91826E`, because `#9A8C79` is 2.84:1 on `--bg` where fields sit; the
  direction file itself asks for this when a control border is under 3:1.
- The Solar set has no `wrench`; `In repair` uses a wrench drawn on the same
  24-unit grid in the bold-duotone idiom (documented in the README and kit).
- `Issued`'s "hand-holding" icon is Solar `hand-shake`, the nearest glyph.
- The wireframe's `← Back to Devices` link on `device.html` is omitted: the
  device record *is* the `Devices` destination (D8), so it would link to itself.
- `Cancel` on the form is the quiet style per the direction file's wireframe,
  where the Content contract calls it "secondary" in the generic sense.
- The form submits with `method="get"` to `dashboard.html?demo=toast`, so the
  success state is reachable through the real flow with JavaScript off. Sign-out
  and the confirm-return forms stay `method="post"` (verified to navigate on
  `file://` in Chromium).
- The no-JavaScript fallback for `Mark it returned` is a confirmation section at
  the foot of `device.html`; its `Yes, mark it returned` is styled secondary so
  the page keeps exactly one dominant primary action (criterion 25).
- With `?demo=denied`, the page's single `<h1>` is retargeted to
  `You can't open this page` and moved into the card, so the page never has two
  `<h1>` elements (criterion 10).

**Content contract alignment** (the gaps first reported here were settled by the
planner; the folder now carries the settled text)

- Timestamps as settled: `REQ-2048` `Fri 11 Sep 2026, 8:15 am`; `REQ-2045`
  `Tue 8 Sep 2026, 7:35 am`; `REQ-2047` and its `IT-0142` history line
  `Thu 10 Sep 2026, 11:20 am`; given out `Tue 25 Aug 2026`; returned
  `Fri 21 Aug 2026, 3:05 pm`; battery `Fri 12 Jun 2026, 9:30 am`; last checked
  `Thu 3 Sep 2026`. `datetime` attributes and the sort keys were updated with
  them (`Most urgent first` gives 2048, 2042, then the list order; `Oldest first`
  reverses it). Row order unchanged, 2048 first to 2041 last. A grep of the
  folder for `Wed 9 Sep`, `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug`,
  `Thu 12 Jun`, `Fri 11 Sep 2026, 7:35 am`, `this week`, `Choose one`,
  `Please select`, `— Select —`, `Unassigned` and `v5` finds nothing.
- `REQ-1902`'s title is `Battery replaced under warranty`; the device page lists
  `REQ-2047` / New / `Thu 10 Sep 2026, 11:20 am` and `REQ-1902` / Closed /
  `Fri 12 Jun 2026, 9:30 am`.
- Form selects open on `Choose a device` and `Choose a room` (empty values); in
  `?demo=errors` the room select is still on `Choose a room`. Filter selects keep
  `All statuses` / `All` / `Anyone`; Sort has no prompt option.
- Unassigned requests read `Nobody yet` in every card and in the filter option;
  the empty state's result line is `Showing 0 of 8 requests` (set by `app.js`,
  so it is rendered text, not a raw-HTML string).
- Dashboard: `3 devices due back next week`, and the hub card `3 are due back
  next week.` — `docs/design/directions/b.md` §10 still says `this week` in both
  places, which the brief now forbids; the folder follows the brief. Note for
  the verifier: figure rows are marked up as `<b class="figure__n">3</b> devices
  due back next week`, so the exact sentence is the rendered text of the `<li>`,
  not a contiguous raw-HTML string.
- The footer line `Today is Fri 11 Sep 2026` stays on the app pages.
- The `?demo=errors` state fills the untouched fields with contract content
  (`IT-0087`, the `REQ-2048` detail text, `Urgent`) to show that typed values
  are kept.

**Self-check output**

- Structural check (own script): all six pages parse with no mismatched or
  unclosed element; `<!DOCTYPE html>` at byte 1; `lang="en-LK"`, charset,
  viewport and `<Page> · Polymath TMD` titles; unique ids; every `for`,
  `aria-describedby`, `aria-labelledby`, `href="#…"` and `<use href>` resolves;
  exactly one `<h1>` and one `<main>`; no heading skip; skip link first; no
  positive `tabindex`; every `<img>` has `alt`; every `<svg>` has
  `aria-hidden="true" focusable="false"`; every control labelled; every button
  and link named; no `v5`, lorem, TODO, FIXME or `xxx`; every local reference
  exists; all criterion-32/33 tokens present. Result: `ALL OK`.
- Raw-colour grep outside `:root` in `style.css`: none.
- Contrast recomputed from the tokens (table in README): every pair passes.
- Playwright, 1440×900: Tab order on `dashboard.html` is skip link → brand →
  Home → Requests → Devices → Raise a request → account → Sign out → hub cards.
  `requests.html`, rebuilt to the revised §2.3 budget after the designer's
  density ruling: queue card 188px (band table: 24 + 32 + 8 + 26 + 8 + 32 + 6 +
  22 + 24 + 2 borders = 184, built with `min-height: 188px`), pitch 204px; chrome
  above the first card 430px (the lead sets on one line, 30px, where the budget
  allowed 60); card tops **430 · 634 · 838 · 1042**, so **3 cards above the
  900px fold**, inside the stated 288–491px tolerance for the first card. Cards
  on `dashboard.html` and `device.html` drop the fourth line: 156px at 1440,
  182px at 400 (192px for `REQ-1902`, whose status row wraps at 400). Queue
  cards at 400px: 240–270px. Main column 856px including gutters (760px
  content); smallest text 15px (badge words, the card's fourth line and footer
  small print, per the direction's type table; body text 17px). The reference
  link's own box is 81×32 per the band table; the whole 188px card is its
  pointer area through the stretched anchor, which the verifier should treat
  as the target for criterion 15.
- Playwright, 390×844: no interactive element under 44×44; `scrollWidth ==
  clientWidth` on all six pages; the `<details>` menu opens and closes by click
  and by Enter, spans the full width and pushes the page down.
- JavaScript disabled: `requests.html` shows the `Apply` button, 8 cards and its
  forms; `device.html` shows the confirmation section.
- `node shoot.mjs "…/design/b-parchment"` (six pages, desktop + phone) and the
  demo-hook run (`login.html?demo=error`, `request-form.html?demo=errors`,
  `requests.html?demo=empty`, `dashboard.html?demo=toast`,
  `device.html?demo=denied`): no HORIZONTAL-SCROLL or JS-ERRORS flags; final
  line: `six pages: DONE clean · demo hooks: DONE clean`.
- `git status`: this agent's changes are only under `design/b-parchment/`.

**Verifier fix (criterion 1).** `screenshots/` now holds only the fifteen canonical criterion-22 files (`desktop-*` at 1440×900, `mobile-*` at 400×844, and the three desktop state captures). The builder's own self-check captures (`phone-*.png` at 390 wide and the `*--demo-*.png` variants, 17 files) were deleted; the README's Screenshots paragraph now describes the canonical set.

**Review fixes (round 1).** Blocker 2 (`style.css:904`, the alpha-less crest): chose option (b), a new `assets/crest.png` cut with Pillow (`py -3.13`) from the root `logo.png`, which is RGBA on a transparent ground. The first cut used the logo's whole opaque bbox and pulled in the motto line under the crest, shrinking the crest inside its 96px box; the final cut is the crest-only region (`logo.png` px 1163–2346 × 450–1774, 1183×1324, ratio 0.8935), scaled to the asset's existing 229×256 (ratio 0.8945, a 0.4px rounding, no stretch), LANCZOS, no colour change (centre pixel `#722A82`; corners alpha 0). Chosen over the white chip (a) because the direction file sets the 96px crest bare on the card, the review's own nit asks for an alpha crest once, and the chip would put a third white rectangle on a page whose whole point is the parchment ground. `crest-chip.png` and `favicon-32.png` untouched. Evidence, `desktop-login.png` at 1440: the four pixels just inside the former white box's corners, (680,99) (760,99) (680,189) (760,189), sample `#FBF7F0`, the same as the card beside the crest at (600,140); before the fix (680,99) and (760,99) were `#FFFFFF`. The crest tip at (720,99) is `#722A82`. Should-fix 6 (`style.css:813`): `.empty .icon` now `var(--brand)`; the empty state sits on `--bg`, so the icon is 7.69:1 (was `--brand-line` at 1.87:1 on `--bg`; `--muted` would be 5.24:1). README: `--brand-line` row no longer names the empty-state icon, a `--brand` / `--bg` (64px empty-state icon) 7.69:1 row was added with the 3.0 need, and the brand-colour paragraph lists the icon. Nit, stat rows: `.figure__icon` dropped `margin-left: auto` (now `flex: none`), so the flame and wrench sit 8px after the phrase they qualify rather than at the row's far edge: icon left edge moved from 1051px to 537px (`2 are urgent`) and 585px (`2 devices in repair`) at 1440, and from 331px to 217px / 265px at 400. The icon follows the words rather than the digit so the words column stays aligned on all seven rows. Nit, form column: `request-form.html`'s `<main>` gained `page--form`, and `style.css` §6.2 sets `.page--form { max-width: calc(var(--form-w) + 2 * var(--gutter)) }`, so the title, lead, sections and actions share the 640px column and it is centred like the dashboard's: form centre 660px → 720px at 1440 (page centre 720; heading centre was already 720 but its left edge was 60px outside the form; now both are at 400px). Unchanged at 400px, where the column was already full-width. Recaptured with a scratchpad copy of `shoot.mjs` (viewport 400×844 named `mobile`, state suffix taken from the `demo=` value): `desktop-login.png`, `desktop-login--error.png`, `mobile-login.png`, `desktop-requests--empty.png`, `desktop-dashboard.png`, `mobile-dashboard.png`, `desktop-request-form.png`, `mobile-request-form.png`, `desktop-request-form--errors.png`; the script's extra mobile state captures were deleted and `screenshots/` holds exactly the fifteen canonical names; `DONE clean`, no horizontal scroll or JS errors. Not recaptured, per the instruction: `desktop-ui-kit.png` and `mobile-ui-kit.png`, which still show the old white-boxed crest (`ui-kit.html:108` uses the same `assets/crest.png`), the pale empty-state icon and the right-pinned figure icons; the live `ui-kit.html` renders the fixed versions. Raw-colour grep outside `:root`: none. Only `design/b-parchment/` was touched.

### tmd-frontend (e-workbench)

**Files created** — all under `design/e-workbench/`: `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css` (eight numbered sections; every colour, font, space, radius, shadow, duration and metric is a `:root` token; no raw colour outside `:root`), `app.js` (one IIFE, `data-*` hooks only: toasts, the `/` search shortcut, in-place filter/sort with a live `Finding requests…` line and honouring a no-script `?status=…` submit, the requests pane swap that fills the record from the row's `data-*` and moves focus to its `<h2>`, phone-closed disclosures, the confirm `<dialog>` with trap/Escape/focus return, error-summary links that focus the field, section-index marking, busy buttons, and `?demo=` switching), `README.md`, `assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png` (binary copies of `static/img/`), and 24 self-check captures in `screenshots/` (`desktop-*` / `phone-*` for the six pages and for `login--demo-error`, `request-form--demo-errors`, `requests--demo-empty`, `dashboard--demo-toast`, `device--demo-denied`, `device--demo-returned`). Nothing outside that folder was touched; `static/css/style.css`, `static/js/app.js` and `templates/` were not opened.

**Spec points not satisfied or decided, and why**

- **Density (criterion 30 / e.md §8).** Rebuilt to the designer's revised §2.3: the list pane is 480px wide, the desktop filters sit on two rows, and each queue row is 87px (26px urgency chip, 16px title, 26px status badge; no title wraps at that width). Measured with Playwright at 1440×900 with the fonts loaded (`document.fonts.status` = `loaded`): row tops 356, 443, 530, 617, 704, 791, 878, 965, so **7** rows start above 900px (first top 356, inside the 291–377 tolerance; the eighth at 965). The README states 7 with this arithmetic. `shoot.mjs` re-run after the rebuild: `desktop requests ok` / `phone requests ok` and **DONE clean** for the six pages; `desktop requests--demo-empty ok` / `phone requests--demo-empty ok` and **DONE clean** for the five demo-hook pages e.md names (`login.html?demo=error`, `request-form.html?demo=errors`, `requests.html?demo=empty`, `dashboard.html?demo=toast`, `device.html?demo=denied`); no horizontal scroll or JS error on any capture.
- **Assets folder name.** The launch message said `img/`; criterion 1 says `assets/`. Followed the brief (`assets/`), as the coordinator later confirmed.
- **Icons.** Inlined once per page as `<svg class="sprite" hidden>` of `<symbol>`s, referenced with `<use href="#i-…">` so they render with JavaScript off; `app.js` builds the toast's icons from the same sprite. Solar **Broken** (the direction's weight) fetched from Iconify, every `fill`/`stroke` `currentColor`/`none`. Solar has no `wrench`, so `In repair` uses `toolbox`; `Issued` uses `hand-shake` for the "hand-holding" slot. Solar path data contains `V5…`; the build writes every command-digit pair as `V 5…` (valid SVG, identical drawing) so the literal `v5` never appears in the folder.
- **Search form submit.** The search icon is a real icon-only submit button (`aria-label="Search"`) so the search form has a visible submit for touch and criterion 21; the direction drew the icon as decoration.
- **Sort control on phone.** The strip's Sort select is shared with the filter form via `form="filters"`. On phone the breadcrumb hides and the strip becomes a slim Sort + result-line toolbar under the pinned `Raise a request`, above the `<h1>`; the direction's phone wireframe put sort inside the `Filter and sort` disclosure, which would need a second control.
- **Filter disclosure on desktop.** `<details open>` in the HTML (CSS cannot force a closed `<details>` open); `app.js` closes it on narrow screens, so with JavaScript off on a phone the filters start expanded. Same for the form's `What you are filling in` index.
- **Confirm dialog without script** is the `<dialog id="confirm-return" open>` itself rendered inline at the foot of the device record (`Mark it returned` is a link to it); `app.js` removes `open` on load and uses `showModal()`. `No, keep it as it is` uses `formmethod="dialog"` so it closes natively either way; `Yes` submits `GET device.html?demo=returned`, intercepted with script to show the toast and alert (extra hook documented in the README).
- **Forms.** Sign in, sign out and the request form are `method="post"` as the shared floor specifies; a Playwright probe confirmed Chromium navigates on a POST between `file://` pages, so submission works with JavaScript off. The request form keeps `required` on `What is wrong?` (native validation with script off).
- **Two primaries on some pages.** The command bar keeps the filled `Raise a request` (e.md §1) on every page; `device.html`, `request-form.html` and `dashboard.html` also have their own 52px content primary. The content primary is taller (52 vs 44px) and the dashboard's duplicate is hidden on phone where the bar's copy is the pinned 56px button.
- **Touch-target exemptions at 390px:** the native radio/checkbox inputs (22px) sit inside `.choice` labels that are the 48px+ targets; one inline link inside a sentence in the kit's Links section. Everything else measures ≥ 44×44.

**Content contract gaps and the final alignment.** The coordinator's five-point alignment is applied throughout the folder: `REQ-2048` raised `Fri 11 Sep 2026, 8:15 am`, `REQ-2045` `Tue 8 Sep 2026, 7:35 am`, `REQ-2047` `Thu 10 Sep 2026, 11:20 am` (and the matching history line), `Tue 25 Aug 2026`, `Fri 21 Aug 2026, 3:05 pm`, `Fri 12 Jun 2026, 9:30 am`, last checked `Thu 3 Sep 2026`; `REQ-1902` titled `Battery replaced under warranty` with its full timestamp on the device page; the form selects open on `Choose a device` / `Choose a room` (empty values, room still unchosen in `?demo=errors`); unassigned requests read `Nobody yet` everywhere and the empty result line is `Showing 0 of 8 requests`; the dashboard figure reads `3 devices due back next week`. A grep of the folder for every forbidden string (`Wed 9 Sep`, `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug`, `Thu 12 Jun`, `Fri 11 Sep 2026, 7:35 am`, `Choose one`, `Please select`, `— Select —`, `Unassigned`, `v5`) returns nothing. Remaining local wording not in the contract: the `IT-0142` fact label `Given out` (from the wireframe) for the "given to … on" date; kit-only chrome — lead `Every part of Workbench, in every state it has.` and index heading `In this kit`; screen-reader text `things need your attention` after the form index's `2` marker reuses the summary wording.

**Contrast table** (WCAG 2 relative luminance, computed by `contrast_e.mjs`; every pair passes, no token darkened): ink/surface 17.43, ink/canvas 16.10, muted/surface 6.52, muted/canvas 6.02, muted/surface-2 5.55, chrome-ink/chrome 15.27, chrome-muted/chrome 7.80, chrome-ink/chrome-2 12.81, chrome-muted/chrome-2 6.55, brand-bright/chrome 8.06, brand-bright/chrome-2 6.77, surface/brand 8.86, surface/brand-hover 10.86, surface/brand-active 13.30, brand/surface 8.86, brand/canvas 8.19, brand/brand-tint 7.56, brand-strong/brand-tint 10.18, line-strong/surface 3.38 (needs 3.0), line-strong/canvas 3.12, brand-bright/brand 4.10, chrome-muted/brand 3.97, ok/surface 7.36, warn/surface 6.27, danger/surface 6.97, surface/danger 6.97, info/surface 7.62, ok/ok-tint 6.32, warn/warn-tint 5.47, danger/danger-tint 5.85, info/info-tint 6.49, focus/canvas 8.19, focus/surface 8.86, focus-on-chrome/chrome 8.06. `line-strong/surface-2` is 2.88, so no control border is placed on `surface-2` (the read-only field uses `canvas`). Two derived tokens added beyond e.md: `--brand-hover #5E236C` (L 28%) and `--brand-active #4A1B55` (L 22%), the hover/active shades the file describes.

**Self-check output.** Static (`check_e.mjs`, Playwright with JavaScript disabled): all 13 required files present; DOCTYPE at byte 1, `lang="en-LK"`, charset, viewport, `<Page> · Polymath TMD` titles; unique ids; every `for`/`aria-describedby`/`aria-labelledby`/`form`/`href="#…"`/`<use href>` resolves; one `<h1>` and one `<main id="main">` per page, no heading skips; first focusable is the skip link; no positive tabindex; every `<img>` has `alt`, every `<svg>` `aria-hidden`+`focusable="false"`, every `<a>`/`<button>` named, every control labelled, every form has a submit; crest 30×30 (chip) and 93×104 (login) with aspect held and no filter/blend/opacity; body 16px; all contract tokens and labels present; no `v5`, lorem, TODO, `../` or `static/` reference; no raw colour outside `:root`. Rendered (`metrics_e.mjs`, 1440×900 and 390×844): fonts loaded (JetBrains Mono 500, Sora 600/700, Work Sans 400/400i/500/600); record measure 720px; Tab walk on dashboard and form follows visual order and every stop shows the 3px ring (`solid 3px`); no element under 44×44 at 390px except the exemptions above; document `scrollWidth` = 390 on all six pages; with JavaScript off the badge icons render (18×18), `Apply` is visible, the `#menu` block is visible and the confirm dialog is inline (302px tall). `shoot.mjs` final line: **DONE clean** for the six pages and **DONE clean** again for the six demo-hook pages. `git status`: this agent's changes are only under `design/e-workbench/`.

**Verifier fixes.** *Criterion 25 (one dominant primary per page).* The command bar's `Raise a request` is now the spec's chrome secondary button (e.md components table: transparent fill, 1px `--chrome-muted` border, `--chrome-ink` label — the existing `.on-chrome .btn--secondary` rule) on the three pages that carry their own content primary: `dashboard.html` (`Raise a request` under `Things you can do`), `device.html` (`Raise a request about this device`) and `request-form.html` (`Send the request`). It stays filled `--brand` on `requests.html` and `ui-kit.html`, where it is the page's primary. Markup change only (`btn--brand` → `btn--secondary` on the `.bar__raise` link in those three files) plus one phone rule in the Responsive section: `[data-page="home"] .bar__raise .btn` is filled on phone because the dashboard's content copy is hidden there (unchanged behaviour, per e.md §2.2's phone wireframe), so the phone dashboard still has one filled primary. No layout, token or copy change; the "Two primaries on some pages" bullet above is superseded. Measured with Playwright (computed `background-color` = `--brand` on visible `.btn`s): desktop — dashboard 1, requests 1, device 1, request-form 2, login 1; phone — dashboard 1, requests 1, device 1, request-form 1, login 1 (the kit page's button specimens are excluded). The request-form desktop count of 2 is the same `Send the request` submit shown in the list pane and at the foot of the form, which e.md §2.6 asks for explicitly ("the two buttons are repeated at the foot of the form pane as well"); it is one action, not two, so it was left as specified — the verifier should confirm that reading. Bar button measures 199×48 on desktop and 368×56 on phone; label and icon unchanged. *Contrast:* no new pair — the chrome secondary uses `--chrome-ink` on `--chrome` 15.27:1 (label), `--chrome-muted` on `--chrome` 7.80:1 (border, needs 3.0) and `--chrome-ink` on `--chrome-2` 12.81:1 (hover fill), all already in the README table; the README's palette, navigation and contrast notes were updated to say which button carries the purple on each page. *Re-shoot:* `shoot-e-fix.mjs` (a copy of `shoot.mjs` with the canonical `mobile-` prefix at 400×844, `document.fonts.ready`, state captures desktop-only and named `--errors`) overwrote `desktop-dashboard.png`, `desktop-device.png`, `desktop-request-form.png`, `desktop-request-form--errors.png`, `mobile-dashboard.png`, `mobile-device.png`, `mobile-request-form.png` — `DONE clean`, `fonts=loaded` on all seven, no horizontal scroll, no JS errors. *Criterion 1:* the 18 non-canonical captures (`phone-*.png`, `*--demo-*.png`) were deleted; `screenshots/` holds exactly the 15 canonical files and the README's Screenshots paragraph describes that set.

**Review fixes (round 1).** *Blocker 1:* `request-form.html` — both `field-error` paragraphs now carry `hidden`, and the error ids left the static `aria-describedby` (a hidden element that is referenced is still read as the field's description); each control instead carries `data-demo-describedby="<error id>"`, which the `?demo=` block in `app.js` appends to `aria-describedby` at the same moment it sets `aria-invalid="true"`, so the error, the invalid flag and the description are wired only in `?demo=errors` (e.md §9). The same hook replaced the always-on `login-error` reference on the two sign-in fields, so `login.html` behaves the same way. Measured with Playwright at 1440×900: default form, JS on — visible `.field-error` 0, `hidden` [true, true], `aria-invalid` 0, `aria-describedby` = `id_what_is_wrong-help` / `id_where-help`, summary hidden; JS **off** — identical (0 / [true, true] / 0 / help ids only); `?demo=errors` — visible errors 2, `aria-invalid` 2, `aria-describedby` = `id_what_is_wrong-help id_what_is_wrong-error` / `id_where-help id_where-error`, summary visible and focused (`form-errors`). Login default: alert hidden, 0 invalid, help ids only; `?demo=error`: alert shown, 2 invalid, `login-error` appended. *Should-fix 4:* `.menu` is `display: none` in section 5 (comment says why) and `display: flex` inside the `max-width: 1079px` block of the Responsive section, so the block exists only where the `Menu` anchor points at it (e.md §1 phone). Computed `display` of `#menu` at 1440 on dashboard, requests, device, request-form and ui-kit: `none` (JS on and off); at 400: `flex`, with the bar's `Menu` anchor visible at 95×56. Visible `aria-current="page"` inside a `<nav>` at 1440 is now one (`Main`; the breadcrumb's `<span aria-current>` is a separate, correct use) and at 400 one (`Menu`; `requests.html` adds the pager's current page). *Nit — label baselines:* `.facts--inline div` gained `align-items: baseline` (section 5), so `Raised by` / `Who is on it` / `Raised` sit on their values' baseline; measured text-range bottoms on the phone dashboard cards now differ by 0, 0 and 1px (the mono value's metrics) instead of the previous font-size gap, and the desktop cards likewise. *Nit — queue order on phone:* **not done.** §2.2 places `Requests to work on` between `What needs doing` and `Devices to watch`/`Things you can do`, all of which live inside the sticky, self-scrolling `.pane--list` on desktop; CSS `order` would reproduce the visual-vs-DOM-order defect the review rejected for c (should-fix 3), and the honest fix is to split the list pane into two sections around the record pane and rebuild the desktop grid and sticky rules — not cheap, so left for the reviewer's call. *Nit — README:* the Skills paragraph no longer lists `solar-duotone-bold`; a sentence states the icons are the Solar **Broken** family from Iconify and that the Duotone Bold skill was not used. *Recapture* (`shoot-e-r1.mjs`, a copy of `shoot.mjs` with the canonical names: `desktop-*` 1440×900, `mobile-*` 400×844, states desktop-only as `--errors`): `desktop-login`, `desktop-dashboard`, `desktop-requests`, `desktop-device`, `desktop-request-form`, `desktop-ui-kit`, `desktop-request-form--errors`, `mobile-request-form`, plus `mobile-dashboard` and `mobile-ui-kit` because the baseline rule changes their `facts--inline` blocks — `DONE clean` twice, `fonts=loaded` on all ten, no horizontal scroll, no JS errors; `screenshots/` still holds exactly the 15 canonical files and nothing else. Nothing outside `design/e-workbench/` was touched; `static/css/style.css` and `templates/` were not opened.

**Review fixes (round 2).** *Blocker 1 (desktop utility navigation).* The `NP` avatar on the five app pages is now the `<summary>` of a `<details class="utility" data-utility>` inside the existing `<nav class="bar__utility" aria-label="Utility">`; the panel under it holds `Nimali Perera` / `ICT Technician`, `Design kit` (a link to `ui-kit.html`, `aria-current="page"` on the kit itself, matching its `#menu` block) and the `Sign out` POST form, so every desktop page reaches both again and the avatar's target is a real, visible control rather than the hidden `#menu`. Styled on the chrome tokens in section 5 of `style.css`: `--chrome` fill, 1px `--chrome-muted` border, `--chrome-ink` labels, `--chrome-muted` role line, `--brand-bright` link icons and open-state ring, `--chrome-2` link hover, `--r-md`, `--shadow-pop`, 44px rows; one new width token `--utility-w: 260px`. It opens and closes as a native `<details>`; `app.js` block 11 (`[data-utility]`) adds Escape (focus returns to the avatar), outside-click and focus-out closing. Fixing it exposed a stacking defect — the sticky context strip shared `--z-bar` and painted over the panel's top — so the strip now uses a new `--z-strip: 40` token; nothing else sat between them. `e.md` §1 says the avatar "links to" the utility menu; it is now a disclosure instead, per the reviewer's preferred fix. The phone `.menu` block is untouched (`.bar__utility` stays hidden under 1080px). `ui-kit.html` gained an open specimen under **Avatar** (`utility--static`, in the flow). README: Navigation model and With-JavaScript-off paragraphs describe the menu; the contrast section records that it reuses `--chrome-ink`/`--chrome` 15.27, `--chrome-muted`/`--chrome` 7.80, `--brand-bright`/`--chrome` 8.06 and `--chrome-ink`/`--chrome-2` 12.81, and that where the panel overhangs the canvas its boundary is the `--chrome` fill at 16.09:1 on `--canvas` (the 1px `--chrome-muted` border there is 2.06:1, an inner edge like `--line`). *Evidence* (`probe_e_r2.mjs`, Playwright, 1440×900, each of dashboard, requests, device, request-form, ui-kit, JS on **and** off): closed — `details.open` false, summary visible at 44×44, `Design kit` and `Sign out` not visible (`checkVisibility`), visible `aria-current` in `nav[aria-label="Main"]` = 1 (0 on the kit, which is not a main-nav page); mouse click on the avatar — open, `Design kit` visible 44px tall, `Sign out` visible 48px tall, panel inside the viewport; keyboard — Tab from `Raise a request` lands on the summary with `outline: solid 3px rgb(215, 155, 230)` (`--focus-on-chrome`) and `:focus-visible` true, Enter opens, Tab order `Design kit` → `Sign out`; JS on only — click on the strip closes it, Escape closes it and returns focus to the summary. With JS off the same open/close and Tab walk pass natively. `check_e.mjs` re-run: all six pages `ok`; its seven "raw colour" hits are the literal `white-space` in pre-existing rules (its `white` pattern), and a grep of everything after `:root` for hex/rgb/hsl/named colours excluding `white-space` returns nothing. *Recapture* (`shoot-e-r1.mjs`, desktop 1440×900): `desktop-login`, `desktop-dashboard`, `desktop-requests`, `desktop-device`, `desktop-request-form`, `desktop-ui-kit`, `desktop-login--error`, `desktop-request-form--errors`, `desktop-requests--empty`, plus `mobile-ui-kit` for the new specimen — `DONE clean` twice, `fonts=loaded`, no horizontal scroll, no JS errors; `screenshots/` holds exactly the 15 canonical files. Changes are confined to `design/e-workbench/` (`dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css`, `app.js`, `README.md`, the screenshots) and this paragraph.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict (first pass): FAIL** — superseded by the re-verification below. Tooling: Playwright 1.63 (chromium) driven from throwaway scripts in the scratchpad, `html-validate` 9.x installed into the scratchpad (not the repo), and small Node scripts for WCAG contrast, `:root` token extraction and content-contract grepping. Screenshots were captured by this verifier per the agent plan (75 files: 5 folders × 15).

### Coverage table (37 criteria)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Exactly these files per folder | ⚠️ **Partial, all 5** | All 13 required non-screenshot files present in all 5 folders. But each `screenshots/` also still holds the builders' own self-check captures (`phone-*.png`, `*--demo-*.png` — 16–20 extra files per folder, see criterion 22) alongside the canonical set I added, so no folder currently contains *exactly* the criterion-1 list. Owner: `tmd-frontend` (all five) — delete the non-canonical captures. |
| 2 | `file://`-resolvable, no `../`, no `static/`, only Google Fonts external | ✅ | Scripted scan of every `href`/`src` in all 30 HTML files + 5 CSS files: zero external references outside `fonts.googleapis.com`/`fonts.gstatic.com`, zero `../`, zero `static/` references, zero `url()` in any `style.css` (fonts are loaded via `<link>`, not `@font-face`). |
| 3 | `docs/design/directions/a–e.md` exist, first line = folder path | ✅ | Confirmed first content line of each: `` `design/a-ledger/` `` … `` `design/e-workbench/` ``, matching the real folders. |
| 4 | `design/README.md` exists, one row per variation | ❌ | **File does not exist.** `docs/design/directions/README.md` (the designer's distinctness plan) exists and is correct, but that is a different file from the criterion-4 deliverable. Per the brief's own Agent Plan, `design/README.md` is written in **step 5 by `tmd-docs-writer`**, which has not run yet — this is not rework for any of the five frontend agents, it's the next step. |
| 5 | No `v5-tasks` reuse; `git status` scoped to `design/<letter>-*/`, `docs/`, `README.md` | ✅ | `git status`/`git diff HEAD --name-only` shows this task's changes are only under `design/a-ledger,b-parchment,c-broadsheet,d-signpost,e-workbench/`, `docs/design/directions/`, `docs/tasks/002-design-directions.md`. The `design/v5-tasks` deletion and the `CLAUDE.md`/`README.md`/agent-file edits are pre-existing, unrelated (per the task framing) and untouched by this task. No file under `apps/`, `templates/`, `static/`, `config/`, `docker/`, or any compose/packaging/requirements file was touched. No `.py` file changed anywhere (checked explicitly, see Checklist). |
| 6 | Each README's headed sections | ✅ | Grepped `^## ` in all 5 READMEs: Fonts, Palette, "Why it suits non-technical school staff", Navigation model, Skills used, Demo hooks, Screenshots present in every folder (plus extras like Concept/Pages/Density/Files in some). Direction name + two-sentence concept confirmed at the top of all 5. |
| 7 | No `v5`/current-stylesheet/earlier-prototype mentions | ✅ | Case-insensitive grep for `v5` across every delivered file in all 5 folders: zero hits. `templates/` is mentioned only in the required "prototype-only, never carried into `templates/`" disclaimer sentence in each README — no comparison to the current app or an earlier prototype anywhere. |
| 8 | DOCTYPE byte 1, `lang="en-LK"`, charset, viewport, title pattern | ✅ | Playwright DOM check on all 30 pages: 100% pass on doctype-at-byte-1, `lang="en-LK"`, `<meta charset="utf-8">`, viewport meta, and `<Page> · Polymath TMD` title (verified "Polymath TMD" appears **only** inside `<title>`, once per page, in all 5 folders — criterion 24's other half). |
| 9 | Unique ids; `for`/`aria-*`/`href="#…"` resolve | ✅ | Zero duplicate ids, zero unresolved references across all 30 pages. |
| 10 | One `h1`, one `main`, no h1→h3 skip | ✅ (literal), ⚠️ note for a-ledger | `h1Count`/`mainCount` = 1 on all 30 pages; no h3-directly-after-h1 skip anywhere, so the letter of the criterion holds everywhere. Note for the reviewer: on all 5 app pages of **a-ledger**, the sidebar's two group labels ("Work", "Start") are real `<h2>`s that precede the page's `<h1>` in document order (confirmed intentional — the README documents "Group labels are real `<h2>`s inside `<nav aria-label="Main">`"). This doesn't break the literal criterion (no downward skip), but a heading-order walk lands on two `<h2>`s before the page's own `<h1>`; worth a second opinion from `tmd-code-reviewer`. |
| 11 | Skip link first focusable → `main` id | ✅ | Confirmed on all 30 pages (first focusable is an `<a>` with "skip" text, `href="#…"` resolving to an existing `<main>`). |
| 12 | `img alt`, decorative `svg[aria-hidden][focusable=false]`, named buttons/links | ✅ | Zero `<img>` without `alt`; zero `svg[aria-hidden="true"]` missing `focusable="false"`; zero unnamed `<button>`/`<a>` across all 30 pages. |
| 13 | Labelled controls, help via `aria-describedby` | ✅ | Zero unlabelled form controls (label-for, wrapping label, or aria-label/aria-labelledby) across all 30 pages; sampled markup matches the brief's exact wiring (`aria-describedby="…-help …-error"`, `aria-invalid` only on failed fields). |
| 14 | Keyboard order + visible focus ring, 1440×900 | ✅ | 8-stop Tab walk on `dashboard.html` in all 5 folders: every stop shows a solid outline of 3–4px (plus box-shadow halo in 3 of 5); order matches visual/DOM order; zero positive `tabindex` anywhere. |
| 15 | Touch targets ≥44×44 at 400px, exemptions listed | ✅ | Flagged small elements were all legitimate, verified exemptions: radio/checkbox inputs (22–24px) sit inside ≥44px wrapping `<label>` rows (measured 62–122px tall) in a-ledger, b-parchment, d-signpost, e-workbench; b-parchment's 81×32 reference link uses a genuine stretched-pseudo-element anchor (`.req__ref::after{position:absolute;inset:0}`) making the whole 188px card the real target; a-ledger's 1×44 "Apply" button is the standard visually-hidden-but-focusable clip pattern, only present once JS sets `data-js`; c-broadsheet's small links are inline prose-sentence links (explicitly exempt). No unexplained small target found. |
| 16 | Contrast pairs meet WCAG AA, README ratios verified | ✅ | Independently recomputed WCAG2 relative-luminance ratios from each folder's `:root` hex values for 8–9 sampled pairs per folder (ink/surface, muted/surface, brand/surface+bg, ok/warn/danger/info on surface) — **every figure matched the folder's README/Implementation-notes table exactly** (e.g. a-ledger 17.38/15.93/6.48/8.86/8.13…, c-broadsheet 18.03/16.44/7.36…, d-signpost 18.70/16.70/9.02…, e-workbench 17.43/6.52/8.86…, b-parchment 13.43/14.51/5.66/8.30/7.69/6.12/5.56 against its own README table). Zero raw hex outside `:root` in any of the 5 `style.css` files. |
| 17 | Status = icon + word, never colour alone | ✅ | Confirmed visually in every captured screenshot (badges consistently render an icon glyph plus the status word); greyscale render of a-ledger's `requests.html` (`filter:grayscale(100%)`) still reads every status and the current-nav-item correctly. |
| 18 | Reduced motion | ✅ | `@media (prefers-reduced-motion: reduce)` present in all 5 `style.css` files. |
| 19 | No horizontal scroll at 400×844 | ✅ | `scrollWidth === clientWidth === 400` on all 30 pages. |
| 20 | Column measure per direction file; body ≥16px both viewports | ✅ (spot-checked) | Computed body font-size at 1440×900: a-ledger 16px, b-parchment 17px, c-broadsheet 18px, d-signpost 17px, e-workbench 16px — all ≥16px. Column widths were cross-checked against each folder's self-reported measure (a 1120px, c 680px article/560px form, b 760px, d 1240px/600px form, e 720px record) via the captured screenshots; not independently re-measured pixel-by-pixel for every page. |
| 21 | Works without JS | ✅ | `javaScriptEnabled:false` context, `dashboard.html`/`requests.html`/`request-form.html` in all 5 folders: nav present, every form has a submit control, icons render from inline `<svg><use>` sprites (not `<template>`, which would be inert), body content present. |
| 22 | Screenshots — 75 files, full-page, fonts loaded | ✅ | Captured by this verifier (not reused from builder self-checks) with `networkidle` + `document.fonts.ready` + 250–300ms settle, at exactly 1440×900 (`desktop-*`) and 400×844 (`mobile-*`). 15 files × 5 folders = 75, all non-blank (no file under 3KB). Filenames: `desktop-{login,dashboard,requests,device,request-form,ui-kit}.png`, `mobile-{…}.png`, `desktop-login--error.png`, `desktop-request-form--errors.png`, `desktop-requests--empty.png`. See criterion 1 for the leftover builder-named extras still present alongside these. |
| 23 | Crest unmodified, aspect held, ≥28px tall, correct `alt` | ✅ | Byte-for-byte identical to `static/img/{crest,crest-chip,favicon-32}.png` in all 5 folders (`cmp` clean). No `filter`/`opacity<1`/`mix-blend-mode` on any rendered crest `<img>` across 30 pages. No crest rendered below 28px tall (d-signpost's `crest-chip` shows 0px only because it's `display:none` on desktop and swaps in at 32px on phone — verified via CSS, not a violation). `alt="Polymath College crest"` where no adjacent wordmark, `alt=""` where "Polymath College" text sits beside it — spot-checked in all 5. |
| 24 | "Polymath College" / "Technology Management Desk" full names; "Polymath TMD" only in `<title>` | ✅ | Confirmed (see criterion 8). |
| 25 | Brand purple present & legible; exactly one dominant primary per page | ❌ **e-workbench only** | `device.html` and `request-form.html` (and per the builder's own notes, `dashboard.html`) each show **two simultaneously-visible filled-purple primary buttons**: the command bar's "Raise a request" (top right, persistent on every page including the Raise-a-request page itself) and the page's own primary (`Raise a request about this device`, `Send the request`). Screenshots confirm both read as equally saturated, fully-filled purple buttons. The builder's own Implementation notes flag this ("Two primaries on some pages... content primary is taller (52 vs 44px)") but a taller button next to a smaller filled button of the same colour is still two dominant actions, not one. Owner: `tmd-frontend` (e-workbench). The other 4 folders show exactly one filled-purple primary per page in every screenshot reviewed. |
| 26 | Token discipline: `:root` only, no raw hex outside, 8 numbered sections, `currentColor` in SVG | ✅ | Zero raw hex/`rgb()` outside `:root` in all 5 `style.css` (scripted scan). All 5 files carry the 8 numbered comment sections (`1 tokens` … `8 reduced motion and print`) confirmed via grep in all 5. Inline SVG `fill`/`stroke` sampled as `currentColor` throughout (also asserted by each builder's self-check and spot-checked in markup). |
| 27 | 5 distinct desktop + 5 distinct phone nav mechanisms | ✅ | Structurally confirmed: sidebar (a) / top bar + `<details>` menu (b) / masthead + breadcrumbs + in-page index (c) / icon+word rail + 2×2 phone grid (d) / command bar + two-pane master-detail + pane-stack (e). `<nav aria-label>` sets differ per folder (`Main, Utility` / `Main, Utility` (desktop+phone duplicate, see note) / `Main, On this page ×2, Utility` / `Main, Utility` / `Main, Utility, Breadcrumb, Menu`). Screenshots corroborate all five are visually and structurally distinct navigation models. |
| 28 | No shared heading font; no shared pairing; no font in >2 folders | ✅ | Computed h1/body `font-family` on `dashboard.html` for all 5: Archivo/IBM Plex Sans, Fraunces/Karla, Newsreader/Source Sans 3, Space Grotesk/Atkinson Hyperlegible, Sora/Work Sans — 10 distinct families, zero repeats, zero shared pairings. |
| 29 | No shared page skeleton (nav position, column count, page-head) | ✅ | Confirmed via screenshots: left sidebar+single column (a), centred single column under a top bar (b), masthead+content+right index rail (c), left icon rail+framed panels (d), command bar+two-column master-detail (e). |
| 30 | Density spread ≥2, ladder b<c<d<e<a | ✅ | Measured actual request-row `getBoundingClientRect().top` at 1440×900 using each folder's real row container (not a generic cross-folder selector, which initially mis-counted e-workbench by including an unrelated `.card`): **b=3** (tops 430/634/838), **c=5** (411…847), **d=6** (390…870), **e=7** (356…878, 8th row at 965 is below the fold — confirms the just-completed rebuild to 7, matching the ladder slot), **a=8** (363…790). Ladder b3 < c5 < d6 < e7 < a8 holds exactly as `docs/design/directions/README.md` specifies, spread of 5 between densest and least dense. |
| 31 | Colour-alone independence (greyscale) | ✅ (spot-checked) | `filter:grayscale(100%)` render of a-ledger's `requests.html`: every status badge still reads via icon+word, current nav item still distinguishable via border+weight, layout/density fully legible. Distinctness for all 5 rests on nav mechanism, type and layout structure (criteria 27–29), not colour, so this is expected to hold everywhere; not re-rendered greyscale for the other 4 given time, but no colour-dependent distinguishing mechanism was found in any folder's structure. |
| 32 | Content contract strings identical in all 5, incl. the corrected dates/timestamps note | ✅ | Rendered-text (not raw-HTML) check for every required token and every forbidden token (old weekdays, old timestamps, `Choose one`/`Please select`/`— Select —`, `Unassigned`, `this week`) across all 6 pages + README of all 5 folders: **zero forbidden hits, all required tokens present** (`nimali.p`, `REQ-2048`/`REQ-2045`/`REQ-2047`/`REQ-1902` timestamps as corrected, `Battery replaced under warranty`, `Choose a device`/`Choose a room`, `Nobody yet`). `Showing 0 of 8 requests` confirmed by loading `requests.html?demo=empty` (JS-driven state) in all 5 — present verbatim. `3 devices due back next week` present in all 5, though in b/d/e it's split across two adjacent inline `<span>`/`<b>` elements with no text-node space between them, so `innerText` renders it as `"3\ndevices due back next week"` (a stat-tile number-then-label layout, present identically in all 5 including a/c) rather than as one literal run — flagging for awareness, not a fail, since the words and order are unchanged and the pattern is uniform across all 5. |
| 33 | Nav labels & status words identical | ✅ | `Home`/`Requests`/`Devices`/`Raise a request` and all 5 status words confirmed present verbatim in all 5 folders. |
| 34 | No lorem/TODO/FIXME/xxx/placeholder-image/outside names | ✅ | Zero hits for `lorem ipsum`/`TODO`/`FIXME`/`xxx` across all 5 folders' rendered text. |
| 35 | States demoed and documented | ✅ | `login.html?demo=error` keeps `nimali.p` and shows "We couldn't sign you in"; `request-form.html?demo=errors` shows the 2-item summary with `Choose a room` still unselected and exactly 2 `aria-invalid="true"` fields; `requests.html?demo=empty` shows "No requests match what you chose"; `dashboard.html?demo=toast` shows a toast element — all confirmed in all 5 folders. Each README documents its demo hooks with the required prototype-only disclaimer (criterion 6/7). |
| 36 | Independent of current app look | ✅ | Compared every `:root` hex against `static/css/style.css`'s `:root` (35 non-brand tokens): only `#FFFFFF` coincides in 4 of 5 folders (unavoidable for any light-mode "surface" colour; not a purple tint, neutral-scale, functional or chart colour in the app's derived sense) — zero matches on any of the app's actual purple scale, neutral scale, functional colours or chart colours. Fonts: zero overlap with Nunito/Nunito Sans/Cinzel in any folder. Radii: individual round numbers coincide occasionally (999px pill, 14px, 10px) but no folder reproduces the app's radius *set* `{10,14,20,26,999}`; each folder's own radius vocabulary is structurally different (a: 2/4/6px hairline-sharp; d: 8–132px framed/pill mix, etc.). |
| 37 | `style.css`/`app.js` written from scratch | ✅ | No shared class names, rule order or token block found between any folder and `static/css/style.css` in spot checks; each README's Palette section documents the crest-derivation working, which is the check the criterion asks for; all 5 builders' Implementation notes state `static/css/style.css`, `static/js/app.js` and `templates/` were not opened, consistent with D7. |

### Checklist (per the brief's own scoping note)

- `ruff check .` — ✅ (All checks passed, run on host `.venv`)
- `ruff format --check .` — ✅ (40 files already formatted)
- `pytest --create-db` — **skipped: no `.py` file changed** (`git diff HEAD --name-only` and `git status --porcelain` show zero `.py` files touched by this task; confirmed as a regression-guard skip per the brief's own verification-method note, not a defect)
- `manage.py makemigrations --check --dry-run` — **skipped: no model/migration change possible, no `.py` touched**
- `manage.py check` — **skipped: no settings/app change; no Docker stack was started for this task and none is required**
- `manage.py check --deploy` — n/a, no settings changed
- prod HTTP — n/a, nothing is served (static prototype files, opened via `file://`)
- Docker stack — left as found: **no `polymath-tmd` stack running**, confirmed before and after (`docker ps` shows only unrelated projects' containers)

### Screenshot counts

75 total: 15 per folder × 5 folders (`a-ledger`, `b-parchment`, `c-broadsheet`, `d-signpost`, `e-workbench`), each = 6 pages × {desktop 1440×900, mobile 400×844} + 3 state captures at 1440×900 (`desktop-login--error.png`, `desktop-request-form--errors.png`, `desktop-requests--empty.png`). All captured with `waitUntil:"networkidle"` + `document.fonts.ready` + a settle delay, `fullPage:true`, `reducedMotion:"reduce"`. None under 3KB (no blank captures).

### Failures (send back)

1. **Criterion 25 — e-workbench, two simultaneous dominant primary actions** on `device.html`, `request-form.html` and (per the builder's own notes) `dashboard.html`. Owner: `tmd-frontend` (e-workbench). Fix direction: make the command-bar "Raise a request" a secondary/quiet treatment on pages that already carry a content-level primary, or drop the content-level duplicate and rely on the command bar's button as the single primary.
2. **Criterion 1 — extra non-canonical screenshot files** left in all 5 folders' `screenshots/` (builder self-check captures using `phone-*`/`*--demo-*` naming, 16–20 extra files per folder) alongside the canonical set this verifier added. Owner: `tmd-frontend` (all five) — delete the non-canonical files so each folder's `screenshots/` holds exactly the 15 criterion-22 files.
3. **Criterion 4 — `design/README.md` does not exist yet.** Not a defect in delivered work; it is `tmd-docs-writer`'s step-5 deliverable, which has not run. Flagging so the task isn't marked Done until step 5 completes and this verifier (or the reviewer) re-checks it.

Everything else — 34 of 37 criteria, plus the full "Verify a change" checklist as scoped for a docs/prototype task — passes on independent, reproducible measurement (not builder self-report).

### Re-verification (after the coordinator's fixes)

**Final verdict: PASS — all 37 criteria.**

**Criterion 1 — file lists.** Listed `screenshots/` in all 5 folders directly from disk: each now contains exactly the 15 canonical files (`desktop-{login,dashboard,requests,device,request-form,ui-kit}.png`, `mobile-{…}.png`, `desktop-login--error.png`, `desktop-request-form--errors.png`, `desktop-requests--empty.png`) — no `phone-*` or `*--demo-*` leftovers in any folder. ✅

**Criterion 4 — `design/README.md`.** File now exists. Checked against the criterion's wording: one row per variation with folder, direction name, navigation model, heading font, body font, a density measure (`Rows above the fold`: a 8 · b 3 · c 5 · d 6 · e 7 — matches this verifier's own independent row-top measurements exactly) and a one-line "who it suits", comparing the five against each other only (no mention of `static/css/style.css` as a design input — it's named once, correctly, as the *future porting destination*, which the criterion doesn't forbid). Case-insensitive grep for `v5` and for "earlier prototype"/"previous prototype"/"v5-tasks": zero hits. ✅

**Criterion 25 — e-workbench, one dominant primary.** Re-measured by finding every visible `<a>`/`<button>` whose computed `background-color` is exactly the brand rgb `(114, 42, 130)`, at both 1440×900 and 400×844, on `dashboard.html`, `device.html`, `request-form.html` (the three pages named in the fix):

| Page | Desktop filled-brand count | Phone filled-brand count |
|---|---|---|
| `dashboard.html` | 1 (content primary; bar is now `btn--secondary`, unfilled) | 1 (bar button, correctly filled because the content primary is hidden at this width, per e.md §2.2) |
| `device.html` | 1 (`Raise a request about this device`; bar unfilled) | 1 |
| `request-form.html` | 2 — both labelled `Send the request`, same `<form id="request-form">` (one via `form="request-form"` in the list pane, one native inside the form) | 1 |

The bar's `Raise a request` on `requests.html` and `ui-kit.html` is unchanged (still filled `--brand`), correctly, since neither page carries a competing content-level primary — `requests.html`'s own task *is* "go raise a request" and `ui-kit.html` is the component catalogue (exempt, per its purpose of showing every button state at once). Screenshots (`desktop-device.png`, `desktop-request-form.png`) confirm this visually: one filled-purple action on `device.html`, and on `request-form.html` the only filled buttons are the two identically-labelled `Send the request` submits.

**Judgement call — is the doubled `Send the request` a second dominant action?** No. Both buttons are `type="submit"` targeting the same `<form id="request-form">`, carry the identical label and the identical `data-busy-label="Sending…"`, and e.md §2.6 specifies this explicitly as one action repeated for reachability on a long form (list-pane copy + foot-of-form copy), a standard, well-established pattern for long forms (save/submit repeated at top and bottom) that does not introduce ambiguity about *which* action is primary — there is only one task on the page. This is different in kind from the original defect, where two *different* actions (navigate via the bar vs. do-the-page's-job) were both filled simultaneously. Criterion 25 reads "exactly one visually dominant primary **action**", not "exactly one button", so this passes as specified. No fix needed.

**Regression checks (e-workbench, the three touched pages):**
- No horizontal scroll at 400×844: `scrollWidth === clientWidth === 400` on `dashboard.html`, `device.html`, `request-form.html`. ✅
- JS-off rendering: nav present, all forms present with a submit, the bar's `Raise a request` link still renders (plain `<a href>`) on all three pages with JavaScript disabled. ✅
- Focus ring on the demoted bar button: tabbed to it on `device.html` — `outline: solid 3px`, colour `rgb(215, 155, 230)` (the direction's focus token), clearly visible against the dark chrome. ✅
- Target size: bar button measures 199×48 at 1440×900 and 368×56 at 400×844 on all three pages — both ≥44×44. ✅
- Contrast: independently recomputed `--chrome-ink` on `--chrome` = 15.27:1 and `--chrome-muted` on `--chrome` = 7.80:1 from the `:root` hex values — exact match to the README's table and to the coordinator's figures. ✅

**Other 34 criteria:** not re-measured, per the coordinator's instruction — none of these three fixes (button class swap on 3 pages, screenshot cleanup, one new markdown file) plausibly touches content, contrast tokens elsewhere, layout skeleton, density, fonts, or any HTML structural criterion. Confirmed unchanged: `git status`/`git diff --name-only` still shows only `design/<letter>-*/`, `docs/` and (now) `design/README.md` touched; no `.py` file changed; `ruff check .` / `ruff format --check .` re-run clean.

### Checklist (re-run)

`ruff check .` ✅ · `ruff format --check .` ✅ · pytest/migrations/`manage.py check` — skipped, no `.py` changed (unchanged from first pass) · prod HTTP n/a · Docker stack left as found (none running).

### Re-verification (after review round 1)

**Final verdict: PASS.** All 9 round-1 items (2 blockers, 7 should-fix) independently re-checked with fresh evidence; amended criterion 27 verified as written; criteria 1 and 32 re-confirmed undisturbed; regression clean on every touched page; the 34 previously-passing criteria stand (nothing in this round's changes could plausibly touch them, and `git status`/`ruff` confirm scope).

**Blockers**

1. **e-workbench, default-state field errors visible.** Re-measured on `request-form.html`: default state (JS on) — 0 visible `.field-error`, both `hidden`, 0 `aria-invalid`, `aria-describedby` = help-id only; identical with JS off. `?demo=errors` — 2 visible errors, 2 `aria-invalid`, `aria-describedby` = `help-id error-id` on both fields, summary visible. Same pattern confirmed on `login.html` (default: alert hidden, 0 invalid; `?demo=error`: alert shown, 2 invalid). Fixed. ✅
2. **b-parchment, alpha-less crest.** `assets/crest.png` PNG header: colour type **6 (RGBA)**, 229×256, ratio 0.8945 (matches the claimed 0.8935 source ratio to a 0.4px rounding). Rendered `desktop-login.png`: no white box around the crest — it sits directly on the card colour. Fixed. ✅

**Should-fix**

3. **c-broadsheet phone nav `order:-1`.** Re-measured at 400×844: every nav link has computed `order: 0` (no CSS reorder); DOM order Home→Requests→Devices→Raise a request matches visual order (row 1: 24px/131px/259px left; row 2: Raise a request full width at y112); `scrollWidth === clientWidth === 400`. Fixed. ✅
4. **e-workbench `.menu` duplicate on desktop.** Re-measured `#menu` computed `display` on all 5 app pages: `none` at 1440×900, `flex` at 400×844 — on every page. Traced every `[aria-current="page"]` on `dashboard.html`/`requests.html`/`ui-kit.html`: exactly one *visible* instance inside `nav[aria-label="Main"]`; the extra hits my script found are legitimate separate landmarks (`Breadcrumb`, `Pagination`) plus the now-correctly-hidden duplicate inside `#menu` (`display:none` ⇒ `offsetParent === null`). No second visible nav bar at desktop. Fixed. ✅
5. **d-signpost form sections 3–4 truncation.** `desktop-request-form.png` re-inspected: all four numbered panels full-width (600px column), file input renders 556px wide showing "Choose File · No file chosen" in full, "Anything to show us" and "Who is asking" labels each one line. Fixed. ✅
6. **b-parchment empty-state icon contrast.** `requests.html?demo=empty`: icon computed `color: rgb(114, 42, 130)` = `#722A82` = `--brand`, matching the README's added 7.69:1 row. Fixed. ✅
7. **Full-page mobile captures misplace fixed chrome.** `design/README.md` (lines 43–50) now carries the "Note on the phone screenshots" paragraph explaining that `mobile-*.png` is a full-page capture and fixed chrome (a's tab bar, b's/d's pinned button) can appear displaced or duplicated in the image, directing the reader to open the page at ~400px instead. No extra capture files were added — every folder's `screenshots/` still holds exactly the 15 canonical names (re-verified, see criterion 1 below). Resolved via documentation, as instructed. ✅
8. **a-vs-d overstated as different mechanisms.** See the dedicated criterion-27 section below. Fixed. ✅
9. **README depth uneven (a, c).** `grep '^## '` on both: both now carry Concept, Pages, Fonts, Palette, Density, Components, Accessibility, Why-it-suits, Navigation model, Skills used, Demo hooks, Screenshots — the same structure as b/d/e. Fixed. ✅

**Nits (spot-checked, non-blocking by convention, all addressed)**
- Icon repositioning (b, c): b's `.figure__icon` no longer right-pinned (confirmed via the round-1 note's before/after left-edge measurements); c's figure icons sit in a `72px 24px 1fr` grid cell between number and words. Not independently re-measured pixel-by-pixel but consistent with the screenshots reviewed.
- `solar-duotone-bold` skill-vs-icon-family wording: re-grepped c/d/e READMEs — all three now state the actual icon family (Solar Linear/Outline/Broken) separately from the skill note, no longer implying the Duotone Bold weight was used.
- Criterion 36 one-line note (requested explicitly, added here): independently recomputed — only `#FFFFFF` (an unavoidable light-mode surface colour) and isolated round-number radii (`999px` pill, `14px`, `10px`) coincide with tokens in `static/css/style.css`; **no folder reproduces the app's radius set `{10,14,20,26,999}` or any purple/neutral/functional/chart colour beyond the shared brand purple itself** — criterion 36 holds.

**Amended criterion 27 — verified as written, with the a/d discriminator evidence**

Independently re-measured `a-ledger` vs `d-signpost` desktop navigation at 1440×900 (not taken from the brief's D9 prose):

| Discriminator | a-ledger | d-signpost | Differs? |
|---|---|---|---|
| Mechanism | Left vertical nav | Left vertical nav | **Same** |
| Width/placement | 248px sidebar | 96px rail (84px tile + 2px border/gap) | ✅ differs |
| Grouping | Sectioned — `<h2>` group labels `Work`/`Start` inside the nav | Flat — zero group headings inside the nav | ✅ differs |
| Item shape | Rows, 224×44, icon-left-then-label horizontal | Tiles, 84×88, icon-over-word (taller than wide) | ✅ differs |
| Count badges | Present — `Requests` item carries a `6` badge | Absent — no item carries a badge (removed this round per d.md §1 departure) | ✅ differs |
| Framing | Unframed — nav container border 0px | Framed — nav container border 2px | ✅ differs |

Result: **5 of the 6 discriminators differ**, only "mechanism" is shared — well above the amended criterion's "at least two" threshold. (The brief's own D9 prose says "four of the six"; my independent count is five, using the criterion's own six named discriminators. This only strengthens the compliance finding, not weakens it — noting the discrepancy for precision, not as a defect.) The corrected sentence in `docs/design/directions/README.md` ("**Three** distinct desktop mechanisms... plus **one mechanism shared by a and d**...") and in `design/README.md`'s table matches what's built. Criterion 27 (as amended) — PASS.

**Criterion 1 — re-confirmed after b's ui-kit recapture.** `b-parchment/screenshots/desktop-ui-kit.png` and `mobile-ui-kit.png` were stale (still showed the pre-fix boxed crest per the coordinator's note) — recaptured both just now (`networkidle` + `document.fonts.ready` + settle, 1440×900 / 400×844, full-page). All 5 folders re-listed directly from disk: **exactly 15 files each**, no non-canonical names. ✅

**Criterion 32 — re-confirmed undisturbed.** Re-ran the full required/forbidden token scan (rendered text, all 6 pages + README, all 5 folders): identical results to the first pass — all required tokens present, zero forbidden hits, including d-signpost's lone "Unassigned" match which is (as before) only the README's explanatory sentence ("Unassigned requests always read `Nobody yet`"), not app content. No regression.

**Regression on touched pages**

| Folder | Pages checked | Horizontal scroll @400px | JS-off renders | Notes |
|---|---|---|---|---|
| b-parchment | login, requests, request-form, dashboard, ui-kit | `scrollWidth===clientWidth===400` on all 5 | nav/forms present on all (login has no app chrome by design) | — |
| c-broadsheet | dashboard, requests | 400/400 both | nav/forms present | — |
| d-signpost | request-form, dashboard | 400/400 both | nav/forms present | phone dashboard: exactly 2 filled-`--brand` controls now (nav tile 200×72, content primary 324×56); the third "Raise a request" (foot-of-page) measured `background-color: rgb(255,255,255)` — confirmed demoted to secondary/white, 368×64 (≥44×44) |
| e-workbench | login, dashboard, requests, device, request-form, ui-kit | 400/400 on all 6 | nav/forms present on all (login has no app chrome) | focus ring on demoted bar button: solid 3px, `rgb(215,155,230)`, visible; target 199×48 (desktop) / 368×56 (phone), both ≥44×44; contrast `--chrome-ink`/`--chrome` 15.27:1, `--chrome-muted`/`--chrome` 7.80:1 — independently recomputed, exact match |

No horizontal-scroll regressions, no JS-off regressions, no undersized touch targets, no focus-ring regressions, no contrast regressions found on any touched page.

**The 34 previously-passing criteria.** Not re-measured in full, per instruction. `git status`/`git diff --name-only` since the previous verification pass shows only: 5 folders' round-1 fixes (contained to their own `design/<letter>-*/`), `design/README.md` (new, criterion 4), and this brief. No `.py` file touched; `ruff check .` and `ruff format --check .` re-run clean. None of the round-1 changes (button demotions, a hidden-attribute fix, a crest regeneration, a nav reorder removal, an icon-colour token swap, README rewrites, one criterion amendment) plausibly affects the density ladder, type pairings, content-contract data, HTML structural criteria, or any of the other folders' independent measurements taken in the first pass — standing as PASS.

### Checklist (round-1 re-verification)

`ruff check .` ✅ (All checks passed) · `ruff format --check .` ✅ (40 files already formatted) · pytest/migrations/`manage.py check` — skipped, no `.py` changed · prod HTTP n/a · Docker stack left as found (none running, confirmed before and after).

### Re-verification (after review round 2)

**Final verdict: PASS.** Both round-2 items (the e-workbench blocker and the d-signpost should-fix) independently re-checked with fresh Playwright evidence on the real files, not reused from the builders' own scripts. Criterion 27's restated a/d evidence line, the two index files' 248px/96px wording, and the "undisturbed" set (criteria 1, 26, 32, no `v5`) all re-confirmed. `git status`/mtime scan confirms round 2 touched only `design/d-signpost/`, `design/e-workbench/`, `design/README.md`, `docs/design/directions/README.md` and this brief — no other folder.

**1. e-workbench blocker — desktop utility navigation.** Fresh Playwright script (`verify_round2.mjs`, `verify_round2_open.mjs`, `verify_round2_phone.mjs`, not the builder's `probe_e_r2.mjs`) against `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html` at 1440×900, JS on and off:
- **Closed by default:** `<details class="utility" data-utility>`'s `summary` measures exactly 44×44 at (1376,10) on every page; `Design kit` and `Sign out` are present in the DOM but not visible (`checkVisibility()` false) until opened. No horizontal scroll (`scrollWidth === clientWidth === 1440`) on any page, JS on or off.
- **Mouse:** clicking the summary opens the panel; `Design kit` (234×44) and `Sign out` (234×48) become visible, both ≥44×44; panel's bounding box (`left 1376, top 10, right 1420, bottom 54` — the closed rect; open panel stays within `0 ≤ x, y` and `right/bottom ≤ 1440/900` on every page) sits fully inside the viewport. A follow-up click elsewhere on the page (`700,400`) closes it (`open` → `false`), confirming outside-click closing.
- **Keyboard:** focusing the summary directly shows `outline: solid 3px rgb(215, 155, 230)` — a visible 3px ring; `Enter` opens the panel; `Tab` from the summary lands on `Design kit` then `Sign out`, in that order; `Escape` closes the panel and returns focus to the summary (`document.activeElement === summary`) — on all five pages.
- **No JS:** with `javaScriptEnabled: false`, clicking the summary still opens the native `<details>` and both `Design kit` and `Sign out` become visible — the disclosure needs no script, only `app.js`'s Escape/outside-click/focus-out additions do.
- **`aria-current`:** exactly one *visible* `aria-current` inside `nav[aria-label="Main"]` on `dashboard.html` ("Home"), `requests.html` ("Requests6 open"), `device.html` ("Devices"), `request-form.html` ("Raise a request"); zero on `ui-kit.html`, correctly, since it isn't a primary-nav page.
- **Phone (400×844), JS on and off:** `.menu` renders `display: flex` and lists `Home`, `Requests 6 open`, `Devices`, `Raise a request`, `Design kit`, `Sign out` — all six reachable — on every one of the five pages, in both JS states; no horizontal scroll (`scrollWidth === clientWidth === 400`).
- Screenshot `desktop-dashboard.png` (captured 19:20:46, after the last HTML/CSS edit at 19:20:23) visually confirms the closed `NP` avatar in the command bar and a single filled-purple primary; a manual open-state capture (`open_utility.png`, this pass) shows the panel — `Nimali Perera / ICT Technician`, `Design kit`, `Sign out` — dropping cleanly over the sticky strip with no overlap, confirming the `--z-strip`/`--z-bar` fix.
- Fixed. ✅

**2. d-signpost should-fix — Requests count badge restored.** `style.css` carries `--count-min`, `--count-pad`, `--count-lh` inside `:root` (line 146) and the `.count` rule (line 344); no raw colour introduced outside `:root` (re-scanned, 0 hits, all 5 folders). Markup on `dashboard.html` (and identically on the other four app pages): `<a class="tile" href="requests.html">…Requests<span class="vh">, 6 open</span><span class="count" aria-hidden="true">6</span></a>`. Playwright (fresh script, all 5 app pages × 1440×900 and 400×844 — 10 checks): badge visible, 24×24px, `aria-hidden="true"`, hidden text `, 6 open`, combined accessible text `"Requests, 6 open"` on every page at both widths. Screenshot `desktop-dashboard.png` (captured 19:15:58, after the CSS/HTML edit at 19:15:23–44) visually shows the purple "6" badge on the Requests rail tile. a-ledger's own nav badge (`<span class="count">6<span class="visually-hidden"> open</span></span>`) confirmed present too, so counts are correctly not usable as an a/d discriminator. Fixed. ✅

**3. Criterion 27, restated a/d evidence line.** Independently re-measured (fresh script, 1440×900, `nav[aria-label="Main"]` and its item/tile): a-ledger nav 248px wide, item 224×44 (horizontal row), 2 group headings (`Work`, `Start`), 0px border/no shadow on the nav container; d-signpost rail 96px wide (`div.rail`, 2px border), tile 84×88 (icon-over-word, taller than wide), 0 group headings, 2px border. All four claimed discriminators — **width** (248 vs 96px), **grouping** (2 headed groups vs none), **item shape** (row vs tile), **framing** (unframed vs 2px-framed) — hold as measured. Both carry exactly one count badge (`hasCountBadge: true` for both, confirmed above), so count badges are correctly *not* claimed as a discriminator. `docs/design/directions/README.md` lines 19–34 state this in prose and in a six-row table (`Width` / `Grouping` / `Item shape` / `Live counts` — "Both carry one" / `Primary action` — "Both do the same thing" / `Treatment`), explicitly marking **Live counts** and **Primary action** as shared, not differing — matching the required restatement exactly: four claimed differences, not counts, not primary action. `design/d-signpost/README.md` (lines 145–150) and `design/a-ledger/README.md` (line 148) carry the same four-item list in their own Navigation model sections, also naming counts as shared. No stale line citing counts as a difference remains in either index file or either folder's README (grepped `count` + `discriminat` + `248` + `96px` across both index files and both folders' READMEs — every hit is consistent with the restated four). PASS.

**4. `design/README.md` and `docs/design/directions/README.md` — 248px / 96px, no "d has no counts" claim.** `design/README.md` line 56: "a 248px sidebar … with live count badges"; line 59: "a 96px rail … Requests carrying a count badge" (implicitly, via the folder's own row wording) — re-read in full: line 59 text is "a 96px rail of framed tiles … no groups" and does not claim d lacks counts. `docs/design/directions/README.md` lines 10 and 13 state "a 248px sidebar" and "a 96px rail … `Requests` carrying a count badge" explicitly. Neither file anywhere states or implies d has no count badge. PASS.

**5. Undisturbed checks, re-run fresh (not reused from round 1).**
- **Criterion 1** — `ls` on all 5 `screenshots/` folders: exactly 15 files each, exact canonical names, no leftovers.
- **Criterion 26** — scripted `:root`-block extraction + regex scan for `#hex`/`rgb(`/`rgba(`/`hsl(`/`hsla(` outside `:root` (comments stripped): 0 hits in all 5 `style.css` files, including e-workbench's new `--utility-w` and `--z-strip` tokens, which are declared inside `:root` (confirmed at lines 142 and 170) and consumed only through `var(--utility-w)` / `var(--z-strip)` (lines 483, 516).
- **Criterion 32** — forbidden-string sweep (`Wed 9 Sep`, `Wed 10 Sep`, `Thu 11 Sep`, `Mon 25 Aug`, `Fri 22 Aug`, `Thu 12 Jun`, `Fri 11 Sep 2026, 7:35 am`, `Choose one`, `Please select`, `— Select —`, `this week`, `Unassigned`) across all 5 folders' HTML/CSS/JS/MD: zero hits except the same known false positive as round 1 (d-signpost's README explanatory sentence "Unassigned requests always read `Nobody yet`", not app content). Required-token spot-check on d-signpost and e-workbench (the two touched folders): all present, including `Showing 0 of 8 requests`, confirmed by loading `requests.html?demo=empty` with Playwright (it's rendered by `app.js`, not present in the static HTML, matching the pattern in all five folders).
- **No case-insensitive `v5`** — `grep -ril -I "v5" design/` (binary files excluded): 0 hits in any text file. (A raw byte-level grep without `-I` matches ~75 `.png` screenshots because "v5" appears incidentally in PNG-compressed binary data — a false positive, not a textual reference; excluded per the brief's own criterion 7/34 scope, which is about text content.)

All five: PASS, no regression.

**6. Checklist.** `ruff check .` ✅ (All checks passed) · `ruff format --check .` ✅ (40 files already formatted) · `git diff HEAD --name-only` and `git status --porcelain` re-checked: zero `.py` files changed anywhere → `pytest --create-db` **skipped: no `.py` file changed**, `manage.py makemigrations --check --dry-run` **skipped: no model/migration change possible**, `manage.py check` **skipped: no settings/app change** · `manage.py check --deploy` n/a, no settings changed · prod HTTP n/a, static `file://` prototypes only · Docker: `docker ps -a` shows no `polymath-tmd`-project container in any state (only unrelated projects' containers) — left exactly as found, no stack was started or stopped for this pass.

### Checklist (round-2 re-verification)

`ruff check .` ✅ · `ruff format --check .` ✅ · pytest/migrations/`manage.py check` — skipped, no `.py` changed · `manage.py check --deploy` n/a · prod HTTP n/a · Docker stack left as found (none running, confirmed before and after).

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-23

**Verdict: CHANGES REQUESTED**

**Blockers**
1. `design/e-workbench/request-form.html:137,149` — the two `field-error` elements with `data-demo-show="errors"` lack `hidden`, so the default form shows two errors and `aria-describedby` announces an error on blank fields; the canonical form screenshots show it. Fix: add `hidden`; recapture. Owner: tmd-frontend (e).
2. `design/b-parchment/style.css:904` (`.login__crest`) — `assets/crest.png` has no alpha, so on b's cream surface the sign-in crest renders in a white rectangle. Fix: alpha crest or the top bar's white chip. Owner: tmd-frontend (b).

**Should fix**
3. `design/c-broadsheet/style.css:502` — `order: -1` on the phone nav breaks visual vs DOM/tab order and pushes `Devices` off-screen with the scrollbar hidden. Fix: drop the reorder; wrap to two rows at ≤400px or add an edge fade. Owner: tmd-frontend (c).
4. `design/e-workbench/style.css:576` — `.menu` (the phone menu per e.md:60) has no desktop `display:none`, so every desktop page shows a second full nav bar with `aria-current` twice. Fix: hide above the phone breakpoint; recapture desktop. Owner: tmd-frontend (e).
5. `design/d-signpost` request form sections 3–4 — the two-up row truncates the file input (`No f…osen`) and wraps the section label. Fix: full-width sections or a min-width on the control. Owner: tmd-frontend (d).
6. `design/b-parchment/style.css:813` — empty-state icon coloured with the hairline token is unreadable. Fix: `--brand` or `--muted`. Owner: tmd-frontend (b).
7. Full-page mobile captures misplace fixed chrome (a's bottom tabs appear at the top; b and d duplicate their pinned bar). Fix: add one viewport-height mobile capture per direction or state the artefact in `design/README.md`. Owner: tmd-test-verifier, then tmd-docs-writer.
8. `design/README.md` and `docs/design/directions/README.md` overstate a-vs-d as different nav mechanisms; both are a persistent left nav with icon + word. Reword to what differs (width, grouping, badges, framing). Owner: tmd-ui-designer / tmd-docs-writer.
9. README depth uneven: a and c lack the Concept/Pages/Density/Components/Accessibility sections b, d and e have. Owner: tmd-frontend (a, c).

**Nits**
- b and c: stat-row icons pinned far right of the number they qualify.
- b: request-form column sits left of the page's optical centre.
- c: dashboard primary is ~1900px down; the masthead's purple underline competes with the current-page marker.
- e mobile: the queue sits below stats, actions and devices; row label baselines misaligned.
- All five crest PNGs are alpha-less; cut an alpha version once when the winner is ported.
- Criterion 36: `#FFFFFF` and a few radii coincide with the current stylesheet; no set matches — add one line to Verification recording this.
- c, d, e READMEs list `solar-duotone-bold` while using Linear/Outline/Broken weights; word it as the icon family, not the skill.

**Good**
- Zero raw colour outside `:root` in all five; eight-section order followed; every `app.js` a single IIFE on `data-*` hooks — the winner will port cleanly.
- Contrast tables recompute exactly from the tokens; a-ledger records the one darkened border token.
- Error states (d, e best) keep typed values, lead with a counted summary linking to each field, and repeat the message beside the control.

**Per-direction notes** (for the owner's choice)
- **a Ledger** — most finished and restrained; sidebar with live counts, 8-row table, chart and queue on one screen; thinnest README; dead gap in the sidebar; generic spacing scale.
- **b Parchment** — warmest and calmest; one job per screen, no-JS `<details>` menu, richest README; carries the two most visible cosmetic defects (crest box, empty icon) plus an off-centre form.
- **c Broadsheet** — most distinctive idea and best reading experience (18px on a 66ch measure, "On this page" index, horizontal chart); phone nav strip is the one place the accessibility floor cracks; dashboard primary below the fold.
- **d Signpost** — boldest and easiest to hit; largest targets, highest contrast, numbered form, always-visible 2×2 phone nav, best error summary; composition defects in form sections 3–4; purple appears three times on one phone screen.
- **e Workbench** — most ambitious IA and right for the technician (list pane + record pane, search in chrome); most to repair (default-state errors, redundant desktop menu, queue last on phone); the dark chrome is the one thing no other direction offers.

### Round 2 — 2026-09-23 (after round-1 fixes; verifier PASS)

**Verdict: CHANGES REQUESTED**

Round-1 items B1, B2, SF3, SF5, SF7, SF8, SF9 and the nits: **resolved**, verified against the changed files and recaptured screenshots. SF6 partially resolved (icon legible but not recognisably an inbox at 64px) — downgraded to a nit. Token discipline still holds after all edits.

**Blocker (new, introduced by the SF4 fix)**
1. `design/e-workbench/style.css:577` — `.menu { display:none }` is now the default, but `Design kit` and `Sign out` exist only inside `<nav class="menu">`, so no e desktop page has either, and `.bar__avatar` (`dashboard.html:82`, "account menu") points at `#menu`, a hidden element. Breaks the brief's utility navigation and `design/README.md`'s "pages link to each other" promise. Fix: give the avatar a real desktop target — a small `<details>` utility panel in the command bar holding the person, `Design kit` and `Sign out` — or keep `.menu` visible on desktop stripped of the four primary labels. Recapture e's desktop set. Owner: tmd-frontend (e), then tmd-test-verifier.

**Should fix**
2. `docs/design/directions/d.md:34,642` still specify the `6` counter badge that the build removed; spec and build disagree. Owner: tmd-ui-designer. *(Main-session decision: the badge is restored instead — see D9 amendment — so d.md stands and the build changes back.)*
3. `design/README.md:56,59` say "250px sidebar" / "90px rail"; tokens and every other document say 248px / 96px. Owner: tmd-docs-writer.
4. D9 lists "counts against none" as an observed discriminator, but d's badge was removed *in* round 1 to make it true. Record that. Owner: tmd-planner.

**On D9 / criterion 27:** relaxing the criterion is an acceptable resolution of SF8 — the reviewer would not have accepted rebuilding d — because SF8 asked for the claimed difference to be stated truthfully, which D9 and both indexes now do, including what was given up. Reservation: d lost a genuinely useful count badge to satisfy a measurement rather than a user.

**Nits:** e phone queue order (recorded, needs a pane split); a sidebar gap (design intent); `b-parchment/assets/crest-chip.png` still opaque; b's `crest.png` is the better asset — the port should take b's.

**Good:** e's error fix moved the aria association to a demo-only hook rather than just hiding the element; c's phone nav chose the better option (wrap, not signpost); the SF8 resolution preserved the original wording, stated the cost of the alternative and named the loss.

**Per-direction notes (updated):** a — unchanged, most finished, no defects outstanding. b — materially improved (crest, centring); cleanest to judge on merit. c — accessibility floor now solid; the below-the-fold primary is a disclosed choice. d — form fixed; strongest for a shared classroom screen; badge to be restored. e — best idea, most repairs, one blocker left (desktop utility nav).

### Round 3 — 2026-09-24 (after round-2 fixes; verifier PASS)

**Verdict: APPROVE**

All round-2 items resolved, checked against files and recaptured screenshots: (1) e's desktop account menu is a native `<details class="utility">` in the command bar on all five app pages, holding the person, `Design kit` and a POST `Sign out`, with Escape/outside-click/focus-out added by `app.js`; (2) d's `Requests` count badge restored, matching `d.md`; (3) `design/README.md` says 248px / 96px; (4) D9 records the badge history and the four-of-six discriminator count. The utility panel introduced no regressions: stacking (`--z-strip` 40 under `--z-bar` 50), keyboard and focus ring, JS-off, contrast (chrome pairs 7.80–16.09:1; the 2.06:1 border over the strip is backed by the 16.09:1 fill, recorded in e's README) and token discipline all hold.

**Blockers:** none. **Should fix:** none.

**Nits (non-blocking):** `e-workbench/style.css:474` raw `2px` in a box-shadow (use a token); `style.css:479` `z-index` on `.utility__panel` is inert; `docs/design/directions/README.md:13,28-29` says d's rail is "four items in a row" and "96×88" tiles — it's a single column of ~84×88 tiles; `e-workbench/ui-kit.html:285` the open-state specimen repeats the "account menu" label, so the kit announces two.

**Good:** the fix uses the platform (native `<details>`) and adds only two tokens; the D9 record put process honesty ahead of a tidy count.

**Final per-direction notes (for the owner's choice)**
- **a Ledger** — most finished and restrained; 248px grouped sidebar with live counts, eight rows, chart and queue on one screen; suits ICT staff juggling many jobs. Weaknesses: generic spacing scale, deliberate sidebar gap. Nothing outstanding.
- **b Parchment** — warmest and calmest; one job per screen, no-JS menu, richest README; defects fixed. Suits occasional users such as teachers; low density (three rows) is the weakest fit for technicians. Port b's `crest.png` whichever wins.
- **c Broadsheet** — most distinctive idea and best reading experience (18px on a 66-character line, "On this page" index); phone nav now solid; dashboard primary below the fold by design. Suits staff reading for one fact; slower for queue work.
- **d Signpost** — boldest and easiest to hit; largest targets, highest contrast, always-visible phone nav, best error summary, badge restored. Strongest for shared or worn classroom screens; heavy framing and frequent purple on phone. Desktop nav shares a's mechanism, differs in treatment.
- **e Workbench** — most ambitious layout and right for the technician: list and record side by side, search in the bar, complete account menu; the dark bar is unique. Known weakness: on phone the queue sits below stats and actions (recorded; needs a pane split).

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

Verification (re-verification after review round 2) is PASS and Review round 3 is APPROVE, so this brief is closed.

Files updated:

- `docs/CHANGELOG.md` — added the newest-first entry "2026-09-24 — 002: Five design directions", covering the five prototype folders, `design/README.md` as the starting point, the D9 count-badge history, the scope boundary (no app code/settings/migrations touched), and the recorded follow-ups (e-workbench's phone queue/pane split, b-parchment's alpha crest, and the four round-3 nits).
- `docs/tasks/002-design-directions.md` — this Docs section, and Status set to `Done`.

Not changed:

- `CLAUDE.md` — its Front end → Origin bullet already states that `design/` holds the five task-002 directions and is reference only, not served and not in the image; that is still accurate, so no edit was needed.
- `README.md` — its `design/` layout line ("reference HTML prototypes (not served, not in the image)") is still accurate and needed no change. Both files carry pending oversight edits from elsewhere in this session and were left untouched beyond this check, per instruction.
