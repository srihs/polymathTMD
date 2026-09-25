# Availability list (`.avail`)

Origin: brief 005, criterion 28 (the Zoom request detail: is each paid host account free for every class, and if not, which bookings clash). For any "can this resource take this booking?" list.

**Why a new component:** each row is an account with a status tag and, when busy, its own list of clashes. `.worklist` rows are block links (one target per row), and nesting a table in a table cell for the clashes would be hard to read on a phone and with a screen reader.

## Anatomy

```html
<ul class="avail">
  <li class="avail__item">
    <div class="avail__who">
      <p class="avail__name">Zoom 02</p>
      <p class="avail__email">zoom02@polymath.lk</p>
    </div>
    <span class="tag tag--warn"><svg class="icon" …><use href="#i-alert-triangle"></use></svg>Busy for 1 of 8 classes</span>
    <ul class="avail__clashes">
      <li><time …>Wed 7 Oct 2026</time>, 8:30 am to 11:30 am clashes with <a href="…">ZL-0031</a> Grade 10 Science, 9:00 am to 12:00 pm</li>
    </ul>
  </li>
</ul>
```

A free account has the `tag--ok` tag (`check-circle`, `Free for all 8 classes`) and no `.avail__clashes`.

## Values

| Part | Spec |
|---|---|
| `.avail` | no list style, margin 0, padding 0 |
| `.avail__item` | grid `minmax(0, 1fr) auto` (who, tag), column gap `var(--space-4)`, row gap `var(--space-2)`, padding `var(--space-4) 0`, top border 1px `--c-border` between items (`+` selector) |
| `.avail__name` | `--fw-semibold`, `--c-heading` |
| `.avail__email` | `--c-muted`, `overflow-wrap: anywhere` |
| Tag | column 2, `align-self: start` |
| `.avail__clashes` | grid column `1 / -1`; `margin: 0; padding-left: var(--space-5)`; disc bullets; each `li` `--c-text`, line height `--lh-body`, margin-bottom `var(--space-1)` |
| Clash link | `--c-primary-text`, underlined; `.tap-link` below 768px (44px) |
| Below 600px | one column: who, then the tag, then the clashes |

Contrast: all existing pairs (f.md §9.5): heading 12.44 / 8.96, muted 5.61 / 5.26, tag ok 4.88 / 6.89, tag warn 5.43 / 7.61.

## States

| State | Tag | Clashes |
|---|---|---|
| Free for every class | `tag--ok`, `check-circle`, `Free for all {n} classes` | none |
| Busy for some | `tag--warn`, `alert-triangle`, `Busy for {k} of {n} classes` | one `li` per clash |
| No accounts at all | the list is not rendered; the box lead says what to do | — |

Status is always the word plus the icon; the colour only repeats it.
