# Retroactively applying the issue templates

GitHub issue forms only apply at creation time - there's no way to reformat an existing issue to match one automatically. For an old issue that predates the templates, or was filed without one, paste the matching block below as a **comment**, not a body edit. Keep the reporter's original text intact; add structure on top of it, don't overwrite what they wrote.

Delete whichever RFC/Objective line doesn't apply and fill in the blanks - these mirror the current `task.yml`/`epic.yml` fields exactly, so triage means the same thing whether an issue went through the template at creation or got this treatment later.

## Task / Bug / Feature

```markdown
### What needs to happen



### Done means



### Does this need an RFC?

No
```

## Epic

```markdown
### What is this initiative



### Will any sub-part need an RFC?

Not sure yet - decide at triage

### Why does this need to be an Epic?

- [ ] Depends on someone outside the team acting first (data center, VSC, ...), their schedule bounds the timeline regardless of how small the work is
- [ ] At least one part is "investigate/figure out X" rather than "do X" - the investigation (done = a decision) and the eventual fix are separately scoped
- [ ] Real elapsed calendar time is involved beyond the work itself (deploy windows, a verification period, external review)
- [ ] No precedent - nobody's done something like this before, so a single confident estimate isn't realistic

### Known sub-parts (optional)


```
