#!/usr/bin/env python3
"""Keep upcoming iterations on the project's Iteration field.

GitHub does not add iterations by itself, so without this the board runs out
and triage has nothing to schedule into. Makes sure at least AHEAD iterations
start after today, each as long as the field's default duration and named
"Iteration <n>" after the highest existing number.

updateProjectV2Field replaces the whole iteration list. Every existing
iteration, completed ones included, is sent back with its id: an iteration
left out or sent without its id would be deleted or recreated, clearing it
from every item that has it. After writing, the script re-reads the field and
fails if any existing id or date changed.

Requires GH_TOKEN, PROJECT_NUMBER. OWNER_TYPE is "organization" (default) or
"user", for testing on a personal project. No-ops cleanly if GH_TOKEN is unset.
"""
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta

ORG = os.environ.get("ORG", "usegalaxy-be")
OWNER_TYPE = os.environ.get("OWNER_TYPE", "organization")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER")
AHEAD = int(os.environ.get("AHEAD", "2"))
DRY_RUN = os.environ.get("DRY_RUN") == "true"

FIELD_QUERY = '''
query($login: String!, $number: Int!) {
  owner: __OWNER_TYPE__(login: $login) {
    projectV2(number: $number) {
      field(name: "Iteration") {
        ... on ProjectV2IterationField {
          id
          configuration {
            startDay
            duration
            iterations { id title startDate duration }
            completedIterations { id title startDate duration }
          }
        }
      }
    }
  }
}
'''

UPDATE_MUTATION = '''
mutation($fieldId: ID!, $config: ProjectV2IterationFieldConfigurationInput!) {
  updateProjectV2Field(input: {fieldId: $fieldId, iterationConfiguration: $config}) {
    projectV2Field { ... on ProjectV2IterationField { id } }
  }
}
'''


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables})
    r = subprocess.run(["gh", "api", "graphql", "--input", "-"],
                       input=body, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"graphql failed:\n{r.stderr}", file=sys.stderr)
        return None
    data = json.loads(r.stdout)
    if data.get("errors"):
        print(f"graphql errors: {data['errors']}", file=sys.stderr)
        return None
    return data["data"]


def fetch_field():
    query = FIELD_QUERY.replace("__OWNER_TYPE__", OWNER_TYPE)
    data = graphql(query, {"login": ORG, "number": int(PROJECT_NUMBER)})
    try:
        return data["owner"]["projectV2"]["field"]
    except (TypeError, KeyError):
        return None


def all_iterations(field):
    conf = field["configuration"]
    its = conf["completedIterations"] + conf["iterations"]
    return sorted(its, key=lambda i: i["startDate"])


def main():
    if not os.environ.get("GH_TOKEN"):
        print("GH_TOKEN not set, skipping (automation not yet activated)")
        return
    if not PROJECT_NUMBER:
        print("PROJECT_NUMBER not set, skipping")
        return

    field = fetch_field()
    if not field or not field.get("id"):
        print("could not load Iteration field, skipping")
        return
    existing = all_iterations(field)
    if not existing:
        print("Iteration field has no iterations, set the first one in the UI")
        return

    duration = field["configuration"]["duration"]
    today = date.today()
    numbers = [int(m.group(1)) for i in existing if (m := re.fullmatch(r"Iteration (\d+)", i["title"]))]
    next_number = max(numbers, default=len(existing)) + 1
    last = existing[-1]
    next_start = date.fromisoformat(last["startDate"]) + timedelta(days=last["duration"])

    upcoming = [i for i in existing if date.fromisoformat(i["startDate"]) > today]
    new = []
    while len(upcoming) + len(new) < AHEAD or next_start <= today:
        new.append({"title": f"Iteration {next_number}", "startDate": str(next_start), "duration": duration})
        next_number += 1
        next_start += timedelta(days=duration)

    if not new:
        print(f"{len(upcoming)} upcoming iteration(s) already, nothing to add")
        return
    for i in new:
        print(f"adding {i['title']} starting {i['startDate']} ({i['duration']} days)")
    if DRY_RUN:
        print("[dry-run] not writing")
        return

    keep = [{"id": i["id"], "title": i["title"], "startDate": i["startDate"], "duration": i["duration"]}
            for i in existing]
    config = {"startDate": existing[0]["startDate"], "duration": duration, "iterations": keep + new}
    if graphql(UPDATE_MUTATION, {"fieldId": field["id"], "config": config}) is None:
        sys.exit(1)

    after = {i["id"]: i for i in all_iterations(fetch_field() or {"configuration": {
        "completedIterations": [], "iterations": []}})}
    broken = [i["title"] for i in existing
              if i["id"] not in after or after[i["id"]]["startDate"] != i["startDate"]]
    if broken:
        print(f"ERROR: existing iterations changed or lost their id: {broken}", file=sys.stderr)
        sys.exit(1)
    added = [i["title"] for i in after.values() if i["title"] in {n["title"] for n in new}]
    print(f"done, existing iterations unchanged, added {added}")


if __name__ == "__main__":
    main()
