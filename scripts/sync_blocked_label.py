#!/usr/bin/env python3
"""Mirror the `blocked` label on an issue to the project's Status field.

On label added: stash the current Status in a hidden marker comment, then
set Status=Blocked.
On label removed: read the stashed Status back from the marker comment and
restore it (defaults to Backlog if no marker is found).

Requires GH_TOKEN, ORG, PROJECT_NUMBER, REPO, ISSUE_NUMBER, ACTION env vars.
"""
import json
import os
import re
import subprocess
import sys

ORG = os.environ["ORG"]
PROJECT_NUMBER = os.environ["PROJECT_NUMBER"]
REPO = os.environ["REPO"]
ISSUE_NUMBER = os.environ["ISSUE_NUMBER"]
ACTION = os.environ["ACTION"]

ISSUE_URL = f"https://github.com/{ORG}/{REPO}/issues/{ISSUE_NUMBER}"
MARKER_RE = re.compile(r"<!-- blocked-sync:prev-status=(.*?) -->")

FIND_ITEM_QUERY = '''
query {
  organization(login: "__ORG__") {
    projectV2(number: __PROJECT_NUMBER__) {
      field(name: "Status") {
        ... on ProjectV2SingleSelectField { id options { id name } }
      }
      items(first: 100) {
        nodes {
          id
          content { ... on Issue { number repository { name } } }
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


def find_item_and_status_field():
    q = (FIND_ITEM_QUERY
         .replace("__ORG__", ORG)
         .replace("__PROJECT_NUMBER__", str(PROJECT_NUMBER)))
    data = graphql(q)
    if not data:
        return None, None, None
    project = data["data"]["organization"]["projectV2"]
    status_field = project["field"]
    for node in project["items"]["nodes"]:
        content = node.get("content")
        if not content:
            continue
        if content["repository"]["name"] == REPO and str(content["number"]) == str(ISSUE_NUMBER):
            current_status = (node.get("status") or {}).get("name")
            return node["id"], current_status, status_field
    return None, None, status_field


def set_status(project_id, item_id, field_id, option_id):
    m = f'''mutation {{
      updateProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}", itemId: "{item_id}", fieldId: "{field_id}",
        value: {{ singleSelectOptionId: "{option_id}" }}
      }}) {{ projectV2Item {{ id }} }}
    }}'''
    run(["gh", "api", "graphql", "-f", f"query={m}"])


def get_project_id():
    q = f'query {{ organization(login: "{ORG}") {{ projectV2(number: {PROJECT_NUMBER}) {{ id }} }} }}'
    data = graphql(q)
    return data["data"]["organization"]["projectV2"]["id"] if data else None


def get_prev_status_from_comments():
    r = run(["gh", "issue", "view", ISSUE_URL, "--json", "comments", "-q", ".comments[].body"])
    if r.returncode != 0:
        return "Backlog"
    matches = MARKER_RE.findall(r.stdout)
    return matches[-1] if matches else "Backlog"


def main():
    if not os.environ.get("GH_TOKEN"):
        print("GH_TOKEN not set, skipping (automation not yet activated)")
        return

    item_id, current_status, status_field = find_item_and_status_field()
    if not item_id or not status_field:
        print(f"no project item found for {ISSUE_URL}, skipping")
        return

    options = {o["name"]: o["id"] for o in status_field["options"]}
    project_id = get_project_id()

    if ACTION == "labeled":
        if current_status == "Blocked":
            return
        run(["gh", "issue", "comment", ISSUE_URL,
             "--body", f"<!-- blocked-sync:prev-status={current_status or 'Backlog'} -->\nMarked Blocked (label sync)."])
        set_status(project_id, item_id, status_field["id"], options["Blocked"])
    elif ACTION == "unlabeled":
        prev = get_prev_status_from_comments()
        if prev not in options:
            prev = "Backlog"
        set_status(project_id, item_id, status_field["id"], options[prev])
        run(["gh", "issue", "comment", ISSUE_URL,
             "--body", f"Restored Status={prev} (label sync)."])


if __name__ == "__main__":
    main()
