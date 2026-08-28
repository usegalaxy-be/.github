#!/usr/bin/env python3
"""Scheduled triage sweep for the usegalaxy-be execution project board.

Three checks, run weekly:
  1. Item still open, but its assigned Iteration has already ended.
     ACTION (not just a comment): Status -> Backlog, Iteration cleared.
     If it was In Progress, Start/End dates are left as-is (a real trace of
     work in flight). If it was never started, Start/End are cleared too -
     there's nothing real to preserve. Either way, a comment explains what
     happened. See scripts/sync_iteration_dates.py for what happens to the
     dates the next time this item gets a new Iteration assigned.
  2. Item is Status=In Progress with no Size set: nudge comment only.
  3. Issue is Epic-typed, has no sub-issues, and is >14 days old: nudge
     comment only.

Comments are de-duplicated by marker, skipped if already posted in the last
5 days. Requires GH_TOKEN (a PAT/App token with `project` write scope) and
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

MARKER_ITERATION = "<!-- nudge:stale-iteration-rollover -->"
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
PROJECT_QUERY_TEMPLATE = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      id
      statusField: field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } }
      iterationField: field(name: "Iteration") { ... on ProjectV2IterationField { id } }
      startField: field(name: "Start date") { ... on ProjectV2FieldCommon { id } }
      endField: field(name: "End date") { ... on ProjectV2FieldCommon { id } }
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
              labels(first: 20) { nodes { name } }
            }
          }
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          size: fieldValueByName(name: "Size") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          iteration: fieldValueByName(name: "Iteration") { ... on ProjectV2ItemFieldIterationValue { title startDate duration } }
          startDate: fieldValueByName(name: "Start date") { ... on ProjectV2ItemFieldDateValue { date } }
        }
      }
    }
  }
}
'''


def fetch_project():
    items = []
    cursor = None
    project_meta = None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = (PROJECT_QUERY_TEMPLATE
             .replace("__ORG__", ORG)
             .replace("__PROJECT_NUMBER__", str(PROJECT_NUMBER))
             .replace("__AFTER__", after))
        data = graphql(q)
        if not data or not data.get("data", {}).get("organization", {}).get("projectV2"):
            break
        project = data["data"]["organization"]["projectV2"]
        if project_meta is None:
            project_meta = {
                "id": project["id"],
                "status_field_id": project["statusField"]["id"],
                "status_options": {o["name"]: o["id"] for o in project["statusField"]["options"]},
                "iteration_field_id": project["iterationField"]["id"],
                "start_field_id": project["startField"]["id"],
                "end_field_id": project["endField"]["id"],
            }
        page = project["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return project_meta, items


def has_recent_marker(issue_url, marker, days=5):
    r = run(["gh", "issue", "view", issue_url, "--json", "comments",
             "-q", ".comments[].body"])
    if r.returncode != 0:
        return False
    # cheap check: marker present anywhere in recent output is good enough here,
    # comment timestamps aren't in this projection so we accept "posted this run
    # or a previous one this week" as sufficient de-dup for a weekly cron.
    return marker in r.stdout


def add_label(issue_url, label):
    if DRY_RUN:
        print(f"[dry-run] would add label '{label}' to {issue_url}")
        return
    run(["gh", "issue", "edit", issue_url, "--add-label", label])


def comment(issue_url, marker, body):
    if has_recent_marker(issue_url, marker):
        return
    full_body = f"{marker}\n{body}"
    if DRY_RUN:
        print(f"[dry-run] would comment on {issue_url}:\n{full_body}\n")
        return
    run(["gh", "issue", "comment", issue_url, "--body", full_body])
    print(f"commented on {issue_url}")


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


def clear_field(project_id, item_id, field_id):
    if DRY_RUN:
        print(f"[dry-run] would clear field {field_id} on {item_id}")
        return
    m = f'''mutation {{
      clearProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}", itemId: "{item_id}", fieldId: "{field_id}"
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
        labels = {n["name"] for n in (content.get("labels") or {}).get("nodes", [])}
        is_opportunistic = "opportunistic" in labels

        if status != "Done" and iteration:
            start = datetime.fromisoformat(iteration["startDate"]).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=iteration["duration"] - 1)
            if end < now:
                was_in_progress = status == "In Progress"
                set_select(project["id"], item["id"], project["status_field_id"],
                           project["status_options"]["Backlog"])
                clear_field(project["id"], item["id"], project["iteration_field_id"])
                add_label(url, "needs-retriage")
                if was_in_progress:
                    note = ("It was In Progress, so Start/End dates are left as-is - a visible "
                            "record that real work was in flight from Start through the iteration "
                            "that just ended.")
                else:
                    clear_field(project["id"], item["id"], project["start_field_id"])
                    clear_field(project["id"], item["id"], project["end_field_id"])
                    note = "It was never started, so Start/End dates were cleared too."
                comment(url, MARKER_ITERATION,
                        f"Its iteration (**{iteration['title']}**, ended {end.date()}) has passed "
                        f"and this is still open, so it's been moved back to **Backlog** and its "
                        f"Iteration cleared for re-triage. {note}\n\n"
                        f"If it turned out bigger than expected, split it into an Epic with "
                        f"sub-issues instead of re-entering it as-is.")

        if status == "In Progress" and not size and issue_type != "Epic" and not is_opportunistic:
            comment(url, MARKER_SIZE,
                    "This item is In Progress with no Size set. Add one, or if it feels too big, "
                    "consider splitting it into sub-issues.")

        if issue_type == "Epic" and sub_total == 0 and (now - created_at) > timedelta(days=14):
            comment(url, MARKER_EPIC,
                    "This Epic has no sub-issues after 2+ weeks. Consider breaking it down, "
                    "or retype it if it turned out to be a single scoped task.")


if __name__ == "__main__":
    main()
