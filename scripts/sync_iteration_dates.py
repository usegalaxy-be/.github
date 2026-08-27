#!/usr/bin/env python3
"""Keep Start/End dates consistent with each item's Iteration.

Runs frequently (every 30 min) so a triage change gets picked up promptly.
For every item whose Iteration is set but whose End date doesn't match that
iteration's actual end:
  - Start date already set  -> preserve it, only move End to the new
    iteration's end. This is the "was in flight, rolled into a later
    iteration" case (nudge_stale_items.py leaves Start alone specifically so
    this branch fires here).
  - Start date blank        -> fresh assignment (first time ever, or was
    cleared because the item never actually started last time). Set both
    Start and End to the new iteration's window.

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

QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      id
      startField: field(name: "Start date") { ... on ProjectV2FieldCommon { id } }
      endField: field(name: "End date") { ... on ProjectV2FieldCommon { id } }
      items(first: 100__AFTER__) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content { ... on Issue { url } }
          iteration: fieldValueByName(name: "Iteration") { ... on ProjectV2ItemFieldIterationValue { title startDate duration } }
          startDate: fieldValueByName(name: "Start date") { ... on ProjectV2ItemFieldDateValue { date } }
          endDate: fieldValueByName(name: "End date") { ... on ProjectV2ItemFieldDateValue { date } }
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
                "start_field_id": project["startField"]["id"],
                "end_field_id": project["endField"]["id"],
            }
        page = project["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return meta, items


def set_date(project_id, item_id, field_id, date_str):
    if DRY_RUN:
        print(f"[dry-run] would set field {field_id} on {item_id} to {date_str}")
        return
    m = f'''mutation {{
      updateProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}", itemId: "{item_id}", fieldId: "{field_id}",
        value: {{ date: "{date_str}" }}
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

    for item in items:
        iteration = item.get("iteration")
        if not iteration:
            continue
        content = item.get("content") or {}
        url = content.get("url", item["id"])

        iter_start = datetime.fromisoformat(iteration["startDate"]).date()
        iter_end = iter_start + timedelta(days=iteration["duration"] - 1)

        current_end = (item.get("endDate") or {}).get("date")
        if current_end == str(iter_end):
            continue  # already consistent, nothing to do

        current_start = (item.get("startDate") or {}).get("date")
        if current_start:
            # Was in flight (Start already recorded) - preserve it, just fix End.
            set_date(project["id"], item["id"], project["end_field_id"], str(iter_end))
            print(f"{url}: preserved start={current_start}, set end={iter_end}")
        else:
            # Fresh assignment - nothing to preserve, use the iteration's own window.
            set_date(project["id"], item["id"], project["start_field_id"], str(iter_start))
            set_date(project["id"], item["id"], project["end_field_id"], str(iter_end))
            print(f"{url}: fresh assignment, set start={iter_start} end={iter_end}")


if __name__ == "__main__":
    main()
