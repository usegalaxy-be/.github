#!/usr/bin/env python3
"""Propagate Pillar/Objective down from an OKR-tagged parent to its sub-issues.

Runs frequently (every 30 min), same reasoning as sync_iteration_dates.py:
sub_issues is a real webhook event (parent_issue_added/removed) but it is
not a valid GitHub Actions trigger, so this has to poll instead of react.

For every item with a parent issue: if the parent's Pillar is a real value
(not blank, not "Reactive / not goal-linked") and the item's own Pillar is
blank, copy Pillar + Objective down from the parent. Never overwrites a
Pillar/Objective a human already set on the item itself.

The OKR label and [OKR] title prefix are NOT propagated - those mark the
top-level Objective-linked issue only, not its sub-issues. Only the
Pillar/Objective field values (used for reporting/rollup) inherit down.

Sub-sub-issues cascade naturally over a couple of poll cycles rather than
needing recursive graph-walking in one pass: a grandchild inherits once its
immediate parent has already inherited on an earlier run.

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

QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      id
      pillarField: field(name: "Pillar") { ... on ProjectV2SingleSelectField { id options { id name } } }
      objectiveField: field(name: "Objective") { ... on ProjectV2SingleSelectField { id options { id name } } }
      items(first: 100__AFTER__) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            ... on Issue {
              id url
              parent { id }
            }
          }
          pillar: fieldValueByName(name: "Pillar") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
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
                "pillar_field_id": project["pillarField"]["id"],
                "pillar_options": {o["name"]: o["id"] for o in project["pillarField"]["options"]},
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

    for item in items:
        content = item.get("content")
        if not content:
            continue
        parent_ref = content.get("parent")
        if not parent_ref:
            continue

        own_pillar = (item.get("pillar") or {}).get("name")
        if own_pillar:
            continue  # already set, by a human or a prior run - never overwrite

        parent_item = by_issue_id.get(parent_ref["id"])
        if not parent_item:
            continue  # parent isn't on this project (yet)

        parent_pillar = (parent_item.get("pillar") or {}).get("name")
        if not parent_pillar or parent_pillar == REACTIVE_OPTION_NAME:
            continue  # parent isn't OKR-linked, nothing to inherit

        parent_objective = (parent_item.get("objective") or {}).get("name")
        url = content["url"]

        set_select(project["id"], item["id"], project["pillar_field_id"],
                   project["pillar_options"][parent_pillar])
        if parent_objective and parent_objective in project["objective_options"]:
            set_select(project["id"], item["id"], project["objective_field_id"],
                       project["objective_options"][parent_objective])

        print(f"{url}: inherited pillar={parent_pillar} objective={parent_objective}")


if __name__ == "__main__":
    main()
