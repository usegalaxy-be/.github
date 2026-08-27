# Picking quarterly focus

`goals.md` says what's legitimate to work on, not when. With 4 Pillars and 11 Objectives, nothing in the goals document itself tells you which 2-3 to actually push this quarter - that decision has to happen separately, and its output is what execution triage consumes (see CONTRIBUTING.md - only Epics under currently-in-focus Objectives get pulled into iterations).

This is a planning conversation, not a board mechanic. Nothing here needs a GitHub field.

## Cadence

Quarterly, alongside whatever review already happens against `goals.md`'s Key Results. Standard OKR practice: score each Objective's Key Results on progress/confidence (a simple on track / at risk / not started is enough, doesn't need to be precise), then use that pass as the moment to decide focus for the next quarter.

## What to weigh, per Objective

- **Impact** - does progress here matter to someone who'll notice? A real external deadline (e.g. a membership/compliance date) beats vague strategic value that doesn't move on its own schedule.
- **Effort / capacity** - roughly how much team bandwidth this would take, weighed against how much capacity is realistically going to reactive work rather than theoretical full capacity.
- **Readiness** - is this Objective's work understood well enough to turn into real Epics, or still vague ideas? Well-scoped beats well-intentioned-but-undefined, even if the undefined one sounds more important.
- **Dependency** - does this block or get blocked by another Objective (e.g. O2.2's model repository underpins O2.1's MaaS)? Sequencing sometimes falls out of dependency alone.
- **Whose call it actually is** - `goals.md` itself notes some goals "can't be fully actioned by the Compute Team." Objectives blocked on outside stakeholders (VSC, Data Center, VIB) are worth flagging separately - either deprioritize since they can't be moved unilaterally, or front-load specifically because the external dependency has its own long lead time.

## Process

1. Whoever's deciding (not necessarily the whole team) spends 30-45 minutes going through the 11 Objectives against the questions above. Structured discussion, not a scoring spreadsheet.
2. Land on 2-3 as the actual focus (or "1-2 per Pillar" if every Pillar should stay represented).
3. Write the decision down somewhere durable - a short note is enough. This is what execution triage filters against.
4. Revisit next quarter. The point isn't a permanent ranking, it's having *a* ranking that beats "everything is P1."

Once focus Objectives are picked, tagging their Epics with Pillar/Objective/Priority on the board is a five-minute mechanical step - the decision above is the actual work.
