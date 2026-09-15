---
name: local-orchestrator
description: Operate the local codex-orch daemon and full-screen board for durable Astra-led worker assignments, inbox routing, process controls, and evidence-based review. Use when the user requests this local orchestration runtime, its board, or work on its active team.
---

# Local orchestrator

Use `codex-orch` for runtime mutations and reads. Use `codex-orch board` for the multi-team TUI. Read the [runtime guide](../../orchestrator/README.md) for startup, command schemas, credential handling, the board, and the offline exercise. The daemon owns SQLite, delivery, resource bookkeeping, and execution logs; edit state through its API. For board keys, attach rules, and requested-versus-observed display, read [references/board.md](references/board.md).

Astra owns planning, assignments, mediated routing, revisions, and acceptance. The coordinator delegates implementation, review, and integration as separate assignments and reviews compact evidence artifacts, not source trees. Automation owns monitoring (`ci_watch`, usage ticks, inbox polling). The integration worker owns CI fixes. Workers execute their assignment and report to the coordinator; they do not spawn nested workers or send worker-to-worker instructions.

`register` defaults to Grok `grok-4.6` high in the owned pane. Do not send `mode` unless the assignment requires `--mode exec`. Explicit `--adapter codex` or `--adapter fake` keep those transports. Budget, preflight, and CI watch use generic `request KIND --body`; do not invent extra CLI verbs.

Write each assignment with its objective, relevant context, expected output, acceptance criteria, dependencies, exclusive write scope, and optional `budgets`. Concurrent writers need registered isolated worktrees. Reuse a worker session for related follow-up work; use a fresh session for unrelated work. Keep the coordinator available for user steering while the daemon records routine progress quietly. Assignment handoffs stay bounded: one worker, one write scope, report back.

Inspect urgent unresolved inbox entries before normal results. Route worker proposals by publishing their original artifact references to explicitly selected recipients. A stored receipt, delivery, acknowledgment, resolution, and accepted result are distinct facts; advance each only with its own evidence.

Hold affected dispatch before urgent replanning. Request process controls through the runtime and inspect their observed outcome. Treat uncertainty as unresolved; do not infer that a tool stopped from the requested state. Preserve old-revision results and assess changed dependencies explicitly before accepting them.

Review finalized result artifacts and criterion-specific validation after execution has been released. A successful exit or worker completion claim alone cannot accept a task. Request a revision when evidence is incomplete. Assign one integration worker to assemble accepted changes; publish through Graphite within the user's authorization, then verify required CI for every exact PR head before accepting the integration task.

On recovery, read team state, resource identities, unresolved deliveries, and incomplete operations before new dispatch. Verify process birth identity and exact tmux ownership. Reuse request IDs when retrying identical commands; inspect ambiguous external effects before retrying them. Takeover rotates the coordinator credential and ownership epoch. Report unsupported live transport or control capabilities plainly and use the documented inbox/status polling path when automatic wake is unproven.
