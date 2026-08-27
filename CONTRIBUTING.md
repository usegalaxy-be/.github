# Working with issues, pull requests, and the project board

This describes how we track and plan work across usegalaxy-be repositories. It applies org-wide (this file is the default for any repo that doesn't have its own).

## Where work is tracked

All issues and PRs across the tracked repos (infrastructure-playbook, usegalaxy-be-tools, galaxytools, usegalaxy-be-doc, usegalaxy-be.github.io, infrastructure, pulsar-deployment, metrics_internal) flow into two project boards:

- **UseGalaxy.be Infrastructure** (execution board): day-to-day and cycle-level tracking of individual issues and PRs.
- **Compute Team Roadmap** (strategic board): pillars, objectives, and epics (quarterly).

Most contributors only need the execution board. The roadmap board is for planning and reporting.

## Issue types

- **Bug** - something broken
- **Feature** - new capability
- **Task** - routine, scoped work
- **Epic** - a multi-part initiative, broken into sub-issues (use GitHub's native sub-issues, not a checklist inside the issue body)

If an issue is accumulating a checklist of more than 2-3 sub-parts inside its own body, that's a sign it should be an Epic with real sub-issues instead. Sub-issues get their own Status/Priority/Size; the parent Epic shows a automatic completion status.

Epics don't get a Size or an Iteration of their own - that would contradict the reason they're an Epic (too big for one iteration/one size bucket). Each sub-issue is sized and scheduled individually; the Epic's "how big" signal is the sub-issue completion rollup, not a Size value.

Epics *do* get their own Start/Target dates - set independently, not derived from anything, at whatever grain makes sense for the initiative (weeks to a quarter). This is the one exception to "dates come from Iteration": Epics have no Iteration, but the Roadmap view needs something to place them on a quarterly timeline, and a multi-cycle initiative's real timeframe is a judgment call, not a mechanical derivation. Set it during triage or whenever the Epic is created, and revisit it the way Priority gets revisited - it's an estimate, not automated.

It's fine, and often more honest, for a non-committed Epic to have **no** Target date at all rather than a fabricated one. A blank Target date correctly says "on the radar, not committed" - only set a real one when there's an actual driver (a leadership commitment, an external deadline, something else depending on it). Don't invent a quarter just to make the Roadmap look populated.


## Project board fields

**Status**: Backlog / In Progress / Blocked / Done. Kept deliberately small so it can be driven by automation (see below).

**Priority**: P0 / P1 / P2. P0 is reserved for genuine escalations - never set automatically. As a starting default: goal-linked work (has a Pillar) defaults to P1, reactive work defaults to P2. Adjust as needed during triage.

Unlike Size and Iteration, Priority applies to Epics too - it's about relative importance, not execution scheduling, so it isn't tied to fitting in one cycle. An Epic's Priority is what should drive which initiatives get staffed; a sub-issue's Priority is more about ordering work within an Epic that's already been deemed worth doing.

**Size**: XS-XL. Set when an item is triaged into an iteration, not before. A single (non-Epic) issue should be scoped to fit inside **one** iteration (2 weeks) - not planned across two from the start. If it can't realistically finish in one iteration, that's the signal to convert it to an Epic and split it into sub-issues, not to plan on rolling it into a second cycle. Rolling over is for the exceptional case where something unexpectedly slips, not a normal planning outcome - see the Start/End date note below.

**Iteration**: 2-week cycles, Monday to Sunday. Represents "what cycle is this planned for," not a deadline. Only items actively planned for the current or next cycle should have one set.

**Pillar / Objective**: which 2026 goal (from the goals document) this work serves, if any. Three states matter, and the difference between the first two is deliberate:
- *Blank* = not yet triaged
- *Reactive / not goal-linked* = triaged, confirmed this doesn't serve a stated objective - covers both spontaneous break-fix work and deliberately planned work (e.g. a scheduled upgrade) that just isn't tied to a 2026 goal. Both are expected, not a problem; this tag is about goal-linkage, not about whether the work was planned or matters.
- *A pillar set* = triaged, goal-linked

Objective options in the field picker show the Key Results under it. A Key Result that's a concrete deliverable becomes an Epic tagged with that Objective.

**Start date / End date**: for regular (non-Epic) issues, only set for items with an Iteration, derived from that iteration's window, kept in sync automatically. Epics are the exception - see Issue types above, their dates are set independently rather than derived. When an item gets a new Iteration and already has a Start date, only End moves forward - Start is preserved so the Roadmap bar visibly stretches across iterations instead of quietly resetting to looking on-track every cycle. If Start is blank (the item never actually got started - see below), both Start and End are set fresh to the new iteration's window.

## Triage

Uses the existing weekly Monday meeting - no separate meeting needed - which alternates between two modes depending on whether it falls on an iteration boundary (every other week; the automated sweep already runs Monday morning, so the board's clean before anyone sits down either week):

**Iteration-boundary Monday** (full triage):
1. Review items the automation bounced back to Backlog (see below) - still the priority? Pull into the iteration starting now. Not right now? Leave in Backlog. Turned out bigger than expected? Split into an Epic instead of re-entering it as-is.
2. Finalize the iteration that's starting: review what was staged as "next" two weeks ago, confirm it still makes sense given current capacity and priorities (this is a real review, not a rubber stamp - things change in two weeks), adjust Size/Priority, lock it in.
3. Triage new Backlog items: the board's **Triage** view (Status=Backlog, Pillar=blank, sorted oldest-first). For each, either set a Pillar/Objective and Priority, or mark it Reactive/not goal-linked. Pull top-priority items into the now-current iteration up to the In Progress column's limit (a soft cap, see column settings); stage a few likely candidates into "next" for visibility, to be properly reviewed at the following iteration boundary.
4. Epic check-in: anything the "no sub-issues after 2 weeks" nudge has flagged, or any Epic close to fully rolled up.

**Mid-iteration Monday** (business as usual): discuss top-priority items, triage any new issues into Backlog (Pillar/Objective/Priority). Nothing iteration-specific - the current iteration is already locked and running.

This is about the execution board (`#8`) and its weekly-to-biweekly rhythm. The strategic roadmap (`#10`, Pillar/Objective progress) runs on a much slower cadence - monthly or quarterly - since "is this Objective on track" isn't a question that changes week to week.

Only genuinely urgent work (something's broken or blocking users right now) skips this and moves straight from Backlog to In Progress. Everything else goes through iteration planning, whether or not it's goal-linked - a deliberately scheduled upgrade or migration is triaged, sized, and scheduled into a cycle the same as goal-linked work, even though it'll end up tagged Reactive/not goal-linked. That tag means "doesn't serve a stated objective," not "wasn't planned" or "isn't important."

There's a third lane besides "urgent, skips the queue" and "goal-linked, competes for iteration slots on Priority": small, cheap, non-urgent, non-goal-linked work (a stale doc fix, a one-line cleanup) that will *always* lose a priority comparison against anything else and would otherwise sit in Backlog forever - which is usually exactly what happens to it under a strict priority-driven queue. Rather than forcing these through Size/Iteration scheduling they have no real timing signal for, mark them with the `opportunistic` label: picked up whenever someone has spare capacity between other things, with no formal commitment to when and no Iteration assigned at all. Unlike `blocked`, this label has no automation behind it - it's purely a marker, not something that needs to gate a workflow. If something's sat untouched for a long time even as "opportunistic" and nobody's ever picked it up, that's a legitimate signal to just close it rather than keep carrying it.

The room for this comes from how the WIP limit is set, not from a quota. Keep iteration planning deliberately below the team's full theoretical capacity rather than filled to the brim - that slack is where opportunistic and unplanned reactive work naturally lands without any bookkeeping. If opportunistic items still never get touched despite the slack existing, a soft prompt in triage ("anything small worth clearing this cycle?") is enough - not a hard "at least one per iteration" rule, which would turn a zero-ceremony lane into its own obligation.

Sequencing *goal-linked* work across Pillars/Objectives that don't themselves imply an order isn't something execution triage is meant to solve either - `goals.md` says what's legitimate to work on, not when. That call belongs to the monthly/quarterly roadmap review: periodically decide which 2-3 Objectives are the actual focus for the coming stretch, and let that decision be what execution triage consumes - only Epics under currently-in-focus Objectives get pulled into iterations, the rest stay tagged and visible on the roadmap without competing for slots yet. Worth a light dependency check at the same review too - some Objectives depend on others even where `goals.md` doesn't say so explicitly (e.g. O2.2's model repository is described as infrastructure O2.1's MaaS would sit on). See [docs/quarterly-planning.md](docs/quarterly-planning.md) for how to actually run that decision.

**When an item is still open at the end of its iteration**, this is handled automatically rather than left for someone to remember: it's moved back to Backlog and its Iteration is cleared, with a comment explaining why. Staying "in iteration" would implicitly claim it's still what's being worked on; going back to Backlog forces a fresh, cheap re-check at the next triage instead of assuming continuity. If it was In Progress, Start/End are left as-is (a real trace that work was in flight); if it never actually started, Start/End are cleared too since there's nothing to preserve.

What's still a human call at that point: if it turned out bigger than expected, split it into an Epic instead of re-entering it as-is. Otherwise, decide at the next triage whether it's still the priority (pull it into the new iteration) or not (leave it in Backlog). An item that keeps bouncing back cycle after cycle is itself worth noticing - either it isn't the priority its label says, or capacity is being chronically eaten by work this board doesn't track at all.

## Pull requests

Merging is not the same as done. Most of this work deploys via a separate playbook run, not CI/CD on merge - a merged PR just means the code is in `main`, not that it's live. Status=Done only happens when the issue is actually closed, and that's a decision for whoever verifies the deploy, not something that fires automatically on merge.

How you reference the issue in the PR depends on which is true for that repo/change:
- **Merge effectively is deploy** (e.g. a docs site that publishes on merge): use `Closes #123`. GitHub auto-closes the issue when this PR merges, which then triggers Status=Done. Fine as-is.
- **Merge triggers a later deploy step** (most repos, most of the time): use `Relates to #123` instead. This links the PR to the issue for traceability without auto-closing anything. Close the issue by hand once the deploy is verified.

This also settles what to do about multiple PRs on one issue: since closing is decoupled from any individual PR merging, it doesn't matter how many PRs are linked or in what order they merge - closing is still one deliberate action once the work is actually live. Don't put `Closes #123` on more than one PR for the same issue if that issue's deploy is gated - GitHub closes the issue the moment *any* of them merges, regardless of the others.

Multiple PRs on one issue isn't automatically a sign it should have been split - a small, well-scoped change can genuinely need PRs in more than one repo (GitHub doesn't allow a PR to span repos), and follow-up/fixup PRs are normal. Worth a second look during the Epic check-in only if there are several PRs and none of them look like an obvious cross-repo split.

Use draft PRs for work-in-progress; mark ready for review only once it's actually reviewable.

## What's automated vs. manual

Automated (see the workflows in this repo, and the board's own Settings > Workflows):
- New issues/PRs are added to the execution board with Status=Backlog
- Closing an issue sets Status=Done (merging a linked PR does not, by itself - see Pull requests above)
- Reopening an issue resets Status=Backlog
- Done items are archived from the board after 14 days
- A `blocked` label mirrors to Status=Blocked (and clears when the label is removed)
- Items still open when their iteration ends are moved back to Backlog with Iteration cleared (Start/End handled per the rules above), with a comment explaining what happened
- Start/End dates are kept in sync with Iteration whenever it changes
- Items entering In Progress with no Size set get a nudge comment
- Epic-typed issues with no sub-issues after some time get a nudge comment

Manual, by design:
- Setting Priority above the P1/P2 defaults
- Setting Pillar/Objective
- Deciding an item is Reactive rather than just untriaged
- Deciding whether an item bumped back to Backlog is still the priority (re-enter it) or not (leave it)
- Deciding a stuck item should become an Epic instead of being re-entered as-is
- Setting/revisiting an Epic's Start/Target dates
- Closing an issue once its deploy is verified (for anything not using `Closes #123`)
