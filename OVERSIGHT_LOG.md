# Oversight Log

This file records oversight episodes on the Polymath TMD project: moments
when the project owner corrected Claude Code's approach, overrode a
decision, or told it that something it produced was wrong. It is research
data for a PhD study on human oversight in agentic software development.

Rows are **appended only**. They are never edited or removed. Each row
corresponds to one git commit carrying `Oversight-*` trailers; see the
"Oversight capture" section of `CLAUDE.md` for the rule, and `/oversight`
(`.claude/commands/oversight.md`) for the command that writes the commit
and this row together.

## Columns

- **Date** — when the commit was made, `YYYY-MM-DD`.
- **Commit** — the short SHA of the commit carrying the `Oversight-*` trailers.
- **Type** — the `Oversight-Type` trailer value.
- **What looked right but was not** — the `Oversight-Trigger` trailer.
- **What I did** — the `Oversight-Action` trailer.
- **Durable** — the `Oversight-Durable` trailer (`yes` / `no`).

A literal `|` inside a cell is escaped as `\|` so the table still parses; the
`Oversight-Trigger` / `Oversight-Action` trailers on the commit itself keep the
raw, unescaped text — the log's escaping is a table-formatting concern only.

| Date | Commit | Type | What looked right but was not | What I did | Durable |
|---|---|---|---|---|---|

Example row (illustration only — not real data, never a table row; the
placeholders below are deliberately not a plausible date or SHA so a script
scanning for `|`-prefixed lines cannot mistake this for a logged episode):

```
| YYYY-MM-DD | <short-sha> | <type> | <Oversight-Trigger, verbatim> | <Oversight-Action, verbatim> | yes\|no |
```

## Checking for a lost episode

The converse of "every row matches a commit" is "every episode commit has a
row." Nothing enforces that automatically — if the episode commit lands but
the session ends before the log commit (step 4 of `/oversight`), the log looks
fine and is silently missing one row. Check by comparing every commit that
carries an `Oversight-*` trailer against the Commit column above:

```
git log --all --format='%h' --grep='^Oversight-Type:'
```

Any short SHA this prints that is not already in the Commit column is a
missing row. Repair it by appending the row (per "Columns" above) and
committing that addition as its own, ordinary commit — never by amending,
rewriting, or otherwise touching the episode commit itself.
