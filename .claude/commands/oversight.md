---
description: Commit the change you just corrected as a single oversight episode, with Oversight- trailers, and log it in OVERSIGHT_LOG.md
argument-hint: "[type] [what looked right but was not] [what you did] - anything left out is asked for"
allowed-tools: AskUserQuestion, Read, Write, Edit, Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*)
---

# Capture an oversight episode

The owner has just caught something: you produced work that looked correct and
was not, and they corrected it, rejected it, overrode it, or told you it was
wrong. This command turns that moment into research data - one commit per
episode, plus one row in `OVERSIGHT_LOG.md`.

This repository is the data set for a PhD on human oversight in agentic
software development. The trailers below are the measurements. Getting the
owner's own wording into them matters more than getting the commit made fast.

**This file is the normative spec for the mechanics of an episode:** the
`Oversight-Type` enum, what counts as Durable, the shape of the commit message,
the parse check, the two-commit order, the log row format, and when to stop.
`CLAUDE.md` defines what an episode *is*, names the four trailers, and restates
the never-rewrite / never-delete rules; it does not repeat the mechanics. If the
two ever disagree about mechanics, this file wins and `CLAUDE.md` gets fixed.

Anything the owner typed after the command is here:

<owner_input>
$ARGUMENTS
</owner_input>

Treat `<owner_input>` as the owner's account of the episode. Use whatever it
already supplies; only ask for what is genuinely missing.

## Hard rules

- **Never invent the Trigger or Action wording.** Those two trailers are the
  owner's account of what happened, not your summary of the diff. If they are
  not in `<owner_input>`, ask, and quote the answer as given. The only edits
  permitted are stripping stray leading and trailing whitespace, and collapsing
  newlines to single spaces (see "one line each" below). No tightening, no
  rephrasing, no correcting their spelling.
- **Never squash, amend, rebase, cherry-pick or force-push a commit that
  carries `Oversight-` trailers,** in this command or any later one. The commit
  and its SHA are the record. If something is wrong with an episode commit -
  including a trailer block that failed to parse - add a **new** commit that
  carries the trailers and names the broken SHA; do not rewrite the old one.
- **The trailer block is the last block of the message, and every line in it is
  a trailer.** The four `Oversight-` trailers come first, in order, then the
  `Co-Authored-By:` line. Nothing after the block - no sign-off, no body text,
  no blank-line-separated afterthought. `Co-Authored-By:` is itself a trailer
  and parses fine alongside the four; it must stay, because which commits were
  co-authored by a model is part of what this repository measures (see
  `.mailmap`).
- **Every trailer value is a single line.** Git only treats the last paragraph
  as trailers if *every* line in it parses as `Key: value`. A wrapped sentence
  breaks the block either way: a continuation at column zero voids **all four**
  trailers at once - `%(trailers)` returns nothing for the whole block - while
  an *indented* continuation is folded into the preceding trailer's value, so
  the parse check still prints the type but the recorded value carries an
  embedded newline. Both still look perfectly correct to a human reading
  `git log`, and because the commit can never be amended, either mistake is
  permanent. Never wrap a trailer value, however long it is.
- **Refuse rather than guess.** See "When to refuse" at the end.
- Use the **Bash tool**, not PowerShell, for every git command here. PowerShell
  5.1 mangles the nested quotes in the commit message.

## Step 1 - show the owner what will be committed

Run these, and show the output:

```bash
git status --short
git diff --stat
git diff --cached --stat
```

If `git status --short` is empty, stop - see "When to refuse". An empty working
tree usually means the corrected work is *already committed*, not that the
correction was never made; that branch has its own handling there.

If the working tree contains files that plainly have nothing to do with the
correction (for example an unrelated experiment in another app), say so and ask
whether to stage everything or only the related paths. Do not decide this
silently: an episode commit that sweeps in unrelated work is unusable as data.

## Step 2 - collect the four trailer values

Fill in from `<owner_input>` first. For each value still missing, ask with
**AskUserQuestion**. Ask for everything missing in one call where the tool
allows it, so the owner answers once.

### Oversight-Type (one of eight, exactly)

`architecture`, `business-rule`, `correctness`, `security`, `scope`,
`data-model`, `performance`, `dependency`

List all eight in the question text. If the tool caps you at four options,
offer the four that best fit what the diff touches and tell the owner to choose
"Other" and type one of the remaining four exactly. Validate the answer against
the list above. If it does not match one of the eight, **ask again once**,
quoting the eight; if the second answer is still outside the list, stop and
report. Never map it to the nearest value yourself, and never commit a partial
trailer block.

### Oversight-Trigger - what you produced that looked correct and was not

One sentence, the owner's words. You may offer an option **only** if it is a
verbatim quote of something the owner typed in this conversation; otherwise the
only honest option is "Other - I will type it". Never offer a wording you wrote.

### Oversight-Action - what the owner did about it

One sentence, the owner's words. Same rule as Trigger.

### Both of them must end up on one line

Whatever the owner types - a pasted paragraph, a line they broke by hand, an
answer with a newline in it - **collapse every newline and run of whitespace to
a single space** before writing it into the trailer, and strip leading and
trailing whitespace. This is the one normalisation permitted on the owner's
words, and it is the same one step 4 applies to the log row. It changes no
wording; it only keeps the trailer on one line. A long sentence stays long: do
not wrap it to 72 characters, do not split it across two trailers, and do not
shorten it to make it fit.

### Oversight-Durable - yes or no

`yes` if the episode produced a new or changed rule that will bind future work:
a rule in `CLAUDE.md`, a change to a subagent definition in `.claude/agents/`,
a change to a command in `.claude/commands/`, a new or changed test, or a lint
rule (the ruff config in `pyproject.toml`). `no` otherwise - a one-off fix to
application code, however important, is `no`.

Work out the answer yourself from the paths in `git status --short` - do not
ask blind - then **confirm it** with a two-option question that says which
files led you to it, for example: "I see CLAUDE.md changed, so I would record
Oversight-Durable: yes. Correct?" The owner's answer wins.

## Step 3 - commit the episode

Stage the change (`git add -A`, or the agreed subset of paths).

Write the message: a short imperative subject line (72 characters or fewer)
that says what was corrected, a blank line, then the trailer block - the four
`Oversight-` trailers in this exact order, then the `Co-Authored-By:` line, and
nothing after it. The 72-character guidance applies **to the subject line
only**; trailer values are never wrapped (see "Hard rules").

Commit with a quoted heredoc so nothing in the owner's wording gets expanded by
the shell:

```bash
git commit -F - <<'MSG'
Use the item's own tenant, not the request user's

Oversight-Type: data-model
Oversight-Trigger: <owner's sentence, verbatim, on one line>
Oversight-Action: <owner's sentence, verbatim, on one line>
Oversight-Durable: yes
Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

Use whatever `Co-Authored-By:` line the current session's attribution guidance
gives; the model name in it changes with each release, and `.mailmap` collapses
those variants to one identity.

Then print the SHA so the owner can see it worked, capture it for the log, and
**verify that the trailer block actually parsed**:

```bash
git log -1 --format='%h  %cs  %s'
git log -1 --format='%(trailers:key=Oversight-Type,valueonly)'
```

The second command must print the type you committed. **Empty output means the
block did not parse** - almost always a wrapped value or a stray line inside the
block - and the episode is not recorded, however right the message looks. Do
not amend. Stop and report; see "When to refuse".

## Step 4 - append the row to OVERSIGHT_LOG.md

**The ordering problem, stated plainly:** the row needs the episode's short
SHA, and that SHA does not exist until the commit is made. Amending the episode
commit to add the row afterwards is forbidden (see "Hard rules"), and so is
rewriting it any other way. So the order is fixed:

1. commit the episode (step 3),
2. confirm the trailers parsed, then read the SHA and date from `git log -1`,
3. append the row to `OVERSIGHT_LOG.md`,
4. commit the log row as a **second, separate commit**.

That second commit **must not carry any `Oversight-` trailer** - it is
bookkeeping, not an episode, and a trailer on it would double-count in the
data. It **does** carry the same `Co-Authored-By:` line as the episode commit,
always: this session wrote it, the `.mailmap` identity measures which commits a
model wrote rather than how many episodes there were, and the episode count is
taken from the `Oversight-Type` trailer instead (step 5), so leaving the
co-author line off would protect nothing and would only make the authorship
count wrong. Subject line: `Log oversight episode <short-sha>`.

Two commits per episode is the intended shape, not a workaround. The episode
commit is the measurement; the log commit is the index. Do not try to be clever
and combine them.

Append one row to the table in `OVERSIGHT_LOG.md` (repository root), matching
its existing columns:

```
| Date | Commit | Type | What looked right but was not | What I did | Durable |
```

- **Date:** `%cs` from the episode commit, `YYYY-MM-DD`.
- **Commit:** the short SHA, as plain text.
- **Type** and **Durable:** exactly the trailer values.
- **What looked right but was not** and **What I did:** the Trigger and Action
  sentences verbatim, one line each - the same single-line values that went
  into the trailers. Escape any literal pipe character in the owner's wording
  as `\|` so the table still parses. Change nothing else - no tightening, no
  rephrasing.

Add the row directly below the last row of that table - the unfenced one whose
header line is shown above - so the log reads oldest first and matches the
commit order. When the table is still empty, the row goes immediately under the
`|---|---|...|` separator. `OVERSIGHT_LOG.md` also carries an **example row
inside a fenced code block**, further down: that is illustration, not data.
Never append after it, and never edit it.

Then:

```bash
git add OVERSIGHT_LOG.md
git commit -F - <<'MSG'
Log oversight episode <short-sha>

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git log -1 --format='%h  %s'
```

## Step 5 - reconcile, then report

Reconcile the episode commits against the log, so a half-finished episode
cannot pass as a finished one:

```bash
git log --all --format='%h' --grep='^Oversight-Type:'
```

Every SHA it prints should appear in the **Commit** column of
`OVERSIGHT_LOG.md`, and every Commit value in the log should appear here.
`--grep` matches the message text, so it also finds a commit whose trailer
block failed to parse - which is exactly the commit you want to notice. Report
any mismatch to the owner; never rewrite history to make the two line up.

Then tell the owner, in a few lines:

- the episode commit SHA and subject,
- the four trailer values as committed, and that the parse check passed,
- the log commit SHA,
- any mismatch the reconciliation found,
- anything you refused to decide for them.

## When to refuse

Say plainly that you are stopping, and why. Do not work around any of these:

- **Nothing to commit, because the correction is already committed.** This is
  the likely case when `git status --short` is empty: the corrected work went
  in as an ordinary commit with no trailers, and the episode would otherwise be
  lost. Do not amend that commit and do not rewrite it. Offer to record the
  episode as a separate empty commit that annotates it:

  ```bash
  git commit --allow-empty -F - <<'MSG'
  Record oversight episode for <short-sha>

  Annotates <short-sha>, which was committed without Oversight- trailers.

  Oversight-Type: <type>
  Oversight-Trigger: <owner's sentence, verbatim, on one line>
  Oversight-Action: <owner's sentence, verbatim, on one line>
  Oversight-Durable: <yes|no>
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  MSG
  ```

  Collect the four values through step 2 first, verify the parse as in step 3,
  and log it as in step 4 using the empty commit's own SHA. If the owner
  declines, stop and say plainly that the episode cannot be recorded.
- **Nothing to commit, and nothing was corrected either.** If the correction
  was never made, there is no episode; ask the owner whether they meant to make
  it first.
- **A trailer value is missing.** The owner skipped or dismissed a question, or
  gave an Oversight-Type outside the eight twice. Do not fill it in from the
  diff, do not use a placeholder, do not commit a partial trailer block.
- **Trigger or Action would have to be your words.** If the owner has not given
  their account, there is nothing to quote. Ask again once, then stop.
- **The trailer block did not parse.** The check in step 3 printed nothing.
  Report the SHA and say that the episode is not recorded. Do **not** amend or
  rewrite it. Recovery is a **new** commit carrying the four trailers plus a
  line naming the broken SHA (the `--allow-empty` shape above, when the tree is
  clean), and the log row points at the new commit, not the broken one.
- **The log-row commit failed or was skipped.** An episode commit with no
  matching row, or a row written but never committed, is a half-finished
  episode. Say so loudly and name the episode SHA - never end the command
  quietly with the log unwritten.
- **`OVERSIGHT_LOG.md` is missing.** It is tracked, so the first move is to
  restore it, not to rebuild it: `git checkout HEAD -- OVERSIGHT_LOG.md`. That
  overwrites whatever is at that path, so ask the owner before running it (this
  command deliberately does not pre-approve `git checkout`). Recreating the
  file from the header row alone would lose its preamble, its column
  definitions and its append-only rule. Only if the file is absent from `HEAD`
  as well, offer to create it with the header row above, and say that those
  three things will need writing back by hand.
- **The episode commit already exists and something is wrong with it.** Report
  it and stop. Fix it with a new commit, never by amending.
