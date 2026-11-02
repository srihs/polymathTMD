# Value to copy (`.copy-value`)

Origin: brief 015, Design D.9.1 (the Zoom connection's `Address for Zoom's Event Subscriptions`, which IT pastes into Zoom's App Marketplace). Use it for any one value that a person must copy exactly into another system, such as a URL or an address. It isn't for secrets; those use `.secret` (`secret-value.md`). For now the Zoom connection change page is its only user.

**Why it's new:**

- **`.facts` doesn't fit.** Its values are body-size proportional text, and on a phone a long-press selects a URL one word at a time.
- **`.secret` doesn't fit either,** although it's the closest. It's built so a host key can be read aloud: 28px, with wide letter-spacing. It's hidden when printed, and its name says "secret". A 50-character URL at that size wraps into four or more lines at 400px, and it isn't a secret.

## Anatomy

```html
<dl class="copy-value">
  <dt class="copy-value__label">Address for Zoom's Event Subscriptions</dt>
  <dd class="copy-value__value" translate="no">{{ webhook_address }}</dd>
  <dd class="copy-value__help">In the Zoom app, open Features, then Event Subscriptions, and paste this into Event notification endpoint URL. Tap or click it once to select it all.</dd>
</dl>
```

- **A `dt`/`dd` pair,** so a screen reader reads the label with the value.
- **The help `dd` is optional.** It's a second description of the same term.
- **The value is plain text.** It isn't a link, which would be followed instead of copied, and it isn't an `<input>`.
- **`translate="no"`** stops browser translation from rewriting it.
- **There's no Copy button.** One is recorded as brief 015's follow-up F1: an `app.js` enhancement on a `data-copy` hook, hidden without JS. It would need `https://` for `navigator.clipboard`.

## Tokens

None new. It reuses `--font-mono` (from `secret-value.md`) and existing tokens only.

## Values

| Part | Spec |
|---|---|
| `.copy-value` | `margin: 0 0 var(--space-5); padding: var(--space-4); border: var(--rule) solid var(--c-border); border-radius: var(--radius); background: var(--c-surface-2);` |
| `.copy-value__label` | `margin: 0 0 var(--space-2); color: var(--c-heading); font-weight: var(--fw-medium);`. It reads like a field label |
| `.copy-value__value` | `margin: 0; color: var(--c-heading); font-family: var(--font-mono); font-size: var(--fs-body); line-height: var(--lh-body); overflow-wrap: anywhere; -webkit-user-select: all; user-select: all; cursor: text;`. One click or tap selects the whole value and nothing around it. Safari needs the prefixed property |
| `.copy-value__help` | `margin: var(--space-2) 0 0; color: var(--c-muted); font-size: var(--fs-help); line-height: var(--lh-body);` |
| Print | No rule. Unlike `.secret`, it prints, because it isn't a secret |

It goes in CSS section 5n, beside `.secret`.

**Contrast** (the same pairs `secret-value.md` measured; the verifier confirms them):

- `--c-heading` on `--c-surface-2`: about 12:1 in light and about 8.5:1 in dark.
- `--c-muted` on `--c-surface-2`: about 5.3:1 in light and about 4.9:1 in dark.

## States

There's only one state: shown. It has no hover, focus or "copied" state, and no JS. The page that holds it decides whether it's rendered.

## Accessibility

- It's not focusable. Keyboard-only users can copy it with caret browsing (F7), or read it and type it. Follow-up F1 would add a keyboard path.
- It isn't a link, so WCAG's target-size rules don't apply to it. The selection works by tap or click anywhere on the value.

## Reflow

- It wraps anywhere.
- At 320px, and at 400% zoom, there's no sideways scroll. A long URL simply takes more lines.

## Used by

| Page | Value |
|---|---|
| `zoom/connection_form.html`, change page only (brief 015) | the absolute `zoom:webhook` address for the connection |
