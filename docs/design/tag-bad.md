# Danger tag (`.tag--bad`)

Origin: brief 015, Design D.9.2 (the `Can't be read` state of a Zoom connection's details or webhook secret, and of an account's Zoom connection). It's a tone modifier on the ported `.tag` (section 5g). The tags were ported with `ok`, `warn`, `note`, `plain` and `brand` only.

Use it only for a state where something is broken and needs fixing before work can go on. It's not for a finished record or a deliberate choice: those are `plain`. It's not for "needs attention soon" either: that's `warn`.

**Why it's new.** `Can't be read` means the server's encryption keys no longer open a saved secret, so booking on that connection stops. The change pages show the same state as a `notice--bad` (brief 015, criteria 15 and 19). A list tag must not look calmer than the page it links to, and no existing tag tone says "broken".

## Anatomy

```html
<span class="tag tag--bad"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-alert-octagon"></use></svg>Can't be read</span>
```

- It always carries the `alert-octagon` icon (the same icon as `notice--bad`) **and** a word. Colour is never the only cue.
- Its tone, icon and word are chosen in one partial only: `zoom/partials/connection_tag.html`.
- `zoom/partials/account_tag.html` includes that partial for its `unreadable` state rather than repeating the markup.

## Tokens

None new. It uses the same pair as `.notice--bad`.

## Values

| Part | Spec |
|---|---|
| `.tag--bad` | `background: var(--c-bad-soft); color: var(--c-bad-text);`, on the line after `.tag--brand` in section 5g |

Everything else (size, padding, radius, icon size and no-wrap) is the base `.tag`. In a `datagrid--wrap-tags` table the words may wrap, as other tags do.

**Contrast** at the 10.5px semibold tag size (AA needs 4.5:1; the verifier confirms):

| Mode | Text | Background | Ratio |
|---|---|---|---|
| Light | `--red-700` `#B42318` | `--red-50` `#FFE3E2` | about 5.4:1 |
| Dark | `--red-300` `#F59A94` | `--red-900` `#432A2A` | about 6.2:1 |

## States

None of its own. It's a static label, so it has no hover or focus.

## Used by

| Partial | State | Word |
|---|---|---|
| `zoom/partials/connection_tag.html` (brief 015) | `"unreadable"` (connection details or webhook secret) | `Can't be read` |
| `zoom/partials/account_tag.html`, `kind="zoom"` (brief 015, through the include above) | `"unreadable"` | `Can't be read` |
