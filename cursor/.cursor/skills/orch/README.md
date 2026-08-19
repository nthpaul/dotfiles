# orch

Personal CLI. Spawn Grok or Cursor workers on a **named team**, then list, steer, and kill them.

Home: `~/.cursor/skills/orch/`
State: `$ORCH_HOME` (default `~/.orch`)
Script: `scripts/orch` (also `~/.local/bin/orch`)

## Skills (how a Cursor pane becomes the orch)

| Skill | What it does |
|---|---|
| **orch** | You are the orch. Pick team + default mode, then only spawn/list/tell/kill. |
| **orch-headless** | Same, default `--mode headless` for the session. |
| **orch-tell** | Same, default `--mode tell` (live grok and cursor panes). |

Say `/orch`, `/orch-headless`, or `/orch-tell` — or “you’re the orch”. The pane stamps `orch team=… default-mode=…` once and does not implement.

## Install

zshrc already has PATH + completion (after hanging-resources, before the grok installer):

```bash
export PATH="$HOME/.cursor/skills/orch/scripts:$PATH"
```

New terminal, or:

```bash
exec zsh
```

Then `orch` and Tab should work.

If the command is missing:

```bash
ln -sf "$HOME/.cursor/skills/orch/scripts/orch" "$HOME/.local/bin/orch"
"$HOME/.cursor/skills/orch/scripts/orch"
```

## Cheat sheet

```bash
orch                         # cheat sheet (not argparse)
orch -h | --help             # same + usage
orch help [command]          # one command, with examples

orch teams
orch claim --team T
orch release --team T

orch spawn --team T --mode headless|tell grok|cursor JOB...
    [--cwd DIR] [--name SCIENTIST] [--id ID] [--steal]

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

`--team` required on spawn / list (except `--all`) / status / logs / result / kill / tell / claim / release.
Default `--mode` is `headless`.

`orch list` prints the team's orch lock (`pid` live/dead, or unclaimed), then workers.
`orch list --all` groups that by team.

## Headless (default)

Background process. Logs and a result file under the team's `jobs/`. No pane. No `tell`.

```bash
orch claim --team fleet-ops
orch spawn --team fleet-ops --mode headless grok "fix the flaky test"
orch spawn --team fleet-ops --cwd ~/projects/the-matrix cursor "summarize open Slack threads"

orch list --team fleet-ops
orch status --team fleet-ops w1a2b3c4
orch logs --team fleet-ops w1a2b3c4 -f
orch result --team fleet-ops w1a2b3c4
orch kill --team fleet-ops w1a2b3c4
```

Grok: `grok -p …`. Cursor: `cursor-agent -p …`. When the process exits, `result.json` gets ok / exit code / a short stdout summary.

## Tell (live pane)

tmux window you can attach. Grok or Cursor. Orch claims a scientist name and you steer with `orch tell`.

```bash
orch spawn --team fleet-ops --mode tell grok "fix the flaky test"
orch spawn --team fleet-ops --mode tell --name curie cursor "watch Slack for X"
orch list --team fleet-ops
orch tell --team fleet-ops w1a2b3c4 --ask "now pull the GitHub PRs"
orch tell --team fleet-ops w1a2b3c4 --status "idle"
orch kill --team fleet-ops w1a2b3c4
```

`orch tell` is `tell NAME --ask|--status` for that worker. Same team only. Worker must be `--mode tell`.

Grok panes skip Cursor's `i` / `C-u` inject (those keys scroll or type a letter in Grok). telld reads `@orch_kind` on the pane.

## What kill does

Stops that team's worker. Drops the row from `workers.json`.

| Mode | Kill |
|------|------|
| **headless** | SIGTERM the process |
| **tell** | Unclaim the scientist (`@scientist` + roster name), `tmux kill-window` (or pane), SIGTERM the pid if still up |

`orch kill --team T --all` does that for every worker on the team.

Does **not** delete git worktrees.

spawn / kill / tell auto-claim the team if the lock is free or the lock pid is dead. A live other orch on the team → refuse unless `--steal`.
