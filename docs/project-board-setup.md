# Activating the board automation

One-time setup, done by whoever administers the execution project board. Two parts: settings GitHub doesn't expose via API (manual, in the UI), and the Actions in this repo (need a secret before they do anything).

## 1. Built-in project workflows (UI only)

GitHub doesn't expose creating/editing a Project's built-in workflows via API, so this has to be done by hand: open the project board -> `...` menu (top right) -> **Workflows**. Configure:

| Trigger | Action |
|---|---|
| Item added to project | Set Status: Backlog |
| Item reopened | Set Status: Backlog |
| Item closed | Set Status: Done |
| Auto-archive items | Archive items where Status = Done, 14 days after being set |

Deliberately **not** configuring "Pull request merged -> Status: Done" - see the Pull requests section in CONTRIBUTING.md. Merging isn't deploying for most of this work, and that rule fires on any linked PR merging regardless of deploy state or how many other PRs are still open on the same issue. Closing (via `Closes #123` on a merge-is-deploy repo, or by hand once a deploy is verified) is the only thing that should set Done.

Also confirm **auto-add** (same menu) is scoped to include all 9 tracked repos.

## 2. Activating the Actions in this repo

The workflows in `.github/workflows/` here (`scheduled-nudges.yml`, `sync-iteration-dates.yml`, `sync-okr-inheritance.yml`, `label-status-sync.yml`) are committed but inert - every job checks for a `PROJECTS_TOKEN` secret and no-ops if it's missing, so nothing runs or fails noisily until you turn it on.

To activate:

1. Create a token with `project` (read/write) and `repo` scope. A fine-grained PAT from a bot/service account is preferable to a personal PAT, since this token will act as whichever account owns it (comments, status changes) - a GitHub App would be the more correct long-term answer, but a PAT is the quicker path to start.
2. Add it as an **organization secret** named `PROJECTS_TOKEN`, scoped to this repo and the 9 tracked repos (org Settings -> Secrets and variables -> Actions).
3. Add an **organization variable** named `PROJECT_NUMBER` set to the number of the live execution board (org Settings -> Secrets and variables -> Actions -> Variables tab). Also update `projects: ["usegalaxy-be/8"]` in both issue templates (`.github/ISSUE_TEMPLATE/*.yml`) to match - currently hardcoded to `#8` until the `#8`/`#12` migration decision is made.
4. Add the caller workflow (`templates/label-status-sync-caller.yml` in this repo) to each of the 9 tracked repos' `.github/workflows/` directory - already done as part of this rollout, nothing further needed unless a new repo joins the tracked set later.
5. Trigger `scheduled-nudges.yml` manually once via **Run workflow** (with `dry_run: true` first) to confirm it can reach the project before waiting for the next Monday cron.

## Tracked repos

infrastructure-playbook, usegalaxy-be-tools, galaxytools, usegalaxy-be-doc, usegalaxy-be.github.io, infrastructure, pulsar-deployment, metrics_internal, issues
