#!/usr/bin/env python3
"""Flag Epics whose own planning window no longer covers the work running under them.

Iteration work and the roadmap are supposed to agree: if a sub-issue is being
worked on now, the Epic (Key Result) above it should be an active initiative -
in progress, and inside its own Start/Target window. When they disagree, the
Roadmap view shows a bar that has nothing to do with what the team is doing.

The Epic's dates are never rewritten here. An Epic's window is a human
judgement (see CONTRIBUTING.md), so the drift is surfaced as a
`roadmap-drift` label on the Epic and left for the Epic check-in to resolve,
either by moving the Epic's dates or by stopping the work under it.

An Epic is checked when there is live work under it: either the Epic itself is
Status = In Progress, or at least one of its descendants is. It is then flagged
for any of:
  - the Epic is not itself Status = In Progress, while work under it is (work
    running under a Key Result nobody has declared active)
  - the Epic has no Start date
  - the Epic's Start date is later than the earliest start of that work (work
    began before the Epic's window opens)
  - the Epic's Target date is earlier than the latest target of that work
    (work is scheduled to run past the date the Epic claims to end)

An Epic that is itself In Progress counts today as the work, so an active Epic
whose Target date has already passed is flagged on that basis alone.

A missing Target date is not drift: CONTRIBUTING.md allows an Epic to carry no
Target when there is no real driver for one.

Unlike `unplanned`, this label is a live state, not a record - it is removed
again as soon as the Epic and its work agree, so the board only ever shows
current disagreements.

Requires GH_TOKEN, ORG, PROJECT_NUMBER. No-ops cleanly if GH_TOKEN is unset.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ORG = os.environ.get("ORG", "usegalaxy-be")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER")
DRY_RUN = os.environ.get("DRY_RUN") == "true"

LABEL = "roadmap-drift"
IN_PROGRESS = "In Progress"
MAX_DEPTH = 20  # guard against a parent cycle, not a real nesting depth

PROJECT_QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      items(first: 100__AFTER__) {
        pageInfo { hasNextPage endCursor }
        nodes {
          content {
            ... on Issue {
              id
              url
              issueType { name }
              parent { id }
              labels(first: 30) { nodes { name } }
              issueFieldValues(first: 10) {
                nodes { ... on IssueFieldDateValue { value field { ... on IssueFieldDate { name } } } }
              }
            }
          }
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
        }
      }
    }
  }
}
'''


def run(cmd, timeout=30):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"command failed: {' '.join(cmd)}\n{r.stderr}", file=sys.stderr)
    return r


def graphql(query):
    r = run(["gh", "api", "graphql", "-f", f"query={query}"])
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def fetch_items():
    items = []
    cursor = None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = (PROJECT_QUERY_TEMPLATE
             .replace("__ORG__", ORG)
             .replace("__PROJECT_NUMBER__", str(PROJECT_NUMBER))
             .replace("__AFTER__", after))
        data = graphql(q)
        if not data or not data.get("data", {}).get("organization", {}).get("projectV2"):
            break
        page = data["data"]["organization"]["projectV2"]["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return items


def dates(content):
    values = {
        fv["field"]["name"]: fv["value"]
        for fv in (content.get("issueFieldValues") or {}).get("nodes", [])
        if fv and fv.get("field")
    }
    out = {}
    for name in ("Start date", "Target date"):
        raw = values.get(name)
        out[name] = datetime.fromisoformat(raw).date() if raw else None
    return out


def add_label(issue_url):
    if DRY_RUN:
        print(f"[dry-run] would add '{LABEL}' to {issue_url}")
        return
    run(["gh", "issue", "edit", issue_url, "--add-label", LABEL])


def remove_label(issue_url):
    if DRY_RUN:
        print(f"[dry-run] would remove '{LABEL}' from {issue_url}")
        return
    run(["gh", "issue", "edit", issue_url, "--remove-label", LABEL])


def top_ancestor(item, by_issue_id):
    """The topmost board item above this one, or None if it has no parent."""
    current = item
    for _ in range(MAX_DEPTH):
        parent_ref = (current.get("content") or {}).get("parent")
        if not parent_ref:
            break
        parent = by_issue_id.get(parent_ref["id"])
        if not parent:
            break  # parent isn't on this project, treat what we have as the top
        current = parent
    return None if current is item else current


def work_window(epic, children, today):
    """Span the Epic's dates have to cover, or None when nothing is running.

    An in-progress item with no dates of its own is being worked on today, so
    today is what the Epic has to cover for it. An Epic that is itself In
    Progress is live work in the same sense, on today.
    """
    starts, targets = [], []
    if (epic.get("status") or {}).get("name") == IN_PROGRESS:
        starts.append(today)
        targets.append(today)
    for c in children:
        d = dates(c["content"])
        starts.append(d["Start date"] or today)
        targets.append(d["Target date"] or today)
    if not starts:
        return None
    return min(starts), max(targets)


def drift_reasons(epic, children, window):
    """Why this Epic and the work under it disagree, in the order they are reported."""
    reasons = []
    epic_status = (epic.get("status") or {}).get("name")
    epic_dates = dates(epic["content"])
    earliest, latest = window

    if children and epic_status != IN_PROGRESS:
        reasons.append(f"Epic status is {epic_status or 'unset'}, not {IN_PROGRESS}")

    if not epic_dates["Start date"]:
        reasons.append("Epic has no Start date")
    elif epic_dates["Start date"] > earliest:
        reasons.append(f"Epic starts {epic_dates['Start date']}, work under it started {earliest}")

    # No Target date is a legitimate state for an Epic without a driver, so
    # only a Target that is actually too early counts as drift.
    if epic_dates["Target date"] and epic_dates["Target date"] < latest:
        reasons.append(f"Epic targets {epic_dates['Target date']}, work under it runs to {latest}")

    return reasons


def main():
    if not os.environ.get("GH_TOKEN"):
        print("GH_TOKEN not set, skipping (automation not yet activated)")
        return
    if not PROJECT_NUMBER:
        print("PROJECT_NUMBER not set, skipping")
        return

    items = fetch_items()
    if not items:
        print("could not load project items, skipping")
        return

    today = datetime.now(timezone.utc).date()

    by_issue_id = {}
    for item in items:
        content = item.get("content")
        if content:
            by_issue_id[content["id"]] = item

    # in-progress descendants, grouped by the top-level item above them
    children_by_epic = {}
    for item in items:
        if not item.get("content"):
            continue
        if (item.get("status") or {}).get("name") != IN_PROGRESS:
            continue
        top = top_ancestor(item, by_issue_id)
        if not top:
            continue
        if (top["content"].get("issueType") or {}).get("name") != "Epic":
            continue  # only Key-Result-level Epics carry a roadmap window
        children_by_epic.setdefault(top["content"]["id"], []).append(item)

    flagged = cleared = 0
    for item in items:
        content = item.get("content")
        if not content:
            continue
        labels = {n["name"] for n in (content.get("labels") or {}).get("nodes", [])}
        children = children_by_epic.get(content["id"], [])
        is_epic = (content.get("issueType") or {}).get("name") == "Epic"

        window = work_window(item, children, today) if is_epic else None
        reasons = drift_reasons(item, children, window) if window else []

        if reasons and LABEL not in labels:
            add_label(content["url"])
            flagged += 1
        elif not reasons and LABEL in labels:
            remove_label(content["url"])
            cleared += 1
            print(f"{content['url']}: back in line with the work under it")

        if reasons:
            live = (f"{len(children)} sub-issue(s) in progress" if children
                    else "Epic itself in progress")
            print(f"{content['url']} ({live}): " + "; ".join(reasons))

    print(f"{flagged} Epic(s) newly flagged {LABEL}, {cleared} cleared")


if __name__ == "__main__":
    main()
