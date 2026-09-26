# Availability list (`.avail`)

Origin: brief 005, criterion 28 (the Zoom request detail: is each paid host account free for every class, and if not, which bookings clash). Extended by brief 006 (the live Zoom connection): a row can also say Zoom itself couldn't be checked, or that the account isn't connected to Zoom yet, and a busy row can mix a database clash with a clash seen only in Zoom. For any "can this resource take this booking?" list.

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
| `.avail__note` (brief 006, D.1.4) | full-width grid column (`grid-column: 1 / -1`), `margin: 0`, `color: var(--c-text)`, `line-height: var(--lh-body)`. Holds the reason text and an optional fix link for the "couldn't check" and "not connected" rows |
| Below 600px | one column: who, then the tag, then the clashes |

Contrast: all existing pairs (f.md §9.5): heading 12.44 / 8.96, muted 5.61 / 5.26, tag ok 4.88 / 6.89, tag warn 5.43 / 7.61.

## States

| State | Tag | Clashes |
|---|---|---|
| Free for every class | `tag--ok`, `check-circle`, `Free for all {n} classes` | none |
| Busy for some | `tag--warn`, `alert-triangle`, `Busy for {k} of {n} classes` | one `li` per clash |
| No accounts at all | the list is not rendered; the box lead says what to do | — |
| Couldn't check (brief 006, D.1.4: the other service — Zoom — didn't answer) | `tag--warn`, `help-circle`, `Couldn't check with Zoom` | none; `.avail__note` holds the reason, what it means, and an optional fix link |
| Not connected (brief 006, D.1.4) | `tag--warn`, `slash`, `Not connected to Zoom` | none; `.avail__note` holds what it means, and a fix link or who to ask |
| Busy, including a clash seen only in the other service (brief 006, D.1.4) | `tag--warn`, `alert-triangle`, `Busy for {k} of {n} classes` | the ordinary `.avail__clashes` list, plus one `li` per outside clash, each on two lines: the class, then `In Zoom: {topic}, {start}–{end}` |

Status is always the word plus the icon; the colour only repeats it. The three brief-006 states use `help-circle` ("we don't know") and `slash` ("switched off / not set up") to read differently from `alert-triangle` ("busy") at a glance, even though all three are `tag--warn`.
