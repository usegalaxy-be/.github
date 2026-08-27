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


## Project board fields

**Status**: Backlog / In Progress / Blocked / Done. Kept deliberately small so it can be driven by automation (see below).

**Priority**: P0 / P1 / P2. P0 is reserved for genuine escalations - never set automatically. As a starting default: goal-linked work (has a Pillar) defaults to P1, reactive work defaults to P2. Adjust as needed during triage.

**Size**: XS-XL. Set when an item is triaged into an iteration, not before. A single (non-Epic) issue should be scoped to fit inside **one** iteration (2 weeks) - not planned across two from the start. If it can't realistically finish in one iteration, that's the signal to convert it to an Epic and split it into sub-issues, not to plan on rolling it into a second cycle. Rolling over is for the exceptional case where something unexpectedly slips, not a normal planning outcome - see the Start/End date note below.

**Iteration**: 2-week cycles, Monday to Sunday. Represents "what cycle is this planned for," not a deadline. Only items actively planned for the current or next cycle should have one set.

**Pillar / Objective**: which 2026 goal (from the goals document) this work serves, if any. Three states matter, and the difference between the first two is deliberate:
- *Blank* = not yet triaged
- *Reactive / not goal-linked* = triaged, confirmed this doesn't serve a stated objective - covers both spontaneous break-fix work and deliberately planned work (e.g. a scheduled upgrade) that just isn't tied to a 2026 goal. Both are expected, not a problem; this tag is about goal-linkage, not about whether the work was planned or matters.
- *A pillar set* = triaged, goal-linked

Objective options in the field picker show the Key Results under it. A Key Result that's a concrete deliverable becomes an Epic tagged with that Objective.

**Start date / End date**: only set for items with an Iteration, derived from that iteration's window, kept in sync automatically. When an item gets a new Iteration and already has a Start date, only End moves forward - Start is preserved so the Roadmap bar visibly stretches across iterations instead of quietly resetting to looking on-track every cycle. If Start is blank (the item never actually got started - see below), both Start and End are set fresh to the new iteration's window.

## Triage

Uses the existing weekly Monday meeting - no separate meeting needed - which alternates between two modes depending on whether it falls on an iteration boundary (every other week; the automated sweep already runs Monday morning, so the board's clean before anyone sits down either week):

**Iteration-boundary Monday** (full triage):
1. Review items the automation bounced back to Backlog (see below) - still the priority? Pull into the iteration starting now. Not right now? Leave in Backlog. Turned out bigger than expected? Split into an Epic instead of re-entering it as-is.
2. Finalize the iteration that's starting: review what was staged as "next" two weeks ago, confirm it still makes sense given current capacity and priorities (this is a real review, not a rubber stamp - things change in two weeks), adjust Size/Priority, lock it in.
3. Triage new Backlog items: filter to Status=Backlog, Pillar=blank, sorted oldest-first. For each, either set a Pillar/Objective and Priority, or mark it Reactive/not goal-linked. Pull top-priority items into the now-current iteration up to the In Progress column's limit (a soft cap, see column settings); stage a few likely candidates into "next" for visibility, to be properly reviewed at the following iteration boundary.
4. Epic check-in: anything the "no sub-issues after 2 weeks" nudge has flagged, or any Epic close to fully rolled up.

**Mid-iteration Monday** (business as usual): discuss top-priority items, triage any new issues into Backlog (Pillar/Objective/Priority). Nothing iteration-specific - the current iteration is already locked and running.

This is about the execution board (`#8`) and its weekly-to-biweekly rhythm. The strategic roadmap (`#10`, Pillar/Objective progress) runs on a much slower cadence - monthly or quarterly - since "is this Objective on track" isn't a question that changes week to week.

Only genuinely urgent work (something's broken or blocking users right now) skips this and moves straight from Backlog to In Progress. Everything else goes through iteration planning, whether or not it's goal-linked - a deliberately scheduled upgrade or migration is triaged, sized, and scheduled into a cycle the same as goal-linked work, even though it'll end up tagged Reactive/not goal-linked. That tag means "doesn't serve a stated objective," not "wasn't planned" or "isn't important."

**When an item is still open at the end of its iteration**, this is handled automatically rather than left for someone to remember: it's moved back to Backlog and its Iteration is cleared, with a comment explaining why. Staying "in iteration" would implicitly claim it's still what's being worked on; going back to Backlog forces a fresh, cheap re-check at the next triage instead of assuming continuity. If it was In Progress, Start/End are left as-is (a real trace that work was in flight); if it never actually started, Start/End are cleared too since there's nothing to preserve.

What's still a human call at that point: if it turned out bigger than expected, split it into an Epic instead of re-entering it as-is. Otherwise, decide at the next triage whether it's still the priority (pull it into the new iteration) or not (leave it in Backlog). An item that keeps bouncing back cycle after cycle is itself worth noticing - either it isn't the priority its label says, or capacity is being chronically eaten by work this board doesn't track at all.

## Pull requests

Link every PR to the issue it resolves (`Closes #123` in the description). A merged PR automatically closes the linked issue and moves it to Status=Done - see Automation below. Use draft PRs for work-in-progress; mark ready for review only once it's actually reviewable.

## What's automated vs. manual

Automated (see the workflows in this repo, and the board's own Settings > Workflows):
- New issues/PRs are added to the execution board with Status=Backlog
- Closing an issue, or merging its linked PR, sets Status=Done
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
