#!/usr/bin/env python3
"""Label work that was done inside an iteration it wasn't committed to.

The `unplanned` label records how work arrived, not how urgent or important
it was - see the "Unplanned work" section in CONTRIBUTING.md. Its purpose is
to make the per-cycle share of uncommitted work measurable, which
docs/quarterly-planning.md otherwise has to guess at.

An item is labelled when it is Status = In Progress and either:
  - its Iteration was set after that iteration's grace window (the first day,
    which covers decisions made in the boundary Monday meeting), or
  - it has no Iteration at all - the `opportunistic` pickup case, real
    capacity spent outside any commitment.

Epics are always skipped: they never get an Iteration by design, so there is
no commitment for them to fall outside of.

The timestamp used is `updatedAt` on the item's Iteration field value, i.e.
when the Iteration was last set, not when the issue was filed. Filing date
would both miss old Backlog items pulled in mid-cycle and wrongly flag items
created and committed during the boundary meeting itself.

The label is never removed once applied - it's a record of what happened.

Requires GH_TOKEN, ORG, PROJECT_NUMBER. No-ops cleanly if GH_TOKEN is unset.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ORG = os.environ.get("ORG", "usegalaxy-be")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER")
DRY_RUN = os.environ.get("DRY_RUN") == "true"
# Days from the iteration's start that still count as "committed at the
# boundary". 1 = the whole first day, so the Monday meeting is inside it.
GRACE_DAYS = int(os.environ.get("GRACE_DAYS", "1"))

LABEL = "unplanned"
IN_PROGRESS = "In Progress"

PROJECT_QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      items(first: 100__AFTER__) {
        pageInfo { hasNextPage endCursor }
        nodes {
          content {
            ... on Issue {
              url
              issueType { name }
              labels(first: 30) { nodes { name } }
            }
          }
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          iteration: fieldValueByName(name: "Iteration") { ... on ProjectV2ItemFieldIterationValue { title startDate updatedAt } }
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


def add_label(issue_url):
    if DRY_RUN:
        print(f"[dry-run] would add '{LABEL}' to {issue_url}")
        return
    run(["gh", "issue", "edit", issue_url, "--add-label", LABEL])


def grace_deadline(iteration):
    """End of the window in which setting an Iteration still counts as committed."""
    start = datetime.fromisoformat(iteration["startDate"]).replace(tzinfo=timezone.utc)
    return start + timedelta(days=GRACE_DAYS)


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

    labelled = 0
    for item in items:
        content = item.get("content") or {}
        if not content:
            continue

        status = (item.get("status") or {}).get("name")
        if status != IN_PROGRESS:
            continue

        if (content.get("issueType") or {}).get("name") == "Epic":
            continue

        labels = {n["name"] for n in (content.get("labels") or {}).get("nodes", [])}
        if LABEL in labels:
            continue

        url = content["url"]
        iteration = item.get("iteration")
        if not iteration:
            # Worked on without ever entering an iteration - opportunistic pickup.
            add_label(url)
            print(f"{url}: in progress with no iteration")
            labelled += 1
            continue

        set_at = datetime.fromisoformat(iteration["updatedAt"].replace("Z", "+00:00"))
        deadline = grace_deadline(iteration)
        if set_at > deadline:
            add_label(url)
            print(f"{url}: added to {iteration['title']} at {set_at:%Y-%m-%d %H:%M}, "
                  f"after the {deadline:%Y-%m-%d} grace deadline")
            labelled += 1

    print(f"{labelled} item(s) newly marked {LABEL}")


if __name__ == "__main__":
    main()
