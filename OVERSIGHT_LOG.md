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
- **Stage** — the `Oversight-Stage` trailer: when the problem was caught
  (`in-loop` / `acceptance` / `production`).
- **Source** — the `Oversight-Source` trailer: who surfaced it (`self` /
  `agent-critique` / `client` / `stakeholder` / `colleague`).

Stage and Source were added on 2026-09-27, as the last two columns so the rows
already in the table stay exactly as they were written. Rows logged before that
date have no cells in those two columns because their commits carry no such
trailers. Their best reconstruction is kept apart, in "Reconstructed fields" at
the foot of this file, and is never written into the rows themselves.

A literal `|` inside a cell is escaped as `\|` so the table still parses; the
`Oversight-Trigger` / `Oversight-Action` trailers on the commit itself keep the
raw, unescaped text — the log's escaping is a table-formatting concern only.

| Date | Commit | Type | What looked right but was not | What I did | Durable | Stage | Source |
|---|---|---|---|---|---|---|---|
| 2026-09-24 | 5eb2344 | scope | Deleting wrong design files inherited from other projeccts | Dont use current designs directions in the project | yes |
| 2026-09-24 | 791ba6b | scope | Designs were rejected by the end user | client asked to replicate the design like in https://themesbrand.com/minia/layouts-lts/index.html same fonts and same layout with features. | no |
| 2026-09-24 | 7256e9d | correctness | login page design is different than the concept | Match the concept exactly | no |
| 2026-09-25 | fc78691 | business-rule | We dont use django admin as per the client requirement. | a project rule, we dont use Djangoadmin. we should have our own screens and datamodels to handle the requirements | yes |

Example row (illustration only — not real data, never a table row; the
placeholders below are deliberately not a plausible date or SHA so a script
scanning for `|`-prefixed lines cannot mistake this for a logged episode):

```
| YYYY-MM-DD | <short-sha> | <type> | <Oversight-Trigger, verbatim> | <Oversight-Action, verbatim> | yes\|no | <stage> | <source> |
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

## Reconstructed fields

**Reconstructed, not recorded.** The four episodes below were committed before
`Oversight-Stage` and `Oversight-Source` existed (2026-09-27). Their commits
carry only four trailers, and those commits are never amended or rewritten.
The Stage and Source values here are Claude Code's best reconstruction from the
session record. Nobody entered them at the time, and the owner hasn't confirmed
them. Treat them as lower-confidence than any recorded trailer, and keep them
separate from recorded data in any analysis.

Written as a list rather than a table so that nothing scanning `|`-prefixed
lines for logged episodes can mistake these for rows of the log.

- **5eb2344**: Stage `in-loop`, Source `self` (both reconstructed). The owner stopped the design-direction work (task 002) from drawing on the earlier `v5-tasks` prototype while it was still being built. Nothing had been handed over yet.
- **791ba6b**: Stage `acceptance`, Source `client` (both reconstructed). The client reviewed the five delivered design directions and rejected all of them.
- **7256e9d**: Stage `in-loop`, Source `self` (both reconstructed). The owner saw that the ported sign-in page didn't match the approved concept while task 004 was being built, before anything reached the client.
- **fc78691**: Stage `in-loop`, Source `self` (both reconstructed). The owner stated the no-Django-admin rule after reviewing brief 005's build, before handover. Uncertain: the trigger says "as per the client requirement", so the client may have raised it first. If so, the Source would be `client` and the Stage possibly `acceptance`.
