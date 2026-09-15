# Architecture parity and acceptance contract

Source: [architecture brief](../../plans/astra-grok-orchestration/sources/brief.tex),
13 September 2026. This document defines required behavior and verification cases.
It does **not** report implementation results. Tests, screenshots, transcripts,
database snapshots, and CI URLs must be attached separately before marking a gate
passed. A simulation establishes store behavior, not live provider capabilities.

Implementation results and the remaining verification boundaries are recorded in
[QA results](qa.md).

## Traceability

The proposed twelve tables are storage responsibilities, not twelve independent
services. Every relationship is team scoped; database constraints and authenticated
runtime validation must agree about that scope.

| Brief requirement | Proposed records | Acceptance cases |
| --- | --- | --- |
| Astra plans, delegates, routes and accepts; workers cannot delegate or route | teams, agents, sessions, command_requests, events | AUTH-1–4, FLOW-1 |
| Stable agent/task/run identity; retries retain history | agents, tasks, runs, sessions | RUN-1–3, REC-1 |
| One current executing attempt per task and exclusive writer scope | tasks, runs, resources | RUN-2, CODE-1 |
| Immutable ordered history and atomic durable receipts | command_requests, events, deliveries, tasks, runs | STORE-1–4 |
| Receipt, delivery, acknowledgment and resolution are distinct | deliveries, issues, operations | MSG-1–4 |
| Structured events, validated sender and references | sessions, events, artifacts | AUTH-1–3, ART-1 |
| Worker proposals become Astra-authorized publications | events, deliveries, artifacts | ROUTE-1–2 |
| Urgent unresolved inbox; coalesced issues; quiet routine progress | events, deliveries, issues | URG-1–3 |
| Pause/cancel requested separately from observed outcomes | operations, runs, deliveries | CTRL-1–4 |
| Old-plan evidence retained and dependency changes reviewed | teams, tasks, runs, events, artifacts | PLAN-1–3 |
| Coordinator ownership epoch and restart reconciliation | teams, sessions, operations, resources, runs | AUTH-4, REC-1–4 |
| Finalized versioned artifacts with hashes | artifacts, events | ART-1–3 |
| Existing window, owned reusable panes, exact handles, focus preservation | resources, agents, runs | PANE-1–4 |
| Bounded workers, isolated worktrees, named integrator, atomic CI-passing PRs | tasks, runs, resources, artifacts | CODE-1–3, FLOW-1 |
| Live launch/stream/ack/follow-up/resume/cancel and exact Astra wake | sessions, operations, deliveries, runs | LIVE-1–4 |

Additional durable tables are unnecessary if the twelve records can represent the
required invariants. An in-memory cache must never be the sole source of request
deduplication, accepted message IDs, control confirmation, resource ownership, or
coordinator ownership. Append-only event records preserve original assignment
revision, sender, content, timestamp, sequence, and artifact references.

## Test fixture and evidence rules

Use an isolated temporary database, artifact directory, git repositories/worktrees,
and tmux server. Create teams T and U; coordinator sessions C1 and C2; workers W1,
W2 and W3; tasks A and B where B depends on A. Record all stable IDs. Run each
crash case across an actual process restart with a reopened database; an exception
inside one process is insufficient evidence of restart safety.

A deterministic adapter must expose barriers before and after transaction commit,
external send, recipient acknowledgment, process launch, and operation observation.
Persist the recipient's accepted message IDs independently of the sender. Use an
external-effect counter to detect duplicate execution. Live cases require the real
installed provider versions and exact commands, with credentials redacted. Record
unsupported behavior explicitly; never convert a queued command into a claimed
interruption or acknowledged delivery.

For every case capture setup, action, expected invariant, observed outcome, command
exit status, and relevant event/delivery/operation IDs. For fault cases also capture
the injection boundary and pre/post-restart state. A passing CLI command alone is
not acceptance evidence.

## Authentication, ownership and storage

- **AUTH-1 — Bound sender.** Authenticate as W1 and supply C1/W2 as sender, a forged
  coordinator role, another run ID, or another team's ID. Reject each mutation
  without state/event/delivery changes. Derive sender from authenticated session;
  possession of public IDs or the current epoch is not authentication.
- **AUTH-2 — Worker limits.** As W1 attempt assignment, acceptance, publication,
  takeover, another worker's acknowledgment, and pause/cancel of W2. Reject each.
  W1's suggested recipients create no worker deliveries until Astra publishes.
- **AUTH-3 — Session/run binding.** Revoke or replace a worker session, then submit
  reports and acks from the old session. They cannot mutate the new run. Reject
  cross-team reply, artifact, dependency, recipient, operation, and resource IDs.
- **AUTH-4 — Epoch fence.** Take over from C1 to C2. Race C1 commands against takeover
  and replay previously queued C1 controls afterward. Commands linearize before
  takeover or are rejected; no stale control dispatch or acceptance occurs after
  takeover. Test assignment, revise, publish, pause, resume, cancel, accept, and
  resource cleanup. A stale session cannot adopt the new epoch by reading it.
- **STORE-1 — Atomic receipt.** Inject failure after each write in assignment and
  result transactions. Reopen the database: either all state/event/delivery/request
  records exist or none do. A returned durable receipt survives restart.
- **STORE-2 — Request identity.** Repeat the same authenticated request ID and
  semantic payload before and after restart and concurrently. Return the original
  receipt, with one event/effect. Changed payload under that ID is rejected.
  Document canonicalization and request-ID namespace; never leak another session's
  receipt on a collision.
- **STORE-3 — Concurrency.** Submit distinct worker reports concurrently. Retain
  every report exactly once with unique increasing team sequence numbers. Rollback
  must not leave a misleading successful receipt. Do not infer cross-worker
  causality from commit sequence.
- **STORE-4 — History.** State transitions append evidence without altering prior
  event content. Export/reopen yields the same history, revision and references.

## Delivery, routing and urgent handling

- **MSG-1 — Four facts.** Store an assignment without sending, submit to adapter,
  acknowledge its ID, and complete the requested action in four separate steps.
  Assert each step changes only its appropriate facts. Neither adapter success nor
  ack accepts a task or resolves an unrelated issue.
- **MSG-2 — Crash before send.** Commit pending delivery, kill runtime before send,
  restart, then dispatch. Deliver the original message ID once to the recipient.
- **MSG-3 — Crash after send.** Let recipient accept/execute the message, kill runtime
  before ack persistence, then restart and retry. Reuse the original ID; recipient
  executes once. If the real adapter cannot establish recipient deduplication or
  acceptance, record uncertainty and prohibit blind external-effect retry.
- **MSG-4 — Recipient isolation.** Publish to W1 and W2. Ack only W2 and restart.
  W1 remains pending/unresolved as appropriate; W2's ack does not acknowledge W1.
  An ack of a later urgent item does not hide an older normal item.
- **ROUTE-1 — Mediated publication.** W1 proposes a versioned contract for W2/W3.
  Only C1's publication creates selected deliveries, retaining the original
  proposal and exact artifact reference. Unselected recipients receive nothing.
- **ROUTE-2 — Actionable bulletin.** Publish an announcement requiring W2 to act.
  Assert a tracked delivery exists, its ack is distinct from action resolution,
  and duplicate publication requests do not fan out again.
- **URG-1 — Ordering.** Queue normal then urgent unresolved issues. Urgent is
  presented first while append-only sequence and older pending items remain intact.
- **URG-2 — Coalescing.** Repeat one issue with new reports: preserve report history
  but show one unresolved issue with updated evidence. Independent issues are not
  merged by equal prose. Resolving one does not resolve another; define reopen
  behavior for a recurrence after resolution.
- **URG-3 — Quiet bookkeeping.** Emit heartbeats, ordinary progress, delivery
  attempts and acks. None creates an Astra conversational acknowledgment loop.
  Results/questions/conflicts produce compact actionable notifications.

## Run lifecycle, controls and revised plans

- **RUN-1 — Stable identity.** Restart worker and reassign task. Agent/task IDs stay
  stable; retry receives a new run ID; old run history and evidence remain queryable.
- **RUN-2 — Single executor.** Race duplicate and distinct assignment requests for
  A. At most one executing attempt exists. A retry cannot start while an old
  attempt's liveness or external actions remain unresolved.
- **RUN-3 — Health versus outcome.** Test exit 0 without result, nonzero exit with
  evidence, live PID with missed heartbeats, and restored heartbeat. None implicitly
  accepts the task. Unresponsive differs from exited, and inspection precedes retry.
- **CTRL-1 — Actual pause.** Pause during a long tool call with a visible side-effect
  counter. Request persistence immediately holds new affected dispatch, but run is
  not reported paused until the adapter confirms quiescence. Unsupported pause or
  a still-running tool is reported accurately. Unrelated W3 continues.
- **CTRL-2 — Resume revision.** Revise an affected assignment while paused. It stays
  held until an explicit authorized resume; resume uses the committed revision.
  Duplicate resume requests cannot start a second execution.
- **CTRL-3 — Cancel race.** Race result/exit with cancel and crash between cancel
  send and confirmation. Preserve both observations; request receipt or signal
  delivery alone is not confirmed cancellation. Late results remain historical
  evidence and cannot silently overwrite accepted/cancelled state.
- **CTRL-4 — Bound control target.** Reuse a pane/session handle for a different run
  before an old queued control dispatches. Reject or reconcile the stale control;
  never interrupt the new occupant. Verify process start identity before signaling.
- **PLAN-1 — Stale result.** Assign B at revision 1, change A's contract at revision
  2, then receive B's revision-1 result. Preserve revision 1 on the result; move to
  review without accepting. Astra must assess changed dependencies and either
  explicitly justify acceptance or request revision. Merely checking team revision
  equality is insufficient; relevant dependency changes must be available to review.
- **PLAN-2 — Unrelated revision.** Change an unrelated task only. Astra can explicitly
  accept valid old-revision evidence after assessment; do not discard all old results.
- **PLAN-3 — Context completeness.** Inspect assignment received by each worker for
  objective, plan decisions, dependency contract references, expected output,
  acceptance checks, revision and exclusive write scope. Returned result contains
  findings, artifact references, validation evidence and unresolved issues.

## Recovery, artifacts and external effects

- **REC-1 — Launch boundaries.** Kill before launch intent, after committed intent
  before spawn, after spawn before handle observation, and after observation before
  receipt. Reconcile process/session/resource identity after restart before new
  dispatch. Each intent produces at most one current attempt; an unknown live
  process is not treated as absent and blindly relaunched.
- **REC-2 — PID reuse.** Replace the observed process with another process using a
  mismatching start identity at the recorded PID (deterministic identity adapter
  acceptable). Recovery and cleanup must not signal the replacement.
- **REC-3 — Coordinator/runtime restart.** Restart both with unresolved normal and
  urgent deliveries, paused runs, and incomplete operations. Restore plan and
  ownership, reconcile real processes/sessions, then permit dispatch. Inbox views
  and selective history recovery require no previous model context.
- **REC-4 — External timeout.** Perform a visible external action but lose its
  response. Mark the operation uncertain, inspect original action identity, and
  retry only after establishing whether it occurred. A unique message ID cannot
  establish exactly-once shell/git/API effects.
- **ART-1 — Finalization.** Attempt result/acceptance with missing file, partial file,
  invalid hash, wrong-team reference or modified content. These cannot satisfy
  acceptance. Finalize and hash before committing any reference.
- **ART-2 — Artifact crash.** Crash during file write and between finalization and
  database commit. Partial/orphan files are never accepted evidence; a committed
  reference always resolves to finalized content. Reconciliation preserves valid
  referenced artifacts.
- **ART-3 — Version retention.** Publish v1 then v2. Original messages still resolve
  v1 and its hash; updating a friendly filename cannot rewrite historical evidence.

## Live transport, panes and integration

- **LIVE-1 — Transport spike.** With installed Grok, launch, stream structured output,
  deliver assignment, establish recipient ack of its ID, send a related follow-up,
  resume session, and cancel. Record exact provider version and supported semantics.
  Shell piping or tmux typing alone does not prove live delivery or acknowledgment.
- **LIVE-2 — Exact Astra wake.** Open two Astra sessions; target one. Send actionable
  issue while target is idle and busy. Verify correct session gets it, the other
  does not, and document queued versus immediate behavior.
- **LIVE-3 — Tool interruption.** Repeat CTRL-1 against a real running Grok tool.
  Observe whether the tool and descendants stop and whether output/effects continue.
  A model interruption alone is not tool cancellation. Record unsupported behavior
  as a remaining gate, not as a passed pause/cancel capability.
- **LIVE-4 — Session policy.** Related follow-up reuses session; unrelated task uses
  a fresh session. No nested workers, mandatory poteto mode, or worker-to-worker
  coordination is introduced.
- **PANE-1 — Existing window.** Start in Astra's existing tmux window. Create a
  separate visible pane per worker plus runtime/status pane, retain exact server,
  window and pane IDs, tile layout and restore focus to the original pane.
- **PANE-2 — Ownership/reuse.** Reuse an idle team-owned pane. Never reuse or clean
  unrelated panes, another team's pane, or a reused handle with mismatching identity.
  Cleanup kills only the intended worker pane, preserving Astra and status panes.
- **PANE-3 — Capacity.** Fill available screen/pane capacity, assign another task,
  and assert it queues without hidden worker execution or destroying existing panes.
- **PANE-4 — Restart.** Restart runtime with panes present, missing and repurposed.
  Reconcile exact ownership before reusing/cleaning; no orphan duplicate panes.
- **CODE-1 — Worktrees.** Resolve the documented wt function location before code
  execution. Concurrent writers use distinct worktrees with nonoverlapping declared
  ownership; one named integration worker assembles accepted changes. Inspect
  actual checkout paths and branch assignments, not just assignment prose.
- **CODE-2 — Review authority.** Result, process exit and passing tests cannot self-
  accept work. Astra acceptance records reviewed evidence; incomplete/missing
  artifacts fail acceptance. Integration includes only accepted changes.
- **CODE-3 — Atomic stack.** In an authorized publishing fixture use gt create and
  gt submit --no-interactive. Each PR is logically atomic and independently passes
  required CI from its own head and base; retain PR URLs and CI evidence. Local
  tests or only the stack tip passing do not establish every PR passed CI.
- **FLOW-1 — MVP demonstration.** In one existing window, Astra delegates two bounded
  tasks, receives both results, requests and receives one revision, and accepts the
  combined outcome through the named integration worker. Include an urgent conflict
  during a tool call and a runtime/coordinator restart. Demonstrate durable history,
  mediated routing, accurate control outcomes and continued unrelated work.

## Release gates and measurements

Stage 1 requires live transport evidence (LIVE-1–3). Stage 2 requires transactional
store, identity and pane evidence (STORE, RUN, ART, PANE). Stage 3 requires routing,
epoch fencing and recovery fault evidence (AUTH, MSG, ROUTE, URG, CTRL, PLAN, REC).
Stage 4 requires role/worktree integration, per-PR CI and the complete MVP flow
(LIVE-4, CODE, FLOW). Missing live capabilities must be stated as limitations and
kept open; passing store tests cannot close a live gate.

Record urgent persistence-to-notification and persistence-to-ack latency separately,
restart-to-reconciled-dispatch time, failed/uncertain deliveries, duplicate recipient
executions, and Astra coordination turns excluding runtime bookkeeping. Record
hardware, worker count, provider versions and sample count. The brief specifies no
numeric latency threshold: report measurements and agree a threshold before using
them as a concurrency-increase gate. Start with two workers.
