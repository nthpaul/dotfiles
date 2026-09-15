# Headless Grok bridge

Implementation baseline: [Astra and Grok: a simpler subagent system](astra-grok-plan.pdf),
14 September 2026. The PDF remains unchanged. The user's subsequent refinement is:
try Grok xhigh before reserving native Astra high subagents for exceptional complexity.

Astra stays in native Codex and owns task selection, context, review, and next steps.
The bridge owns five operations, exact Grok sessions, execution records, and process
cleanup. It has no team registry, task scheduler, acceptance ledger, or publication engine.
Legacy `codex-orch` remains available with its existing records and behavior.

## Install and use

Requires Python 3.11+, Git, and an authenticated `grok` CLI on PATH. Tested locally with
Grok 1.0.30 and Codex 0.154.0. The core uses the standard library; MCP uses the official
Python SDK as an optional dependency.

```sh
cd codex/.codex/orchestrator
python3 -m pip install -e '.[mcp]'
codex mcp add grok_bridge -- grok-bridge mcp
```

Open a new Codex session after registering the MCP server. A running conversation may
not reload its tool catalog. The same operations are available through the CLI in an
existing session, with JSON argument files (or stdin):

```sh
grok-bridge spawn --input /absolute/path/task.json
grok-bridge wait --input /absolute/path/wait.json
grok-bridge inspect --input /absolute/path/inspect.json
```

Example spawn arguments:

```json
{
  "request_id": "permission-recovery-review-1",
  "cwd": "/absolute/path/isolated-worktree",
  "task": "Objective: review the permission-denial recovery path. Context: handler.py and its tests implement reopening an existing proposal. Check for races and lost retries. Completion: report concrete defects with file locations and a reproduction, or state which cases you checked. This is read-only.",
  "write_scope": [],
  "effort": "high"
}
```

`--home /path/to/state` selects an independent store; default is `~/.codex/grok-bridge`.
The `fake` adapter is an explicit CLI/Python testing seam, never a Grok fallback or MCP option.

## Coordinator loop

1. Decide whether delegation saves useful work. Handle tiny or tightly coupled tasks
   directly. For a substantial independent task, provide its objective, relevant paths
   and context, constraints, write scope, and observable completion criteria.
2. Start at most three Grok workers in one bridge store. Default to medium; choose high
   for difficult debugging/review. Try xhigh before escalating exceptional complexity
   to native Astra high. Effort labels are provider-specific, not interchangeable.
3. Continue useful work or call `wait` (0–30 seconds). Pending means keep working/waiting.
4. Assess **both** execution state and worker `report.outcome`. `completed` execution
   can carry a `blocked` or `partial` task report. Check evidence and relevant tests.
5. Use `inspect` for message/tool history. Resume the exact session for related fixes,
   missing evidence, or report formatting. Use a fresh session for unrelated work.
6. Integrate and verify combined behavior. The coordinator handles Graphite and CI under
   the user's authorization. Do not end the task merely because a worker exited.

Malformed JSON is a failed report, with provider output retained. Ask that same worker
to return the required JSON only; do not automatically rerun its underlying task.

## Interface and records

| Operation | Contract |
|---|---|
| `spawn` | `task`, `cwd`, `request_id`, optional `write_scope` and `effort`; returns run/session IDs after durable launch intent. |
| `wait` | `run_ids`, optional `after` event cursor and `timeout`; returns terminal reports, cursor, and pending IDs. Use a fixed run set per cursor; begin at zero when changing that set. |
| `inspect` | No ID lists runs; `session_id` lists that conversation; `run_id` returns report and message/tool history, paged by `after` and `limit` (1–200). |
| `resume` | `session_id`, `task`, `request_id`, optional effort; a distinct run in the same Grok conversation and worktree. `recovery_checked` acknowledges investigation after interruption. |
| `cancel` | `run_id`; durable termination request. Wait/inspect until observed settlement or explicit interruption. |

SQLite is authoritative for run ownership and events. Each run directory retains immutable
request/prompt, any prior-run handoff, normalized history, raw provider JSONL, stderr,
final text, and durable result. History pages are capped at 32 KB; oversized records
return a preview and remain intact on disk. Provider reasoning/signatures are excluded
from model-facing history. Full provider records may contain sensitive task content.

A detached supervisor survives MCP disconnection. The child records its process birth
identity before executing Grok, fencing the launch/crash window. One unreleased run owns
a session; conflicting writers in the same linked worktree are rejected, including
writers launched in different subdirectories. Repeating identical request IDs returns
the original run; changed inputs reject. No ambiguous execution is automatically retried.

Successful execution requires a terminal provider envelope, validated report, normal
exit, and release of observed child processes. If the supervisor is lost, recovery keeps
any available report as evidence while recording `interrupted`: exit and cleanup are
unverified. A persisted result survives loss of the subsequent database commit.
Pending cancellation is honored by recovery even if the supervisor dies during cancel.

After interruption, inspect worktree/history and external effects before checked resume.
Cancel can release observed ownership without starting another task. Resume preserves
conversation state; it does not restore old code or undo side effects.

## Limits

- Write scopes and `--no-subagents` are worker instructions/CLI policy, not an OS sandbox.
  Grok runs with the user's authorized local permissions. Linked worktrees isolate edits.
- Process control covers observed descendants with checked birth identities. It cannot
  prove that an unobserved daemonized process or a remote side effect has stopped.
- No automatic wake-up of an idle/exited coordinator, and no native subagent UI integration.
- At most three workers **per store**; separate testing stores are independent.
- The bridge does not automatically retry failures, increase effort, or accept code.

## QA, rollout, and rollback

See [pilot evidence and PDF acceptance gates](grok-pilot.md). Run deterministic tests with:

```sh
python3 -m unittest discover -s tests -v
```

The opt-in `benchmarks/grok_pilot.py` creates matching code fixtures in detached worktrees
and uses authenticated Codex/Grok. It saves prompts, events, implementation files, timing,
and independent validation outside the repository. It does not commit or publish work.

Cutover is gated on lifecycle checks, meaningful handoff, actual-client integration,
exact-head CI for every atomic PR, and useful pilot results. Do not claim a latency gain
from toy tasks. The pilot may justify keeping small tasks in Astra.

Rollback: `codex mcp remove grok_bridge`; stop outstanding bridge runs with `cancel` and
retain `~/.codex/grok-bridge` for inspection. Follow the existing legacy runtime guide
and local-orchestrator legacy instructions. No legacy state migration or deletion occurs.

Protocol references: [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
