---
name: local-orchestrator
description: Coordinate bounded headless Grok workers from native Codex through the local Grok bridge; inspect results, resume exact sessions, and handle recovery. Also supports explicitly requested legacy codex-orch teams and board.
---

# Local orchestration

Astra stays in native Codex and owns planning, handoffs, review, and next steps. Use the
five `grok_bridge` MCP tools, or the equivalent `grok-bridge` CLI when the current client
has not loaded MCP. Read the [bridge guide](../../orchestrator/docs/grok-bridge.md) for
schemas, setup, records, limits, and the [PDF baseline](../../orchestrator/docs/astra-grok-plan.pdf).
For this machine, read `~/.codex/grok-bridge/ACTIVATION.json` when present: it records
activation and live verification after the [historical pilot](../../orchestrator/docs/grok-pilot.md).
When activation is verified and merge_sync_pending is false, use the bridge for new delegated work. For an explicitly requested existing team/board, use
[legacy instructions](references/legacy.md); preserve its records.

## Choose useful delegation

Do small or tightly dependent work directly. Delegate substantial independent work when
it lets Astra make useful progress in parallel. Default Grok medium; use high for difficult
implementation/debugging or review. Try Grok xhigh before escalating exceptional complexity
to a native **Astra high** subagent. Native Codex subagents remain available; do not globally
disable them. Grok workers have one delegation level and must not spawn subagents.

At most three active Grok workers per bridge store. Every writer needs a separate linked
git worktree and explicit write scope. Empty scope means read-only by worker instruction;
it is not an OS sandbox. Do not delegate overlapping writers into the same worktree.

## Handoff and loop

Give each worker a concrete objective, relevant context and paths, constraints and scope,
observable completion criteria, and expected evidence. Include commands or reproduction
steps when known. Do not dump the whole conversation or require a plan/acceptance ceremony.

After `spawn`, retain run/session IDs and do useful work or `wait`. Pending means keep
working/waiting. On a terminal result, read both execution state and report outcome, review
its evidence, and verify important behavior. Successful execution does not establish task
correctness; a valid report can say blocked or partial.

Use `inspect` for bounded message/tool history. Ask the same session to fix defects or
provide missing evidence via `resume`; use a fresh session for unrelated work. If a report
is malformed, request the required JSON without rerunning the original task. Final reports
contain outcome, summary, changes/findings, validation, unresolved issues, and artifacts.

The coordinator may read code and make small dependent changes. Integrate accepted work,
run appropriate combined validation, and use Graphite within the user's authorization.
Every PR remains atomic and must pass CI at its exact head. Do not end merely because
workers have returned; finish the user's outcome or report the actual blocker.

## Recovery

Retry an identical operation with the original request ID; new work gets a new ID. Never
blindly relaunch after interruption. Inspect saved history, worktree, and external effects
before setting `recovery_checked` on resume. Cancellation is a durable request; inspect
observed cleanup. It does not undo edits or remote effects.

Use a fixed run set for each wait cursor, or start at zero after changing the set. Results
remain inspectable after client reconnect. No automatic wake of an idle/exited coordinator
or native subagent UI integration is promised; keep the coordinating turn active.
