# F — Desk

A static prototype of the Technology Management Desk in the shape of the admin layout the client
asked for: a grouped left sidebar, a top bar with search, notifications and the user menu, a title
and breadcrumb row, cards on a grid, a footer, light and dark mode, and a layout settings panel.
It is dressed in the crest purple and built only from the measurements in
`docs/design/directions/f.md`. None of the reference's code or files were used (see
**Reference and licence** at the end).

## How to open it

Open any page straight from disk, for example `design/f-desk/dashboard.html`, in Chromium, Edge or
Chrome. Start at `login.html` and sign in with anything to reach the dashboard.

**Firefox** keeps `localStorage` separate for each file on `file://`, so the layout settings do not
carry from one page to the next there. To try persistence in Firefox, serve the folder instead:
`py -3.13 -m http.server 8123` run from `design/f-desk/`, then open `http://localhost:8123/`.

## Files

| File | What it is |
|---|---|
| `login.html`, `dashboard.html`, `requests.html`, `device.html`, `request-form.html`, `ui-kit.html` | The six screens |
| `style.css` | The whole stylesheet, token-first, in the nine sections brief 003 criterion 29 names |
| `theme-init.js` | Runs in `<head>` before `style.css`; reads `tmd-layout` and sets the four attributes on `<html>`, nothing else |
| `app.js` | One IIFE of enhancements, bound only to `data-*` attributes, loaded with `defer` |
| `assets/` | `crest.png`, `crest-chip.png`, `favicon-32.png` (binary copies, unmodified) |
| `screenshots/` | The 39 captures listed under **Screenshots** |

## Layout settings

The four settings live on `<html>`:

| Attribute | Values | Default |
|---|---|---|
| `data-theme` | `light`, `dark` | absent, so the page follows the device (`prefers-color-scheme`), also with JavaScript off |
| `data-width` | `full`, `boxed` (1300px, centred) | `full` |
| `data-nav-size` | `standard` (250px), `compact` (160px), `icons` (70px) | `standard` |
| `data-nav-tone` | `light`, `dark`, `purple` | `light` |

They are saved in `localStorage` under the single key `tmd-layout`, as a JSON object with the keys
`theme`, `width`, `navSize` and `navTone`, for example
`{"theme":"dark","width":"boxed","navSize":"compact","navTone":"purple"}`. `theme` is only saved
once someone picks a colour mode, so until then the page keeps following the device. `Reset to
default` removes the key.

Change them with the gear button in the top bar, or `Layout settings` in the user menu. CSS reads
the attributes only to switch token blocks (section 1) and apply the size variants (section 6).

**The menu button and the saved sidebar size.** The saved `navSize` is always the size chosen in
the settings panel. The menu button at the top left collapses the sidebar to icons only and expands
it back to that chosen size (or to Standard, when the chosen size is itself icons only). The button
does **not** save anything: it collapses the sidebar for the page you are on, and a reload or the
next page shows the chosen size again. The panel's `Sidebar size` radios always show what is on
screen, so after a collapse they show `Icons only` until the page is left. This keeps
`tmd-layout` to exactly its four keys and means the button can never "forget" a Compact choice.

## Fonts

**IBM Plex Sans** 300, 400, 500 and 600, from Google Fonts with `display=swap`. It is the only
family: body text, headings, the sidebar, tables, forms, and the wordmark `Technology Management
Desk` (14.4px/600). Weight 300 is used once, for the motto on the sign-in page. Sizes follow the
reference's measured type scale (brief decision D9): body, table cells, form fields and breadcrumb
14px; sidebar items 14.4px; sidebar children 13.6px; group titles 12px; page title 18px; card
titles 15.4px; stat numbers 21px (20.4px below 992px); help text, notification body and time
13px; error text 12.25px; status tags and the bell count 10.5px/600, the smallest text in the
folder (the reference's smallest is 10.2px; its tags are 10.5px/700, and 700 is not loaded).

## Palette

Every raw colour is written once, in the palette block at the top of `style.css`. Everything else
refers to it: the light tokens, the dark tokens (`--dk-*`), the four sidebar tone sets
(`--tone-light-*`, `--tone-dim-*` for the light tone in dark mode, `--tone-dark-*`,
`--tone-purple-*`) and the `--nav-*` names the sidebar reads.

**How it was derived.** The neutrals are the reference's measured neutrals, except where they
failed WCAG AA. Those were darkened in light mode or lightened in dark mode: muted text
`#636779`, the control border `#868A9B`/`#808782`, the dark-mode muted text `#9CA3AD` and the
sidebar greys. The primary is the crest purple `#722A82`, read from `logo.png`. `#F1EAF3` is the
crest at 10% on white. `#3E2F43` is the crest at 25% on the dark surface. `#5C1F6A` and `#8A3D9C`
are the crest darker and lighter along the same hue. `#CFA3DA` is the crest lightened until it
passes 5:1 on every dark surface, and `#D5BFDA` until it passes 4.5:1 on the crest itself. The
status families keep green, amber, red and blue, with new text shades that pass 4.5:1 on their tints.
In light mode the soft tints are the family colour at the measured 18% over white (`#D9F2E8`,
`#FFF4E0`, `#FFE3E2`, `#DFEFFC`, and `#E6D9E9` for the brand tags and icon discs). `--c-primary-soft`
stays `#F1EAF3` for the secondary button, the avatar and selected rows.

**Where the crest purple shows**: the primary buttons, the search button, the active sidebar item
and its 3px bar, links, focus rings, the chart bars, the avatar, the brand tags, the purple sidebar
tone and the sign-in brand panel. In dark mode, text, focus and chart marks use `#CFA3DA`. Filled
buttons stay `#722A82` with white text at 8.86:1.

### Palette primitives

| Token | Hex |
|---|---|
| `--white` | `#FFFFFF` |
| `--grey-25` | `#FCFAFD` |
| `--grey-50` | `#F8F9FA` |
| `--grey-100` | `#EEEFF3` |
| `--grey-150` | `#ECEBF2` |
| `--grey-200` | `#E9E9EF` |
| `--grey-210` | `#E9ECEF` |
| `--grey-300` | `#CED4DA` |
| `--grey-320` | `#C9CBD4` |
| `--grey-400` | `#ADB5BD` |
| `--grey-430` | `#9CA3AD` |
| `--grey-440` | `#99A4B1` |
| `--grey-500` | `#868A9B` |
| `--grey-520` | `#808782` |
| `--grey-600` | `#636779` |
| `--grey-650` | `#545A6D` |
| `--grey-700` | `#4A504D` |
| `--grey-750` | `#3A3E3C` |
| `--grey-800` | `#383D3B` |
| `--grey-820` | `#363A38` |
| `--grey-850` | `#313533` |
| `--grey-900` | `#2C302E` |
| `--grey-950` | `#262928` |
| `--crest-50` | `#F1EAF3` |
| `--crest-100` | `#E6D9E9` |
| `--crest-80` | `#F1E6F4` |
| `--crest-200` | `#D5BFDA` |
| `--crest-300` | `#CFA3DA` |
| `--crest-400` | `#9A5AA8` |
| `--crest-500` | `#8A3D9C` |
| `--crest-600` | `#722A82` |
| `--crest-700` | `#5C1F6A` |
| `--crest-900` | `#3E2F43` |
| `--green-50` | `#D9F2E8` |
| `--green-300` | `#6FD3A6` |
| `--green-700` | `#17744F` |
| `--green-900` | `#22382F` |
| `--amber-50` | `#FFF4E0` |
| `--amber-300` | `#F2C46D` |
| `--amber-700` | `#8A5A00` |
| `--amber-900` | `#3D3322` |
| `--red-50` | `#FFE3E2` |
| `--red-300` | `#F59A94` |
| `--red-700` | `#B42318` |
| `--red-900` | `#432A2A` |
| `--blue-50` | `#DFEFFC` |
| `--blue-300` | `#8CBDF2` |
| `--blue-700` | `#1E5FA8` |
| `--blue-900` | `#22334A` |

### Semantic tokens, light and dark

| Token | Light | Dark |
|---|---|---|
| `--c-page` | `#FFFFFF` | `#313533` |
| `--c-surface` | `#FFFFFF` | `#2C302E` |
| `--c-surface-2` | `#F8F9FA` | `#363A38` |
| `--c-field` | `#F8F9FA` | `#363A38` |
| `--c-sheet` | `#FCFAFD` | `#313533` |
| `--c-border` | `#E9E9EF` | `#383D3B` |
| `--c-control` | `#868A9B` | `#808782` |
| `--c-text` | `#313533` | `#ADB5BD` |
| `--c-heading` | `#313533` | `#CED4DA` |
| `--c-muted` | `#636779` | `#9CA3AD` |
| `--c-primary` | `#722A82` | `#722A82` |
| `--c-primary-hover` | `#5C1F6A` | `#8A3D9C` |
| `--c-primary-text` | `#722A82` | `#CFA3DA` |
| `--c-primary-soft` | `#F1EAF3` | `#3E2F43` |
| `--c-on-primary` | `#FFFFFF` | `#FFFFFF` |
| `--c-focus` | `#722A82` | `#CFA3DA` |
| `--c-ok-text` | `#17744F` | `#6FD3A6` |
| `--c-ok-soft` | `#D9F2E8` | `#22382F` |
| `--c-ok-line` | `rgba(23, 116, 79, 0.3)` | `rgba(111, 211, 166, 0.3)` |
| `--c-warn-text` | `#8A5A00` | `#F2C46D` |
| `--c-warn-soft` | `#FFF4E0` | `#3D3322` |
| `--c-warn-line` | `rgba(138, 90, 0, 0.3)` | `rgba(242, 196, 109, 0.3)` |
| `--c-bad-text` | `#B42318` | `#F59A94` |
| `--c-bad-soft` | `#FFE3E2` | `#432A2A` |
| `--c-bad-line` | `rgba(180, 35, 24, 0.3)` | `rgba(245, 154, 148, 0.3)` |
| `--c-bad-solid` | `#B42318` | `#B42318` |
| `--c-note-text` | `#1E5FA8` | `#8CBDF2` |
| `--c-note-soft` | `#DFEFFC` | `#22334A` |
| `--c-note-line` | `rgba(30, 95, 168, 0.3)` | `rgba(140, 189, 242, 0.3)` |
| `--c-plain-text` | `#545A6D` | `#CED4DA` |
| `--c-plain-soft` | `#EEEFF3` | `#3A3E3C` |
| `--c-brand-text` | `#722A82` | `#CFA3DA` |
| `--c-brand-soft` | `#E6D9E9` | `#3E2F43` |
| `--c-count-bg` | `#B42318` | `#B42318` |
| `--c-count-text` | `#FFFFFF` | `#FFFFFF` |
| `--c-boxed-outside` | `#ECEBF2` | `#262928` |
| `--c-chart-bar` | `#722A82` | `#CFA3DA` |
| `--c-chart-zero` | `#868A9B` | `#808782` |
| `--c-chart-grid` | `#E9E9EF` | `#383D3B` |
| `--c-chart-label` | `#636779` | `#9CA3AD` |
| `--c-shadow-pop` | `0 5px 20px -6px rgba(99, 103, 121, 0.14)` | `0 5px 20px -6px rgba(0, 0, 0, 0.5)` |
| `--c-shadow-sheet` | `0 0 24px rgba(0, 0, 0, 0.06), 0 1px 0 rgba(0, 0, 0, 0.02)` | `0 0 24px rgba(0, 0, 0, 0.3)` |

### Sidebar tones

| Token | Light tone, light mode | Light tone, dark mode | Dark tone | Purple tone |
|---|---|---|---|---|
| `--nav-bg` | `#FCFAFD` | `#2C302E` | `#2C302E` | `#722A82` |
| `--nav-border` | `#E9E9EF` | `#383D3B` | `#383D3B` | `#722A82` |
| `--nav-brand` | `#313533` | `#E9ECEF` | `#E9ECEF` | `#FFFFFF` |
| `--nav-group` | `#545A6D` | `#9CA3AD` | `#9CA3AD` | `#D5BFDA` |
| `--nav-text` | `#545A6D` | `#E9ECEF` | `#99A4B1` | `#D5BFDA` |
| `--nav-child` | `#545A6D` | `#ADB5BD` | `#99A4B1` | `#D5BFDA` |
| `--nav-hover-text` | `#722A82` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| `--nav-active-text` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-active-bg` | `transparent` | `#3E2F43` | `#3E2F43` | `#5C1F6A` |
| `--nav-active-bar` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-focus` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-card-bg` | `#F1EAF3` | `#313533` | `#313533` | `#5C1F6A` |
| `--nav-card-title` | `#722A82` | `#CFA3DA` | `#CFA3DA` | `#FFFFFF` |
| `--nav-card-text` | `#313533` | `#ADB5BD` | `#ADB5BD` | `#F1E6F4` |
| `--nav-card-btn-bg` | `#722A82` | `#722A82` | `#722A82` | `#FFFFFF` |
| `--nav-card-btn-text` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#722A82` |
| `--nav-scroll` | `#C9CBD4` | `#4A504D` | `#4A504D` | `#9A5AA8` |

### Contrast pairs

WCAG 2.x ratios, computed from the token values in `style.css` by resolving each `var()` chain,
and **truncated** to two decimals (never rounded up), so a figure never overstates a pass. Three
figures therefore read 0.01 lower than in `docs/design/directions/f.md` §9.5, whose rounding
varies: `#313533` on white is 12.443 (f.md 12.45), `#313533` on `#F8F9FA` is 11.805 (f.md 11.81),
and `#E9ECEF` on `#2C302E` is 11.285 (f.md 11.29). All
text in this folder is under 24px, so every text pair needs 4.5:1; marks (control borders, focus
rings, chart bars, the active bar, icons that carry meaning) need 3:1. Lowest text pair:
**4.53:1**. Lowest mark pair: **3.13:1**.

| Pair | Light mode | Dark mode |
|---|---|---|
| `--c-text` on `--c-page` | #313533 / #FFFFFF **12.44** | #ADB5BD / #313533 **5.99** |
| `--c-text` on `--c-surface` | #313533 / #FFFFFF **12.44** | #ADB5BD / #2C302E **6.44** |
| `--c-text` on `--c-surface-2` | #313533 / #F8F9FA **11.80** | #ADB5BD / #363A38 **5.56** |
| `--c-text` on `--c-field` | #313533 / #F8F9FA **11.80** | #ADB5BD / #363A38 **5.56** |
| `--c-text` on `--c-sheet` | #313533 / #FCFAFD **11.98** | #ADB5BD / #313533 **5.99** |
| `--c-text` on `--c-primary-soft` | #313533 / #F1EAF3 **10.54** | #ADB5BD / #3E2F43 **5.98** |
| `--c-heading` on `--c-surface` | #313533 / #FFFFFF **12.44** | #CED4DA / #2C302E **8.95** |
| `--c-heading` on `--c-surface-2` | #313533 / #F8F9FA **11.80** | #CED4DA / #363A38 **7.72** |
| `--c-heading` on `--c-sheet` | #313533 / #FCFAFD **11.98** | #CED4DA / #313533 **8.32** |
| `--c-heading` on `--c-primary-soft` | #313533 / #F1EAF3 **10.54** | #CED4DA / #3E2F43 **8.30** |
| `--c-muted` on `--c-page` | #636779 / #FFFFFF **5.60** | #9CA3AD / #313533 **4.89** |
| `--c-muted` on `--c-surface` | #636779 / #FFFFFF **5.60** | #9CA3AD / #2C302E **5.26** |
| `--c-muted` on `--c-surface-2` | #636779 / #F8F9FA **5.31** | #9CA3AD / #363A38 **4.53** |
| `--c-muted` on `--c-field` | #636779 / #F8F9FA **5.31** | #9CA3AD / #363A38 **4.53** |
| `--c-muted` on `--c-sheet` | #636779 / #FCFAFD **5.39** | #9CA3AD / #313533 **4.89** |
| `--c-muted` on `--c-primary-soft` | #636779 / #F1EAF3 **4.75** | #9CA3AD / #3E2F43 **4.87** |
| `--c-primary-text` on `--c-surface` | #722A82 / #FFFFFF **8.86** | #CFA3DA / #2C302E **6.31** |
| `--c-primary-text` on `--c-surface-2` | #722A82 / #F8F9FA **8.40** | #CFA3DA / #363A38 **5.44** |
| `--c-primary-text` on `--c-sheet` | #722A82 / #FCFAFD **8.54** | #CFA3DA / #313533 **5.86** |
| `--c-primary-text` on `--c-primary-soft` | #722A82 / #F1EAF3 **7.51** | #CFA3DA / #3E2F43 **5.85** |
| `--c-on-primary` on `--c-primary` | #FFFFFF / #722A82 **8.86** | #FFFFFF / #722A82 **8.86** |
| `--c-on-primary` on `--c-primary-hover` | #FFFFFF / #5C1F6A **11.29** | #FFFFFF / #8A3D9C **6.50** |
| `--c-on-primary` on `--c-bad-solid` | #FFFFFF / #B42318 **6.57** | #FFFFFF / #B42318 **6.57** |
| `--c-count-text` on `--c-count-bg` | #FFFFFF / #B42318 **6.57** | #FFFFFF / #B42318 **6.57** |
| `--c-bad-text` on `--c-surface` | #B42318 / #FFFFFF **6.57** | #F59A94 / #2C302E **6.32** |
| `--c-ok-text` on `--c-ok-soft` | #17744F / #D9F2E8 **4.88** | #6FD3A6 / #22382F **6.89** |
| `--c-warn-text` on `--c-warn-soft` | #8A5A00 / #FFF4E0 **5.43** | #F2C46D / #3D3322 **7.60** |
| `--c-bad-text` on `--c-bad-soft` | #B42318 / #FFE3E2 **5.42** | #F59A94 / #432A2A **6.19** |
| `--c-note-text` on `--c-note-soft` | #1E5FA8 / #DFEFFC **5.49** | #8CBDF2 / #22334A **6.50** |
| `--c-plain-text` on `--c-plain-soft` | #545A6D / #EEEFF3 **5.97** | #CED4DA / #3A3E3C **7.26** |
| `--c-brand-text` on `--c-brand-soft` | #722A82 / #E6D9E9 **6.52** | #CFA3DA / #3E2F43 **5.85** |
| `--c-chart-label` on `--c-surface` | #636779 / #FFFFFF **5.60** | #9CA3AD / #2C302E **5.26** |
| `--c-control` on `--c-surface` (non-text, needs 3:1) | #868A9B / #FFFFFF **3.43** | #808782 / #2C302E **3.63** |
| `--c-control` on `--c-field` (non-text, needs 3:1) | #868A9B / #F8F9FA **3.25** | #808782 / #363A38 **3.13** |
| `--c-control` on `--c-sheet` (non-text, needs 3:1) | #868A9B / #FCFAFD **3.30** | #808782 / #313533 **3.38** |
| `--c-focus` on `--c-page` (non-text, needs 3:1) | #722A82 / #FFFFFF **8.86** | #CFA3DA / #313533 **5.86** |
| `--c-focus` on `--c-surface` (non-text, needs 3:1) | #722A82 / #FFFFFF **8.86** | #CFA3DA / #2C302E **6.31** |
| `--c-focus` on `--c-sheet` (non-text, needs 3:1) | #722A82 / #FCFAFD **8.54** | #CFA3DA / #313533 **5.86** |
| `--c-primary-text` on `--c-primary-soft` (non-text, needs 3:1) | #722A82 / #F1EAF3 **7.51** | #CFA3DA / #3E2F43 **5.85** |
| `--c-bad-text` on `--c-field` (non-text, needs 3:1) | #B42318 / #F8F9FA **6.23** | #F59A94 / #363A38 **5.45** |
| `--c-bad-text` on `--c-surface` (non-text, needs 3:1) | #B42318 / #FFFFFF **6.57** | #F59A94 / #2C302E **6.32** |
| `--c-ok-text` on `--c-surface` (non-text, needs 3:1) | #17744F / #FFFFFF **5.75** | #6FD3A6 / #2C302E **7.35** |
| `--c-chart-bar` on `--c-surface` (non-text, needs 3:1) | #722A82 / #FFFFFF **8.86** | #CFA3DA / #2C302E **6.31** |
| `--c-chart-zero` on `--c-surface` (non-text, needs 3:1) | #868A9B / #FFFFFF **3.43** | #808782 / #2C302E **3.63** |

| Sidebar pair | Light tone, light mode | Light tone, dark mode | Dark tone | Purple tone |
|---|---|---|---|---|
| `--nav-brand` on `--nav-bg` | #313533 / #FCFAFD **11.98** | #E9ECEF / #2C302E **11.28** | #E9ECEF / #2C302E **11.28** | #FFFFFF / #722A82 **8.86** |
| `--nav-group` on `--nav-bg` | #545A6D / #FCFAFD **6.61** | #9CA3AD / #2C302E **5.26** | #9CA3AD / #2C302E **5.26** | #D5BFDA / #722A82 **5.18** |
| `--nav-text` on `--nav-bg` | #545A6D / #FCFAFD **6.61** | #E9ECEF / #2C302E **11.28** | #99A4B1 / #2C302E **5.28** | #D5BFDA / #722A82 **5.18** |
| `--nav-child` on `--nav-bg` | #545A6D / #FCFAFD **6.61** | #ADB5BD / #2C302E **6.44** | #99A4B1 / #2C302E **5.28** | #D5BFDA / #722A82 **5.18** |
| `--nav-hover-text` on `--nav-bg` | #722A82 / #FCFAFD **8.54** | #FFFFFF / #2C302E **13.38** | #FFFFFF / #2C302E **13.38** | #FFFFFF / #722A82 **8.86** |
| `--nav-active-text` on `--nav-active-bg` | #722A82 / #FCFAFD **8.54** | #CFA3DA / #3E2F43 **5.85** | #CFA3DA / #3E2F43 **5.85** | #FFFFFF / #5C1F6A **11.29** |
| `--nav-active-bar` on `--nav-active-bg` (non-text) | #722A82 / #FCFAFD **8.54** | #CFA3DA / #3E2F43 **5.85** | #CFA3DA / #3E2F43 **5.85** | #FFFFFF / #5C1F6A **11.29** |
| `--nav-focus` on `--nav-bg` (non-text) | #722A82 / #FCFAFD **8.54** | #CFA3DA / #2C302E **6.31** | #CFA3DA / #2C302E **6.31** | #FFFFFF / #722A82 **8.86** |
| `--nav-focus` on `--nav-card-bg` (non-text) | #722A82 / #F1EAF3 **7.51** | #CFA3DA / #313533 **5.86** | #CFA3DA / #313533 **5.86** | #FFFFFF / #5C1F6A **11.29** |
| `--nav-card-title` on `--nav-card-bg` | #722A82 / #F1EAF3 **7.51** | #CFA3DA / #313533 **5.86** | #CFA3DA / #313533 **5.86** | #FFFFFF / #5C1F6A **11.29** |
| `--nav-card-text` on `--nav-card-bg` | #313533 / #F1EAF3 **10.54** | #ADB5BD / #313533 **5.99** | #ADB5BD / #313533 **5.99** | #F1E6F4 / #5C1F6A **9.34** |
| `--nav-card-btn-text` on `--nav-card-btn-bg` | #FFFFFF / #722A82 **8.86** | #FFFFFF / #722A82 **8.86** | #FFFFFF / #722A82 **8.86** | #722A82 / #FFFFFF **8.86** |

When the Requests children open as a panel in icons-only size, they use `--c-text` on `--c-surface`,
the first pairs in the table above.

## Why it suits non-technical school staff

The client wants this layout, and the staff will see it next to the reference, so the shape is kept:
the sidebar on the left, one search box, a bell, and your name at the top right. Inside that shape,
nothing asks staff to decode anything. The sidebar says `Home`, `Requests`, `Devices` and
`Raise a request`, grouped under plain headings. Every status is an icon and a word (`Waiting on
someone`, not an amber dot). Unread notifications say `New` rather than relying on bold text.
Every button, menu row and radio is at least 44px tall, so a teacher on a phone between lessons can
tap it. Grey text was darkened wherever the reference's greys would be hard to read on a projector
or in a bright classroom.

`Raise a request` is always one click away: in the sidebar's `Requests` group, on the help card, on
the dashboard and on the device page. The form keeps everything typed when something is missing and
says exactly what to fix. Colour mode follows the device until someone changes it, so a teacher
whose laptop is in dark mode is not dazzled.

## Navigation model

- **Desktop (992px and wider).** A 250px sidebar with four groups (`Menu`, `Help desk`,
  `Equipment`, `Prototype`). `Requests` is a `<details>` holding `All requests` and
  `Raise a request`, open on the two request pages. The current page has `aria-current="page"`,
  purple text and a 3px bar. The sidebar can be compact (160px, icon over word) or icons only
  (70px). In icons only, the hovered or keyboard-focused row widens to 260px to show its word, and
  the `Requests` children appear in a panel under it.
- **Phone (below 992px).** The sidebar is off-screen. The menu button opens it as a 250px drawer
  over a dimmed page. `Escape`, the dimmed page and `Close the menu` close it, and focus returns to
  the menu button. The top-bar search collapses to an icon that opens the same form.
- **Without JavaScript.** Desktop shows the full sidebar. On a phone a `Menu` link (`href="#nav"`)
  opens the sidebar with `:target`, and `Close the menu` links back to `#main`. The notifications,
  user menu, `Requests` group and phone search are all `<details>`, so they open without a script.

## Needs JavaScript

Exactly these controls need a script. Each one carries `hidden` in the HTML and `app.js` reveals it,
so nothing is a dead button when scripts are off.

| Control | Without JavaScript |
|---|---|
| Menu button (collapse on desktop, drawer on phone) | Hidden. Desktop shows the full sidebar. Phone shows a `Menu` link to `#nav` that opens the sidebar with `:target`; `Close the menu` links back to `#main`. |
| Colour-mode button (top bar and sign-in page) | Hidden. The colour mode follows the device through `prefers-color-scheme`. |
| `Layout settings` buttons (top-bar gear, user-menu item, the design kit's Dialog box) | Hidden. The page uses the defaults. |
| The toast's `Undo` | Hidden. |

Also added by `app.js`, though nothing is hidden without it: `Escape` and click-outside on the
dropdowns, one dropdown open at a time, the drawer's focus handling (`inert` on the page behind it),
saving choices to `tmd-layout`, the error-summary links moving focus into their field, and the
`?demo=` hooks.

## Demo hooks

These are **prototype only** and are never carried into `templates/`. They let the owner and the
verifier see each state without a server.

| URL | State |
|---|---|
| `login.html?demo=error` | Sign-in error. The notice is focused, both fields are marked invalid, and `Username` keeps `nimali.p`. |
| `request-form.html?demo=errors` | The form with two errors. The summary is focused and links to each field, everything typed is kept, and `Where is it?` still shows `Choose a room`. |
| `requests.html?demo=empty` | No results. The search box keeps `REQ-2049`, the line reads `Showing 0 of 8 requests`, and the empty state offers `Clear the filters`. |
| `?demo=toast` on any app page | The success toast `Request sent. We gave it the number REQ-2049.` with `Undo` and `Close`. Sending the request form lands on `dashboard.html?demo=toast`. |

## Screenshots

`screenshots/` holds 39 full-page captures, taken with the web fonts loaded. Desktop is 1440×900 and
mobile is 400×844. In the two `settings-open` captures (and the two `menu-open` ones), only the
first screen of the page is dimmed and the panel only covers that first screen. That is how a
full-page capture records a fixed panel and backdrop, not how the page looks: in a browser, the
panel and the dimming always fill the window as you scroll.

- Each page in light and dark, desktop and mobile: `desktop-P--light.png`, `desktop-P--dark.png`,
  `mobile-P--light.png`, `mobile-P--dark.png` for `login`, `dashboard`, `requests`, `device`,
  `request-form` and `ui-kit` (24 files).
- States, in light mode: `desktop-login--error.png`, `desktop-request-form--errors.png`,
  `desktop-requests--empty.png`, `desktop-dashboard--toast.png`.
- The shell on `dashboard.html`: `desktop-dashboard--settings-open--light.png`,
  `desktop-dashboard--settings-open--dark.png`, `desktop-dashboard--notifications-open.png`,
  `desktop-dashboard--user-menu-open.png`, `desktop-dashboard--nav-compact.png`,
  `desktop-dashboard--nav-icons.png` (with the pointer on `Requests`, so the flyout shows),
  `desktop-dashboard--nav-dark.png`, `desktop-dashboard--nav-purple.png`,
  `desktop-dashboard--boxed.png`, `mobile-dashboard--menu-open--light.png` and
  `mobile-dashboard--menu-open--dark.png`.

## Skills used

- Designer (`docs/design/directions/f.md`): see that file and brief 003's Design section.
- Builder: `accessible-content:form-labelling` (visible labels, help before the control and linked
  with `aria-describedby`, fieldsets and legends for the radio groups, errors linked to their
  fields). `solar-duotone-bold` was preloaded but deliberately **not** used: brief decision D4 sets
  Feather for this folder only.

## Reference and licence

**The reference.** The client pointed us at **Minia** (the "LTS" vertical layout), a paid admin
template by **Themesbrand**, sold on **ThemeForest**. **No Minia licence was bought.** This folder
was **observed, not copied**. The designer measured the public demo's rendered geometry, font sizes
and sampled colours in a browser and recorded them in `docs/design/directions/f.md`. The builder
worked only from that file. No HTML, CSS, JavaScript, class name, attribute name, comment, image,
illustration or icon file was taken from the demo or its package, and the reference site was not
opened while building. Every name in this folder is our own.

**Third-party pieces used**, and nothing else:

| Piece | Licence | Why |
|---|---|---|
| IBM Plex Sans (300, 400, 500, 600), loaded from Google Fonts | SIL Open Font License 1.1 | The owner asked for the same font as the reference, and it is openly licensed. |
| Feather icons: 37 icons inlined as an SVG `<symbol>` sprite on each page, path data taken from the `feather-icons` npm package (version 4.29.2) | MIT (notice below) | For fidelity: the reference uses Feather-style line icons in its shell. A sprite of `<symbol>`s is used rather than a `<template>`, because `<use>` needs no script. |

The Feather MIT notice, reproduced in full:

```
The MIT License (MIT)

Copyright (c) 2013-2023 Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**The reference's libraries that were not used**, and what replaced each (brief decision D2):

| The reference uses | Replaced by |
|---|---|
| Bootstrap 5 (grid, components, JS) | Our own CSS grid, flexbox and custom properties in `style.css` |
| jQuery | Plain JavaScript in one IIFE (`app.js`), bound to `data-*` attributes |
| MetisMenu (the expandable sidebar) | `<details>` and `<summary>` |
| SimpleBar (custom scrollbars) | Native scrolling with `scrollbar-width: thin` and `scrollbar-color` from tokens |
| ApexCharts | One inline SVG bar chart with a visible text alternative |
| Material Design Icons | Not used; Feather alone |
