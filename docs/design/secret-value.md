# Secret value (`.secret`)

Origin: brief 011, D11 and criterion 42 (the Zoom account's host key, shown once on its own page as the IT desk's fallback). Use it for any one value that a person must read out or type somewhere else exactly: large, monospaced and easy to select. For now the host key reveal page is its only user.

**Why it's new:** `.facts` values are body-size proportional text. A host key is read digit by digit over the phone. It needs a size and a font where `1`, `l` and `7`, and `0` and `O`, can't be confused, and nothing else in the kit is like that.

## Anatomy

```html
<div class="secret">
  <p class="secret__label">Host key</p>
  <p class="secret__value" translate="no">{{ host_key }}</p>
</div>
```

- The value is printed **once**, as plain text. It isn't in an `<input>`, which a password manager or autofill might capture, or in a `title` or `aria-label`.
- `translate="no"` stops browser translation from rewriting it.
- There's no copy button. The guidance is to read it over the phone, not paste it into a message.

## Tokens

New, in block 1b (type), next to `--font`:

| Token | Value |
|---|---|
| `--font-mono` | `ui-monospace, "Cascadia Mono", Consolas, "SF Mono", Menlo, monospace` |
| `--fs-secret` | `1.75rem` (28px at the default size) |

Everything else reuses tokens that already exist.

## Values

| Part | Spec |
|---|---|
| `.secret` | `margin: 0 0 var(--space-5); padding: var(--space-5); border: var(--rule) solid var(--c-border); border-radius: var(--radius); background: var(--c-surface-2);` |
| `.secret__label` | `margin: 0 0 var(--space-2); font-size: var(--fs-help); color: var(--c-muted);` |
| `.secret__value` | `margin: 0; font-family: var(--font-mono); font-size: var(--fs-secret); font-weight: var(--fw-semibold); line-height: var(--lh-tight); letter-spacing: 0.12em; color: var(--c-heading); overflow-wrap: anywhere; user-select: all;` (one click or tap selects the whole value, and nothing around it) |
| Print (`@media print`, section 9) | `.secret__value { visibility: hidden; }`, so the key isn't printed by accident. The label stays, so the printout shows the page was a key page |

Contrast: `--c-heading` on `--c-surface-2` is about 12:1 in light (`--grey-850` on `--grey-50`) and about 8.5:1 in dark (`--grey-300` on `--grey-820`). `--c-muted` on `--c-surface-2` is about 5.3:1 in light and about 4.9:1 in dark. The verifier confirms these.

## States

There's only one state: shown. The page that holds it decides whether it's rendered at all.

## Reflow

At 320px a 10-character key at 28px monospace with the letter spacing is about 200px wide, which fits the column. A longer value wraps anywhere rather than scrolling sideways.

## Used by

| Page | Value |
|---|---|
| `zoom/host_key_reveal.html` (brief 011) | the account's host key |
