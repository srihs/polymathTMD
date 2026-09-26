# Class rows (`.classrows`)

Origin: brief 011, criterion 8 (the request detail's Classes list gains a `Cancel this class` action per class and a `Cancelled` tag with who, when and why). Use it for any numbered list of a booking's classes where a class can carry its own status or action. The plain `.occurrences` list (`zoom/partials/occurrence_list.html`) stays for read-only lists: the public confirm page, and the cancel confirm page's "will be cancelled" and "stay as they were" lists.

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

- The `with` values are `occurrences` (list of Occurrence), `cancellable_ids` (set of int), `in_progress_id` (int or `None`) and `link_request_pk` (int).
- A row shows at most one of: the action, the `In progress` tag, or the `Cancelled` tag.
- The `when` span is `zoom/partials/class_span.html`. The note's time is `zoom/partials/when.html`. The reason prints with `linebreaksbr`.
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
| `.classrows__note` | `margin: 0 0 var(--space-2); font-size: var(--fs-help); line-height: var(--lh-body); color: var(--c-text); overflow-wrap: anywhere;` |
| `.classrows--cols` | at `min-width: 1400px` only: `columns: 2; column-gap: var(--space-8);`. Below that it's one column, because the action needs room beside the date. At 1024px with the standard sidebar, two columns would squeeze each row |
| Below 600px | `.classrows__action { margin-left: 0; }` The row wraps: the date on line 1, then the action or tag on line 2, starting at the left edge under the date. Without this rule, `margin-left: auto` would push a wrapped action to the far right, away from the date it belongs to |

Contrast: all existing pairs. `--c-text` 12.44 / 6.45, `--c-muted` 5.61 / 5.26, `tag--plain` 5.97 / 7.27 and `tag--note` (existing, checked with the note tag), link `--c-primary-text` 8.86 / 6.31 (f.md §9.5).

## States

| Class state | Row |
|---|---|
| Can be cancelled (`pk in cancellable_ids`) | date, then `Cancel this class` (accessible name includes the date) |
| In progress (`pk == in_progress_id`) | date, then the `tag--note` / `clock` tag `In progress` |
| Cancelled (`cancelled_at`) | muted date, the `tag--plain` / `slash` tag `Cancelled`, then the note `Cancelled by {name} on {when}: {reason}` |
| Held, or anything else (a waiting request, a one-off booking) | date only |

## Behaviour

There's no JS. The action is a plain link to a confirm page.
