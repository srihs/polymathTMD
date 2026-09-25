# Status tabs (`.tabs`)

Origin: brief 005, criterion 20 (the Zoom link request queue: `Waiting` / `Link sent` / `Not approved` / `All`, each with a count). For any list page that is split by status.

**Why a new component:** f-desk filters lists with `<select>`s (`.finder__filters`). A queue with four fixed statuses reads faster as links you can see at once, each with its count. They are **links**, not ARIA tabs: each one loads a new page with `?status=…`, works without JS, and can be bookmarked. So there is no `role="tablist"` and no arrow-key handling.

## Anatomy

```html
<nav class="tabs" aria-label="Filter by status">
  <ul class="tabs__list">
    <li><a class="tabs__link" href="?status=waiting" aria-current="page">Waiting <span class="tabs__count">3<span class="visually-hidden"> requests</span></span></a></li>
    <li><a class="tabs__link" href="?status=approved">Link sent <span class="tabs__count">12<span class="visually-hidden"> requests</span></span></a></li>
    …
  </ul>
</nav>
```

It sits in a `.box__head` (padding reduced to `0 var(--space-5)` for that head, so the links' bar lines up with the head's bottom border).

## Values

| Part | Spec |
|---|---|
| `.tabs__list` | flex, `flex-wrap: wrap`, gap 0, no list style, margin 0, padding 0 |
| `.tabs__link` | inline-flex, align centre, gap `var(--space-2)`, `min-height: var(--target)` (and at ≥768px `min-height: 56px`, the box head's height), padding `0 var(--space-4)`, `--fs-body`, `--fw-regular`, `--c-text`, no underline, `position: relative` |
| Hover | text `--c-primary-text` |
| Focus | 2px `--c-focus` outline, offset `-2px` (inset, so it isn't clipped by the box) |
| Current (`aria-current="page"`) | text `--c-primary-text`, weight `--fw-semibold`, plus a 3px bar (`::after`, `--nav-bar` height, full link width, `--c-primary-text`) along the bottom edge. The bar and the weight are the non-colour cues |
| `.tabs__count` | `--fs-tag` (10.5px) / `--fw-semibold`, `--lh-flat`, padding `var(--tag-pad-y) var(--tag-pad-x)`, `--radius`, `--c-plain-soft` background, `--c-plain-text` text. On the current tab: `--c-brand-soft` / `--c-brand-text` |
| Below 600px | `.tabs__list` becomes a 2-column grid (`repeat(2, minmax(0, 1fr))`); each link fills its cell; the current one keeps its bottom bar |

Contrast: `--c-text` on `--c-surface` 12.44 / 6.45; `--c-primary-text` on `--c-surface` 8.86 / 6.31; count plain 5.97 / 7.27, brand 6.52 / 5.85 (f.md §9.5). The bar is non-text: 8.86 / 6.31.

## States

| State | Look |
|---|---|
| Idle | `--c-text`, plain count |
| Hover | `--c-primary-text` |
| Focus | inset focus ring |
| Current | primary text, 600, bottom bar, brand count, `aria-current="page"` |
| Count 0 | shown as `0` (a tab never hides) |

## Behaviour

Plain links. Switching tab drops the search and the page number, so each tab's count matches its list. No JS.
