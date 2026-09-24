# Direction C — Broadsheet

Broadsheet sets the Technology Management Desk like a well-printed school notice: a ruled masthead across the top, one generous column of 18px text you can actually read, and a thin "On this page" index down the side so long records stay navigable. It has no boxes, no shadows and no rounded corners — structure comes from rules, indents and the space between things, the way a page of print does.

Open any page straight from the file system (`design/c-broadsheet/dashboard.html`). Google Fonts is the only thing fetched from the network; everything else is inside this folder.

## Concept

A page of print, not a panel of controls. Everything that other directions would box — a request, a device, a figure, a form field — is a ruled row on lilac-grey paper, set in a serif heading face over a large humanist sans, with the page's apparatus (the section index, or on the queue the filters) kept out in the margin so the reading column carries only what there is to read. Because it is drawn with rules instead of cards, a page printed from it looks like the screen, which matters in a school that still puts paper in a file.

Three things carry the direction: the two-row ruled masthead with the crest chip and wordmark; the 680px reading column beside a 240px sticky margin; and status shown as a small tinted pill with a linear icon and a word, the one non-text shape on the page.

## Pages

| File | What it is |
|---|---|
| `login.html` | Sign in — a title page: the 2px rule across the top, the crest at 104px, `Welcome back`, two underline fields in a 380px column, one purple button |
| `dashboard.html` | Home — seven figures as ruled rows, four requests to work on, three devices to watch, the one chart (horizontal bars), and `Things you can do` |
| `requests.html` | Requests — `<h1>`, lead, search, count and eight ruled rows in the column; `Filter and sort` in the sticky margin; empty state; pagination |
| `device.html` | Devices — the `IT-0142` record: status pills, two buttons, four ruled sections (`<dl>` facts, linked requests, a hanging-date timeline), the confirm-return dialog with a foot-of-page fallback |
| `request-form.html` | Raise a request — seven fields in four sections on a 560px column, the error summary as a left-ruled alert, the urgency radios as 56px rows |
| `ui-kit.html` | Design kit — every component in every state, the icon set, type scale, colour table with ratios, spacing scale, focus ring on light and dark |

The device register list is deliberately not prototyped: `Devices` opens the single `IT-0142` record (brief decision D8), because `requests.html` already proves the list, filter, sort, status and empty-state patterns a register would reuse.

## Fonts

| Family (Google Fonts) | Weights loaded | Used for |
|---|---|---|
| **Newsreader** | 400 italic, 500, 600 | Wordmark `Polymath College` (600, 22/26, letter-spacing .005em), h1 (600, 44/52; 34/42 on a phone), h2 (600, 28/36; 24/32 on a phone), h3 (500, 21/30, design kit only), figure numbers (500, 30/34, tabular numerals), help text and timeline dates (400 italic, 16/24 and 17/24) |
| **Source Sans 3** | 400, 600, 700 | Body 18/30 on a 66-character measure, lead 20/32, metadata 16/24, labels (600, 17/24), buttons and navigation (700, 17/22), badge words (600, 15/20) |

The wordmark font is Newsreader 600. Headings are never letterspaced and never uppercase. Body text is 18px at both viewports — the largest of the five directions.

## Palette

Derivation: the crest purple `#722A82` is `hsl(289, 51%, 34%)`. Broadsheet keeps that hue and drops its saturation almost to nothing for the paper, so every neutral is a lilac-grey cast of the crest rather than a separate colour. Ink is the same hue at 12% lightness, which is why the type reads as black but never cold. Functional hues sit far from 289° (158°, 40°, 348°, 202°) so they can never be mistaken for the brand.

| Token | Hex | Derived from the crest |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#4A1857` | Crest hue at L 24% — hover, the tallest chart bar |
| `--brand-tint` | `#F2E9F6` | Crest hue at L 95% — badge and avatar fill |
| `--rule-brand` | `#C6B0D0` | Crest hue at L 76% — decorative hairline beside the timeline |
| `--ink` | `#1A1420` | Crest hue at S 20% L 12% — the type |
| `--muted` | `#5C5266` | Crest hue at S 10% L 36% — metadata, help, lead |
| `--rule` | `#DCD2E4` | Crest hue at L 86% — 1px section rules |
| `--rule-strong` | `#8C8095` | Crest hue at S 14% L 54% — field underlines |
| `--bg` | `#F7F3FA` | Crest hue at S 30% L 97% — the paper |
| `--surface` | `#FFFFFF` | The masthead, fields and footer |
| `--surface-2` | `#EFE8F4` | Crest hue at L 94% — hovered rows, read-only fields |
| `--ok` / `--ok-tint` | `#0C5F46` / `#E3F1EB` | Hue 158 — Fixed, Good, In store |
| `--warn` / `--warn-tint` | `#7A5300` / `#F7EEDC` | Hue 40 — Waiting on someone, In repair, Needs repair |
| `--danger` / `--danger-tint` | `#A3244A` / `#FAE7EC` | Hue 348 — Urgent, Out of service, errors |
| `--info` / `--info-tint` | `#0B5478` / `#E4EFF6` | Hue 202 — New, Issued |
| `--focus` | `#722A82` | Focus ring on light surfaces; on `--ink` surfaces the ring is `--surface` |

**Where the brand colour appears on every page:** the `Raise a request` navigation label and its underline, the current-page underline in the masthead, the primary button, every link, the field underline on focus, the `In progress` badge, the chart bars and the focus ring.

### Contrast pairs (computed with the WCAG 2 relative-luminance formula, not estimated)

| Pair | Ratio | Needs | Result |
|---|---|---|---|
| `--ink` on `--surface` | 18.03:1 | 4.5 | pass |
| `--ink` on `--bg` | 16.44:1 | 4.5 | pass |
| `--ink` on `--surface-2` | 15.04:1 | 4.5 | pass |
| `--ink` on `--brand-tint` | 15.25:1 | 4.5 | pass |
| `--muted` on `--surface` | 7.36:1 | 4.5 | pass |
| `--muted` on `--bg` | 6.71:1 | 4.5 | pass |
| `--muted` on `--surface-2` | 6.14:1 | 4.5 | pass |
| `--surface` on `--brand` (primary button label) | 8.86:1 | 4.5 | pass |
| `--brand` on `--surface` (links, nav) | 8.86:1 | 4.5 | pass |
| `--brand` on `--bg` | 8.09:1 | 4.5 | pass |
| `--brand` on `--surface-2` | 7.40:1 | 4.5 | pass |
| `--brand` on `--brand-tint` (In progress badge) | 7.50:1 | 4.5 | pass |
| `--brand-strong` on `--brand-tint` (avatar) | 11.39:1 | 4.5 | pass |
| `--brand-strong` on `--surface` | 13.47:1 | 4.5 | pass |
| `--rule-strong` on `--surface` (field underline) | 3.73:1 | 3.0 | pass |
| `--rule-strong` on `--bg` | 3.40:1 | 3.0 | pass |
| `--ok` on `--surface` | 7.66:1 | 4.5 | pass |
| `--ok` on `--bg` | 6.99:1 | 4.5 | pass |
| `--ok` on `--ok-tint` | 6.58:1 | 4.5 | pass |
| `--warn` on `--surface` | 6.85:1 | 4.5 | pass |
| `--warn` on `--bg` | 6.25:1 | 4.5 | pass |
| `--warn` on `--warn-tint` | 5.94:1 | 4.5 | pass |
| `--danger` on `--surface` | 7.22:1 | 4.5 | pass |
| `--danger` on `--bg` | 6.59:1 | 4.5 | pass |
| `--danger` on `--danger-tint` | 6.09:1 | 4.5 | pass |
| `--surface` on `--danger` | 7.22:1 | 4.5 | pass |
| `--info` on `--surface` | 8.22:1 | 4.5 | pass |
| `--info` on `--bg` | 7.50:1 | 4.5 | pass |
| `--info` on `--info-tint` | 7.04:1 | 4.5 | pass |
| `--focus` on `--bg` | 8.09:1 | 3.0 | pass |
| `--focus` on `--surface` | 8.86:1 | 3.0 | pass |
| `--focus` on `--surface-2` | 7.40:1 | 3.0 | pass |
| `--surface` ring on `--ink` (toast, skip link) | 18.03:1 | 3.0 | pass |
| `--surface` text on `--ink` (toast) | 18.03:1 | 4.5 | pass |

`--rule` (1.46:1) and `--rule-brand` (2.00:1) are decorative hairlines only; a field underline always uses `--rule-strong` or darker. `--focus` on `--ink` would be 2.03:1, which is why dark surfaces switch the ring to `--surface`. No control-border pair fell under 3:1, so no token needed darkening.

## Why it suits non-technical school staff

Anoma runs the office and lives in printed lists, letters and registers; Ruwan reads a device record before he signs a purchase off; Dilani opens the desk twice a term to say a laptop will not join the Wi-Fi. They are reading people rather than dashboard people, and each is usually hunting for one fact in a page of facts. Broadsheet gives them the largest body text of the five (18px on a 66-character line), headings that visibly rank, and a record page whose four sections are listed in the margin, so "warranty" is one click rather than one scroll. Every field says what to type in a short italic aside, the urgency choices are plain sentences ("A class or the office is stopped right now."), and every error keeps what was typed and says what to do next.

Because the page is drawn with rules instead of cards, a page printed from it looks like the screen — which matters in a school that still puts paper in a file. Each page has exactly one purple button, and it sits where the page's job is done: `Sign in` under the fields, `Send the request` at the foot of the form, `Raise a request about this device` at the top of the record, and on the dashboard `Raise a request` in `Things you can do` at the end of the page, while the masthead's purple `Raise a request` label is the route to it from anywhere. The four navigation labels are places or jobs (`Home`, `Requests`, `Devices`, `Raise a request`), not data types.

## Navigation model

**Desktop (1080px and wider): ruled masthead with breadcrumbs, plus an "On this page" index beside the column.** Row 1 (64px) carries the crest chip and `Polymath College` at the left, the signed-in person and a `Sign out` button at the right, under a 2px ink rule. Row 2 (56px) holds the four labels; the current one is bold with a 3px purple underline, and `Raise a request` is set in purple with a 2px underline so it reads as the action without becoming a button. Row 3, the breadcrumb trail (`Devices › IT-0142`, last item as text), exists only on `device.html`, where there is a level to climb; the other pages are one step from the masthead, so their masthead is 123px. The content is a centred 1040px band: a 680px article column (560px on the form), a 40px gutter, and a sticky 240px margin slot. On the dashboard, device record, form and design kit that slot is `<nav aria-label="On this page">` listing the page's `<h2>`s, the current one marked with a 2px purple bar; on `requests.html` it is the `Filter and sort` `<aside>` holding Status, How urgent, Who is on it, Sort and `Clear the filters`, so the queue's reading column carries nothing but the `<h1>`, lead, search, count and rows. `Design kit` sits in the footer beside the college name.

**Phone (under 1080px): sticky masthead with a horizontally scrolling navigation strip.** A 56px masthead (crest chip, wordmark, `Sign out` with its word visible), then a strip of 48px-tall links that scrolls sideways where the four labels overflow it, with a visible thin scrollbar and, between 401 and 560px, a persistent edge fade that says there is more. **At 400px and narrower the four labels cannot fit one row, so the strip wraps instead: `Home`, `Requests` and `Devices` share the first row and `Raise a request` takes the whole second row, under the thumb.** Nothing scrolls, nothing is hidden, and the DOM order (`Home` · `Requests` · `Devices` · `Raise a request`) is the visual and Tab order at every width. The breadcrumb line follows at 15px on `device.html` only. The "On this page" index becomes a closed `<details>` directly under the `<h1>`; on `requests.html` the margin `<aside>` becomes a closed `<details>` titled `Filter and sort` under the search field, with the same controls in the same order.

**With JavaScript off:** the strip is a CSS overflow (or wrapping) container, the index is a `<details>`, the breadcrumbs are links, the filter and sort form is a `<form method="get">` with its own `Apply` button (hidden only once scripting is present), the confirm dialog falls back to a section at the foot of the device record reached by the same link, and the toast's sentence is repeated as an alert on the page. `app.js` adds only: `?demo=` switching, the scrollspy highlight in the desktop index, in-place queue filtering with a live count, hiding `Apply`, toast rendering, focusing the error summary, the `<dialog>` focus trap, and closing the phone disclosures on load.

## Density

Low–medium: fewer rows than the working screens, more words in each. Request rows have a 109px pitch on desktop (reference, urgency and status on the first line; the sentence at 18px; one line of metadata at 16px; 12px of padding above and below; a 1px rule). The queue page spends its space on the reading column, not on apparatus: the masthead is two rows (123px, no breadcrumb), the column runs `<h1>` → lead → search → count → rows with no section headings, and the filters, sort and `Clear the filters` sit in the sticky margin `<aside>`. Measured at 1440×900 the first row top is at **411px** (the direction file budgets 438 with a two-line lead; here the lead fits on one line at 680px, and 411 is inside the file's 355–463 tolerance) and the five row tops are 411 · 520 · 629 · 738 · 847, so **5 request rows start inside the first 900px** (the sixth at 956). On the five-direction ladder that is b Parchment 3 < **c Broadsheet 5** < d Signpost 6 < e Workbench 7 < a Ledger 8.

## Components

Everything is square (`--radius: 0`); the 999px status pill is the one curve. There are no shadows except `--shadow-pop` on the modal and the toast, which sit above the page rather than on it. Structure is rules: `--rule-hair` 1px between rows, `--rule-section` 2px ink above each section.

| Component | Class | Treatment |
|---|---|---|
| Primary button | `.btn--primary` | `--brand` fill, `--surface` label, 52px tall, Source Sans 3 700; hover to `--brand-strong`. One per page |
| Secondary button | `.btn--secondary` | 2px `--ink` border, no fill, 48px |
| Quiet button / link | `.btn--quiet` | `--brand` text with a 1px underline that thickens to 2px on hover; 44px hit area. `Cancel` is this |
| Destructive button | `.btn--danger` | 2px `--danger` border, `--danger-tint` on hover; kept 24px from the primary |
| Icon-only, disabled, busy | `.btn--icon`, `[disabled]`, `[aria-busy]` | 48×48 with `aria-label`; `--muted` on `--surface-2`; `Sending…` with an 18px spinner and locked width |
| Field | `.control` | Underline field: 48px, `--surface` fill, 1px `--rule-strong` bottom line; 2px `--brand` on focus plus the 3px ring; 2px `--danger` when `aria-invalid` |
| Label / help / error | `.field__label`, `.help`, `.field-error` | Label 17px semibold; help Newsreader italic 16px between label and field; error 17px semibold `--danger` with a 18px icon, both wired with `aria-describedby` |
| Radios / checkboxes | `.choices`, `.choice` | A `<fieldset>` with a legend; each option a 56px ruled row whose whole width is the target; the control drawn at 24px inside a 44px box |
| Status badge | `.badge--info / --brand / --warn / --ok / --muted / --danger` | 28px pill, tint fill, no border, 18px linear icon plus the word at 15px semibold |
| Urgency chip | `.urgency--danger / --muted` | Icon plus word, no fill, no border; `Urgent` in `--danger` bold, the others `--muted` |
| Row (request / device) | `.row`, `.queue tr` | No card: 1px rule above, reference and status on the first line, the sentence at 18px, metadata at 16px `--muted`; hover fills `--surface-2` edge to edge |
| Fact list | `.facts` | `<dl>` with the term in a 140px `--muted` column and the value at 18px, one rule per pair |
| Figure | `.figure` | Newsreader 500 number at 30px with tabular numerals, an icon where the figure has one, the words at 18px; 56px ruled row |
| Timeline item | `.timeline__item` | The date hangs in a 140px column in Newsreader italic; the entry sits against a 1px `--rule-brand` line with a 24px indent; no dots |
| Alert | `.alert--info / --ok / --warn / --danger` | 2px left rule in the functional hue, no fill, 20px icon, Newsreader 21px title, 18px body |
| Toast | `.toast` | Bottom-left, `--ink` fill, `--surface` text, square, `--shadow-pop`, `Undo` and `Close`; `role="status"`, 8 seconds, pauses on hover or focus |
| Modal | `.modal` | A `<dialog>` 520px wide, 2px `--ink` border, `--shadow-pop`; traps focus, Escape closes, focus returns to the opener |
| Empty state | `.empty` | Centred between two 2px rules: 48px icon, heading, one sentence, one button, 54px of air |
| Pagination | `.pager` | `Previous`, the page, `Next` on one ruled line; 48px targets, 24px apart |
| "On this page" index | `.pageindex`, `.pageindex-m` | Sticky margin list of the page's `<h2>`s with a 2px `--brand` bar on the current one; a `<details>` on a phone |
| Filter and sort aside | `.filters-aside` | The queue's margin slot: four selects and `Clear the filters`, sticky under the masthead; a `<details>` on a phone |
| Avatar | `.avatar` | The person is set as text; a 40px `--brand-tint` initials block exists for where a name is too long |
| Chart | `.chart` | Horizontal bars, one series, `--brand` with the peak in `--brand-strong`, values at the bar end, a text alternative under it; Wednesday's zero is a labelled empty bar |

Icons are **Solar Linear** (Iconify `solar`, 1.5px strokes), inlined once per page as `<symbol>`s and used with `<use>`, always `currentColor`, at 18px beside text, 20px in alerts and 48px in empty states: `star` New, `refresh-circle` In progress, `clock-circle` Waiting on someone, `check-circle` Fixed and Good, `archive` Closed, `box` In store, `hand-stars` Issued, `sledgehammer` In repair (Solar has no wrench), `close-circle` Out of service, `danger-triangle` Needs repair, `hourglass` Can wait, `flag` Normal, `fire` Urgent.

Tokens: a 6px space scale (`--s1` 6 … `--s7` 72), a type scale in px with matching line heights, four durations (150ms underline, 180ms index and modal, 200ms toast), and every colour above — all declared once in `:root` of `style.css`, which is ordered as tokens · base · icons · shell · components · page-specific · responsive · reduced motion and print.

## Accessibility

- **Landmarks:** `<header>` with `<nav aria-label="Main">` (and `<nav aria-label="Breadcrumb">` on the device record), `<main id="main">`, `<nav aria-label="On this page">` or the `Filter and sort` `<aside>` beside the column, `<footer>` with `<nav aria-label="Utility">`, `role="search"` on the queue's search form.
- **Headings:** one `<h1>` per page, worded as the navigation label that reached it; `<h2>` per section; `<h3>` only inside design-kit specimens. The "On this page" index is generated from exactly those `<h2>`s. `requests.html` has one `<h2>`, the aside's `Filter and sort`.
- **Skip links:** `Skip to main content` first on every page; `Skip to the queue` after the masthead on `requests.html`, landing on the `<table>`.
- **Forms:** every control has a visible `<label for>`; help and error text are linked with `aria-describedby` in that order; `aria-invalid="true"` only on fields that failed; the urgency radios are a `<fieldset>` with a legend and their help linked to the fieldset; the error summary is `role="alert" tabindex="-1"`, focused on load, with a link that moves focus to each field; nothing typed is lost.
- **The queue** is a `<table>` with a visually hidden caption, `<th scope="col">` headers and `<th scope="row">` on the reference, styled as ruled rows; `aria-sort` follows the sort control.
- **Status** is always an icon plus a word, never colour alone; urgency also changes weight.
- **Focus:** a 3px `--focus` ring with a 2px offset on every focusable element; `--surface` on dark surfaces. Tab order follows DOM order, which is the visual order at every width (the phone strip no longer reorders anything).
- **Targets:** 44px minimum at phone width — nav links 48px, fields 48px, buttons 48–52px, radios and checkboxes in a 44px box, breadcrumb and index links 44px, pagination 48px. Inline links inside a sentence of prose are the only exemption.
- **Motion:** underlines and the index marker move in 150–180ms; the toast and modal fade in 200/180ms; nothing else moves, and `prefers-reduced-motion: reduce` collapses every duration to .01ms.
- **Dialogs:** the modal traps focus, closes on Escape and returns focus to `Mark it returned`; without JavaScript the same words sit in a section at the foot of the page.

## Skills used

Designer (from the direction file): `ux-strategy:information-architecture`, `ui-design:design-screen`, `ui-design:visual-hierarchy`, `ui-design:type-system`, `ui-design:color-palette`, `interaction-design:state-machine`, `interaction-design:form-design`, `cognitive-accessibility:plain-language-design`, `accessible-content:heading-structure`, `dataviz`.

Builder (loaded for this folder): `editorial-tech`, `light-mode-paper-technical`, `ui-design:readable-measure`, `ui-design:typography-scale`, `accessible-content:heading-structure`, `accessible-content:table-accessibility`, `accessible-content:form-labelling`, `ux-strategy:information-architecture`, `dataviz`, `cognitive-accessibility:plain-language-design`.

Icon family: **Solar Linear** — the Linear weight of the Solar set on Iconify, as the direction file specifies (the shared `solar-duotone-bold` skill's guidance on sizing, pairing icons with words and keeping to one family was followed; the Duotone Bold weight itself is not used).

## Demo hooks

| URL | State |
|---|---|
| `login.html?demo=error` | `We couldn't sign you in`; `nimali.p` stays in the username box; focus moves to the password field |
| `request-form.html?demo=errors` | `We couldn't send this yet — 2 things need your attention`, with a link to each field; every typed value is kept; the two failed fields get `aria-invalid="true"`, a 2px danger underline and their message; focus moves to the summary |
| `requests.html?demo=empty` | The filters are set to a combination that matches nothing (Closed and Urgent) and the queue shows `No requests match what you chose` with `Clear the filters`; the count reads `Showing 0 of 8 requests` |
| `dashboard.html?demo=toast` (or any app page) | The toast `Request sent. We gave it the number REQ-2049.` with `Undo` and `Close`, plus the same sentence as a success alert at the top of the page |
| `device.html?demo=denied` | `You can't open this page` with a link to raise a request; the masthead and breadcrumbs stay |

These hooks are prototype-only. They exist so the owner and the verifier can reach each state without a server, and they are never carried into `templates/`.

## Screenshots

`screenshots/` holds the fifteen canonical captures: full-page views of every page at 1440×900 (`desktop-*.png`) and at 400×844 (`mobile-*.png`), plus the state captures `desktop-login--error.png`, `desktop-request-form--errors.png` and `desktop-requests--empty.png`. All are taken with the web fonts loaded.

## Files

`login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html`, `style.css` (eight numbered sections, every value a `:root` token), `app.js` (one IIFE bound to `data-*` hooks), `assets/` (the three crest cut-outs, copied unmodified), `screenshots/`.
