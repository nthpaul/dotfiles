# Board

`codex-orch board` reads `state.sqlite3` read-only for every team in `--home` and each extra `--homes` path. Mutations use the home coordinator token against `op=command`. Board does not write SQLite and does not send fields `cmd_register` ignores.

## Keys

| Key | Action |
| --- | --- |
| `tab` / `1-9` | Sections: teams, tasks, epochs, revisions, attempts, workers, inbox, issues, deliveries, operations, resources |
| `j` / `k` | Move |
| `t` | Next team in this home |
| `n` | Next home |
| `/` | Filter |
| `enter` | Toggle detail |
| `a` | Focus the exact owned live tmux pane (`socket` + `@window` + `%pane`) |
| `p` / `r` / `x` | `control` pause / resume / cancel |
| `h` / `H` | `hold` / clear hold (`filter` text is the reason, else `board`) |
| `q` | Quit |

`--snapshot` (and non-TTY stdout) prints the same layout at `--width` x `--height`. `status`, `history`, `inbox`, `bulletin`, and pane `display.py` stay.

## Honesty

- **Requested** is `runs.desired`, the last `control_requested` / hold list, or the command just sent.
- **Observed** is `runs.observed`, `runs.health`, `runs.released`, pane probe, and `operations.state`.
- A successful request is not an observed stop. `REQUESTED!=OBSERVED` stays until they match.
- Pane probe states: `live`, `dead`, `missing`, `stale`, `unknown`. Attach only `live` owned panes.
- Stale coordinator epoch or missing credentials: show the error and do not send `op=command`. Do not takeover from the board.
- Usage is the stored `runner_usage` event or `runs/<run_id>/usage.json` (`baseline` / `current` / `delta`). Print keys that exist. Do not invent `0`. No object means `usage unknown`.
- PR exact-head: `operations.intent.expected_head` versus `outcome.head` / `passed` / `stack` / `reason`. Missing outcome is `unchecked`.
- Do not render tokens, `token_hash`, runner logs, or `reasoning` / `thinking` / `prompt` body keys.

## Commands the board does not wrap

`request budget`, `request preflight`, and `request ci_watch` stay generic `request KIND --body` from the coordinator session. Register defaults to grok-4.6 high; pass `--mode exec` only when the assignment needs the headless path.
