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


## Project board fields

**Status**: Backlog / In Progress / Blocked / Done. Kept deliberately small so it can be driven by automation (see below).

**Priority**: P0 / P1 / P2. P0 is reserved for genuine escalations - never set automatically. As a starting default: goal-linked work (has a Pillar) defaults to P1, reactive work defaults to P2. Adjust as needed during triage.

**Size**: XS-XL. Set when an item is triaged into an iteration, not before. An XL item is a sign it should become an Epic with sub-issues rather than staying a single issue.

**Iteration**: 2-week cycles, Monday to Sunday. Represents "what cycle is this planned for," not a deadline. Only items actively planned for the current or next cycle should have one set.

**Pillar / Objective**: which 2026 goal (from the goals document) this work serves, if any. Three states matter, and the difference between the first two is deliberate:
- *Blank* = not yet triaged
- *Reactive / not goal-linked* = triaged, confirmed this doesn't serve a stated objective (most break-fix and tool-maintenance work falls here, and that's expected, not a problem)
- *A pillar set* = triaged, goal-linked

Objective options in the field picker show the Key Results under it. A Key Result that's a concrete deliverable becomes an Epic tagged with that Objective.

**Start date / End date**: only set for items with an Iteration, derived from that iteration's window.

## Triage

At the start of each iteration: filter the board to Status=Backlog, Pillar=blank, sorted oldest-first. Work down the list - for each item, either set a Pillar/Objective and Priority, or mark it Reactive/not goal-linked. Pull top-priority items into the new iteration until the In Progress column's limit is reached (see column settings on the board - the limit is a soft cap).

Reactive work doesn't need to wait for triage or an iteration assignment - it can move straight from Backlog to In Progress as it comes up. Iteration planning is for goal-linked and/or plannable work.

## Pull requests

Link every PR to the issue it resolves (`Closes #123` in the description). A merged PR automatically closes the linked issue and moves it to Status=Done - see Automation below. Use draft PRs for work-in-progress; mark ready for review only once it's actually reviewable.

## What's automated vs. manual

Automated (see the workflows in this repo, and the board's own Settings > Workflows):
- New issues/PRs are added to the execution board with Status=Backlog
- Closing an issue, or merging its linked PR, sets Status=Done
- Reopening an issue resets Status=Backlog
- Done items are archived from the board after 14 days
- A `blocked` label mirrors to Status=Blocked (and clears when the label is removed)
- Items sitting in a completed iteration without being closed get a nudge comment
- Items entering In Progress with no Size set get a nudge comment
- Epic-typed issues with no sub-issues after some time get a nudge comment

Manual, by design:
- Setting Priority above the P1/P2 defaults
- Setting Pillar/Objective
- Deciding an item is Reactive rather than just untriaged
- Moving unfinished items out of a completed iteration into the next one
