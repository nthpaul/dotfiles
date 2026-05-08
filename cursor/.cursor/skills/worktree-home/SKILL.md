---
name: worktree-home
description: >-
  Resolves and creates git worktrees under one canonical directory with deterministic
  folder names from branch names. Use when the user or agent needs a worktree, parallel
  branches, or a second checkout; when avoiding ad-hoc ../ paths; or when looking for
  an existing worktree.
---

# Worktree home (lightweight)

## Canonical location (single place to look)

All worktrees for this repository live under **one root**, so agents and humans only need to list one directory to see what already exists.

**Root directory:** `$TRABA_WORKTREES_ROOT` (default: `~/.traba/worktrees`)

**Layout:**

```text
$TRABA_WORKTREES_ROOT/<repo-slug>/<branch-slug>/
```

- **repo-slug:** basename of the repository root (e.g. `traba` for `.../traba`), or override with `TRABA_WORKTREE_REPO_SLUG` when multiple clones share the same basename.
- **branch-slug:** the full branch name with every `/` replaced by `-` (one-to-one, deterministic).

**Examples:**

| Branch                 | `branch-slug`                    |
| ---------------------- | -------------------------------- |
| `main`                 | `main`                           |
| `ple/eng-18856-foo`   | `ple-eng-18856-foo`            |

**Resolve path (before or after the worktree exists):**

```bash
"$HOME/.cursor/skills/worktree-home/scripts/wt-path.sh"
"$HOME/.cursor/skills/worktree-home/scripts/wt-path.sh" ple/eng-18856-foo
```

The script only prints the path. Same branch → same path, always.

## Agent checklist

1. **Discover existing worktrees:** `ls "$TRABA_WORKTREES_ROOT/<repo-slug>"` (use default root if env unset).
2. **Path for a branch:** run `wt-path.sh <branch>` from any directory inside the repo.
3. **Create** (when needed), using the path from `wt-path.sh` — e.g.  
   `git worktree add "$("$HOME/.cursor/skills/worktree-home/scripts/wt-path.sh" my/feature)" -b my/feature`  
   or, if the branch already exists,  
   `git worktree add "$("$HOME/.cursor/skills/worktree-home/scripts/wt-path.sh" my/feature)" my/feature`
4. **Do not** place agent worktrees in arbitrary `../` siblings; use this layout only so every agent knows where to look.

## When `wt` (shell helper) is used

If the user’s `wt` helper creates worktrees, it should be configured to use the **same** root and the **same** slug rule as `wt-path.sh`, or call `wt-path.sh` to obtain the path. Otherwise the “one place to look” rule breaks.

## Optional local overrides

| Env                         | Purpose                                          |
| --------------------------- | ------------------------------------------------ |
| `TRABA_WORKTREES_ROOT`      | Base directory (default `~/.traba/worktrees`)  |
| `TRABA_WORKTREE_REPO_SLUG`  | Subfolder name when basename is ambiguous     |
