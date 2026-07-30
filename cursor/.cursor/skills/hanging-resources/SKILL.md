---
name: hanging-resources
description: >-
  Identify hanging local resources and list them: idle cursor-agent sessions,
  stuck Hermes gateway restarts, idle Codex sandboxes, leftover git worktrees
  under ~/.traba/worktrees, and Docker leftovers. Use when the user asks about
  hanging resources, hanging items, leftover agents/worktrees, or wants a
  cleanup inventory.
---

# Hanging resources

Scan the machine for leftover agent/dev resources and **list** them.
Do **not** kill or remove anything unless the user explicitly asks.

## Quick start

Run the scanner:

```bash
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh"
```

Optional flags:

```bash
# Only one category
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh" --only agents
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh" --only worktrees
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh" --only hermes
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh" --only codex
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh" --only docker

# Treat cursor-agent idle after N minutes (default 30)
"$HOME/.cursor/skills/hanging-resources/scripts/scan.sh" --agent-idle-min 60
```

## What counts as hanging

| Category | Signal |
|----------|--------|
| **Idle cursor-agent** | `cursor-agent` process older than idle threshold, ~0% CPU. Exclude the current agent (this chat) when obvious. |
| **Stuck Hermes gateway** | `hermes_cli.main gateway restart` still running (any age). |
| **Idle Codex sandbox** | `codex sandbox` / related `node_repl` older than ~1h with ~0% CPU. Ignore the Codex app itself. |
| **Leftover worktrees** | Entries under `$TRABA_WORKTREES_ROOT` (default `~/.traba/worktrees`) registered via `git worktree list` on known repos (`traba`, `the-matrix` if present). Main checkouts are not hanging. |
| **Docker leftovers** | `docker ps -a` when the daemon is up. If the daemon is down, say so once — do not invent containers. |

Expected / not hanging by default:

- Active `cursor-agent` for this chat (young or using CPU)
- `tell daemon run`
- Language servers / MCP helpers / IDE helpers
- Live tmux sessions themselves (only report idle agents *inside* them)

## Report format

Lead with a one-line verdict (`clean` or `N hanging items`).

Then a table (or tight bullets) of findings only:

```markdown
| Category | Age | Detail | Suggested cleanup |
|----------|-----|--------|-------------------|
| Idle cursor-agent | 10h | pid 76723 · cwd praxis · ~608MB | kill pid |
| Leftover worktree | — | ~/.traba/worktrees/traba/ple-eng-… | git worktree remove --force |
```

Group by category. Skip empty categories.

End with: ask which items to kill/remove. Do not act until they say so.

## Cleanup (only when asked)

- **cursor-agent / hermes / codex sandbox:** `kill <pid>` (escalate to `kill -9` only if still alive after a few seconds).
- **Worktrees:** from the repo root:
  `git worktree remove --force <path>` then `git worktree prune`.
  Large `node_modules` trees are slow — say so; do not use `lsof +D` (too slow).
- Prefer removing only the paths/pids the user named. If they say “all”, remove every finding from the last scan.

## Notes

- Worktree layout matches [worktree-home](../worktree-home/SKILL.md): `$TRABA_WORKTREES_ROOT/<repo-slug>/<branch-slug>/`.
- Keep the report plain and short. No jargon pile-up.
