---
name: graph-stack-merge-safe
description: >-
  Merge a Graphite PR stack bottom-up without orphaning child PRs. Use when the
  user asks to merge a stack, land stacked PRs, or squash-merge Graphite branches.
  Pairs with graph-stack-merge-order and graph-stack-merge-recover.
---

# Graphite stack merge (safe)

Merge stacked PRs **bottom → top** without closing upper PRs unmerged.

## When to use

- User says "merge the stack", "land the PRs", "merge in order"
- After `loop-stack` reports merge-ready
- **Not** for a single standalone PR (use `gh pr merge` directly)

## Preconditions

1. Every PR in the stack: required CI green, zero unresolved threads (`loop-stack` exit condition).
2. Read **`graph-stack-merge-order`** if the stack spans multiple repos.
3. List stack PRs: `gt log short` + `gh pr list --head <branch> --json number,title,state`.

## Safe merge procedure

### Preferred: Graphite merge

If Graphite merge queue / `gt merge` is available for the repo, use that — it handles stack ordering and branch retention.

### Manual: `gh pr merge` bottom-up

For each PR from bottom to top:

```bash
gh pr view <N> --repo <owner/repo> --json mergeable,mergeStateStatus,state
gh pr merge <N> --repo <owner/repo> --squash
# Do NOT pass --delete-branch until the entire stack is merged
```

**Critical:** omit `--delete-branch` on every merge **except optionally the top PR after the last merge succeeds**.

### Why

Squash-merging the bottom PR with `--delete-branch` deletes its head branch. Child PRs often target that branch as `baseRefName`. GitHub **closes** them without merging — upper stack commits never reach `main`.

Observed failure mode: parent #1801 merged with branch delete → #1802 and #1803 closed, unmerged.

## After each merge

1. Confirm merge: `gh pr view <N> --json state,mergedAt` → `MERGED`.
2. Check child PR state before merging next:

```bash
gh pr view <child-N> --repo <owner/repo> --json state,mergedAt,baseRefName,mergeable
```

If child is `CLOSED` with `mergedAt: null` → stop manual merge; use **`graph-stack-merge-recover`**.

3. If child is still `OPEN` with `baseRefName: main` (Graphite retargeted) → continue.

## After full stack landed

Optional cleanup:

```bash
gh pr merge <top-N> --repo <owner/repo> --squash --delete-branch  # top only
```

Run **`git fetch origin main && git log origin/main --oneline -10`** to confirm every intended change is on `main`.

## Pair with

| Skill | Role |
|-------|------|
| `graph-stack-merge-order` | Cross-repo / dependency ordering |
| `graph-stack-merge-recover` | Child PR closed after parent merge |
| `loop-stack` | Pre-merge CI + thread gate |
| `pr-stack-ship` | Push fixes before merge |
