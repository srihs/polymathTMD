# Danger button (`.button--danger`)

Origin: brief 011 (cancel a booking), criteria 7 and 35. The kit had no destructive button, so this note defines it. Criterion 35 now pins it as `.button--danger`, used only for the confirm page's final button, with the entry links staying `button--secondary`. Use it for the **one final button that destroys something and can't be undone**, on a page whose only job is to confirm that act (the cancel confirm page). Don't use it for links that lead to a confirm page, or anywhere else. Those use `button--secondary`, as `Reject this request` does.

**Why it's new:** `button--primary` is crest purple, the colour of every "go ahead" action in the app (approve, save, send). A cancel that deletes a meeting in Zoom and emails the requester needs to look different from those at a glance. The words carry the meaning. The red fill only repeats it, so it's never colour alone.

## Anatomy

```html
<button class="button button--danger" type="submit" data-busy-text="Removing it from Zoom…">Cancel and email the requester</button>
```

It has the same box as every `.button`: 44px minimum height, `--fs-body`, radius `--radius`, inline-flex, and an optional leading icon.

## Tokens

New palette value, in the **first** `:root` block (1a), next to the other reds:

| Token | Value | Why |
|---|---|---|
| `--red-800` | `#912018` | the hover fill, one step darker than `--red-700` |

New semantic tokens, in block 1c (light). They're **not** overridden in 1d (dark), because the same fill works in both modes:

| Token | Value |
|---|---|
| `--c-danger` | `var(--red-700)` |
| `--c-danger-hover` | `var(--red-800)` |
| `--c-on-danger` | `var(--white)` |

## Values

| Part | Spec |
|---|---|
| `.button--danger` | `border-color: var(--c-danger); background: var(--c-danger); color: var(--c-on-danger);` There's no shadow: `--shadow-primary` is purple and belongs to the primary button |
| `:hover` | `border-color: var(--c-danger-hover); background: var(--c-danger-hover);` |
| Focus | the global focus ring (`--c-focus`, 2px, offset), unchanged |
| Busy (`aria-disabled="true"`) | unchanged colours and `cursor: progress` (`busy-button.md`) |
| Below 600px, in `.form-actions` | full width, like every button there (existing rule) |

Place the rules in section 5d, after `.button--secondary:hover`.

## Contrast

| Pair | Ratio | Needed |
|---|---|---|
| `--white` on `--red-700` (idle, both modes) | about 6.6:1 | 4.5:1 (text) |
| `--white` on `--red-800` (hover) | about 8.7:1 | 4.5:1 |
| Fill against `--c-surface`, light | about 6.6:1 | 3:1 (non-text) |
| Fill against `--c-surface`, dark (`--grey-900`) | about 2:1 | none: the white label identifies the control, exactly as with `button--primary` in dark mode |

The verifier confirms these with a checker.

## States

| State | Look |
|---|---|
| Idle | red fill, white label |
| Hover | darker red fill |
| Focus | the global ring |
| Busy | same colours, busy text, `cursor: progress` |

There's no disabled look. A page that can't perform the act doesn't render the button at all.

## Copy rule

The label says the whole act, verb first, the same as `Approve and email the link` and `Reject and email the reason`. For example, `Cancel and email the requester`. It's never just `Yes`, `OK` or `Confirm`.

## Used by

| Page | Button |
|---|---|
| `zoom/cancel_confirm.html` (brief 011) | `Cancel and email the requester`, beside the safe way out, a `button--quiet` link that names what's kept: `Keep the booking` or `Keep the class` |
