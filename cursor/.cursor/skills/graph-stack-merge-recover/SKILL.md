---
name: graph-stack-merge-recover
description: >-
  Recover unmerged upper-stack PRs after a parent Graphite PR merged and deleted
  its branch (child PR CLOSED but not MERGED). Cherry-pick onto main, force-push,
  open a new PR. Use when gh pr merge closed child PRs or stack upper layers were orphaned.
---

# Graphite stack merge recover

Upper stack PRs were **closed without merging** because the bottom PR merged and deleted its base branch.

## Detect

```bash
gh pr view <N> --repo <owner/repo> --json number,state,mergedAt,headRefName,baseRefName,title
```

Recover when **`state: CLOSED`** and **`mergedAt: null`**.

Also check siblings in the stack — often multiple children orphan at once.

## Recover one layer (worktree required)

Do **not** use the main checkout. Use `worktree-home` path for the repo.

### 1. Identify the stack-only commit(s)

The orphaned PR's branch may still exist locally/remotely:

```bash
git fetch origin
git log origin/<head-branch> --oneline -10
```

Find commits **not** already on `origin/main`. Often one commit per upper layer after squash-merge of lower layers.

If the branch was force-pushed during restack, use the old tip SHA from `gh pr view <N> --json commits` or reflog.

### 2. Cherry-pick onto main (not full rebase)

**Do not** `git rebase origin/main` the whole old stack — lower commits are already squashed on `main` and will conflict.

```bash
cd "$(~/.cursor/skills/worktree-home/scripts/wt-path.sh <branch>)"  # or existing worktree
git fetch origin
git checkout -B <branch> origin/main
git cherry-pick <stack-only-commit-sha>
```

If multiple stack-only commits, cherry-pick in order (oldest first).

### 3. Push and open new PR

```bash
git push -u origin <branch> --force-with-lease
gh pr create --repo <owner/repo> --head <branch> --base main \
  --title "<same [TICKET] title>" \
  --body "<note: follow-up after #<parent> merge, rebased onto main>"
```

`gh pr reopen` usually fails after branch deletion — create a new PR.

### 4. Repeat bottom-up

After the recovered PR merges, recover the next layer the same way (cherry-pick its unique commit onto updated `main`).

## Verify recovery commit is correct

```bash
git log origin/main..HEAD --oneline   # should show only this layer's commits
git diff origin/main...HEAD --stat    # should match original PR intent
```

## Prevent recurrence

Next time use **`graph-stack-merge-safe`**: merge bottom without `--delete-branch` until the stack is fully landed.

## Example (this session)

- #1801 merged → #1802/#1803 closed unmerged
- Cherry-pick stack2 commit onto `main` → new #1804
- Cherry-pick stack4 commit onto `main` → new #1805
