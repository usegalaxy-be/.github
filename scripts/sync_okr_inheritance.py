#!/usr/bin/env python3
"""Propagate Objective down from an OKR-tagged parent to its sub-issues,
recursively through sub-sub-issues and beyond.

Runs frequently (every 30 min), same reasoning as sync_iteration_dates.py:
sub_issues is a real webhook event (parent_issue_added/removed) but it is
not a valid GitHub Actions trigger, so this has to poll instead of react.

For every item with a parent issue: if the parent's Objective is a real
value (not blank, not "Reactive / not goal-linked") and the item's own
Objective is blank, copy Objective down from the parent. Never overwrites
an Objective a human already set on the item itself.

The OKR label and [OKR] title prefix are NOT propagated - those mark the
top-level Objective-linked issue only, not its sub-issues. Only the
Objective field value (used for reporting/rollup) inherits down.

The propagation pass repeats in-memory until a full pass makes no further
changes (bounded by MAX_PASSES), so a whole parent -> child -> grandchild
-> ... chain resolves within a single run instead of needing several poll
cycles to cascade one level at a time.

Includes archived items (archivedStates: [ARCHIVED, NOT_ARCHIVED]) - the
default is active-only, but Objective is a permanent record of what an
item served, not something that should stop propagating just because the
item was later closed and auto-archived off the board.

Requires GH_TOKEN, ORG, PROJECT_NUMBER. No-ops cleanly if GH_TOKEN is unset.
"""
import json
import os
import subprocess
import sys

ORG = os.environ.get("ORG", "usegalaxy-be")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER")
DRY_RUN = os.environ.get("DRY_RUN") == "true"

REACTIVE_OPTION_NAME = "Reactive / not goal-linked"
MAX_PASSES = 20  # generous headroom for any realistic sub-issue chain depth

QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      id
      objectiveField: field(name: "Objective") { ... on ProjectV2SingleSelectField { id options { id name } } }
      items(first: 100__AFTER__, archivedStates: [ARCHIVED, NOT_ARCHIVED]) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            ... on Issue {
              id url
              parent { id }
            }
          }
          objective: fieldValueByName(name: "Objective") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
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


def fetch_project():
    items = []
    cursor = None
    meta = None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = (QUERY_TEMPLATE
             .replace("__ORG__", ORG)
             .replace("__PROJECT_NUMBER__", str(PROJECT_NUMBER))
             .replace("__AFTER__", after))
        data = graphql(q)
        if not data or not data.get("data", {}).get("organization", {}).get("projectV2"):
            break
        project = data["data"]["organization"]["projectV2"]
        if meta is None:
            meta = {
                "id": project["id"],
                "objective_field_id": project["objectiveField"]["id"],
                "objective_options": {o["name"]: o["id"] for o in project["objectiveField"]["options"]},
            }
        page = project["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return meta, items


def set_select(project_id, item_id, field_id, option_id):
    if DRY_RUN:
        print(f"[dry-run] would set field {field_id} on {item_id} to option {option_id}")
        return
    m = f'''mutation {{
      updateProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}", itemId: "{item_id}", fieldId: "{field_id}",
        value: {{ singleSelectOptionId: "{option_id}" }}
      }}) {{ projectV2Item {{ id }} }}
    }}'''
    graphql(m)


def main():
    if not os.environ.get("GH_TOKEN"):
        print("GH_TOKEN not set, skipping (automation not yet activated)")
        return
    if not PROJECT_NUMBER:
        print("PROJECT_NUMBER not set, skipping")
        return

    project, items = fetch_project()
    if not project:
        print("could not load project, skipping")
        return

    # index by underlying issue node id, for parent lookups
    by_issue_id = {}
    for item in items:
        content = item.get("content")
        if content:
            by_issue_id[content["id"]] = item

    # in-memory objective per item, updated as we go so a pass can see a
    # value set earlier in the same pass (or a prior pass) as already there
    current_objective = {
        item["id"]: (item.get("objective") or {}).get("name")
        for item in items
    }

    for _pass in range(MAX_PASSES):
        changed = False

        for item in items:
            content = item.get("content")
            if not content:
                continue
            if current_objective.get(item["id"]):
                continue  # already set, by a human or an earlier pass - never overwrite

            parent_ref = content.get("parent")
            if not parent_ref:
                continue

            parent_item = by_issue_id.get(parent_ref["id"])
            if not parent_item:
                continue  # parent isn't on this project (yet)

            parent_objective = current_objective.get(parent_item["id"])
            if not parent_objective or parent_objective == REACTIVE_OPTION_NAME:
                continue  # parent isn't OKR-linked (yet, this pass), nothing to inherit

            if parent_objective not in project["objective_options"]:
                continue

            current_objective[item["id"]] = parent_objective
            set_select(project["id"], item["id"], project["objective_field_id"],
                       project["objective_options"][parent_objective])
            print(f"{content['url']}: inherited objective={parent_objective}")
            changed = True

        if not changed:
            break


if __name__ == "__main__":
    main()
