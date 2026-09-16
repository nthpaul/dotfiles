---
name: local-orchestrator
description: Delegate substantial independent work or independent review to headless Grok workers from native Codex; inspect results, resume exact sessions, and handle recovery. Also supports explicitly requested legacy codex-orch teams and board.
---

# Local orchestration

Astra stays in native Codex and owns planning, handoffs, review, and next steps. Use the
five `grok_bridge` MCP tools, or the equivalent `grok-bridge` CLI when the current client
has not loaded MCP. Read the [bridge guide](../../orchestrator/docs/grok-bridge.md) when
you need schemas, setup, or recovery details. For an explicitly requested existing team/board,
use [legacy instructions](references/legacy.md); preserve its records.

## Choose useful delegation

Keep small fixes, prioritization, routine CI triage, and tightly dependent work in the
coordinator. Delegate a substantial independent outcome when the coordinator can advance a
different concern, or when independent review is valuable or explicitly requested. Do not
investigate the worker's assigned problem in parallel; verify its evidence when it returns.
Default Grok medium; use high for difficult implementation/debugging or review. Try xhigh
before exceptional escalation to a native **Astra high** subagent. Grok workers must not
spawn subagents.

At most three active Grok workers per bridge store. Every writer needs a separate linked
git worktree and explicit write scope. Empty scope means read-only by worker instruction;
it is not an OS sandbox. Assign one owner for dependency installation and heavyweight
combined builds/evals; workers run the focused checks their assignment needs.

## Handoff and loop

Give each worker a concrete objective, relevant context and paths, constraints and scope,
observable completion criteria, and expected evidence. Include commands or reproduction
steps when known. Do not dump the whole conversation or require a plan/acceptance ceremony.

After `spawn`, retain run/session IDs and do useful work or `wait`. Pending means keep
working/waiting. On a terminal result, read both execution state and report outcome, review
its evidence, and verify important behavior. Successful execution does not establish task
correctness; a valid report can say blocked or partial.

Read terminal reports and usage totals first; use `inspect` history only for missing evidence
or diagnosis. Keep reports concise and put detailed evidence in artifacts. Review at a
meaningful completion checkpoint, then handle small dependent corrections locally. Resume
the exact session when a concrete defect or missing evidence needs its accumulated
investigation. For an independent task, use a fresh session with relevant paths and facts;
a related topic alone does not justify replaying a large history.

The bridge normalizes unambiguous report wrappers without a model call. If parsing still
fails, inspect the retained output before requesting a formatting-only correction; never
rerun the underlying task for formatting. Use measured session totals to assess further
delegation; absent usage is unknown, and cached input is separate from other input.

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
