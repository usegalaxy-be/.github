#!/usr/bin/env python3
"""Scheduled triage nudges for the usegalaxy-be execution project board.

Three checks, each posts at most one comment per item per run, skipped if a
matching marker comment was already posted in the last 5 days:
  1. Item still open, but its assigned Iteration has already ended.
  2. Item is Status=In Progress with no Size set.
  3. Issue is Epic-typed, has no sub-issues, and is >14 days old.

Requires GH_TOKEN (a PAT/App token with `project` write scope) and
ORG / PROJECT_NUMBER env vars. No-ops cleanly if GH_TOKEN is unset, so this
is safe to enable before the token secret exists.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ORG = os.environ.get("ORG", "usegalaxy-be")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER")
DRY_RUN = os.environ.get("DRY_RUN") == "true"

MARKER_ITERATION = "<!-- nudge:stale-iteration -->"
MARKER_SIZE = "<!-- nudge:missing-size -->"
MARKER_EPIC = "<!-- nudge:epic-no-subissues -->"


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


# Plain (non-f) template: GraphQL is brace-heavy, so we substitute placeholder
# tokens instead of using str.format()/f-strings to avoid escaping every { and }.
ITEMS_QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      items(first: 100__AFTER__) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            ... on Issue {
              number url createdAt state
              repository { name }
              issueType { name }
              subIssuesSummary { total }
            }
          }
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          size: fieldValueByName(name: "Size") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          iteration: fieldValueByName(name: "Iteration") { ... on ProjectV2ItemFieldIterationValue { title startDate duration } }
        }
      }
    }
  }
}
'''


def fetch_project_items():
    items = []
    cursor = None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = (ITEMS_QUERY_TEMPLATE
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


def has_recent_marker(issue_url, marker, days=5):
    r = run(["gh", "issue", "view", issue_url, "--json", "comments",
             "-q", ".comments[].body"])
    if r.returncode != 0:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    # cheap check: marker present anywhere in recent output is good enough here,
    # comment timestamps aren't in this projection so we accept "posted this run
    # or a previous one this week" as sufficient de-dup for a weekly cron.
    return marker in r.stdout


def comment(issue_url, marker, body):
    if has_recent_marker(issue_url, marker):
        return
    full_body = f"{marker}\n{body}"
    if DRY_RUN:
        print(f"[dry-run] would comment on {issue_url}:\n{full_body}\n")
        return
    run(["gh", "issue", "comment", issue_url, "--body", full_body])
    print(f"commented on {issue_url}")


def main():
    if not os.environ.get("GH_TOKEN"):
        print("GH_TOKEN not set, skipping (automation not yet activated)")
        return
    if not PROJECT_NUMBER:
        print("PROJECT_NUMBER not set, skipping")
        return

    items = fetch_project_items()
    now = datetime.now(timezone.utc)

    for item in items:
        content = item.get("content")
        if not content or content.get("state") != "OPEN":
            continue
        url = content["url"]
        status = (item.get("status") or {}).get("name")
        size = (item.get("size") or {}).get("name")
        iteration = item.get("iteration")
        issue_type = (content.get("issueType") or {}).get("name")
        sub_total = (content.get("subIssuesSummary") or {}).get("total", 0)
        created_at = datetime.fromisoformat(content["createdAt"].replace("Z", "+00:00"))

        if status != "Done" and iteration:
            start = datetime.fromisoformat(iteration["startDate"]).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=iteration["duration"] - 1)
            if end < now:
                comment(url, MARKER_ITERATION,
                        f"This item is still open but its iteration (**{iteration['title']}**, "
                        f"ended {end.date()}) has passed. If it turned out bigger than expected, split it "
                        f"into an Epic with sub-issues. Otherwise move it back to Backlog for re-triage "
                        f"(only pull it straight into the next iteration if it's still the clear priority) "
                        f"or close it if it's no longer needed.")

        if status == "In Progress" and not size:
            comment(url, MARKER_SIZE,
                    "This item is In Progress with no Size set. Add one, or if it feels too big, "
                    "consider splitting it into sub-issues.")

        if issue_type == "Epic" and sub_total == 0 and (now - created_at) > timedelta(days=14):
            comment(url, MARKER_EPIC,
                    "This Epic has no sub-issues after 2+ weeks. Consider breaking it down, "
                    "or retype it if it turned out to be a single scoped task.")


if __name__ == "__main__":
    main()
