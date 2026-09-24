# Direction A — Ledger

## Concept

Ledger is the ICT technician's day on one screen: a quiet slate-paper console where every request, count and due date is a line in a book you can read without scrolling. It earns its density from restraint — hairlines instead of boxes, one chroma (the crest purple) instead of a palette, and numbers set in a mono face so columns line up like a register.

The geometry follows from that: nothing is rounder than 6px, no static surface has a shadow (only the modal and the toast), separation is always a 1px `--line` rule, the timeline nodes and the avatar are squares, and every reference, tag, date and amount is set in IBM Plex Mono with tabular numerals so a column of them reads like a ledger page. Open any page straight from the file system; Google Fonts is the only external resource.

## Pages

| Page | What it shows | Chrome |
|---|---|---|
| `login.html` | `Welcome back`, the crest at 72px (56px on phone), Username and Password with their help lines, `Sign in`, and the footer `Polymath College · Technology Management Desk`. A 420px ruled card centred on the slate page, which carries a faint 12px grid that stops 64px from the card. `?demo=error` shows `We couldn't sign you in` with `nimali.p` kept. | No app chrome |
| `dashboard.html` | `Home`: the seven figure tiles (`6 requests open` … `34 out on loan`, the urgent tile with a red top rule and the flame), the four `Requests to work on` rows, `Devices to watch` (IT-0087, IT-0056, IT-0142), the one bar chart with its visible text alternative, and `Things you can do`. `?demo=toast` adds the success toast and alert. | Sidebar / tab bar, `Home` current |
| `requests.html` | `Requests`: the search and filter panel (one row at ≥1280px), the live result line, the 8-row queue table with icon-and-word status badges and outline urgency chips, and pagination. Below 1024px the same table becomes a card list. `?demo=empty` shows the empty state. | `Requests` current, count pill `6` |
| `device.html` | `IT-0142 — Dell Latitude 3540 laptop`: breadcrumb `Devices › IT-0142`, `Issued` and `Good` badges, the two actions, two fact panels side by side, the two linked requests, and the five-entry timeline. `Mark it returned` opens a `<dialog>` (or, without JavaScript, jumps to the confirmation section at the foot of the page). `?demo=denied` shows the no-permission panel. | `Devices` current |
| `request-form.html` | `Raise a request`: one 640px left-aligned column, four sections (`About the problem`, `How soon you need it`, `Anything to show us`, `Who is asking`), the seven fields with their help lines, and `Send the request` / `Cancel` 24px apart. `?demo=errors` shows the summary and the two field errors with everything typed kept. | `Raise a request` current |
| `ui-kit.html` | `Design kit`: every component in every state, each in a ruled specimen strip with a mono caption naming its class and tokens, plus the icon set at every size, the type scale, the colour tokens with hex and contrast, the spacing scale, and the focus ring on a light and on a dark surface. | Utility link `Design kit` current |

## Fonts

Loaded from Google Fonts, exactly these weights:

| Family | Weights | Used for |
|---|---|---|
| **Archivo** | 600, 700 | Headings (`h1` 30/36 desktop, 26/32 phone; `h2` 20/26; `h3` 17/24), buttons (600, 16/20) and the **wordmark** `Polymath College` (700, 17/20, uppercase, `.10em` tracking) in the sidebar and on the sign-in page |
| **IBM Plex Sans** | 400, 500, 600 | Body 16/26 (never below 16px), lead 18/28, table cells 16/22, labels 600 16/22, help 15/22, and the 13px uppercase column headers, nav group titles and chips (600, `.06em`) |
| **IBM Plex Mono** | 500 | References, tags, dates, money and counts (`REQ-2048`, `IT-0142`, `Rs 285,000`, `5CG4113XYZ`) at 15/20 with tabular numerals; figure tiles at 34/38 |

Prose is capped at `--measure: 62ch`; the request form column is 640px; tables may use the full 1120px content column.

## Palette

**Derivation from the crest.** `logo.png` is a purple shield, `#722A82` = `hsl(289, 51%, 34%)`. Every purple step keeps hue 289 and moves only lightness. The neutrals take that same hue and pull it 59° toward blue (hue 230) while draining the saturation to 12–26%, giving a cool slate paper that reads as a complement to the mark rather than a tint of it. Functional colours sit at hues far from 289 (212 · 164 · 31 · 346) at lightnesses that hold at least 4.5:1 on white; their badge borders are the same hue at L 80%.

| Token | Hex | How it was derived |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-hover` / `--brand-active` | `#5E236B` / `#491B54` | `--brand` at L −6 / L −12 (button hover and press) |
| `--brand-strong` | `#4E1C59` | Hue 289 at L 26% — text on purple tints |
| `--brand-tint` | `#F6EEF8` | Hue 289 at L 96% |
| `--brand-line` | `#C9A7D1` | Hue 289 at L 80% — decorative rules only |
| `--ink` | `#171A23` | Slate 230 at L 12% |
| `--muted` | `#565E72` | Slate 230 at L 39% |
| `--line` | `#D6DBE6` | Slate 230 at L 87% — hairlines |
| `--line-strong` | `#7D829B` | Slate 230 at **L 55%** — control borders. The direction brief proposed L 60% (`#858DA1`), which is 2.81:1 on `--surface-2`, where the sidebar's Sign out button sits; the brief's own rule ("if a control-border pair is under 3:1, darken that token one step") moved it one step down |
| `--bg` | `#F3F5FA` | Slate 230 at L 97% — the page |
| `--surface` | `#FFFFFF` | Cards, table body |
| `--surface-2` | `#E9ECF4` | Slate 230 at L 94% — sidebar, table head |
| `--info` / `--info-tint` / `--info-line` | `#0F4C93` / `#E7F0FB` / `#B5CAE3` | Hue 212 — New, Issued |
| `--ok` / `--ok-tint` / `--ok-line` | `#0B6B52` / `#E3F3EE` / `#B5E3D7` | Hue 164 — Fixed, Good, In store |
| `--warn` / `--warn-tint` / `--warn-line` | `#8A4B07` / `#FBEFE0` / `#E3CDB5` | Hue 31 — Waiting on someone, In repair, Needs repair |
| `--danger` / `--danger-hover` / `--danger-tint` / `--danger-line` | `#A81436` / `#8D112D` / `#FBE7EB` / `#E3B5C0` | Hue 346 — Urgent, Out of service, errors |
| `--muted-line` | `#C5C9D3` | Muted hue at L 80% — Closed badge border |
| `--focus` / `--focus-halo` | `#722A82` / `#FFFFFF` | The focus ring is the brand, with a 2px white halo so it reads on dark and purple surfaces |
| `--backdrop` | `rgba(23, 26, 35, .55)` | `--ink` at 55% — the modal backdrop, the one translucent fill |
| `--shadow-pop` | `0 1px 2px rgba(23,26,35,.10), 0 8px 24px rgba(23,26,35,.10)` | Modal and toast only; no other surface has a shadow |

**Where the crest purple appears on every page:** the primary button (`Raise a request` in the sidebar and tab bar, `Sign in`, `Send the request`, `Raise a request about this device`), the current navigation item's 3px bar and label, links, nav icons, the request count pill, the `In progress` badge, the timeline rail and nodes, the chart bars, and the focus ring.

**Contrast pairs**, computed with the WCAG 2 relative-luminance formula from the `:root` values in `style.css` (a small Node script, not estimated):

| Pair | Ratio | Needs | Result |
|---|---|---|---|
| `--ink` on `--surface` | 17.38:1 | 4.5 | pass |
| `--ink` on `--bg` | 15.93:1 | 4.5 | pass |
| `--ink` on `--surface-2` | 14.70:1 | 4.5 | pass |
| `--muted` on `--surface` | 6.48:1 | 4.5 | pass |
| `--muted` on `--bg` | 5.94:1 | 4.5 | pass |
| `--muted` on `--surface-2` | 5.48:1 | 4.5 | pass |
| `--surface` on `--brand` (primary button) | 8.86:1 | 4.5 | pass |
| `--brand` on `--surface` (links, icons) | 8.86:1 | 4.5 | pass |
| `--brand` on `--bg` | 8.13:1 | 4.5 | pass |
| `--brand` on `--surface-2` (sidebar icons, current item) | 7.50:1 | 4.5 | pass |
| `--brand-strong` on `--brand-tint` (count pill, In progress, avatar) | 11.32:1 | 4.5 | pass |
| `--surface` on `--brand-hover` / `--brand-active` | 10.35:1 / 13.35:1 | 4.5 | pass |
| `--line-strong` on `--surface` (field border) | 3.79:1 | 3.0 | pass |
| `--line-strong` on `--bg` | 3.48:1 | 3.0 | pass |
| `--line-strong` on `--surface-2` (Sign out button in the sidebar) | 3.21:1 | 3.0 | pass |
| `--info` on `--info-tint` | 7.37:1 | 4.5 | pass |
| `--ok` on `--ok-tint` | 5.66:1 | 4.5 | pass |
| `--warn` on `--warn-tint` | 5.99:1 | 4.5 | pass |
| `--danger` on `--danger-tint` | 6.29:1 | 4.5 | pass |
| `--info` / `--ok` / `--warn` / `--danger` on `--surface` (chips, error text, icons) | 8.48 / 6.48 / 6.80 / 7.45:1 | 4.5 | pass |
| `--surface` on `--danger` (destructive button) | 7.45:1 | 4.5 | pass |
| `--surface` on `--ink` (toast) | 17.38:1 | 4.5 | pass |
| `--focus` ring on `--bg` / `--surface` / `--surface-2` | 8.13 / 8.86 / 7.50:1 | 3.0 | pass |
| `--focus-halo` on `--ink` / on `--brand` (the halo carries the ring on dark surfaces) | 17.38 / 8.86:1 | 3.0 | pass |

`--line` (1.39:1) and `--brand-line` (2.11:1) are decorative hairlines only; no control border, no meaning-bearing icon and no text uses them.

## Density

Ledger is the **densest** of the five directions: the whole queue is meant to be read without scrolling. Measured at 1440×900 on `requests.html`: the page head, the single-row filter panel, the result line and the table head occupy 363px, rows are 61px (two lines at most — the longest titles and the `Raised` date wrap once inside fixed column widths of 110 / flexible / 150 / 205 / 120 / 150 / 150px), so the eighth row starts at 790px and **all 8 request rows start above 900px**. The seven dashboard figures fit one row of seven tiles at 1440 (4 + 3 below 1280), the four open requests sit in a table rather than cards, and the device record shows both fact panels side by side. Table cells are 16px on 22px leading with 8px vertical padding; the 13px uppercase column headers and chips are the only text under 15px, and body text is never below 16px. On a phone the same markup relaxes: 2-up tiles, 104px stacked queue cards, one fact panel above the other.

## Components

All defined once in `style.css` section 5 and shown in every state on `ui-kit.html`.

| Component | Class | Treatment |
|---|---|---|
| Primary button | `.btn.btn-primary` | `--brand` fill, white label, `--r-md`, 44px (52px `.btn-lg` for the page's main action, 48px in the sidebar and tab bar), hover `--brand-hover`, press `--brand-active`, no movement |
| Secondary / quiet / destructive | `.btn-secondary` `.btn-quiet` `.btn-danger` | White fill with a `--line-strong` border; borderless `--brand` label with underline on hover; `--danger` fill, never within 24px of the primary |
| Icon-only button | `.btn-icon` | 44×44, always `aria-label` **and** `title` (used only for `Clear the search box` and the toast's Close) |
| Busy button | `[aria-busy="true"]` | Label swaps to `Sending…` behind a 16px spinner, `disabled`, width locked before the swap |
| Field | `.field` `.label` `.help` `.input` `.select` `.textarea` `.file` | 44px (48px on phone), white fill, 1px `--line-strong` border, `--r-sm`; label 16px semibold, help 15px `--muted` between label and control; focus turns the border `--brand` under the ring |
| Field error | `[aria-invalid="true"]` `.field-error` | 2px `--danger` border with a 4px `--danger-tint` left edge, message below in 15px `--danger` with the `!` icon; `aria-describedby` reads help then error |
| Radio / checkbox row | `.choice` | 44px bordered row, the option sentence inside the `<label>`, `--brand-tint` fill when checked |
| Search field | `.search` | 48px on phone, magnifier at left, clear button at right (only once scripting is present) |
| Status badge | `.badge.badge-info/-brand/-warn/-ok/-muted/-danger` | 28px, tint fill, L80 border in the same hue, 16px Solar Bold icon + 14px semibold word, never one without the other |
| Urgency chip | `.badge.chip.chip-muted/-danger` | Same shell, outline only, so it never competes with status |
| Table row | `.table.queue tr` | 61px at most, 1px `--line` rule, hover `--surface-2`, no zebra; `<th scope="row">` on the reference; becomes a grid card under 1024px from the same markup |
| Card / list card | `.card` `.card-list` | White, 1px `--line`, `--r-md`, padding 24px, no shadow |
| Figure tile | `.stat` `.stat-urgent` | Mono 34px number over 15px `--muted` words; the urgent tile adds a 3px `--danger` top rule and the flame |
| Timeline item | `.timeline li` | 1px `--brand-line` rail, 9px `--brand` square node, mono date, then who, then what |
| Alert | `.alert.alert-info/-success/-warning/-danger` | Tint band with a 4px left bar in the hue, 24px icon, 17px Archivo title, 16px body; the error summary is `role="alert" tabindex="-1"` |
| Toast | `.toast` | `--ink` fill, white text, `--shadow-pop`, `role="status"`, `Undo` and `Close`, 8 s auto-dismiss paused on hover and focus; bottom-left above the sidebar on desktop, bottom-centre on phone |
| Modal | `dialog.modal` | 480px, `--r-lg`, `--shadow-pop`, focus on the title, Tab trapped, Escape closes, focus returns to `Mark it returned` |
| Empty state | `.empty` | Centred 48px `--line-strong` icon, one heading, one sentence, one primary button |
| Pagination | `.pagination .page-link` | 44px links, current page `aria-current="page"` with a 2px `--brand` underline |
| Wayfinding | `.nav-item[aria-current="page"]` `.count` `.breadcrumb` | 3px purple bar + purple bold label + `aria-current`; mono count pill; breadcrumb on the device page |
| Avatar | `.avatar` | 36px `--r-sm` square, `--brand-tint` fill, `--brand-strong` mono initials `NP` |
| Icons | `.icon` `.icon-22` `.icon-24` `.icon-40` `.icon-48` | Solar Bold, one `<symbol>` sprite per page, `fill="currentColor"`; 16px in badges, 20px in text, 22px in the tab bar, 24px in alerts, 40px no-permission, 48px empty state |

## Accessibility

- **Landmarks:** `<header>`, `<nav aria-label="Main">`, `<main id="main">`, `<nav aria-label="Utility">` and `<footer>` once per app page; `role="search"` on the filter form; `<nav aria-label="Breadcrumb">` on the device page. The sign-in page has `<main>` and `<footer>` only.
- **Headings:** one `<h1>` per page, worded as the navigation label that reached it (`Home`, `Requests`, `Raise a request`, `Design kit`; `Devices` opens `IT-0142 — Dell Latitude 3540 laptop` with `Devices` in its breadcrumb); `<h2>` per section, including the sidebar's `Work` and `Start` group titles; `<h3>` only inside the kit specimens. No level is skipped.
- **Skip link** `Skip to main content` is the first focusable element on every page and points at `#main`, which has `tabindex="-1"`.
- **Focus ring:** 3px `--focus` (the crest purple) with a 2px offset and a 2px white halo inside the offset, on every focusable element, so it reads on white, on slate, on the purple button and on the dark toast. Never removed, never replaced by a colour change alone. `ui-kit.html` shows it on a light and on a dark surface.
- **Keyboard:** tab order follows visual order (skip link → sidebar or top bar → main → utility); no positive `tabindex`; nothing is reachable by hover alone; the dialog traps Tab, closes on Escape and returns focus to its opener; the error summary takes focus on load and each of its links moves focus to the field.
- **Forms:** every control has a visible `<label for>`; help text sits between the label and the control and is linked with `aria-describedby`; a placeholder is never the only label; `aria-invalid="true"` only on fields that failed, with the error `<p id="…-error">` appended to `aria-describedby` after the help; the urgency radios are a `<fieldset>` with `<legend>How urgent is it?</legend>`; `Your name` is a real read-only labelled input.
- **Tables:** `<caption>` (visually hidden), `<th scope="col">` on every column, `<th scope="row">` on the reference, `aria-sort` on the sorted column, and a visually hidden column name inside each cell for the phone card layout.
- **Status is never colour alone:** every request status, device status, condition and urgency is an icon plus its word; greyscale the page and nothing is lost.
- **Touch targets:** at 390px every control is at least 44×44 — tab-bar cells 87×56 and 130×56, list rows ≥104px, primary buttons 52px, fields 48px, pagination 44px; radios are 22px inside 44px `<label>` rows that are the target; `Cancel` sits 24px from `Send the request`.
- **Motion:** hover and focus colours 120ms linear; toast 160ms slide-and-fade in, 120ms out; modal backdrop fade only. The `prefers-reduced-motion: reduce` guard in `style.css` section 8 collapses every animation and transition to 0.01ms and sets `scroll-behavior: auto`.
- **Text size:** body 16px on 26px leading, never smaller; lead 18px; the only text under 15px is the 13px uppercase column-header / eyebrow style, used for labels only.
- **Contrast:** every pair in the Palette table above meets AA; control borders meet 3:1 on every surface they sit on.

## Why it suits non-technical school staff

Nimali Perera is the only technician on site, and her problem is not learning software — it is holding eight open jobs in her head while Suresh Kumara stands at the ICT Room door about the projector in Science Block Lab 2. Ledger never hides anything from her: the sidebar shows `6` beside `Requests` before she clicks, the whole queue of eight fits above the fold at 1440×900, and every status is a word next to an icon (`In progress`, `Waiting on someone`) so she scans a column instead of reading it. The seven figures on `Home` are the seven numbers she is asked for in the staff room, worded the way she would say them (`3 devices due back next week`).

For the teacher or office administrator who borrows the screen — Dilani Fernando reporting that a laptop will not connect, Anoma Silva reporting a jammed printer — the same design is safe because everything that exists is on the page with a label on it. There is no menu to discover, no hover to find, and no icon standing alone: the four navigation words are `Home`, `Requests`, `Devices` and `Raise a request`, and the one filled purple button on every screen is the thing most people came to do. The request form asks one question at a time in plain words (`What is wrong?`, `Where is it?`, `How urgent is it?`) with an example under each, keeps what was typed when something is missing, and tells the person exactly which two things to fix. On a phone, the tab bar keeps `Raise a request` under the right thumb, and a 44–56px target size means it works for a hurried tap between lessons.

## Navigation model

**Desktop (≥1024px) — left vertical nav: a persistent 248px sidebar, items grouped under `Work` and `Start` headings, with live queue counts and the primary action inside it.** (A left vertical nav is not unique to Ledger — Signpost also uses one, as a 96px framed rail; what is Ledger's own is the wide grouped sidebar with counts and the full-width button.) A 248px slate (`--surface-2`) panel, separated from the white content column by a 1px `--line` rule, holds: the 32px crest chip and wordmark; group `Work` → `Home`, `Requests` (count pill `6`), `Devices`; group `Start` → the one filled purple `Raise a request` button (48px); and at the bottom the person (`NP` avatar, `Nimali Perera`, `ICT Technician`), `Design kit` and a `Sign out` button in a POST form. The current item is marked three ways: `aria-current="page"`, a 3px purple bar on its left edge, and a purple bold label. Group labels are real `<h2>`s inside `<nav aria-label="Main">`.

**Phone (<1024px) — fixed bottom tab bar, icon and word** (the only direction of the five that uses one). Four tabs, 56px tall plus the safe-area inset: `Home`, `Requests` (count badge), `Devices`, `Raise a request` — the last is the widest cell, under the right thumb, and the only one with a filled purple background. A 52px sticky top bar keeps the crest chip, the page name and a `Menu` link, which is a plain anchor to `#utility`, the section at the end of the document holding the person, `Design kit` and `Sign out`. The content column reserves 96px at the bottom so nothing hides behind the bar.

**With JavaScript off.** Every part of the navigation is plain HTML and CSS: the sidebar and tab bar are the same `<nav>` restyled at the breakpoint, the counts and the current-page marking are in the markup, and `Menu` is an anchor. The filter and sort form on `requests.html` is a `<form method="get">` with an `Apply` button (visually hidden only once scripting is present); the phone `Filter and sort` disclosure is a `<details>`; the `Mark it returned` button on `device.html` is a link to a confirmation section at the foot of the page, which the script upgrades to a `<dialog>`; the sign-out is a POST form. Nothing the pages' tasks need is JavaScript-only.

**The device register list is deliberately not prototyped.** `Devices` opens the single record `IT-0142`, because `requests.html` already proves the list, filter, sort, status and empty-state patterns a register list would reuse.

## Skills used

- Named by the direction brief and loaded: `technical-wireframe-info-layout` (annotation and linework discipline only; its dark surface was not used), `container-lines`, `number-details`, `accessible-content:table-accessibility`, `interaction-design:search-ux`, `inclusive-interaction:keyboard-navigation`, `solar-duotone-bold` (the **Bold** weight; icons fetched by name from the Solar set), `dataviz` (the one bar chart: single series, no legend, direct label on the maximum, text alternative beside it), `cognitive-accessibility:plain-language-design`.
- Preloaded for the builder: `accessible-content:form-labelling`.
- `ui-design:information-density`, also named by the brief, is not an installed skill (the nearest installed one is `adaptive-interfaces:information-density`); the density rules in the direction brief itself were followed instead.

## Demo hooks

These query-string switches exist so the states can be reached without a server. They are **prototype-only** and are never carried into `templates/`.

| URL | State |
|---|---|
| `login.html?demo=error` | Sign-in error: the alert `We couldn't sign you in`, username still `nimali.p`, password cleared and focused, both fields `aria-invalid` |
| `request-form.html?demo=errors` | Validation errors: summary alert with two links, `What is wrong?` and `Where is it?` marked `aria-invalid` with their messages wired through `aria-describedby`; every other field keeps what was typed; focus moves to the summary |
| `request-form.html?demo=server` | Server error: `We couldn't save that just now`, nothing lost |
| `requests.html?demo=empty` | Empty list: `No requests match what you chose` with the `Clear the filters` button; the search box keeps its text |
| `dashboard.html?demo=toast` (or `?demo=toast` on any app page) | Success toast `Request sent. We gave it the number REQ-2049.` with `Undo`; the dashboard also shows the same sentence as a success alert, and focus lands on the `<h1>` |
| `device.html?demo=returned` | The toast `IT-0142 is back in the ICT Store.` — where the no-JavaScript confirmation form lands; the `<dialog>` shows the same toast on `Yes, mark it returned` |
| `device.html?demo=denied` | No permission: `You can't open this page` with `Raise a request`; the sidebar stays so the person is not stranded |

The in-place filter (status, urgency, who, sort, search) is live on `requests.html` without any hook; the result line reads `Finding requests…` while it runs and then announces the count.

## Screenshots

`screenshots/` holds the fifteen canonical full-page captures of the delivered HTML, taken with the web fonts loaded: `desktop-*.png` at 1440×900 and `mobile-*.png` at 400×844 for the six pages, plus the state captures `desktop-login--error.png`, `desktop-request-form--errors.png` and `desktop-requests--empty.png` at 1440×900.

## Notes for whoever ports this stylesheet

- `style.css` is organised in the eight numbered sections the task brief names; every colour, font, space, radius, shadow and duration is a `:root` token and nothing outside `:root` carries a raw colour.
- Icons are Solar Bold, inlined once per page as an SVG `<symbol>` sprite at the top of `<body>` and referenced with `<use href="#i-…">` and `fill="currentColor"`; `app.js` clones from the same sprite for the toast. Solar has no `wrench` glyph, so `In repair` uses `toolbox`; `Issued` uses `hand-shake`.
- The one chart (`Requests raised in the last five school days`: Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1) is inline SVG with `role="img"`, an `aria-label` reading `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.`, and the same figures printed beside it as a visible `<figcaption>`. Tuesday, the highest, is `--brand-strong` with its value above the bar; Wednesday's zero is drawn as a labelled 2px `--line-strong` empty bar so the category is never dropped.
- The crest images in `assets/` are byte copies of the three cut-outs and are never recoloured, filtered or stretched; `crest.png` is shown at 72px (56px on phone) on the sign-in page, `crest-chip.png` at 32px in the sidebar and top bar.
