---
name: hanging-resources
description: >-
  Identify hanging local resources and list them: idle cursor-agent, Claude,
  Grok, and Codex sessions, stuck Hermes gateway restarts, leftover git
  worktrees under ~/.traba/worktrees, and Docker leftovers. Use when the user
  asks about hanging resources, hanging items, leftover agents/worktrees, or
  wants a cleanup inventory. Prefer the hanging-resources CLI — do not re-scan
  by hand.
---

# Hanging resources

Scan the machine for leftover agent/dev resources and **list** them.
Do **not** kill or remove anything unless the user explicitly asks.

## Command

Deterministic CLI (no model). On PATH as `hanging-resources`:

```bash
hanging-resources
hanging-resources --only agents
hanging-resources --only claude
hanging-resources --only grok
hanging-resources --only codex
hanging-resources --only worktrees
hanging-resources --only hermes
hanging-resources --only docker
hanging-resources --agent-idle-min 60
```

Tab completion (zsh): type `hanging-resources` then Tab. Needs a new terminal, or `exec zsh`.

If the command is missing, the script is:

```bash
"$HOME/.cursor/skills/hanging-resources/scripts/hanging-resources"
```

(`scripts/scan.sh` is a thin wrapper around `hanging-resources scan`.)

Cleanup (only when the user names targets, or `--all` for that type):

```bash
hanging-resources clean agents 30526
hanging-resources clean agents --all --dry-run
hanging-resources clean agents --all --kill-9

hanging-resources clean claude --all
hanging-resources clean grok 41200
hanging-resources clean hermes --all
hanging-resources clean codex 1234

hanging-resources clean worktrees ple-eng-23589-adjust-empty-break-clear
hanging-resources clean worktrees traba/ple-eng-23593-ops-failure-kind-stamp
hanging-resources clean worktrees --all --dry-run

hanging-resources clean docker kafka
hanging-resources clean docker cc37134712fe
hanging-resources clean docker --all --dry-run
hanging-resources clean docker postgres_local --force
```

`--all` for docker skips running containers unless you also pass `--force`.
`--dry-run` prints the plan and does nothing.

## What counts as hanging

| Category | Signal |
|----------|--------|
| **Idle cursor-agent** | `cursor-agent` process older than idle threshold, ~0% CPU. The CLI skips its own parent chain. |
| **Idle Claude** | Claude Code CLI (`claude` or `~/.local/share/claude/versions/…`). Same idle rule. Skip the desktop app and slack-code-bridge. |
| **Idle Grok** | `grok` / `~/.grok/bin/grok` (including `grok -p` orch workers). Same idle rule. |
| **Stuck Hermes gateway** | `hermes_cli.main gateway restart` still running (any age). |
| **Idle Codex** | Codex CLI (`codex` / `codex.js`), plus `codex sandbox` / `node_repl` (sandbox idle after ~1h). Skip the Codex app. |
| **Leftover worktrees** | Entries under `$TRABA_WORKTREES_ROOT` (default `~/.traba/worktrees`) registered via `git worktree list` on known repos (`traba`, `the-matrix` if present). Main checkouts are not hanging. |
| **Docker leftovers** | `docker ps -a` when the daemon is up. If the daemon is down, say so once — do not invent containers. |

Expected / not hanging by default:

- Active `cursor-agent` / `claude` / `grok` / `codex` for this chat (young or using CPU)
- `tell daemon run`
- Language servers / MCP helpers / IDE helpers
- Live tmux sessions themselves (only report idle agents *inside* them)

## Report format

Lead with the CLI verdict (`clean` or `N hanging item(s)`).

Then a table (or tight bullets) of findings only. Group by category. Skip empty categories.
Each item includes listen ports (`ports 3000, 8787` or `ports none`). Process rows include child listeners. Docker uses published ports. Worktrees include listeners whose cwd is in that tree.

End with: ask which items to kill/remove. Do not act until they say so.

## Cleanup (only when asked)

- **cursor-agent / claude / grok / hermes / codex:** `hanging-resources clean agents|claude|grok|hermes|codex <pid>` (add `--kill-9` if TERM is not enough).
- **Worktrees:** `hanging-resources clean worktrees <path|repo/slug|slug>`. Large `node_modules` trees are slow — say so; do not use `lsof +D` (too slow).
- **Docker:** `hanging-resources clean docker <id|name>`. Running containers need `--force`.
- Prefer removing only the paths/pids the user named. If they say “all”, `hanging-resources clean <type> --all` (show `--dry-run` first if they might not want the whole set).

## Notes

- Worktree layout matches [worktree-home](../worktree-home/SKILL.md): `$TRABA_WORKTREES_ROOT/<repo-slug>/<branch-slug>/`.
- Keep the report plain and short. No jargon pile-up.
- On PATH via stowed zshrc (`~/.cursor/skills/hanging-resources/scripts`), same pattern as `agent-tell`. New shell or `exec zsh`.
