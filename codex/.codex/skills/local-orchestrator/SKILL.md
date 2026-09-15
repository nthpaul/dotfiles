---
name: local-orchestrator
description: Operate the local codex-orch daemon for durable Astra-led worker assignments, inbox routing, process controls, and evidence-based review. Use when the user requests this local orchestration runtime or work on its active team.
---

# Local orchestrator

Use `codex-orch` for runtime mutations and reads. Read the [runtime guide](../../orchestrator/README.md) for startup, command schemas, credential handling, and the offline exercise. The daemon owns SQLite, delivery, resource bookkeeping, and execution logs; edit state through its API.

Astra owns planning, assignments, mediated routing, revisions, and acceptance. Register bounded workers with the default Astra model and medium reasoning unless the task specifies another adapter or model. Workers execute their assignment and report to the coordinator; they do not spawn nested workers or send worker-to-worker instructions.

Write each assignment with its objective, relevant context, expected output, acceptance criteria, dependencies, and exclusive write scope. Concurrent writers need registered isolated worktrees. Reuse a worker session for related follow-up work; use a fresh session for unrelated work. Keep the coordinator available for user steering while the daemon records routine progress quietly.

Inspect urgent unresolved inbox entries before normal results. Route worker proposals by publishing their original artifact references to explicitly selected recipients. A stored receipt, delivery, acknowledgment, resolution, and accepted result are distinct facts; advance each only with its own evidence.

Hold affected dispatch before urgent replanning. Request process controls through the runtime and inspect their observed outcome. Treat uncertainty as unresolved; do not infer that a tool stopped from the requested state. Preserve old-revision results and assess changed dependencies explicitly before accepting them.

Review finalized result artifacts and criterion-specific validation after execution has been released. A successful exit or worker completion claim alone cannot accept a task. Request a revision when evidence is incomplete. Assign one integration worker to assemble accepted changes; publish through Graphite within the user's authorization, then verify required CI for every exact PR head before accepting the integration task.

On recovery, read team state, resource identities, unresolved deliveries, and incomplete operations before new dispatch. Verify process birth identity and exact tmux ownership. Reuse request IDs when retrying identical commands; inspect ambiguous external effects before retrying them. Takeover rotates the coordinator credential and ownership epoch. Report unsupported live transport or control capabilities plainly and use the documented inbox/status polling path when automatic wake is unproven.
