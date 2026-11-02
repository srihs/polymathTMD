# Class rows (`.classrows`)

Origin: brief 011, criterion 8 (the request detail's Classes list gains a `Cancel this class` action per class and a `Cancelled` tag with who, when and why). Amended by brief 012, criterion 6: a `Move this class` action beside the cancel action, and a `Moved` tag and note. Amended by brief 013: the notes say when a change was made directly in Zoom. Use it for any numbered list of a booking's classes where a class can carry its own status or action. The plain `.occurrences` list (`zoom/partials/occurrence_list.html`) stays for read-only lists: the public confirm page, and the cancel confirm page's "will be cancelled" and "stay as they were" lists.

**Why it's new:** `.occurrences` is one line of text per class, laid out in CSS columns. It has no room for a tag, a 44px action, or a reason on a second line. `.worklist` rows aren't numbered, and they're built around a reference link rather than a date. `.avail` is one row per account.

## Anatomy

Partial `zoom/partials/class_rows.html`, included with `only`:

```html
<ol class="classrows classrows--cols">                                   <!-- --cols only when more than 6 classes -->
  <li class="classrows__item">                                           <!-- a cancellable class -->
    <div class="classrows__row">
      <span class="classrows__when"><time datetime="…">Mon 12 Oct 2026</time>, 8:30 am to 11:30 am</span>
      <a class="classrows__action" href="{% url 'zoom:cancel_class' link_request_pk occurrence.pk %}">Cancel this class<span class="visually-hidden"> on Mon 12 Oct 2026</span></a>
    </div>
  </li>
  <li class="classrows__item">                                           <!-- in progress (only with in_progress_id; brief 011 criterion 8, D13 G1) -->
    <div class="classrows__row">
      <span class="classrows__when">…</span>
      <span class="tag tag--note"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-clock"></use></svg>In progress</span>
    </div>
  </li>
  <li class="classrows__item classrows__item--cancelled">                <!-- cancelled -->
    <div class="classrows__row">
      <span class="classrows__when">…</span>
      <span class="tag tag--plain"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-slash"></use></svg>Cancelled</span>
    </div>
    <p class="classrows__note">Cancelled by Nimal Perera on <time datetime="…">Mon 28 Sep 2026</time>, 10:04 am: The teacher is away that week.</p>
  </li>
  <li class="classrows__item">…</li>                                    <!-- held or not cancellable: the time only -->
</ol>
```

- The `with` values are `occurrences` (list of Occurrence), `cancellable_ids` (set of int), `movable_ids` (set of int; brief 012), `in_progress_id` (int or `None`) and `link_request_pk` (int).
- The `when` span is `zoom/partials/class_span.html`. The notes' times are `zoom/partials/when.html`. The reason prints with `linebreaksbr`.

**What a row shows** (amended by brief 012, which replaced 011's rule that a row shows "at most one of" the action, the `In progress` tag or the `Cancelled` tag). Parts appear in this order:

| Part | When | Markup |
|---|---|---|
| Date | always | `span.classrows__when`. For a moved class it's the **new** time. The old time isn't stored, so it's never shown |
| `Moved` tag (brief 012) | `moved_at` and **not** `cancelled_at` | `span.tag.tag--plain` with `calendar` and `Moved` |
| `In progress` tag | `pk == in_progress_id` | `span.tag.tag--note` with `clock` |
| `Cancelled` tag | `cancelled_at` | `span.tag.tag--plain` with `slash` |
| `Move this class` (brief 012) | `pk in movable_ids` | `a.classrows__action` → `zoom:move_class link_request_pk occurrence.pk`, then visually hidden ` on {date}` |
| `Cancel this class` | `pk in cancellable_ids` | `a.classrows__action` → `zoom:cancel_class`, then visually hidden ` on {date}` |
| Moved note (brief 012) | `moved_at` and not `moved_in_zoom`, cancelled or not (it's history) | `p.classrows__note`: `Moved by {name} on {when}.` |
| Moved note, in Zoom (brief 013) | `moved_in_zoom` | `p.classrows__note`: `Moved directly in Zoom. Copied here on {when}.` (`when` = `moved_at`, when the app copied it, not when Zoom was changed) |
| Cancelled note | `cancelled_at` and not `cancelled_in_zoom` | `p.classrows__note`: `Cancelled by {name} on {when}: {reason}` |
| Cancelled note, in Zoom (brief 013) | `cancelled_in_zoom` | `p.classrows__note`: `Cancelled directly in Zoom. Copied here on {when}.` The stored reason isn't printed: it's the same words |

- A cancelled or in-progress class is never in `movable_ids` or `cancellable_ids`. So a row has either a status tag and no actions, or up to two actions. `Moved` is the one tag that can sit beside the actions.
- `Moved` is hidden on a cancelled class, so the row keeps a single status word. Its `Moved by …` note still shows, before the cancelled note, so the notes read in the order things happened.
- `Move this class` comes before `Cancel this class`: the less final action comes first in reading and tab order.
- A one-off booking has an empty `cancellable_ids` (the whole-booking cancel covers its one class), but its class can be in `movable_ids`. So its single row shows only `Move this class`.
- **Where a change came from** (brief 013) is decided on the model, never in the template: `Occurrence.moved_in_zoom` and `cancelled_in_zoom` are true when the timestamp is set and the `*_by` user is empty. The tags don't change: `Moved` and `Cancelled` describe the class's state, whoever changed it. Only the note says the source.
- Keep whitespace between the spans in the markup, so the accessible names have their spaces.

## Values

| Part | Spec |
|---|---|
| `.classrows` | `margin: 0; padding-left: var(--space-6);` with decimal markers, the same as `.occurrences`, so the numbers still read "class 3 of 8" |
| `.classrows__item` | a normal `list-item` (the marker must survive). `break-inside: avoid`. `+ .classrows__item` gets `margin-top: var(--space-1)` |
| `.classrows__row` | `display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-1) var(--space-3); min-height: var(--target);` |
| `.classrows__when` | `--c-text`. It's never struck through: a line through a date makes it harder to read |
| `.classrows__item--cancelled .classrows__when` | `--c-muted`. The tag's word and icon carry the meaning; the muted colour only repeats it |
| `.classrows__action` | `display: inline-flex; align-items: center; min-height: var(--target); margin-left: auto;` with the ported link colour and underline. It's 44px tall at every width, not just on phones, because it sits in a dense list |
| `.classrows__action ~ .classrows__action` (brief 012) | `margin-left: 0;` Only the first action is pushed right, and a second one sits beside it, separated by the row's 12px column gap. Their 44px hit areas don't overlap. Place the rule straight after `.classrows__action` |
| `.classrows__note` | `margin: 0 0 var(--space-2); font-size: var(--fs-help); line-height: var(--lh-body); color: var(--c-text); overflow-wrap: anywhere;` |
| `.classrows--cols` | at `min-width: 1400px` only: `columns: 2; column-gap: var(--space-8);`. Below that it's one column, because the action needs room beside the date. At 1024px with the standard sidebar, two columns would squeeze each row. A row with a date, the `Moved` tag and both actions (about 560px) wraps inside a column: the date and tag on line 1, then the actions. That's accepted |
| Below 600px | `.classrows__action { margin-left: 0; }` The row wraps: the date on line 1, then the actions or tag on line 2, starting at the left edge under the date. Without this rule, `margin-left: auto` would push a wrapped action to the far right, away from the date it belongs to |

Contrast: all existing pairs. `--c-text` 12.44 / 6.45, `--c-muted` 5.61 / 5.26, `tag--plain` 5.97 / 7.27 and `tag--note` (existing, checked with the note tag), link `--c-primary-text` 8.86 / 6.31 (f.md §9.5). Brief 012 adds no new pair: `Moved` is `tag--plain`.

## States

| Class state | Row |
|---|---|
| Can be moved and cancelled (in both `movable_ids` and `cancellable_ids`; brief 012) | date, then `Move this class`, then `Cancel this class` (each accessible name includes the date) |
| Can be moved only (a one-off booking's class; brief 012) | date, then `Move this class` |
| Can be cancelled only | date, then `Cancel this class` |
| Moved (`moved_at`; brief 012) | the new date, the `tag--plain` / `calendar` tag `Moved`, any actions it still has, then the note `Moved by {name} on {when}.`, or the Zoom note `Moved directly in Zoom. Copied here on {when}.` (brief 013) |
| In progress (`pk == in_progress_id`) | date, then the `tag--note` / `clock` tag `In progress` (plus `Moved` and its note if it was moved) |
| Cancelled (`cancelled_at`) | muted date, the `tag--plain` / `slash` tag `Cancelled`, then the moved note if it was moved, then the note `Cancelled by {name} on {when}: {reason}`, or the Zoom note `Cancelled directly in Zoom. Copied here on {when}.` (brief 013) |
| Held, or anything else (a waiting request) | date only (plus `Moved` and its note if it was moved) |

## Behaviour

There's no JS. Each action is a plain link: `Cancel this class` to a confirm page, and `Move this class` to the move form (brief 012).
