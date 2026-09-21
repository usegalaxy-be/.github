#!/usr/bin/env python3
"""Keep Start/Target dates consistent with each item's Iteration.

Start date and Target date are org-level Issue Fields (Settings > Planning >
Issue Fields), not project fields - read/written via updateIssueFieldValue
against the issue itself, not updateProjectV2ItemFieldValue against the
project item. Iteration stays project-local (no org equivalent exists).

Runs frequently (every 30 min) so a triage change gets picked up promptly.
For every item whose Iteration is set but whose Target date doesn't match that
iteration's actual end:
  - Start date already set  -> preserve it, only move Target to the new
    iteration's end. This is the "was in flight, rolled into a later
    iteration" case (nudge_stale_items.py leaves Start alone specifically so
    this branch fires here).
  - Start date blank        -> fresh assignment (first time ever, or was
    cleared because the item never actually started last time). Set both
    Start and Target to the new iteration's window.

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

ORG_DATE_FIELDS_QUERY = '''
query {
  organization(login: "__ORG__") {
    issueFields(first: 20) {
      nodes { __typename ... on IssueFieldDate { id name } }
    }
  }
}
'''

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
              labels(first: 20) { nodes { name } }
              issueFieldValues(first: 10) {
                nodes { ... on IssueFieldDateValue { value field { ... on IssueFieldDate { name } } } }
              }
            }
          }
          iteration: fieldValueByName(name: "Iteration") { ... on ProjectV2ItemFieldIterationValue { title startDate duration } }
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


def fetch_org_date_field_ids():
    q = ORG_DATE_FIELDS_QUERY.replace("__ORG__", ORG)
    data = graphql(q)
    if not data or not data.get("data", {}).get("organization"):
        return None
    fields = {}
    for node in data["data"]["organization"]["issueFields"]["nodes"]:
        if node.get("__typename") == "IssueFieldDate":
            fields[node["name"]] = node["id"]
    return fields


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


def set_date(issue_id, field_id, date_str):
    if DRY_RUN:
        print(f"[dry-run] would set field {field_id} on issue {issue_id} to {date_str}")
        return
    m = f'''mutation {{
      updateIssueFieldValue(input: {{
        issueId: "{issue_id}", issueField: {{ fieldId: "{field_id}", dateValue: "{date_str}" }}
      }}) {{ clientMutationId }}
    }}'''
    graphql(m)


def remove_label(issue_url, label):
    if DRY_RUN:
        print(f"[dry-run] would remove label '{label}' from {issue_url}")
        return
    run(["gh", "issue", "edit", issue_url, "--remove-label", label])


def field_values_by_name(content):
    return {
        fv["field"]["name"]: fv["value"]
        for fv in (content.get("issueFieldValues") or {}).get("nodes", [])
        if fv and fv.get("field")
    }


def main():
    if not os.environ.get("GH_TOKEN"):
        print("GH_TOKEN not set, skipping (automation not yet activated)")
        return
    if not PROJECT_NUMBER:
        print("PROJECT_NUMBER not set, skipping")
        return

    date_fields = fetch_org_date_field_ids()
    if not date_fields or "Start date" not in date_fields or "Target date" not in date_fields:
        print("could not load org Start date/Target date fields, skipping")
        return

    items = fetch_items()
    if not items:
        print("could not load project items, skipping")
        return

    for item in items:
        iteration = item.get("iteration")
        if not iteration:
            continue
        content = item.get("content") or {}
        if not content:
            continue
        issue_id = content["id"]
        url = content.get("url", issue_id)
        labels = {n["name"] for n in (content.get("labels") or {}).get("nodes", [])}
        values = field_values_by_name(content)

        iter_start = datetime.fromisoformat(iteration["startDate"]).date()
        iter_end = iter_start + timedelta(days=iteration["duration"] - 1)

        current_target = values.get("Target date")
        if current_target == str(iter_end):
            continue  # already consistent, nothing to do

        # A real Iteration (re)assignment just happened - if this item was
        # sitting with needs-retriage (bounced back by nudge_stale_items.py),
        # that's now resolved.
        if "needs-retriage" in labels:
            remove_label(url, "needs-retriage")

        current_start = values.get("Start date")
        if current_start:
            # Was in flight (Start already recorded) - preserve it, just fix Target.
            set_date(issue_id, date_fields["Target date"], str(iter_end))
            print(f"{url}: preserved start={current_start}, set target={iter_end}")
        else:
            # Fresh assignment - nothing to preserve, use the iteration's own window.
            set_date(issue_id, date_fields["Start date"], str(iter_start))
            set_date(issue_id, date_fields["Target date"], str(iter_end))
            print(f"{url}: fresh assignment, set start={iter_start} target={iter_end}")


if __name__ == "__main__":
    main()
