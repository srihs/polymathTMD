`design/f-desk/`

# Direction F — Desk (a clean-room look-alike of the client's reference admin layout)

**What this is.** The client asked for the Technology Management Desk to look and behave like one
specific commercial admin template (named only under **Reference and licence** at the end of this
file). This spec re-creates that template's shell and visual language from **measurements**, in our
own tokens, class names and markup, dressed in the crest purple `#722A82`. The builder writes every
line from this file; nothing from the reference is copied (brief 003, criteria 1–6).

**Who it suits.** School staff who will be shown this side by side with the reference and asked
"is it the same?". The layout, type and spacing match. The only places we differ are where the
reference would fail a staff member: targets under 44px, grey text under 4.5:1, status shown by
colour alone. Each of those is listed as a deviation in the fidelity checklist (§13), so the client
sees it rather than discovering it.

---

## 0. How the values in this file were obtained

Every numeric value carries one of three tags. The verifier re-measures the **[I]** rows first.

| Tag | Meaning | How |
|---|---|---|
| **[M]** | **Measured** on the live reference | Playwright, run by the main session (read-only). `getComputedStyle` and `getBoundingClientRect` per layout region at 1440×900 and 400×844, light and dark, plus sidebar sizes "small" (icons) and "medium" (compact) (pass 1). Pass 2 opened the dropdowns and settings panel, and measured the reference's buttons, forms, validation, tables and sign-in pages, the boxed layout, the dark and brand sidebar tones, and the icons-size hover flyout. Pass 3 measured the notification rows, the soft badges, the settings panel in dark mode and the phone brand box. Output: session scratchpad `ref/*.json` (pass 2: `ref/pass2.json`, pass 3: `ref/pass3.json`) + `ref/*.png`, never the repo. |
| **[S]** | **Read off the reference screenshots** | The same scratchpad PNGs, read visually. Good to about ±2px and to "which colour family". |
| **[I]** | **Inferred**, not measured | Not in the measurement run (no element on the dashboard, or a panel that was closed). Chosen to be consistent with the measured values. **Re-measure before sign-off**; the list is in §15. |
| **[D]** | **Our decision**, no reference equivalent | Content the reference does not have, or a deviation forced by the floor. |

The reference's full set of rendered font sizes on its dashboard at 1440 is **[M]**: 10.2, 10.5,
10.8, 11, 12, 12.25, 13, 13.6, 14, 14.4, 15.4, 16, 17.5, 18, 21px. The **smallest is 10.2px**.
Criterion 26's floor is therefore: no text in the folder is smaller than **10.2px**. Our smallest
text is the 10.5px notification count.

---

## 1. The shell at a glance

```
1440 × 900, light, sidebar standard, full width
x=0          250                                                                       1440
┌────────────┬──────────────────────────────────────────────────────────────────────────┐ y=0
│ (crest)    │[≡]  [ Reference or words, e.g. REQ-2048        [⌕]]   [☾] [🔔³] [⚙] ┃NP Nimali Perera ▾┃│
│ Technology │ 52   search 304 wide, 44 tall                        52   52   52  ┃   ICT Technician ┃│
│ Management │                                                                          │ 70 (+1 border)
│ Desk       ├──────────────────────────────────────────────────────────────────────────┤ y=71
│────────────│  Home                                                            Home    │ title row
│ Menu       │                                                                          │ 18px/500, 24px below
│ ▌⌂ Home    │ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐                   │
│ Help desk  │ │ stat      │ │ stat      │ │ stat      │ │ stat      │  4 × 265, 24 gaps │
│  ☰ Requests›│ └───────────┘ └───────────┘ └───────────┘ └───────────┘                   │
│ Equipment  │ ┌──────────────────────────────────────┐ ┌─────────────────────────────┐  │
│  ▭ Devices │ │ Requests raised this week            │ │ Needs doing today  [Raise…] │  │
│ Prototype  │ │  (bar chart)                         │ │  3 request rows             │  │
│  ▦ Design kit││                                      │ └─────────────────────────────┘  │
│            │ └──────────────────────────────────────┘ ┌─────────────────────────────┐  │
│┌──────────┐│                                          │ Devices                     │  │
││Something ││                                          └─────────────────────────────┘  │
││not work… ││ ──────────────────────────────────────────────────────────────────────── │
││[Raise a…]││  2026 © Polymath College                      Technology Management Desk│ footer 60
│└──────────┘│                                                                          │
└────────────┴──────────────────────────────────────────────────────────────────────────┘
```

```
400 × 844, light (phone, below 992px)
┌──────┬─────┬──────────────────────────────────┐
│(crest)│ [≡] │           [⌕] [☾] [🔔³] [⚙] ┃NP┃│ 70 (+1)
│  73   │ 52  │           44  44   44   44  ┃60┃│
├──────┴─────┴──────────────────────────────────┤
│ Home                                          │ title, 18px/500
│ Home                                          │ breadcrumb stacked under it, 8px gap
│ ┌───────────────────────────────────────────┐ │
│ │ stat (full width, one per row)            │ │ 30px page padding each side
│ └───────────────────────────────────────────┘ │
│ …                                             │
│  2026 © Polymath College                      │ footer, stacked, centred
│  Technology Management Desk                   │
└───────────────────────────────────────────────┘
With JS: [≡] opens the sidebar as a 250px drawer from the left over a scrim.
With JS off: [≡] is hidden and a "Menu" link (href="#nav") sits in its place.
```

### 1.1 Shell geometry

| Region | Our spec | Tag |
|---|---|---|
| Sidebar width, standard | **250px** | [M] |
| Sidebar width, compact | **160px** | [M] |
| Sidebar width, icons | **70px** | [M] |
| Brand row at the top of the sidebar | 250 × 70px, padding 0 24px, same background as the sidebar, 1px right border `--nav-border` | [M] |
| Top bar | **70px** tall plus a 1px bottom border (71px box), `--c-surface`, border `--c-border`, padding-right 24px | [M] |
| Top-bar icon button | **52 × 70px** at ≥992px, icon 20px centred; **44 × 70px** below 992px | [M] 52×70 / [I] icon size / [D] 44 |
| Page padding | top **24px** under the top bar, sides **30px**, bottom 24px above the footer | [M] (content starts x=280 at 1440 and x=30 at 400) |
| Grid gutter | **24px** column and row gap | [M] (stat cards 265 wide with 24 gaps) |
| Title row | h1 left, breadcrumb right, row height 22px + **24px** padding-bottom | [M] |
| Footer | **60px**, padding 20px 30px, `--c-surface`, top border `--c-border`, 14px `--c-muted` | [M] height/padding/size, [D] colour (see §13 row 30) |
| Boxed width | **1300px**, centred (x=70 at 1440), shell shadow `--shadow-boxed`, `--c-boxed-outside` either side | [M] width, position and shadow; [I] outside colour |
| Phone breakpoint (sidebar becomes a drawer) | **below 992px** | [M] (the reference's lg breakpoint; its sidebar is 0×0 at 400) |
| Other breakpoints used | 1200px (stat cards 4-up → 2-up below), 768px (title row stacks, table becomes row cards); the user name and role hide below 992px, with the drawer | [M] breakpoint values exist on the reference; which layout changes at each is [I] |

### 1.2 Layout mechanism (for the builder)

- `<body>` holds `.skip`, the icon sprite, then `.shell`, a CSS grid:
  `grid-template-columns: var(--nav-w) minmax(0, 1fr)`, `grid-template-rows: auto 1fr auto`.
  - `.sidenav` (`<aside>` containing `<nav aria-label="Main">`) spans all three rows in column 1.
    `position: sticky; top: 0; height: 100vh; overflow-y: auto` (in `icons` size: `overflow: visible`,
    so flyouts can escape). Native scroll with `scrollbar-width: thin` and
    `scrollbar-color: var(--nav-scroll) transparent`.
  - `.topbar` (`<header>`) is row 1 of column 2, `position: sticky; top: 0; z-index: 20`.
  - `<main id="main">` is row 2 of column 2 and holds `.titlebar` then the page's cards.
  - `.page-foot` (`<footer>`) is row 3 of column 2.
- `--nav-w` is set **only** by `[data-nav-size]` (250 / 160 / 70px). Nothing else changes widths.
- `[data-width="boxed"] .shell { max-width: var(--boxed-w); margin-inline: auto; box-shadow: var(--shadow-boxed) }`,
  and `html[data-width="boxed"]` paints `--c-boxed-outside` on `<body>`.
- **Below 992px**: `.shell` becomes one column. `.sidenav` is `position: fixed; inset: 0 auto 0 0;
  width: 250px; transform: translateX(-100%)` and is shown by **either** `.sidenav:target`
  (no-JS, from the `Menu` link) **or** `.sidenav[data-open]` (set by `app.js`). The phone drawer always
  uses the standard 250px layout, whatever `data-nav-size` says, and keeps the chosen tone.
- The drawer is **not** a `<dialog>`. Reason: one element must be the always-visible desktop sidebar
  **and** the phone drawer, and a closed `<dialog>` is `display: none` without JS, which would break
  criteria 18 and 25. `app.js` gives the open drawer the modal behaviour instead: it sets `inert` on
  `.topbar`, `<main>` and `.page-foot`, shows `.scrim`, moves focus to the drawer's `Close the menu`
  button, and on close removes `inert` and returns focus to the toggle. The settings panel **is** a
  `<dialog>` (§6).

---

## 2. Sidebar

### 2.1 Structure (every app page, identical except `aria-current` and the `open` flag)

```html
<aside class="sidenav" id="nav" data-nav>
  <div class="sidenav__brand">
    <img src="assets/crest-chip.png" alt="" …> <span class="sidenav__wordmark">Technology Management Desk</span>
  </div>
  <a class="sidenav__close" href="#main" data-nav-close>…x icon… Close the menu</a>   <!-- phone only -->
  <nav aria-label="Main">
    <p class="sidenav__group-title" id="nav-g1">Menu</p>
    <ul class="sidenav__list" aria-labelledby="nav-g1"> <li> Home </li> </ul>
    <p class="sidenav__group-title" id="nav-g2">Help desk</p>
    <ul class="sidenav__list" aria-labelledby="nav-g2">
      <li><details class="sidenav__parent" [open]>
            <summary class="sidenav__link">icon · Requests · chevron</summary>
            <ul class="sidenav__children"> All requests · Raise a request </ul>
          </details></li>
    </ul>
    <p … id="nav-g3">Equipment</p> <ul …> Devices </ul>
    <p … id="nav-g4">Prototype</p> <ul …> Design kit </ul>
  </nav>
  <section class="helpcard" aria-labelledby="help-title"> … </section>
</aside>
```

- Group titles are `<p>` elements that label their lists, **not** headings, so every page's heading
  outline starts at its `<h1>` (criterion 8).
- The crest has `alt=""` because the wordmark beside it names the product (002/23).
- `Close the menu` is an `<a href="#main">` so that with JS off it clears `:target` and closes the
  drawer; `app.js` intercepts it. It is `display: none` at ≥992px.

### 2.2 Items and states

| Part | Spec | Tag |
|---|---|---|
| Group title | 12px/500, line 18px, padding 12px 20px, row 42px, colour `--nav-group`, sentence case (no capitals transform) | [M] |
| First group title top | 10px below the brand row (y=80 at 1440) | [M] |
| Item (link or summary) | 14.4px/500, line 21.6px, padding 0 24px, **min-height 44px**, flex row, gap 10px, colour `--nav-text` | [M] size, weight, padding, idle colour `#545A6D`; [D] 44px (reference row 41.4px) |
| Item icon | 16 × 16px Feather, `currentColor`, stroke 2 | [M] |
| Child item | 13.6px/500, line 20.4px, padding-left **52.8px**, padding-right 24px, **min-height 44px**, colour `--nav-child` | [M] size, weight, indent; [D] 44px (reference row about 33px) |
| Hover | text and icon become `--nav-hover-text`; no background | [S] |
| Current page (`aria-current="page"`) | text and icon `--nav-active-text`, **plus a 3px bar** `--nav-active-bar` on the left edge (inset, full row height), plus `--nav-active-bg` (transparent in the light tone) | [M] colour role; [D] the bar (shape cue so current is not colour-only, and the brief's "active-nav indicator") |
| Parent containing the current page | parent label in `--nav-active-text`, no bar (the bar is on the child) | [S] |
| Chevron | Feather `chevron-right`, 16px, right-aligned in the row (right padding 24px), rotates **90°** when `[open]`, 200ms | [S] (the reference shows a right chevron at x≈221) |
| `summary` marker | hidden (`list-style: none` and `::-webkit-details-marker { display: none }`); the chevron replaces it | [D] |
| Focus | 2px `--nav-focus` outline, offset -2px (inset, so it is not clipped by the sidebar's scroll box) | [D] |

### 2.3 The three sizes (`data-nav-size`)

| | standard | compact | icons |
|---|---|---|---|
| Width | 250px [M] | 160px [M] | 70px [M] |
| Brand row | crest-chip 32px tall + wordmark (2 lines, balanced) | crest-chip 32px + wordmark hidden visually (`.offscreen`) | crest-chip 32px only, centred; wordmark `.offscreen` |
| Group titles | left, as §2.2 | centred [S] | `.offscreen` (still label their lists) [M: 0×0 on the reference] |
| Item layout | icon left, label right | icon **above** label, both centred; row **61px** tall [M]; icon 16px | icon only, centred; row **52px** tall [M]; icon **18px** [M]; label `.offscreen` until hover/focus |
| Chevron | right, rotating | below the label, 12px, rotating [D: reference hides it; kept as the only cue that `Requests` opens] | hidden |
| Children | in flow, indented 52.8px | in flow, centred, 13.6px, no indent [I] | **flyout** [M]: when `Requests` is `[open]` (or hovered / focused within), its `.sidenav__children` sits directly **under the label chip** (left: 70px, top: 51px from the item's top), **190px** wide, `--c-surface` background, `--shadow-pop`, padding 5px 0, no radius; child links 14px/**400** `--c-text`, padding 0 20px, **min-height 44px** [D; reference rows ≈36px] |
| Icons-size label on hover **and** `:focus-visible` | — | — | [M] the hovered row widens to **260px** (70 + 190): the label shows to the right of the icon, 14.4px/500, row 52px, padding 15px 20px, background `--nav-bg`, text `--nav-hover-text`, no shadow. Use `:hover` and `:focus-visible` on the link, **and** `:focus-within` on the item. |
| Help card | shown | hidden [M: 0×0 at small] | hidden |
| Top-bar toggle | at the top bar's left edge | same | same |

`Raise a request` stays reachable in every size through the `Requests` parent (and in the dashboard's
`Needs doing today` card).

### 2.4 Help card

- `margin: 48px 24px 24px` [M top/sides], radius 4px [M], padding 20px [M], background `--nav-card-bg`,
  text centred. No illustration (criterion 3).
- Title `Something not working?` as `<p class="helpcard__title" id="help-title">`, 15.4px/500
  `--nav-card-title` (not a heading, same reason as the group titles).
- Body `Tell us and we'll sort it out.` 14px/400 `--nav-card-text`, margin 8px 0 16px.
- Button `Raise a request` → `request-form.html`, full width, 44px, `--nav-card-btn-bg` /
  `--nav-card-btn-text`.

---

## 3. Top bar

Order, left to right (criterion 12): **menu toggle**, **search form**, (flex spacer), **colour-mode
button**, **notifications**, **settings button**, **user menu**. With JS off, the toggle, the
colour-mode button and the settings button carry `hidden`, and the phone-only `Menu` link is shown.

| Part | Spec | Tag |
|---|---|---|
| Menu toggle | `<button class="icon-button" data-nav-toggle aria-controls="nav" aria-expanded="true" hidden>` + `.offscreen` name. Feather `menu` 20px. **Desktop**: collapses the sidebar to `icons` **for the current page only** and expands it back to the size chosen in the settings panel (or to `standard` if the chosen size is `icons`). It **does not write** `tmd-layout`: only the settings panel saves `navSize`, so the stored object keeps exactly its four keys (criterion 4) and a reload always shows the chosen size. The settings radios show the chosen, saved size. `aria-expanded="false"` and name `Show the menu` when collapsed, else `true` / `Hide the menu`. **Phone**: opens the drawer; name `Show the menu`, `aria-expanded="false"` until open. | [M] 52×70; [D] behaviour |
| `Menu` link (no JS, phone only) | `<a class="icon-button" href="#nav" data-nav-link>` with the menu icon + visible word `Menu` 14px/500, 44px tall. `app.js` sets `hidden` on it. Hidden at ≥992px in CSS. | [D] |
| Search form | `<form class="topsearch" role="search" method="get" action="requests.html">`, label `Search requests` (`.offscreen`), input `name="q"` `type="search"`, placeholder `Reference or words, e.g. REQ-2048`, button `Search` (icon + `.offscreen` word). | contract |
| Search field | **304px** wide (`--search-w`) [D: at 240px the contract placeholder `Reference or words, e.g. REQ-2048` is clipped, which criterion 26 forbids; reference 219–221px], **44px** tall [D, ref 40], radius 4px [M], background `--c-surface-2` [M `#F8F9FA`], **1px border `--c-control`** [D, ref has no border in light], padding 0 52px 0 16px [M ≈17/50], 14px text [M] | |
| Search button | inside the field on the right, **44 × 44px** [D, ref 36 × 34], `--c-primary` fill, white icon 16px, radius 0 4px 4px 0, `--shadow-primary` [M shadow shape] | |
| Search gap | 20px after the toggle [M] | |
| Right-hand icon buttons | 52 × 70px each, icon 20px `--c-text` | [M] box, icon colour `#313533` and the toggle glyph box (20 × 16px); [S] 20px for the right-hand icons |
| Notifications trigger | `<details class="pop" data-pop>` → `<summary class="icon-button">` bell 20px + `.offscreen` `Notifications, 3 new` + count `3` (`aria-hidden="true"`) | contract |
| Count | circle-ish pill, min-width 18px, height 16px, radius 999px, 10.5px/600, `--c-count-bg` / `--c-count-text`, positioned top 12px, right 10px of the button | [M] 10.5px, 16px tall, y=12; [D] weight 600 (700 is not loaded) and colour (see §13 row 20) |
| User menu trigger | `<details class="pop" data-pop>` → `<summary class="whoami">`: avatar 36px, then `Nimali Perera` (14px/500 `--c-heading`) over `ICT Technician` (12px/400 `--c-muted`), then `chevron-down` 16px. Height 70px, padding 0 16px, background `--c-surface-2`, 1px left and right border `--c-border` | [M] avatar 36px, [S] shaded block with side borders, [I] role line (the reference shows only a name) |
| Avatar | 36px circle, `--c-primary-soft` bg, `--c-primary-text` initials `NP` 14px/600 | [M] size; [D] initials, no photo (criterion 3) |
| Phone (<992px) | brand box 73 × 70 with the 32px crest-chip **centred** (about 20px each side), background `--nav-bg` with a 1px right border `--nav-border` (so it follows the chosen sidebar tone, like the sidebar's own brand row) [M pass 3: `#FBFAFF` / `#2C302E`, right border `#E9E9EF` / `#383D3B`]; it holds the crest-chip, links to `dashboard.html`, `.offscreen` `Home`. [D: the reference pads the box 0 24px, which leaves only 25px for content and cannot fit the 32px crest-chip (002/23 requires at least 28px). We keep the measured box size and centre the crest instead of keeping the measured padding.] Then the toggle, then right-hand group. Search collapses to a `<details class="pop">` whose summary is the search icon (`.offscreen` `Search requests`) and whose panel holds the same form, full width under the top bar. Buttons 44 × 70. User summary shows the avatar only (60px wide block); name and role move into the dropdown's head. Colour mode stays; settings button hidden below 600px (still in the user menu). | [M] 73px brand box, [S] search collapses to an icon on the reference |
| Below 992px | user name and role hidden from the summary (avatar only), shown in the user dropdown head. Same breakpoint as the drawer, so the whole top bar switches to its phone layout at once | [D] |

---

## 4. Dropdowns (notifications and user menu)

Both are `<details class="pop" data-pop>`; they open with JS off. `app.js` adds: `Escape` closes and
returns focus to the summary; a click outside closes; opening one closes the other.

| Part | Spec | Tag |
|---|---|---|
| Panel | `position: absolute; top: 100%; right: 0`; notifications **320px** wide, padding 0; user menu **min-width 160px** (`width: max-content`), padding **4px**; `--c-surface`; 1px `--c-border`; radius 4px; shadow `--shadow-pop` | [M] both widths, paddings, border, radius, shadow; the panel's top edge is the top bar's bottom (y=70) |
| Panel on phone | `position: fixed; left: 12px; right: 12px; top: 71px; width: auto` | [D] |
| Head | padding 16px; `Notifications` **14px/500**, line 16.8px, `--c-heading` (a `<p>`, id used by the list's `aria-labelledby`) | [M] |
| Notification item | a link, `display: grid; grid-template-columns: 32px 1fr; gap: 16px`; padding 12px 16px; min-height 44px; **no divider between items**. Icon disc 32px in a status tint (below). Title 14px/500 `--c-heading`; body **13px/400** `--c-muted`, line 19.5px; time **13px/400** `--c-muted`, line 19.5px, with a 12px `clock` icon | [M] title, body and time sizes, weights and colour role, and the 16px gap (text starts 65px in); [S] 32px disc, no dividers |
| New vs read | the three new items: title 14px/**600** + a `New` tag (`.tag--brand`, see §7.4) after the title. The read item: weight 500, no tag, no time line | [D] so "new" is a word, not a tint; **needs planner confirmation** (§16) |
| Item hover/focus | background `--c-surface-2` | [I] |
| Icon per item | REQ-2048 `alert-triangle` on `--c-bad-soft` / `--c-bad-text`; REQ-2047 `user-plus` on `--c-note-*`; REQ-2046 `clock` on `--c-warn-*`; IT-0142 `monitor` on `--c-brand-*` | [D] |
| Foot | border-top 1px; one link `See all requests` + `arrow-right` 14px, centred, 44px tall, 14px/400 `--c-primary-text` | [S] |
| User menu head | shown only below 992px: avatar 36px + name + role, padding 12px | [D] |
| User menu items | `Design kit` (icon `grid`) → `ui-kit.html`; `Layout settings` (icon `sliders`, a `<button data-settings-open hidden>`); divider; `Sign out` (icon `log-out`) → `login.html`. Each **min-height 44px**, padding 0 16px, 14px/400 `--c-text`, icon 16px `--c-muted`, gap 8px | [M] 14px/400, 16px side padding; [D] 44px (reference 35.2px) |

---

## 5. Title row and breadcrumb

- `.titlebar`: `display: flex; justify-content: space-between; align-items: center; padding-bottom: 24px` [M].
- `<h1 class="page-heading">` 18px/500, line 21.6px, `--c-heading`, margin 0 [M].
- `<nav class="crumbs" aria-label="Breadcrumb"><ol>…</ol></nav>` 14px/400 [M].
  - Links `--c-text` [M], no underline, underline on hover and focus.
  - Separator: Feather `chevron-right` 14px `--c-muted`, 8px each side, drawn as an inline SVG
    `aria-hidden="true"` between items (or as a CSS `::before` mask; not text) [M: a right-chevron
    glyph at 75% text colour; each item after the first has 8px left padding].
  - Current item: `<li><span aria-current="page">…</span></li>`, colour `--c-muted` [M: 75% text
    colour, which blends to about `#646766`, 5.65:1; our `--c-muted` `#636779` is 5.61:1, the same step].
  - `dashboard.html` has a single-item trail `Home` (current).
- **Below 768px** the row stacks: h1, then the breadcrumb 8px below, both left-aligned [M: h1 y=94,
  breadcrumb y=124 at 400].

---

## 6. Layout settings panel

`<dialog class="sheet" data-settings aria-labelledby="sheet-title">`, opened with `showModal()` by any
`[data-settings-open]` button (top bar gear, user menu item). Both openers are `hidden` without JS.

| Part | Spec | Tag |
|---|---|---|
| Position and size | fixed to the right edge, full height, **300px** wide, `margin: 0 0 0 auto`, `max-height: 100vh; height: 100vh` | [M] 300 × 900 at x=1440 (off-screen when closed) |
| Surface | `--c-sheet` (light `#FCFAFD`, dark `#313533`), shadow `--shadow-sheet` | [M] colours and two-layer shadow |
| Backdrop | `::backdrop { background: var(--scrim) }` | [S] the page is dimmed grey behind the panel; exact colour [I] |
| Enter | slides from `translateX(100%)` to 0 in 250ms `--ease`; reduced motion: no slide | [I] |
| Head | **56px** tall, padding **0 16px**, bottom border `--c-border`; `<h2 id="sheet-title">Layout settings</h2>` at **17.5px/500**, line 21px, `--c-heading` (its own h2 role, §8); `Close` button right: `x` icon 16px + visible word `Close`, 44px tall, `.button--quiet` | [M] 56px head with 16px padding (pass 3), title size, weight, line and colour in light and dark, x=16 and y=18 in the panel; [S] the rule under it; [D] the close control is a 44px button with the word `Close` (reference: 24px dark disc with an x) |
| Body | padding 24px; first a line `Your choices are saved in this browser only.` 14px `--c-muted`, margin-bottom 24px | [M] 24px side padding; contract words |
| Fieldsets | four, in order: `Colour mode` (`Light`, `Dark`), `Page width` (`Full width`, `Boxed`), `Sidebar size` (`Standard`, `Compact`, `Icons only`), `Sidebar colour` (`Light`, `Dark`, `Purple`). `border: 0; padding: 0; margin: 0 0 32px`. `<legend>` **14px/500**, line 16.8px, `--c-heading`, margin-bottom 12px | [M] legend style; [S] ≈86px from one group title to the next; contract words |
| Option layout | two-option groups (`Colour mode`, `Page width`) put their two rows **side by side** (two equal columns, gap 8px); three-option groups stack their rows | [S] |
| Radio row (`.choice`) | `<label>` wrapping a native radio: flex, gap 8px, **min-height 44px**, padding 0 12px, radius 4px, 1px `--c-border`; radio 18px with `accent-color: var(--c-primary-text)`; text **14px/500** `--c-text` [M pass 3: `#ADB5BD` in dark]. `:has(:checked)` row: border `--c-primary-text`, `--c-primary-soft` bg. Stacked rows have an 8px gap | [M] label 14px/500, radio 14px filled with the primary when checked; [D] 44px bordered rows and an 18px radio (reference: bare 14px radio + label, ≈21px rows) |
| Sidebar colour rows | add a 16 × 16px swatch before the word, radius 2px, 1px `--c-control` border, filled with that tone's `--nav-bg` | [D] |
| Radio names | `theme` (`light`/`dark`), `width` (`full`/`boxed`), `nav-size` (`standard`/`compact`/`icons`), `nav-tone` (`light`/`dark`/`purple`); each input has `data-setting` | contract |
| Foot | sticky at the bottom, padding 16px 24px, top border; `Reset to default` as `.button--secondary`, full width | [D] |
| Behaviour | Changing a radio applies at once (sets the `<html>` attribute and writes `tmd-layout`). Opening the panel syncs every radio to the current `<html>` state (with no saved theme, `Colour mode` shows the mode the system is giving). `Escape` or `Close` closes and returns focus to the opener; when the opener was the user-menu item, focus returns to the user menu's `<summary>` (its `<details>` closes as the panel opens). `Reset to default` removes `tmd-layout`, removes `data-theme`, sets `full` / `standard` / `light`, re-syncs radios, keeps the panel open and focus on the reset button. | contract / [D] |

---

## 7. Components

Our class vocabulary (the builder uses these names and no others for these roles; none appears in
the reference's markup):

`skip`, `offscreen`, `shell`, `sidenav` (+ `__brand`, `__wordmark`, `__close`, `__group-title`,
`__list`, `__link`, `__icon`, `__label`, `__parent`, `__chevron`, `__children`), `helpcard`,
`topbar` (+ `__start`, `__end`), `icon-button`, `topsearch`, `pop` (+ `__panel`, `__head`, `__item`,
`__foot`), `count`, `whoami`, `initials`, `titlebar`, `page-heading`, `crumbs`, `sheet`
(+ `__head`, `__body`, `__foot`), `choice`, `scrim`, `page-foot`, `box` (+ `__head`, `__title`,
`__body`, `__foot`), `cards` (+ `--four`, `--two-one`, `--one-two`), `stat` (+ `__num`, `__words`,
`__icon`, `__sub`), `button` (+ `--primary`, `--secondary`, `--quiet`, `--danger`, `--icon`),
`tag` (+ `--ok`, `--warn`, `--bad`, `--note`, `--plain`, `--brand`), `field` (+ `__label`, `__help`,
`__error`), `input`, `options`, `notice` (+ `--bad`, `--ok`, `--warn`, `--note`), `flash`, `empty`,
`datagrid`, `datagrid-wrap`, `facts`, `history`, `pager`, `chart`, `signin`, `signin__form`,
`signin__brand`.

### 7.1 Box (card)

| Part | Spec | Tag |
|---|---|---|
| Surface | `--c-surface`, 1px `--c-border`, radius **4px**, no shadow, margin-bottom 24px | [M] (content card: white, 1px `#E9E9EF`, radius 4, `box-shadow: none`) |
| Head | `.box__head`: flex, space-between, align centre; padding **20px**; bottom border 1px `--c-border`; background `--c-surface` (so it matches the dark ladder) | [M] padding 20, border, height 62 |
| Title | `<h2 class="box__title">` 15.4px/500, line 18.48px, `--c-heading`, margin 0 | [M] |
| Body | padding **20px** | [M] |
| Foot | optional, padding 12px 20px, top border, used for `See all requests` links | [I] |
| Stat box | no head; body padding 20px; min-height 133px | [S] |

### 7.2 Stat tile

- `.stat` inside a box body: grid `1fr auto`.
- `.stat__num` 21px/500, line 25.2px, `--c-heading` [M]; **20.4px** below 992px [M].
- `.stat__words` 14px/400 `--c-muted`, on the line **below** the number [M size/colour role].
- In the DOM the number and the words are one `<p>` (`<span class="stat__num">6</span> <span
  class="stat__words">requests open</span>`) so the text reads exactly `6 requests open`.
  **Deviation**: the reference prints the label **above** the value; we print the value first so the
  contract phrase is read in its own order (row 32).
- `.stat__icon`: 48px disc, `--c-brand-soft` fill, Feather icon 24px `--c-primary-text`, top-right.
  Replaces the reference's sparkline (sparklines are out of scope; row 32).
- `.stat__sub` (first tile only): margin-top 16px, a `.tag--bad` with `alert-triangle` reading
  `2 are urgent`.

### 7.3 Buttons

| Variant | Spec | Tag |
|---|---|---|
| All | inline-flex, gap 8px, **min-height 44px**, padding 0 12px, radius 4px, **14px/400**, line 21px, border 1px transparent; icon 16px | [M] radius 4, 14px/400, 12px side padding; [D] 44px (reference 38px) |
| Primary | `--c-primary` bg, 1px `--c-primary` border, `--c-on-primary` text, `--shadow-primary`; hover `--c-primary-hover` | [M] fill, border, `0 2px 6px` shadow at 50% |
| Secondary (the reference's "soft" button) | `--c-primary-soft` bg, `--c-primary-text` text, no border, no shadow; hover: `--c-primary` bg, `--c-on-primary` text | [M] primary at 10% with primary text; [S] hover |
| Quiet (the reference's "link" button) | transparent, `--c-primary-text` text; hover underline | [M] |
| Danger | `--c-bad-solid` bg, `--c-on-primary` text | [I] |
| Icon-only | 44 × 44px, `.offscreen` label | [D] |
| Disabled | `disabled` attribute, opacity .6, `cursor: not-allowed` (exempt from contrast, WCAG 1.4.3) | [I] |
| Busy | `aria-busy="true"`, the icon swaps to `loader` spinning 1s linear (static under reduced motion), label unchanged | [D] |
| Focus (all) | 2px `--c-focus` outline, offset 2px | [D] |

### 7.4 Tags (soft status badges)

- `.tag`: inline-flex, align centre, gap 4px, padding 3px 5px, radius 4px, **10.5px/600**, line
  height 1, icon 12px, `white-space: nowrap`. Background: the family colour at 18% over the surface
  (the `--c-*-soft` tokens); text: a strong shade of the same family (the `--c-*-text` tokens).
  [M pass 3: 10.5px/700 in body text, line 1, padding 0.25em top and bottom, tint at 18% alpha;
  S: small radius on square badges; I: the side padding.]
- **Deviations**: the reference prints the saturated hue on its own 18% tint, which is about 2.5:1.
  We keep the tint and darken (light mode) or lighten (dark mode) the text until it passes 4.5:1.
  Weight is 600 because 700 is not loaded (D3). The icon is added so status is an icon plus a word
  (row 21).

| Word | Variant | Icon (Feather) |
|---|---|---|
| Request `New` | `--note` | `plus-circle` |
| `In progress` | `--brand` | `loader` (static) |
| `Waiting on someone` | `--warn` | `clock` |
| `Fixed` | `--ok` | `check-circle` |
| `Closed` | `--plain` | `archive` |
| Device `In store` | `--plain` | `package` |
| `Issued` | `--brand` | `user-check` |
| `In repair` | `--warn` | `tool` |
| `Out of service` (status and condition) | `--bad` | `x-octagon` |
| Condition `Good` | `--ok` | `check-circle` |
| `Needs repair` | `--warn` | `alert-circle` |
| Urgency `Urgent` | `--bad` | `alert-triangle` |
| `Normal` | `--plain` | `minus-circle` |
| `Can wait` | `--plain` | `coffee` |
| Notification `New` (§4, pending confirmation) | `--brand` | none (a word tag) |

### 7.5 Form fields

| Part | Spec | Tag |
|---|---|---|
| Label | `<label class="field__label">` 14px/500 `--c-heading`, margin-bottom 8px | [M] 14px/500; [I] margin |
| Help | `<p class="field__help" id="…-help">` **13px/400**, line 19.5px, `--c-muted`, between label and control, margin-bottom 8px | [M] 13px at 75% text colour; [D] placed above the control (form-design rule) |
| Input / select | `.input`: **44px** tall, full width, padding 0 12px (select: 0 36px 0 12px), 14px `--c-text`, `--c-field` bg, 1px `--c-control` border, radius 4px | [M] 14px, `#F8F9FA` fill, radius 4, 12px / 36px padding; [D] 44px (reference 38px) and a 3:1 border (reference `#E9E9EF`, 1.2:1) |
| Textarea | the input's measured values (14px, `--c-field`, radius 4px, 12px side padding), min-height 110px, padding 10px 12px, `resize: vertical` | [I, our decision]: the reference's form-elements page has no textarea (checked in pass 3), so there is nothing to measure |
| Select arrow | native `appearance: auto` (keeps the platform arrow; no image asset) | [D] |
| File input | native; `::file-selector-button` styled as `.button--secondary` (44px) | [D] |
| Read-only | `--c-surface-2` bg, dashed 1px `--c-control` border | [D] |
| Focus | border `--c-focus` + 2px outline `--c-focus`, offset 1px | [D] |
| Error | `aria-invalid="true"`; border 2px `--c-bad-solid`; `.field__error` under the control: `alert-circle` 14px + text, **12.25px/400**, line 18.4px, `--c-bad-text`, margin-top 6px; `aria-describedby` lists help id then error id | [M] 12.25px/400 in the danger colour; [D] colour `#B42318` (reference `#FD625E` is 2.96:1), the icon, the 2px border |
| Radios as options (`How urgent is it?`) | `<fieldset class="options">` + `<legend>` styled as a label; three `.choice` rows side by side at ≥768px (equal thirds), stacked below; each row: native radio 18px, word 14px/500, its help line 13px `--c-muted`; `:has(:checked)` border `--c-primary-text` + `--c-primary-soft` bg | [D] |
| Checkbox | native, 18px, `accent-color: var(--c-primary-text)`, wrapped in a 44px-tall label | [M] reference 14px, radius 3.5px; [D] 18px |
| Search field in cards | as `.input` with a leading `search` icon 16px at 12px from the left (padding-left 36px) | [I] |

### 7.6 Data grid (tables)

| Part | Spec | Tag |
|---|---|---|
| Table | `.datagrid` width 100%, `border-collapse: collapse`, 14px/400 | [M] |
| Cell | padding **12px**, bottom border 1px `--c-border`, vertical-align middle | [M] |
| Head cell | `<th scope="col">` 14px/**600** `--c-heading`, `--c-surface` bg (no fill), bottom border 1px `--c-border`, padding 12px | [M] 14px, white, bottom rule, 12px; [D] weight 600 (reference 700, which is not loaded, D3) |
| Row hover | `--c-surface-2` | [I] |
| Caption | `<caption class="offscreen">` naming the table | [D] |
| Wrapper | `.datagrid-wrap { overflow-x: auto }` at ≥768px (for 1024px with the standard sidebar) | [D] |
| **Below 768px** | each row becomes a card: `tr` display block, 1px `--c-border`, radius 4px, padding 12px, margin-bottom 12px; `td` display grid `8.5em 1fr`, padding 6px 0, no border; each `td` starts with `<span class="datagrid__label" aria-hidden="true">Status</span>` (shown only here); `thead` is visually hidden. Add explicit `role="table"/"rowgroup"/"row"/"columnheader"/"cell"` to keep table semantics when `display` changes. | [D] (reference scrolls the table sideways; we stack so no text is clipped at 400px, criterion 26) |

### 7.7 Notices, flash, empty state

- `.notice`: flex, gap 12px, padding 12px 16px, radius 4px, 1px border in the family's text colour
  at 30% (a token per family, `--c-*-line`), soft background, icon 20px in the text colour, title
  14px/600, body 14px/400. Families `--bad` (`alert-octagon`), `--ok` (`check-circle`), `--warn`
  (`alert-triangle`), `--note` (`info`).
- `.flash` (toast): `position: fixed; right: 24px; bottom: 24px; width: 360px` (phone: left and right
  12px, width auto); `--c-surface`, 1px `--c-border`, radius 4px, `--shadow-pop`, padding 12px 16px;
  `check-circle` 20px `--c-ok-text`, then the message 14px, then `Undo` (`.button--quiet`, `hidden`
  without JS) and `Close` (icon-only `x`, 44px). `role="status"`. It does not time out.
- `.empty`: centred, padding 48px 20px; 64px disc `--c-surface-2` with `search` 28px `--c-muted`;
  heading `<h2>` (h2 role, 15.4px/500); body 14px `--c-muted` max 40ch; button.

### 7.8 Facts list, history, pager

- `.facts`: `<dl>` as a grid `minmax(8em, 12em) 1fr`, row gap 12px; `<dt>` 14px/400 `--c-muted`,
  `<dd>` 14px/500 `--c-heading`. Two such columns side by side at ≥1200px.
- `.history`: `<ol>`; each item has a 12px dot (`--c-primary-text` ring 2px on `--c-surface`) on a
  2px `--c-border` vertical line at left 6px; content padding-left 28px, padding-bottom 20px. Line 1:
  time 12px `--c-muted` (with `<time datetime>`); line 2: who 14px/500 `--c-heading`; line 3: what
  14px/400.
- `.pager` (ui-kit only): row of 44 × 44px links, radius 4px, 1px `--c-border`; current `--c-primary`
  fill + `aria-current="page"`; previous/next with `chevron-left`/`chevron-right` + `.offscreen` words.

### 7.9 Icons

Feather (MIT), inlined once per page as `<svg class="sprite" aria-hidden="true" …><symbol id="i-…"
viewBox="0 0 24 24">…</symbol></svg>` directly after the skip link, byte-identical on all six pages.
Uses: `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-home"/></svg>`. Every
`fill`/`stroke` is `currentColor`; `fill="none"`, `stroke-width="2"`, round caps and joins, as
Feather draws them. Sizes: 12, 14, 16, 18, 20, 24px (`--icon-*` tokens).

Symbols needed (ids `i-<feather name>`): `menu`, `x`, `search`, `moon`, `sun`, `bell`, `settings`,
`sliders`, `chevron-down`, `chevron-right`, `chevron-left`, `home`, `inbox` (Requests), `list`
(All requests), `plus-circle` (Raise a request, `New`), `monitor` (Devices), `grid` (Design kit),
`log-out`, `user-plus`, `user-check`, `clock`, `alert-triangle`, `alert-circle`, `alert-octagon`,
`x-octagon`, `check-circle`, `archive`, `package`, `tool`, `minus-circle`, `coffee`, `loader`, `info`,
`arrow-right`, `upload`, `calendar`, `trash-2`.

---

## 8. Type scale

Font: **IBM Plex Sans** 300/400/500/600 from Google Fonts with `display=swap` (D3). `html` stays at
16px; `body` sets 14px. Sizes are px (they are measured values; rems would round).

| Role | Element(s) | Size | Weight | Line height | 400px | Tag |
|---|---|---|---|---|---|---|
| Body copy | `body`, `p`, `li`, `dd` | **14px** | 400 | 21px | 14px | [M] |
| Table cell | `td` | **14px** | 400 | 21px | 14px | [M] |
| Table head | `th` | 14px | 600 | 21px | 14px | [M] size; [D] weight (reference 700) |
| Form-field text | `input`, `select`, `textarea` | **14px** | 400 | 21px | 14px | [M] input and select; textarea: none on the reference, so it follows the input |
| Form label | `label` | 14px | 500 | 21px | 14px | [M] |
| Settings legend | `.sheet legend` | 14px | 500 | 16.8px | 14px | [M] |
| Settings option | `.choice` text | 14px | 500 | 21px | 14px | [M] |
| Help text | `.field__help`, urgency option help | **13px** | 400 | 19.5px | 13px | [M] |
| Error text | `.field__error` | **12.25px** | 400 | 18.4px | 12.25px | [M] |
| Sidebar item | `.sidenav__link` | **14.4px** | 500 | 21.6px | 14.4px | [M] |
| Sidebar child | `.sidenav__children a` | **13.6px** | 500 | 20.4px | 13.6px | [M] |
| Sidebar group title | `.sidenav__group-title` | **12px** | 500 | 18px | 12px | [M] |
| Wordmark | `.sidenav__wordmark` | 14.4px | 600 | 1.2 | 14.4px | [D] |
| Breadcrumb | `.crumbs` | **14px** | 400 | 21px | 14px | [M] |
| Page title | `h1` on the five app pages | **18px** | 500 | 21.6px | 18px | [M] |
| Sign-in title | `h1` on `login.html` | **17.5px** | 500 | 21px | 17.5px | [M] |
| Settings panel title | `h2#sheet-title` | **17.5px** | 500 | 21px | 17.5px | [M] |
| Card title and every other `h2` (empty state) | `h2` | **15.4px** | 500 | 18.48px | 15.4px | [M] |
| Sub-heading | `h3` (sections inside a box, ui-kit subsections) | **14px** | 600 | 21px | 14px | [I] (the reference's smallest heading is body-sized) |
| `h4`–`h6` | not used | — | — | — | — | — |
| Stat number | `.stat__num` | **21px** | 500 | 25.2px | **20.4px** | [M] both |
| Stat words | `.stat__words` | 14px | 400 | 21px | 14px | [M] |
| Top-bar name / role | `.whoami` | 14px / 12px | 500 / 400 | 18px | hidden <992 | [I] |
| Dropdown head | `.pop__head` | 14px | 500 | 16.8px | 14px | [M] |
| Notification title / body / time | `.pop__item` | 14 / 13 / 13px | 500 (600 new) / 400 / 400 | 16.8 / 19.5 / 19.5px | same | [M] (pass 3) |
| User-menu item | `.pop__item` (user menu) | 14px | 400 | 21px | 14px | [M] |
| Button | `.button` | 14px | 400 | 21px | 14px | [M] |
| Tag | `.tag` | **10.5px** | 600 | 1 (10.5px) | 10.5px | [M] size and line (pass 3); [D] weight (reference 700, not loaded) |
| Count on the bell | `.count` | **10.5px** | 600 | 10.5px | 10.5px | [M] size; [D] weight |
| Chart labels | SVG `<text>` | 12px | 400 | — | 12px | [I] |
| Footer | `.page-foot` | 14px | 400 | 21px | 14px | [M] |
| Sign-in motto | `.signin__brand` motto | 21px | **300** | 1.4 | 17.5px | [D] (the one use of 300) |

Smallest text on the reference: **10.2px** [M]. Smallest text in the folder: 10.5px (bell count and status tags).

---

## 9. Palette and tokens

All raw colour values live only in the token blocks (criterion 29). **Structure** (so no hex is
written twice):

1. `:root` holds the light semantic tokens, **and** the dark primitives as `--dk-*` (the only place
   the dark hexes are written), **and** the nav-tone primitives `--tone-dark-*` and `--tone-purple-*`.
2. The dark block maps light semantic tokens to `var(--dk-*)`, and is applied by **two** selectors
   that share one rule body: `:root[data-theme="dark"]` and, inside
   `@media (prefers-color-scheme: dark)`, `:root:not([data-theme="light"])`. (If the builder cannot
   share one body across the media query, repeat the **mapping** block, never the hex values.)
3. The nav-tone blocks set only `--nav-*` from the tone primitives: `[data-nav-tone="dark"]`,
   `[data-nav-tone="purple"]`; the light tone maps `--nav-*` to the page mode's own values (so in dark
   mode the "Light" sidebar is dark, as on the reference, where the sidebar follows the mode).

### 9.1 How the colours were derived

- **Neutrals** are the reference's measured neutrals [M] (`#313533` text, `#E9E9EF` border,
  `#F8F9FA` field, `#2C302E`/`#313533`/`#383D3B`/`#363A38` dark ladder, `#ADB5BD`/`#CED4DA` dark text),
  except where they fail AA; those are darkened or lightened and marked [D].
- **Primary** is the crest purple `#722A82` from `logo.png`, replacing the reference's primary
  everywhere it appears (button fill, active nav, search button, links, chart, soft tints).
- **Primary tints**: `#F1EAF3` is `#722A82` at 10% over white (the reference's help card and soft
  badges use its primary at 10%); `#3E2F43` is `#722A82` at 25% over `#2C302E`; `#5C1F6A` and
  `#8A3D9C` are the crest darkened and lightened along the same hue; `#CFA3DA` is the crest tinted
  toward white until it reaches 5:1+ on every dark surface.
- **Status families** keep the reference's hue families (green, amber, red, blue) with their tints,
  but take new text shades that pass 4.5:1 [D].

### 9.2 Light mode (`:root`)

| Token | Hex | Use |
|---|---|---|
| `--c-page` | `#FFFFFF` [M] | page background |
| `--c-surface` | `#FFFFFF` [M] | cards, top bar, footer, dropdowns |
| `--c-surface-2` | `#F8F9FA` [M] | search field, table head, user block, hovers |
| `--c-field` | `#F8F9FA` [M] | form controls (same value as `--c-surface-2`, own token) |
| `--c-sheet` | `#FCFAFD` [D from M `#FBFAFF`] | settings panel |
| `--c-border` | `#E9E9EF` [M] | card, top bar, footer, table rules (decorative) |
| `--c-control` | `#868A9B` [D] | control borders, zero-bar stub |
| `--c-text` | `#313533` [M] | body text, icons |
| `--c-heading` | `#313533` [M] | headings, values |
| `--c-muted` | `#636779` [D from M `#74788D` / 75% text] | help, time, footer, stat words |
| `--c-primary` | `#722A82` | primary fill, search button |
| `--c-primary-hover` | `#5C1F6A` | primary hover |
| `--c-primary-text` | `#722A82` | links, active nav, quiet buttons, chart bars |
| `--c-primary-soft` | `#F1EAF3` | selected option rows, avatar, brand tints |
| `--c-on-primary` | `#FFFFFF` | text on primary / danger fills |
| `--c-focus` | `#722A82` | focus rings |
| `--c-ok-text` / `--c-ok-soft` | `#17744F` / `#D9F2E8` | success (soft = the reference's green `#2AB57D` at 18% over white) |
| `--c-warn-text` / `--c-warn-soft` | `#8A5A00` / `#FFF4E0` | warning (soft = `#FFBF53` at 18%) |
| `--c-bad-text` / `--c-bad-soft` | `#B42318` / `#FFE3E2` | danger (soft = `#FD625E` at 18%) |
| `--c-bad-solid` | `#B42318` | danger button, error border, bell count bg |
| `--c-note-text` / `--c-note-soft` | `#1E5FA8` / `#DFEFFC` | information, request `New` (soft = `#4BA6EF` at 18%) |
| `--c-plain-text` / `--c-plain-soft` | `#545A6D` / `#EEEFF3` | neutral tags [I: the reference's grey soft badge was not captured] |
| `--c-brand-text` / `--c-brand-soft` | `#722A82` / `#E6D9E9` | brand tags, stat and notification icon discs (soft = the crest at 18%) |
| `--c-*-line` | the family's text colour at 30% alpha, e.g. `rgba(180, 35, 24, 0.3)` | notice borders (decorative) |
| `--c-count-bg` / `--c-count-text` | `#B42318` / `#FFFFFF` | bell count |
| `--c-boxed-outside` | `#ECEBF2` [I] | body behind a boxed page |
| `--c-chart-bar` / `--c-chart-zero` / `--c-chart-grid` / `--c-chart-label` | `#722A82` / `#868A9B` / `#E9E9EF` / `#636779` | chart |
| `--scrim` | `rgba(33, 26, 36, 0.4)` [S grey dim; I exact value] | drawer and dialog backdrop |
| `--shadow-pop` | `0 5px 20px -6px rgba(99, 103, 121, 0.14)` [M shape] | dropdowns, flyouts, toast |
| `--shadow-primary` | `0 2px 6px rgba(114, 42, 130, 0.5)` [M shape] | primary buttons |
| `--shadow-sheet` | `0 0 24px rgba(0, 0, 0, 0.06), 0 1px 0 rgba(0, 0, 0, 0.02)` [M] | settings panel |
| `--shadow-boxed` | `0 5px 20px -6px rgba(99, 103, 121, 0.14)` [M shape, the same as the dropdowns] | boxed shell |

### 9.3 Dark mode (`--dk-*` primitives, mapped onto the same names)

| Token | Hex | Tag |
|---|---|---|
| `--c-page` | `#313533` | [M] |
| `--c-surface` | `#2C302E` | [M] cards, top bar, sidebar, dropdowns |
| `--c-surface-2` | `#363A38` | [M] search field |
| `--c-field` | `#363A38` | [M] |
| `--c-sheet` | `#313533` | [M] |
| `--c-border` | `#383D3B` | [M] |
| `--c-control` | `#808782` | [D] (reference `#3B403D` is 1.1:1) |
| `--c-text` | `#ADB5BD` | [M] |
| `--c-heading` | `#CED4DA` | [M] |
| `--c-muted` | `#9CA3AD` | [D] (reference 75% text ≈ 4.35:1) |
| `--c-primary` | `#722A82` | fills keep the crest; white on it is 8.86:1 |
| `--c-primary-hover` | `#8A3D9C` | |
| `--c-primary-text` | `#CFA3DA` | crest tint for text, active nav, focus, chart |
| `--c-primary-soft` | `#3E2F43` | |
| `--c-focus` | `#CFA3DA` | |
| ok / warn / bad / note / plain / brand text on soft | `#6FD3A6`/`#22382F` · `#F2C46D`/`#3D3322` · `#F59A94`/`#432A2A` · `#8CBDF2`/`#22334A` · `#CED4DA`/`#3A3E3C` · `#CFA3DA`/`#3E2F43` | [D] |
| `--c-bad-solid`, `--c-count-bg` | `#B42318` (white 6.57:1) | [D] |
| `--c-boxed-outside` | `#262928` | [I] |
| chart bar / zero / grid / label | `#CFA3DA` / `#808782` / `#383D3B` / `#9CA3AD` | |

### 9.4 Sidebar tones (`--nav-*`)

Four sets, because the reference's "Dark" sidebar in **light** mode uses greyer item text than its
sidebar in **dark** mode (both measured). The light tone in dark mode maps to the fourth column's
values, which live in the `--dk-*` primitives; the dark and purple tones use `--tone-dark-*` and
`--tone-purple-*` in both modes.

| Token | Light tone, light mode | Light tone, dark mode | Dark tone (any mode) | Purple tone (any mode) |
|---|---|---|---|---|
| `--nav-bg` | `#FCFAFD` [D from M `#FBFAFF`] | `#2C302E` [M] | `#2C302E` [M] | `#722A82` [D, crest, in place of the reference's primary] |
| `--nav-border` | `#E9E9EF` [M] | `#383D3B` [M] | `#383D3B` | `#722A82` (none visible) |
| `--nav-brand` (wordmark) | `#313533` | `#E9ECEF` | `#E9ECEF` | `#FFFFFF` |
| `--nav-group` | `#545A6D` [M] | `#9CA3AD` [D from M `#858D98`] | `#9CA3AD` [D from M `#858D98`] | `#D5BFDA` [D from M white at 60%] |
| `--nav-text` | `#545A6D` [M] | `#E9ECEF` [D from M `#FFFFFF`] | `#99A4B1` [M] | `#D5BFDA` [D from M white at 60%] |
| `--nav-child` | `#545A6D` [M] | `#ADB5BD` [D from M `#858D98`] | `#99A4B1` [I, = items] | `#D5BFDA` [I, = items] |
| `--nav-hover-text` | `#722A82` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| `--nav-active-text` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-active-bg` | `transparent` | `#3E2F43` | `#3E2F43` | `#5C1F6A` |
| `--nav-active-bar` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-focus` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-card-bg` | `#F1EAF3` [M 10% primary] | `#313533` [M] | `#313533` | `#5C1F6A` |
| `--nav-card-title` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-card-text` | `#313533` | `#ADB5BD` | `#ADB5BD` | `#F1E6F4` |
| `--nav-card-btn-bg` / `-text` | `#722A82` / `#FFFFFF` | `#722A82` / `#FFFFFF` | `#722A82` / `#FFFFFF` | `#FFFFFF` / `#722A82` |
| `--nav-scroll` | `#C9CBD4` | `#4A504D` | `#4A504D` | `#9A5AA8` |

### 9.5 Contrast pairs (WCAG 2.x relative luminance; the verifier recomputes)

Text needs 4.5:1 (every text role here is under 24px), non-text 3:1.

**Rounding rule: ratios are truncated to two decimals, never rounded up**, so no figure overstates
a pass. The lowest figures are 4.53:1 for text (`--c-muted` on `#363A38`) and 3.13:1 for non-text
(`--c-control` on `#363A38`). The ratios below were recomputed by hand and are good to about ±0.01.
Where the builder's README table (computed exactly, then truncated) differs in the second
decimal, the README value governs; no pass or fail depends on that digit.

**Light mode**

| Pair | Ratio |
|---|---|
| `--c-text` `#313533` on `#FFFFFF` | 12.44 |
| `--c-text` on `--c-surface-2` `#F8F9FA` | 11.80 |
| `--c-text` on `--c-primary-soft` `#F1EAF3` | 10.55 |
| `--c-muted` `#636779` on `#FFFFFF` | 5.61 |
| `--c-muted` on `#F8F9FA` | 5.32 |
| `--c-muted` on `--c-sheet` / `--nav-bg` `#FCFAFD` | 5.40 |
| `--c-primary-text` `#722A82` on `#FFFFFF` | 8.86 |
| `#722A82` on `#F8F9FA` | 8.41 |
| `#722A82` on `#F1EAF3` | 7.52 |
| `#FFFFFF` on `--c-primary` `#722A82` | 8.86 |
| `#FFFFFF` on `--c-primary-hover` `#5C1F6A` | 11.29 |
| `#FFFFFF` on `--c-bad-solid` `#B42318` | 6.57 |
| ok `#17744F` on `#D9F2E8` | 4.88 |
| warn `#8A5A00` on `#FFF4E0` | 5.43 |
| bad `#B42318` on `#FFE3E2` | 5.42 |
| note `#1E5FA8` on `#DFEFFC` | 5.48 |
| notice body `--c-text` `#313533` on the lowest-contrast soft tint (`#FFE3E2`) | 10.27 |
| plain `#545A6D` on `#EEEFF3` | 5.97 |
| brand `#722A82` on `#E6D9E9` (tags, icon discs) | 6.52 |
| non-text: `--c-control` `#868A9B` on `#FFFFFF` / `#F8F9FA` / `#FCFAFD` | 3.43 / 3.25 / 3.30 |
| non-text: focus `#722A82` on `#FFFFFF` / `#FCFAFD` | 8.86 / 8.54 |
| non-text: chart bar `#722A82` on `#FFFFFF`; zero stub `#868A9B` on `#FFFFFF` | 8.86; 3.43 |

**Dark mode**

| Pair | Ratio |
|---|---|
| `--c-text` `#ADB5BD` on `--c-surface` `#2C302E` | 6.45 |
| `#ADB5BD` on `--c-page` `#313533` | 6.00 |
| `#ADB5BD` on `--c-surface-2` `#363A38` | 5.56 |
| `#ADB5BD` on `--c-primary-soft` `#3E2F43` | 5.98 |
| `--c-heading` `#CED4DA` on `#2C302E` | 8.96 |
| `--c-muted` `#9CA3AD` on `#2C302E` / `#313533` / `#363A38` | 5.26 / 4.89 / 4.53 |
| `--c-primary-text` `#CFA3DA` on `#2C302E` / `#313533` / `#363A38` / `#3E2F43` | 6.31 / 5.87 / 5.44 / 5.85 |
| `#FFFFFF` on `#722A82` / `#8A3D9C` / `#B42318` | 8.86 / 6.51 / 6.57 |
| ok `#6FD3A6` on `#22382F` | 6.89 |
| warn `#F2C46D` on `#3D3322` | 7.61 |
| bad `#F59A94` on `#432A2A` | 6.20 |
| note `#8CBDF2` on `#22334A` | 6.51 |
| plain `#CED4DA` on `#3A3E3C` | 7.27 |
| brand `#CFA3DA` on `#3E2F43` | 5.85 |
| non-text: `--c-control` `#808782` on `#363A38` / `#2C302E` / `#313533` | 3.13 / 3.64 / 3.38 |
| non-text: focus and chart bar `#CFA3DA` on `#2C302E` | 6.31 |
| non-text: zero stub `#808782` on `#2C302E` | 3.64 |

**Sidebar tones**

| Pair | Light tone, light mode | Light tone, dark mode | Dark tone | Purple tone |
|---|---|---|---|---|
| wordmark on `--nav-bg` | `#313533`/`#FCFAFD` 11.99 | `#E9ECEF`/`#2C302E` 11.28 | 11.28 | `#FFFFFF`/`#722A82` 8.86 |
| group title | `#545A6D` 6.61 | `#9CA3AD` 5.26 | `#9CA3AD` 5.26 | `#D5BFDA` 5.19 |
| item | `#545A6D` 6.61 | `#E9ECEF` 11.28 | `#99A4B1` 5.29 | `#D5BFDA` 5.19 |
| child | `#545A6D` 6.61 | `#ADB5BD` 6.45 | `#99A4B1` 5.29 | `#D5BFDA` 5.19 |
| hover | `#722A82` 8.54 | `#FFFFFF` 13.38 | `#FFFFFF` 13.38 | `#FFFFFF` 8.86 |
| active text on active bg | `#722A82`/`#FCFAFD` 8.54 | `#CFA3DA`/`#3E2F43` 5.85 | 5.85 | `#FFFFFF`/`#5C1F6A` 11.29 |
| active bar (non-text) | 8.54 | `#CFA3DA` on `#2C302E` 6.31 | 6.31 | `#FFFFFF` on `#5C1F6A` 11.29 |
| focus ring (non-text) | 8.54 | 6.31 | 6.31 | 8.86 |
| help card title / body | 7.52 / 10.55 | 5.87 / 6.00 | 5.87 / 6.00 | 11.29 / 9.34 |
| help card button text | `#FFFFFF`/`#722A82` 8.86 | 8.86 | 8.86 | `#722A82`/`#FFFFFF` 8.86 |
| icons-size children flyout: `--c-text` on `--c-surface` | 12.44 | 6.45 | as the page mode | as the page mode |

For the record, the reference's own values fail here. The dark-mode group title `#858D98` on
`#2C302E` is 3.99:1. White at 60% on the crest purple (the reference's brand-sidebar treatment,
blending to `#C7AACD`) is 4.25:1. Our replacements are listed above.

### 9.6 Other tokens

| Group | Tokens |
|---|---|
| Font | `--font: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` |
| Sizes | `--fs-10-5`, `--fs-12`, `--fs-12-25`, `--fs-13`, `--fs-13-6`, `--fs-14`, `--fs-14-4`, `--fs-15-4`, `--fs-16`, `--fs-17-5`, `--fs-18`, `--fs-20-4`, `--fs-21` (values as named, in px) |
| Weights | `--fw-light: 300`, `--fw-regular: 400`, `--fw-medium: 500`, `--fw-semibold: 600` |
| Space | `--space-1: 4px`, `-2: 8px`, `-3: 12px`, `-4: 16px`, `-5: 20px`, `-6: 24px`, `-7: 30px`, `-8: 48px` |
| Radius | `--radius: 4px`, `--radius-pill: 999px`, `--radius-round: 50%` |
| Shell | `--nav-w-standard: 250px`, `--nav-w-compact: 160px`, `--nav-w-icons: 70px`, `--nav-w` (switched), `--topbar-h: 70px`, `--footer-h: 60px`, `--boxed-w: 1300px`, `--gutter: 24px`, `--page-pad-x: 30px`, `--target: 44px` |
| Icons | `--icon-12` … `--icon-24` |
| Motion | `--dur-fast: 150ms`, `--dur: 200ms`, `--dur-slow: 250ms`, `--ease: cubic-bezier(.2, .8, .2, 1)` |

---

## 10. Pages

### 10.1 `dashboard.html`

```
1440 (content column 1130 wide, from x=280)
Home                                                                               Home
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ 6               (◎)  │ │ 1               (◎)  │ │ 3               (◎)  │ │ 2               (◎)  │
│ requests open        │ │ raised today         │ │ devices due back     │ │ devices in repair    │
│ [▲ 2 are urgent]     │ │                      │ │ next week            │ │                      │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
┌─────────────────────────────────────────────────────┐ ┌───────────────────────────────────────┐
│ Requests raised this week                           │ │ Needs doing today   [+ Raise a request]│
├─────────────────────────────────────────────────────┤ ├───────────────────────────────────────┤
│  2 ┤        ██                                       │ │ REQ-2048  Projector in Lab 2 shows a  │
│  1 ┤  ██    ██         ██    ██                      │ │ blue screen  [▲ Urgent] [⟳ In progress]│
│  0 ┼──██────██───0─────██────██──                    │ │ Nimali Perera                         │
│     Mon   Tue   Wed   Thu   Fri                      │ │ REQ-2047 … [+ New] · Nobody yet       │
│ Requests raised: Monday 1, Tuesday 2, Wednesday 0,   │ │ REQ-2046 … [◷ Waiting on someone]     │
│ Thursday 1, Friday 1.                                │ ├───────────────────────────────────────┤
└─────────────────────────────────────────────────────┘ │          See all requests →           │
  (8 of 12 columns)                                     └───────────────────────────────────────┘
                                                        ┌───────────────────────────────────────┐
                                                        │ Devices                               │
                                                        │ 128 devices in the register           │
                                                        │ 34 out on loan                        │
                                                        │ IT-0142 — Dell Latitude 3540 laptop   │
                                                        │ Who has it   Dilani Fernando          │
                                                        │ Due back     Mon 21 Sep 2026          │
                                                        └───────────────────────────────────────┘
                                                          (4 of 12 columns)
```

```
400: title, breadcrumb stacked; the four stat boxes one per row (full width);
then "Requests raised this week"; then "Needs doing today"; then "Devices". 1024: stat boxes 2 × 2.
```

- `.cards--four` for the stats (4-up ≥1200, 2-up 768–1199, 1-up below); `.cards--two-one` for the
  rest (8/4 columns ≥1200, one column below).
- **Primary action**: `Raise a request` in the `Needs doing today` head (`.button--primary`, icon
  `plus-circle`). One per page.
- Each row in `Needs doing today` is a link to `requests.html` (block link, min-height 44px): line 1
  `REQ-2048` 14px/600 + title; line 2 the urgency and status tags; line 3 `Who is on it` value
  (`Nobody yet` for REQ-2047) in `--c-muted`. Rows: REQ-2048, REQ-2047, REQ-2046.
- `Devices` box: the two figures as `.stat`-style lines (number 21px/500 + words), then a `.facts`
  list for `IT-0142`, with the tag linking to `device.html`.
- **Chart** (`.chart`, inline SVG, `viewBox="0 0 560 220"`, width 100%, height 220px, `aria-hidden="true"`
  `focusable="false"`):
  - Plot area x 40–540, baseline y 180, 1 unit = 70px (so 2 → y 40).
  - Gridlines at 0, 1, 2 (1px, `--c-chart-grid`), y-axis labels `0` `1` `2` at x 28, right-aligned,
    12px `--c-chart-label`.
  - Five bars, 48px wide, centred in five 100px slots, radius 3px on the top corners, fill
    `currentColor` with `color: var(--c-chart-bar)`.
  - A value label above each bar, 12px `--c-text`.
  - **Wednesday**: no bar; a 48 × 2px stub on the baseline in `--c-chart-zero` and the label `0`
    above it, so the day is visibly present with a value of zero.
  - Day labels `Mon Tue Wed Thu Fri` under the slots, 12px `--c-chart-label`.
  - Directly below the SVG, a visible `<p>`: `Requests raised: Monday 1, Tuesday 2, Wednesday 0,
    Thursday 1, Friday 1.` (14px `--c-muted`). This is the text alternative.
- `?demo=toast`: shows the flash on load.

### 10.2 `requests.html`

```
1440
Requests                                                                 Home  ›  Requests
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Everything staff have asked us to fix. Open the ones marked urgent first. [+ Raise a request]│  box head (lead 14px, not a heading)
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Search requests                                                                          │
│ [⌕ Reference, words, or a person's name, e.g. projector or REQ-2048          ] [Search]   │
│ Status            How urgent        Who is on it        Sort                             │
│ [All statuses ▾]  [All ▾]           [Anyone ▾]          [Newest first ▾]                  │
│ Showing 8 of 8 requests                                                                  │
│ ┌────────┬───────────────────────┬───────────┬────────┬──────────┬──────────────┬──────┬───────┐
│ │Reference│What is wrong          │Raised by  │Device  │How urgent│Status        │Who is│Raised │
│ ├────────┼───────────────────────┼───────────┼────────┼──────────┼──────────────┼──────┼───────┤
│ │REQ-2048│Projector in Lab 2 …   │Suresh K…  │IT-0087 │[▲ Urgent]│[⟳ In progress]│Nimali│Fri 11…│
│ │ … 8 rows, 12px cell padding, rows ≈ 45–66px                                            │
│ └──────────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

```
400
Requests
Home › Requests
┌───────────────────────────────────┐
│ Everything staff have asked …     │
│ [+ Raise a request] (full width)  │
├───────────────────────────────────┤
│ Search requests                   │
│ [⌕ ……………………………………………… ]         │
│ [Search]              (full width)│
│ Status        [All statuses ▾]    │  each filter full width, stacked
│ How urgent    [All ▾]             │
│ Who is on it  [Anyone ▾]          │
│ Sort          [Newest first ▾]    │
│ Showing 8 of 8 requests           │
│ ┌───────────────────────────────┐ │
│ │ Reference     REQ-2048        │ │  row card: label column 8.5em
│ │ What is wrong Projector in …  │ │
│ │ Raised by     Suresh Kumara   │ │
│ │ Device        IT-0087         │ │
│ │ How urgent    [▲ Urgent]      │ │
│ │ Status        [⟳ In progress] │ │
│ │ Who is on it  Nimali Perera   │ │
│ │ Raised        Fri 11 Sep …    │ │
│ └───────────────────────────────┘ │
└───────────────────────────────────┘
```

- One box. Its head holds the lead sentence (`<p>`, 14px `--c-text`) and the primary
  `Raise a request` button. The box has no `h2` title; the page `h1` names it.
- Filter form: `<form method="get" action="requests.html">`. Row 1: search (label `Search requests`,
  visible here, 14px/500) + `Search` submit as `.button--secondary`, so the page keeps one primary
  action. Row 2: four selects in a 4-column grid (≥992), 2-column (768–991),
  stacked (<768).
- Result line `Showing 8 of 8 requests`: 14px/500 `--c-heading`, `role="status"`, 16px above the table.
- Columns: `Reference`, `What is wrong`, `Raised by`, `Device`, `How urgent`, `Status`,
  `Who is on it`, `Raised`. `IT-0142` links to `device.html`; other tags are plain text. `Raised`
  uses `<time datetime>`. `Nobody yet` is set in the same style as a name (not muted, not italic):
  it is a real value, not a missing one.
- **Empty (`?demo=empty`)**: the search input keeps its value, the result line reads
  `Showing 0 of 8 requests`, and the table is replaced by `.empty`: heading
  `No requests match what you chose`, body `Try clearing the filters, or search for a different word.`,
  button `Clear the filters` (`.button--secondary`, a link to `requests.html`).

### 10.3 `device.html`

Title `IT-0142 — Dell Latitude 3540 laptop`, breadcrumb `Home › Devices › IT-0142`. `.cards--one-two`
(4/8 columns ≥1200, one column below). **Left box** (no title): 48px `monitor` disc, the tag line
`IT-0142` 14px/600 with `Laptop` in `--c-muted`, then the tags `[user-check Issued]` and
`[check-circle Good]`, then `.facts`: `Who has it` Dilani Fernando · `Where it is` Grade 6B Classroom ·
`Due back` Mon 21 Sep 2026 · `Given out` Tue 25 Aug 2026; then the page's primary button
`Raise a request` (full width, → `request-form.html`). **Right column**, three boxes: `Details`
(`.facts` in two columns: `Serial` 5CG4113XYZ, `Bought` 14 Feb 2024, `Value` Rs 285,000,
`Warranty until` 13 Feb 2027, `Condition` Good, `Last checked` Thu 3 Sep 2026); `Linked requests`
(a `.datagrid` with `Reference`, `What is wrong`, `Status`, `Raised`: REQ-2047 `New`, REQ-1902
`Closed`); `History` (`.history`, the five entries newest first). Phone: all boxes stacked in that
order.

### 10.4 `request-form.html`

Title `Raise a request`, breadcrumb `Home › Requests › Raise a request`. One box, 8 of 12 columns at
≥1200 (≈740px), full width below; no box title. Fields in contract order, 20px apart (§7.5); the
urgency options as three `.choice` rows side by side (≥768). Foot of the form: `Send the request`
(`.button--primary`) then `Cancel` (`.button--secondary`, a link to `dashboard.html`), gap 12px,
left-aligned; on phone both full width, primary first.
**Errors (`?demo=errors`)**: a `.notice--bad` at the top of the box, `tabindex="-1"`, focused on load:
title `We couldn't send this yet — 2 things need your attention`, then a list of two links to
`#what` and `#where` whose text is the field label. The two fields show their error text (§7.5);
everything typed is kept, and `Where is it?` still shows `Choose a room`.
**Toast (`?demo=toast`)**: the flash `Request sent. We gave it the number REQ-2049.` with `Undo`.

### 10.5 `login.html` (the split sign-in)

```
1440
┌────────────────────────┬──────────────────────────────────────────────────────────────┐
│ [crest] Technology  [☾]│                                                              │
│         Management Desk│                                                              │
│                        │                     ┌──────────────┐                         │
│ Welcome back           │                     │   (crest,    │  white disc 220px       │
│ Sign in to the         │                     │    160 tall) │                         │
│ Technology Mgmt Desk.  │                     └──────────────┘                         │
│                        │                                                              │
│ Username               │               Vivere Disce ~ Learn to Live                   │
│ The name the school …  │                   (21px/300, white)                          │
│ [nimali.p           ]  │                                                              │
│ Password               │                    brand panel, --c-primary                  │
│ Passwords are case …   │                                                              │
│ [••••••••           ]  │                                                              │
│ [      Sign in       ] │                                                              │
│                        │                                                              │
│ Polymath College ·     │                                                              │
│ Technology Mgmt Desk   │                                                              │
└────────────────────────┴──────────────────────────────────────────────────────────────┘
  form column 360px [M], heading and brand line centred   the rest
```

- `<main class="signin">`: grid `360px 1fr` at ≥1400px [M: 360px column at 1440], `420px 1fr` at
  992–1399 [I], one column below 992 [I].
- Form column: `--c-surface`, padding **48px** at the sides [M: fields start x=48 and are 264px wide],
  48px top and bottom, flex column. At the top, the brand line (crest-chip **28px** tall + wordmark),
  **centred** [M: 28px logo centred at y=49]. The form is centred vertically [S: heading at y=196].
  At the bottom, the footer line, centred, 14px `--c-muted` [S]. The colour-mode button (hidden
  without JS) sits top-right of this column.
- `h1` `Welcome back` 17.5px/500 [M], **centred**; the sub-line is 14px `--c-muted`, also centred
  [S]; 48px gap from the sub-line to the first label [S].
- Fields as §7.5: labels left-aligned, fields 44px tall and full column width (264px) [M width; D
  height, reference 38px]. `Sign in` is `.button--primary`, full width, 44px, 24px above it [M: full
  width, primary shadow; D height].
- Brand panel: `--c-primary` fill (both modes); the crest `assets/crest.png` at 160px tall, centred
  on a 220px circle filled with `--c-on-primary` (white in both modes) so the purple crest is not lost
  on purple (the image itself is unmodified, 002/23); the motto below in `--c-on-primary` 21px/300,
  24px under the circle. No carousel, no bubbles, no illustration.
- **Below 992px**: the form column first (full width, padding 30px), then the brand panel as a
  band (padding 32px, crest 96px tall on a 132px disc, motto 17.5px/300).
- **Error (`?demo=error`)**: `.notice--bad` above the fields, `tabindex="-1"`, focused on load, title
  `We couldn't sign you in`, body as contract; both inputs `aria-invalid="true"` and
  `aria-describedby` include the notice's id; `Username` keeps `nimali.p`.

### 10.6 `ui-kit.html`

Title `Design kit`, breadcrumb `Home › Design kit`. A column of boxes, each with an `h2` title naming
a section of the 002 must-show list (`Buttons`, `Links`, `Form fields`, `Status tags`, `Urgency`,
`List row`, `Box`, `Stat tile`, `History`, `Notices`, `Toast`, `Dialog`, `Empty state`, `Pager`,
`Breadcrumb`, `Avatar`, `Icons`, `Type scale`, `Colours`, `Spacing`, `Focus`), with `h3` for
subsections. The type-scale box lists every role in §8 with its px size. The colours box lists every
token with hex and ratio for light, dark and the three tones. The focus box shows the ring on
`--c-surface`, on `--c-primary`, and on each nav tone. `Dialog` demonstrates the settings `<dialog>`
(an `Open the layout settings` button is **not** added; it reuses the top-bar gear, so no new string).

---

## 11. States (every page)

| State | Where | What the user sees |
|---|---|---|
| Default | all | as wireframed |
| Empty | `requests.html?demo=empty` | §10.2 |
| Loading | none (static prototype; no async). `ui-kit` shows the busy button only | — |
| Validation errors | `request-form.html?demo=errors`, `login.html?demo=error` | §10.4, §10.5 |
| Server error | not modelled (no server) | — |
| Success | `?demo=toast` on any app page | the flash, `role="status"`, focus stays where it was |
| No permission | not modelled; the signed-in user is the technician | — |
| Dropdown open | notifications, user menu | §4 |
| Settings open | any app page | §6 |
| Drawer open | <992px | §1.2 |

---

## 12. Accessibility, keyboard, motion

- **Landmarks**: skip link (first focusable, `href="#main"`), `<aside>` with `<nav aria-label="Main">`,
  `<header>` (top bar), `<main id="main">`, `<footer>`, breadcrumb `<nav aria-label="Breadcrumb">`,
  search form `role="search"`.
- **Headings**: one `h1` per page (in the title row); `h2` for box titles, the empty state and the
  settings panel; `h3` inside boxes. Sidebar group titles, the help card title and dropdown heads
  are not headings.
- **Tab order** (1440): skip link → sidebar (brand has no link) → `Home` → `Requests` summary →
  (children if open) → `Devices` → `Design kit` → help card button → menu toggle → search input →
  `Search` → colour mode → notifications → settings → user menu → breadcrumb links → page content →
  footer. This matches visual order because the sidebar is left of and above the top bar in reading
  order. (On phone the drawer's DOM position is the same; closed, it is `visibility: hidden` so it
  leaves the tab order, and with `:target` it is visible.)
- **Focus after actions**: drawer close → toggle; dropdown `Escape` → its summary; settings close →
  opener (or the user summary); `?demo=errors`/`error` → the notice; `Clear the filters` → page load,
  focus at top as normal.
- **Targets**: every control ≥44 × 44px at 400 and at 1440 (sidebar rows, top-bar buttons, dropdown
  items, radio rows, pager, flash buttons). Breadcrumb links are inline text and exempt; give them
  `padding-block: 12px` anyway at <768px so they reach 44px.
- **Status**: every status, condition, urgency and notification state is an icon plus a word.
- **Motion** (all removed under `prefers-reduced-motion: reduce`): sidebar width change 200ms
  (`--nav-w` transition on the grid column), drawer slide 250ms, scrim fade 200ms, dropdown panel
  fade + 4px rise 150ms on open, settings panel slide 250ms, chevron rotation 200ms, busy spinner.

### 12.1 Needs JavaScript (criterion 25; exactly these)

| Control | Without JS |
|---|---|
| Menu toggle (collapse on desktop, drawer on phone) | hidden; desktop shows the full sidebar; phone shows a `Menu` link to `#nav`, which opens the sidebar with `:target`, and `Close the menu` links back to `#main` |
| Colour-mode button (top bar, sign-in) | hidden; the mode follows the system through `prefers-color-scheme` |
| `Layout settings` buttons (top-bar gear, user-menu item) | hidden; the page uses the defaults |
| Toast `Undo` | hidden |

**Enhanced by JS, but nothing is hidden without it**: `Escape` and outside-click on the two
dropdowns, one-dropdown-at-a-time, drawer focus containment (`inert`), the `?demo=` hooks, saving
choices to `tmd-layout`.

### 12.2 Settings contract (unchanged from the brief)

`<html lang="en-LK" data-width="full" data-nav-size="standard" data-nav-tone="light">` in the HTML,
with **no** `data-theme` (so CSS follows the system). `theme-init.js` (in `<head>`, before
`style.css`, no `defer`/`async`) reads `localStorage["tmd-layout"]`, parses it inside `try`, and for
each of the four keys whose value is in the allowed set, sets the attribute. Nothing else.

---

## 13. Fidelity checklist

"Reference" values are at 1440×900 unless marked 400. M = measured with Playwright computed style
and bounding box; S = read off the reference screenshot; I = inferred, not measured (re-measure,
§15). The reviewer ticks each row side by side with the reference, in light and dark.

| # | Aspect | Reference (observed, and how it was measured) | Our spec | Deliberate deviation and why | Reviewer ✓ |
|---|---|---|---|---|---|
| 1 | Sidebar width, standard | 250px (M, bbox) | 250px | — | ✓ R1 |
| 2 | Sidebar width, compact | 160px (M, bbox) | 160px | — | ✓ R1 |
| 3 | Sidebar width, icons | 70px (M, bbox) | 70px | — | ✓ R1 |
| 4 | Collapse behaviour | The hamburger collapses the sidebar to the 70px icon size. On hover the row widens to 260px (label 14.4/500 in primary on the sidebar colour, padding 15px 20px), and the children drop below it in a 190px white panel with the dropdown shadow and 5px vertical padding (M). Below 992px the sidebar is off-canvas (M, 0×0 at 400) | Toggle collapses to `icons` for the current page only and expands back to the size chosen in settings (`standard` if that is `icons`); the same 260px row and 190px children panel on hover **and** keyboard focus; drawer below 992px | Flyout also on focus, so it is not hover-only (002/14). Child rows are 44px (reference ≈36px). The collapse is not saved: only the settings panel writes the sidebar size, which keeps `tmd-layout` to exactly four keys (criterion 4) | ✓ R1 (behaviour changed after R1: collapse no longer saved) |
| 5 | Brand area | 250 × 70px box, sidebar colour, 24px side padding, 1px right border (M) | Same box, crest-chip 32px + two-line wordmark | Our brand row is inside the sidebar, not the top bar (criterion 10 puts the crest in the sidebar); the toggle therefore sits at the top bar's left edge instead of inside the brand box, moving the search 52px right | ✓ R1 |
| 6 | Group-title style | 12px/500, line 18px, padding 12px 20px, row 42px, `#545A6D`, sentence case (M) | Identical; colour `--nav-group` | Dark mode colour lightened `#858D98` → `#9CA3AD` (3.99:1 → 5.26:1) | ✓ R1 |
| 7 | Menu-item height | 41.4px (M) | 44px | +2.6px for the 44px target floor | ✓ R1 |
| 8 | Menu-item text | 14.4px/500, padding 9.92px 24px (M) | 14.4px/500, padding 0 24px, min-height 44px | — | ✓ R1 |
| 9 | Menu icon size | 16px standard, 18px icons size (M) | 16px / 18px | — | ✓ R1 |
| 10 | Active state | Text and icon in primary, no background, no bar (M colour, S) | Text and icon `--nav-active-text` + 3px left bar | Primary is crest purple; the bar makes "current" readable without colour (CLAUDE.md, brief criterion 29) | ✓ R1 |
| 11 | Child items | 13.6px/500, indent 52.8px, row ≈33px (M) | 13.6px/500, indent 52.8px, row 44px | 44px floor | ✓ R1 |
| 12 | Expandable-item chevron | Right chevron at the row's right edge, turns downward when open (S); hidden in compact and icons sizes (S) | `chevron-right` 16px, rotates 90° in 200ms; shown in compact (12px, under the label), hidden in icons | Kept in compact: it is the only cue that `Requests` opens | ✓ R1 |
| 13 | Help card in sidebar | 201px wide, margin 48px 24px 0, radius 4px, primary at 10%, illustration (M) | Same box and tint, no illustration, title + body + button | No illustration (criterion 3) | ✓ R1 |
| 14 | Top-bar height | 70px + 1px border = 71px (M) | 70px + 1px | — | ✓ R1 |
| 15 | Top-bar order | Left: logo box, hamburger, search. Right: language, colour mode, apps grid, notifications, settings, user (S) | Left: toggle, search. Right: colour mode, notifications, settings, user | Language switcher and apps grid left out (D8) | ✓ R1 |
| 16 | Top-bar icon buttons | 52 × 70px, icon ≈20px (M box, S icon) | 52 × 70px, icon 20px; 44 × 70 below 992px | — | ✓ R1 |
| 17 | Search-field style | 219 × 40px, `#F8F9FA`, no border, radius 4px, 14px text, padding-right 50px, primary button 36 × 34 inside on the right with a primary shadow (M) | 304 × 44px, `--c-surface-2`, 1px `--c-control` border, radius 4px, 14px; button 44 × 44 inside right, crest purple, primary shadow | Border added (field edge was 1.05:1; needs 3:1). Height and button to 44px (target floor). Width 304px: at 240px the contract placeholder `Reference or words, e.g. REQ-2048` is clipped, which criterion 26 forbids | ✓ R1 |
| 18 | Dropdown width | Notifications 320px, padding 0; profile 160px, padding 4px; both 1px `#E9E9EF`, radius 4px, shadow `0 5px 20px -6px` at 10% (M) | Notifications 320px; user menu min 160px (grows to fit `Layout settings`), padding 4px; same border, radius and shadow shape | — | ✓ R1 |
| 19 | Dropdown header, items, footer | Header `Notifications` 14px/500 with 16px padding and an "Unread (3)" link on the right; items: 32px round image, then title 14px/500, text 13px/400 at 75% colour, time 13px/400 at 75% colour with a clock icon; text column starts 65px in; no dividers; footer link centred over a top rule (M pass 2 and pass 3; S for the image, dividers and footer). Profile items 14px/400, padding 5.6px 16px, 35.2px tall (M) | Head 14px/500, padding 16px, no right-hand link; items 32px disc + 16px gap + title 14/500 + body 13/400 + time 13/400, both `--c-muted`; no dividers; footer `See all requests` 44px; user items 14px/400, 44px | New items get a `New` tag and weight 600, so unread is a word, not a tint. No "Unread" link (no such string in the contract). Rows 44px | not ticked in R1 (time and title were inferred); re-check after pass 3 |
| 20 | Notification count | 10.5px/700, white on `#FD625E`, pill 19 × 16px at y=12 (M) | 10.5px/600, white on `#B42318`, pill 18+ × 16px at y=12 | White on the reference red is 2.96:1; 700 weight is not loaded (D3) | ✓ R1 |
| 21 | Badges (soft tint) | Text in the family colour on the same colour at **18%** alpha; **10.5px/700** in body text (0.75em; 10.8px inside the 14.4px sidebar), line height 1, padding 0.25em top and bottom; square badges have a small radius, pills 800px with 0.6em sides (M on the reference's general-UI page, pass 3; S for the square badge's radius) | Tag: **10.5px/600**, line 1, padding 3px 5px, radius 4px, a 12px icon + the word; background = the family colour at 18% over the surface (light); text a darker (light) / lighter (dark) shade of the family | Reference text on its tint is ≈2.5:1 (danger `#FD625E` on its tint 2.45:1); ours 4.88–6.52:1. Weight 600 (700 not loaded). Icon added (status as icon + word) | not ticked in R1 (never measured); re-check after pass 3 |
| 22 | Title row | h1-sized title 18px/500 left, breadcrumb 14px right, padding-bottom 24px, height 46px (M) | Same | — | ✓ R1 |
| 23 | Breadcrumb separator and colour | Right-chevron glyph separator at 75% text colour, 8px padding; links in text colour; current item at 75% text colour (≈`#646766`, 5.65:1) (M) | `chevron-right` 14px `--c-muted`, 8px each side; links `--c-text`; current `--c-muted` `#636779` (5.61:1) | — (our muted token is the same step as the reference's 75% text) | ✓ R1 |
| 24 | Title row on phone | Title, then breadcrumb 8px below, both left (M, y=94 and y=124 at 400) | Same, below 768px | — | ✓ R1 |
| 25 | Card style | White, 1px `#E9E9EF` border, radius 4px, no shadow; header padding 20px with a 1px `#E9E9EF` bottom border; body padding 20px; title 15.4px/500 (M) | Same values | — | ✓ R1 |
| 26 | Grid gutter | 24px between cards (M: 265px cards at 24px gaps) | 24px | — | ✓ R1 |
| 27 | Page padding | Content begins 30px right of the sidebar and 24px below the top bar; 30px at 400 (M) | 30px sides, 24px top | — | ✓ R1 |
| 28 | Type scale: body, table, breadcrumb, footer | 14px/400, line 21px (M) | 14px/400, 21px | none (D9) | ✓ R1 |
| 29 | Type scale: headings | Page title 18/500; card title 15.4/500; stat value 21/500 (20.4 at 400); other sizes present 17.5, 16 (M) | h1 18/500; h2 15.4/500; stat 21 (20.4); sign-in h1 17.5/500; h3 14/600 | none (D9) | ✓ R1 |
| 30 | Type scale: small text and weights | 10.5, 12, 12.25, 13, 13.6px present; smallest 10.2px; weights 400/500/700 seen, 300/600 loaded (M) | Help 13, error 12.25, tag 10.5, notification body and time 13, child 13.6, count 10.5; weights 300/400/500/600 | Grey small text darkened where below 4.5:1 (muted `#74788D` → `#636779`); sizes unchanged; 700 → 600 | ✓ R1 (tag size changed 12 → 10.5 after R1; re-check) |
| 31 | Buttons | Radius 4px, 14px/400, padding 7.52px 12px, 38px tall; primary fill with a primary-tinted shadow `0 2px 6px` at 50%; soft variant = primary at 10% with primary text; link variant = primary text; outline = 1px primary border (M) | Radius 4px, 14px/400, padding 0 12px, 44px tall; primary as measured in crest purple; secondary = the soft variant; quiet = the link variant | 44px floor. Outline and large variants not used (no need on these six screens) | ✓ R1 |
| 32 | Stat tile | Label (14px, 75% text) above the value (21px/500); sparkline at right; small coloured delta badge + "Since last week" (M, S) | Value above words; 48px icon disc at right; only the first tile has a sub-line (`2 are urgent`) | Contract wording must read in order (`6 requests open`); no sparklines or deltas (brief scope) | ✓ R1 |
| 33 | Form controls | Label 14px/500; input and select 38px, `#F8F9FA` fill, 1px `#E9E9EF` border, radius 4px, padding 7.52px 12px (select right 36px), 14px; help 13px at 75% text colour; error text 12.25px/400 in `#FD625E`; checkbox 14px, radius 3.5px (M). **The reference has no textarea on its form-elements page** (checked in pass 3), so there is nothing to compare ours with | Label 14px/500; controls 44px, `#F8F9FA` fill, 1px `--c-control` border, radius 4px, padding 0 12px (select right 36px), 14px; help 13px `--c-muted` above the control; error 12.25px/400 `#B42318` with an icon; checkbox 18px. Textarea: the input's measured values, min-height 110px, padding 10px 12px [I, our decision] | 44px; a 3:1 border (reference 1.2:1); error colour 2.96:1 → 6.57:1; help above the field; 18px checkbox. Textarea not comparable (the reference has none) | not ticked in R1 (textarea inferred); tick the measurable parts, textarea stays not comparable |
| 34 | Tables | Cells padding 12px, 14px, white, `#E9E9EF` bottom rules, 46px rows; head cells 14px/700, white, bottom rule (M) | Same; head 14px/600 | Weight 600 (700 not loaded). Below 768px rows become cards instead of side-scrolling, so no text is clipped at 400px | ✓ R1 |
| 35 | Dark-mode surface ladder | Page `#313533`; top bar, sidebar, card head, cells, dropdown `#2C302E`; border `#383D3B`; field `#363A38`; text `#ADB5BD`; headings `#CED4DA` (M) | Same hexes | Control border `#3B403D` → `#808782` (3:1); muted → `#9CA3AD` | ✓ R1 |
| 36 | Light-mode surfaces | Page and cards white; sidebar `#FBFAFF`; field `#F8F9FA`; text `#313533`; border `#E9E9EF` (M) | Same, sidebar `#FCFAFD` | Sidebar tint moved toward the crest hue (≈1 step) | ✓ R1 |
| 37 | Settings panel | Right side, 300px wide, full height, `#FBFAFF` in light and `#313533` in dark, soft two-layer shadow; head row 56px with 16px padding; title 17.5px/500 at x=16, y=18 (`#313533` light, `#CED4DA` dark); 24px body padding; group titles 14px/500 (`#CED4DA` in dark); options 14px/500 (`#ADB5BD` in dark) with 14px radios filled with the primary when checked; two-option groups side by side, three-option groups stacked; close = 24px dark disc (M, light pass 2, dark pass 3); a rule under the head, page dimmed grey behind (S) | Right `<dialog>`, 300px, `--c-sheet`, the same shadow; head 56px, padding 0 16px; title 17.5/500 `--c-heading`; legends 14/500 `--c-heading`; options 14/500 `--c-text`; the same side-by-side / stacked layout; `--scrim` backdrop | Only four option groups (D8); options are 44px bordered rows with 18px radios; `Close` is a 44px button with the word | not ticked in R1 (dark internals not captured); re-check after pass 3 |
| 38 | Sidebar colour options | Light; Dark = `#2C302E` with items `#99A4B1` and titles `#858D98`; Brand = the primary with items and titles in white at 60% (M) | Light; Dark = `#2C302E`, items `#99A4B1`, titles `#9CA3AD`; Purple = `#722A82`, items and titles `#D5BFDA` | Dark titles 3.99 → 5.26:1; white at 60% on the crest is 4.25:1, so we use 70% (`#D5BFDA`, 5.19:1) | ✓ R1 |
| 39 | Boxed width | 1300px, centred (x=70 at 1440), shell shadow `0 5px 20px -6px` at 10% (M); outside colour not measured | 1300px, the same shadow shape, `--c-boxed-outside` | — | ✓ R1 |
| 40 | Footer | 60px, padding 20px 12px, 14px, `#74788D`, white, 1px top border (M) | 60px, padding 20px 30px, 14px `--c-muted`, `--c-surface`, 1px top border | Text darkened (4.36:1 → 5.61:1); side padding aligned with the content's 30px | ✓ R1 |
| 41 | Phone breakpoint and drawer | Sidebar off-canvas below 992px; the hamburger opens it over the page (M, S) | Same breakpoint; 250px drawer, scrim, `Escape`, scrim click and `Close the menu` close it; `:target` without JS | Close button and no-JS path added (criterion 18) | ✓ R1 |
| 42 | Phone top bar | 73 × 70px brand box in the **sidebar colour** (`#FBFAFF` light, `#2C302E` dark) with a **1px right border** (`#E9E9EF` / `#383D3B`), padding 0 24px; top bar white (light) / `#2C302E` (dark) with a 1px bottom border; hamburger 52 × 70 at x=73; then search icon, bell, settings, avatar block (M pass 3, light and dark; S for the order) | 73 × 70px brand box with `--nav-bg` and a 1px right border `--nav-border` (it follows the chosen sidebar tone, as the reference's does), with the 32px crest-chip centred (≈20px each side); toggle; search icon, colour mode, bell, settings (hidden <600px), avatar block; buttons 44 × 70 | Brand box size, colour and border **match** the reference. Its padding does not: 0 24px leaves 25px, too narrow for the 32px crest, so we keep the measured box and centre the crest. Colour mode kept on phone (a listed feature); settings reachable from the user menu on very small screens | not ticked in R1 (brand box was plain white); re-check after pass 3 |
| 43 | User block in the top bar | Avatar 36px round, name, chevron, on a light shaded block with side borders (M, S) | Same, initials `NP` instead of a photo, plus the role line | No photos (criterion 3); role shown (criterion 14) | ✓ R1 |
| 44 | Sign-in page | Split: 360px white form column left, with a 28px logo centred at the top, a centred 17.5px/500 heading, 48px side padding, 264px fields and a full-width 38px primary button, and a centred footer. On the right a primary-colour panel with a photo, decoration and a testimonial carousel (M, S) | 360px form column, 48px padding, 28px crest-chip and wordmark centred, centred heading and sub-line, 264px fields, full-width `Sign in`; crest-purple panel with the crest on a white disc and the motto | Fields and button 44px. No photo, carousel or illustration; crest on white so it is not lost on purple | ✓ R1 |

**44 rows. Review round 1: 39 of 44 ticked** (reviewer, side by side with the reference, light and
dark). Rows 19, 21, 33, 37 and 42 were not ticked; pass 3 measured 19, 21, 37 and 42, and the spec
now matches or records a deviation for each. Row 33's textarea has no counterpart on the reference.
"R1" in the last column is the reviewer's round-1 tick. Numeric rows without a deviation that the
verifier measures at 1440: 1, 2, 3, 8 (font), 9, 14, 16, 18, 22, 23, 24 (at 400), 25, 26, 27, 28,
29, 30 (sizes), 36, 39, and 42 (at 400). Rows 31, 33, 34 and 37 are also measurable for everything
except their listed deviations.

---

## 14. Skills for the builder

`inclusive-interaction:keyboard-navigation`, `ui-design:dark-mode-design`,
`design-systems:accessibility-audit`, `dataviz` (the chart), `design-systems:theming-system`
(the attribute-switched token blocks).

---

## 15. Values to re-measure (the [I] list)

Two measurement passes were run. Pass 1 covered the dashboard shell with its panels closed. Pass 2
covered:
- the content card and the non-current menu item;
- the top-bar icon and the breadcrumb separator;
- the notifications and profile dropdowns and the settings panel, open;
- the boxed layout, and the dark and brand sidebar tones in light mode;
- the buttons, form, validation and basic-tables pages;
- the sign-in page and the icons-size hover flyout.

Pass 3 (after review round 1) covered:
- the notification rows' title, body and time;
- the reference's soft badges, from its general-UI page;
- the settings panel internals in dark mode;
- the phone brand box and top bar, in light and dark;
- a check for a textarea on the form-elements page (there is none).

The following are still **inferred**:

1. **Textarea** (§7.5): **not measurable**. The reference's form-elements page has no textarea
   (checked in pass 3). Ours follows the measured input, with min-height 110px and padding 10px
   12px. Checklist row 33 marks it "not comparable".
2. **Soft badges, remaining parts** (§7.4): the square badge's radius (4px read off the
   screenshot), its side padding (5px assumed), the grey (plain) family, and the tint alpha in dark
   mode. The dark tints are unchanged (`--c-*-soft` in §9.3).
3. **Compact size** (§2.3): how the children of an expandable item are shown.
4. **Boxed layout**: the page colour outside the 1300px shell (`--c-boxed-outside`).
5. **Settings backdrop**: the exact colour and alpha (`--scrim`).
6. **Right-hand top-bar icons**: 20px, read off the screenshots. The measured glyph was the
   hamburger, 20 × 16px.
7. **Sub-item colours** in the dark and brand sidebar tones (set equal to the items).
8. **Dark mode for the dropdown items and the sign-in page** (the settings panel's dark internals
   are now measured).
9. **Sign-in form column** at widths between 992 and 1399px (420px assumed).
10. **`h3`**: 14px/600. The reference's dashboard has no `h3` role to measure.

If a re-measured value differs from "Our spec" by more than 2px, or falls in a different colour
family, correct the checklist row and the matching section here first, then in the build.

### Changed after pass 2 (old → new)

The builder started from the earlier version of this file. These are the only values that changed.
Everything not listed was either confirmed by pass 2 or is unchanged.

**Shell and sidebar**

1. Icons-size hover label (§2.3): a separate chip with `--shadow-pop` → **the hovered row widens to
   260px**, background `--nav-bg`, text `--nav-hover-text`, padding 15px 20px, **no shadow**.
2. Icons-size children flyout (§2.3):
   - position: right of the item → **directly under the label row** (left 70px, top 51px);
   - width: 200px → **190px**;
   - background: `--nav-bg` → **`--c-surface`**;
   - corners: radius 0 4px 4px 0 → **no radius**;
   - padding: none → **5px 0**;
   - child links: 13.6px/500 `--nav-child` → **14px/400 `--c-text`**, padding 0 20px, still 44px
     tall.
3. Sidebar tones (§9.4). The table now has four columns, and "Light tone in dark mode" is its own
   set. That set keeps the old values: items `#E9ECEF`, children `#ADB5BD`.
   - Dark tone `--nav-text`: `#E9ECEF` → **`#99A4B1`**.
   - Dark tone `--nav-child`: `#ADB5BD` → **`#99A4B1`**.
   - Purple tone `--nav-text`: `#F1E6F4` → **`#D5BFDA`**.
   - Purple tone `--nav-group`: `#D8BEDF` → **`#D5BFDA`**.
   - Purple tone `--nav-child`: `#E6D3EA` → **`#D5BFDA`**.
   - Purple tone `--nav-card-text` stays `#F1E6F4`.
4. `--shadow-boxed`: `0 0 24px rgba(0, 0, 0, 0.06)` →
   **`0 5px 20px -6px rgba(99, 103, 121, 0.14)`** (the same value as `--shadow-pop`).
5. `--scrim`: `rgba(33, 26, 36, 0.55)` → **`rgba(33, 26, 36, 0.4)`**.

**Dropdowns**

6. Notifications head `Notifications`: 16px/500, line 21px → **14px/500, line 16.8px**.
7. Notification items (§4):
   - grid gap: 12px → **16px**;
   - border-top between items → **none**;
   - footer link weight: 500 → **400**.
8. User menu panel:
   - width: 220px → **`min-width: 160px; width: max-content`**;
   - panel padding: 0 → **4px**;
   - the head shown below 992px (was 768px; see the verification note below): padding 16px → **12px**;
   - item icon gap: **8px**, now stated.

**Settings panel**

9. Settings head (§6):
   - height: 70px → **56px**;
   - padding: 0 24px → **0 16px 0 24px**;
   - title: 15.4px/500, line 18.48px → **17.5px/500, line 21px** (a new "Settings panel title" row
     in §8).
10. Settings legends: 14px/600, margin-bottom 8px → **14px/500, line 16.8px, margin-bottom 12px**.
    Fieldset margin-bottom: 24px → **32px**.
11. Settings options:
    - layout: all stacked → **`Colour mode` and `Page width` rows side by side** in two equal
      columns (gap 8px); the three-option groups stay stacked;
    - `.choice` gap: 12px → **8px**;
    - `.choice` text: 14px (weight unstated) → **14px/500**.

**Buttons and forms**

12. Buttons (§7.3):
    - padding: 0 16px → **0 12px**;
    - weight: 500 → **400**;
    - primary: now also has a **1px `--c-primary` border**.
13. Secondary button: `--c-surface` bg + 1px `--c-control` border + `--c-heading` text →
    **`--c-primary-soft` bg + `--c-primary-text` text, no border**. Hover: `--c-surface-2` →
    **`--c-primary` bg + `--c-on-primary` text**. This affects `Search` and `Clear the filters` on
    the requests page, `Cancel` on the form, `Reset to default` in the settings panel, and the file
    button.
14. Help text (`.field__help`, and the urgency options' help lines): 12.25px, line 18px →
    **13px, line 19.5px**.
15. Error text (`.field__error`): 12.25px/500 → **12.25px/400**, line 18.4px.
16. `--c-field` (light): `#FFFFFF` → **`#F8F9FA`**. The select's right padding is now stated as
    36px.

**Tables**

17. Table head cells: 14px/500 on `--c-surface-2` → **14px/600 on `--c-surface`**, with a 1px
    `--c-border` bottom rule.

**Sign-in page (§10.5)**

18. Sign-in page:
    - `360px 1fr` grid: from ≥1200px → **≥1400px**; `420px 1fr` now covers 992–1399px;
    - form column padding: 48px 40px → **48px on every side**;
    - brand line: unspecified → **crest-chip 28px tall, centred**;
    - heading and sub-line: left-aligned → **centred**, with a **48px** gap from the sub-line to the
      first label;
    - footer line: → **centred**;
    - `Sign in`: **24px** above it, now stated.

**Aligned with the build after verification** (these follow the build; the build does not change):

19. Top-bar search field width: 240px → **304px** (`--search-w`). At 240px the contract
    placeholder is clipped, which criterion 26 forbids (§3, checklist row 17).
20. Top-bar user block: avatar only, and name and role moved into the dropdown head, below 768px →
    **below 992px**. That is the drawer's breakpoint, so the whole top bar changes layout at one
    width (§1.1, §3, §4, §8).

**Unchanged by pass 2, now tagged [M]:** the card shadow (none), the idle menu-item colour
`#545A6D`, the breadcrumb separator and current-item colour, form labels at 14px/500, table cell
padding and rules, the boxed width of 1300px, and the sign-in column width and heading size.

**Contrast re-check for the changed colours** (all pass):
- `#99A4B1` on `#2C302E`: 5.29:1.
- `#D5BFDA` on `#722A82`: 5.19:1.
- `--c-primary-text` on `--c-primary-soft` (the new secondary button): 7.52:1 light, 5.85:1 dark.
- White on `--c-primary` (secondary hover): 8.86:1.
- `--c-text` on `#F8F9FA` (fields): 11.80:1.
- `--c-muted` placeholder on `#F8F9FA`: 5.32:1.
- `--c-control` border on `#F8F9FA`: 3.25:1.
- 13px help text in `--c-muted`: 5.32:1 on `#F8F9FA`, 5.61:1 on white.

### Changed after pass 3 (old → new)

These follow the third measurement pass and the review round 1 findings. Items 7 and 8 record
changes the builder has already made. Everything not listed is unchanged.

**Status tags (§7.4, §8, checklist row 21)**

1. Tag type: 12px/500, line 18px → **10.5px/600, line height 1**. Measured 10.5px/700; 700 is not
   loaded.
2. Tag padding: 3px 8px → **3px 5px**. Radius 4px, 12px icon and 4px gap are unchanged.
3. Light-mode soft tints are now the family colour at the measured **18%** over white:

   | Token | Old | New | Text on it, old → new |
   |---|---|---|---|
   | `--c-ok-soft` | `#E3F4EC` | **`#D9F2E8`** | 5.05 → 4.88 |
   | `--c-warn-soft` | `#FFF3DC` | **`#FFF4E0`** | 5.39 → 5.43 |
   | `--c-bad-soft` | `#FDECEB` | **`#FFE3E2`** | 5.75 → 5.42 |
   | `--c-note-soft` | `#E7F0FB` | **`#DFEFFC`** | 5.61 → 5.48 |
   | `--c-brand-soft` | `#F1EAF3` | **`#E6D9E9`** | 7.52 → 6.52 |

   The new figures are the builder's exact, truncated values.

   The text tokens, `--c-plain-soft`, `--c-primary-soft` (still `#F1EAF3`, used by the secondary
   button, avatar and selected rows) and all dark-mode tints are unchanged. `--c-brand-soft` and
   `--c-primary-soft` are now different values. The brand tints are used by the brand tags and by
   the stat and notification icon discs.

**Notifications (§4, §8, checklist row 19)**

4. Notification time: 12px/400, line 18px → **13px/400, line 19.5px**, `--c-muted`. The title's
   line height is now stated as 16.8px.

**Settings panel (§6, checklist row 37)**

5. Settings head padding: 0 16px 0 24px → **0 16px**. The measured 16px padding puts the title at
   x=16. The height stays 56px. The option text is now stated as `--c-text`.

**Phone top bar (§3, checklist row 42)**

6. Phone brand box: plain (top-bar white) → **`--nav-bg` background with a 1px right border
   `--nav-border`**, 73 × 70px, with the 32px crest-chip **centred** (≈20px each side). This was
   amended after the build: the measured 0 24px padding leaves 25px, which cannot fit the crest, so
   the measured box size wins over the measured padding (a recorded deviation). The reviewer's row-42 finding is ruled a **match,
   not a deviation**: there is no accessibility cost, and the box follows the chosen sidebar tone,
   as the reference's does. The crest-chip image has its own white background, so it stays visible
   on the purple tone.

**Already in the build**

7. Sidebar collapse (§3, checklist row 4): "toggles between the saved size and `icons` **and saves
   it**" → **collapses for the current page only; expands back to the size chosen in settings, or
   `standard` if that is `icons`; never writes `tmd-layout`**. Only the settings panel saves the
   sidebar size, so the stored object keeps exactly four keys (criterion 4).
8. Contrast figures are **truncated to two decimals, never rounded up** (§9.5):
   - `#313533` on white: 12.45 → **12.44**;
   - `#313533` on `#F8F9FA`: 11.81 → **11.80**;
   - `#E9ECEF` on `#2C302E`: 11.29 → **11.28**;
   - the minimums: `--c-muted` on `#363A38` 4.54 → **4.53**, and `--c-control` on `#363A38`
     3.14 → **3.13**.

   f.md's other ratios are hand-computed to about ±0.01. The builder's exact, truncated README
   table governs the second decimal.

**Checklist (§13)**

9. The `Reviewer ✓` column is filled with the reviewer's 39 round-1 ticks. Rows 19, 21, 33, 37 and
   42 are marked for re-check after pass 3.

---

## 16. For the planner to confirm

- **Card and section titles** that reuse contract wording: dashboard `Requests raised this week`,
  `Needs doing today`, `Devices` (from the brief); device page `Details`, `Linked requests`,
  `History`; ui-kit section titles as listed in §10.6 (taken from 002's must-show list).
  `Details` is the one word not already in a contract; alternative: no title on that box.
- **Field labels on `device.html`** (`Who has it`, `Where it is`, `Due back`, `Given out`, `Serial`,
  `Bought`, `Value`, `Warranty until`, `Condition`, `Last checked`) are the content model's field
  names; `Given out` and `Last checked` come from the contract's prose.
- **The word `New` on unread notifications** (§4). It is already a contract status word; without it,
  unread would be shown by weight and tint only.

---

## Reference and licence

The reference is **Minia** (layout "LTS", vertical), a paid admin template by **Themesbrand**, sold
on **ThemeForest**. The client has **not** bought a licence. This direction was **observed, not
copied**: the numbers above were measured from its public demo page in a browser (computed styles,
element boxes and screenshots kept in the session scratchpad, outside the repository), and every
token name, class name, attribute name, file and line of code in `design/f-desk/` is our own.

The reference is built on Bootstrap 5, jQuery, MetisMenu, SimpleBar, ApexCharts, Feather icons and
Material Design Icons. We use none of those libraries (brief D2):

| Reference uses | We use instead |
|---|---|
| Bootstrap 5 (CSS grid, components, JS) | our own CSS grid, flexbox and custom properties |
| jQuery | vanilla JS in one IIFE, bound to `data-*` hooks |
| MetisMenu (expandable sidebar) | `<details>` / `<summary>` |
| SimpleBar (custom scrollbars) | native overflow with `scrollbar-width` and `scrollbar-color` |
| ApexCharts | one inline SVG bar chart with a text alternative |
| Material Design Icons | not used |
| Feather icons | **used** (MIT), path data taken from Feather's own source, inlined as a sprite |

Third-party pieces used: **IBM Plex Sans** (SIL Open Font License 1.1, via Google Fonts), because the
owner asked for the same font; **Feather** (MIT), for fidelity to the reference's line icons. Nothing
else.
