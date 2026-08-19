---
name: orch
description: >-
  Spawn and steer a team of Grok or Cursor workers with the orch CLI.
  Use when the user wants orch, a named team, headless grok/cursor jobs,
  tell-mode panes, or to claim/list/status/logs/kill workers. Prefer the
  orch CLI — do not spawn workers by hand.
---

# orch

One CLI for a **team** of workers. Orch spawns, lists, steers, and kills.
It does not do the work.

State: `$ORCH_HOME` (default `~/.orch`). Tab: `orch` then Tab (`exec zsh` if new).

## When to use

- User says orch, team, spawn a grok/cursor worker, or kill a worker
- Headless fire-and-forget jobs, or a live tell pane they can watch
- Do **not** start `grok` / `cursor-agent` / tmux by hand for this

## Cheat sheet

```bash
orch                         # cheat sheet
orch help spawn              # one command + examples

orch teams
orch claim --team T
orch release --team T

orch spawn --team T --mode headless grok JOB
orch spawn --team T --mode tell cursor JOB

orch list --team T
orch list --all
orch status --team T ID
orch logs --team T ID [-f]
orch result --team T ID

orch kill --team T ID
orch kill --team T --all

orch tell --team T ID --ask "..."
orch tell --team T ID --status "..."
```

`--team` is required on spawn / list (unless `--all`) / status / logs / result / kill / tell / claim / release.

## Team rule

Workers belong to one team. List, kill, tell, and job files never cross teams.
Two live orchs on the same team: refuse unless `--steal`.
spawn / kill / tell auto-claim if the lock is free or the lock pid is dead.

Team names: `[a-z][a-z0-9-]{0,31}`. Worker ids: `w` + 8 hex (`w1a2b3c4`).

## Modes (tell vs headless)

| Mode | What you get | Kinds |
|------|----------------|-------|
| **headless** (default) | Background process. Result under the team's `jobs/`. No pane. No `tell`. | grok or cursor |
| **tell** | tmux window you can attach. Scientist name. Steer with `orch tell`. | **cursor only** in v1 |

`tell` + `grok` → exit 2: Grok tell is not v1; use `--mode headless`.

Do not run both modes on the same worker. Do not tell across teams.

`orch tell` is `tell NAME --ask|--status` for a **tell-mode** worker on that team.
That is not a headless result file.

## Kill

Stops that team's worker. Drops it from `workers.json`.

- **Headless:** SIGTERM the process
- **Tell:** unclaim the scientist, kill the tmux window, SIGTERM the pid if still up
- Does **not** delete git worktrees
