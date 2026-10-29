This PR addresses [issue title](link).

<!-- Skip the line above when there is no issue. Add "Closes owner/repo#N" on its own line only when merging is the deploy. -->

<!-- What changes, in a few plain sentences. -->

## How to test

After deploying to test:
- <!-- One simple check per change: a tool run in the UI, or one copy-pasteable command. -->

After deploying to prod:
- <!-- The same check on prod. -->

## How to deploy

<!-- Delete this section when merging is the deploy. -->

```
# cd into the worktree
git fetch origin && git merge origin/main
ansible-playbook <playbook> --limit <test hosts> --check --diff
ansible-playbook <playbook> --limit <test hosts>
```

Then the same for prod.

## RFC

<!-- Link the RFC this change depends on, or delete this section. -->
