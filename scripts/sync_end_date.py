#!/usr/bin/env python3
"""Set the End date on items that have reached Status = Done.

End date is an org-level Issue Field (Settings > Planning > Issue Fields),
written via updateIssueFieldValue against the issue itself. Unlike Start and
Target it is not derived from the Iteration - an item's iteration can change
after the fact, when it actually finished cannot. The value used is the
issue's own closedAt date, so a re-run always produces the same answer; an
item marked Done while still open falls back to today.

Existing End dates are never overwritten or cleared, so a manually recorded
Epic date survives - including the deliberate far-future bound some long
running OKR Epics carry while still in progress. An item that is reopened
therefore keeps its old End date until someone clears it by hand.

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
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          content {
            ... on Issue {
              id
              url
              closedAt
              issueFieldValues(first: 10) {
                nodes { ... on IssueFieldDateValue { value field { ... on IssueFieldDate { name } } } }
              }
            }
          }
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


def fetch_end_date_field_id():
    q = ORG_DATE_FIELDS_QUERY.replace("__ORG__", ORG)
    data = graphql(q)
    if not data or not data.get("data", {}).get("organization"):
        return None
    for node in data["data"]["organization"]["issueFields"]["nodes"]:
        if node.get("__typename") == "IssueFieldDate" and node["name"] == "End date":
            return node["id"]
    return None


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
        print(f"[dry-run] would set End date on issue {issue_id} to {date_str}")
        return
    m = f'''mutation {{
      updateIssueFieldValue(input: {{
        issueId: "{issue_id}", issueField: {{ fieldId: "{field_id}", dateValue: "{date_str}" }}
      }}) {{ clientMutationId }}
    }}'''
    graphql(m)


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

    field_id = fetch_end_date_field_id()
    if not field_id:
        print("could not load the org End date field, skipping")
        return

    items = fetch_items()
    if not items:
        print("could not load project items, skipping")
        return

    today = datetime.now(timezone.utc).date()

    for item in items:
        content = item.get("content") or {}
        if not content.get("id"):
            continue  # draft item or pull request, no issue fields to write
        issue_id = content["id"]
        url = content.get("url", issue_id)
        status = (item.get("status") or {}).get("name")
        if status != "Done":
            continue
        if field_values_by_name(content).get("End date"):
            continue  # already recorded, never overwrite

        closed_at = content.get("closedAt")
        end = (datetime.fromisoformat(closed_at.replace("Z", "+00:00")).date()
               if closed_at else today)
        set_date(issue_id, field_id, str(end))
        print(f"{url}: done, set end={end}")


if __name__ == "__main__":
    main()
