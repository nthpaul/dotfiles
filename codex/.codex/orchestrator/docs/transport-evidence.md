# Local provider transport evidence

Verified 2026-09-14 on macOS with `codex-cli 0.154.0` and
`grok 1.0.30 (04b7ffed98c6) [stable]`. These are local CLI observations, not
promises about other versions. Probe working directory:
`/var/folders/03/jljkhjcd1nl_ksq1rj8kx6lc0000gp/T/orch-transport-chaadc7x`.
Raw temporary JSONL and stderr remain there; they are deliberately not committed
because provider initialization lists local integrations and streaming includes
reasoning content. The adapter exposes only assistant text, result, session ID,
and error, never reasoning deltas.

## Real runs

| Check | Observed evidence |
| --- | --- |
| Codex fresh | `gpt-6-astra`, `model_reasoning_effort="medium"`, `exec --json`, read-only sandbox. Exit 0, `thread.started` ID `01a0a1f8-71e0-77c1-bd30-64972e442b0a`, completed agent message `ACK copper-owl-913`, then `turn.completed`. |
| Codex exact resume | `exec [global flags] resume --model gpt-6-astra -c 'model_reasoning_effort="medium"' <same UUID> <followup>`. Asked for the remembered marker without supplying it. Same thread ID, final `copper-owl-913`, exit 0. |
| Grok fresh | `--no-subagents --output-format streaming-messages-json --include-partial-messages --model grok-4.6 --reasoning-effort medium --session-id d91a09d1-21ba-4bce-9895-6709d04125a7 --single <prompt>`. Init echoed predetermined UUID. Text deltas assembled `ACK silver-birch-914`; final result repeated it, exit 0. |
| Grok exact resume | Replaced fresh `--session-id` with `--resume <same UUID>`. Asked for remembered marker without supplying it. Result `silver-birch-914`, same UUID, exit 0. |
| Grok cancellation | Exact-resume story request; after first stream event, signaled only its new process group with SIGTERM. Exit -15 in 0.020 seconds. No tool calls were requested. |
| Codex queue | `codex queue --thread 01a0a1f8-71e0-77c1-bd30-64972e442b0a --message <wake probe>` exited 0, returning queued message `01a0a1fa-bc76-7d62-890d-1da6f6c0d845` for that exact thread. No wake response appeared in the headless session transcript during observation. |
| Idle interactive Codex wake | A separate, read-only Astra medium TUI in isolated tmux server `orch-wake-spike` answered its initial prompt and became idle. Queueing exact fresh thread `01a0a205-ec8b-7c73-bb1e-511cd39c1127` produced queued message `01a0a206-6770-79a2-90df-586d50340b5b`; the thread transcript then recorded assistant final `INTERACTIVE WAKE ACK 914` in 5.850 seconds. The probe TUI and isolated tmux server were closed afterward. Sanitized evidence: [interactive-wake.json](evidence/interactive-wake.json). |

Probes requested no tools or file edits. Codex probes used `--ignore-user-config`
and `-s read-only`; Grok probes restricted built-in tools to `read_file` and disabled
web search. Neither trace showed tools running. Grok initialization still listed
MCP integrations and inherited `bypassPermissions`; its `--tools` switch alone
does not prove all external tools are removed. Production commands use `--always-approve` for Grok headless execution; `dontAsk` rejected a delegated shell tool in the live probe. Codex workers inherit the user's approval and sandbox configuration, including the requested full-access defaults on this machine. Explicit write scopes still require isolated worktrees
and worker instructions; Grok auto-approval is not a filesystem sandbox.

## Parser contract

Codex JSONL supplies `thread.started`, `turn.started`, completed items, and
`turn.completed`. The observed agent-message text was emitted as one completed
item, not token deltas. Each completed agent message yields `text` and a candidate
`result`; keep the last result and require successful completion before entering
review. A process exit or result never accepts the task.

Grok JSONL supplies a system init, Anthropic-shaped `stream_event` records, whole
assistant messages, and a final `result` envelope. Only `text_delta` contributes
incremental text. Whole assistant messages are ignored to avoid displaying the
same content twice; final `result` replaces the accumulated text. Thinking,
tool-input deltas, and unknown records are not treated as results.

Commands are argv arrays, never shell strings. Prompts travel in argv and can be
visible to local process inspection. Callers must set `stdin=DEVNULL` and subprocess
cwd. Codex supports stdin, but the shared command-only interface does not provide
a stdin payload; Grok also has a prompt-file option. A future transport can adopt
prompt files/stdin without claiming this MVP already does so. All followups and
wakes validate exact UUIDs, avoiding title ambiguity or latest-session routing.

## Unsupported or uncertain behavior

- No provider supplies the runtime's structured delivery acknowledgment. A model
  saying ACK in these probes proves prompt processing, not protocol deduplication.
- No live stdin steering or cooperative pause is implemented. Dispatch waits for
  a free worker; later turns explicitly resume the persisted session.
- SIGSTOP/SIGCONT are operating-system process controls. SIGTERM proves local
  process exit only; it does not prove remote inference cancellation, tool-child
  termination outside the process group, rollback, or exactly-once effects.
- `codex queue` automatically woke the idle interactive TUI in the separate probe,
  with 5.850-second model acknowledgment latency. This is one local observation,
  not a latency bound. An exited headless exec session did not visibly self-wake.
  Queue submission alone remains a receipt; confirmation requires observing the
  targeted session's response. Busy-turn interruption and urgent tool preemption
  have not been proven by this idle wake test.
- A predetermined Grok UUID is visible in launch argv before startup, but callers
  must persist launch intent before executing if they need crash reconciliation.
  Stream-init discovery alone cannot eliminate the send/before-ack ambiguity.
- Fake workers retain a supplied session UUID but do not simulate model memory.

## Deterministic fixture and tests

`python3 -m unittest discover -s tests -p test_adapters.py -v`: six tests pass.
Tests cover explicit routing, malformed records, provider failures, Grok duplicate
suppression, thinking exclusion, and real fake-worker subprocess success/failure.

A fake assignment can contain this exact separate line:

```text
FAKE_SCRIPT={"progress":["started","working"],"delay":1,"result":"ready for review"}
```

`error` emits `turn.failed`; `exit_code` independently controls process outcome.
Delay follows each progress message, allowing deterministic pause/cancel probes.

## Full runtime live validation

A real Unix-socket daemon launched two separate runner subprocesses, one using
Codex Astra medium and one using Grok 4.6 medium. Both assignments requested only
marker acknowledgments and prohibited tools, nested agents, edits, and external
contacts. Results were `ACK amber-heron-914` and `ACK teal-fox-914`; both runs
released successfully and produced finalized result artifacts.

The coordinator requested a revision of the Codex task, revised its objective,
and reassigned it to the same worker session. The new prompt asked for the
remembered marker without providing it. The final response was
`amber-heron-914 revised`, with the same external session UUID
`01a0a207-caf1-7590-8572-87788a8bcab4`. All three runs released successfully;
three evidence artifacts were finalized, and both tasks remained awaiting
coordinator review. No worker accepted its own result. The daemon was stopped
after completion. [Sanitized runtime evidence](evidence/live-runtime.json)
retains exact outcomes and session IDs without credentials or raw provider logs.

Twelve runner tests cover durable retry after a daemon commit, duplicate-run
locking, ambiguous launch refusal, same-session publication followups, observed
child completion after parent exit, cancellation, pause/resume observation versus
confirmation, takeover after assignment acceptance, missing terminal results,
and an exact worker reporting command with credential-file routing instead of
credential contents.

## Real foreground tool control

The daemon created and registered a temporary isolated git worktree, then launched
an Astra medium writing assignment scoped exclusively to `heartbeat.txt`. Astra
invoked a foreground Python shell tool that flushed one heartbeat every 0.2 seconds
for a bounded 30-second run. The coordinator requested pause, resume, and cancel
through the ordinary daemon API while that tool was running.

| Request | Actual process observation | File activity over the next 1.2 seconds |
| --- | --- | --- |
| Pause, generation 1 | All six observed provider/tool processes were `T`; the heartbeat Python process was among them. | 6 → 6 lines: stopped. |
| Resume, generation 2 | All six observed processes were `R`. | 7 → 13 lines: resumed. |
| Cancel, generation 3 | All six observed processes exited, including the exact heartbeat tool birth identity. | 14 → 14 lines: stopped permanently. |

The runner waited for the observed tool processes to end before releasing the run
as cancelled. Final state was `released: 1`, `observed: exited`, with control
generation 3 confirmed by observed execution exit. No result was accepted and no
manual process signals or unknown-PID cleanup were used. The daemon was stopped
afterward; the temporary worktree remains as local evidence.

Each macOS pause/resume/cancel signal observation retained `outcome: uncertain`
because birth-identity validation and PID-addressed signaling are not atomic.
Pause and resume did not advance the confirmed control generation. This test
establishes the observed local tool behavior, not a guarantee about escaped tools,
remote side effects, rollback, or every future provider version. Exact process
birth identities and state samples are retained in
[sanitized real-tool control evidence](evidence/live-tool-control.json).

## Revised instructions after an urgent stop (CTRL-2)

Neither adapter replaces instructions inside a stopped, in-flight provider turn.
OS resume continues that same turn with its original assignment. It is suitable
only when the assignment is unchanged; the runtime rejects resume after its spec
has changed. Pausing a process does not deliver the revised plan to the model.

For both Codex and Grok, the implemented urgent-replan sequence is:

1. Hold affected dispatch and request pause; inspect actual tool/process state.
2. When the assignment must change, request cancel and wait until the old run and
   its observed tools have exited and the run is released. Reconcile uncertainty
   before retrying; do not infer that remote side effects were rolled back.
3. Resolve blocking issues, request `retry` with the task ID and a reason, and
   commit the complete revised spec with `replan`. Clear any separate dispatch
   holds once their conditions are resolved.
4. Assign a new run to the same related-work worker session. Codex uses exact-ID
   `exec resume`; Grok uses exact-ID `--resume`. The new model turn receives the
   revised assignment and revision while retaining conversation history.

Each retry has a new run ID; the prior assignment, output, and controls remain in
history. Queued publications are likewise injected as explicit followup turns
when the worker is free, not into a paused model/tool call. This is a
cancel-and-retry workflow, not live replacement of an executing prompt.

## Grok foreground tool control

With the final `--always-approve` adapter configuration, Grok 4.6 medium executed
the bounded foreground Python heartbeat tool through the actual daemon and runner
in a runtime-created isolated worktree. The coordinator issued all controls
through the normal API; no manual process signals were used.

| Request | Actual process observation | Heartbeat over the next 1.2 seconds |
| --- | --- | --- |
| Pause, generation 1 | All 30 observed provider/tool processes were `T`. | 8 → 8 lines: stopped. |
| Resume, generation 2 | All 30 observed processes were `R`. | 10 → 16 lines: resumed. |
| Cancel, generation 3 | All 28 remaining observed processes exited; two had already exited naturally. | 17 → 17 lines: stopped permanently. |

The exact heartbeat tool identity exited, and every original observed process
identity was independently rechecked as exited afterward. The runtime released
the run as cancelled, with generation 3 confirmed after execution ended and no
result event. The daemon was stopped; the temporary worktree remains as evidence.
[Sanitized Grok real-tool evidence](evidence/live-grok-tool-control.json) retains
the exact birth identities, state samples, and file counts.

As with Astra, the macOS control records preserve `outcome: uncertain` because
PID validation and signaling are not atomic. This passes the observed local
foreground-tool pause/resume/cancel gate; it does not establish rollback, control
of escaped processes, or cancellation of remote side effects.

The earlier `dontAsk` configuration cancelled the shell invocation before any
heartbeat file existed. That superseded configuration failure is retained in
[the permission baseline](evidence/grok-tool-permission-baseline.json). The final
probe above used the user's authorized automatic-approval configuration.
