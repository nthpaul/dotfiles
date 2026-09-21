---
name: hanging-resources
description: >-
  Identify hanging local resources and list them: idle and headless
  cursor-agent / Claude / Grok / Codex processes (including grok -p,
  cursor-agent -p, claude -p, codex exec, orch wrappers), stuck Hermes
  gateway restarts, Docker leftovers, and git worktrees. Stale worktrees
  (no live process cwd inside) are removed, not listed for later. Use when
  the user asks about hanging resources, leftover agents/worktrees, or disk
  from old checkouts. Prefer the hanging-resources CLI — do not re-scan by hand.
---

# Hanging resources

Scan the machine for leftover agent/dev resources and **list** them.
Do **not** kill processes or remove Docker containers unless the user explicitly asks.

Stale worktrees are the exception: every run of this skill removes them before the report.
Run `hanging-resources clean worktrees --stale`. Do not ask which worktrees to remove.

## Command

Deterministic CLI (no model). On PATH as `hanging-resources`:

```bash
hanging-resources
hanging-resources --only agents
hanging-resources --only claude
hanging-resources --only grok
hanging-resources --only codex
hanging-resources --only orch
hanging-resources --only headless
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

Cleanup:

```bash
hanging-resources clean agents 30526
hanging-resources clean agents --all --dry-run
hanging-resources clean agents --all --kill-9

hanging-resources clean claude --all
hanging-resources clean grok 41200
hanging-resources clean orch --all
hanging-resources clean hermes --all
hanging-resources clean codex 1234

hanging-resources clean worktrees                  # stale checkouts; this is the run
hanging-resources clean worktrees --stale --dry-run
hanging-resources clean worktrees some-slug --force # in-use checkout, only when named

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
| **Idle cursor-agent** | Interactive `cursor-agent` older than idle threshold, ~0% CPU. Skips its own parent chain. Also matches `agent` (PATH symlink) and `~/.local/share/cursor-agent/…`. |
| **Headless cursor-agent** | `cursor-agent -p` / `--print` (orch workers included). Listed at any age / CPU. |
| **Idle Claude** | Interactive Claude Code CLI (`claude` or `~/.local/share/claude/versions/…`). Same idle rule. Skip the desktop app and slack-code-bridge. |
| **Headless Claude** | `claude -p` / `--print`. Listed at any age / CPU. |
| **Idle Grok** | Interactive `grok` / `~/.grok/bin/grok`. Same idle rule. Skip Grok Bot.app. |
| **Headless Grok** | `grok -p` / `--single` / `--prompt-file` / `--prompt-json`, plus `grok agent headless` / `stdio` / `serve`. Listed at any age / CPU. |
| **Orch wrappers** | `orch __wrap` parent of a headless grok/cursor worker. Listed at any age / CPU. |
| **Stuck Hermes gateway** | `hermes_cli.main gateway restart` still running (any age). |
| **Idle Codex** | Interactive Codex CLI (`codex` / `codex.js`), plus `codex sandbox` / `node_repl` (sandbox idle after ~1h). Skip the Codex app. |
| **Headless Codex** | `codex exec` (alias `e`). Listed at any age / CPU. |
| **Stale worktree** | A directory under a worktree root that has a `.git` file or directory, and no live process has its cwd inside it. Roots: `$TRABA_WORKTREES_ROOT` (default `~/.traba/worktrees`), `~/projects/worktrees`, `~/.grok/worktrees`, `~/.cursor/worktrees`, `~/.claude/worktrees`, one or two levels down. Main repos under `~/projects/<repo>` are not worktrees. |
| **Docker leftovers** | `docker ps -a` when the daemon is up. If the daemon is down, say so once — do not invent containers. |

Expected / not hanging by default:

- Active interactive `cursor-agent` / `claude` / `grok` / `codex` for this chat (young or using CPU)
- `tell daemon run`
- Language servers / MCP helpers / IDE helpers
- Live tmux sessions themselves (only report idle agents *inside* them)
- Headless `-p` / `exec` / `orch __wrap` processes **are** hanging — they are background leftovers even while busy

## Report format

Lead with the CLI verdict (`clean` or `N hanging item(s)`).

Then a table (or tight bullets) of findings only. Group by category. Skip empty categories.
Each item includes listen ports (`ports 3000, 8787` or `ports none`). Process rows include child listeners. Docker uses published ports. Worktrees are tagged `stale` or `in-use`, and include listeners whose cwd is in that tree.

For processes and Docker, end by asking which items to kill or remove. Do not act on those until they say so. Worktrees are already removed by the stale pass; report what went and which checkouts stayed because they are in use.

## Cleanup

- **Worktrees:** `hanging-resources clean worktrees --stale` on every run. In-use checkouts stay. A named in-use checkout needs `--force`. `--all` without `--force` is the stale set. Large `node_modules` trees are slow. Do not use `lsof +D`.
- **cursor-agent / claude / grok / orch / hermes / codex:** `hanging-resources clean agents|claude|grok|orch|hermes|codex <pid>` (add `--kill-9` if TERM is not enough).
- **Docker:** `hanging-resources clean docker <id|name>`. Running containers need `--force`.
- For processes and Docker, remove only the paths or pids the user named. If they say “all”, `hanging-resources clean <type> --all` (show `--dry-run` first if they might not want the whole set).

## Notes

- Worktree layout matches [worktree-home](../worktree-home/SKILL.md): `$TRABA_WORKTREES_ROOT/<repo-slug>/<branch-slug>/`.
- Keep the report plain and short. No jargon pile-up.
- On PATH via stowed zshrc (`~/.cursor/skills/hanging-resources/scripts`), same pattern as `agent-tell`. New shell or `exec zsh`.
