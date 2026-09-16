# Grok bridge pilot and PDF acceptance record

Baseline: [unchanged implementation-plan PDF](astra-grok-plan.pdf), 14 September 2026.
Evidence directory on Paul's machine: `/Users/ple/Documents/Codex/astra-grok-pilot/`.
This is a directional pilot, not a statistically reliable harness ranking.

## Running the current pilot

`benchmarks/grok_pilot.py` compares direct work with a coordinator allowed to delegate
selectively. It does not force worker calls, history inspection, or a recall follow-up.
Both modes have the same fixture tasks and independent verifier. Run both against the
same `--revision`, using a Python environment with the MCP dependency installed.
`metrics.json` records wall time, verifier results, raw coordinator turn usage, worker
counter totals with coverage, and worker execution states. The two small algorithm fixtures
can check the decision to keep work local; they do not establish savings on substantial
investigations or implementation tasks. Use representative work before claiming those gains.

The results and rollout status below describe the original 14 September pilot, which
forced delegation and included extra transport exercises. They are historical evidence,
not measurements of the current selective workflow.

## What the original pilot establishes

- Two headless live Groks can run concurrently and return separate validated reports.
- A related follow-up resumes the exact session. In the read/recall test, the source file
  was removed before follow-up; the worker recalled `cobalt-731` without another tool call.
- Native Codex CLI invoked the five-operation MCP server, delegated two scoped code tasks,
  inspected history, integrated both files, validated them, and collected same-session recall
  without manual relay. The current desktop conversation also drove live workers through
  the Python/CLI path and remained available for user steering. Direct MCP hot-reload into
  an already running desktop conversation has not been demonstrated.
- The stdio integration test disconnected/reconnected MCP clients and retrieved saved results.
- Fault tests exercise duplicate request IDs, busy sessions, concurrency limits, cancellation
  and observed children, supervisor loss, pre-exec identity registration, database commit
  failure after durable result persistence, and interrupted results without false success.
- Grok xhigh independently reviewed lifecycle code. It identified a real pre-registration
  crash gap. Native Astra high then reviewed that exceptional-complexity path, reproduced
  a cancellation race, and verified the fixes. No remaining findings in that bounded review.
- The xhigh review initially prefixed its JSON with prose. The strict parser correctly
  rejected the report; its original evidence remained in Grok session history. A
  formatting-only same-session follow-up succeeded without repeating the review.

The installed snapshot also passed a live missing-input task (transport completed with
`report.outcome=blocked`) and cancellation of a live Grok terminal task. Nine owned process
identities were observed before cancellation, and all observed identities were released.
Artifacts: `live-controls/results.json` and `live-controls.log` in the evidence directory.

## Live read and recall smoke test

| Run | Verified outcome | Run time |
|---|---|---:|
| Grok medium | Correct sum and valid report | 12.29 s |
| Grok high | Correct sum and valid report | 138.03 s |
| Same-session Grok medium follow-up | Correct recall after file removal | 6.10 s |

These tasks establish transport/continuation behavior, not representative coding performance.
The large latency difference is one observation; it does not establish that effort alone
caused it. Provider and startup variability were not controlled.

## Matched code pilot

Both cases start at revision `e2404d9a6ccfb945b01d8b55961d17c2bd08ed54` with identical
fixture files. One case merges closed intervals; the other returns a deterministic
lexicographic topological order. Separate linked worktrees isolate delegated writers.
An independent verifier checks mutation, generators, invalid intervals, duplicate edges,
cycles, and 30 generated graphs against exhaustive valid orders.

| Mode | Time through independent verification | Verifier | Worker correction retries |
|---|---:|---|---:|
| Codex Astra high alone | 50.15 s | Pass | 0 |
| Codex Astra high + two Grok medium workers | 198.51 s | Pass | 0 |
| Codex Astra high + two Grok high workers | 271.34 s | Pass | 0 |

Delegated timings include the requested history inspection and extra recall turn; the
baseline does not perform that integration-specific exercise. Coordinator-selected extra
validation also differed. Consequently this is a whole-workflow pilot, not a controlled
model inference benchmark. There is one sample per mode. No universal speedup is claimed.

The medium workers themselves took 55.2 s and 50.9 s, concurrently; recall took 25.4 s.
High workers took 50.6 s and 187.6 s; high recall took 35.7 s. Both modes passed,
and the coordinators reported zero defects and no unresolved issues. The full workflow was slower than direct work for these small tasks.

**Operating decision:** keep small or tightly coupled tasks in Astra. Use Grok for substantial,
independently verifiable work that allows useful parallel progress. Default to medium, high
for difficult work, and xhigh before exceptional native Astra high escalation. Do not force
all tasks through delegation or automatically climb effort levels.

Reproduce a mode with:

```sh
python3 benchmarks/grok_pilot.py --output /absolute/path/new-pilot --mode baseline --revision HEAD
# Supply the exact baseline revision to subsequent medium/high runs.
```

Artifacts include per-mode `metrics.json`, coordinator `events.jsonl`, final reports,
worktrees, bridge database/history, and independent verifier results. Provider token usage
is retained per run; Codex turn usage is in its event log. The original xhigh review required
one formatting correction. No user intervention or editing conflict occurred in the code pilots.

## PDF gates and rollout status

| PDF gate | Evidence/status |
|---|---|
| PR 1: launch, terminal parsing, malformed/error handling | Passed deterministic adapter tests; live valid and invalid report cases observed. |
| PR 2: durable lifecycle, recall, cancellation, recovery | Passed subprocess/fault tests and live continuation; no automatic replay after ambiguous execution. |
| PR 3: five operations, actual-client loop, reconnect | Native Codex CLI/MCP and current-client CLI exercised; direct desktop MCP discovery awaits a new tool session. |
| PR 4: pilot, measured decision, CI, controlled cutover | Pilot informs selective delegation; three code-layer heads passed CI. Pilot-head CI is recorded externally. Graphite PR creation remains blocked. |

The final full suite passed **159 tests in 41.94 seconds**, including the removed-directory
request-replay regression. Existing legacy behavior remains tested.

Graphite successfully pushed the initial three branches, but rejected PR creation because
its GitHub permissions do not allow submission for `nthpaul/dotfiles`. The final three code-layer heads passed Linux/macOS Actions:

- Transport `86a7b11`: https://github.com/nthpaul/dotfiles/actions/runs/34927089659
- Runtime `b765fa1`: https://github.com/nthpaul/dotfiles/actions/runs/34927108328
- MCP `d035851`: https://github.com/nthpaul/dotfiles/actions/runs/34927123939

The pilot/documentation branch is checked after its commit; the final exact-head results
are retained in the external evidence directory. No PRs have been created yet because
of the Graphite permission failure.

**No default cutover yet.** A snapshot is installed at
`~/.local/share/grok-bridge/venv/bin/grok-bridge` for explicit use; MCP SDK 1.29.0 is
pinned in that environment. The user's default MCP configuration and active skill are
unchanged. The implementation is available for explicit testing. The legacy
runtime and its records are retained; no default legacy state directory existed locally at
inspection. Unrelated user config changes are excluded. The two Traba/Matrix PRs remain
parked until architecture rollout gates are satisfied.
