# MVP implementation and QA

Validated locally on 14 September 2026. The runtime implements the six-page
brief's coordinator/worker workflow with twelve SQLite tables. Three separate
Astra medium agents implemented transport/resources and independently derived
the acceptance contract; the coordinator implemented storage/runtime and fixed
findings from their tests and live probes.

This is local execution evidence. [The parity contract](parity.md) defines the
broader acceptance cases; it is not a claim that every possible failure schedule
or provider version has been tested.

## Automated results

From `codex/.codex/orchestrator`:

```sh
python3 -m unittest discover -s tests -v
```

The final run passed **111 tests in 35.303 seconds** on macOS, Python 3.14.6 and SQLite 3.53.4.
The [machine-readable result](evidence/automated-qa.json) includes the table
inventory and database integrity results.
The suite uses temporary databases, Unix-socket daemons, actual runner subprocesses,
private tmux servers, and isolated Git repositories. Provider behavior in this
suite comes from the deterministic fixture. Live provider evidence is listed
separately below.

| Area | Tests | Established behavior |
| --- | ---: | --- |
| Storage and commands | 33 | Authenticated roles and team scope; durable replay; atomic rollback; concurrent reports; immutable history; task dependencies; revisions; artifact hashes; explicit acceptance; issue escalation; routed publications. |
| Runtime recovery | 23 | Coordinator epoch fences; ambiguous launch refusal; identity-bound process ownership; quarantine/reconciliation; released-run isolation; integration reservations. |
| Daemon scenarios | 13 | Two tasks plus revision and acceptance; actual daemon restart with surviving runner; committed observation replay; urgent pause/replan/cancel/retry; publication fanout; worktree exclusion; tmux output, focus, capacity and reuse. |
| Runner | 12 | Durable journal/outbox; duplicate-run lock; exact-session followups; tool descendants after parent exit; control observations; release only after observed execution ends. |
| Integration gates | 15 | Every downstack PR's required checks; exact head/base/state revalidation; failures and missing checks rejected; accepted commit provenance; submitted integration requires subsequent CI evidence. |
| Resources | 6 | Process birth identity; actual tool-child controls; private tmux ownership; isolated worktree creation; two real local Graphite commits with checks at each commit. |
| Provider adapters | 6 | Exact UUID routing; safe argv boundaries; stream parsing; no thinking/duplicate text as results; explicit provider failures; fake subprocess execution. |
| CLI | 3 | Argument/credential handling and installed command behavior. |

Crash coverage combines actual daemon process restarts with deterministic
reconstruction of ambiguous launch and lost-response journal boundaries. It does
not exhaustively kill a process after every individual database write or reproduce
every network timing race.

Additional checks passed: Python compilation, SQLite integrity and foreign-key
checks, twelve application tables, CLI `doctor`, skill validation, CI workflow YAML
parsing, and `git diff --check`. The wrapper and source are linked into this user's
`~/.local/bin` and `~/.codex`. No default persistent team was started by QA.

## Live checks

Installed versions: Codex CLI 0.154.0 and Grok CLI 1.0.30. Models were
`gpt-6-astra` and `grok-4.6`, both with medium reasoning.

| Scenario | Result and evidence |
| --- | --- |
| Real daemon launches Astra and Grok workers | Both returned their assigned markers, released execution and finalized artifacts. Tasks remained awaiting coordinator review. [Runtime evidence](evidence/live-runtime.json). |
| Related work resumes exact conversation | Both CLIs remembered a marker in direct probes; the full runtime also revised an Astra task and resumed the same external UUID. [Transport evidence](transport-evidence.md). |
| Idle coordinator wake | An isolated interactive Astra TUI responded to an exact-thread queued message in 5.850 seconds. [Wake evidence](evidence/interactive-wake.json). |
| Astra foreground shell-tool controls | A real heartbeat tool stopped on pause, resumed writing, and exited on cancel. The runner reaped observed tool descendants before releasing the run. [Control evidence](evidence/live-tool-control.json). |
| Grok foreground shell-tool controls | With `--always-approve`, all 30 observed processes stopped and resumed; all original identities were confirmed exited after cancellation. Heartbeats were 8→8 paused, 10→16 resumed, and 17→17 cancelled. The run released as cancelled with no result. [Probe evidence](evidence/live-grok-tool-control.json). The initial `dontAsk` tool rejection is retained as [baseline evidence](evidence/grok-tool-permission-baseline.json). |
| Local Graphite stack | Two successive `gt create` commits in a temporary worktree each passed a real Python behavior check. The source repository was preserved. This test is in `test_resources.py` and skips when Graphite is unavailable. |

Raw provider output remains in temporary probe directories rather than source
control because it includes local integration inventories and reasoning streams.
The linked evidence retains useful outcomes and identities without credentials.

## Operational boundaries

- Revised instructions cannot replace an executing provider turn. Pause first
  when needed, cancel and wait for release, then retry/replan and assign the new
  turn to the same related-work session. Resume rejects a changed assignment.
- macOS signaling is PID-addressed even after checking a precise birth identity.
  Pause/resume therefore retain an uncertain control outcome despite observed
  stopped/running processes. Cancellation confirmation comes from observed exit.
  Tools that escape before discovery and remote side effects are outside the
  local process-tree guarantee.
- Idle interactive Astra wake passed; an exited headless session did not
  self-wake. Queue receipt alone is not evidence of a model acknowledgment or
  urgent interruption during a busy turn.
- Publications reach busy workers through a subsequent exact-session turn; idle
  workers consume them on their next authorized assignment. They do not create
  unrequested tasks or inject instructions into a suspended tool call.
- Remote PR publication and hosted CI were not run. Their validation gates have
  deterministic tests, and a Linux/macOS GitHub Actions workflow is included.
  Only the local macOS suite has an observed passing result here.
- Session credentials enforce protocol roles, not isolation from other programs
  running as the same OS user. Codex inherits user sandbox/approval configuration;
  Grok uses auto-approval so delegated headless tools can run.
