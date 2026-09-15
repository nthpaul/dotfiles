> Headless Grok bridge implementation and rollout: [guide](docs/grok-bridge.md),
> [acceptance evidence](docs/grok-pilot.md), [PDF baseline](docs/astra-grok-plan.pdf).
> The legacy runtime below remains available; cutover is gated by the pilot record.

# Local orchestration runtime

`codex-orch` runs a local SQLite daemon, bounded worker processes, and durable coordinator inboxes. Astra owns assignments, plan revisions, routing, and acceptance. Workers report through the daemon. `register` defaults to Grok `grok-4.6` with high reasoning in the owned worker pane. Explicit `--adapter codex` keeps Codex `gpt-6-astra` / medium. `--adapter fake` is the deterministic offline fixture. `--mode exec` keeps the current `codex exec` / `grok --single` / fake JSONL path. Codex workers inherit your Codex approval and sandbox configuration.

This directory documents the implemented runtime. Architecture proposals under `../plans/` describe broader designs and do not establish executable capabilities or completed validation gates.

## Start

Requires Python 3.11 or newer. The dotfiles wrapper is `../../.local/bin/codex-orch`; after linking the `codex` stow package it is available at `~/.local/bin/codex-orch`. It loads this source tree without package installation. Alternatively, from this directory use `python3 -m orchestrator`.

Check local capabilities and start the daemon:

```sh
codex-orch doctor
codex-orch start
```

`doctor` checks Python and SQLite JSON/STRICT support in memory and locates optional provider, tmux, git, Graphite, and GitHub tools. Missing optional tools report unavailable capabilities; they do not prevent offline operation. It does not open runtime state, inspect credentials, or contact providers.

`start` launches a detached local daemon with a private `daemon.log`, waits up to five seconds for readiness, and prints the PID and paths. Repeated calls return the existing daemon. For foreground operation use `codex-orch daemon --home ~/.codex/orchestration`.

Initialize a team:

```sh
codex-orch init 'Deliver the scoped objective'
codex-orch register implementer
codex-orch board
codex-orch status
codex-orch inbox --priority urgent
```

`board` is the full-screen TUI over every team in `--home`, plus extra homes from repeated `--homes`. Non-TTY stdout and `--snapshot` print a deterministic layout for QA (`--width` / `--height`). Keyboard: `tab` or `1-9` sections, `j`/`k` rows, `t` team, `n` home, `/` filter, `a` attach the exact owned live tmux pane, `p`/`r`/`x` pause/resume/cancel, `h` hold. Controls go through the authenticated daemon API only. The status line labels **requested** desired state separately from **observed** run/pane/operation state. Missing, dead, stale, and unknown panes are named as such and are not focused. Usage prints stored `runner_usage` / `runs/<id>/usage.json` keys; a missing key stays absent (`usage unknown` when there is no object). Existing `status`, `history`, `inbox`, `bulletin`, and pane `display.py` stay.

The default state directory is `~/.codex/orchestration`; `--home` works before or after the subcommand. State includes `state.sqlite3`, artifacts, execution logs, and credential files. Credentials are written with mode 0600. Initialization saves coordinator credentials to `HOME/coordinator.json`; registration saves worker credentials under `HOME/workers/`. Output shows the credential path without revealing the token. Use `--credentials PATH` to select another session. Keep this state outside the source repository.

Inside tmux, `init` automatically resolves the current pane to its exact socket and window; focus is preserved. Use `init --headless` to disable pane allocation, or explicitly select both target handles:

```sh
codex-orch init 'Visible worker team' \
  --tmux-socket "$(tmux display-message -p '#{socket_path}')" \
  --tmux-window "$(tmux display-message -p '#{window_id}')"
```

Use a fresh state directory or credential destination for another team. Pane allocation preserves focus, tiles the window, reuses dead team-owned panes, and queues allocation when capacity is reached. Cleanup verifies team, agent, and worker-purpose tags. The socket and `@window` are exact handles, not names resolved against the current client.

## Offline two-task exercise

Use a dedicated home and start its daemon:

```sh
codex-orch start --home /tmp/codex-orch-example
```

The commands below need no provider account or network. Fake scripts can be embedded as an actual `FAKE_SCRIPT={...}` line in the task objective; the runner appends the objective as readable text after the JSON contract. `field` extracts a JSON response field using Python.

```sh
orch() { codex-orch --home /tmp/codex-orch-example "$@"; }
field() { python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
orch init 'Check two bounded fake tasks and request one revision' --headless
SESSION_A=$(orch register worker-a --adapter fake | field session_id)
SESSION_B=$(orch register worker-b --adapter fake | field session_id)
orch request task --body '{"task_id":"example-a","spec":{"objective":"Return first fixture result","expected_output":"Result text","criteria":[],"write":false}}'
orch request task --body '{"task_id":"example-b","spec":{"objective":"Return second fixture result","expected_output":"Result text","criteria":[],"write":false}}'
RUN_A=$(orch request assign --body "{\"task_id\":\"example-a\",\"session_id\":\"$SESSION_A\"}" | field run_id)
RUN_B=$(orch request assign --body "{\"task_id\":\"example-b\",\"session_id\":\"$SESSION_B\"}" | field run_id)
orch status
orch inbox
```

Poll `status` until both runs have a `result_event` and `released: 1`. Inspect each result and its finalized artifact through `history --run-id "$RUN_A"` and the corresponding artifact path in runtime state. The daemon finalizes result text as evidence. Empty `criteria` here exercises the fixture; real tasks should name meaningful acceptance criteria.

```sh
orch request review --body "{\"run_id\":\"$RUN_A\",\"decision\":\"revise\",\"reason\":\"Exercise a second attempt before acceptance\"}"
RUN_A2=$(orch request assign --body "{\"task_id\":\"example-a\",\"session_id\":\"$SESSION_A\"}" | field run_id)
orch status
```

After inspecting the second result and confirming its process is released:

```sh
orch request review --body "{\"run_id\":\"$RUN_A2\",\"decision\":\"accept\",\"reason\":\"Inspected finalized fixture result\",\"checks\":[]}"
orch request review --body "{\"run_id\":\"$RUN_B\",\"decision\":\"accept\",\"reason\":\"Inspected finalized fixture result\",\"checks\":[]}"
orch request finish --body '{}'
orch shutdown
```

## Commands and evidence

`request KIND --body JSON` sends any supported command. `--body @PATH` reads a JSON object from a file. Initialization and every mutation print their request ID to stderr before contacting the daemon. Supply `--request-id ID` to retry a lost response; the same ID must carry the same body and coordinator epoch. A new request ID denotes a new action.

| Command kind | Body fields |
| --- | --- |
| `task` | `task_id` optional; `spec` with `objective`, `expected_output`, `context`, `cwd`, `write`, `dependencies`, `criteria` |
| `assign` | `task_id`, `session_id` |
| `retry` | Released failed/cancelled `task_id`, `reason`; preserves the previous attempt |
| `session` | `agent_id`; creates a fresh conversation by default; `fresh: false` plus `session_id` selects an existing related conversation |
| `ack` | `delivery_id`; acknowledges receipt without resolving an issue |
| `retry_delivery` | `delivery_id`, `reason`, `not_accepted_confirmed: true`; retries the original message only after checking recipient acceptance |
| `control` | `run_id`, `action`: `pause`, `resume`, or `cancel` |
| `hold` | `task_id`, `reason`, optional `clear: true` |
| `budget` | `scope` `team`/`agent`/`task`/`run` plus `id` and `budgets`, or `task_id` and `budgets`. Empty keys mean unlimited. |
| `preflight` | `task_id`, `commands` argv list, optional `scope` paths and `environment` |
| `ci_watch` | `task_id`, `pr`, `expected_head`, optional `interval_ms` and `max_attempts` |
| `replan` | `reason`, `tasks` mapping task IDs to complete replacement specs |
| `artifact` | `path` to a file to finalize |
| `report` | Worker credentials; `run_id`, `type`, `text`, `artifact_ids`, optional `priority` |
| `publish` | `proposal_event`, selected recipient agent IDs in `recipients` |
| `resolve` | `issue_id`, `resolution` |
| `review` | `run_id`, `decision`, `reason`, acceptance `checks`; optional `reviewed_commits` binds full commit OIDs to the review |
| `compatibility` | Accepted `task_id`, `compatible` boolean, `reason` |
| `takeover` | Optional `external_id`; rotates coordinator credentials and epoch |
| `finish` | Empty object; validates all tasks accepted and no unresolved issues/operations |

A passing acceptance check contains `criterion`, `passed: true`, and `artifact_ids`. Each declared criterion needs exactly one passing check. Old-revision results also require `compatible: true` and `compatibility_reason` describing checked dependency changes. For code intended for integration, include `reviewed_commits` with the full commit OIDs you inspected. Exit code zero, a delivery receipt, acknowledgment, or a live PID cannot satisfy review.

`status`, `history`, `inbox`, and `bulletin` emit JSON. History supports `--task-id`, `--run-id`, `--type`, `--after`, and `--limit`. Inbox supports `--priority urgent`. `--filters JSON` passes a filter object. Routine progress is stored without generating coordinator notifications; actionable messages and results enter the inbox. A bulletin publication records the original proposal and creates recipient deliveries. Busy workers process publications through an exact-session follow-up before finishing; idle workers retain them for their next authorized assignment. Publications do not implicitly create new tasks.

## Controls and recovery

A pause request changes desired state and holds dispatch; inspect the observed control result before replanning work that depends on tools having stopped. When instructions change, cancel the old attempt, wait for execution release, use `retry`, and assign the revised task to the same session. The adapters cannot replace instructions inside a suspended provider turn; `resume` rejects a changed assignment instead of resuming stale work. macOS exposes precise process birth identities but no atomic identity-bound signal API. Its process-tree helper therefore reports uncertainty even when the observed descendants are stopped. Linux uses pidfds when available. Observed descendants are journaled and checked even after reparenting. A tool that escapes before it is observed is outside this process-tree boundary. An ambiguous outcome needs inspection and an explicit recovery decision.

Restart the daemon with the same `--home`, then inspect status, pending operations, urgent inbox, and run identities before assigning replacements. Session takeover requires current coordinator credentials and rotates the epoch; earlier coordinator sessions lose mutation authority. Retry an uncertain external operation only after inspecting its original effect. Message deduplication does not make external effects exactly once.

An optional `--coordinator-thread` records the exact coordinator thread identity. The live gate verified waking an idle interactive Astra TUI in 5.85 seconds; an exited headless session did not self-wake. Queue submission remains separate from acknowledgment. See [transport evidence](docs/transport-evidence.md) for the exact tested configurations.

## Worktrees and integration

Concurrent writers require registered isolated worktrees with explicit repository, branch, path, and starting ref. Worktree creation preserves the original repository and does not delete branches or directories. One integration worker assembles accepted changes. Graphite operations use `gt create` and `gt submit --no-interactive`; publication must stay within the user's existing authorization.

Create a registered worktree with:

```sh
codex-orch request worktree --body '{"repo":"/absolute/repository","path":"/absolute/worker-tree","branch":"worker-branch","ref":"origin/main"}'
```

This returns an operation ID; inspect `status` for its observed outcome before assigning a writing task whose `cwd` is that path. Integration uses `request integration` with `task_id` naming a nonterminal task whose spec contains `integration: true` and whose registered worktree is idle. The operation reserves that worktree until completion; uncertain effects quarantine it until reconciliation. Git and network operations run outside the daemon request loop so controls remain responsive. Action-specific fields are:

| `action` | Additional fields |
| --- | --- |
| `cherry_pick` | Full OIDs in `commits`, and one accepted `source_runs` entry per commit; each OID must appear in that run's accepted `reviewed_commits` |
| `create` | `branch`, `message`; paired `trunk`, `parent` for first use of a raw git worktree |
| `ci` | Top `pr`, full `expected_head`; discovers and verifies every downstack PR |
| `submit` | `authorized: true` reflecting the user's publication authorization |

A raw `git worktree` branch is initially untracked by Graphite. On its first `create`, pass explicit local `trunk` and `parent` branches, for example `"trunk":"main","parent":"main"`. The helper runs repository-local `gt init --trunk` and `gt track --parent` before `gt create --all`. The parent must already be a tracked ancestor. Subsequent creates use the current tracked branch and omit these setup fields. This updates shared repository Graphite metadata; it does not change global Graphite configuration.

For an ambiguous operation, use `request reconcile` with `operation_id`, observed `outcome` (`succeeded` or `failed`), `external_effects_checked: true`, and an evidence-based `reason`. For a lost run, use `run_id`, `external_effects_checked: true`, and `reason`; live registered runner/provider identities prevent release. Reconciliation records an inspected outcome, not a blind retry.

The integration helper follows PR base branches to the repository default branch and verifies required checks for every exact head. Missing checks, failures, pending checks, inaccessible status, closed PRs, ambiguous parents, and changed heads/bases fail verification. Acceptance of a submitted integration task requires passing stack CI after submission, with the same current local head. No live remote publication is part of the offline fixture.

## Validation boundaries

Run the test suite from this directory:

```sh
python3 -m unittest discover -s tests -v
```

Resource tests use temporary processes, a private tmux server, and temporary git repositories. Fake adapters exercise runtime behavior without provider side effects. Real Astra/Grok execution, exact-session continuation, interactive Astra wake, and pause/resume/cancel during a real foreground tool call were also exercised; see [QA results](docs/qa.md) and [transport evidence](docs/transport-evidence.md). Remote Graphite publication and hosted CI were not exercised; their gates have deterministic tests and the repository includes a Linux/macOS CI workflow.
